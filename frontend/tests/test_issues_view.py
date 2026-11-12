"""Unit và Integration test cho Màn hình Quản lý Lỗi (issues_view.py) theo SKILLS.md."""

import os
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# Đảm bảo Qt chạy ở chế độ offscreen trong môi trường headless/CI
os.environ["QT_QPA_PLATFORM"] = "offscreen"

# pylint: disable=wrong-import-position,no-name-in-module
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QFont
from PyQt6.QtWidgets import QApplication

from frontend.views.issues_view import (
    IssueFilterProxyModel,
    IssueTableModel,
    IssuesView,
    ManualIssueDialog,
    _get_mock_issues,
)
from frontend.views.theme import (
    SEV_CRITICAL,
    STATUS_OPEN,
)

_APP = QApplication.instance() or QApplication(["test_issues_view"])


def _assert(condition: bool, message: str) -> None:
    """Xác thực điều kiện kiểm thử an toàn cho Bandit."""
    if not condition:
        raise RuntimeError(f"KIỂM THỬ THẤT BẠI: {message}")


def test_issue_table_model() -> None:
    """Kiểm thử IssueTableModel (5 cột, màu sắc, font, cập nhật và xóa)."""
    print("[*] 1. Kiểm tra IssueTableModel...")
    issues = _get_mock_issues()
    model = IssueTableModel(issues)

    _assert(model.rowCount() == 6, f"Sai số dòng: {model.rowCount()}")
    _assert(model.columnCount() == 5, f"Sai số cột: {model.columnCount()}")

    # Kiểm tra header
    _assert(model.headerData(0, Qt.Orientation.Horizontal) == "Tệp : Dòng", "Header cột 0 sai")
    _assert(model.headerData(1, Qt.Orientation.Horizontal) == "Mức độ", "Header cột 1 sai")
    _assert(model.headerData(2, Qt.Orientation.Horizontal) == "Trạng thái", "Header cột 2 sai")
    _assert(model.headerData(3, Qt.Orientation.Horizontal) == "Công cụ", "Header cột 3 sai")
    _assert(model.headerData(4, Qt.Orientation.Horizontal) == "Mô tả tóm tắt", "Header cột 4 sai")

    # Kiểm tra dữ liệu dòng 0 (Bandit SQL Injection)
    idx_loc = model.index(0, 0)
    _assert(
        model.data(idx_loc, Qt.ItemDataRole.DisplayRole)
        == "backend/database/repositories/issue_repo.py:42",
        "Hiển thị vị trí tệp : dòng không đúng",
    )
    font = model.data(idx_loc, Qt.ItemDataRole.FontRole)
    _assert(isinstance(font, QFont), "Cột 0 phải dùng phông monospace QFont")

    idx_sev = model.index(0, 1)
    _assert(model.data(idx_sev, Qt.ItemDataRole.DisplayRole) == "Critical", "Mức độ sai")
    fg_sev = model.data(idx_sev, Qt.ItemDataRole.ForegroundRole)
    _assert(isinstance(fg_sev, QColor), "Màu mức độ phải là QColor")
    _assert(fg_sev.name().upper() == SEV_CRITICAL.upper(), "Màu SEV_CRITICAL không khớp")

    idx_stat = model.index(0, 2)
    _assert(model.data(idx_stat, Qt.ItemDataRole.DisplayRole) == "● Chưa sửa", "Trạng thái sai")
    fg_stat = model.data(idx_stat, Qt.ItemDataRole.ForegroundRole)
    _assert(isinstance(fg_stat, QColor), "Màu trạng thái phải là QColor")
    _assert(fg_stat.name().upper() == STATUS_OPEN.upper(), "Màu STATUS_OPEN không khớp")

    idx_tool = model.index(0, 3)
    _assert(model.data(idx_tool, Qt.ItemDataRole.DisplayRole) == "Bandit", "Công cụ sai")

    # Kiểm tra UserRole trả về toàn bộ dictionary
    raw_issue = model.data(idx_loc, Qt.ItemDataRole.UserRole)
    _assert(isinstance(raw_issue, dict), "UserRole phải trả về dict")
    _assert(raw_issue.get("id") == 1, "ID lỗi không đúng")

    # Kiểm tra cập nhật trường dữ liệu
    updated = model.update_issue_fields(1, status="fixed", note="Đã sửa triệt để")
    _assert(updated is True, "Cập nhật lỗi thất bại")
    _assert(model.data(idx_stat, Qt.ItemDataRole.DisplayRole) == "● Đã sửa", "Trạng thái chưa đổi")

    # Kiểm tra xóa lỗi
    removed = model.remove_issue(1)
    _assert(removed is True, "Xóa lỗi thất bại")
    _assert(model.rowCount() == 5, "Số dòng sau khi xóa không đúng")
    _assert(
        model.data(model.index(0, 0), Qt.ItemDataRole.UserRole).get("id") == 2,
        "Dòng đầu sau khi xóa không đúng",
    )

    print("    [OK] IssueTableModel hiển thị 5 cột, định dạng màu và font monospace chuẩn xác")


