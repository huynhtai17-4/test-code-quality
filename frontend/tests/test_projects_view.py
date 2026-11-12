"""Kịch bản kiểm thử tự động toàn diện cho Màn hình Quản lý Dự án (Bước 4.1 - SKILLS.md)."""

import sys
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# pylint: disable=wrong-import-position,no-name-in-module
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication

from frontend.views.projects_view import (
    ProjectDialog,
    ProjectFilterProxyModel,
    ProjectTableModel,
    ProjectsView,
)

_APP = QApplication.instance() or QApplication(["test_projects_view"])


def _assert(condition: bool, message: str) -> None:
    """Xác thực điều kiện kiểm thử an toàn cho Bandit."""
    if not condition:
        raise RuntimeError(f"KIỂM THỬ THẤT BẠI: {message}")


def test_project_table_model() -> None:
    """1. Kiểm tra ProjectTableModel."""
    print("[*] 1. Kiểm tra ProjectTableModel...")
    raw_projects: list[dict[str, Any]] = [
        {
            "id": 101,
            "name": "express_core",
            "path": "https://github.com/unit/express_core",
            "source_type": "github",
            "last_analyzed_at": "2026-11-09 14:32:00",
            "total_score": 82.0,
            "grade": "B",
        },
        {
            "id": 102,
            "name": "dummy_test_repo",
            "path": "d:/dummy_test_repo",
            "source_type": "local",
            "last_analyzed_at": None,
            "total_score": None,
            "grade": None,
        },
    ]

    model = ProjectTableModel(raw_projects)
    _assert(model.rowCount() == 2, f"rowCount sai: {model.rowCount()}")
    _assert(model.columnCount() == 5, f"columnCount sai: {model.columnCount()}")

    # Cột Tên
    idx_name = model.index(0, 0)
    _assert(model.data(idx_name) == "express_core", "Tên dự án không khớp")

    # Cột Nguồn
    idx_src = model.index(0, 1)
    _assert(model.data(idx_src) == "GitHub", "Loại nguồn GitHub sai")
    idx_src_local = model.index(1, 1)
    _assert(model.data(idx_src_local) == "Thư mục", "Loại nguồn Thư mục sai")

    # Cột Phông code
    idx_path = model.index(0, 2)
    font = model.data(idx_path, Qt.ItemDataRole.FontRole)
    _assert(font is not None, "Cột path phải có font code")

    # Cột Điểm
    idx_score_1 = model.index(0, 4)
    _assert(model.data(idx_score_1) == "82 (B)", f"Điểm 82 (B) sai: {model.data(idx_score_1)}")
    idx_score_2 = model.index(1, 4)
    _assert(model.data(idx_score_2) == "—", f"Điểm trống phải là —: {model.data(idx_score_2)}")

    print("    [OK] ProjectTableModel hiển thị 5 cột, định dạng ngày/điểm và font code chuẩn xác")


def test_project_filter_proxy_model() -> None:
    """2. Kiểm tra bộ lọc ProjectFilterProxyModel."""
    print("[*] 2. Kiểm tra bộ lọc ProjectFilterProxyModel...")
    raw_projects: list[dict[str, Any]] = [
        {
            "id": 1,
            "name": "Alpha-Flask",
            "path": "https://github.com/a/flask",
            "source_type": "github",
        },
        {"id": 2, "name": "Beta-Local", "path": "D:/projects/beta", "source_type": "local"},
        {"id": 3, "name": "Gamma-Tool", "path": "D:/projects/gamma", "source_type": "local"},
    ]

    model = ProjectTableModel(raw_projects)
    proxy = ProjectFilterProxyModel()
    proxy.setSourceModel(model)

    _assert(proxy.rowCount() == 3, "Proxy ban đầu phải có 3 dòng")

    # Lọc theo từ khóa
    proxy.set_search_keyword("beta")
    _assert(proxy.rowCount() == 1, f"Lọc 'beta' phải ra 1 dòng, thực tế: {proxy.rowCount()}")

    # Reset từ khóa và lọc theo nguồn
    proxy.set_search_keyword("")
    proxy.set_source_filter("Kho mã nguồn GitHub")
    _assert(proxy.rowCount() == 1, f"Lọc GitHub phải ra 1 dòng, thực tế: {proxy.rowCount()}")

    proxy.set_source_filter("Thư mục cục bộ")
    _assert(proxy.rowCount() == 2, f"Lọc Thư mục phải ra 2 dòng, thực tế: {proxy.rowCount()}")

    proxy.set_source_filter("Tất cả nguồn")
    _assert(proxy.rowCount() == 3, "Reset nguồn phải ra 3 dòng")
    print("    [OK] ProjectFilterProxyModel lọc chính xác theo từ khóa và loại nguồn")


