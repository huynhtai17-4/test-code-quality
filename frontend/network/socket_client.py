"""Lớp quản lý kết nối TCP Socket Client (SocketClient) giao tiếp với Backend."""

import logging
import socket
from types import TracebackType
from typing import Any

from frontend.config import SERVER_HOST, SERVER_PORT, SOCKET_TIMEOUT
from frontend.network import protocol

logger = logging.getLogger(__name__)


class SocketClient:
    """
    Quản lý phiên kết nối TCP Socket Client tới Backend Server.

    - Khởi tạo kết nối với cấu hình từ frontend/config.py.
    - Đóng gói yêu cầu dạng chuẩn: {"action": action, "data": data}.
    - Hỗ trợ ngữ cảnh context manager (with SocketClient() as client:).
    - Bắt ngoại lệ mạng an toàn, không làm crash ứng dụng giao diện.
    """

    def __init__(
        self,
        host: str = SERVER_HOST,
        port: int = SERVER_PORT,
        timeout: float = SOCKET_TIMEOUT,
    ) -> None:
        self.host = host
        self.port = port
        self.timeout = timeout
        self.sock: socket.socket | None = None

    @property
    def is_connected(self) -> bool:
        """Kiểm tra socket có đang được mở hay không."""
        return self.sock is not None

    def connect(self) -> bool:
        """
        Thiết lập kết nối socket TCP tới Backend Server.

        Returns:
            bool: True nếu kết nối thành công, False nếu máy chủ tắt hoặc lỗi mạng.
        """
        if self.sock is not None:
            return True

        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(self.timeout)
            sock.connect((self.host, self.port))
            self.sock = sock
            logger.info("Đã kết nối thành công tới %s:%s", self.host, self.port)
            return True
        except (ConnectionRefusedError, TimeoutError, OSError) as exc:
            logger.warning("Không thể kết nối tới %s:%s: %s", self.host, self.port, exc)
            self.close()
            return False

    def send_request(
        self,
        action: str,
        data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Đóng gói và gửi yêu cầu tới server, sau đó nhận và trả về kết quả phản hồi.

        Args:
            action: Tên hành động router backend (ví dụ: 'project.list', 'analysis.run').
            data: Dữ liệu tham số gửi kèm (mặc định là dict rỗng).

        Returns:
            dict: Phản hồi chuẩn từ server hoặc dict lỗi nếu mất kết nối.
        """
        if self.sock is None and not self.connect():
            return {
                "status": "error",
                "message": f"Không thể kết nối tới máy chủ tại {self.host}:{self.port}",
            }

        if self.sock is None:
            return {
                "status": "error",
                "message": "Kết nối socket chưa được khởi tạo",
            }

        request_payload = {
            "action": str(action).strip(),
            "data": data if isinstance(data, dict) else {},
        }

        # 1. Gửi gói tin request
        success = protocol.send_json(self.sock, request_payload)
        if not success:
            self.close()
            return {
                "status": "error",
                "message": "Lỗi đường truyền khi gửi yêu cầu tới máy chủ",
            }

        # 2. Nhận gói tin response
        response = protocol.recv_json(self.sock)
        if response is None:
            self.close()
            return {
                "status": "error",
                "message": "Mất kết nối với máy chủ khi chờ phản hồi",
            }

        return response

    def close(self) -> None:
        """Đóng kết nối socket một cách an toàn."""
        if self.sock is not None:
            try:
                self.sock.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            try:
                self.sock.close()
            except OSError:
                pass
            self.sock = None

    def __enter__(self) -> "SocketClient":
        """Hỗ trợ ngữ cảnh `with SocketClient() as client:`."""
        self.connect()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Tự động đóng kết nối khi thoát ngữ cảnh."""
        self.close()
