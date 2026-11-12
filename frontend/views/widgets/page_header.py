"""Thanh tiêu đề trang (PageHeader) tích hợp nút hành động chuẩn giao diện kỹ thuật."""

from PyQt6.QtWidgets import (  # pylint: disable=no-name-in-module
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from frontend.views.theme import TEXT_MAIN, TEXT_MUTED


class PageHeader(QWidget):
    """Tiêu đề màn hình gồm nhãn chính, phụ đề kỹ thuật và khu vực nút thao tác bên phải."""

    def __init__(
        self,
        title: str,
        subtitle: str = "",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("PageHeaderWidget")

        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(16)

        # Cột trái: Tiêu đề + Phụ đề
        text_layout = QVBoxLayout()
        text_layout.setContentsMargins(0, 0, 0, 0)
        text_layout.setSpacing(3)

        self._lbl_title = QLabel(title, self)
        self._lbl_title.setObjectName("PageTitle")
        self._lbl_title.setStyleSheet(
            f"color: {TEXT_MAIN}; font-size: 20px; font-weight: 700; "
            "letter-spacing: -0.3px; border: none;"
        )

        self._lbl_subtitle = QLabel(subtitle, self)
        self._lbl_subtitle.setObjectName("PageSubtitle")
        self._lbl_subtitle.setStyleSheet(
            f"color: {TEXT_MUTED}; font-size: 12px; font-weight: 500; border: none;"
        )
        if not subtitle:
            self._lbl_subtitle.hide()

        text_layout.addWidget(self._lbl_title)
        text_layout.addWidget(self._lbl_subtitle)
        main_layout.addLayout(text_layout)

        main_layout.addStretch()

        # Khu vực nút bên phải
        self._actions_layout = QHBoxLayout()
        self._actions_layout.setContentsMargins(0, 0, 0, 0)
        self._actions_layout.setSpacing(8)
        main_layout.addLayout(self._actions_layout)

    @property
    def lbl_title(self) -> QLabel:
        """Thuộc tính truy cập nhãn tiêu đề."""
        return self._lbl_title

    @property
    def lbl_subtitle(self) -> QLabel:
        """Thuộc tính truy cập nhãn phụ đề."""
        return self._lbl_subtitle

    def set_title(self, title: str) -> None:
        """Cập nhật tiêu đề màn hình."""
        self._lbl_title.setText(str(title).strip())

    def set_subtitle(self, subtitle: str) -> None:
        """Cập nhật phụ đề kỹ thuật."""
        clean_sub = str(subtitle).strip()
        self._lbl_subtitle.setText(clean_sub)
        self._lbl_subtitle.setVisible(bool(clean_sub))

    def them_nut_phai(self, button: QPushButton) -> None:
        """Thêm nút hành động vào phía bên phải của tiêu đề trang."""
        self._actions_layout.addWidget(button)

    def add_action(self, button: QPushButton) -> None:
        """Bí danh tiếng Anh cho them_nut_phai."""
        self.them_nut_phai(button)
