"""Module điều phối và định tuyến các yêu cầu từ Client tới Handler tương ứng."""

import logging
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

# Đảm bảo đường dẫn import hoạt động khi chạy trực tiếp file này
ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# pylint: disable=wrong-import-position
from backend.handlers import (
    handle_create_issue,
    handle_create_project,
    handle_delete_history,
    handle_delete_issue,
    handle_delete_project,
    handle_get_config,
    handle_get_project,
    handle_list_history,
    handle_list_issues,
    handle_list_projects,
    handle_run_analysis,
    handle_update_config,
    handle_update_issue_status,
    handle_update_project,
)

logger = logging.getLogger(__name__)

HandlerType = Callable[[dict[str, Any]], dict[str, Any]]

ACTION_ROUTES: dict[str, HandlerType] = {
    # Nhóm dự án
    "project.create": handle_create_project,
    "project.list": handle_list_projects,
    "project.get": handle_get_project,
    "project.update": handle_update_project,
    "project.delete": handle_delete_project,
    # Nhóm phân tích
    "analysis.run": handle_run_analysis,
    # Nhóm sự cố (Issues)
    "issue.list": handle_list_issues,
    "issue.update_status": handle_update_issue_status,
    "issue.delete": handle_delete_issue,
    "issue.create": handle_create_issue,
    # Nhóm lịch sử quét
    "history.list": handle_list_history,
    "history.delete": handle_delete_history,
    # Nhóm cấu hình
    "config.get": handle_get_config,
    "config.update": handle_update_config,
}


def dispatch_request(request: Any) -> dict[str, Any]:
    """
    Điều phối yêu cầu từ Client dựa trên trường 'action' tới handler tương ứng.

    Args:
        request: Dữ liệu yêu cầu từ Client (phải là dict dạng JSON đối tượng).

    Returns:
        dict: Kết quả phản hồi từ handler hoặc thông báo lỗi chuẩn.
    """
    # 1. Kiểm tra request phải là dict
    if not isinstance(request, dict):
        return {
            "status": "error",
            "message": "Yêu cầu phải ở định dạng JSON đối tượng",
        }

    # 2. Kiểm tra trường 'action'
    action = request.get("action")
    if not action or not isinstance(action, str):
        return {
            "status": "error",
            "message": "Thiếu trường 'action' trong yêu cầu",
        }

    clean_action = action.strip()

    # 3. Tìm kiếm handler
    handler_func = ACTION_ROUTES.get(clean_action)
    if not handler_func:
        return {
            "status": "error",
            "message": f"Hành động '{clean_action}' không được hỗ trợ",
        }

    # 4. Trích xuất data (tự động chuẩn hóa về dict nếu không phải dict)
    data = request.get("data")
    if not isinstance(data, dict):
        data = {}

    # 5. Thực thi an toàn qua handler
    try:
        return handler_func(data)
    except Exception as exc:  # pylint: disable=broad-exception-caught
        logger.exception("Lỗi bất thường khi xử lý hành động '%s': %s", clean_action, exc)
        return {
            "status": "error",
            "message": f"Lỗi nội bộ khi xử lý '{clean_action}': {exc}",
        }
