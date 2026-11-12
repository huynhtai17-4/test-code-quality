"""Unit và Integration test cho Màn hình Lịch sử & So sánh (history_view.py) theo SKILLS.md."""

import json
import os
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# Đảm bảo Qt chạy ở chế độ offscreen trong môi trường headless/CI
os.environ["QT_QPA_PLATFORM"] = "offscreen"

# pylint: disable=wrong-import-position,no-name-in-module
from PyQt6.QtCore import QItemSelectionModel, Qt
from PyQt6.QtGui import QColor, QFont
from PyQt6.QtWidgets import QApplication

from frontend.views.history_view import (
    ComparisonDialog,
    HistoryTableModel,
    HistoryTrendCanvas,
    HistoryView,
    _get_mock_history_sessions,
)
from frontend.views.theme import (
    GRADE_A,
    GRADE_B,
    GRADE_F,
    TEXT_MUTED,
)

_APP = QApplication.instance() or QApplication(["test_history_view"])


def _assert(condition: bool, message: str) -> None:
    """Xác thực điều kiện kiểm thử an toàn cho Bandit."""
    if not condition:
        raise RuntimeError(f"KIỂM THỬ THẤT BẠI: {message}")


def test_history_table_model() -> None:
    """Kiểm thử HistoryTableModel (7 cột, định dạng điểm, xếp loại, font monospace)."""
    print("[*] 1. Kiểm tra HistoryTableModel...")
    sessions = _get_mock_history_sessions()
    model = HistoryTableModel(sessions)

    _assert(model.rowCount() == 5, f"Sai số dòng: {model.rowCount()}")
    _assert(model.columnCount() == 7, f"Sai số cột: {model.columnCount()}")

    # Kiểm tra header
    _assert(model.headerData(0, Qt.Orientation.Horizontal) == "Mã phiên", "Header cột 0 sai")
    _assert(model.headerData(1, Qt.Orientation.Horizontal) == "Thời gian", "Header cột 1 sai")
    _assert(model.headerData(2, Qt.Orientation.Horizontal) == "Điểm số", "Header cột 2 sai")
    _assert(model.headerData(3, Qt.Orientation.Horizontal) == "Xếp loại", "Header cột 3 sai")
    _assert(model.headerData(4, Qt.Orientation.Horizontal) == "Tổng lỗi", "Header cột 4 sai")
    _assert(
        model.headerData(5, Qt.Orientation.Horizontal) == "Nghiêm trọng (C / H)",
        "Header cột 5 sai",
    )
    _assert(model.headerData(6, Qt.Orientation.Horizontal) == "Khác (M / L)", "Header cột 6 sai")

    # Dòng 0 phải là phiên mới nhất (#5 - 79.3 B) do tự động sort descending
    idx_id = model.index(0, 0)
    _assert(model.data(idx_id, Qt.ItemDataRole.DisplayRole) == "#5", "Phiên mới nhất phải là #5")
    font = model.data(idx_id, Qt.ItemDataRole.FontRole)
    _assert(isinstance(font, QFont), "Mã phiên phải dùng phông monospace QFont")

    idx_score = model.index(0, 2)
    _assert(
        model.data(idx_score, Qt.ItemDataRole.DisplayRole) == "79.3 / 100",
        "Điểm số phiên #5 sai",
    )

    idx_grade = model.index(0, 3)
    _assert(model.data(idx_grade, Qt.ItemDataRole.DisplayRole) == "B", "Xếp loại phiên #5 sai")
    fg_grade = model.data(idx_grade, Qt.ItemDataRole.ForegroundRole)
    _assert(isinstance(fg_grade, QColor), "Màu xếp loại phải là QColor")
    _assert(fg_grade.name().upper() == GRADE_B.upper(), "Màu GRADE_B không khớp")

    idx_tot = model.index(0, 4)
    _assert(model.data(idx_tot, Qt.ItemDataRole.DisplayRole) == "8", "Tổng lỗi phiên #5 sai")

    idx_ch = model.index(0, 5)
    _assert(
        model.data(idx_ch, Qt.ItemDataRole.DisplayRole) == "C: 0 | H: 2",
        "Phân bố C/H phiên #5 sai",
    )

    idx_ml = model.index(0, 6)
    _assert(
        model.data(idx_ml, Qt.ItemDataRole.DisplayRole) == "M: 4 | L: 2",
        "Phân bố M/L phiên #5 sai",
    )

    # Kiểm tra xóa phiên quét
    removed = model.remove_session(5)
    _assert(removed is True, "Xóa phiên #5 thất bại")
    _assert(model.rowCount() == 4, "Số dòng sau khi xóa phải là 4")
    _assert(
        model.data(model.index(0, 0), Qt.ItemDataRole.DisplayRole) == "#4",
        "Dòng đầu sau khi xóa phải là #4",
    )

    print("    [OK] HistoryTableModel hiển thị 7 cột, định dạng màu và font monospace chuẩn xác")


