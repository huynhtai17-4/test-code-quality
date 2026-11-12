"""
Kiểm thử tích hợp cho Cửa sổ chính (MainWindow) trong môi trường headless.
Kiểm tra cấu trúc giao diện, đồng bộ thanh điều hướng, liên kết luồng tín hiệu và phím tắt.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# Đảm bảo Qt chạy ở chế độ offscreen không cần màn hình hiển thị
os.environ["QT_QPA_PLATFORM"] = "offscreen"

# pylint: disable=wrong-import-position,no-name-in-module
import pytest
from PyQt6.QtCore import QSettings
from PyQt6.QtWidgets import QApplication

from frontend import config
from frontend.main_window import MainWindow
from frontend.views.analysis_view import AnalysisView
from frontend.views.history_view import HistoryView
from frontend.views.issues_view import IssuesView
from frontend.views.projects_view import ProjectsView
from frontend.views.settings_view import SettingsView
from frontend.workers.request_worker import RequestWorker

_APP = QApplication.instance() or QApplication(["test_main_window"])


@pytest.fixture(autouse=True)
def _patch_background_ping():
    """Ngăn luồng mạng ping nền tự động trong quá trình chạy headless test."""
    with patch.object(RequestWorker, "start", lambda _self: None):
        yield


def _assert(condition: bool, message: str) -> None:
    """Hàm xác thực điều kiện kiểm thử an toàn cho Bandit."""
    if not condition:
        raise RuntimeError(f"KIỂM THỬ THẤT BẠI: {message}")


def test_main_window_initialization() -> None:
    """Kiểm tra khởi tạo MainWindow với đầy đủ thuộc tính kích thước và view."""
    window = MainWindow()
    try:
        _assert(
            window.windowTitle()
            == "Hệ thống phân tích và đánh giá chất lượng mã nguồn mở",
            "Tiêu đề cửa sổ chính không đúng quy chuẩn SKILLS.md.",
        )
        _assert(
            window.minimumWidth() == 1100 and window.minimumHeight() == 680,
            "Kích thước tối thiểu không đạt 1100x680.",
        )
        _assert(
            window.width() >= 1100 and window.height() >= 680,
            "Kích thước cửa sổ nhỏ hơn giới hạn tối thiểu.",
        )
        _assert(
            window.sidebar is not None and window.sidebar.width() == 188,
            "Chiều rộng Sidebar phải cố định 188px.",
        )
        _assert(
            window.stack is not None and window.stack.count() == 5,
            "QStackedWidget phải chứa 5 view.",
        )
        _assert(
            isinstance(window.stack.widget(0), ProjectsView),
            "View 0 phải là ProjectsView.",
        )
        _assert(
            isinstance(window.stack.widget(1), AnalysisView),
            "View 1 phải là AnalysisView.",
        )
        _assert(
            isinstance(window.stack.widget(2), IssuesView),
            "View 2 phải là IssuesView.",
        )
        _assert(
            isinstance(window.stack.widget(3), HistoryView),
            "View 3 phải là HistoryView.",
        )
        _assert(
            isinstance(window.stack.widget(4), SettingsView),
            "View 4 phải là SettingsView.",
        )

        _assert(window.stack.currentIndex() == 0, "Trang mặc định ban đầu phải là index 0.")
        _assert(
            window.btn_projects is not None and window.btn_projects.isChecked(),
            "Nút Dự án trên Sidebar phải được kích hoạt mặc định.",
        )
        _assert(
            window.lbl_current_project is not None
            and "Chưa chọn" in window.lbl_current_project.text(),
            "Nhãn dự án ban đầu phải hiển thị Chưa chọn.",
        )
    finally:
        window.close()


def test_tab_switching() -> None:
    """Kiểm tra việc chuyển đổi giữa các tab qua phương thức switch_tab."""
    window = MainWindow()
    try:
        # Chuyển sang Phân tích (index 1)
        window.switch_tab(1)
        _assert(window.stack.currentIndex() == 1, "Stack index phải chuyển sang 1.")
        _assert(
            window.btn_analysis is not None and window.btn_analysis.isChecked(),
            "Nút Phân tích phải được chọn khi chuyển sang index 1.",
        )

        # Chuyển sang Lỗi phát hiện (index 2)
        window.switch_tab(2)
        _assert(window.stack.currentIndex() == 2, "Stack index phải chuyển sang 2.")
        _assert(
            window.btn_issues is not None and window.btn_issues.isChecked(),
            "Nút Lỗi phát hiện phải được chọn khi chuyển sang index 2.",
        )

        # Chuyển sang Lịch sử quét (index 3)
        window.switch_tab(3)
        _assert(window.stack.currentIndex() == 3, "Stack index phải chuyển sang 3.")
        _assert(
            window.btn_history is not None and window.btn_history.isChecked(),
            "Nút Lịch sử quét phải được chọn khi chuyển sang index 3.",
        )

        # Chuyển sang Cài đặt (index 4)
        window.switch_tab(4)
        _assert(window.stack.currentIndex() == 4, "Stack index phải chuyển sang 4.")
        _assert(
            window.btn_settings is not None and window.btn_settings.isChecked(),
            "Nút Cài đặt phải được chọn khi chuyển sang index 4.",
        )

        # Quay lại Dự án (index 0)
        window.switch_tab(0)
        _assert(window.stack.currentIndex() == 0, "Stack index phải quay về 0.")
        _assert(
            window.btn_projects is not None and window.btn_projects.isChecked(),
            "Nút Dự án phải được chọn khi quay về index 0.",
        )

        # Kiểm tra index ngoài phạm vi hợp lệ
        window.switch_tab(99)
        _assert(window.stack.currentIndex() == 0, "Index ngoài phạm vi không được đổi tab.")
    finally:
        window.close()


def test_sidebar_buttons_click() -> None:
    """Kiểm tra bấm nút trên Sidebar kích hoạt đúng tab tương ứng."""
    window = MainWindow()
    try:
        _assert(window.btn_analysis is not None, "btn_analysis không được rỗng.")
        window.btn_analysis.click()
        _APP.processEvents()
        _assert(window.stack.currentIndex() == 1, "Click btn_analysis phải chuyển sang tab 1.")

        _assert(window.btn_settings is not None, "btn_settings không được rỗng.")
        window.btn_settings.click()
        _APP.processEvents()
        _assert(window.stack.currentIndex() == 4, "Click btn_settings phải chuyển sang tab 4.")
    finally:
        window.close()


def test_signal_wiring_projects_to_analysis() -> None:
    """Kiểm tra tín hiệu open_analysis từ ProjectsView chuyển tab và nạp dự án sang AnalysisView."""
    window = MainWindow()
    try:
        dummy_project = {
            "id": 99,
            "name": "DuAnMau_Testing",
            "source_type": "local",
            "source_path": "D:/Projects/Sample",
        }

        _assert(window.projects_view is not None, "projects_view không được rỗng.")
        window.projects_view.open_analysis.emit(dummy_project)
        _APP.processEvents()

        _assert(
            window.current_project == dummy_project,
            "current_project của MainWindow không được cập nhật đúng.",
        )
        _assert(
            window.lbl_current_project is not None
            and "DuAnMau_Testing" in window.lbl_current_project.text(),
            "Nhãn trạng thái không hiển thị đúng tên dự án.",
        )
        _assert(
            window.stack is not None and window.stack.currentIndex() == 1,
            "Không tự động chuyển sang tab Phân tích (index 1).",
        )
        _assert(
            window.btn_analysis is not None and window.btn_analysis.isChecked(),
            "Nút Phân tích trên Sidebar chưa được đánh dấu chọn.",
        )
        # pylint: disable=protected-access
        _assert(
            window.analysis_view is not None and window.analysis_view._project_id == 99,
            "AnalysisView chưa nhận đúng ID dự án.",
        )
    finally:
        window.close()


def test_signal_wiring_analysis_and_history_to_issues() -> None:
    """Kiểm tra tín hiệu chuyển trang xem lỗi từ AnalysisView và HistoryView."""
    window = MainWindow()
    try:
        # 1. Từ AnalysisView -> IssuesView
        _assert(window.analysis_view is not None, "analysis_view không được rỗng.")
        window.analysis_view.switch_to_issues.emit(42)
        _APP.processEvents()

        _assert(
            window.stack is not None and window.stack.currentIndex() == 2,
            "Không chuyển sang tab Lỗi (index 2) từ AnalysisView.",
        )
        _assert(
            window.btn_issues is not None and window.btn_issues.isChecked(),
            "Nút Lỗi phát hiện chưa được chọn trên Sidebar.",
        )
        # pylint: disable=protected-access
        _assert(
            window.issues_view is not None and window.issues_view._session_id == 42,
            "IssuesView chưa nạp đúng session_id 42 từ AnalysisView.",
        )

        # 2. Từ HistoryView -> IssuesView
        _assert(window.history_view is not None, "history_view không được rỗng.")
        window.history_view.open_session_issues.emit(88)
        _APP.processEvents()

        _assert(
            window.stack is not None and window.stack.currentIndex() == 2,
            "Không chuyển sang tab Lỗi (index 2) từ HistoryView.",
        )
        # pylint: disable=protected-access
        _assert(
            window.issues_view is not None and window.issues_view._session_id == 88,
            "IssuesView chưa nạp đúng session_id 88 từ HistoryView.",
        )
    finally:
        window.close()


def test_status_message_forwarding() -> None:
    """Kiểm tra tín hiệu status_message từ các view con được đẩy lên QStatusBar."""
    window = MainWindow()
    try:
        _assert(window.projects_view is not None, "projects_view không được rỗng.")
        test_msg_1 = "Đã tải danh sách dự án thành công."
        window.projects_view.status_message.emit(test_msg_1)
        _APP.processEvents()
        _assert(
            window.statusBar().currentMessage() == test_msg_1,
            "Thanh trạng thái không hiển thị đúng thông báo từ ProjectsView.",
        )

        _assert(window.settings_view is not None, "settings_view không được rỗng.")
        test_msg_2 = "Cài đặt trọng số hoàn tất."
        window.settings_view.status_message.emit(test_msg_2)
        _APP.processEvents()
        _assert(
            window.statusBar().currentMessage() == test_msg_2,
            "Thanh trạng thái không hiển thị đúng thông báo từ SettingsView.",
        )
    finally:
        window.close()


def test_connection_status_updating() -> None:
    """Kiểm tra hàm update_connection_status cập nhật đúng giao diện nhãn kết nối."""
    window = MainWindow()
    try:
        _assert(window.lbl_connection is not None, "lbl_connection không được rỗng.")
        # Giả lập kết nối thành công
        window.update_connection_status(True)
        _assert(
            "Đã kết nối" in window.lbl_connection.text(),
            "Nhãn không hiển thị trạng thái Đã kết nối.",
        )
        _assert(
            f"{config.SERVER_HOST}:{config.SERVER_PORT}" in window.lbl_connection.text(),
            "Nhãn không chứa đúng địa chỉ host:port cấu hình.",
        )

        # Giả lập mất kết nối
        window.update_connection_status(False)
        _assert(
            "Mất kết nối" in window.lbl_connection.text(),
            "Nhãn không hiển thị trạng thái Mất kết nối máy chủ.",
        )

        # Giả lập kết quả ping khi server offline: {"status": "ok", "data": False}
        window.check_server_connection()
        # pylint: disable=protected-access
        if hasattr(window, "_ping_worker") and window._ping_worker:
            window._ping_worker.finished.emit({"status": "ok", "data": False})
            _assert(
                "Mất kết nối" in window.lbl_connection.text(),
                "Khi data=False nhãn phải hiển thị Mất kết nối máy chủ.",
            )
            # Phát tín hiệu finished với {"status": "ok", "data": True}
            window._ping_worker.finished.emit({"status": "ok", "data": True})
            _assert(
                "Đã kết nối" in window.lbl_connection.text(),
                "Khi data=True nhãn phải hiển thị Đã kết nối.",
            )
    finally:
        window.close()


def test_shortcuts_and_refresh() -> None:
    """Kiểm tra gọi hàm làm mới dữ liệu và phím tắt tạo dự án mới."""
    window = MainWindow()
    try:
        _assert(window.projects_view is not None, "projects_view không được rỗng.")
        _assert(window.settings_view is not None, "settings_view không được rỗng.")

        # Giả lập mock phương thức làm mới của các view
        window.projects_view.load_projects = MagicMock()
        window.settings_view.load_current_configs = MagicMock()

        # Làm mới khi đang ở tab 0 (Dự án)
        window.switch_tab(0)
        window.refresh_current_view()
        window.projects_view.load_projects.assert_called_once()

        # Làm mới khi đang ở tab 4 (Cài đặt)
        window.switch_tab(4)
        window.refresh_current_view()
        window.settings_view.load_current_configs.assert_called_once()

        # Phím tắt Ctrl+N kích hoạt _on_add_project
        # pylint: disable=protected-access
        window.projects_view._on_add_project = MagicMock()
        window._on_shortcut_new_project()
        _assert(
            window.stack is not None and window.stack.currentIndex() == 0,
            "Ctrl+N phải chuyển về tab Dự án.",
        )
        window.projects_view._on_add_project.assert_called_once()
    finally:
        window.close()


def test_window_geometry_persistence() -> None:
    """Kiểm tra cơ chế lưu và khôi phục geometry qua QSettings."""
    window = MainWindow()
    try:
        window.resize(1300, 800)
        window.close()

        settings = QSettings("CodeQualityAnalyzer", "DesktopGUI")
        saved_geo = settings.value("geometry")
        _assert(saved_geo is not None, "Geometry không được lưu vào QSettings khi đóng cửa sổ.")
    finally:
        window.close()


def main() -> None:
    """Hàm chạy toàn bộ các bài kiểm thử tích hợp MainWindow."""
    # Chặn toàn bộ luồng mạng TCP nền trong quá trình chạy kiểm thử giao diện
    with patch.object(RequestWorker, "start", lambda _self: None):
        print("=== BẮT ĐẦU KIỂM THỬ TÍCH HỢP MAIN WINDOW (PyQt6 Headless) ===")
        test_main_window_initialization()
        print("  ✓ test_main_window_initialization hoàn thành.")

        test_tab_switching()
        print("  ✓ test_tab_switching hoàn thành.")

        test_sidebar_buttons_click()
        print("  ✓ test_sidebar_buttons_click hoàn thành.")

        test_signal_wiring_projects_to_analysis()
        print("  ✓ test_signal_wiring_projects_to_analysis hoàn thành.")

        test_signal_wiring_analysis_and_history_to_issues()
        print("  ✓ test_signal_wiring_analysis_and_history_to_issues hoàn thành.")

        test_status_message_forwarding()
        print("  ✓ test_status_message_forwarding hoàn thành.")

        test_connection_status_updating()
        print("  ✓ test_connection_status_updating hoàn thành.")

        test_shortcuts_and_refresh()
        print("  ✓ test_shortcuts_and_refresh hoàn thành.")

        test_window_geometry_persistence()
        print("  ✓ test_window_geometry_persistence hoàn thành.")

        print("\n>>> TẤT CẢ CÁC BÀI KIỂM THỬ MAIN WINDOW ĐÃ ĐẠT 100%! <<<")


if __name__ == "__main__":
    main()
