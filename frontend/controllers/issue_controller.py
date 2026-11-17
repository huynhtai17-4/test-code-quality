"""Bộ điều khiển quản lý nghiệp vụ lỗi mã nguồn (IssueController)."""

from __future__ import annotations

import logging
from typing import Any

from PyQt6.QtCore import pyqtSignal  # pylint: disable=no-name-in-module

from frontend.controllers.base_controller import BaseController
from frontend.network import api

logger = logging.getLogger(__name__)


class IssueController(BaseController):
    """Điều phối toàn bộ logic gọi API và luồng dữ liệu cho màn hình Quản lý Lỗi (IssuesView)."""

    issues_loaded = pyqtSignal(list, int)
    issue_updated = pyqtSignal(int, str, object)
    issues_deleted = pyqtSignal(list)
    issue_created = pyqtSignal(dict)

    def load_session_issues(self, session_id: int) -> None:
        """Tải danh sách lỗi của phiên phân tích từ máy chủ qua API."""
        def _do_load() -> dict[str, Any]:
            return api.list_issues(session_id)

        def _on_success(response: dict[str, Any]) -> None:
            raw_issues = response.get("issues") or response.get("data") or []
            issues = list(raw_issues) if isinstance(raw_issues, list) else []
            self.issues_loaded.emit(issues, session_id)
            self.status_message.emit(f"Đã nạp {len(issues)} lỗi của phiên #{session_id}.")

        def _on_error(error_msg: str) -> None:
            self.error_occurred.emit(error_msg)
            self.status_message.emit(f"Lỗi tải danh sách lỗi: {error_msg}")

        self._execute_async(
            task_fn=_do_load,
            on_success=_on_success,
            on_error=_on_error,
            loading_status=f"Đang tải danh sách lỗi phiên #{session_id}...",
        )

    def update_issue(self, issue_id: int, status: str, note: str | None = None) -> None:
        """Cập nhật trạng thái hoặc ghi chú của lỗi qua API."""
        def _do_update() -> dict[str, Any]:
            return api.update_issue_status(issue_id, status, note)

        def _on_success(_response: dict[str, Any]) -> None:
            self.issue_updated.emit(issue_id, status, note)
            self.status_message.emit(f"Đã cập nhật lỗi #{issue_id}.")

        self._execute_async(
            task_fn=_do_update,
            on_success=_on_success,
            loading_status=f"Đang cập nhật lỗi #{issue_id}...",
        )

    def batch_update_status(self, issue_ids: list[int], new_status: str) -> None:
        """Cập nhật trạng thái hàng loạt cho nhiều lỗi."""
        if not issue_ids:
            return

        def _do_batch() -> list[int]:
            succeeded: list[int] = []
            for iid in issue_ids:
                try:
                    api.update_issue_status(iid, new_status)
                    succeeded.append(iid)
                except Exception as exc:  # pylint: disable=broad-exception-caught
                    logger.debug("Lỗi cập nhật trạng thái issue %s: %s", iid, exc)
            return succeeded

        def _on_success(succeeded_ids: list[int]) -> None:
            for iid in succeeded_ids:
                self.issue_updated.emit(iid, new_status, None)
            self.status_message.emit(
                f"Đã đổi trạng thái {len(succeeded_ids)} lỗi thành công."
            )

        self._execute_async(
            task_fn=_do_batch,
            on_success=_on_success,
            loading_status=f"Đang đổi trạng thái {len(issue_ids)} lỗi...",
        )

    def delete_issues(self, issue_ids: list[int]) -> None:
        """Xóa một hoặc nhiều lỗi khỏi hệ thống."""
        if not issue_ids:
            return

        def _do_delete() -> list[int]:
            deleted: list[int] = []
            for iid in issue_ids:
                try:
                    api.delete_issue(iid)
                    deleted.append(iid)
                except Exception as exc:  # pylint: disable=broad-exception-caught
                    logger.debug("Lỗi xóa issue %s: %s", iid, exc)
            return deleted

        def _on_success(deleted_ids: list[int]) -> None:
            self.issues_deleted.emit(deleted_ids)
            self.status_message.emit(f"Đã xóa thành công {len(deleted_ids)} lỗi.")

        self._execute_async(
            task_fn=_do_delete,
            on_success=_on_success,
            loading_status=f"Đang xóa {len(issue_ids)} lỗi...",
        )

    def create_manual_issue(self, session_id: int, issue_data: dict[str, Any]) -> None:
        """Thêm mới một lỗi ghi nhận thủ công vào phiên phân tích."""
        fpath = str(issue_data.get("file_path", "")).strip()
        line = issue_data.get("line_number")
        sev = str(issue_data.get("severity", "medium"))
        msg = str(issue_data.get("message", "")).strip()
        note = issue_data.get("note")

        def _do_create() -> dict[str, Any]:
            return api.create_manual_issue(
                session_id=session_id,
                file=fpath,
                line=line,
                severity=sev,
                message=msg,
                note=note,
            )

        def _on_success(response: dict[str, Any]) -> None:
            created = response.get("issue") or response.get("data") or {}
            self.issue_created.emit(created)
            self.status_message.emit("Thêm lỗi thủ công thành công.")
            self.load_session_issues(session_id)

        self._execute_async(
            task_fn=_do_create,
            on_success=_on_success,
            loading_status="Đang lưu lỗi thủ công...",
        )