def test_comparison_dialog() -> None:
    """Kiểm thử hộp thoại ComparisonDialog đối chiếu 2 phiên quét."""
    print("[*] 2. Kiểm tra ComparisonDialog...")
    sessions = _get_mock_history_sessions()
    sess_old = sessions[0]  # #1 (45.0 F)
    sess_new = sessions[4]  # #5 (79.3 B)

    # Thử truyền ngược thứ tự (sess_new trước, sess_old sau) để kiểm tra tự động sắp xếp
    dialog = ComparisonDialog(sess_new, sess_old)
    _assert(
        dialog.windowTitle() == "So sánh kết quả giữa hai phiên phân tích",
        "Tiêu đề hộp thoại sai",
    )
    _assert(dialog.old_sess.get("id") == 1, "Phiên cũ phải là #1")
    _assert(dialog.new_sess.get("id") == 5, "Phiên mới phải là #5")

    # Kiểm tra bảng đối chiếu
    table = dialog._build_comparison_table()  # pylint: disable=protected-access
    _assert(table.rowCount() == 6, "Bảng so sánh phải có 6 dòng")
    _assert(table.columnCount() == 4, "Bảng so sánh phải có 4 cột")

    # Kiểm tra dòng Độ phức tạp (dòng 0): 40.0 -> 76.0 (+36.00)
    delta_item = table.item(0, 3)
    _assert("▲ +36.00" in delta_item.text(), f"Delta độ phức tạp sai: {delta_item.text()}")
    _assert(delta_item.foreground().color().name().upper() == GRADE_A.upper(), "Màu tăng phải xanh")

    # Kiểm tra dòng Điểm tổng kết (dòng 5): 45.0 (F) -> 79.3 (B) (+34.30)
    tot_name = table.item(5, 0)
    tot_delta = table.item(5, 3)
    _assert(tot_name.text() == "Điểm tổng kết", "Tên dòng 5 phải là Điểm tổng kết")
    _assert("▲ +34.30" in tot_delta.text(), f"Delta điểm tổng kết sai: {tot_delta.text()}")

    # Kiểm tra trường hợp điểm giảm hoặc không đổi
    sess_reduced = dict(sess_new)
    sess_reduced["id"] = 6
    sess_reduced["total_score"] = 60.0
    sess_reduced["started_at"] = "2026-11-12 10:00:00"
    sess_reduced["summary"] = json.dumps({
        "criteria_scores": {
            "complexity": 76.0,  # không đổi (diff = 0)
            "security": 60.0,    # giảm từ 84 xuống 60 (diff = -24)
        }
    })

    dialog_down = ComparisonDialog(sess_new, sess_reduced)
    table_down = dialog_down._build_comparison_table()  # pylint: disable=protected-access
    diff_comp = table_down.item(0, 3)
    diff_sec = table_down.item(1, 3)

    _assert("— 0.00" in diff_comp.text(), f"Delta không đổi sai: {diff_comp.text()}")
    _assert(
        diff_comp.foreground().color().name().upper() == TEXT_MUTED.upper(),
        "Màu không đổi phải xám",
    )
    _assert("▼ -24.00" in diff_sec.text(), f"Delta giảm sai: {diff_sec.text()}")
    _assert(diff_sec.foreground().color().name().upper() == GRADE_F.upper(), "Màu giảm phải đỏ")

    print("    [OK] ComparisonDialog đối chiếu tiêu chí và tính toán độ lệch delta chuẩn xác")


