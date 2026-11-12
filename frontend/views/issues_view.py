"""Màn hình Quản lý Lỗi mã nguồn (IssuesView) theo chuẩn kỹ thuật SKILLS.md."""

import sys
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# pylint: disable=wrong-import-position,no-name-in-module,too-many-lines
from PyQt6.QtCore import (
    QAbstractTableModel,
    QItemSelection,
    QModelIndex,
    QSortFilterProxyModel,
    Qt,
    pyqtSignal,
)
from PyQt6.QtGui import QColor, QFont, QKeySequence, QShortcut
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QComboBox,
    QDialog,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMenu,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QSplitter,
    QStackedLayout,
    QTableView,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from frontend.network import api
from frontend.views.theme import (
    BORDER,
    SEV_CRITICAL,
    SEVERITY_COLORS,
    STATUS_FIXED,
    STATUS_IGNORED,
    STATUS_IN_PROGRESS,
    STATUS_OPEN,
    SURFACE,
    TEXT_MAIN,
    TEXT_MUTED,
    lay_font_code,
    load_stylesheet,
)
from frontend.views.widgets.empty_state import EmptyState
from frontend.views.widgets.inline_notice import InlineNotice
from frontend.views.widgets.page_header import PageHeader
from frontend.views.widgets.panel import Panel
from frontend.views.widgets.severity_badge import SeverityBadge
from frontend.views.widgets.table_utils import chuan_hoa_bang
from frontend.workers.request_worker import RequestWorker

_HEADERS = (
    "Tệp : Dòng",
    "Mức độ",
    "Trạng thái",
    "Công cụ",
    "Mô tả tóm tắt",
)

_SEVERITY_TITLES: dict[str, str] = {
    "critical": "Critical",
    "high": "High",
    "medium": "Medium",
    "low": "Low",
    "info": "Low",
}

_STATUS_DISPLAY_MAP: dict[str, str] = {
    "open": "● Chưa sửa",
    "in_progress": "● Đang sửa",
    "fixed": "● Đã sửa",
    "ignored": "● Báo sai",
    "false_positive": "● Báo sai",
}

_TOOL_DISPLAY_MAP: dict[str, str] = {
    "bandit": "Bandit",
    "pylint": "Pylint",
    "radon": "Radon",
    "pip-audit": "Pip-audit",
    "pip_audit": "Pip-audit",
    "manual": "Manual",
}


def _normalize_severity(sev: Any) -> str:
    """Chuẩn hóa chuỗi mức độ nghiêm trọng."""
    raw = str(sev or "medium").strip().lower()
    return _SEVERITY_TITLES.get(raw, "Medium")


def _normalize_status(st: Any) -> str:
    """Chuẩn hóa mã trạng thái lỗi về 4 nhóm chuẩn."""
    raw = str(st or "open").strip().lower()
    if raw == "false_positive":
        return "ignored"
    if raw in ("open", "in_progress", "fixed", "ignored"):
        return raw
    return "open"


def _format_location(issue: dict[str, Any]) -> str:
    """Định dạng vị trí tệp và dòng dạng filename.py:42."""
    file_path = str(issue.get("file_path") or issue.get("file") or "").strip()
    line_no = issue.get("line_number")
    if line_no is None:
        line_no = issue.get("line")
    if line_no is not None and str(line_no).strip():
        return f"{file_path}:{line_no}"
    return file_path or "—"