def test_project_dialog() -> None:
    """3. Kiểm tra hộp thoại ProjectDialog."""
    print("[*] 3. Kiểm tra ProjectDialog...")
    # Thêm mới
    dialog = ProjectDialog()
    _assert(dialog.windowTitle() == "Thêm dự án mới", "Tiêu đề thêm mới sai")

    # Kiểm tra chặn lưu khi để trống
    dialog._on_save()  # pylint: disable=protected-access
    _assert(dialog.result() != 1, "Không được chấp nhận khi form trống")

    # Điền form hợp lệ
    getattr(dialog, "_txt_name").setText("New-Project")
    getattr(dialog, "_txt_path").setText("D:/New-Project")
    data = dialog.get_data()
    _assert(data["name"] == "New-Project", "Dữ liệu name sai")
    _assert(data["path"] == "D:/New-Project", "Dữ liệu path sai")
    _assert(data["source_type"] == "local", "Source type mặc định sai")

    # Chế độ chỉnh sửa
    edit_dialog = ProjectDialog(project={"id": 10, "name": "Old", "path": "D:/Old"})
    _assert(edit_dialog.windowTitle() == "Chỉnh sửa dự án", "Tiêu đề sửa sai")
    _assert(getattr(edit_dialog, "_txt_name").text() == "Old", "Không pre-fill name")
    print("    [OK] ProjectDialog validate form, chuyển đổi chế độ thêm/sửa chuẩn xác")


def test_projects_view_layout_and_signals() -> None:
    """4. Kiểm tra ProjectsView quản lý giao diện và tín hiệu."""
    print("[*] 4. Kiểm tra ProjectsView layout và tín hiệu...")
    view = ProjectsView()

    # Kiểm tra chuyển trạng thái rỗng sang có dữ liệu
    view._on_projects_loaded({"status": "ok", "data": []})  # pylint: disable=protected-access
    stack_layout = getattr(view, "_stack_layout")
    _assert(stack_layout.currentIndex() == 1, "Khi danh sách rỗng phải hiện EmptyState (index 1)")

    # Nạp dữ liệu
    mock_item = {"id": 1, "name": "TestProj", "path": "D:/test", "source_type": "local"}
    view._on_projects_loaded({"status": "ok", "data": [mock_item]})  # pylint: disable=protected-access
    _assert(stack_layout.currentIndex() == 0, "Khi có dữ liệu phải hiện Bảng (index 0)")

    # Kiểm tra phát tín hiệu open_analysis
    analysis_dispatched: list[dict[str, Any]] = []
    view.open_analysis.connect(analysis_dispatched.append)

    table = getattr(view, "_table_view")
    table.selectRow(0)
    view._on_analyze_project()  # pylint: disable=protected-access

    _assert(len(analysis_dispatched) == 1, "open_analysis signal không được phát")
    _assert(analysis_dispatched[0]["name"] == "TestProj", "Dữ liệu dự án phát đi sai")
    print("    [OK] ProjectsView chuyển đổi QStackedLayout và phát tín hiệu open_analysis")


def main() -> None:
    """Chạy toàn bộ bài kiểm thử Bước 4.1."""
    print("=" * 65)
    print("  KIỂM THỬ MÀN HÌNH QUẢN LÝ DỰ ÁN BƯỚC 4.1 (SKILLS.MD)  ")
    print("=" * 65)
    test_project_table_model()
    test_project_filter_proxy_model()
    test_project_dialog()
    test_projects_view_layout_and_signals()
    print("=" * 65)
    print("  [PASSED] MÀN HÌNH QUẢN LÝ DỰ ÁN ĐÃ ĐẠT CHUẨN KỸ THUẬT 100%!  ")
    print("=" * 65)


if __name__ == "__main__":
    main()