def test_history_trend_canvas() -> None:
    """Kiểm thử khung vẽ biểu đồ xu hướng HistoryTrendCanvas."""
    print("[*] 3. Kiểm tra HistoryTrendCanvas...")
    canvas = HistoryTrendCanvas()

    # Dưới 2 phiên -> hiển thị thông điệp rỗng
    canvas.draw_trend([])
    _assert(len(canvas.ax.texts) > 0, "Dưới 2 phiên phải hiển thị văn bản thông báo")

    canvas.draw_trend([{"id": 1, "total_score": 50.0}])
    _assert(len(canvas.ax.texts) > 0, "1 phiên phải hiển thị thông báo nhẹ nhàng")

    # Đủ 5 phiên -> vẽ đường nối và 2 điểm nhãn
    sessions = _get_mock_history_sessions()
    canvas.draw_trend(sessions)

    lines = canvas.ax.get_lines()
    _assert(len(lines) == 1, "Phải vẽ đúng 1 đường xu hướng")
    _assert(len(lines[0].get_xdata()) == 5, "Đường xu hướng phải đi qua 5 điểm dữ liệu")
    _assert(canvas.ax.get_ylim()[1] >= 100, "Trục Y phải phủ đến 100")

    print("    [OK] HistoryTrendCanvas vẽ đường xu hướng và nhãn điểm số chuẩn xác")


def test_history_view() -> None:
    """Kiểm thử màn hình chính HistoryView và điều phối tương tác."""
    print("[*] 4. Kiểm tra HistoryView...")
    view = HistoryView()
    sessions = _get_mock_history_sessions()
    view.set_sessions(sessions)

    _assert(view.content_stack.currentIndex() == 0, "Có dữ liệu phải hiển thị bảng")
    _assert(view.table_view.model().rowCount() == 5, "Bảng phải hiển thị 5 dòng")
    _assert("Tổng số phiên: 5" in view.lbl_count.text(), "Nhãn tổng số phiên sai")

    # Ban đầu chưa chọn dòng nào: cả 3 nút đều bị vô hiệu
    _assert(view.btn_compare.isEnabled() is False, "Chưa chọn thì So sánh phải disabled")
    _assert(view.btn_view_issues.isEnabled() is False, "Chưa chọn thì Xem lỗi phải disabled")
    _assert(view.btn_delete.isEnabled() is False, "Chưa chọn thì Xóa phải disabled")

    # Chọn 1 dòng: Nút Xem lỗi & Xóa bật, Nút So sánh tắt
    view.table_view.selectRow(0)
    _APP.processEvents()

    _assert(view.btn_compare.isEnabled() is False, "1 dòng thì So sánh phải disabled")
    _assert(view.btn_view_issues.isEnabled() is True, "1 dòng thì Xem lỗi phải enabled")
    _assert(view.btn_delete.isEnabled() is True, "1 dòng thì Xóa phải enabled")

    # Kiểm tra phát tín hiệu open_session_issues khi bấm Xem chi tiết lỗi
    received_sid: list[int] = []
    view.open_session_issues.connect(received_sid.append)
    view.btn_view_issues.click()
    _APP.processEvents()

    _assert(len(received_sid) == 1 and received_sid[0] == 5, "Tín hiệu open_session_issues sai")

    # Chọn thêm 1 dòng nữa (thành 2 dòng): Nút So sánh bật
    mode = QItemSelectionModel.SelectionFlag.Select | QItemSelectionModel.SelectionFlag.Rows
    view.table_view.selectionModel().select(view.table_view.model().index(1, 0), mode)
    _APP.processEvents()

    _assert(view.btn_compare.isEnabled() is True, "2 dòng thì So sánh phải enabled")
    _assert(view.btn_view_issues.isEnabled() is False, "2 dòng thì Xem lỗi phải disabled")
    _assert(view.btn_delete.isEnabled() is True, "2 dòng thì Xóa phải enabled")

    # Kiểm tra trạng thái rỗng
    view.set_sessions([])
    _assert(view.content_stack.currentIndex() == 1, "0 phiên phải chuyển sang EmptyState")
    _assert("Tổng số phiên: 0" in view.lbl_count.text(), "Nhãn tổng số phiên rỗng sai")

    print("    [OK] HistoryView điều phối trạng thái nút, tín hiệu và EmptyState hoàn hảo")


def main() -> None:
    """Hàm chạy toàn bộ các bài kiểm thử Bước 4.4."""
    print("=" * 65)
    print("  KIỂM THỬ MÀN HÌNH LỊCH SỬ & SO SÁNH BƯỚC 4.4 (SKILLS.MD)  ")
    print("=" * 65)

    test_history_table_model()
    test_comparison_dialog()
    test_history_trend_canvas()
    test_history_view()

    print("=" * 65)
    print("  [PASSED] MÀN HÌNH LỊCH SỬ & SO SÁNH ĐÃ ĐẠT CHUẨN KỸ THUẬT 100%!  ")
    print("=" * 65)


if __name__ == "__main__":
    main()
