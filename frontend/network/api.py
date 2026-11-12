"""Các hàm tiện ích API gọi ngắn hạn (Short-lived Socket Client) tới Backend."""

from typing import Any

from frontend.config import ANALYSIS_TIMEOUT
from frontend.network.socket_client import SocketClient


def _call_api(
    action: str,
    data: dict[str, Any] | None = None,
    timeout: float | None = None,
) -> dict[str, Any]:
    """Hàm phụ trợ: Mở kết nối -> Gửi yêu cầu -> Nhận phản hồi -> Đóng kết nối."""
    kwargs: dict[str, Any] = {}
    if timeout is not None:
        kwargs["timeout"] = timeout
    with SocketClient(**kwargs) as client:
        return client.send_request(action=action, data=data)


# =====================================================================
# 1. KIỂM TRA KẾT NỐI (PING)
# =====================================================================
def ping_server(
    host: str | None = None,
    port: int | None = None,
    timeout: float = 3.0,
) -> bool:
    """
    Kiểm tra máy chủ Backend có đang hoạt động và chấp nhận kết nối hay không.

    Args:
        host: Địa chỉ IP máy chủ (mặc định SERVER_HOST).
        port: Cổng kết nối (mặc định SERVER_PORT).
        timeout: Thời gian chờ tối đa (giây).

    Returns:
        bool: True nếu kết nối thành công, False nếu máy chủ chưa bật.
    """
    try:
        kwargs: dict[str, Any] = {"timeout": timeout}
        if host is not None:
            kwargs["host"] = host
        if port is not None:
            kwargs["port"] = port
        with SocketClient(**kwargs) as client:
            return client.connect()
    except Exception:  # pylint: disable=broad-exception-caught
        return False


# =====================================================================
# 2. QUẢN LÝ DỰ ÁN (PROJECTS)
# =====================================================================
def list_projects() -> dict[str, Any]:
    """Lấy danh sách tất cả các dự án trong hệ thống."""
    return _call_api("project.list", {})


def get_project(project_id: int) -> dict[str, Any]:
    """Lấy thông tin chi tiết một dự án theo ID."""
    return _call_api("project.get", {"project_id": project_id})


def create_project(  # pylint: disable=too-many-arguments,too-many-positional-arguments
    name: str,
    path: str,
    desc: str = "",
    source_type: str = "local",
    timeout: float = 60.0,
) -> dict[str, Any]:
    """
    Đăng ký một dự án mới vào hệ thống.

    Args:
        name: Tên dự án.
        path: Đường dẫn thư mục mã nguồn.
        desc: Mô tả ngắn gọn về dự án.
        source_type: Loại nguồn ('local', 'git', ...).
        timeout: Thời gian chờ tối đa cho tạo/clone dự án.
    """
    payload = {
        "name": name,
        "source_path": path,
        "description": desc,
        "source_type": source_type,
    }
    return _call_api("project.create", payload, timeout=timeout)


def update_project(
    project_id: int,
    name: str | None = None,
    path: str | None = None,
    description: str | None = None,
    source_type: str | None = None,
) -> dict[str, Any]:
    """Cập nhật thông tin dự án."""
    payload: dict[str, Any] = {"project_id": project_id}
    if name is not None:
        payload["name"] = name
    if path is not None:
        payload["source_path"] = path
    if description is not None:
        payload["description"] = description
    if source_type is not None:
        payload["source_type"] = source_type
    return _call_api("project.update", payload)


def delete_project(project_id: int) -> dict[str, Any]:
    """Xóa một dự án theo ID kèm toàn bộ dữ liệu lịch sử liên quan."""
    return _call_api("project.delete", {"project_id": project_id})


# =====================================================================
# 3. TIẾN TRÌNH PHÂN TÍCH (ANALYSIS)
# =====================================================================
def run_analysis(
    project_id: int,
    timeout: float = ANALYSIS_TIMEOUT,
) -> dict[str, Any]:
    """
    Khởi động phiên kiểm định mã nguồn toàn diện cho dự án.

    Args:
        project_id: ID của dự án cần phân tích.
        timeout: Thời gian chờ tối đa cho phân tích (mặc định ANALYSIS_TIMEOUT).
    """
    return _call_api("analysis.run", {"project_id": project_id}, timeout=timeout)


# =====================================================================
# 4. QUẢN LÝ SỰ CỐ / LỖI MÃ NGUỒN (ISSUES)
# =====================================================================
def list_issues(
    session_id: int,
    status: str | None = None,
    severity: str | None = None,
    tool: str | None = None,
) -> dict[str, Any]:
    """Lấy danh sách lỗi mã nguồn của một phiên quét."""
    payload: dict[str, Any] = {"session_id": session_id}
    if status:
        payload["status"] = status
    if severity:
        payload["severity"] = severity
    if tool:
        payload["tool"] = tool
    return _call_api("issue.list", payload)


def update_issue_status(
    issue_id: int,
    status: str,
    note: str | None = None,
) -> dict[str, Any]:
    """Cập nhật trạng thái xử lý lỗi (open/in_progress/fixed/ignored) và ghi chú."""
    payload: dict[str, Any] = {"issue_id": issue_id, "status": status}
    if note is not None:
        payload["note"] = note
    return _call_api("issue.update_status", payload)


def delete_issue(issue_id: int) -> dict[str, Any]:
    """Xóa một lỗi khỏi cơ sở dữ liệu."""
    return _call_api("issue.delete", {"issue_id": issue_id})


def create_manual_issue(  # pylint: disable=too-many-arguments,too-many-positional-arguments
    session_id: int,
    file: str,
    line: int | None = None,
    severity: str = "medium",
    message: str = "",
    note: str | None = None,
) -> dict[str, Any]:
    """Thêm lỗi thủ công từ phản ánh của người kiểm thử."""
    payload: dict[str, Any] = {
        "session_id": session_id,
        "file_path": file,
        "line_number": line,
        "severity": severity,
        "message": message,
    }
    if note is not None:
        payload["note"] = note
    return _call_api("issue.create", payload)


# =====================================================================
# 5. LỊCH SỬ QUÉT & CẤU HÌNH TRỌNG SỐ (HISTORY & CONFIG)
# =====================================================================
def list_history(project_id: int, limit: int = 50) -> dict[str, Any]:
    """Xem danh sách các lần quét trước đây của dự án."""
    return _call_api("history.list", {"project_id": project_id, "limit": limit})


def delete_history(session_id: int) -> dict[str, Any]:
    """Xóa một phiên quét trong lịch sử."""
    return _call_api("history.delete", {"session_id": session_id})


def get_config(active_only: bool = False) -> dict[str, Any]:
    """Lấy danh sách các tiêu chí và trọng số tính điểm."""
    return _call_api("config.get", {"active_only": active_only})


def update_config(
    criterion_or_weights: str | dict[str, float],
    weight: float | None = None,
) -> dict[str, Any]:
    """
    Cập nhật trọng số tính điểm cho một hoặc nhiều tiêu chí.

    Args:
        criterion_or_weights: Tên tiêu chí (str) hoặc dictionary {metric: weight}.
        weight: Giá trị trọng số (float) nếu cập nhật đơn lẻ.
    """
    if isinstance(criterion_or_weights, dict):
        return _call_api("config.update", {"weights": criterion_or_weights})
    return _call_api("config.update", {"criterion": criterion_or_weights, "weight": weight})
