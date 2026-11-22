"""Handler xử lý các yêu cầu CRUD cho đối tượng dự án (projects)."""

import sys
from pathlib import Path
from typing import Any

# Đảm bảo đường dẫn import hoạt động khi chạy trực tiếp file này
ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# pylint: disable=wrong-import-position
from backend.database.repositories import project_repo, session_repo
from backend.handlers._base import error_response, parse_positive_int, success_response


def handle_create_project(data: dict[str, Any]) -> dict[str, Any]:
    """
    Xử lý thêm mới dự án vào hệ thống.

    Yêu cầu các trường: 'name', 'source_path' (hoặc 'path').
    """
    try:
        name = str(data.get("name", "")).strip()
        if not name:
            return error_response("Tên dự án (name) không được để trống")

        source_path = str(data.get("source_path") or data.get("path") or "").strip()
        if not source_path:
            return error_response("Đường dẫn mã nguồn (source_path) không được để trống")

        description = data.get("description")
        language = str(data.get("language") or "python").strip()

        proj_id = project_repo.create_project(
            name=name,
            path=source_path,
            description=description,
            language=language,
        )
        return success_response({"project_id": proj_id})
    except Exception as exc:  # pylint: disable=broad-exception-caught
        return error_response(f"Lỗi khi tạo dự án: {exc}")


def handle_list_projects(_data: dict[str, Any]) -> dict[str, Any]:
    """Lấy danh sách tất cả các dự án đã đăng ký trong hệ thống."""
    try:
        projects = project_repo.get_all_projects()
        for proj in projects:
            sessions = session_repo.get_sessions_by_project(proj["id"], limit=1)
            if sessions:
                proj["latest_session"] = sessions[0]
        return success_response(projects)
    except Exception as exc:  # pylint: disable=broad-exception-caught
        return error_response(f"Lỗi khi lấy danh sách dự án: {exc}")


def handle_get_project(data: dict[str, Any]) -> dict[str, Any]:
    """Lấy thông tin chi tiết một dự án theo project_id."""
    try:
        project_id = parse_positive_int(data.get("project_id"), "project_id")
        project = project_repo.get_project_by_id(project_id)
        if not project:
            return error_response(f"Không tìm thấy dự án với ID = {project_id}")
        sessions = session_repo.get_sessions_by_project(project_id, limit=1)
        if sessions:
            project["latest_session"] = sessions[0]
        return success_response(project)
    except Exception as exc:  # pylint: disable=broad-exception-caught
        return error_response(f"Lỗi khi lấy thông tin dự án: {exc}")


def handle_update_project(data: dict[str, Any]) -> dict[str, Any]:
    """Cập nhật thông tin dự án (name, path/source_path, description, language)."""
    try:
        project_id = parse_positive_int(data.get("project_id"), "project_id")

        fields: dict[str, Any] = {}
        if "name" in data and str(data["name"]).strip():
            fields["name"] = str(data["name"]).strip()
        if "path" in data and str(data["path"]).strip():
            fields["path"] = str(data["path"]).strip()
        elif "source_path" in data and str(data["source_path"]).strip():
            fields["path"] = str(data["source_path"]).strip()
        if "description" in data:
            fields["description"] = data["description"]
        if "language" in data and str(data["language"]).strip():
            fields["language"] = str(data["language"]).strip()

        if not fields:
            return error_response("Không có trường dữ liệu hợp lệ để cập nhật")

        updated = project_repo.update_project(project_id, **fields)
        return success_response({"updated": updated})
    except Exception as exc:  # pylint: disable=broad-exception-caught
        return error_response(f"Lỗi khi cập nhật dự án: {exc}")


def handle_delete_project(data: dict[str, Any]) -> dict[str, Any]:
    """Xóa dự án theo project_id (tự động xóa kèm các session và issue liên quan)."""
    try:
        project_id = parse_positive_int(data.get("project_id"), "project_id")
        deleted = project_repo.delete_project(project_id)
        return success_response({"deleted": deleted})
    except Exception as exc:  # pylint: disable=broad-exception-caught
        return error_response(f"Lỗi khi xóa dự án: {exc}")
