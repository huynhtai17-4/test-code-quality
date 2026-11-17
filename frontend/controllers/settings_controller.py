"""Bộ điều khiển quản lý cấu hình hệ thống và kiểm tra kết nối (SettingsController)."""

from __future__ import annotations

from typing import Any

from PyQt6.QtCore import pyqtSignal  # pylint: disable=no-name-in-module

from frontend.controllers.base_controller import BaseController
from frontend.network import api


class SettingsController(BaseController):
    """Điều phối toàn bộ logic gọi API và cấu hình cho màn hình Cài đặt (SettingsView)."""

    ping_result = pyqtSignal(bool, str)
    configs_loaded = pyqtSignal(list)
    configs_saved = pyqtSignal(bool, str)

    def ping_server(self, host: str, port: int) -> None:
        """Kiểm tra khả năng kết nối tới Socket Server Backend."""
        def _do_ping() -> bool:
            return bool(api.ping_server(host=host, port=port, timeout=3.0))

        def _on_success(is_ok: bool) -> None:
            if is_ok:
                self.ping_result.emit(True, "● Kết nối thành công tới máy chủ")
                self.status_message.emit("Kết nối máy chủ Backend thành công.")
            else:
                self.ping_result.emit(
                    False,
                    "● Không thể kết nối tới máy chủ (kiểm tra lại cổng và tiến trình Backend)",
                )
                self.status_message.emit("Không thể kết nối tới máy chủ.")

        def _on_error(error_msg: str) -> None:
            self.ping_result.emit(
                False,
                f"● Lỗi kiểm tra kết nối: {error_msg}",
            )
            self.status_message.emit("Không thể kết nối tới máy chủ.")

        self._execute_async(
            task_fn=_do_ping,
            on_success=_on_success,
            on_error=_on_error,
            loading_status="Đang kiểm tra kết nối máy chủ...",
        )

    def load_current_configs(self) -> None:
        """Tải cấu hình trọng số thực tế từ backend."""
        def _do_load() -> dict[str, Any]:
            return api.get_config()

        def _on_success(response: dict[str, Any]) -> None:
            configs = response.get("data")
            if isinstance(configs, list):
                self.configs_loaded.emit(configs)
                self.status_message.emit("Đã nạp cấu hình trọng số từ máy chủ.")
            else:
                self.configs_loaded.emit([])

        def _on_error(_err_msg: str) -> None:
            self.status_message.emit("Không thể đọc cấu hình trọng số từ máy chủ.")

        self._execute_async(
            task_fn=_do_load,
            on_success=_on_success,
            on_error=_on_error,
            loading_status="Đang tải cấu hình...",
        )

    def save_configs(self, weights: dict[str, float]) -> None:
        """Lưu các giá trị trọng số vào cơ sở dữ liệu qua API."""
        def _do_save() -> dict[str, Any]:
            return api.update_config(weights)

        def _on_success(_response: dict[str, Any]) -> None:
            self.configs_saved.emit(True, "Đã lưu cấu hình trọng số thành công.")
            self.status_message.emit("Đã lưu cấu hình trọng số thành công.")

        def _on_error(error_msg: str) -> None:
            self.configs_saved.emit(False, error_msg)
            self.status_message.emit(f"Lỗi khi lưu cấu hình trọng số: {error_msg}")

        self._execute_async(
            task_fn=_do_save,
            on_success=_on_success,
            on_error=_on_error,
            loading_status="Đang lưu cấu hình trọng số...",
        )
