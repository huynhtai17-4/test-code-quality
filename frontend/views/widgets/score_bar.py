"""Widget thanh điểm thành phần (ScoreBar) theo chuẩn SKILLS.md."""

from PyQt6.QtCore import (  # pylint: disable=no-name-in-module
    QEasingCurve,
    QPropertyAnimation,
)
from PyQt6.QtWidgets import (  # pylint: disable=no-name-in-module
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QVBoxLayout,
    QWidget,
)

from frontend.views.theme import (
    ACCENT,
    BORDER_SOFT,
    TEN_TIEU_CHI,
    TEXT_MAIN,
    TRONG_SO_MAC_DINH,
)


class ScoreBar(QWidget):  # pylint: disable=too-few-public-methods
    """
    Thanh hiển thị điểm số tiêu chí thành phần (Thanh ngang mảnh 6px).

    - Nhãn tên tiêu chí bên trái, điểm số căn phải.
    - Thanh tiến độ mảnh cao đúng 6px.
    - Tooltip hiển thị tỷ trọng và điểm đóng góp khi di chuột.
    - Hỗ trợ animation mượt nhẹ (<= 350ms) từ 0 đến điểm thực tế.
    """

    def __init__(
        self,
        criterion_key: str,
        score: float = 0.0,
        weight: float | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.criterion_key = criterion_key
        self.weight = (
            weight
            if weight is not None
            else TRONG_SO_MAC_DINH.get(criterion_key, 0.20)
        )
        self.score = float(score)

        self._anim: QPropertyAnimation | None = None
        self._setup_ui()
        self.set_score(self.score, self.weight, animate=False)

    def _setup_ui(self) -> None:
        """Khởi tạo giao diện thanh điểm."""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 4, 0, 4)
        main_layout.setSpacing(4)

        # Hàng trên: Tên tiêu chí + Điểm số
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)

        title = TEN_TIEU_CHI.get(self.criterion_key, self.criterion_key)
        self._lbl_title = QLabel(title, self)
        self._lbl_title.setStyleSheet(
            f"color: {TEXT_MAIN}; font-size: 13px; font-weight: 500;"
        )

        self._lbl_score = QLabel(f"{int(round(self.score))}", self)
        self._lbl_score.setStyleSheet(
            f"color: {TEXT_MAIN}; font-size: 13px; font-weight: 600;"
        )

        header_layout.addWidget(self._lbl_title)
        header_layout.addStretch()
        header_layout.addWidget(self._lbl_score)

        # Hàng dưới: QProgressBar mảnh 6px
        self._bar = QProgressBar(self)
        self._bar.setRange(0, 100)
        self._bar.setValue(0)
        self._bar.setTextVisible(False)
        self._bar.setFixedHeight(6)
        self._bar.setStyleSheet(
            f"QProgressBar {{"
            f"    background-color: {BORDER_SOFT};"
            f"    border: none;"
            f"    border-radius: 3px;"
            f"}}"
            f"QProgressBar::chunk {{"
            f"    background-color: {ACCENT};"
            f"    border-radius: 3px;"
            f"}}"
        )

        main_layout.addLayout(header_layout)
        main_layout.addWidget(self._bar)

    def set_score(
        self,
        score: float,
        weight: float | None = None,
        animate: bool = True,
    ) -> None:
        """Cập nhật điểm số, trọng số và hiệu ứng thanh tiến trình."""
        self.score = max(0.0, min(100.0, float(score)))
        if weight is not None:
            self.weight = max(0.0, min(1.0, float(weight)))

        int_score = int(round(self.score))

        if self.score >= 80.0:
            bar_color = "#10B981"
        elif self.score >= 70.0:
            bar_color = "#3B82F6"
        elif self.score >= 60.0:
            bar_color = "#F59E0B"
        elif self.score >= 50.0:
            bar_color = "#F97316"
        else:
            bar_color = "#EF4444"

        self._lbl_score.setText(f"{int_score}")
        self._lbl_score.setStyleSheet(
            f"color: {bar_color}; font-size: 13px; font-weight: 600;"
        )
        self._bar.setStyleSheet(
            f"QProgressBar {{"
            f"    background-color: {BORDER_SOFT};"
            f"    border: none;"
            f"    border-radius: 3px;"
            f"}}"
            f"QProgressBar::chunk {{"
            f"    background-color: {bar_color};"
            f"    border-radius: 3px;"
            f"}}"
        )

        # Cập nhật tooltip theo chuẩn SKILLS.md
        weight_percent = int(round(self.weight * 100))
        contrib_score = round(self.score * self.weight, 1)
        tip_text = (
            f"Trọng số: {weight_percent}% "
            f"(Đóng góp {contrib_score:.1f} điểm vào điểm tổng)"
        )
        self.setToolTip(tip_text)
        self._bar.setToolTip(tip_text)

        if animate:
            if self._anim and self._anim.state() == QPropertyAnimation.State.Running:
                self._anim.stop()

            self._anim = QPropertyAnimation(self._bar, b"value", self)
            self._anim.setDuration(300)  # <= 350ms theo SKILLS.md
            self._anim.setStartValue(self._bar.value())
            self._anim.setEndValue(int_score)
            self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)
            self._anim.start()
        else:
            self._bar.setValue(int_score)
