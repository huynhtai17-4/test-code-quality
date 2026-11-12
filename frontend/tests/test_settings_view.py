"""Unit và Integration test cho Màn hình Cài đặt (settings_view.py) theo SKILLS.md."""

import os
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# Đảm bảo Qt chạy ở chế độ offscreen trong môi trường headless/CI
os.environ["QT_QPA_PLATFORM"] = "offscreen"

# pylint: disable=wrong-import-position,no-name-in-module
from PyQt6.QtWidgets import QApplication

from frontend import config
from frontend.views.settings_view import SettingsView
from frontend.views.theme import (
    GRADE_A,
    SEV_CRITICAL,
)

_APP = QApplication.instance() or QApplication(["test_settings_view"])


def _assert(condition: bool, message: str) -> None:
    """Xác thực điều kiện kiểm thử an toàn cho Bandit."""
    if not condition:
        raise RuntimeError(f"KIỂM THỬ THẤT BẠI: {message}")


def test_settings_view_initialization() -> None:
    """Kiểm thử khởi tạo SettingsView và các giá trị mặc định."""
    print("[*] 1. Kiểm tra khởi tạo SettingsView và giá trị mặc định...")
    view = SettingsView()

    _assert(view.ip_edit.text() == config.SERVER_HOST, "IP mặc định sai")
    _assert(view.port_spin.value() == config.SERVER_PORT, "Port mặc định sai")
    _assert(view.port_spin.minimum() == 1024, "Min port phải là 1024")
    _assert(view.port_spin.maximum() == 65535, "Max port phải là 65535")

    # Kiểm tra 5 tiêu chí
    _assert(len(view.weight_spins) == 5, "Phải có đúng 5 tiêu chí chấm điểm")
    for key in ("complexity", "security", "pylint", "health", "dependency"):
        _assert(key in view.weight_spins, f"Thiếu tiêu chí: {key}")
        spin = view.weight_spins[key]
        _assert(spin.minimum() == 0.00, "Min spin phải là 0.00")
        _assert(spin.maximum() == 1.00, "Max spin phải là 1.00")

    # Tổng mặc định phải là 1.00 và nút Lưu bật
    _assert("1.00" in view.lbl_total_value.text(), "Tổng ban đầu phải là 1.00")
    _assert(view.btn_save.isEnabled() is True, "Nút Lưu phải kích hoạt khi tổng = 1.00")
    _assert(GRADE_A in view.lbl_total_status.styleSheet(), "Trạng thái hợp lệ phải có màu xanh")

    print("    [OK] SettingsView nạp chính xác thông số mạng và 5 trọng số tiêu chí")


def test_weight_validation() -> None:
    """Kiểm thử logic xác thực tổng trọng số và cơ chế bật/tắt nút Lưu."""
    print("[*] 2. Kiểm tra xác thực tổng trọng số và nút Lưu thay đổi...")
    view = SettingsView()

    # Tăng trọng số complexity từ 0.25 lên 0.40 -> Tổng = 1.15
    view.weight_spins["complexity"].setValue(0.40)
    _APP.processEvents()

    _assert("1.15" in view.lbl_total_value.text(), "Tổng mới phải là 1.15")
    _assert("1.15" in view.lbl_total_status.text(), "Thông báo lỗi phải hiển thị tổng 1.15")
    _assert(SEV_CRITICAL in view.lbl_total_status.styleSheet(), "Cảnh báo phải có màu đỏ")
    _assert(view.btn_save.isEnabled() is False, "Nút Lưu phải bị vô hiệu khi tổng != 1.00")

    # Giảm trọng số dependency từ 0.15 về 0.00 -> Tổng = 1.00
    view.weight_spins["dependency"].setValue(0.00)
    _APP.processEvents()

    _assert("1.00" in view.lbl_total_value.text(), "Tổng mới phải là 1.00")
    _assert(view.btn_save.isEnabled() is True, "Nút Lưu phải bật khi tổng = 1.00")
    _assert("hợp lệ" in view.lbl_total_status.text(), "Phải hiện thông báo hợp lệ")

    # Kiểm tra nút Khôi phục mặc định
    view.btn_reset.click()
    _APP.processEvents()

    weights = view.get_weights()
    _assert(weights["complexity"] == 0.25, "Complexity sau reset phải là 0.25")
    _assert(weights["security"] == 0.25, "Security sau reset phải là 0.25")
    _assert(weights["pylint"] == 0.20, "Pylint sau reset phải là 0.20")
    _assert(weights["health"] == 0.15, "Health sau reset phải là 0.15")
    _assert(weights["dependency"] == 0.15, "Dependency sau reset phải là 0.15")
    _assert(view.btn_save.isEnabled() is True, "Sau reset nút Lưu phải bật")

    # Kiểm tra set_weights
    custom_weights = {
        "complexity": 0.20,
        "security": 0.20,
        "pylint": 0.20,
        "health": 0.20,
        "dependency": 0.20,
    }
    view.set_weights(custom_weights)
    _APP.processEvents()

    _assert(view.get_weights() == custom_weights, "set_weights nạp dữ liệu không khớp")
    _assert(view.btn_save.isEnabled() is True, "Tổng 5x0.20 = 1.00 nên nút Lưu phải bật")

    print("    [OK] Cơ chế kiểm soát trọng số, vô hiệu nút Lưu và khôi phục hoạt động hoàn hảo")


def test_ping_server_interaction() -> None:
    """Kiểm thử tương tác nút Kiểm tra kết nối."""
    print("[*] 3. Kiểm tra tính năng kiểm tra kết nối máy chủ...")
    view = SettingsView()
    # Nhập cổng giả lập không mở
    view.port_spin.setValue(59998)
    _APP.processEvents()

    status_messages: list[str] = []
    view.status_message.connect(status_messages.append)

    # Bấm nút ping máy chủ
    view.btn_ping.click()
    _APP.processEvents()

    if view._active_worker:  # pylint: disable=protected-access
        view._active_worker.wait()  # pylint: disable=protected-access
        _APP.processEvents()

    _assert(view.btn_ping.isEnabled() is True, "Nút ping phải được kích hoạt lại sau kiểm tra")
    _assert(len(view.lbl_ping_result.text()) > 0, "Nhãn kết quả ping phải có nội dung")

    print("    [OK] Tương tác kiểm tra kết nối xử lý mượt mà qua RequestWorker")


def main() -> None:
    """Hàm chạy toàn bộ bài kiểm thử Bước 4.5."""
    print("=" * 65)
    print("  KIỂM THỬ MÀN HÌNH CÀI ĐẶT HỆ THỐNG BƯỚC 4.5 (SKILLS.MD)  ")
    print("=" * 65)

    test_settings_view_initialization()
    test_weight_validation()
    test_ping_server_interaction()

    print("=" * 65)
    print("  [PASSED] MÀN HÌNH CÀI ĐẶT HỆ THỐNG ĐÃ ĐẠT CHUẨN KỸ THUẬT 100%!  ")
    print("=" * 65)


if __name__ == "__main__":
    main()
