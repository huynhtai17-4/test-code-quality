import logging
import httpx
from config import build_headers, build_cookies, save_config

log = logging.getLogger("deepseek")

async def create_session(client: httpx.AsyncClient, cfg: dict) -> str:
    """Tạo một đoạn chat (session) mới trên chat.deepseek.com"""
    url = "https://chat.deepseek.com/api/v0/chat_session/create"
    headers = build_headers(cfg)
    cookies = build_cookies(cfg)

    res = await client.post(url, json={"character_id": None}, headers=headers, cookies=cookies)
    res.raise_for_status()
    data = res.json()

    biz = data.get("data", {}).get("biz_data", {})
    session_id = biz.get("id") or biz.get("chat_session", {}).get("id")
    if not session_id:
        raise RuntimeError(f"Không thể tạo phiên chat mới: {data}")

    log.info(f"Đã tạo phiên chat mới: {session_id}")
    cfg["chat_session_id"] = session_id
    save_config(cfg)
    return session_id

async def get_or_create_session(client: httpx.AsyncClient, cfg: dict, force_new: bool = False) -> str:
    """Lấy phiên chat hiện tại hoặc tạo phiên mới nếu chưa có / force_new=True."""
    if not force_new and cfg.get("chat_session_id"):
        return cfg["chat_session_id"]
    return await create_session(client, cfg)
