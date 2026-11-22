"""Component khung chi tiết lỗi và trình xem trích đoạn mã nguồn (IssueDetailPanel)."""

from __future__ import annotations

from typing import Any

from PyQt6.QtCore import Qt, pyqtSignal  # pylint: disable=no-name-in-module
from PyQt6.QtGui import (  # pylint: disable=no-name-in-module
    QColor,
    QTextCursor,
    QTextFormat,
)
from PyQt6.QtWidgets import (  # pylint: disable=no-name-in-module
    QApplication,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QStackedLayout,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from frontend.models.issue_model import (
    _TOOL_DISPLAY_MAP,
    _format_location,
    _normalize_severity,
    _prepare_snippet_lines,
)
from frontend.views.theme import (
    BORDER,
    BORDER_SOFT,
    SURFACE,
    SURFACE_ALT,
    TEXT_MAIN,
    TEXT_MUTED,
    lay_font_code,
)
from frontend.views.widgets.severity_badge import SeverityBadge


# pylint: disable=too-many-instance-attributes
class IssueDetailPanel(QFrame):
    """
    Khung hiển thị chi tiết thông tin lỗi, trích đoạn code và cập nhật trạng thái/ghi chú.
    """

    save_note_requested = pyqtSignal(int, str, object)
    explain_requested = pyqtSignal(int)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._selected_issue: dict[str, Any] | None = None

        self.setStyleSheet(
            f"QFrame {{ background-color: {SURFACE}; border: 1px solid {BORDER}; "
            f"border-radius: 4px; }}"
        )

        self._detail_stack = QStackedLayout(self)
        self._detail_stack.setContentsMargins(0, 0, 0, 0)

        # 1. Widgets form chi tiết
        self.lbl_detail_location = QLabel("—")
        self.badge_severity = SeverityBadge("Medium")
        self.lbl_detail_rule = QLabel("—")
        self.txt_detail_desc = QTextEdit()
        self.txt_code_snippet = QPlainTextEdit()
        self.ai_container: QFrame | None = None
        self.lbl_ai_triage = QLabel("")
        self.txt_ai_analysis = QTextEdit()
        self.txt_ai_patch = QPlainTextEdit()
        self.btn_copy_patch = QPushButton("Sao chép mã sửa")
        self.btn_explain_ai = QPushButton("Phân tích bằng DeepSeek")
        self.combo_detail_status = QComboBox()
        self.edit_detail_note = QLineEdit()
        self.btn_save_note = QPushButton("Lưu ghi chú")

        self._setup_ui()

    def _setup_ui(self) -> None:
        """Khởi tạo bố cục các trang Placeholder và Detail Form."""
        # Trang 0: Placeholder
        placeholder = self._create_placeholder()
        self._detail_stack.addWidget(placeholder)

        # Trang 1: Form chi tiết
        detail_form = self._create_form()
        self._detail_stack.addWidget(detail_form)

        self._detail_stack.setCurrentIndex(0)

    def _create_placeholder(self) -> QWidget:
        """Tạo trang thông báo khi chưa chọn lỗi nào trên bảng."""
        placeholder = QWidget(self)
        layout = QVBoxLayout(placeholder)
        layout.setContentsMargins(20, 24, 20, 24)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        lbl_hint = QLabel(
            "Chọn một dòng lỗi trên bảng để xem chi tiết và khuyến nghị sửa chữa.",
            placeholder,
        )
        lbl_hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_hint.setStyleSheet(
            f"color: {TEXT_MUTED}; font-size: 13px; font-weight: 500; border: none;"
        )
        layout.addWidget(lbl_hint)
        return placeholder

    def _create_form(self) -> QWidget:
        """Tạo trang chi tiết bao gồm thông tin vị trí, code snippet và thanh lưu ghi chú."""
        form_widget = QWidget(self)
        layout = QVBoxLayout(form_widget)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(8)

        # Header chi tiết
        header_layout = QHBoxLayout()
        header_layout.setSpacing(10)

        self.lbl_detail_location.setFont(lay_font_code(12))
        self.lbl_detail_location.setStyleSheet("font-weight: 600; border: none;")

        self.lbl_detail_rule.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 13px; border: none;")

        header_layout.addWidget(self.lbl_detail_location)
        header_layout.addWidget(self.badge_severity)
        header_layout.addWidget(self.lbl_detail_rule)
        header_layout.addStretch()
        layout.addLayout(header_layout)

        # Khối mô tả chi tiết
        self.txt_detail_desc.setReadOnly(True)
        self.txt_detail_desc.setStyleSheet(
            "QTextEdit { border: none; background: transparent; font-size: 13px; }"
        )
        self.txt_detail_desc.setPlaceholderText(
            "Chọn một dòng lỗi trên bảng để xem chi tiết và khuyến nghị sửa chữa..."
        )
        layout.addWidget(self.txt_detail_desc)

        # Code Snippet Viewer
        self.txt_code_snippet.setReadOnly(True)
        self.txt_code_snippet.setFont(lay_font_code(11))
        self.txt_code_snippet.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self.txt_code_snippet.setStyleSheet(
            f"QPlainTextEdit {{ background-color: {SURFACE_ALT}; border: 1px solid {BORDER_SOFT}; "
            f"border-radius: 4px; padding: 6px; color: {TEXT_MAIN}; }}"
        )
        self.txt_code_snippet.setVisible(False)
        layout.addWidget(self.txt_code_snippet, 1)

        layout.addWidget(self._create_ai_block(form_widget))

        # Thanh cập nhật trạng thái & ghi chú
        status_bar_layout = QHBoxLayout()
        status_bar_layout.setSpacing(8)

        lbl_status = QLabel("Trạng thái:")
        lbl_status.setStyleSheet("border: none; font-size: 13px;")

        self.combo_detail_status.addItem("Chưa sửa", "open")
        self.combo_detail_status.addItem("Đang sửa", "in_progress")
        self.combo_detail_status.addItem("Đã sửa", "fixed")
        self.combo_detail_status.addItem("Báo sai", "ignored")

        lbl_note = QLabel("Ghi chú:")
        lbl_note.setStyleSheet("border: none; font-size: 13px;")

        self.edit_detail_note.setPlaceholderText("Ghi chú hướng khắc phục hoặc tiến độ...")
        self.btn_save_note.clicked.connect(self._on_save_clicked)

        status_bar_layout.addWidget(lbl_status)
        status_bar_layout.addWidget(self.combo_detail_status)
        status_bar_layout.addWidget(lbl_note)
        status_bar_layout.addWidget(self.edit_detail_note, 1)
        status_bar_layout.addWidget(self.btn_save_note)

        layout.addLayout(status_bar_layout)
        return form_widget

    def _create_ai_block(self, parent: QWidget) -> QWidget:
        """Tạo khối thẩm định & đề xuất sửa lỗi từ DeepSeek AI."""
        self.ai_container = QFrame(parent)
        self.ai_container.setObjectName("AiDetailBox")
        self.ai_container.setStyleSheet(
            f"QFrame#AiDetailBox {{ background-color: {SURFACE_ALT}; border: 1px solid {BORDER_SOFT}; "
            f"border-radius: 4px; padding: 4px; }}"
        )
        ai_layout = QVBoxLayout(self.ai_container)
        ai_layout.setContentsMargins(8, 6, 8, 6)
        ai_layout.setSpacing(6)

        ai_header = QHBoxLayout()
        ai_title = QLabel("Thẩm định & Đề xuất sửa (DeepSeek AI):")
        ai_title.setStyleSheet(f"font-weight: 600; font-size: 12px; color: {TEXT_MAIN}; border: none;")
        self.lbl_ai_triage.setStyleSheet(f"font-size: 11px; font-weight: 600; color: {TEXT_MUTED}; border: none;")
        ai_header.addWidget(ai_title)
        ai_header.addWidget(self.lbl_ai_triage)
        ai_header.addStretch()

        self.btn_copy_patch.setFixedHeight(26)
        self.btn_copy_patch.clicked.connect(self._on_copy_patch_clicked)
        ai_header.addWidget(self.btn_copy_patch)

        self.btn_explain_ai.setFixedHeight(26)
        self.btn_explain_ai.clicked.connect(self._on_explain_clicked)
        ai_header.addWidget(self.btn_explain_ai)
        ai_layout.addLayout(ai_header)

        self.txt_ai_analysis.setReadOnly(True)
        self.txt_ai_analysis.setStyleSheet("QTextEdit { border: none; background: transparent; font-size: 12px; }")
        self.txt_ai_analysis.setMaximumHeight(50)
        ai_layout.addWidget(self.txt_ai_analysis)

        self.txt_ai_patch.setReadOnly(True)
        self.txt_ai_patch.setFont(lay_font_code(11))
        self.txt_ai_patch.setMaximumHeight(65)
        self.txt_ai_patch.setStyleSheet(
            f"QPlainTextEdit {{ background-color: {SURFACE}; border: 1px solid {BORDER_SOFT}; border-radius: 3px; }}"
        )
        ai_layout.addWidget(self.txt_ai_patch)
        return self.ai_container

    def _on_copy_patch_clicked(self) -> None:
        """Sao chép đoạn mã sửa lỗi do AI đề xuất vào clipboard."""
        patch_text = self.txt_ai_patch.toPlainText().strip()
        if patch_text:
            clipboard = QApplication.clipboard()
            if clipboard:
                clipboard.setText(patch_text)

    def _on_explain_clicked(self) -> None:
        """Gửi tín hiệu yêu cầu DeepSeek AI phân tích lỗi hiện tại."""
        if not self._selected_issue:
            return
        raw_id = self._selected_issue.get("id") or self._selected_issue.get("issue_id")
        if raw_id:
            self.explain_requested.emit(int(raw_id))

    def _on_save_clicked(self) -> None:
        """Phát tín hiệu yêu cầu lưu ghi chú lên màn hình cha."""
        if not self._selected_issue:
            return
        raw_id = self._selected_issue.get("id") or self._selected_issue.get("issue_id")
        issue_id = int(raw_id) if raw_id is not None else 0
        new_status = str(self.combo_detail_status.currentData() or "open")
        new_note = self.edit_detail_note.text().strip() or None
        self.save_note_requested.emit(issue_id, new_status, new_note)

    def set_save_enabled(self, enabled: bool) -> None:
        """Bật/tắt trạng thái nút lưu ghi chú."""
        self.btn_save_note.setEnabled(enabled)

    def get_selected_issue(self) -> dict[str, Any] | None:
        """Lấy thông tin lỗi hiện đang được chọn hiển thị."""
        return self._selected_issue

    def display_issue(self, issue: dict[str, Any]) -> None:
        """Hiển thị thông tin chi tiết một lỗi vào panel dưới."""
        self._detail_stack.setCurrentIndex(1)
        self._selected_issue = issue
        self.lbl_detail_location.setText(_format_location(issue))
        self.badge_severity.set_severity(_normalize_severity(issue.get("severity")))

        tool_name = _TOOL_DISPLAY_MAP.get(
            str(issue.get("tool") or "").lower(),
            str(issue.get("tool") or "").capitalize(),
        )
        rule_code = str(issue.get("rule_code") or "").strip()
        rule_text = f"Công cụ: {tool_name}"
        if rule_code:
            rule_text += f" · Mã kiểm thử: {rule_code}"
        self.lbl_detail_rule.setText(rule_text)

        desc = str(issue.get("message") or "")
        remediation = str(issue.get("remediation") or "").strip()
        if remediation:
            desc = f"{desc}\n\nĐề xuất khắc phục:\n{remediation}"
        self.txt_detail_desc.setPlainText(desc)

        target_line = 0
        raw_line = issue.get("line_number")
        if raw_line is None:
            raw_line = issue.get("line")
        if raw_line is not None:
            try:
                target_line = int(raw_line)
            except (ValueError, TypeError):
                target_line = 0

        self._display_code_snippet(issue.get("code_snippet"), target_line)

        raw_status = str(issue.get("status") or "open").lower()
        idx = self.combo_detail_status.findData(raw_status)
        if idx >= 0:
            self.combo_detail_status.setCurrentIndex(idx)
        else:
            self.combo_detail_status.setCurrentIndex(0)

        note_text = str(issue.get("note") or "")
        self.edit_detail_note.setText(note_text)

        self._display_ai_info(issue)

    def _display_ai_info(self, issue: dict[str, Any]) -> None:
        """Cập nhật giao diện thẩm định và bản vá DeepSeek AI."""
        ai_analysis = str(issue.get("ai_analysis") or "").strip()
        ai_triage = str(issue.get("ai_triage") or "").strip()
        ai_patch = str(issue.get("ai_patch") or "").strip()

        if ai_analysis:
            triage_label = "Rủi ro xác nhận" if ai_triage == "confirmed_risk" else "Nghi ngờ báo giả"
            self.lbl_ai_triage.setText(f"· Đánh giá: {triage_label}")
            self.txt_ai_analysis.setPlainText(ai_analysis)
            self.txt_ai_analysis.setVisible(True)
            self.btn_explain_ai.setVisible(False)
            if ai_patch:
                self.txt_ai_patch.setPlainText(ai_patch)
                self.txt_ai_patch.setVisible(True)
                self.btn_copy_patch.setVisible(True)
            else:
                self.txt_ai_patch.clear()
                self.txt_ai_patch.setVisible(False)
                self.btn_copy_patch.setVisible(False)
        else:
            self.lbl_ai_triage.setText("· Chưa thẩm định")
            self.txt_ai_analysis.setPlainText(
                "Nhấn 'Phân tích bằng DeepSeek' để AI giải thích nguyên nhân và đề xuất mã sửa."
            )
            self.txt_ai_analysis.setVisible(True)
            self.txt_ai_patch.clear()
            self.txt_ai_patch.setVisible(False)
            self.btn_copy_patch.setVisible(False)
            self.btn_explain_ai.setVisible(True)

    def _display_code_snippet(self, snippet_raw: Any, target_line: int) -> None:
        """Hiển thị đoạn trích mã nguồn có số dòng và tô màu đỏ nhạt dòng lỗi."""
        self.txt_code_snippet.clear()
        self.txt_code_snippet.setExtraSelections([])
        if not snippet_raw:
            self.txt_code_snippet.setVisible(False)
            self.txt_detail_desc.setMaximumHeight(16777215)
            return

        formatted_lines = _prepare_snippet_lines(snippet_raw, target_line)
        if not formatted_lines:
            self.txt_code_snippet.setVisible(False)
            self.txt_detail_desc.setMaximumHeight(16777215)
            return

        self.txt_code_snippet.setVisible(True)
        self.txt_detail_desc.setMaximumHeight(85)
        full_text = "\n".join(text for _, text in formatted_lines)
        self.txt_code_snippet.setPlainText(full_text)

        extra_selections: list[QTextEdit.ExtraSelection] = []
        doc = self.txt_code_snippet.document()
        if target_line > 0:
            for block_idx, (ln, _) in enumerate(formatted_lines):
                if ln == target_line:
                    block = doc.findBlockByLineNumber(block_idx)
                    if block.isValid():
                        sel = QTextEdit.ExtraSelection()
                        sel.format.setBackground(QColor("#FDECEC"))
                        sel.format.setProperty(
                            QTextFormat.Property.FullWidthSelection, True
                        )
                        sel.cursor = QTextCursor(block)
                        extra_selections.append(sel)
        self.txt_code_snippet.setExtraSelections(extra_selections)

    def clear(self) -> None:
        """Xóa trắng nội dung panel chi tiết và quay về trang hướng dẫn."""
        self._selected_issue = None
        self.lbl_detail_location.setText("—")
        self.badge_severity.set_severity("Medium")
        self.lbl_detail_rule.setText("—")
        self.txt_detail_desc.clear()
        self.txt_code_snippet.clear()
        self.txt_code_snippet.setVisible(False)
        self.lbl_ai_triage.setText("")
        self.txt_ai_analysis.clear()
        self.txt_ai_patch.clear()
        self.txt_ai_patch.setVisible(False)
        self.btn_copy_patch.setVisible(False)
        self.btn_explain_ai.setVisible(False)
        self.edit_detail_note.clear()
        self._detail_stack.setCurrentIndex(0)
