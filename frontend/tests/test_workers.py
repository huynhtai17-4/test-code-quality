"""Kịch bản kiểm thử tích hợp Tầng Mạng & Luồng chạy ngầm (Bước 3 - SKILLS.md)."""

import socket
import sys
import threading
import time
from pathlib import Path
from typing import Any

# Đảm bảo đường dẫn import hoạt động từ thư mục gốc
ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# pylint: disable=wrong-import-position,no-name-in-module
from PyQt6.QtCore import QCoreApplication

from backend.config import SERVER_HOST, SERVER_PORT
from backend.network.socket_server import SocketServer
from frontend.network import api, protocol
from frontend.network.socket_client import SocketClient
from frontend.workers.analysis_worker import AnalysisWorker
from frontend.workers.request_worker import RequestWorker

_APP = QCoreApplication.instance() or QCoreApplication(["test_workers"])


def _assert(condition: bool, message: str) -> None:
    """Kiểm tra điều kiện kiểm định an toàn (thay thế assert cho Bandit)."""
    if not condition:
        raise RuntimeError(f"KIỂM THỬ THẤT BẠI: {message}")


def test_protocol_framing() -> None:
    """1. Kiểm tra đóng gói và bóc tách gói tin TCP (Framing)."""
    print("[*] 1. Kiểm tra giao thức protocol.py (Framing 4-byte)...")
    server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_sock.bind(("127.0.0.1", 0))
    server_sock.listen(1)
    port = server_sock.getsockname()[1]

    client_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_sock.connect(("127.0.0.1", port))
    conn, _ = server_sock.accept()

    try:
        # Gửi / nhận JSON
        test_payload = {"action": "test.ping", "data": {"num": 42, "msg": "Xin chào"}}
        send_ok = protocol.send_json(client_sock, test_payload)
        _assert(send_ok, "send_json thất bại")

        received = protocol.recv_json(conn)
        _assert(received == test_payload, f"recv_json không khớp: {received}")

        # Gửi / nhận raw bytes
        test_bytes = b"HELLOWORLD_RAW_DATA_12345"
        bytes_ok = protocol.send_bytes(conn, test_bytes)
        _assert(bytes_ok, "send_bytes thất bại")

        received_bytes = protocol.recv_bytes(client_sock)
        _assert(received_bytes == test_bytes, "recv_bytes không khớp")

        print("    [OK] Đóng gói 4 byte độ dài và truyền nhận JSON/bytes chính xác 100%")
    finally:
        client_sock.close()
        conn.close()
        server_sock.close()


def test_socket_client_error_handling() -> None:
    """2. Kiểm tra xử lý lỗi khi mất kết nối hoặc sai cổng."""
    print("[*] 2. Kiểm tra SocketClient xử lý lỗi kết nối an toàn...")
    # Thử kết nối tới cổng không tồn tại (ví dụ cổng 59999)
    client = SocketClient(host="127.0.0.1", port=59999, timeout=0.5)
    connected = client.connect()
    _assert(not connected, "SocketClient không được kết nối tới cổng đóng")

    resp = client.send_request("project.list")
    _assert(resp.get("status") == "error", "send_request phải trả về status error")
    print("    [OK] Bắt lỗi ConnectionRefused / Timeout an toàn, không sập chương trình")


def test_request_worker_unit() -> None:
    """3. Kiểm tra RequestWorker với API thành công và thất bại."""
    print("[*] 3. Kiểm tra RequestWorker (QThread)...")

    # Trường hợp 1: API thành công
    def mock_success_api() -> dict[str, Any]:
        return {"status": "ok", "data": ["item_1", "item_2"]}

    worker_ok = RequestWorker(mock_success_api)
    result_box: list[dict[str, Any]] = []
    worker_ok.finished.connect(result_box.append)
    worker_ok.start()
    worker_ok.wait(2000)
    _APP.processEvents()

    _assert(len(result_box) == 1, "Tín hiệu finished không được phát")
    _assert(result_box[0].get("status") == "ok", "Dữ liệu trả về không đúng")

    # Trường hợp 2: API báo lỗi
    def mock_error_api() -> dict[str, Any]:
        return {"status": "error", "message": "Lỗi dữ liệu mẫu"}

    worker_err = RequestWorker(mock_error_api)
    err_box: list[str] = []
    worker_err.failed.connect(err_box.append)
    worker_err.start()
    worker_err.wait(2000)
    _APP.processEvents()

    _assert(len(err_box) == 1, "Tín hiệu failed không được phát")
    _assert("Lỗi dữ liệu mẫu" in err_box[0], "Nội dung lỗi không đúng")
    print("    [OK] RequestWorker phát tín hiệu finished/failed chính xác 100%")


