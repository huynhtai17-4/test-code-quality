"""Handler xử lý các yêu cầu CRUD cho danh sách lỗi (issues)."""

import sys
from pathlib import Path
from typing import Any

# Đảm bảo đường dẫn import hoạt động khi chạy trực tiếp file này
ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# pylint: disable=wrong-import-position
from backend.database.repositories import issue_repo
from backend.handlers._base import error_response, parse_positive_int, success_response

VALID_STATUSES = frozenset({"open", "in_progress", "fixed", "false_positive", "ignored"})
VALID_SEVERITIES = frozenset({"info", "low", "medium", "high", "critical"})


def handle_list_issues(data: dict[str, Any]) -> dict[str, Any]:
    """
    Lấy danh sách lỗi thuộc một phiên quét cụ thể.

    Hỗ trợ lọc tùy chọn theo: status, severity, tool.
    """
    try:
        session_id = parse_positive_int(data.get("session_id"), "session_id")
        status = data.get("status")
        severity = data.get("severity")
        tool = data.get("tool")

        if status and str(status).lower() not in VALID_STATUSES:
            return error_response(f"Trạng thái lọc không hợp lệ: {status}")
        if severity and str(severity).lower() not in VALID_SEVERITIES:
            return error_response(f"Mức độ lỗi lọc không hợp lệ: {severity}")

        mapped_status = "ignored" if status and str(status).lower() == "false_positive" else status

        issues = issue_repo.get_issues_by_session(
            session_id=session_id,
            status=mapped_status,
            severity=severity,
            tool=tool,
        )
        return success_response(issues)
    except Exception as exc:  # pylint: disable=broad-exception-caught
        return error_response(f"Lỗi khi lấy danh sách lỗi: {exc}")


def handle_update_issue_status(data: dict[str, Any]) -> dict[str, Any]:
    """
    Cập nhật trạng thái xử lý lỗi (open, in_progress, fixed, false_positive, ignored) và ghi chú.
    """
    try:
        issue_id = parse_positive_int(data.get("issue_id"), "issue_id")

        raw_status = str(data.get("status", "")).strip().lower()
        if not raw_status:
            return error_response("Thiếu trường bắt buộc: 'status'")
        if raw_status not in VALID_STATUSES:
            valid_list = ", ".join(sorted(VALID_STATUSES))
            return error_response(f"Trạng thái không hợp lệ. Phải thuộc: {valid_list}")

        note = data.get("note")
        updated = issue_repo.update_issue_status(
            issue_id=issue_id,
            status=raw_status,
            note=note,
        )
        return success_response({"updated": updated})
    except Exception as exc:  # pylint: disable=broad-exception-caught
        return error_response(f"Lỗi khi cập nhật trạng thái lỗi: {exc}")


def handle_delete_issue(data: dict[str, Any]) -> dict[str, Any]:
    """Xóa một lỗi theo issue_id."""
    try:
        issue_id = parse_positive_int(data.get("issue_id"), "issue_id")
        deleted = issue_repo.delete_issue(issue_id)
        return success_response({"deleted": deleted})
    except Exception as exc:  # pylint: disable=broad-exception-caught
        return error_response(f"Lỗi khi xóa lỗi: {exc}")


def handle_create_issue(data: dict[str, Any]) -> dict[str, Any]:
    """
    Thêm lỗi thủ công từ người dùng vào phiên quét.

    Yêu cầu: session_id, file (hoặc file_path), message.
    Tùy chọn: line, severity (mặc định 'medium'), note, category (mặc định 'quality').
    """
    try:
        session_id = parse_positive_int(data.get("session_id"), "session_id")

        file_path = str(data.get("file_path") or data.get("file") or "").strip()
        if not file_path:
            return error_response("Đường dẫn file (file / file_path) không được để trống")

        message = str(data.get("message", "")).strip()
        if not message:
            return error_response("Nội dung thông báo (message) không được để trống")

        raw_severity = str(data.get("severity") or "medium").strip().lower()
        if raw_severity not in VALID_SEVERITIES:
            valid_sevs = ", ".join(sorted(VALID_SEVERITIES))
            return error_response(f"Mức độ lỗi không hợp lệ. Phải thuộc: {valid_sevs}")

        raw_line = data.get("line_number")
        if raw_line is None:
            raw_line = data.get("line")
        try:
            line_no = int(raw_line) if raw_line is not None else None
        except (ValueError, TypeError):
            line_no = None

        new_issue_id = issue_repo.create_issue(
            session_id=session_id,
            file_path=file_path,
            message=message,
            severity=raw_severity,
            tool="manual",
            category=str(data.get("category") or "quality").strip(),
            line_number=line_no,
            note=data.get("note"),
        )
        return success_response({"issue_id": new_issue_id})
    except Exception as exc:  # pylint: disable=broad-exception-caught
        return error_response(f"Lỗi khi tạo lỗi thủ công: {exc}")


def _test_issue_handler() -> None:
    """Kịch bản kiểm thử độc lập cho issue_handler."""
    from backend.database.repositories import project_repo, session_repo  # pylint: disable=import-outside-toplevel

    print("[*] Khởi tạo dữ liệu kiểm thử độc lập cho issue_handler...")
    proj_id = project_repo.create_project(
        name="Issue Handler Temp Project",
        path="backend/samples/bad_project",
    )
    sess_id = session_repo.create_session(project_id=proj_id, status="completed")

    try:
        # 1. Thêm lỗi thủ công
        create_res = handle_create_issue({
            "session_id": sess_id,
            "file": "backend/sample.py",
            "line": 15,
            "severity": "high",
            "message": "Phát hiện biến chưa khởi tạo do người dùng thêm thủ công",
        })
        print(f"[+] Thêm lỗi thủ công: {create_res}")
        if create_res.get("status") != "ok":
            return

        iss_id = create_res["data"]["issue_id"]

        # 2. Cập nhật trạng thái lỗi
        update_res = handle_update_issue_status({
            "issue_id": iss_id,
            "status": "false_positive",
            "note": "Đã kiểm tra, đây là tính năng cố ý",
        })
        print(f"[+] Cập nhật trạng thái: {update_res}")

        # 3. Lấy danh sách lỗi
        list_res = handle_list_issues({"session_id": sess_id})
        print(f"[+] Danh sách lỗi phiên quét: {len(list_res.get('data', []))} lỗi")

        # 4. Xóa lỗi
        del_res = handle_delete_issue({"issue_id": iss_id})
        print(f"[+] Xóa lỗi: {del_res}")

    finally:
        project_repo.delete_project(proj_id)
        print("[+] Đã dọn dẹp dữ liệu kiểm thử.")


if __name__ == "__main__":
    _test_issue_handler()
