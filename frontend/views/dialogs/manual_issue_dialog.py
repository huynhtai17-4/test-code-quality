"""Hộp thoại thêm mới lỗi phát hiện thủ công cho phiên phân tích."""

from __future__ import annotations

from typing import Any

from PyQt6.QtCore import Qt  # pylint: disable=no-name-in-module
from PyQt6.QtWidgets import (  # pylint: disable=no-name-in-module
    QComboBox,
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from frontend.views.theme import SEV_CRITICAL


class ManualIssueDialog(QDialog):  # pylint: disable=too-few-public-methods
    """
    Hộp thoại thêm lỗi phát hiện thủ công (ManualIssueDialog).

    Cho phép kiểm thử viên ghi nhận các lỗi logic hoặc bảo mật vào phiên quét.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Thêm lỗi phát hiện thủ công")
        self.setModal(True)
        self.resize(520, 480)

        self.file_edit = QLineEdit()
        self.file_edit.setPlaceholderText("ví dụ: backend/database/db.py")

        self.line_spin = QSpinBox()
        self.line_spin.setRange(1, 100000)
        self.line_spin.setValue(1)

        self.sev_combo = QComboBox()
        self.sev_combo.addItem("Nghiêm trọng", "critical")
        self.sev_combo.addItem("Cao", "high")
        self.sev_combo.addItem("Trung bình", "medium")
        self.sev_combo.addItem("Thấp", "low")
        self.sev_combo.setCurrentIndex(2)

        self.rule_edit = QLineEdit()
        self.rule_edit.setPlaceholderText("ví dụ: SEC-CUSTOM-01 hoặc CWE-89")

        self.message_edit = QTextEdit()
        self.message_edit.setPlaceholderText(
            "Mô tả chi tiết nguyên nhân rủi ro hoặc lỗ hổng bảo mật phát hiện..."
        )
        self.message_edit.setMinimumHeight(100)

        self.note_edit = QLineEdit()
        self.note_edit.setPlaceholderText("Ghi chú hướng khắc phục hoặc khuyến nghị xử lý...")

        self.error_label = QLabel()
        self.error_label.setStyleSheet(f"color: {SEV_CRITICAL}; font-size: 12px;")
        self.error_label.setVisible(False)

        self._init_layout()

    def _init_layout(self) -> None:
        """Thiết lập bố cục form nhập liệu và nút thao tác."""
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(12)
        main_layout.setContentsMargins(20, 20, 20, 20)

        form_layout = QFormLayout()
        form_layout.setSpacing(10)
        form_layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        form_layout.addRow("Đường dẫn tệp (*):", self.file_edit)
        form_layout.addRow("Số dòng:", self.line_spin)
        form_layout.addRow("Mức độ nghiêm trọng:", self.sev_combo)
        form_layout.addRow("Tiêu đề / Mã kiểm thử:", self.rule_edit)
        form_layout.addRow("Mô tả chi tiết (*):", self.message_edit)
        form_layout.addRow("Ghi chú khắc phục:", self.note_edit)

        main_layout.addLayout(form_layout)
        main_layout.addWidget(self.error_label)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        btn_cancel = QPushButton("Hủy")
        btn_cancel.clicked.connect(self.reject)

        btn_save = QPushButton("Lưu lỗi")
        btn_save.setProperty("role", "primary")
        btn_save.clicked.connect(self._on_save)

        btn_layout.addWidget(btn_cancel)
        btn_layout.addWidget(btn_save)
        main_layout.addLayout(btn_layout)

        self.file_edit.setFocus()

    def _on_save(self) -> None:
        """Xác thực tính hợp lệ của dữ liệu trước khi hoàn tất."""
        file_path = self.file_edit.text().strip()
        message = self.message_edit.toPlainText().strip()

        if not file_path:
            self.error_label.setText("Đường dẫn tệp tin không được để trống.")
            self.error_label.setVisible(True)
            self.file_edit.setFocus()
            return

        if not message:
            self.error_label.setText("Mô tả chi tiết lỗ hổng không được để trống.")
            self.error_label.setVisible(True)
            self.message_edit.setFocus()
            return

        self.error_label.setVisible(False)
        self.accept()

    def get_issue_data(self) -> dict[str, Any]:
        """Lấy dictionary thông tin lỗi đã nhập."""
        return {
            "file_path": self.file_edit.text().strip(),
            "line_number": self.line_spin.value(),
            "severity": self.sev_combo.currentData(),
            "rule_code": self.rule_edit.text().strip() or "MANUAL-01",
            "message": self.message_edit.toPlainText().strip(),
            "note": self.note_edit.text().strip() or None,
            "tool": "manual",
        }
