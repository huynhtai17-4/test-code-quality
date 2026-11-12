"""Repository xử lý các thao tác dữ liệu cho bảng analysis_sessions."""

from typing import Any, Optional

from ._base import execute_insert, execute_write, fetch_all, fetch_one

VALID_SESSION_STATUSES = frozenset({"pending", "running", "completed", "failed"})
_ALLOWED_METRIC_FIELDS = frozenset({
    "total_files",
    "total_loc",
    "total_issues",
    "maintainability_index",
    "cyclomatic_complexity",
    "pylint_score",
    "security_issues_count",
    "summary",
})


def create_session(
    project_id: int,
    total_score: Optional[float] = None,
    grade: Optional[str] = None,
    summary: Optional[str] = None,
    status: Optional[str] = None,
) -> int:
    """Tạo phiên quét mã nguồn mới cho dự án và trả về session ID."""
    resolved_status = status or ("completed" if total_score is not None else "pending")
    if resolved_status not in VALID_SESSION_STATUSES:
        raise ValueError(f"Trạng thái phiên quét không hợp lệ: {resolved_status}")

    sql = """
        INSERT INTO analysis_sessions (
            project_id, status, total_score, grade, summary, completed_at
        )
        VALUES (
            %s, %s, %s, %s, %s,
            CASE WHEN %s IN ('completed', 'failed') THEN CURRENT_TIMESTAMP ELSE NULL END
        )
    """
    params = (
        project_id,
        resolved_status,
        total_score,
        grade,
        summary,
        resolved_status,
    )
    return execute_insert(sql, params)


def update_session_results(
    session_id: int,
    total_score: Optional[float] = None,
    grade: Optional[str] = None,
    status: str = "completed",
    metrics: Optional[dict[str, Any]] = None,
) -> bool:
    """Cập nhật điểm tổng kết, xếp loại, trạng thái và các chỉ số phân tích của phiên quét."""
    if status not in VALID_SESSION_STATUSES:
        raise ValueError(f"Trạng thái phiên quét không hợp lệ: {status}")

    metric_data = metrics or {}
    invalid_keys = set(metric_data.keys()) - _ALLOWED_METRIC_FIELDS
    if invalid_keys:
        raise ValueError(f"Chỉ số không hợp lệ: {', '.join(sorted(invalid_keys))}")

    sql = """
        UPDATE analysis_sessions
        SET status = %s,
            total_score = CASE WHEN %s THEN %s ELSE total_score END,
            grade = CASE WHEN %s THEN %s ELSE grade END,
            total_files = CASE WHEN %s THEN %s ELSE total_files END,
            total_loc = CASE WHEN %s THEN %s ELSE total_loc END,
            total_issues = CASE WHEN %s THEN %s ELSE total_issues END,
            maintainability_index = CASE WHEN %s THEN %s ELSE maintainability_index END,
            cyclomatic_complexity = CASE WHEN %s THEN %s ELSE cyclomatic_complexity END,
            pylint_score = CASE WHEN %s THEN %s ELSE pylint_score END,
            security_issues_count = CASE WHEN %s THEN %s ELSE security_issues_count END,
            summary = CASE WHEN %s THEN %s ELSE summary END,
            completed_at = CASE WHEN %s IN ('completed', 'failed') THEN CURRENT_TIMESTAMP ELSE completed_at END
        WHERE id = %s
    """
    params = (
        status,
        total_score is not None,
        total_score,
        grade is not None,
        grade,
        "total_files" in metric_data,
        metric_data.get("total_files"),
        "total_loc" in metric_data,
        metric_data.get("total_loc"),
        "total_issues" in metric_data,
        metric_data.get("total_issues"),
        "maintainability_index" in metric_data,
        metric_data.get("maintainability_index"),
        "cyclomatic_complexity" in metric_data,
        metric_data.get("cyclomatic_complexity"),
        "pylint_score" in metric_data,
        metric_data.get("pylint_score"),
        "security_issues_count" in metric_data,
        metric_data.get("security_issues_count"),
        "summary" in metric_data,
        metric_data.get("summary"),
        status,
        session_id,
    )
    return execute_write(sql, params) > 0


def get_session_by_id(session_id: int) -> Optional[dict[str, Any]]:
    """Lấy thông tin chi tiết một phiên quét theo ID."""
    sql = """
        SELECT s.*, p.name AS project_name, p.path AS project_path
        FROM analysis_sessions AS s
        INNER JOIN projects AS p ON p.id = s.project_id
        WHERE s.id = %s
    """
    return fetch_one(sql, (session_id,))


def get_sessions_by_project(project_id: int, limit: int = 50) -> list[dict[str, Any]]:
    """Truy vấn lịch sử các phiên quét của một dự án theo thứ tự mới nhất."""
    sql = """
        SELECT id, project_id, status, total_files, total_loc, total_issues,
               maintainability_index, cyclomatic_complexity, pylint_score,
               security_issues_count, total_score, grade, summary,
               started_at, completed_at
        FROM analysis_sessions
        WHERE project_id = %s
        ORDER BY started_at DESC, id DESC
        LIMIT %s
    """
    return fetch_all(sql, (project_id, limit))


def get_recent_sessions(limit: int = 20) -> list[dict[str, Any]]:
    """Truy vấn danh sách các phiên quét gần nhất trên toàn hệ thống."""
    sql = """
        SELECT s.id, s.project_id, p.name AS project_name, s.status,
               s.total_files, s.total_issues, s.total_score, s.grade,
               s.started_at, s.completed_at
        FROM analysis_sessions AS s
        INNER JOIN projects AS p ON p.id = s.project_id
        ORDER BY s.started_at DESC, s.id DESC
        LIMIT %s
    """
    return fetch_all(sql, (limit,))


def delete_session(session_id: int) -> bool:
    """Xóa một phiên quét theo ID."""
    return execute_write("DELETE FROM analysis_sessions WHERE id = %s", (session_id,)) > 0
