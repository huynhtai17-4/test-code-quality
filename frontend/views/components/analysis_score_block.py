"""Component hiển thị khối điểm số tổng quan và 6 tiêu chí kiểm định (AnalysisScoreBlock)."""

from __future__ import annotations

from PyQt6.QtCore import Qt  # pylint: disable=no-name-in-module
from PyQt6.QtWidgets import (  # pylint: disable=no-name-in-module
    QFrame,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from frontend.reports.report_generator import (
    _get_grade_for_score,
    _get_score_color,
)
from frontend.views.theme import (
    BORDER_SOFT,
    SURFACE,
    TEXT_MAIN,
    TEXT_MUTED,
    lay_font_code,
)
from frontend.views.widgets.grade_label import GradeLabel
from frontend.views.widgets.score_bar import ScoreBar

_CRITERIA_KEYS = (
    "complexity",
    "security",
    "pylint",
    "health",
    "dependency",
    "malware",
)


# pylint: disable=too-few-public-methods
class AnalysisScoreBlock(QFrame):
    """Khối hiển thị xếp loại chữ cái, điểm số tổng, 2 thẻ chỉ số và 6 thanh tiêu chí."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setStyleSheet(
            f"QFrame {{ background-color: {SURFACE};"
            f" border: 1px solid {BORDER_SOFT}; border-radius: 6px; }}"
        )

        self._grade_label = GradeLabel("A", 100.0, self)
        self._lbl_quality_val: QLabel | None = None
        self._lbl_security_val: QLabel | None = None
        self._score_bars: dict[str, ScoreBar] = {}

        self._init_ui()

    def _init_ui(self) -> None:
        """Khởi tạo bố cục 3 cột: Xếp loại, 2 Thẻ chỉ số và 6 Thanh tiêu chí."""
        h_layout = QHBoxLayout(self)
        h_layout.setContentsMargins(20, 16, 20, 16)
        h_layout.setSpacing(20)

        # Cột 1: GradeLabel
        left_col = QWidget(self)
        left_col.setFixedWidth(200)
        left_layout = QVBoxLayout(left_col)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.addWidget(self._grade_label, alignment=Qt.AlignmentFlag.AlignCenter)
        h_layout.addWidget(left_col)

        # Cột 2: Chất lượng Code & An toàn Bảo mật
        dual_col = QWidget(self)
        dual_col.setFixedWidth(240)
        dual_layout = QVBoxLayout(dual_col)
        dual_layout.setContentsMargins(0, 0, 0, 0)
        dual_layout.setSpacing(10)

        card_qual, self._lbl_quality_val = self._create_flat_card(
            "Chất lượng Code",
            "Cấu trúc, PEP8, độ phức tạp",
            dual_col,
        )
        card_sec, self._lbl_security_val = self._create_flat_card(
            "An toàn Bảo mật",
            "SAST, CVE, hành vi mã độc",
            dual_col,
        )
        dual_layout.addWidget(card_qual)
        dual_layout.addWidget(card_sec)
        h_layout.addWidget(dual_col)

        # Đường phân cách dọc
        v_line = QFrame(self)
        v_line.setFixedWidth(1)
        v_line.setStyleSheet(f"background-color: {BORDER_SOFT}; border: none;")
        h_layout.addWidget(v_line)

        # Cột 3: 6 thanh tiêu chí ScoreBar
        right_col = QWidget(self)
        right_layout = QVBoxLayout(right_col)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(8)

        for key in _CRITERIA_KEYS:
            score_bar = ScoreBar(key, score=0.0, parent=right_col)
            self._score_bars[key] = score_bar
            right_layout.addWidget(score_bar)

        h_layout.addWidget(right_col, stretch=1)

    @staticmethod
    def _create_flat_card(
        title: str,
        subtitle: str,
        parent: QWidget,
    ) -> tuple[QFrame, QLabel]:
        """Tạo thẻ chỉ số phẳng nền SURFACE, viền BORDER_SOFT, bo góc 6px."""
        card = QFrame(parent)
        card.setStyleSheet(
            f"QFrame {{ background-color: {SURFACE}; border: 1px solid {BORDER_SOFT}; "
            f"border-radius: 6px; }} QLabel {{ border: none; background: transparent; }}"
        )
        vbox = QVBoxLayout(card)
        vbox.setContentsMargins(12, 8, 12, 8)
        vbox.setSpacing(2)

        lbl_title = QLabel(title, card)
        lbl_title.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 11px; font-weight: 600;")

        lbl_score = QLabel("— / 100", card)
        lbl_score.setFont(lay_font_code(14))
        lbl_score.setStyleSheet(f"color: {TEXT_MAIN}; font-weight: bold;")

        lbl_sub = QLabel(subtitle, card)
        lbl_sub.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 10px;")

        vbox.addWidget(lbl_title)
        vbox.addWidget(lbl_score)
        vbox.addWidget(lbl_sub)
        return card, lbl_score

    @staticmethod
    def _set_metric_label(label: QLabel | None, score: float) -> None:
        """Cập nhật giá trị hiển thị và màu sắc cho thẻ chỉ số."""
        if not label:
            return
        clamped = max(0.0, min(100.0, score))
        color = _get_score_color(clamped)
        grade = _get_grade_for_score(clamped)
        label.setText(f"{clamped:.1f} / 100  ({grade})")
        label.setStyleSheet(f"color: {color}; font-weight: bold;")

    def update_scores(
        self,
        total_score: float,
        grade: str,
        quality_score: float,
        security_score: float,
        crit_scores: dict[str, float],
    ) -> None:
        """Cập nhật toàn bộ điểm tổng kết, xếp loại và các tiêu chí chi tiết."""
        self._grade_label.set_grade_and_score(grade, total_score)
        self._set_metric_label(self._lbl_quality_val, quality_score)
        self._set_metric_label(self._lbl_security_val, security_score)

        for key, score_bar in self._score_bars.items():
            score_bar.set_score(float(crit_scores.get(key, 0.0)))
