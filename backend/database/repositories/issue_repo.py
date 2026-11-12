"""Repository xử lý các thao tác dữ liệu cho bảng issues."""

from typing import Any, Optional

from ._base import execute_insert, execute_many, execute_write, fetch_all, fetch_one

VALID_ISSUE_STATUSES = frozenset({"open", "in_progress", "fixed", "ignored"})
VALID_ISSUE_SEVERITIES = frozenset({"info", "low", "medium", "high", "critical"})


def create_issue(session_id: int, **fields: Any) -> int:
    """Thêm một lỗi thủ công hoặc đơn lẻ vào bảng issues và trả về ID."""
    severity = str(fields.get("severity", "medium")).lower()
    if severity not in VALID_ISSUE_SEVERITIES:
        raise ValueError(f"Mức độ lỗi không hợp lệ: {severity}")

    raw_status = str(fields.get("status", "open")).lower()
    clean_status = "ignored" if raw_status == "false_positive" else raw_status
    if clean_status not in VALID_ISSUE_STATUSES:
        raise ValueError(f"Trạng thái lỗi không hợp lệ: {raw_status}")

    file_path = str(fields.get("file_path") or fields.get("file") or ".")
    message = str(fields.get("message", ""))
    tool = str(fields.get("tool", "manual"))
    rule_code = fields.get("rule_code")
    category = str(fields.get("category", "quality"))
    line_number = fields.get("line_number")
    if line_number is None and "line" in fields:
        line_number = fields["line"]
    column_number = fields.get("column_number")
    note = fields.get("note")

    sql = """
        INSERT INTO issues (
            session_id, tool, rule_code, severity, category,
            file_path, line_number, column_number, message, status, note
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """
    params = (
        session_id,
        tool,
        rule_code,
        severity,
        category,
        file_path,
        line_number,
        column_number,
        message,
        clean_status,
        note,
    )
    return execute_insert(sql, params)


def add_issues_bulk(session_id: int, issues: list[dict[str, Any]]) -> int:
    """
    Thêm hàng loạt lỗi phát hiện được trong một phiên quét.

    Trả về số bản ghi đã được chèn vào bảng issues.
    """
    if not issues:
        return 0

    sql = """
        INSERT INTO issues (
            session_id, tool, rule_code, severity, category,
            file_path, line_number, column_number, message, status, note
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """
    rows = []
    for item in issues:
        severity = item.get("severity", "medium")
        if severity not in VALID_ISSUE_SEVERITIES:
            raise ValueError(f"Mức độ lỗi không hợp lệ: {severity}")

        status = item.get("status", "open")
        if status not in VALID_ISSUE_STATUSES:
            raise ValueError(f"Trạng thái lỗi không hợp lệ: {status}")

        rows.append((
            session_id,
            item["tool"],
            item.get("rule_code"),
            severity,
            item.get("category", "quality"),
            item["file_path"],
            item.get("line_number"),
            item.get("column_number"),
            item["message"],
            status,
            item.get("note"),
        ))

    return execute_many(sql, rows)


def get_issues_by_session(
    session_id: int,
    status: Optional[str] = None,
    severity: Optional[str] = None,
    tool: Optional[str] = None,
) -> list[dict[str, Any]]:
    """Lấy danh sách lỗi của một phiên quét, hỗ trợ lọc theo status, severity, tool."""
    if status is not None and status not in VALID_ISSUE_STATUSES:
        raise ValueError(f"Trạng thái lỗi không hợp lệ: {status}")
    if severity is not None and severity not in VALID_ISSUE_SEVERITIES:
        raise ValueError(f"Mức độ lỗi không hợp lệ: {severity}")

    sql = """
        SELECT id, session_id, tool, rule_code, severity, category,
               file_path, line_number, column_number, message,
               status, note, created_at, updated_at
        FROM issues
        WHERE session_id = %s
          AND (%s IS NULL OR status = %s)
          AND (%s IS NULL OR severity = %s)
          AND (%s IS NULL OR tool = %s)
        ORDER BY CASE severity
            WHEN 'critical' THEN 1
            WHEN 'high' THEN 2
            WHEN 'medium' THEN 3
            WHEN 'low' THEN 4
            WHEN 'info' THEN 5
            ELSE 6 END, id ASC
    """
    params = (session_id, status, status, severity, severity, tool, tool)
    return fetch_all(sql, params)


def get_issue_by_id(issue_id: int) -> Optional[dict[str, Any]]:
    """Lấy thông tin chi tiết một lỗi theo ID."""
    sql = """
        SELECT id, session_id, tool, rule_code, severity, category,
               file_path, line_number, column_number, message,
               status, note, created_at, updated_at
        FROM issues
        WHERE id = %s
    """
    return fetch_one(sql, (issue_id,))


def update_issue_status(
    issue_id: int,
    status: str,
    note: Optional[str] = None,
) -> bool:
    """Cập nhật trạng thái xử lý của lỗi (open, in_progress, fixed, ignored) và tùy chọn ghi chú."""
    mapped_status = "ignored" if status.lower() == "false_positive" else status.lower()
    if mapped_status not in VALID_ISSUE_STATUSES:
        raise ValueError(f"Trạng thái lỗi không hợp lệ: {status}")

    if note is not None:
        sql = "UPDATE issues SET status = %s, note = %s WHERE id = %s"
        return execute_write(sql, (mapped_status, note, issue_id)) > 0

    return execute_write(
        "UPDATE issues SET status = %s WHERE id = %s",
        (mapped_status, issue_id),
    ) > 0


def add_issue_note(issue_id: int, note: str) -> bool:
    """Thêm hoặc cập nhật ghi chú cho một lỗi."""
    return execute_write("UPDATE issues SET note = %s WHERE id = %s", (note, issue_id)) > 0


def delete_issue(issue_id: int) -> bool:
    """Xóa một lỗi theo ID."""
    return execute_write("DELETE FROM issues WHERE id = %s", (issue_id,)) > 0


def delete_issues_by_session(session_id: int) -> int:
    """Xóa toàn bộ lỗi thuộc về một phiên quét và trả về số dòng đã xóa."""
    return execute_write("DELETE FROM issues WHERE session_id = %s", (session_id,))


# Bí danh tương thích
bulk_create_issues = add_issues_bulk
