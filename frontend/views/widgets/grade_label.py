"""Widget hiển thị chữ cái xếp loại và điểm tổng kết (GradeLabel) theo SKILLS.md."""

from PyQt6.QtCore import Qt  # pylint: disable=no-name-in-module
from PyQt6.QtWidgets import QLabel, QVBoxLayout, QWidget  # pylint: disable=no-name-in-module

from frontend.views.theme import (
    GRADE_A,
    GRADE_COLORS,
    TEXT_MAIN,
    TEXT_MUTED,
)


class GradeLabel(QWidget):  # pylint: disable=too-few-public-methods
    """
    Điểm nhấn thị giác chính của màn hình phân tích.

    - Chữ cái xếp loại (A-F) cỡ 72px bold mang màu chuẩn.
    - Điểm số tổng đặt ngay bên dưới cỡ 40px semibold (ví dụ: 82 / 100).
    - Mọi chi tiết xung quanh tối giản, thanh lịch, không đổ bóng màu mè.
    """

    def __init__(
        self,
        grade: str = "A",
        total_score: float = 100.0,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.grade = str(grade).strip().upper()
        self.total_score = float(total_score)

        self._setup_ui()
        self.set_grade_and_score(self.grade, self.total_score)

    def _setup_ui(self) -> None:
        """Thiết lập bố cục chữ cái và điểm số."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(2)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Chữ cái xếp loại (64px, bold)
        self._lbl_grade = QLabel("A", self)
        self._lbl_grade.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Điểm tổng (26px, semibold)
        self._lbl_score = QLabel("100 / 100", self)
        self._lbl_score.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Dòng chú thích nhỏ
        self._lbl_sub = QLabel("Điểm chất lượng mã nguồn", self)
        self._lbl_sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._lbl_sub.setWordWrap(False)
        self._lbl_sub.setStyleSheet(
            f"color: {TEXT_MUTED}; font-size: 11px; margin-top: 2px;"
        )

        layout.addWidget(self._lbl_grade)
        layout.addWidget(self._lbl_score)
        layout.addWidget(self._lbl_sub)

    def set_grade(self, grade: str, total_score: float | None = None) -> None:
        """Cập nhật xếp loại và điểm số (tương thích ngược cho các lời gọi set_grade)."""
        score = self.total_score if total_score is None else float(total_score)
        self.set_grade_and_score(grade, score)

    def set_grade_and_score(self, grade: str, total_score: float) -> None:
        """Cập nhật xếp loại và điểm tổng kết."""
        self.grade = str(grade).strip().upper()
        self.total_score = float(total_score)

        grade_color = GRADE_COLORS.get(self.grade, GRADE_A)
        self._lbl_grade.setText(self.grade)
        self._lbl_grade.setStyleSheet(
            f"font-size: 64px;"
            f"font-weight: bold;"
            f"color: {grade_color};"
            f"line-height: 1;"
            f"padding: 0px;"
            f"margin: 0px;"
        )

        # Điểm có thể hiển thị số nguyên hoặc 1 chữ số thập phân nếu cần
        if self.total_score.is_integer():
            score_str = f"{int(self.total_score)}"
        else:
            score_str = f"{self.total_score:.1f}"

        self._lbl_score.setText(f"{score_str} / 100")
        self._lbl_score.setStyleSheet(
            f"font-size: 26px;"
            f"font-weight: 700;"
            f"color: {TEXT_MAIN};"
            f"padding: 0px;"
            f"margin: 0px;"
        )