class IssueTableModel(QAbstractTableModel):
    """
    Model bảng dữ liệu danh sách lỗi (IssueTableModel).

    Quản lý 5 cột chuẩn:
    0: Tệp : Dòng (font monospace)
    1: Mức độ (Critical, High, Medium, Low với màu SEV_*)
    2: Trạng thái (● Chưa sửa, ● Đang sửa, ● Đã sửa, ● Báo sai với màu STATUS_*)
    3: Công cụ (Bandit, Pylint, Radon, Pip-audit, Manual)
    4: Mô tả tóm tắt (Tiêu đề lỗi hoặc thông điệp cảnh báo)
    """

    def __init__(self, issues: list[dict[str, Any]] | None = None) -> None:
        super().__init__()
        self._issues: list[dict[str, Any]] = list(issues or [])
        self._font_code: QFont = lay_font_code(11)

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:  # pylint: disable=invalid-name
        """Số dòng dữ liệu trong bảng."""
        if parent.isValid():
            return 0
        return len(self._issues)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:  # pylint: disable=invalid-name
        """Số cột dữ liệu cố định (5 cột)."""
        if parent.isValid():
            return 0
        return len(_HEADERS)

    def headerData(  # pylint: disable=invalid-name
        self,
        section: int,
        orientation: Qt.Orientation,
        role: int = Qt.ItemDataRole.DisplayRole,
    ) -> Any:
        """Tiêu đề các cột dữ liệu."""
        if orientation == Qt.Orientation.Horizontal and role == Qt.ItemDataRole.DisplayRole:
            if 0 <= section < len(_HEADERS):
                return _HEADERS[section]
        return None

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        """Cung cấp dữ liệu, màu sắc và phông chữ cho từng ô."""
        if not index.isValid() or not 0 <= index.row() < len(self._issues):
            return None

        issue = self._issues[index.row()]
        col = index.column()
        result: Any = None

        if role == Qt.ItemDataRole.DisplayRole:
            result = self._get_display_data(issue, col)
        elif role == Qt.ItemDataRole.ForegroundRole:
            result = self._get_foreground_color(issue, col)
        elif role == Qt.ItemDataRole.FontRole and col == 0:
            result = self._font_code
        elif role == Qt.ItemDataRole.UserRole:
            result = issue
        elif role == Qt.ItemDataRole.ToolTipRole:
            result = str(issue.get("message") or "")

        return result

    @staticmethod
    def _get_display_data(issue: dict[str, Any], col: int) -> str:
        """Trích xuất chuỗi hiển thị theo cột."""
        extractors = (
            _format_location,
            lambda it: _normalize_severity(it.get("severity")),
            lambda it: _STATUS_DISPLAY_MAP.get(_normalize_status(it.get("status")), "● Chưa sửa"),
            lambda it: _TOOL_DISPLAY_MAP.get(
                str(it.get("tool") or "").strip().lower(),
                str(it.get("tool") or "").capitalize(),
            ),
            lambda it: (str(it.get("message") or "").strip().splitlines() or [""])[0],
        )
        if 0 <= col < len(extractors):
            return extractors[col](issue)
        return ""

    @staticmethod
    def _get_foreground_color(issue: dict[str, Any], col: int) -> QColor | None:
        """Lấy màu chữ theo mức độ hoặc trạng thái lỗi."""
        if col == 1:
            sev_title = _normalize_severity(issue.get("severity"))
            return QColor(SEVERITY_COLORS.get(sev_title, TEXT_MAIN))
        if col == 2:
            st_key = _normalize_status(issue.get("status"))
            color_map = {
                "open": STATUS_OPEN,
                "in_progress": STATUS_IN_PROGRESS,
                "fixed": STATUS_FIXED,
                "ignored": STATUS_IGNORED,
            }
            return QColor(color_map.get(st_key, TEXT_MAIN))
        return None

    def set_issues(self, issues: list[dict[str, Any]]) -> None:
        """Cập nhật toàn bộ danh sách lỗi và vẽ lại bảng."""
        self.beginResetModel()
        self._issues = list(issues)
        self.endResetModel()

    def get_issues(self) -> list[dict[str, Any]]:
        """Lấy danh sách lỗi hiện tại."""
        return list(self._issues)

    def get_issue(self, row: int) -> dict[str, Any] | None:
        """Lấy bản ghi lỗi tại vị trí dòng chỉ định."""
        if 0 <= row < len(self._issues):
            return self._issues[row]
        return None

    def update_issue_fields(
        self,
        issue_id: int,
        status: str | None = None,
        note: str | None = None,
    ) -> bool:
        """Cập nhật trường trạng thái hoặc ghi chú của lỗi theo ID."""
        for row_idx, item in enumerate(self._issues):
            curr_id = item.get("id") if item.get("id") is not None else item.get("issue_id")
            if curr_id == issue_id:
                if status is not None:
                    item["status"] = _normalize_status(status)
                if note is not None:
                    item["note"] = note
                top_left = self.index(row_idx, 0)
                bottom_right = self.index(row_idx, len(_HEADERS) - 1)
                self.dataChanged.emit(top_left, bottom_right)
                return True
        return False

    def remove_issue(self, issue_id: int) -> bool:
        """Xóa một lỗi khỏi danh sách dữ liệu."""
        for row_idx, item in enumerate(self._issues):
            curr_id = item.get("id") if item.get("id") is not None else item.get("issue_id")
            if curr_id == issue_id:
                self.beginRemoveRows(QModelIndex(), row_idx, row_idx)
                self._issues.pop(row_idx)
                self.endRemoveRows()
                return True
        return False


