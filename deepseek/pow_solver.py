import base64
import json
import logging
import httpx
from deepseek_pow.models.challenge import Challenge
from deepseek_pow.solvers.deepseek_hash_v1_solver import DeepSeekHashV1Solver
from config import build_headers, build_cookies

log = logging.getLogger("deepseek")
solver = DeepSeekHashV1Solver()

async def get_pow_token(client: httpx.AsyncClient, cfg: dict, target_path: str = "/api/v0/chat/completion") -> str:
    """Tạo và giải PoW Challenge cho target_path chỉ định."""
    url = "https://chat.deepseek.com/api/v0/chat/create_pow_challenge"
    payload = {"target_path": target_path}
    headers = build_headers(cfg)
    cookies = build_cookies(cfg)

    res = await client.post(url, json=payload, headers=headers, cookies=cookies)
    res.raise_for_status()
    data = res.json()

    raw_challenge = data.get("data", {}).get("biz_data", {}).get("challenge")
    if not raw_challenge:
        raise RuntimeError(f"DeepSeek PoW Error: Không nhận được challenge ({data})")

    algorithm = raw_challenge.get("algorithm")
    if algorithm != "DeepSeekHashV1":
        raise RuntimeError(f"Thuật toán PoW không hỗ trợ: {algorithm}")

    challenge_obj = Challenge(
        algorithm=raw_challenge["algorithm"],
        challenge=raw_challenge["challenge"],
        salt=raw_challenge["salt"],
        signature=raw_challenge["signature"],
        difficulty=raw_challenge["difficulty"],
        expire_at=raw_challenge["expire_at"]
    )

    solution = solver.solve(challenge_obj)
    answer = int(solution.answer)

    pow_obj = {
        "algorithm": algorithm,
        "challenge": raw_challenge["challenge"],
        "salt": raw_challenge["salt"],
        "answer": answer,
        "signature": raw_challenge["signature"],
        "target_path": target_path
    }

    compact_json = json.dumps(pow_obj, separators=(",", ":"), ensure_ascii=False)
    return base64.b64encode(compact_json.encode("utf-8")).decode("ascii")
