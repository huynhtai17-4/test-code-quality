"""Handler xử lý các yêu cầu xem và xóa lịch sử phiên quét (history/sessions)."""

import sys
from pathlib import Path
from typing import Any

# Đảm bảo đường dẫn import hoạt động khi chạy trực tiếp file này
ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# pylint: disable=wrong-import-position
from backend.database.repositories import session_repo
from backend.handlers._base import error_response, parse_positive_int, success_response


def handle_list_history(data: dict[str, Any]) -> dict[str, Any]:
    """
    Lấy danh sách lịch sử các phiên quét của một dự án.

    Yêu cầu: project_id.
    Tùy chọn: limit (mặc định 50).
    """
    try:
        project_id = parse_positive_int(data.get("project_id"), "project_id")

        raw_limit = data.get("limit", 50)
        try:
            limit = int(raw_limit)
            if limit <= 0:
                limit = 50
        except (ValueError, TypeError):
            limit = 50

        sessions = session_repo.get_sessions_by_project(project_id=project_id, limit=limit)
        return success_response(sessions)
    except Exception as exc:  # pylint: disable=broad-exception-caught
        return error_response(f"Lỗi khi lấy lịch sử quét: {exc}")


def handle_delete_history(data: dict[str, Any]) -> dict[str, Any]:
    """
    Xóa một phiên quét theo session_id (tự động xóa kèm các issue thuộc phiên đó).
    """
    try:
        session_id = parse_positive_int(data.get("session_id"), "session_id")
        deleted = session_repo.delete_session(session_id)
        return success_response({"deleted": deleted})
    except Exception as exc:  # pylint: disable=broad-exception-caught
        return error_response(f"Lỗi khi xóa phiên quét: {exc}")
