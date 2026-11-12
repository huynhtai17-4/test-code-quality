"""Widget trạng thái rỗng (EmptyState) theo chuẩn SKILLS.md."""

from PyQt6.QtCore import Qt, pyqtSignal  # pylint: disable=no-name-in-module
from PyQt6.QtGui import (  # pylint: disable=no-name-in-module
    QColor,
    QPainter,
    QPen,
)
from PyQt6.QtWidgets import (  # pylint: disable=no-name-in-module
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from frontend.views.theme import (
    BORDER_SOFT,
    SURFACE_ALT,
    TEXT_MAIN,
    TEXT_MUTED,
)


class _EmptyIconPlaceholder(QWidget):  # pylint: disable=too-few-public-methods
    """Khối biểu tượng hình học tối giản không dùng emoji khi chưa có SVG/PNG."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedSize(54, 54)

    def paintEvent(self, _event: object) -> None:  # pylint: disable=invalid-name
        """Vẽ biểu tượng trang tài liệu viền mỏng phẳng, thanh lịch."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Nền hộp bo góc 8px
        painter.setPen(QPen(QColor(BORDER_SOFT), 1))
        painter.setBrush(QColor(SURFACE_ALT))
        painter.drawRoundedRect(3, 3, 48, 48, 6, 6)

        # 3 dòng ngang mô phỏng văn bản/tài liệu tối giản
        pen = QPen(QColor(BORDER_SOFT), 2)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        painter.drawLine(14, 18, 30, 18)
        painter.drawLine(14, 26, 38, 26)
        painter.drawLine(14, 34, 26, 34)


class EmptyState(QWidget):
    """
    Widget hiển thị trạng thái danh sách hoặc bảng rỗng (Không có dữ liệu).

    - Căn giữa toàn bộ nội dung với khoảng cách đệm thoáng đãng.
    - Không dùng icon emoji (❌, ⚠️) theo đúng tiêu chuẩn SKILLS.md.
    - Nút thao tác chính (nếu có) phát ra tín hiệu action_clicked.
    """

    action_clicked = pyqtSignal()

    def __init__(
        self,
        title: str = "Không có dữ liệu",
        description: str = "",
        action_text: str | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)

        self._setup_ui()
        self.set_content(title, description, action_text)

    def _setup_ui(self) -> None:
        """Thiết lập cấu trúc bố cục căn giữa."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 48, 32, 48)
        layout.setSpacing(14)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setMinimumHeight(240)

        # 1. Khối biểu tượng
        icon_widget = _EmptyIconPlaceholder(self)
        layout.addWidget(icon_widget, alignment=Qt.AlignmentFlag.AlignCenter)

        # 2. Tiêu đề chính
        self._lbl_title = QLabel("", self)
        self._lbl_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._lbl_title.setStyleSheet(
            f"color: {TEXT_MAIN};"
            f"font-size: 16px;"
            f"font-weight: 600;"
            f"margin-top: 4px;"
        )
        layout.addWidget(self._lbl_title)

        # 3. Dòng mô tả chi tiết / Hướng dẫn
        self._lbl_desc = QLabel("", self)
        self._lbl_desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._lbl_desc.setWordWrap(True)
        self._lbl_desc.setMinimumWidth(320)
        self._lbl_desc.setMaximumWidth(480)
        self._lbl_desc.setStyleSheet(
            f"color: {TEXT_MUTED};"
            f"font-size: 13px;"
            f"line-height: 1.5;"
            f"padding: 4px 0;"
        )
        layout.addWidget(self._lbl_desc)

        # 4. Nút hành động chính (Tuỳ chọn)
        self._btn_action = QPushButton("", self)
        self._btn_action.setProperty("role", "primary")
        self._btn_action.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_action.clicked.connect(self.action_clicked.emit)
        layout.addWidget(self._btn_action, alignment=Qt.AlignmentFlag.AlignCenter)

    def set_content(
        self,
        title: str,
        description: str = "",
        action_text: str | None = None,
    ) -> None:
        """Cập nhật nội dung tiêu đề, mô tả và nút bấm."""
        self._lbl_title.setText(str(title).strip())

        desc_clean = str(description).strip()
        if desc_clean:
            self._lbl_desc.setText(desc_clean)
            self._lbl_desc.show()
        else:
            self._lbl_desc.hide()

        if action_text and action_text.strip():
            self._btn_action.setText(action_text.strip())
            self._btn_action.setVisible(True)
        else:
            self._btn_action.setVisible(False)

    def set_title(self, title: str) -> None:
        """Cập nhật riêng tiêu đề chính."""
        self._lbl_title.setText(str(title).strip())

    def set_description(self, description: str) -> None:
        """Cập nhật riêng mô tả chi tiết."""
        desc_clean = str(description).strip()
        self._lbl_desc.setText(desc_clean)
        self._lbl_desc.setVisible(bool(desc_clean))

    def set_action_text(self, action_text: str | None) -> None:
        """Cập nhật nhãn nút hành động chính (truyền None để ẩn)."""
        has_text = bool(action_text and action_text.strip())
        if has_text and action_text:
            self._btn_action.setText(action_text.strip())
        self._btn_action.setVisible(has_text)
