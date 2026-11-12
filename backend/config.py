"""Cấu hình toàn cục cho hệ thống Backend (mạng TCP, CSDL MySQL và SQLite)."""

import os
from pathlib import Path
from dotenv import load_dotenv

# Đường dẫn thư mục backend và file .env
BASE_DIR = Path(__file__).resolve().parent
ENV_PATH = BASE_DIR / ".env"

# Nạp các biến môi trường từ file .env
if ENV_PATH.exists():
    load_dotenv(dotenv_path=ENV_PATH)
else:
    load_dotenv()


def _get_int_env(key: str, default: int) -> int:
    """Chuyển đổi biến môi trường sang int có fallback mặc định an toàn."""
    value = os.getenv(key)
    if value is None or not str(value).strip():
        return default
    try:
        return int(value)
    except ValueError:
        return default


# Cấu hình Socket Server
SERVER_HOST: str = os.getenv("SERVER_HOST", "127.0.0.1")
SERVER_PORT: int = _get_int_env("SERVER_PORT", 8000)

# Cấu hình Database
DB_TYPE: str = os.getenv("DB_TYPE", "").strip().lower()
SQLITE_PATH: str = os.getenv("SQLITE_PATH", str(BASE_DIR / "database" / "code_quality.db"))

DB_HOST: str = os.getenv("DB_HOST", "127.0.0.1")
DB_PORT: int = _get_int_env("DB_PORT", 3306)
DB_USER: str = os.getenv("DB_USER", "root")
DB_PASSWORD: str = os.getenv("DB_PASSWORD", "")
DB_DATABASE: str = os.getenv("DB_NAME") or os.getenv("DB_DATABASE", "code_quality_db")

DB_CONFIG: dict = {
    "host": DB_HOST,
    "port": DB_PORT,
    "user": DB_USER,
    "password": DB_PASSWORD,
    "database": DB_DATABASE,
    "charset": "utf8mb4",
}
