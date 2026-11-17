"""Bộ điều khiển quản lý nghiệp vụ lịch sử quét và đối chiếu phiên (HistoryController)."""

from __future__ import annotations

from typing import Any

from PyQt6.QtCore import pyqtSignal  # pylint: disable=no-name-in-module

from frontend.controllers.base_controller import BaseController
from frontend.network import api


class HistoryController(BaseController):
    """Điều phối toàn bộ logic gọi API và luồng dữ liệu cho màn hình Lịch sử (HistoryView)."""

    history_loaded = pyqtSignal(list, int)
    session_deleted = pyqtSignal(int)

    def load_project_history(self, project_id: int) -> None:
        """Tải danh sách các phiên kiểm định của dự án qua API."""
        def _do_load() -> dict[str, Any]:
            return api.list_history(project_id)

        def _on_success(response: dict[str, Any]) -> None:
            raw_sessions = response.get("history") or response.get("data") or []
            sessions = list(raw_sessions) if isinstance(raw_sessions, list) else []
            self.history_loaded.emit(sessions, project_id)
            self.status_message.emit(f"Đã tải {len(sessions)} phiên phân tích trong lịch sử.")

        def _on_error(error_msg: str) -> None:
            self.error_occurred.emit(error_msg)
            self.status_message.emit(f"Lỗi tải lịch sử quét: {error_msg}")

        self._execute_async(
            task_fn=_do_load,
            on_success=_on_success,
            on_error=_on_error,
            loading_status=f"Đang tải lịch sử phiên quét dự án #{project_id}...",
        )

    def delete_session(self, session_id: int) -> None:
        """Xóa một phiên kiểm định khỏi lịch sử qua API."""
        def _do_delete() -> dict[str, Any]:
            return api.delete_history(session_id)

        def _on_success(_response: dict[str, Any]) -> None:
            self.session_deleted.emit(session_id)
            self.status_message.emit(f"Đã xóa phiên #{session_id} khỏi lịch sử.")

        self._execute_async(
            task_fn=_do_delete,
            on_success=_on_success,
            loading_status=f"Đang xóa phiên #{session_id}...",
        )
