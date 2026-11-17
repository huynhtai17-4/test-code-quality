"""Component hiển thị tiến trình đang quét động thời gian thực (AnalysisScanningBlock)."""

from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal  # pylint: disable=no-name-in-module
from PyQt6.QtWidgets import (  # pylint: disable=no-name-in-module
    QFrame,
    QLabel,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from frontend.views.theme import (
    BORDER_SOFT,
    SURFACE,
    SURFACE_ALT,
    TEXT_MAIN,
)


class AnalysisScanningBlock(QFrame):
    """Khối hiển thị thanh tiến độ phần trăm và nhãn mô tả các bước quét."""

    cancel_requested = pyqtSignal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setStyleSheet(
            f"QFrame {{ background-color: {SURFACE};"
            f" border: 1px solid {BORDER_SOFT}; border-radius: 4px; }}"
        )

        self._lbl_scanning_step = QLabel("Đang chuẩn bị phiên quét...", self)
        self._progress_bar = QProgressBar(self)
        self._btn_cancel_scan = QPushButton("Hủy phân tích", self)

        self._init_ui()

    def _init_ui(self) -> None:
        """Khởi tạo bố cục khối đang quét."""
        v_layout = QVBoxLayout(self)
        v_layout.setContentsMargins(32, 24, 32, 24)
        v_layout.setSpacing(12)
        v_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        lbl_scan_tag = QLabel("ĐANG TIẾN HÀNH KIỂM ĐỊNH MÃ NGUỒN", self)
        lbl_scan_tag.setStyleSheet("color: #1F5FA8; font-weight: 600; font-size: 12px;")

        self._lbl_scanning_step.setStyleSheet(
            f"color: {TEXT_MAIN}; font-size: 14px; font-weight: 500;"
        )

        self._progress_bar.setRange(0, 100)
        self._progress_bar.setValue(0)
        self._progress_bar.setFixedHeight(8)
        self._progress_bar.setTextVisible(False)
        self._progress_bar.setStyleSheet(
            f"QProgressBar {{ background-color: {SURFACE_ALT}; border: none; border-radius: 4px; }}"
            f"QProgressBar::chunk {{ background-color: #1F5FA8; border-radius: 4px; }}"
        )

        self._btn_cancel_scan.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_cancel_scan.clicked.connect(self.cancel_requested.emit)

        v_layout.addWidget(lbl_scan_tag, alignment=Qt.AlignmentFlag.AlignCenter)
        v_layout.addWidget(self._lbl_scanning_step, alignment=Qt.AlignmentFlag.AlignCenter)
        v_layout.addWidget(self._progress_bar)
        v_layout.addWidget(self._btn_cancel_scan, alignment=Qt.AlignmentFlag.AlignCenter)

    def set_progress(self, msg: str, pct: int) -> None:
        """Cập nhật thông điệp và tỷ lệ phần trăm quét hiện tại."""
        self._lbl_scanning_step.setText(msg)
        self._progress_bar.setValue(pct)

    def reset(self) -> None:
        """Đặt lại giá trị tiến độ về trạng thái ban đầu."""
        self._progress_bar.setValue(0)
        self._lbl_scanning_step.setText("Đang chuẩn bị phiên quét...")