def test_analysis_worker_unit() -> None:
    """4. Kiểm tra AnalysisWorker và tính năng hủy (cancel)."""
    print("[*] 4. Kiểm tra AnalysisWorker và cơ chế hủy tiến trình...")
    worker = AnalysisWorker(project_id=999)
    progress_records: list[tuple[str, int]] = []
    worker.progress.connect(lambda msg, pct: progress_records.append((msg, pct)))

    # Kiểm tra lệnh hủy trước khi chạy
    worker.cancel()
    _assert(worker.is_cancelled, "Cờ is_cancelled phải là True")

    worker.start()
    worker.wait(2000)
    _APP.processEvents()

    _assert(len(progress_records) > 0, "Không nhận được tín hiệu tiến trình")
    last_msg = progress_records[-1][0]
    _assert("hủy" in last_msg.lower(), f"Thông báo hủy không khớp: {last_msg}")
    print("    [OK] AnalysisWorker khởi tạo tín hiệu và hỗ trợ dừng hủy an toàn")


def test_live_server_integration() -> None:
    """5. Kiểm tra tích hợp trực tiếp với Backend Socket Server."""
    print("[*] 5. Kiểm tra tích hợp trực tiếp với Backend Socket Server...")
    server_thread: threading.Thread | None = None
    server_instance: SocketServer | None = None

    # Kiểm tra xem máy chủ có đang chạy sẵn không
    if not api.ping_server(timeout=1.0):
        print("    -> Khởi động Backend SocketServer tạm thời để kiểm thử...")
        server_instance = SocketServer(host=SERVER_HOST, port=SERVER_PORT)
        server_thread = threading.Thread(target=server_instance.start, daemon=True)
        server_thread.start()
        time.sleep(0.5)

    try:
        # 1. Ping
        ping_ok = api.ping_server(timeout=2.0)
        _assert(ping_ok, f"ping_server thất bại tới {SERVER_HOST}:{SERVER_PORT}")
        print("    [OK] ping_server() -> True")

        # 2. Lấy cấu hình trọng số
        cfg_resp = api.get_config()
        _assert(cfg_resp.get("status") == "ok", f"get_config thất bại: {cfg_resp}")
        print(f"    [OK] api.get_config() trả về {len(cfg_resp.get('data', []))} tiêu chí")

        # 3. Lấy danh sách dự án
        proj_resp = api.list_projects()
        _assert(proj_resp.get("status") == "ok", f"list_projects thất bại: {proj_resp}")
        print(f"    [OK] api.list_projects() trả về {len(proj_resp.get('data', []))} dự án")

        # 4. Chạy RequestWorker trực tiếp với Backend
        worker = RequestWorker(api.get_config)
        finished_results: list[dict[str, Any]] = []
        worker.finished.connect(finished_results.append)
        worker.start()
        worker.wait(3000)
        _APP.processEvents()

        _assert(len(finished_results) == 1, "RequestWorker không nhận được phản hồi từ server")
        _assert(finished_results[0].get("status") == "ok", "Kết quả trả về không hợp lệ")
        print("    [OK] RequestWorker kết nối Backend Server và phát tín hiệu hoàn tất")

    finally:
        if server_instance is not None:
            print("    -> Dọn dẹp máy chủ SocketServer tạm thời...")
            server_instance.stop()
            time.sleep(0.2)


def main() -> None:
    """Hàm chạy toàn bộ bài kiểm thử tích hợp Bước 3."""
    print("=" * 65)
    print("  KIỂM THỬ TẦNG MẠNG & LUỒNG BẤT ĐỒNG BỘ BƯỚC 3 (SKILLS.MD)  ")
    print("=" * 65)
    test_protocol_framing()
    test_socket_client_error_handling()
    test_request_worker_unit()
    test_analysis_worker_unit()
    test_live_server_integration()
    print("=" * 65)
    print("  [PASSED] TẤT CẢ CÁC MỤC KIỂM THỬ BƯỚC 3 ĐÃ ĐẠT CHUẨN 100%!  ")
    print("=" * 65)


if __name__ == "__main__":
    main()