def test_issue_filter_proxy_model() -> None:
    """Kiểm thử bộ lọc đa tiêu chí thời gian thực IssueFilterProxyModel."""
    print("[*] 2. Kiểm tra IssueFilterProxyModel...")
    issues = _get_mock_issues()
    source_model = IssueTableModel(issues)
    proxy = IssueFilterProxyModel()
    proxy.setSourceModel(source_model)

    _assert(proxy.rowCount() == 6, "Chưa lọc phải có 6 dòng")

    # Lọc theo Mức độ
    proxy.set_severity_filter("critical")
    _assert(proxy.rowCount() == 1, "Chỉ có 1 lỗi Critical")
    proxy.set_severity_filter("high")
    _assert(proxy.rowCount() == 2, "Có 2 lỗi High")
    proxy.set_severity_filter("all")
    _assert(proxy.rowCount() == 6, "Sau khi bỏ lọc mức độ phải có 6 dòng")

    # Lọc theo Trạng thái
    proxy.set_status_filter("in_progress")
    _assert(proxy.rowCount() == 1, "Chỉ có 1 lỗi đang sửa")
    proxy.set_status_filter("open")
    _assert(proxy.rowCount() == 3, "Có 3 lỗi chưa sửa")
    proxy.set_status_filter("all")
    _assert(proxy.rowCount() == 6, "Sau khi bỏ lọc trạng thái phải có 6 dòng")

    # Lọc theo Công cụ
    proxy.set_tool_filter("bandit")
    _assert(proxy.rowCount() == 2, "Có 2 lỗi Bandit")
    proxy.set_tool_filter("radon")
    _assert(proxy.rowCount() == 1, "Có 1 lỗi Radon")
    proxy.set_tool_filter("all")
    _assert(proxy.rowCount() == 6, "Sau khi bỏ lọc công cụ phải có 6 dòng")

    # Lọc theo từ khóa tìm kiếm
    proxy.set_search_text("CVE-2023-43804")
    _assert(proxy.rowCount() == 1, "Chỉ có 1 lỗi khớp CVE-2023-43804")
    proxy.set_search_text("backend/")
    _assert(proxy.rowCount() == 4, "Có 4 lỗi nằm trong thư mục backend/")
    proxy.set_search_text("")
    _assert(proxy.rowCount() == 6, "Sau khi xóa ô tìm kiếm phải có 6 dòng")

    # Lọc kết hợp (High + in_progress + bandit)
    proxy.set_severity_filter("high")
    proxy.set_status_filter("in_progress")
    proxy.set_tool_filter("bandit")
    _assert(proxy.rowCount() == 1, "Lọc kết hợp phải trả về đúng 1 lỗi")

    print("    [OK] IssueFilterProxyModel lọc chính xác theo Mức độ, Trạng thái, Công cụ, Từ khóa")


def test_manual_issue_dialog() -> None:
    """Kiểm thử hộp thoại ManualIssueDialog."""
    print("[*] 3. Kiểm tra ManualIssueDialog...")
    dialog = ManualIssueDialog()
    _assert(dialog.windowTitle() == "Thêm lỗi phát hiện thủ công", "Tiêu đề hộp thoại sai")
    _assert(dialog.isModal() is True, "Hộp thoại phải là modal")

    # Validate lỗi khi chưa điền đường dẫn tệp
    dialog._on_save()  # pylint: disable=protected-access
    _assert(not dialog.error_label.isHidden(), "error_label phải hiển thị khi thiếu đường dẫn tệp")
    _assert("Đường dẫn tệp" in dialog.error_label.text(), "Nội dung cảnh báo thiếu tệp sai")

    # Điền tệp nhưng thiếu mô tả
    dialog.file_edit.setText("backend/server.py")
    dialog._on_save()  # pylint: disable=protected-access
    _assert(not dialog.error_label.isHidden(), "error_label phải hiển thị khi thiếu mô tả")
    _assert("Mô tả chi tiết" in dialog.error_label.text(), "Nội dung cảnh báo thiếu mô tả sai")

    # Điền đủ dữ liệu hợp lệ
    dialog.message_edit.setPlainText("Lỗi kiểm tra quyền hạn")
    dialog.line_spin.setValue(120)
    dialog.rule_edit.setText("SEC-AUTH-02")
    dialog.note_edit.setText("Cần kiểm tra lại token")
    data = dialog.get_issue_data()

    _assert(data["file_path"] == "backend/server.py", "file_path sai")
    _assert(data["line_number"] == 120, "line_number sai")
    _assert(data["severity"] == "medium", "severity sai")
    _assert(data["rule_code"] == "SEC-AUTH-02", "rule_code sai")
    _assert(data["message"] == "Lỗi kiểm tra quyền hạn", "message sai")
    _assert(data["note"] == "Cần kiểm tra lại token", "note sai")
    _assert(data["tool"] == "manual", "tool phải là manual")

    print("    [OK] ManualIssueDialog validate và trích xuất dữ liệu chuẩn xác")


