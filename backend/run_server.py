"""Điểm khởi chạy chính (entrypoint) của Backend TCP Socket Server."""

import logging
import signal
import sys
from pathlib import Path
from typing import Any

# Đảm bảo đường dẫn import hoạt động khi chạy từ thư mục bất kỳ
ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# pylint: disable=wrong-import-position
from backend.config import DB_DATABASE, DB_HOST, DB_PORT, SERVER_HOST, SERVER_PORT
from backend.network.socket_server import SocketServer

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("run_server")


def _print_banner() -> None:
    """In giao diện banner thông tin khởi động hệ thống trực quan."""
    line = "=" * 70
    sub_line = "-" * 70
    banner = f"""
{line}
   CODE QUALITY & SECURITY ANALYZER - BACKEND SERVER
{line}
  [*] Địa chỉ lắng nghe : {SERVER_HOST}:{SERVER_PORT}
  [*] CSDL MySQL        : {DB_HOST}:{DB_PORT} (Database: {DB_DATABASE})
  [*] Kiến trúc xử lý   : Multi-threaded TCP Socket Server (Framing)
  [*] Bộ công cụ hỗ trợ : Radon, Pylint, Bandit, Pip-audit, Project Health
{sub_line}
  [i] Hướng dẫn: Nhấn Ctrl+C để dừng máy chủ an toàn.
{line}
"""
    print(banner)


def main() -> None:
    """Khởi tạo và vận hành Socket Server."""
    _print_banner()

    server = SocketServer(host=SERVER_HOST, port=SERVER_PORT)

    def _shutdown_handler(signum: int, _frame: Any) -> None:
        """Xử lý tín hiệu ngắt từ hệ điều hành (SIGINT, SIGTERM)."""
        print(f"\n[*] Đã nhận tín hiệu dừng hệ thống ({signum}). Đang tắt máy chủ...")
        server.stop()
        print("[+] Máy chủ đã dừng và giải phóng tài nguyên. Tạm biệt!")
        sys.exit(0)

    signal.signal(signal.SIGINT, _shutdown_handler)
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, _shutdown_handler)

    try:
        server.start()
    except OSError as exc:
        print("\n" + "!" * 70)
        print("[-] CẢNH BÁO LỖI KHỞI ĐỘNG MÁY CHỦ (OSError):")
        print(f"    Chi tiết: {exc}")
        print(f"    -> Cổng {SERVER_PORT} có thể đang bị ứng dụng khác chiếm dụng.")
        print("    -> Gợi ý: Hãy kiểm tra tiến trình đang sử dụng hoặc thay đổi")
        print("              biến SERVER_PORT trong tệp cấu hình 'backend/.env'.")
        print("!" * 70 + "\n")
        sys.exit(1)
    except Exception as exc:  # pylint: disable=broad-exception-caught
        logger.exception("Lỗi không mong muốn trong tiến trình chính: %s", exc)
        sys.exit(1)


if __name__ == "__main__":
    main()
