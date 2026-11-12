"""Khung chứa nội dung và bảng (Panel) theo phong cách kỹ thuật."""

from PyQt6.QtWidgets import QFrame, QWidget  # pylint: disable=no-name-in-module


class Panel(QFrame):  # pylint: disable=too-few-public-methods
    """Khung nền trắng viền mảnh bo góc bao quanh bảng hoặc nhóm nội dung."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("Panel")
        self.setStyleSheet(
            "QFrame#Panel { background-color: #FFFFFF; "
            "border: 1px solid #E2E5E9; border-radius: 6px; }"
        )