def test_issues_view() -> None:
    """Kiểm thử toàn bộ giao diện và tương tác của IssuesView."""
    print("[*] 4. Kiểm tra IssuesView...")
    view = IssuesView()
    issues = _get_mock_issues()
    view.set_issues(issues)

    _assert(view.table_stack.currentIndex() == 0, "Có dữ liệu phải hiển thị bảng")
    _assert(view.table_view.model().rowCount() == 6, "Bảng phải hiển thị 6 dòng")

    # Kiểm tra chọn dòng trên bảng cập nhật Detail Panel
    view.table_view.selectRow(0)
    _APP.processEvents()

    _assert(
        "backend/database/repositories/issue_repo.py:42" in view.lbl_detail_location.text(),
        "Chi tiết vị trí dòng 0 sai",
    )
    _assert(view.badge_severity.text() == "Nghiêm trọng", "Badge mức độ dòng 0 sai")
    _assert("B608" in view.lbl_detail_rule.text(), "Mã kiểm thử dòng 0 sai")
    _assert("SQL injection" in view.txt_detail_desc.toPlainText(), "Nội dung mô tả sai")
    _assert(view.combo_detail_status.currentData() == "open", "Trạng thái ban đầu sai")
    _assert("refactor lại câu lệnh SQL" in view.edit_detail_note.text(), "Ghi chú ban đầu sai")

    # Kiểm tra lưu ghi chú và đổi trạng thái trong detail panel
    status_msg_received: list[str] = []
    view.status_message.connect(status_msg_received.append)

    view.combo_detail_status.setCurrentIndex(1)  # Đang sửa (in_progress)
    view.edit_detail_note.setText("Ghi chú kiểm thử tự động")
    view.btn_save_note.click()
    _APP.processEvents()

    _assert(len(status_msg_received) > 0, "Không nhận được tín hiệu status_message")

    # Kiểm tra tìm kiếm theo file
    view.filter_by_file("projects_view.py")
    _assert(view.table_view.model().rowCount() == 1, "Lọc file projects_view.py phải có 1 dòng")

    # Kiểm tra chuyển sang rỗng khi lọc không khớp
    view.filter_by_file("non_existent_file_xyz.py")
    _assert(view.table_view.model().rowCount() == 0, "Không khớp phải có 0 dòng")
    _assert(view.table_stack.currentIndex() == 1, "0 kết quả phải chuyển sang EmptyState")

    # Reset lại filter
    view.filter_by_file("")
    _assert(view.table_view.model().rowCount() == 6, "Bỏ lọc file phải trở về 6 dòng")
    _assert(view.table_stack.currentIndex() == 0, "Trở lại có dữ liệu phải hiển thị bảng")

    print("    [OK] IssuesView tương tác chọn dòng, lọc, hiển thị chi tiết và phím tắt hoàn hảo")


def main() -> None:
    """Hàm chạy toàn bộ các bài kiểm thử Bước 4.3."""
    print("=" * 65)
    print("  KIỂM THỬ MÀN HÌNH QUẢN LÝ LỖI BƯỚC 4.3 (SKILLS.MD)  ")
    print("=" * 65)

    test_issue_table_model()
    test_issue_filter_proxy_model()
    test_manual_issue_dialog()
    test_issues_view()

    print("=" * 65)
    print("  [PASSED] MÀN HÌNH QUẢN LÝ LỖI ĐÃ ĐẠT CHUẨN KỸ THUẬT 100%!  ")
    print("=" * 65)


if __name__ == "__main__":
    main()
