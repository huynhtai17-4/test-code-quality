"""Các hàm tiện ích dùng chung cho tầng Handlers."""

import logging
from typing import Any

logger = logging.getLogger(__name__)


def success_response(data: Any = None) -> dict[str, Any]:
    """Tạo phản hồi chuẩn trạng thái thành công."""
    return {"status": "ok", "data": data}


def error_response(message: str) -> dict[str, Any]:
    """Tạo phản hồi chuẩn trạng thái lỗi."""
    return {"status": "error", "message": str(message)}


def parse_positive_int(value: Any, field_name: str) -> int:
    """Chuyển đổi và kiểm tra giá trị là số nguyên dương (> 0)."""
    if value is None:
        raise ValueError(f"Thiếu trường bắt buộc: '{field_name}'")
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Trường '{field_name}' phải là số nguyên hợp lệ") from exc

    if parsed <= 0:
        raise ValueError(f"Trường '{field_name}' phải lớn hơn 0")
    return parsed
