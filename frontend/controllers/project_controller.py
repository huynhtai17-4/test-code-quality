"""Bộ điều khiển quản lý nghiệp vụ dự án (ProjectController)."""

from __future__ import annotations

from typing import Any

from PyQt6.QtCore import pyqtSignal  # pylint: disable=no-name-in-module

from frontend.controllers.base_controller import BaseController
from frontend.network import api


class ProjectController(BaseController):
    """Điều phối toàn bộ logic gọi API và luồng dữ liệu cho màn hình Quản lý Dự án."""

    projects_loaded = pyqtSignal(list)
    project_created = pyqtSignal(dict)
    project_updated = pyqtSignal(dict)
    project_deleted = pyqtSignal(int, str)

    def load_projects(self) -> None:
        """Tải danh sách dự án từ máy chủ qua API."""
        self._execute_async(
            task_fn=api.list_projects,
            on_success=self._on_load_success,
            on_error=self._on_load_failed,
            loading_status="Đang tải danh sách dự án...",
        )

    def _on_load_success(self, response: dict[str, Any]) -> None:
        """Xử lý khi danh sách dự án được tải về thành công."""
        projects = response.get("projects") or response.get("data") or []
        if isinstance(projects, list):
            self.projects_loaded.emit(projects)
            self.status_message.emit(f"Đã tải {len(projects)} dự án.")
        else:
            self.projects_loaded.emit([])
            self.status_message.emit("Đã tải 0 dự án.")

    def _on_load_failed(self, error_msg: str) -> None:
        """Xử lý khi tải danh sách dự án thất bại."""
        self.error_occurred.emit(error_msg)
        self.status_message.emit(f"Lỗi kết nối: {error_msg}")

    def create_project(self, data: dict[str, str]) -> None:
        """Thêm mới một dự án vào cơ sở dữ liệu qua API."""
        name = data.get("name", "")
        path = data.get("path", "")
        desc = data.get("description", "")
        source_type = data.get("source_type", "local")

        def _do_create() -> dict[str, Any]:
            return api.create_project(name=name, path=path, desc=desc, source_type=source_type)

        def _on_success(response: dict[str, Any]) -> None:
            created = response.get("project") or response.get("data") or {}
            self.project_created.emit(created)
            self.status_message.emit(f"Đã thêm dự án '{name}' thành công.")
            self.load_projects()

        self._execute_async(
            task_fn=_do_create,
            on_success=_on_success,
            loading_status=f"Đang thêm dự án '{name}'...",
        )

    def update_project(self, project_id: int, data: dict[str, str]) -> None:
        """Cập nhật thông tin dự án qua API."""
        name = data.get("name", "")
        path = data.get("path", "")
        desc = data.get("description", "")
        source_type = data.get("source_type", "local")

        def _do_update() -> dict[str, Any]:
            return api.update_project(
                project_id,
                name=name,
                path=path,
                description=desc,
                source_type=source_type,
            )

        def _on_success(response: dict[str, Any]) -> None:
            updated = response.get("project") or response.get("data") or {}
            self.project_updated.emit(updated)
            self.status_message.emit(f"Cập nhật dự án '{name}' thành công.")
            self.load_projects()

        self._execute_async(
            task_fn=_do_update,
            on_success=_on_success,
            loading_status=f"Đang cập nhật dự án '{name}'...",
        )

    def delete_project(self, project_id: int, project_name: str) -> None:
        """Xóa dự án khỏi hệ thống qua API."""
        def _do_delete() -> dict[str, Any]:
            return api.delete_project(project_id)

        def _on_success(_response: dict[str, Any]) -> None:
            self.project_deleted.emit(project_id, project_name)
            self.status_message.emit(f"Đã xóa dự án '{project_name}' thành công.")
            self.load_projects()

        self._execute_async(
            task_fn=_do_delete,
            on_success=_on_success,
            loading_status=f"Đang xóa dự án '{project_name}'...",
        )