class IssueFilterProxyModel(QSortFilterProxyModel):
    """
    Bộ lọc đa tiêu chí thời gian thực cho danh sách lỗi.

    Hỗ trợ lọc đồng thời theo: Mức độ, Trạng thái, Công cụ và Từ khóa tìm kiếm.
    """

    def __init__(self, parent: Any = None) -> None:
        super().__init__(parent)
        self._filter_severity: str = "all"
        self._filter_status: str = "all"
        self._filter_tool: str = "all"
        self._filter_text: str = ""

    def set_severity_filter(self, severity: str) -> None:
        """Thiết lập bộ lọc mức độ ('all', 'critical', 'high', 'medium', 'low')."""
        norm = str(severity or "all").strip().lower()
        if self._filter_severity != norm:
            self._filter_severity = norm
            self.invalidateFilter()

    def set_status_filter(self, status: str) -> None:
        """Thiết lập bộ lọc trạng thái ('all', 'open', 'in_progress', 'fixed', 'ignored')."""
        norm = _normalize_status(status) if status != "all" else "all"
        if self._filter_status != norm:
            self._filter_status = norm
            self.invalidateFilter()

    def set_tool_filter(self, tool: str) -> None:
        """Thiết lập bộ lọc công cụ ('all', 'bandit', 'pylint', 'radon', 'pip-audit', 'manual')."""
        norm = str(tool or "all").strip().lower().replace("_", "-")
        if self._filter_tool != norm:
            self._filter_tool = norm
            self.invalidateFilter()

    def set_search_text(self, text: str) -> None:
        """Thiết lập từ khóa tìm kiếm (lọc theo file, mã lỗi hoặc mô tả)."""
        norm = str(text or "").strip().lower()
        if self._filter_text != norm:
            self._filter_text = norm
            self.invalidateFilter()

    def filterAcceptsRow(  # pylint: disable=invalid-name
        self,
        source_row: int,
        source_parent: QModelIndex,
    ) -> bool:
        """Đánh giá xem dòng dữ liệu nguồn có thỏa mãn toàn bộ bộ lọc hay không."""
        source_model = self.sourceModel()
        if not source_model:
            return False

        idx = source_model.index(source_row, 0, source_parent)
        issue = source_model.data(idx, Qt.ItemDataRole.UserRole)
        if not isinstance(issue, dict):
            return False

        return (
            self._matches_severity(issue)
            and self._matches_status(issue)
            and self._matches_tool(issue)
            and self._matches_search(issue)
        )

    def _matches_severity(self, issue: dict[str, Any]) -> bool:
        """Kiểm tra điều kiện lọc mức độ nghiêm trọng."""
        if self._filter_severity == "all":
            return True
        raw_sev = str(issue.get("severity") or "").strip().lower()
        return raw_sev == self._filter_severity

    def _matches_status(self, issue: dict[str, Any]) -> bool:
        """Kiểm tra điều kiện lọc trạng thái."""
        if self._filter_status == "all":
            return True
        st = _normalize_status(issue.get("status"))
        return st == self._filter_status

    def _matches_tool(self, issue: dict[str, Any]) -> bool:
        """Kiểm tra điều kiện lọc công cụ phát hiện."""
        if self._filter_tool == "all":
            return True
        tool = str(issue.get("tool") or "").strip().lower().replace("_", "-")
        return tool == self._filter_tool

    def _matches_search(self, issue: dict[str, Any]) -> bool:
        """Kiểm tra điều kiện từ khóa tìm kiếm."""
        if not self._filter_text:
            return True
        file_path = str(issue.get("file_path") or "").lower()
        msg = str(issue.get("message") or "").lower()
        rule = str(issue.get("rule_code") or "").lower()
        tool = str(issue.get("tool") or "").lower()
        return (
            self._filter_text in file_path
            or self._filter_text in msg
            or self._filter_text in rule
            or self._filter_text in tool
        )

    def lessThan(self, left: QModelIndex, right: QModelIndex) -> bool:  # pylint: disable=invalid-name
        """Hỗ trợ sắp xếp thông minh theo mức độ nghiêm trọng hoặc chuỗi ký tự."""
        if left.column() == 1:
            src = self.sourceModel()
            issue_l = src.data(left, Qt.ItemDataRole.UserRole) if src else None
            issue_r = src.data(right, Qt.ItemDataRole.UserRole) if src else None
            if isinstance(issue_l, dict) and isinstance(issue_r, dict):
                sev_ranks = {"critical": 0, "high": 1, "medium": 2, "low": 3}
                rank_l = sev_ranks.get(str(issue_l.get("severity", "")).lower(), 9)
                rank_r = sev_ranks.get(str(issue_r.get("severity", "")).lower(), 9)
                return rank_l < rank_r
        return super().lessThan(left, right)


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


