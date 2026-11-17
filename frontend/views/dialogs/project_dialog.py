"""Hộp thoại thêm mới và chỉnh sửa thông tin dự án."""

from __future__ import annotations

from typing import Any

from PyQt6.QtCore import Qt  # pylint: disable=no-name-in-module
from PyQt6.QtWidgets import (  # pylint: disable=no-name-in-module
    QComboBox,
    QDialog,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from frontend.views.theme import SURFACE, TEXT_MAIN


# pylint: disable=too-many-instance-attributes,too-few-public-methods
class ProjectDialog(QDialog):
    """Hộp thoại thêm mới hoặc chỉnh sửa dự án (Bo góc 8px, phím Enter/Esc)."""

    def __init__(
        self,
        project: dict[str, Any] | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._project = project
        self.is_edit_mode = project is not None

        title = "Chỉnh sửa dự án" if self.is_edit_mode else "Thêm dự án mới"
        self.setWindowTitle(title)
        self.resize(520, 360)
        self.setStyleSheet(
            f"QDialog {{ background-color: {SURFACE}; border-radius: 8px; }}"
        )

        self._txt_name = QLineEdit(self)
        self._cbo_source = QComboBox(self)
        self._txt_path = QLineEdit(self)
        self._btn_browse = QPushButton("Duyệt thư mục...", self)
        self._txt_desc = QTextEdit(self)
        self._lbl_error = QLabel("", self)
        self._btn_save = QPushButton("Lưu dự án", self)

        self._setup_ui()
        if self._project:
            self._fill_data(self._project)

    def _setup_ui(self) -> None:
        """Khởi tạo bố cục form nhập liệu."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)

        header_text = "Chỉnh sửa dự án" if self.is_edit_mode else "Thêm dự án mới"
        lbl_head = QLabel(header_text, self)
        lbl_head.setStyleSheet(f"font-size: 16px; font-weight: 600; color: {TEXT_MAIN};")
        layout.addWidget(lbl_head)

        form = QFormLayout()
        form.setSpacing(10)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)

        self._txt_name.setPlaceholderText("Ví dụ: Flask, Django-Shop, Tool-Analyzer...")
        form.addRow("Tên dự án (*):", self._txt_name)

        self._cbo_source.addItems(["Thư mục cục bộ", "Kho mã nguồn GitHub"])
        self._cbo_source.currentTextChanged.connect(self._on_source_type_changed)
        form.addRow("Loại nguồn:", self._cbo_source)

        path_box = QHBoxLayout()
        self._txt_path.setPlaceholderText("Ví dụ: D:/Projects/my-python-app")
        self._btn_browse.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_browse.clicked.connect(self._on_browse)
        path_box.addWidget(self._txt_path, stretch=1)
        path_box.addWidget(self._btn_browse)
        form.addRow("Đường dẫn / URL (*):", path_box)

        self._txt_desc.setFixedHeight(64)
        self._txt_desc.setPlaceholderText("Mô tả ngắn gọn về phạm vi kiểm định của dự án...")
        form.addRow("Mô tả:", self._txt_desc)

        layout.addLayout(form)

        self._lbl_error.setStyleSheet("color: #B42318; font-size: 12px;")
        self._lbl_error.hide()
        layout.addWidget(self._lbl_error)
        layout.addStretch()

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)
        btn_layout.addStretch()

        btn_cancel = QPushButton("Hủy", self)
        btn_cancel.clicked.connect(self.reject)

        self._btn_save.setProperty("role", "primary")
        self._btn_save.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_save.setDefault(True)
        self._btn_save.clicked.connect(self._on_save)

        btn_layout.addWidget(btn_cancel)
        btn_layout.addWidget(self._btn_save)
        layout.addLayout(btn_layout)

        self._txt_name.setFocus()

    def _on_source_type_changed(self, text: str) -> None:
        """Đổi placeholder và trạng thái nút duyệt theo loại nguồn."""
        if "GitHub" in text:
            self._txt_path.setPlaceholderText("https://github.com/user/repository")
            self._btn_browse.setEnabled(False)
        else:
            self._txt_path.setPlaceholderText("Ví dụ: D:/Projects/my-python-app")
            self._btn_browse.setEnabled(True)

    def _on_browse(self) -> None:
        """Mở hộp thoại chọn thư mục mã nguồn từ máy tính."""
        folder = QFileDialog.getExistingDirectory(self, "Chọn thư mục mã nguồn Python", "")
        if folder:
            self._txt_path.setText(str(folder).replace("\\", "/"))

    def _fill_data(self, project: dict[str, Any]) -> None:
        """Điền thông tin dự án hiện có khi chỉnh sửa."""
        self._txt_name.setText(str(project.get("name", "")))
        path = str(project.get("path") or project.get("source_path") or "")
        self._txt_path.setText(path)
        self._txt_desc.setPlainText(str(project.get("description", "")))

        if "github" in path.lower() or "http" in path.lower():
            self._cbo_source.setCurrentIndex(1)
        else:
            self._cbo_source.setCurrentIndex(0)

    def _on_save(self) -> None:
        """Kiểm tra hợp lệ trước khi lưu."""
        name = self._txt_name.text().strip()
        path = self._txt_path.text().strip()

        if not name:
            self._lbl_error.setText("Tên dự án không được để trống.")
            self._lbl_error.show()
            self._txt_name.setFocus()
            return

        if not path:
            self._lbl_error.setText("Đường dẫn mã nguồn hoặc URL không được để trống.")
            self._lbl_error.show()
            self._txt_path.setFocus()
            return

        self._lbl_error.hide()
        self.accept()

    def get_data(self) -> dict[str, str]:
        """Lấy dữ liệu đã nhập từ form."""
        source_type = "github" if self._cbo_source.currentIndex() == 1 else "local"
        return {
            "name": self._txt_name.text().strip(),
            "path": self._txt_path.text().strip(),
            "description": self._txt_desc.toPlainText().strip(),
            "source_type": source_type,
        }
