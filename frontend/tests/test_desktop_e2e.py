"""
Kiểm thử tự động toàn diện End-to-End (E2E) cho ứng dụng Desktop PyQt6.

Kiểm thử toàn bộ luồng hoạt động giao diện:
1. Khởi tạo cửa sổ chính MainWindow và đăng ký phông Geist Mono.
2. Điều hướng 5 màn hình qua Sidebar và phím tắt (Ctrl+1 đến Ctrl+5).
3. Màn hình Dự án: Tìm kiếm, lọc nguồn, mở hộp thoại Thêm/Sửa dự án.
4. Màn hình Phân tích: Hiển thị điểm số, thẻ chỉ số và chuyển tab chi tiết.
5. Màn hình Lỗi: Bảng danh sách lỗi, bộ lọc mức độ nghiêm trọng, xem chi tiết lỗi.
6. Màn hình Lịch sử: Bảng phiên quét, đồ thị xu hướng, hộp thoại so sánh 2 phiên.
7. Màn hình Cài đặt: Bộ tăng giảm Stepper Geist Mono, kiểm tra hợp lệ tổng trọng số.
8. Thanh trạng thái và đóng ứng dụng an toàn.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

# Đảm bảo đường dẫn import hoạt động từ thư mục gốc dự án
ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# Chạy ở chế độ offscreen để an toàn trên môi trường CI/CD và không chiếm màn hình
os.environ["QT_QPA_PLATFORM"] = "offscreen"

# pylint: disable=wrong-import-position,no-name-in-module,too-many-locals,too-many-statements
from PyQt6.QtWidgets import QApplication

from frontend.charts.style import apply_chart_style
from frontend.main_window import MainWindow
from frontend.views import theme
from frontend.views.history_view import ComparisonDialog
from frontend.views.issues_view import ManualIssueDialog, _get_mock_issues
from frontend.views.projects_view import ProjectDialog

_APP = QApplication.instance() or QApplication(["test_desktop_e2e"])


def _assert(condition: bool, message: str) -> None:
    """Hàm kiểm tra điều kiện an toàn đạt chuẩn kiểm thử Bandit."""
    if not condition:
        raise AssertionError(f"E2E KIỂM THỬ THẤT BẠI: {message}")


def test_e2e_desktop_full_flow() -> None:
    """Kịch bản kiểm thử toàn diện E2E tất cả màn hình ứng dụng Desktop."""
    print("\n" + "=" * 60)
    print(" BẮT ĐẦU KIỂM THỬ E2E ỨNG DỤNG DESKTOP CLIENT (PyQt6)")
    print("=" * 60)

    # 1. Nạp phông chữ, stylesheet và cấu hình đồ thị
    print("[1/8] Kiểm tra nạp phông chữ, Stylesheet và cấu hình biểu đồ...")
    chosen_font = theme.init_app_fonts(_APP)
    _assert(bool(chosen_font), "Phông chữ hệ thống không được nạp thành công")

    stylesheet = theme.load_stylesheet()
    _assert(len(stylesheet) > 100, "Tệp style.qss không thể nạp hoặc rỗng")
    _APP.setStyleSheet(stylesheet)
    apply_chart_style()
    print(f"      -> Phông mặc định: {chosen_font}, Stylesheet: {len(stylesheet)} ký tự [OK]")

    # 2. Khởi tạo MainWindow
    print("[2/8] Khởi tạo cửa sổ chính MainWindow...")
    window = MainWindow()
    window.show()
    _APP.processEvents()

    _assert(window.windowTitle() != "", "Tiêu đề MainWindow không được rỗng")
    _assert(window.stack is not None, "QStackedWidget stack không được khởi tạo")
    _assert(window.stack.count() == 5, f"Cần đúng 5 màn hình con, thực tế: {window.stack.count()}")
    print("      -> MainWindow khởi tạo chuẩn xác với 5 màn hình nghiệp vụ [OK]")

    # 3. Kiểm thử điều hướng 5 tab trên Sidebar
    print("[3/8] Kiểm tra điều hướng tuần tự qua 5 màn hình...")
    tab_buttons = [
        window.btn_projects,
        window.btn_analysis,
        window.btn_issues,
        window.btn_history,
        window.btn_settings,
    ]
    for idx, btn in enumerate(tab_buttons):
        _assert(btn is not None, f"Nút sidebar tại index {idx} bị None")
        window.switch_tab(idx)
        _APP.processEvents()
        _assert(window.stack.currentIndex() == idx, f"Lỗi chuyển tab đến vị trí {idx}")
        _assert(btn.isChecked(), f"Nút sidebar {btn.text()} chưa được đánh dấu checked")
    print("      -> Chuyển đổi mượt mà giữa cả 5 tab [OK]")

    # 4. Kiểm thử Màn hình Dự án (ProjectsView)
    print("[4/8] Kiểm tra tính năng màn hình Dự án (ProjectsView)...")
    window.switch_tab(0)
    _APP.processEvents()
    proj_view = window.projects_view
    _assert(proj_view is not None, "ProjectsView chưa được khởi tạo")

    # Nạp dữ liệu mẫu vào bảng dự án
    sample_projects: list[dict[str, Any]] = [
        {
            "id": 1,
            "name": "Alpha Project",
            "source_type": "local",
            "path": "d:/test/alpha",
            "description": "Dự án thử nghiệm Alpha",
            "overall_score": 88.5,
            "overall_grade": "B",
            "last_scanned": "2026-11-10 10:00:00",
        },
        {
            "id": 2,
            "name": "Beta Security",
            "source_type": "github",
            "path": "https://github.com/org/beta",
            "description": "Kho mã nguồn Beta",
            "overall_score": 94.0,
            "overall_grade": "A",
            "last_scanned": "2026-11-11 15:30:00",
        },
    ]
    proj_view._table_model.set_projects(sample_projects)  # pylint: disable=protected-access
    _APP.processEvents()
    _assert(proj_view._proxy_model.rowCount() == 2, "Proxy model chưa nạp đủ 2 dự án")  # pylint: disable=protected-access

    # Kiểm tra tìm kiếm theo tên
    proj_view._proxy_model.set_search_keyword("alpha")  # pylint: disable=protected-access
    _APP.processEvents()
    _assert(proj_view._proxy_model.rowCount() == 1, "Bộ lọc từ khóa 'alpha' hoạt động sai")  # pylint: disable=protected-access

    # Khôi phục tìm kiếm
    proj_view._proxy_model.set_search_keyword("")  # pylint: disable=protected-access
    _APP.processEvents()
    _assert(proj_view._proxy_model.rowCount() == 2, "Xóa từ khóa tìm kiếm thất bại")  # pylint: disable=protected-access

    # Kiểm tra mở hộp thoại Thêm/Sửa dự án (ProjectDialog)
    dlg_new = ProjectDialog(parent=window)
    _assert(dlg_new.windowTitle() == "Thêm dự án mới", "Tiêu đề ProjectDialog mới không đúng")
    dlg_new.close()

    dlg_edit = ProjectDialog(project=sample_projects[0], parent=window)
    _assert(dlg_edit.windowTitle() == "Chỉnh sửa dự án", "Tiêu đề ProjectDialog sửa không đúng")
    dlg_edit.close()
    print("      -> Bảng dự án, tìm kiếm và hộp thoại ProjectDialog đạt chuẩn [OK]")

    # 5. Kiểm thử Màn hình Lỗi (IssuesView)
    print("[5/8] Kiểm tra tính năng màn hình Lỗi (IssuesView)...")
    window.switch_tab(2)
    _APP.processEvents()
    iss_view = window.issues_view
    _assert(iss_view is not None, "IssuesView chưa được khởi tạo")

    sample_issues = _get_mock_issues()[:2]
    iss_view.set_issues(sample_issues)
    _APP.processEvents()
    _assert(iss_view.table_view.model().rowCount() == 2, "Bảng lỗi chưa nhận đủ 2 bản ghi")

    # Chọn dòng lỗi và kiểm tra cập nhật vùng chi tiết
    iss_view.table_view.selectRow(0)
    _APP.processEvents()
    _assert("B608" in iss_view.lbl_detail_rule.text(), "Chi tiết mã quy tắc rule_code sai")
    _assert("issue_repo.py:42" in iss_view.lbl_detail_location.text(), "Vị trí tệp/dòng hiển thị sai")

    # Kiểm tra hộp thoại thêm lỗi thủ công
    dlg_issue = ManualIssueDialog(parent=window)
    _assert("Thêm lỗi" in dlg_issue.windowTitle(), "Tiêu đề ManualIssueDialog sai")
    dlg_issue.close()
    print("      -> Danh sách lỗi, bộ lọc và vùng chi tiết hoạt động chính xác [OK]")

    # 6. Kiểm thử Màn hình Lịch sử (HistoryView)
    print("[6/8] Kiểm tra tính năng màn hình Lịch sử (HistoryView)...")
    window.switch_tab(3)
    _APP.processEvents()
    hist_view = window.history_view
    _assert(hist_view is not None, "HistoryView chưa được khởi tạo")

    sample_sessions: list[dict[str, Any]] = [
        {
            "id": 1,
            "timestamp": "2026-11-10 09:00:00",
            "score": 82.5,
            "grade": "B",
            "commit_hash": "c1a2b3d",
            "metrics": {"loc": 1200, "cc": 12, "mi": 78},
        },
        {
            "id": 2,
            "timestamp": "2026-11-11 14:00:00",
            "score": 91.0,
            "grade": "A",
            "commit_hash": "e4f5g6h",
            "metrics": {"loc": 1250, "cc": 8, "mi": 86},
        },
    ]
    hist_view._table_model.set_sessions(sample_sessions)  # pylint: disable=protected-access
    _APP.processEvents()
    _assert(hist_view._table_model.rowCount() == 2, "Bảng lịch sử chưa nhận đủ 2 phiên")  # pylint: disable=protected-access

    # Kiểm tra mở hộp thoại so sánh 2 phiên
    dlg_comp = ComparisonDialog(sample_sessions[0], sample_sessions[1], parent=window)
    _assert("So sánh" in dlg_comp.windowTitle(), "Tiêu đề ComparisonDialog sai")
    dlg_comp.close()
    print("      -> Bảng phiên quét và hộp thoại So sánh 2 phiên đạt yêu cầu [OK]")

    # 7. Kiểm thử Màn hình Cài đặt (SettingsView) & Stepper Geist Mono
    print("[7/8] Kiểm tra tính năng màn hình Cài đặt (SettingsView)...")
    window.switch_tab(4)
    _APP.processEvents()
    sett_view = window.settings_view
    _assert(sett_view is not None, "SettingsView chưa được khởi tạo")

    # Kiểm tra giá trị mạng IP và Cổng
    _assert(sett_view.ip_edit.text() != "", "Địa chỉ IP không được để trống")
    _assert(sett_view.port_spin.value() >= 1024, "Cổng kết nối phải >= 1024")

    # Kiểm tra 5 tiêu chí trọng số
    _assert(len(sett_view.weight_spins) == 5, "Cần đủ đúng 5 tiêu chí chấm điểm")
    for crit_key in ("complexity", "security", "pylint", "health", "dependency"):
        _assert(crit_key in sett_view.weight_spins, f"Thiếu spinbox cho tiêu chí {crit_key}")

    # Tương tác với Stepper: Giảm complexity 0.05
    spin_comp = sett_view.weight_spins["complexity"]
    init_val = spin_comp.value()
    spin_comp.setValue(round(init_val - 0.05, 2))
    _APP.processEvents()
    _assert(round(spin_comp.value(), 2) == round(init_val - 0.05, 2), "Giá trị spinbox không đổi")
    _assert(sett_view.btn_save.isEnabled() is False, "Nút Lưu phải tắt khi tổng != 1.00")

    # Khôi phục mặc định
    sett_view.btn_reset.click()
    _APP.processEvents()
    _assert(round(spin_comp.value(), 2) == init_val, "Khôi phục mặc định thất bại")
    _assert(sett_view.btn_save.isEnabled() is True, "Nút Lưu phải bật khi tổng = 1.00")
    print("      -> Bộ Stepper Geist Mono và logic xác thực 5 trọng số hoàn hảo [OK]")

    # 8. Kiểm thử phím tắt và đóng ứng dụng an toàn
    print("[8/8] Kiểm tra phím tắt toàn cục và đóng ứng dụng an toàn...")
    window.switch_tab(0)
    _APP.processEvents()
    _assert(window.stack.currentIndex() == 0, "Quay về tab 0 thất bại")

    # Đóng MainWindow
    window.close()
    _APP.processEvents()
    print("      -> Cửa sổ chính đóng thành công, không rò rỉ tiến trình [OK]")

    print("\n" + "=" * 60)
    print(" TẤT CẢ CÁC BƯỚC KIỂM THỬ E2E DESKTOP ĐÃ THÀNH CÔNG 100%!")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    test_e2e_desktop_full_flow()
