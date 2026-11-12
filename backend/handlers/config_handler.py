"""Handler xử lý các yêu cầu xem và cập nhật cấu hình trọng số (scoring config)."""

import sys
from pathlib import Path
from typing import Any

# Đảm bảo đường dẫn import hoạt động khi chạy trực tiếp file này
ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# pylint: disable=wrong-import-position
from backend.database.repositories import config_repo
from backend.handlers._base import error_response, success_response


def handle_get_config(data: dict[str, Any]) -> dict[str, Any]:
    """
    Lấy danh sách các tiêu chí và trọng số chấm điểm.

    Tùy chọn: active_only (bool, mặc định False).
    """
    try:
        active_only = bool(data.get("active_only", False))
        configs = config_repo.get_all_configs(active_only=active_only)
        return success_response(configs)
    except Exception as exc:  # pylint: disable=broad-exception-caught
        return error_response(f"Lỗi khi đọc cấu hình trọng số: {exc}")


def _parse_weights_payload(data: dict[str, Any]) -> dict[str, float]:
    """Trích xuất và kiểm tra tính hợp lệ của dữ liệu trọng số từ yêu cầu."""
    weights_dict: dict[str, float] = {}

    # Trường hợp 1: Dữ liệu dạng {'weights': {'metric_a': 25.0, ...}}
    if "weights" in data and isinstance(data["weights"], dict):
        for key, val in data["weights"].items():
            weight_float = float(val)
            if weight_float < 0 or weight_float > 100:
                raise ValueError(f"Trọng số của '{key}' phải từ 0 đến 100: {val}")
            weights_dict[str(key).strip()] = weight_float

    # Trường hợp 2: Dữ liệu dạng {'weights': [{'criterion': '...', 'weight': 25.0}, ...]}
    elif "weights" in data and isinstance(data["weights"], list):
        for item in data["weights"]:
            if isinstance(item, dict):
                key = str(item.get("metric_key") or item.get("criterion") or "").strip()
                val = float(item.get("weight", 0.0))
                if not key:
                    raise ValueError(
                        "Mỗi tiêu chí trong danh sách phải có tên (metric_key/criterion)"
                    )
                if val < 0 or val > 100:
                    raise ValueError(f"Trọng số của '{key}' phải từ 0 đến 100: {val}")
                weights_dict[key] = val

    # Trường hợp 3: Cập nhật đơn lẻ {'metric_key': '...', 'weight': 25.0} hoặc {'criterion': ...}
    elif ("metric_key" in data or "criterion" in data) and "weight" in data:
        key = str(data.get("metric_key") or data.get("criterion") or "").strip()
        val = float(data["weight"])
        if not key:
            raise ValueError("Tên tiêu chí (metric_key / criterion) không được để trống")
        if val < 0 or val > 100:
            raise ValueError(f"Trọng số của '{key}' phải từ 0 đến 100: {val}")
        weights_dict[key] = val

    return weights_dict


def handle_update_config(data: dict[str, Any]) -> dict[str, Any]:
    """
    Cập nhật trọng số chấm điểm cho một hoặc nhiều tiêu chí.

    Hỗ trợ:
    - Cập nhật đơn: {'metric_key': str, 'weight': float}
    - Cập nhật nhiều: {'weights': {key: weight, ...}} hoặc list các dict.
    """
    try:
        weights_dict = _parse_weights_payload(data)
        if not weights_dict:
            return error_response("Không tìm thấy dữ liệu trọng số hợp lệ cần cập nhật")

        if len(weights_dict) == 1:
            key, val = next(iter(weights_dict.items()))
            updated = config_repo.update_config(key, val)
            return success_response({"updated": updated, "updated_count": 1 if updated else 0})

        updated_count = config_repo.update_weights_bulk(weights_dict)
        return success_response({"updated": updated_count > 0, "updated_count": updated_count})
    except Exception as exc:  # pylint: disable=broad-exception-caught
        return error_response(f"Lỗi khi cập nhật trọng số: {exc}")


def _test_config_handler() -> None:
    """Kịch bản kiểm thử độc lập cho config_handler."""
    print("[*] Kiểm thử độc lập config_handler...")

    # 1. Đọc danh sách cấu hình
    configs_res = handle_get_config({})
    print(f"[+] Đọc cấu hình: {len(configs_res.get('data', []))} tiêu chí")
    if not configs_res.get("data"):
        return

    first_item = configs_res["data"][0]
    metric_key = first_item["metric_key"]
    original_weight = float(first_item["weight"])
    print(f"    - Tiêu chí đầu tiên: '{metric_key}', trọng số gốc: {original_weight}%")

    try:
        # 2. Cập nhật thử trọng số
        new_weight = 33.0
        up_res = handle_update_config({"metric_key": metric_key, "weight": new_weight})
        print(f"[+] Cập nhật trọng số mới ({new_weight}%): {up_res}")

        # 3. Đọc lại để kiểm chứng
        verify_res = handle_get_config({})
        for cfg in verify_res.get("data", []):
            if cfg["metric_key"] == metric_key:
                print(f"[+] Đã xác minh trong DB: '{metric_key}' = {cfg['weight']}%")
                break
    finally:
        # Khôi phục trọng số gốc
        restore_res = handle_update_config({"metric_key": metric_key, "weight": original_weight})
        print(f"[+] Khôi phục lại trọng số gốc: {restore_res.get('status')}")


if __name__ == "__main__":
    _test_config_handler()
