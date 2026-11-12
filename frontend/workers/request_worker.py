"""Luồng chạy ngầm thực thi các tác vụ mạng ngắn (RequestWorker) kế thừa QThread."""

from collections.abc import Callable
from typing import Any
from PyQt6.QtCore import QObject, QThread, pyqtSignal  # pylint: disable=no-name-in-module


class RequestWorker(QThread):  # pylint: disable=too-few-public-methods
    """
    Luồng bất đồng bộ cho các tác vụ mạng ngắn (CRUD danh sách, lấy cấu hình, đổi trạng thái lỗi).

    Đảm bảo giao diện người dùng không bị đơ giật trong khi chờ Socket Backend phản hồi.
    """

    finished = pyqtSignal(dict)
    failed = pyqtSignal(str)

    def __init__(
        self,
        api_func: Callable[..., dict[str, Any]],
        *args: Any,
        parent: QObject | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(parent)
        self._api_func = api_func
        self._args = args
        self._kwargs = kwargs

    def run(self) -> None:
        """Thực thi hàm API trong luồng phụ và phát tín hiệu an toàn về giao diện chính."""
        try:
            response = self._api_func(*self._args, **self._kwargs)
            if isinstance(response, dict) and response.get("status") == "error":
                error_msg = str(response.get("message") or "Yêu cầu từ máy chủ thất bại")
                self.failed.emit(error_msg)
            elif isinstance(response, dict):
                self.finished.emit(response)
            else:
                self.finished.emit({"status": "ok", "data": response})
        except Exception as exc:  # pylint: disable=broad-exception-caught
            self.failed.emit(str(exc))
