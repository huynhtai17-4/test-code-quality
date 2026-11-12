"""Widget chấm tròn trạng thái lỗi (StatusDot) theo chuẩn SKILLS.md."""

from PyQt6.QtCore import Qt  # pylint: disable=no-name-in-module
from PyQt6.QtGui import (  # pylint: disable=no-name-in-module
    QColor,
    QPaintEvent,
    QPainter,
)
from PyQt6.QtWidgets import (  # pylint: disable=no-name-in-module
    QHBoxLayout,
    QLabel,
    QWidget,
)

from frontend.views.theme import (
    STATUS_COLORS,
    STATUS_LABELS,
    TEXT_MAIN,
)


class _DotCircle(QWidget):  # pylint: disable=too-few-public-methods
    """Thành phần vẽ chấm tròn 8x8px khử răng cưa bằng QPainter."""

    def __init__(self, color_hex: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.color_hex = color_hex
        self.setFixedSize(8, 8)

    def set_color(self, color_hex: str) -> None:
        """Cập nhật màu chấm tròn và vẽ lại."""
        self.color_hex = color_hex
        self.update()

    def paintEvent(self, _event: QPaintEvent | None) -> None:  # pylint: disable=invalid-name
        """Vẽ chấm tròn 8x8px hoàn hảo."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(self.color_hex))
        painter.drawEllipse(0, 0, 8, 8)


class StatusDot(QWidget):  # pylint: disable=too-few-public-methods
    """
    Widget hiển thị trạng thái xử lý lỗi (Chấm tròn 8px + nhãn chữ).

    Không tô màu toàn bộ nền ô bảng, chỉ hiển thị chấm tròn màu và chữ màu chính.
    """

    def __init__(
        self,
        status: str = "open",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)

        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(6)

        self._dot = _DotCircle(STATUS_COLORS.get(status, "#B42318"), self)
        self._label = QLabel("", self)
        self._label.setStyleSheet(
            f"color: {TEXT_MAIN}; font-size: 13px; font-weight: normal;"
        )

        self.layout.addWidget(self._dot)
        self.layout.addWidget(self._label)
        self.layout.addStretch()

        self.set_status(status)

    def set_status(self, status: str) -> None:
        """Cập nhật trạng thái xử lý và màu sắc tương ứng."""
        clean_status = str(status).strip().lower()
        color = STATUS_COLORS.get(clean_status, STATUS_COLORS["open"])
        text = STATUS_LABELS.get(clean_status, "Chưa sửa")

        self._dot.set_color(color)
        self._label.setText(text)
