"""Widget thông báo nội dòng (InlineNotice) phẳng theo chuẩn SKILLS.md."""

from PyQt6.QtCore import Qt, pyqtSignal  # pylint: disable=no-name-in-module
from PyQt6.QtWidgets import (  # pylint: disable=no-name-in-module
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QWidget,
)

from frontend.views.theme import (
    ACCENT,
    BORDER,
    BORDER_SOFT,
    SEV_CRITICAL,
    SEV_HIGH,
    SURFACE,
    SURFACE_ALT,
    TEXT_MAIN,
    TEXT_MUTED,
)

_NOTICE_COLORS: dict[str, str] = {
    "info": ACCENT,
    "warning": SEV_HIGH,
    "error": SEV_CRITICAL,
    "offline": TEXT_MUTED,
}


class InlineNotice(QFrame):
    """
    Thanh thông báo phẳng đặt nội dòng trong trang hoặc phía trên bảng dữ liệu.

    - Nền SURFACE_ALT (#F5F6F8), viền mảnh 1px BORDER_SOFT (#E4E7EC), bo góc 4px.
    - Thanh vạch màu chỉ thị 3px bên trái ứng với loại thông báo (info/warning/error/offline).
    - Hỗ trợ nút phụ bên phải (Thử lại, Bỏ qua...) phát tín hiệu action_clicked/retry_clicked.
    - Không dùng icon emoji (❌, ⚠️) theo đúng tiêu chuẩn SKILLS.md.
    """

    action_clicked = pyqtSignal()
    retry_clicked = pyqtSignal()

    def __init__(
        self,
        message: str = "",
        notice_type: str = "info",
        action_text: str | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._message = message
        self._notice_type = notice_type
        self._action_text = action_text

        self._setup_ui()
        self.set_notice(message, notice_type, action_text)

    def _setup_ui(self) -> None:
        """Khởi tạo cấu trúc giao diện thông báo."""
        self.setStyleSheet(
            f"InlineNotice {{"
            f"    background-color: {SURFACE_ALT};"
            f"    border: 1px solid {BORDER_SOFT};"
            f"    border-radius: 4px;"
            f"}}"
        )

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(10)
        layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        # 1. Thanh vạch màu chỉ thị loại thông báo (3x16px)
        self._indicator_bar = QWidget(self)
        self._indicator_bar.setFixedWidth(3)
        self._indicator_bar.setFixedHeight(18)
        layout.addWidget(self._indicator_bar)

        # 2. Nội dung thông báo chính
        self._lbl_message = QLabel("", self)
        self._lbl_message.setStyleSheet(
            f"color: {TEXT_MAIN};"
            f"font-size: 13px;"
            f"border: none;"
            f"background: transparent;"
        )
        self._lbl_message.setWordWrap(True)
        layout.addWidget(self._lbl_message, stretch=1)

        # 3. Nút hành động phụ / Thử lại (Tuỳ chọn)
        self._btn_action = QPushButton("", self)
        self._btn_action.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_action.setStyleSheet(
            f"QPushButton {{"
            f"    background-color: {SURFACE};"
            f"    border: 1px solid {BORDER};"
            f"    border-radius: 4px;"
            f"    padding: 3px 10px;"
            f"    font-size: 12px;"
            f"    font-weight: 500;"
            f"    color: {TEXT_MAIN};"
            f"}}"
            f"QPushButton:hover {{"
            f"    background-color: {SURFACE_ALT};"
            f"    border-color: {TEXT_MUTED};"
            f"}}"
        )
        self._btn_action.clicked.connect(self._on_action_clicked)
        layout.addWidget(self._btn_action)

    def _on_action_clicked(self) -> None:
        """Điều phối tín hiệu khi người dùng nhấn nút hành động."""
        self.action_clicked.emit()
        self.retry_clicked.emit()

    def set_notice(
        self,
        message: str,
        notice_type: str = "info",
        action_text: str | None = None,
    ) -> None:
        """Cập nhật toàn bộ thông điệp, kiểu cảnh báo và nút hành động."""
        self._message = str(message).strip()
        self._notice_type = str(notice_type).strip().lower()
        self._action_text = action_text

        # Cập nhật màu thanh chỉ thị
        color = _NOTICE_COLORS.get(self._notice_type, ACCENT)
        self._indicator_bar.setStyleSheet(
            f"background-color: {color}; border-radius: 1px; border: none;"
        )

        # Cập nhật nội dung thông báo
        self._lbl_message.setText(self._message)

        # Cập nhật nút bấm
        if action_text and action_text.strip():
            self._btn_action.setText(action_text.strip())
            self._btn_action.show()
        else:
            self._btn_action.hide()

    def set_message(self, message: str) -> None:
        """Cập nhật nội dung thông báo."""
        self.set_notice(message, self._notice_type, self._action_text)

    def set_notice_type(self, notice_type: str) -> None:
        """Cập nhật loại cảnh báo ('info', 'warning', 'error', 'offline')."""
        self.set_notice(self._message, notice_type, self._action_text)

    def set_action_text(self, action_text: str | None) -> None:
        """Cập nhật nhãn nút phụ (truyền None để ẩn)."""
        self.set_notice(self._message, self._notice_type, action_text)
