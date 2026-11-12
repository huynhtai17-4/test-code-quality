"""Repository xử lý các thao tác dữ liệu cho bảng scoring_config."""

from typing import Any, Optional

from ._base import execute_many, execute_write, fetch_all, fetch_one


def _validate_weight(weight: float) -> None:
    """Kiểm tra trọng số nằm trong khoảng hợp lệ [0, 100]."""
    if weight < 0 or weight > 100:
        raise ValueError(f"Trọng số phải nằm trong khoảng 0 đến 100 (nhận được: {weight})")


def get_all_configs(active_only: bool = False) -> list[dict[str, Any]]:
    """Lấy danh sách cấu hình trọng số chấm điểm."""
    sql_active = """
        SELECT id, metric_key, metric_name, weight, description, is_active, updated_at
        FROM scoring_config
        WHERE is_active = TRUE
        ORDER BY id ASC
    """
    sql_all = """
        SELECT id, metric_key, metric_name, weight, description, is_active, updated_at
        FROM scoring_config
        ORDER BY id ASC
    """
    return fetch_all(sql_active if active_only else sql_all)


def get_config_by_key(metric_key: str) -> Optional[dict[str, Any]]:
    """Lấy thông tin cấu hình trọng số theo metric_key."""
    sql = """
        SELECT id, metric_key, metric_name, weight, description, is_active, updated_at
        FROM scoring_config
        WHERE metric_key = %s
    """
    return fetch_one(sql, (metric_key,))


def update_weight(
    metric_key: str,
    weight: float,
    is_active: Optional[bool] = None,
) -> bool:
    """Cập nhật trọng số (và tùy chọn trạng thái kích hoạt) cho một tiêu chí chấm điểm."""
    _validate_weight(weight)

    sql = """
        UPDATE scoring_config
        SET weight = %s,
            is_active = CASE WHEN %s THEN %s ELSE is_active END
        WHERE metric_key = %s
    """
    params = (weight, is_active is not None, is_active, metric_key)
    return execute_write(sql, params) > 0


def update_weights_bulk(weights: dict[str, float]) -> int:
    """
    Cập nhật hàng loạt trọng số cho nhiều tiêu chí trong cùng một transaction.

    Trả về số bản ghi được cập nhật.
    """
    if not weights:
        return 0

    for value in weights.values():
        _validate_weight(value)

    sql = "UPDATE scoring_config SET weight = %s WHERE metric_key = %s"
    rows = [(value, key) for key, value in weights.items()]
    return execute_many(sql, rows)


def update_config(
    metric_key: str,
    weight: float,
    is_active: Optional[bool] = None,
) -> bool:
    """Bí danh cho update_weight để hỗ trợ các tầng nghiệp vụ."""
    return update_weight(metric_key, weight, is_active)
