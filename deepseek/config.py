import json
import logging
from pathlib import Path
from typing import Dict, Optional

log = logging.getLogger("deepseek")
CONFIG_PATH = Path(__file__).parent / "config.json"
EXAMPLE_PATH = Path(__file__).parent / "config.example.json"

def load_config() -> dict:
    if not CONFIG_PATH.exists() and EXAMPLE_PATH.exists():
        import shutil
        shutil.copy(EXAMPLE_PATH, CONFIG_PATH)
    if not CONFIG_PATH.exists():
        raise FileNotFoundError(f"Không tìm thấy file cấu hình: {CONFIG_PATH}")
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def save_config(cfg: dict):
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)

def update_config(new_data: dict) -> dict:
    cfg = load_config()
    for k, v in new_data.items():
        if isinstance(v, dict) and isinstance(cfg.get(k), dict):
            cfg[k].update(v)
        else:
            cfg[k] = v
    save_config(cfg)
    return cfg

def build_headers(cfg: dict, pow_token: Optional[str] = None) -> Dict[str, str]:
    device = cfg.get("device", {})
    headers = {
        "authority": "chat.deepseek.com",
        "accept": "*/*",
        "accept-language": "en-US,en;q=0.9,vi;q=0.8",
        "authorization": f"Bearer {cfg.get('auth_token', '')}",
        "content-type": "application/json",
        "origin": "https://chat.deepseek.com",
        "referer": "https://chat.deepseek.com/",
        "sec-ch-ua": '"Google Chrome";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-origin",
        "user-agent": device.get("user_agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"),
        "x-client-platform": "web",
        "x-client-version": "2.7.0",
        "x-device-id": device.get("x_device_id", ""),
        "x-hif-leim": device.get("x_hif_leim", "")
    }
    if pow_token:
        headers["x-ds-pow-response"] = pow_token
    return headers

def build_cookies(cfg: dict) -> dict:
    return cfg.get("cookies", {})
