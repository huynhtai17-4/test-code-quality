import asyncio
import json
import logging
import httpx
from config import build_headers, build_cookies, save_config
from session import get_or_create_session
from pow_solver import get_pow_token

log = logging.getLogger("deepseek")

async def chat_completion(
    client: httpx.AsyncClient,
    cfg: dict,
    prompt: str,
    thinking_enabled: bool = True,
    force_new_session: bool = False,
    max_retries: int = 3,
) -> str:
    """Gửi câu hỏi tới DeepSeek Web và bóc tách câu trả lời từ luồng SSE."""
    session_id = await get_or_create_session(client, cfg, force_new=force_new_session)

    for attempt in range(max_retries):
        try:
            pow_token = await get_pow_token(client, cfg)
            headers = build_headers(cfg, pow_token)
            cookies = build_cookies(cfg)

            payload = {
                "chat_session_id": session_id,
                "parent_message_id": None,
                "prompt": prompt,
                "ref_file_ids": [],
                "thinking_enabled": thinking_enabled,
                "search_enabled": False,
            }

            url = "https://chat.deepseek.com/api/v0/chat/completion"
            async with client.stream(
                "POST",
                url,
                json=payload,
                headers=headers,
                cookies=cookies,
                timeout=120.0,
            ) as resp:
                if resp.status_code in (429, 503) or "busy" in (await resp.aread()).decode(errors="ignore").lower():
                    wait = 2 ** attempt + 1
                    log.warning(f"DeepSeek bị giới hạn / bận – thử lại sau {wait}s...")
                    await asyncio.sleep(wait)
                    # Tạo phiên chat mới khi thử lại
                    session_id = await get_or_create_session(client, cfg, force_new=True)
                    continue

                resp.raise_for_status()

                full_response = []
                is_in_response = False

                async for line in resp.aiter_lines():
                    if not line.startswith("data:"):
                        continue
                    data_str = line[5:].strip()
                    if data_str == "[DONE]":
                        break
                    try:
                        msg = json.loads(data_str)
                    except json.JSONDecodeError:
                        continue

                    # Khởi tạo khối RESPONSE
                    if "v" in msg and isinstance(msg["v"], dict) and "response" in msg["v"]:
                        fragments = msg["v"]["response"].get("fragments", [])
                        for f in fragments:
                            if f.get("type") == "RESPONSE":
                                is_in_response = True
                                if f.get("content"):
                                    full_response.append(f["content"])
                        continue

                    # Chuyển đổi trạng thái từ THINK sang RESPONSE
                    if msg.get("p") == "response/fragments" and isinstance(msg.get("v"), list):
                        for f in msg.get("v", []):
                            if isinstance(f, dict) and f.get("type") == "RESPONSE":
                                is_in_response = True
                                if f.get("content"):
                                    full_response.append(f["content"])
                        continue

                    # Thu thập text delta trong khối RESPONSE
                    if is_in_response and "v" in msg and isinstance(msg["v"], str):
                        if msg.get("o") == "SET" or msg.get("p") == "response/status":
                            continue
                        full_response.append(msg["v"])

                result_text = "".join(full_response).strip()
                if result_text:
                    return result_text

                # Nếu chưa nhận được kết quả (có thể do session bận), tạo session mới và retry
                log.warning(f"Chưa nhận được phản hồi (lần {attempt + 1}/{max_retries}), đang thử lại...")
                session_id = await get_or_create_session(client, cfg, force_new=True)
                await asyncio.sleep(2.0)

        except httpx.HTTPStatusError as e:
            log.error(f"HTTP error {e.response.status_code}: {e}")
            if e.response.status_code in (401, 403):
                raise RuntimeError("Auth token hoặc cookies đã hết hạn! Vui lòng cập nhật config.json")
            if attempt == max_retries - 1:
                raise
            await asyncio.sleep(2 ** attempt)
        except Exception as e:
            log.exception(f"Lỗi gửi câu hỏi: {e}")
            if attempt == max_retries - 1:
                raise
            await asyncio.sleep(2 ** attempt)

    raise RuntimeError("Không thể nhận câu trả lời sau số lần thử tối đa.")
