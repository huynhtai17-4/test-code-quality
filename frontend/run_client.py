"""
Tệp khởi chạy chính của ứng dụng Desktop GUI Client.
Khởi tạo QApplication, nạp QSS, cấu hình Matplotlib và mở MainWindow.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

# Đảm bảo đường dẫn import hoạt động khi chạy từ thư mục bất kỳ
ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# pylint: disable=no-name-in-module,wrong-import-position
from PyQt6.QtCore import qInstallMessageHandler
from PyQt6.QtWidgets import QApplication


def _qt_message_handler(_mode: Any, _context: Any, message: str) -> None:
    """Bộ lọc thông điệp Qt để loại bỏ các cảnh báo nội bộ không gây hại của Qt C++."""
    msg_str = str(message)
    if "setPointSize" in msg_str or "already owned by another" in msg_str:
        return
    sys.stderr.write(f"{msg_str}\n")
    sys.stderr.flush()


qInstallMessageHandler(_qt_message_handler)

from frontend.charts.style import apply_chart_style
from frontend.main_window import MainWindow
from frontend.views import theme


def main() -> None:
    """Khởi tạo toàn bộ môi trường và khởi chạy ứng dụng GUI."""
    app = QApplication(sys.argv)
    app.setOrganizationName("CodeQualityAnalyzer")
    app.setApplicationName("DesktopClient")

    # Nạp và kích hoạt phông chữ kỹ thuật Geist Mono toàn cục
    theme.init_app_fonts(app)

    # Nạp stylesheet hệ thống phẳng
    stylesheet = theme.load_stylesheet()
    if stylesheet:
        app.setStyleSheet(stylesheet)

    # Nạp cấu hình đồ thị phẳng của Matplotlib
    apply_chart_style()

    # Khởi tạo và hiển thị cửa sổ chính
    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
