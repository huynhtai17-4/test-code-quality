"""Component giao diện Tab Tổng quan chỉ số kiểm định (AnalysisOverviewTab)."""

from __future__ import annotations

from typing import Any

from PyQt6.QtCore import Qt, pyqtSignal  # pylint: disable=no-name-in-module
from PyQt6.QtWidgets import (  # pylint: disable=no-name-in-module
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from frontend.views.theme import (
    BORDER_SOFT,
    SURFACE,
    TEXT_MAIN,
    TEXT_MUTED,
)
from frontend.views.widgets.severity_badge import SeverityBadge


# pylint: disable=too-many-instance-attributes
class AnalysisOverviewTab(QWidget):
    """Tab 1: Hiển thị 4 mức độ nghiêm trọng và 3 chỉ số tổng quan tệp tin/dòng mã/lỗi."""

    jump_to_issues_requested = pyqtSignal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self._lbl_crit_cnt = QLabel("0", self)
        self._lbl_high_cnt = QLabel("0", self)
        self._lbl_med_cnt = QLabel("0", self)
        self._lbl_low_cnt = QLabel("0", self)

        self._lbl_files = QLabel("—", self)
        self._lbl_loc = QLabel("—", self)
        self._lbl_issues = QLabel("—", self)

        self._init_ui()

    def _init_ui(self) -> None:
        """Khởi tạo bố cục các thẻ mức độ lỗi và hàng thống kê."""
        v_layout = QVBoxLayout(self)
        v_layout.setContentsMargins(16, 16, 16, 16)
        v_layout.setSpacing(16)

        v_layout.addLayout(self._create_severity_row())
        v_layout.addLayout(self._create_metrics_row())

        jump_bar = QHBoxLayout()
        jump_bar.addStretch()
        btn_jump = QPushButton("Xem toàn bộ danh sách lỗi trong bảng Issues →", self)
        btn_jump.setProperty("role", "primary")
        btn_jump.setFixedHeight(34)
        btn_jump.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_jump.clicked.connect(self.jump_to_issues_requested.emit)
        jump_bar.addWidget(btn_jump)
        v_layout.addLayout(jump_bar)
        v_layout.addStretch()

    def _create_severity_row(self) -> QHBoxLayout:
        """Tạo hàng 4 thẻ mức độ lỗi."""
        sev_row = QHBoxLayout()
        sev_row.setSpacing(14)

        levels = (
            ("Critical", self._lbl_crit_cnt),
            ("High", self._lbl_high_cnt),
            ("Medium", self._lbl_med_cnt),
            ("Low", self._lbl_low_cnt),
        )
        for lvl, lbl_w in levels:
            cell = QFrame(self)
            cell.setObjectName("StatCard")
            cell.setStyleSheet(
                f"QFrame#StatCard {{ background-color: {SURFACE};"
                f" border: 1px solid {BORDER_SOFT}; border-radius: 6px; }}"
                f"QLabel {{ border: none; background: transparent; }}"
            )
            c_layout = QVBoxLayout(cell)
            c_layout.setContentsMargins(14, 12, 14, 12)
            c_layout.setSpacing(8)
            c_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

            badge = SeverityBadge(lvl, show_vietnamese=True, parent=cell)
            lbl_w.setStyleSheet(
                f"font-size: 24px; font-weight: bold; color: {TEXT_MAIN};"
                f" border: none; background: transparent;"
            )

            c_layout.addWidget(badge)
            c_layout.addWidget(lbl_w)
            sev_row.addWidget(cell)
        return sev_row

    def _create_metrics_row(self) -> QHBoxLayout:
        """Tạo hàng thống kê số lượng file, LOC và tổng lỗi."""
        info_row = QHBoxLayout()
        info_row.setSpacing(14)

        metrics = (
            ("Tổng số tệp tin", self._lbl_files),
            ("Tổng số dòng mã", self._lbl_loc),
            ("Tổng số lỗi phát hiện", self._lbl_issues),
        )
        for title, val_lbl in metrics:
            item_box = QFrame(self)
            item_box.setObjectName("StatCard")
            item_box.setStyleSheet(
                f"QFrame#StatCard {{ background-color: {SURFACE};"
                f" border: 1px solid {BORDER_SOFT}; border-radius: 6px; }}"
                f"QLabel {{ border: none; background: transparent; }}"
            )
            i_layout = QVBoxLayout(item_box)
            i_layout.setContentsMargins(16, 12, 16, 12)
            i_layout.setSpacing(6)

            lbl_t = QLabel(title, item_box)
            lbl_t.setStyleSheet(
                f"color: {TEXT_MUTED}; font-size: 12px; font-weight: 500;"
                f" border: none; background: transparent;"
            )
            val_lbl.setStyleSheet(
                f"font-size: 24px; font-weight: bold; color: {TEXT_MAIN};"
                f" border: none; background: transparent;"
            )

            i_layout.addWidget(lbl_t)
            i_layout.addWidget(val_lbl)
            info_row.addWidget(item_box)
        return info_row

    def update_severity_labels(self, sev_dist: dict[str, int]) -> None:
        """Cập nhật số lượng lỗi cho 4 mức độ Critical, High, Medium, Low."""
        self._lbl_crit_cnt.setText(str(sev_dist.get("Critical", 0)))
        self._lbl_high_cnt.setText(str(sev_dist.get("High", 0)))
        self._lbl_med_cnt.setText(str(sev_dist.get("Medium", 0)))
        self._lbl_low_cnt.setText(str(sev_dist.get("Low", 0)))

    def update_overview_counts(
        self,
        files_count: Any,
        total_loc: Any,
        total_issues: Any,
    ) -> None:
        """Cập nhật các nhãn số lượng tệp tin, dòng mã và tổng số lỗi."""
        self._lbl_files.setText(str(files_count) if files_count is not None else "—")
        self._lbl_loc.setText(str(total_loc) if total_loc is not None else "—")
        self._lbl_issues.setText(str(total_issues) if total_issues is not None else "0")

    def get_display_stats(self) -> tuple[str, str, str]:
        """Lấy giá trị chuỗi hiển thị tệp tin, LOC và tổng lỗi."""
        return self._lbl_files.text(), self._lbl_loc.text(), self._lbl_issues.text()