class IssuesView(QWidget):  # pylint: disable=too-many-instance-attributes
    """
    Màn hình Quản lý Lỗi mã nguồn (IssuesView).

    Điều phối toàn bộ bảng danh sách lỗi, chi tiết lỗi, thao tác đổi trạng thái,
    ghi chú và xóa lỗi theo thời gian thực.
    """

    status_message = pyqtSignal(str)
    issue_updated = pyqtSignal(int)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._session_id: int | None = None
        self._selected_issue: dict[str, Any] | None = None
        self._active_worker: RequestWorker | None = None
        self._active_workers: list[RequestWorker] = []

        self._table_model = IssueTableModel()
        self._proxy_model = IssueFilterProxyModel(self)
        self._proxy_model.setSourceModel(self._table_model)

        self.combo_filter_sev = QComboBox()
        self.combo_filter_status = QComboBox()
        self.combo_filter_tool = QComboBox()
        self.search_input = QLineEdit()
        self.btn_add_issue = QPushButton("Thêm lỗi")

        self.table_view = QTableView()
        self.empty_state = EmptyState(
            title="Không tìm thấy lỗi nào",
            description="Không có lỗi nào khớp với bộ lọc hiện tại hoặc dự án chưa có lỗi.",
        )
        self.table_stack = QStackedLayout()

        self.lbl_detail_location = QLabel("—")
        self.badge_severity = SeverityBadge("Medium")
        self.lbl_detail_rule = QLabel("—")
        self.txt_detail_desc = QTextEdit()
        self.combo_detail_status = QComboBox()
        self.edit_detail_note = QLineEdit()
        self.btn_save_note = QPushButton("Lưu ghi chú")

        self.inline_notice = InlineNotice(parent=self)
        self.inline_notice.setVisible(False)
        self._detail_stack: QStackedLayout | None = None

        self._init_ui()
        self._setup_shortcuts()

    def _init_ui(self) -> None:
        """Xây dựng bố cục giao diện hoàn chỉnh theo chuẩn ArtCraft."""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(32, 28, 32, 24)
        main_layout.setSpacing(16)

        # 1. Tiêu đề màn hình chuẩn PageHeader
        header = PageHeader(
            title="Lỗi phát hiện",
            subtitle="Chi tiết các vi phạm quy chuẩn, độ phức tạp và lỗ hổng bảo mật",
            parent=self,
        )
        self.btn_add_issue.setProperty("role", "primary")
        self.btn_add_issue.setText("+ Thêm lỗi")
        self.btn_add_issue.clicked.connect(self._on_add_issue_clicked)
        header.them_nut_phai(self.btn_add_issue)
        main_layout.addWidget(header)

        main_layout.addWidget(self.inline_notice)
        main_layout.addLayout(self._create_toolbar())

        splitter = QSplitter(Qt.Orientation.Vertical)
        splitter.setChildrenCollapsible(False)

        table_container = self._create_table_container()
        detail_container = self._create_detail_panel()

        splitter.addWidget(table_container)
        splitter.addWidget(detail_container)
        splitter.setSizes([550, 350])
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)

        main_layout.addWidget(splitter, 1)

    def _create_toolbar(self) -> QHBoxLayout:
        """Tạo thanh công cụ trên cùng với các bộ lọc theo chuẩn ArtCraft."""
        layout = QHBoxLayout()
        layout.setSpacing(10)

        lbl_sev = QLabel("Mức:")
        lbl_sev.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 13px;")
        self.combo_filter_sev.addItems(
            ["Tất cả", "Nghiêm trọng", "Cao", "Trung bình", "Thấp"]
        )
        self.combo_filter_sev.setItemData(0, "all")
        self.combo_filter_sev.setItemData(1, "critical")
        self.combo_filter_sev.setItemData(2, "high")
        self.combo_filter_sev.setItemData(3, "medium")
        self.combo_filter_sev.setItemData(4, "low")
        self.combo_filter_sev.currentIndexChanged.connect(self._on_filter_changed)

        lbl_status = QLabel("Trạng thái:")
        lbl_status.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 13px;")
        self.combo_filter_status.addItems(
            ["Tất cả", "Chưa sửa", "Đang sửa", "Đã sửa", "Báo sai"]
        )
        self.combo_filter_status.setItemData(0, "all")
        self.combo_filter_status.setItemData(1, "open")
        self.combo_filter_status.setItemData(2, "in_progress")
        self.combo_filter_status.setItemData(3, "fixed")
        self.combo_filter_status.setItemData(4, "ignored")
        self.combo_filter_status.currentIndexChanged.connect(self._on_filter_changed)

        lbl_tool = QLabel("Công cụ:")
        lbl_tool.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 13px;")
        self.combo_filter_tool.addItems(
            ["Tất cả", "Bandit", "Pylint", "Radon", "Pip-audit", "Thủ công"]
        )
        self.combo_filter_tool.setItemData(0, "all")
        self.combo_filter_tool.setItemData(1, "bandit")
        self.combo_filter_tool.setItemData(2, "pylint")
        self.combo_filter_tool.setItemData(3, "radon")
        self.combo_filter_tool.setItemData(4, "pip-audit")
        self.combo_filter_tool.setItemData(5, "manual")
        self.combo_filter_tool.currentIndexChanged.connect(self._on_filter_changed)

        self.search_input.setPlaceholderText(
            "Tìm kiếm theo tệp, mã kiểm thử hoặc mô tả... (Ctrl+F)"
        )
        self.search_input.setClearButtonEnabled(True)
        self.search_input.textChanged.connect(self._on_search_changed)

        layout.addWidget(lbl_sev)
        layout.addWidget(self.combo_filter_sev)
        layout.addWidget(lbl_status)
        layout.addWidget(self.combo_filter_status)
        layout.addWidget(lbl_tool)
        layout.addWidget(self.combo_filter_tool)
        layout.addWidget(self.search_input, 1)

        return layout

    def _create_table_container(self) -> QWidget:
        """Tạo khung chứa bảng danh sách lỗi kết hợp EmptyState qua QStackedLayout."""
        container = QWidget()
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(0)

        self.table_view.setModel(self._proxy_model)
        chuan_hoa_bang(self.table_view, cot_gian=4, cot_so=())
        self.table_view.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.table_view.setSortingEnabled(True)
        self.table_view.sortByColumn(1, Qt.SortOrder.AscendingOrder)
        self.table_view.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table_view.customContextMenuRequested.connect(self._on_table_context_menu)

        selection_model = self.table_view.selectionModel()
        if selection_model:
            selection_model.selectionChanged.connect(self._on_selection_changed)

        table_panel = Panel(self)
        panel_layout = QVBoxLayout(table_panel)
        panel_layout.setContentsMargins(0, 0, 0, 0)
        panel_layout.addWidget(self.table_view)

        self.table_stack.addWidget(table_panel)
        self.table_stack.addWidget(self.empty_state)
        container_layout.addLayout(self.table_stack)

        return container

    def _create_detail_placeholder(self, parent: QWidget) -> QWidget:
        """Tạo trang thông điệp hướng dẫn khi chưa chọn lỗi nào trên bảng."""
        placeholder = QWidget(parent)
        ph_layout = QVBoxLayout(placeholder)
        ph_layout.setContentsMargins(20, 24, 20, 24)
        ph_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_hint = QLabel(
            "Chọn một dòng lỗi trên bảng để xem chi tiết và khuyến nghị sửa chữa.",
            placeholder,
        )
        lbl_hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_hint.setStyleSheet(
            f"color: {TEXT_MUTED}; font-size: 13px; font-weight: 500; border: none;"
        )
        ph_layout.addWidget(lbl_hint)
        return placeholder

    def _create_detail_form(self, parent: QWidget) -> QWidget:
        """Tạo trang form chi tiết khi đã chọn một lỗi."""
        detail_form = QWidget(parent)
        layout = QVBoxLayout(detail_form)
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
        layout.addWidget(self.txt_detail_desc, 1)

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
        self.btn_save_note.clicked.connect(self._on_save_detail_note)

        status_bar_layout.addWidget(lbl_status)
        status_bar_layout.addWidget(self.combo_detail_status)
        status_bar_layout.addWidget(lbl_note)
        status_bar_layout.addWidget(self.edit_detail_note, 1)
        status_bar_layout.addWidget(self.btn_save_note)

        layout.addLayout(status_bar_layout)
        return detail_form

    def _create_detail_panel(self) -> QFrame:
        """Tạo khung chi tiết lỗi (Detail Panel) bên dưới QSplitter."""
        panel = QFrame()
        panel.setStyleSheet(
            f"QFrame {{ background-color: {SURFACE}; border: 1px solid {BORDER}; "
            f"border-radius: 4px; }}"
        )
        self._detail_stack = QStackedLayout(panel)
        self._detail_stack.setContentsMargins(0, 0, 0, 0)

        # 1. Trang hướng dẫn khi chưa chọn lỗi (Placeholder)
        placeholder = self._create_detail_placeholder(panel)
        self._detail_stack.addWidget(placeholder)  # Index 0

        # 2. Trang hiển thị chi tiết khi đã chọn lỗi (Form)
        detail_form = self._create_detail_form(panel)
        self._detail_stack.addWidget(detail_form)  # Index 1

        self._detail_stack.setCurrentIndex(0)
        return panel

    def _setup_shortcuts(self) -> None:
        """Thiết lập phím tắt Ctrl+F và phím Delete."""
        shortcut_find = QShortcut(QKeySequence("Ctrl+F"), self)
        shortcut_find.activated.connect(self._focus_search)

        shortcut_del = QShortcut(QKeySequence("Delete"), self.table_view)
        shortcut_del.activated.connect(self._on_delete_selected_issues)

    def _focus_search(self) -> None:
        """Đưa con trỏ vào ô tìm kiếm và bôi đen toàn bộ."""
        self.search_input.setFocus()
        self.search_input.selectAll()

    def _on_filter_changed(self) -> None:
        """Kích hoạt cập nhật bộ lọc đa tiêu chí."""
        sev = self.combo_filter_sev.currentData() or "all"
        status = self.combo_filter_status.currentData() or "all"
        tool = self.combo_filter_tool.currentData() or "all"

        self._proxy_model.set_severity_filter(sev)
        self._proxy_model.set_status_filter(status)
        self._proxy_model.set_tool_filter(tool)
        self._update_table_stack()

    def _on_search_changed(self, text: str) -> None:
        """Cập nhật từ khóa tìm kiếm."""
        self._proxy_model.set_search_text(text)
        self._update_table_stack()

    def _update_table_stack(self) -> None:
        """Chuyển đổi giữa bảng dữ liệu và trạng thái rỗng khi không có dòng nào."""
        if self._proxy_model.rowCount() == 0:
            self.table_stack.setCurrentIndex(1)
            self._clear_detail_panel()
        else:
            self.table_stack.setCurrentIndex(0)

    def _on_selection_changed(
        self,
        _selected: QItemSelection,
        _deselected: QItemSelection,
    ) -> None:
        """Cập nhật khung chi tiết khi người dùng chọn dòng trên bảng."""
        indexes = self.table_view.selectionModel().selectedRows()
        if not indexes:
            self._clear_detail_panel()
            return

        proxy_index = indexes[0]
        source_index = self._proxy_model.mapToSource(proxy_index)
        issue = self._table_model.data(source_index, Qt.ItemDataRole.UserRole)
        if isinstance(issue, dict):
            self._display_issue_detail(issue)

    def _display_issue_detail(self, issue: dict[str, Any]) -> None:
        """Hiển thị thông tin chi tiết một lỗi vào panel dưới."""
        if self._detail_stack is not None:
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
        self.txt_detail_desc.setPlainText(desc)

        curr_status = _normalize_status(issue.get("status"))
        idx = self.combo_detail_status.findData(curr_status)
        if idx >= 0:
            self.combo_detail_status.setCurrentIndex(idx)

        self.edit_detail_note.setText(str(issue.get("note") or ""))

    def _clear_detail_panel(self) -> None:
        """Xóa trắng nội dung khung chi tiết."""
        if self._detail_stack is not None:
            self._detail_stack.setCurrentIndex(0)
        self._selected_issue = None
        self.lbl_detail_location.setText("—")
        self.badge_severity.set_severity("Medium")
        self.lbl_detail_rule.setText("—")
        self.txt_detail_desc.clear()
        self.edit_detail_note.clear()

    def _on_save_detail_note(self) -> None:
        """Lưu trạng thái và ghi chú từ panel chi tiết xuống cơ sở dữ liệu."""
        if not self._selected_issue:
            self.status_message.emit("Chưa chọn lỗi để cập nhật.")
            return

        issue_id = self._selected_issue.get("id") or self._selected_issue.get("issue_id")
        new_status = self.combo_detail_status.currentData() or "open"
        new_note = self.edit_detail_note.text().strip()

        if issue_id is None or self._session_id is None:
            target_id = int(issue_id) if issue_id is not None else 0
            self._table_model.update_issue_fields(
                issue_id=target_id,
                status=new_status,
                note=new_note,
            )
            self._selected_issue["status"] = new_status
            self._selected_issue["note"] = new_note
            self.status_message.emit("Đã lưu ghi chú lỗi (chế độ độc lập).")
            return

        self._execute_update_issue(int(issue_id), new_status, new_note)

    def _execute_update_issue(self, issue_id: int, status: str, note: str | None) -> None:
        """Gửi yêu cầu cập nhật lỗi qua RequestWorker."""
        self.btn_save_note.setEnabled(False)

        worker = RequestWorker(api.update_issue_status, issue_id, status, note, parent=self)
        self._active_workers.append(worker)
        self._active_worker = worker

        def _cleanup() -> None:
            if worker in self._active_workers:
                self._active_workers.remove(worker)
            if not self._active_workers:
                self.btn_save_note.setEnabled(True)
                self._active_worker = None

        def _on_finished(_res: dict[str, Any]) -> None:
            _cleanup()
            self._table_model.update_issue_fields(issue_id, status, note)
            if self._selected_issue:
                self._selected_issue["status"] = status
                self._selected_issue["note"] = note
            self.status_message.emit("Đã cập nhật trạng thái lỗi thành công.")
            self.issue_updated.emit(issue_id)

        def _on_failed(err_msg: str) -> None:
            _cleanup()
            self.inline_notice.show_notice(
                f"Lỗi khi cập nhật trạng thái: {err_msg}",
                notice_type="error",
            )
            self.status_message.emit("Cập nhật lỗi thất bại.")

        worker.finished.connect(_on_finished)
        worker.failed.connect(_on_failed)
        worker.start()

    def _on_table_context_menu(self, pos: Any) -> None:
        """Hiển thị menu ngữ cảnh chuột phải trên bảng dữ liệu."""
        selected_rows = self.table_view.selectionModel().selectedRows()
        if not selected_rows:
            return

        menu = QMenu(self)

        status_menu = menu.addMenu("Chuyển trạng thái sang")
        act_open = status_menu.addAction("Chưa sửa")
        act_in_progress = status_menu.addAction("Đang sửa")
        act_fixed = status_menu.addAction("Đã sửa")
        act_ignored = status_menu.addAction("Báo sai")

        act_open.triggered.connect(lambda: self._batch_update_status("open"))
        act_in_progress.triggered.connect(lambda: self._batch_update_status("in_progress"))
        act_fixed.triggered.connect(lambda: self._batch_update_status("fixed"))
        act_ignored.triggered.connect(lambda: self._batch_update_status("ignored"))

        menu.addSeparator()
        act_delete = menu.addAction("Xóa lỗi đã chọn")
        act_delete.triggered.connect(self._on_delete_selected_issues)

        global_pos = self.table_view.viewport().mapToGlobal(pos)
        menu.exec(global_pos)

    def _batch_update_status(self, new_status: str) -> None:
        """Cập nhật trạng thái hàng loạt cho các dòng đang chọn."""
        selected_rows = self.table_view.selectionModel().selectedRows()
        if not selected_rows:
            return

        for proxy_index in selected_rows:
            source_index = self._proxy_model.mapToSource(proxy_index)
            issue = self._table_model.data(source_index, Qt.ItemDataRole.UserRole)
            if isinstance(issue, dict):
                issue_id = issue.get("id") or issue.get("issue_id")
                if issue_id is not None and self._session_id is not None:
                    self._execute_update_issue(int(issue_id), new_status, issue.get("note"))
                else:
                    issue["status"] = new_status
                    target_id = int(issue_id) if issue_id is not None else 0
                    self._table_model.update_issue_fields(target_id, new_status)

        self.status_message.emit(f"Đã cập nhật trạng thái cho {len(selected_rows)} lỗi.")

    def _on_delete_selected_issues(self) -> None:
        """Xác nhận và xóa các lỗi đang được chọn."""
        selected_rows = self.table_view.selectionModel().selectedRows()
        if not selected_rows:
            return

        confirm = QMessageBox.question(
            self,
            "Xác nhận xóa lỗi",
            f"Bạn có chắc chắn muốn xóa {len(selected_rows)} lỗi đã chọn khỏi hệ thống?\n"
            "Thao tác này sẽ xóa vĩnh viễn dữ liệu và không thể hoàn tác.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return

        target_ids: list[int] = []
        api_issue_ids: list[int] = []
        for proxy_index in reversed(selected_rows):
            issue = self._table_model.data(
                self._proxy_model.mapToSource(proxy_index), Qt.ItemDataRole.UserRole
            )
            if isinstance(issue, dict):
                raw_id = issue.get("id") or issue.get("issue_id")
                if raw_id is not None:
                    target_ids.append(int(raw_id))
                    if self._session_id is not None:
                        api_issue_ids.append(int(raw_id))
                else:
                    target_ids.append(0)

        for tid in target_ids:
            self._table_model.remove_issue(tid)

        self._update_table_stack()

        if api_issue_ids:
            def _delete_job() -> dict[str, Any]:
                for iid in api_issue_ids:
                    api.delete_issue(iid)
                return {"status": "ok", "deleted_count": len(api_issue_ids)}

            worker = RequestWorker(_delete_job, parent=self)
            self._active_workers.append(worker)
            self._active_worker = worker

            def _on_done(_res: dict[str, Any] | None = None) -> None:
                if worker in self._active_workers:
                    self._active_workers.remove(worker)
                if not self._active_workers:
                    self._active_worker = None
                self.status_message.emit(
                    f"Đã xóa thành công {len(selected_rows)} lỗi khỏi phiên quét."
                )

            def _on_error(err_msg: str) -> None:
                if worker in self._active_workers:
                    self._active_workers.remove(worker)
                if not self._active_workers:
                    self._active_worker = None
                self.inline_notice.show_notice(
                    f"Lỗi khi xóa lỗi trên máy chủ: {err_msg}",
                    notice_type="error",
                )
                self.status_message.emit("Xóa lỗi thất bại.")

            worker.finished.connect(_on_done)
            worker.failed.connect(_on_error)
            worker.start()
        else:
            self.status_message.emit(
                f"Đã xóa thành công {len(selected_rows)} lỗi khỏi phiên quét."
            )

    def _on_add_issue_clicked(self) -> None:
        """Mở hộp thoại thêm lỗi thủ công và lưu vào CSDL."""
        dialog = ManualIssueDialog(self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        issue_data = dialog.get_issue_data()

        if self._session_id is not None:
            worker = RequestWorker(
                api.create_manual_issue,
                self._session_id,
                issue_data["file_path"],
                issue_data["line_number"],
                issue_data["severity"],
                issue_data["message"],
                issue_data.get("note"),
                parent=self,
            )
            self._active_worker = worker

            def _on_created(res: dict[str, Any]) -> None:
                new_id = res.get("data", {}).get("issue_id", 0)
                issue_data["id"] = new_id
                current_list = self._table_model.get_issues()
                current_list.insert(0, issue_data)
                self._table_model.set_issues(current_list)
                self._update_table_stack()
                self.status_message.emit("Đã thêm lỗi thủ công thành công.")
                self.issue_updated.emit(new_id)

            def _on_failed(err_msg: str) -> None:
                self.inline_notice.show_notice(
                    f"Không thể lưu lỗi thủ công: {err_msg}",
                    notice_type="error",
                )

            worker.finished.connect(_on_created)
            worker.failed.connect(_on_failed)
            worker.start()
        else:
            issue_data["id"] = 999
            current_list = self._table_model.get_issues()
            current_list.insert(0, issue_data)
            self._table_model.set_issues(current_list)
            self._update_table_stack()
            self.status_message.emit("Đã thêm lỗi thủ công (chế độ độc lập).")

    def load_session_issues(self, session_id: int) -> None:
        """Tải danh sách lỗi thuộc một phiên phân tích từ Backend qua RequestWorker."""
        self._session_id = session_id
        self.inline_notice.setVisible(False)

        worker = RequestWorker(api.list_issues, session_id, parent=self)
        self._active_worker = worker

        def _on_loaded(res: dict[str, Any]) -> None:
            issues = res.get("data")
            if isinstance(issues, list):
                self._table_model.set_issues(issues)
                self._update_table_stack()
                self.status_message.emit(f"Đã tải {len(issues)} lỗi phát hiện.")

        def _on_failed(err_msg: str) -> None:
            self.inline_notice.show_notice(
                f"Lỗi khi tải danh sách lỗi: {err_msg}",
                notice_type="error",
                action_text="Thử lại",
            )
            self.inline_notice.retry_clicked.connect(lambda: self.load_session_issues(session_id))
            self.status_message.emit("Không thể tải danh sách lỗi.")

        worker.finished.connect(_on_loaded)
        worker.failed.connect(_on_failed)
        worker.start()

    def set_issues(self, issues: list[dict[str, Any]], session_id: int | None = None) -> None:
        """Nạp trực tiếp danh sách lỗi vào màn hình."""
        self._session_id = session_id
        self._table_model.set_issues(issues)
        self._update_table_stack()

    def filter_by_file(self, file_path: str) -> None:
        """Thiết lập lọc theo đường dẫn tệp tin cụ thể."""
        self.search_input.setText(file_path)
        self._on_search_changed(file_path)


def _get_mock_issues() -> list[dict[str, Any]]:
    """Tạo 6 lỗi mẫu đa dạng đại diện cho các công cụ Bandit, Pylint, Pip-audit, Radon."""
    return [
        {
            "id": 1,
            "file_path": "backend/database/repositories/issue_repo.py",
            "line_number": 42,
            "severity": "critical",
            "status": "open",
            "tool": "bandit",
            "rule_code": "B608",
            "message": (
                "B608: Có nguy cơ SQL injection do nối chuỗi trực tiếp vào câu truy vấn.\n"
                "Khuyến nghị: Sử dụng tham số hóa câu truy vấn (%s) thay vì nối chuỗi."
            ),
            "note": "Cần refactor lại câu lệnh SQL để tránh SQL injection.",
        },
        {
            "id": 2,
            "file_path": "backend/config.py",
            "line_number": 18,
            "severity": "high",
            "status": "in_progress",
            "tool": "bandit",
            "rule_code": "B105",
            "message": (
                "B105: Phát hiện mật khẩu cơ sở dữ liệu hardcoded trực tiếp trong mã nguồn.\n"
                "Khuyến nghị: Chuyển toàn bộ bí mật vào file biến môi trường .env."
            ),
            "note": "Đang chuyển cấu hình sang nạp từ biến môi trường qua os.environ.",
        },
        {
            "id": 3,
            "file_path": "frontend/views/projects_view.py",
            "line_number": 112,
            "severity": "low",
            "status": "fixed",
            "tool": "pylint",
            "rule_code": "C0301",
            "message": (
                "C0301: Chiều dài dòng vượt quá giới hạn chuẩn 100 ký tự (108/100).\n"
                "Khuyến nghị: Xuống dòng hợp lý theo tiêu chuẩn PEP8."
            ),
            "note": "Đã ngắt dòng thành nhiều dòng ngắn hơn.",
        },
        {
            "id": 4,
            "file_path": "backend/analyzer/metrics.py",
            "line_number": 85,
            "severity": "medium",
            "status": "open",
            "tool": "radon",
            "rule_code": "RADON-CC",
            "message": (
                "Độ phức tạp chu trình (Cyclomatic Complexity) của "
                "hàm calculate_all là 18 (Bậc C).\n"
                "Khuyến nghị: Tách hàm thành các phương thức nhỏ hơn để tăng tính bảo trì."
            ),
            "note": None,
        },
        {
            "id": 5,
            "file_path": "requirements.txt",
            "line_number": 14,
            "severity": "high",
            "status": "open",
            "tool": "pip-audit",
            "rule_code": "CVE-2023-43804",
            "message": (
                "Thư viện urllib3 phiên bản 1.26.15 dính lỗ hổng Cookie Leakage (CVE-2023-43804).\n"
                "Khuyến nghị: Nâng cấp urllib3 lên phiên bản >= 1.26.17 hoặc >= 2.0.6."
            ),
            "note": "Đã tạo ticket phụ trách nâng cấp thư viện tuần tới.",
        },
        {
            "id": 6,
            "file_path": "backend/network/router.py",
            "line_number": 77,
            "severity": "medium",
            "status": "ignored",
            "tool": "manual",
            "rule_code": "SEC-CUSTOM-01",
            "message": (
                "Thiếu kiểm tra quyền hạn chi tiết khi gọi endpoint config.update.\n"
                "Khuyến nghị: Bổ sung lớp middleware kiểm tra token phiên làm việc."
            ),
            "note": "Báo sai: Môi trường mạng nội bộ hiện tại chưa yêu cầu phân quyền quản trị.",
        },
    ]


def main() -> None:
    """Hàm chạy thử độc lập màn hình Quản lý Lỗi (IssuesView) trong cửa sổ 1100x700."""
    app = QApplication(sys.argv)
    stylesheet = load_stylesheet()
    if stylesheet:
        app.setStyleSheet(stylesheet)

    view = IssuesView()
    view.setWindowTitle("Code Quality & Security Analyzer - Quản lý Lỗi")
    view.resize(1100, 700)

    mock_issues = _get_mock_issues()
    view.set_issues(mock_issues)

    view.status_message.connect(lambda msg: print(f"[Status] {msg}"))
    view.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
