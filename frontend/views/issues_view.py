"""Màn hình Quản lý Lỗi mã nguồn (IssuesView) theo chuẩn kỹ thuật SKILLS.md."""

import sys
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# pylint: disable=wrong-import-position,no-name-in-module
from PyQt6.QtCore import (
    QItemSelection,
    Qt,
    pyqtSignal,
)
from PyQt6.QtGui import (
    QKeySequence,
    QShortcut,
)
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMenu,
    QMessageBox,
    QPushButton,
    QSplitter,
    QStackedLayout,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from frontend.controllers.issue_controller import IssueController
from frontend.models.issue_model import (
    IssueFilterProxyModel,
    IssueTableModel,
)
from frontend.views.components.issue_detail_panel import IssueDetailPanel
from frontend.views.dialogs.manual_issue_dialog import ManualIssueDialog
from frontend.views.widgets.empty_state import EmptyState
from frontend.views.widgets.inline_notice import InlineNotice
from frontend.views.widgets.page_header import PageHeader
from frontend.views.widgets.panel import Panel
from frontend.views.widgets.pill_badge_delegate import PillBadgeDelegate
from frontend.views.widgets.table_utils import chuan_hoa_bang


class IssuesView(QWidget):  # pylint: disable=too-many-instance-attributes
    """
    Màn hình Quản lý Lỗi mã nguồn (IssuesView).

    Điều phối danh sách bảng lỗi, bộ lọc đa tiêu chí và panel chi tiết lỗi.
    """

    status_message = pyqtSignal(str)
    issue_updated = pyqtSignal(int)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._session_id: int | None = None

        self._controller = IssueController(self)
        self._controller.issues_loaded.connect(self._on_issues_loaded)
        self._controller.issue_updated.connect(self._on_issue_updated)
        self._controller.issues_deleted.connect(self._on_issues_deleted)
        self._controller.issue_created.connect(self._on_issue_created)
        self._controller.error_occurred.connect(self._on_issue_error)
        self._controller.status_message.connect(self.status_message.emit)

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
        self.detail_panel = IssueDetailPanel(self)

        self.inline_notice = InlineNotice(parent=self)
        self.inline_notice.setVisible(False)

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
        self.detail_panel.save_note_requested.connect(self._on_save_detail_note)

        splitter.addWidget(table_container)
        splitter.addWidget(self.detail_panel)
        splitter.setSizes([550, 350])
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)

        main_layout.addWidget(splitter, 1)

    def _create_toolbar(self) -> QHBoxLayout:
        """Khởi tạo thanh công cụ bộ lọc 3 cấp độ và thanh tìm kiếm thời gian thực."""
        layout = QHBoxLayout()
        layout.setSpacing(10)

        lbl_sev = QLabel("Mức:")
        self.combo_filter_sev.addItem("Tất cả", "all")
        self.combo_filter_sev.addItem("Critical", "critical")
        self.combo_filter_sev.addItem("High", "high")
        self.combo_filter_sev.addItem("Medium", "medium")
        self.combo_filter_sev.addItem("Low", "low")
        self.combo_filter_sev.currentIndexChanged.connect(self._on_filter_changed)

        lbl_status = QLabel("Trạng thái:")
        self.combo_filter_status.addItem("Tất cả", "all")
        self.combo_filter_status.addItem("Chưa sửa", "open")
        self.combo_filter_status.addItem("Đang sửa", "in_progress")
        self.combo_filter_status.addItem("Đã sửa", "fixed")
        self.combo_filter_status.addItem("Báo sai", "ignored")
        self.combo_filter_status.currentIndexChanged.connect(self._on_filter_changed)

        lbl_tool = QLabel("Công cụ:")
        self.combo_filter_tool.addItem("Tất cả", "all")
        self.combo_filter_tool.addItem("Bandit", "bandit")
        self.combo_filter_tool.addItem("Pylint", "pylint")
        self.combo_filter_tool.addItem("Radon", "radon")
        self.combo_filter_tool.addItem("Pip-audit", "pip-audit")
        self.combo_filter_tool.addItem("Mã độc & AST", "malware-ast")
        self.combo_filter_tool.addItem("Manual", "manual")
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
        self.table_view.setItemDelegateForColumn(1, PillBadgeDelegate("severity", self.table_view))
        self.table_view.setItemDelegateForColumn(2, PillBadgeDelegate("status", self.table_view))
        self.table_view.setItemDelegateForColumn(3, PillBadgeDelegate("tool", self.table_view))
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
            self.detail_panel.clear()
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
            self.detail_panel.clear()
            return

        proxy_index = indexes[0]
        source_index = self._proxy_model.mapToSource(proxy_index)
        issue = self._table_model.data(source_index, Qt.ItemDataRole.UserRole)
        if isinstance(issue, dict):
            self.detail_panel.display_issue(issue)

    def _on_save_detail_note(self, issue_id: int, status: str, note: str | None) -> None:
        """Gửi yêu cầu cập nhật lỗi qua Controller."""
        if self._session_id is not None:
            self.detail_panel.set_save_enabled(False)
            self._controller.update_issue(issue_id, status, note)
        else:
            selected = self.detail_panel.get_selected_issue()
            if selected:
                selected["status"] = status
                selected["note"] = note
            self._table_model.update_issue_fields(issue_id, status, note)
            self.status_message.emit("Đã lưu ghi chú lỗi (chế độ độc lập).")

    def _on_issue_updated(self, issue_id: int, status: str, note: str | None) -> None:
        """Xử lý giao diện khi cập nhật thông tin lỗi thành công."""
        self.detail_panel.set_save_enabled(True)
        self._table_model.update_issue_fields(issue_id, status, note)
        self.issue_updated.emit(issue_id)

    def _on_issue_error(self, err_msg: str) -> None:
        """Hiển thị thông báo lỗi trên giao diện."""
        self.detail_panel.set_save_enabled(True)
        self.inline_notice.show_notice(
            f"Lỗi thao tác: {err_msg}",
            notice_type="error",
        )

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
        """Cập nhật trạng thái hàng loạt cho các dòng đang chọn qua Controller."""
        selected_rows = self.table_view.selectionModel().selectedRows()
        if not selected_rows:
            return

        api_issue_ids: list[int] = []
        for proxy_index in selected_rows:
            source_index = self._proxy_model.mapToSource(proxy_index)
            issue = self._table_model.data(source_index, Qt.ItemDataRole.UserRole)
            if isinstance(issue, dict):
                issue_id = issue.get("id") or issue.get("issue_id")
                if issue_id is not None and self._session_id is not None:
                    api_issue_ids.append(int(issue_id))
                else:
                    issue["status"] = new_status
                    target_id = int(issue_id) if issue_id is not None else 0
                    self._table_model.update_issue_fields(target_id, new_status)

        if api_issue_ids:
            self._controller.batch_update_status(api_issue_ids, new_status)
        else:
            self.status_message.emit(f"Đã cập nhật trạng thái cho {len(selected_rows)} lỗi.")

    def _on_delete_selected_issues(self) -> None:
        """Xác nhận và xóa các lỗi đang được chọn qua Controller."""
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
        for proxy_index in reversed(selected_rows):
            issue = self._table_model.data(
                self._proxy_model.mapToSource(proxy_index), Qt.ItemDataRole.UserRole
            )
            if isinstance(issue, dict):
                raw_id = issue.get("id") or issue.get("issue_id")
                if raw_id is not None:
                    target_ids.append(int(raw_id))
                else:
                    target_ids.append(0)

        for tid in target_ids:
            self._table_model.remove_issue(tid)

        self._update_table_stack()

        if self._session_id is not None and target_ids:
            self._controller.delete_issues(target_ids)
        else:
            self.status_message.emit(
                f"Đã xóa thành công {len(selected_rows)} lỗi khỏi phiên quét."
            )

    def _on_issues_deleted(self, deleted_ids: list[int]) -> None:
        """Cập nhật giao diện sau khi Controller hoàn tất xóa lỗi."""
        for did in deleted_ids:
            self._table_model.remove_issue(did)
        self._update_table_stack()

    def _on_add_issue_clicked(self) -> None:
        """Mở hộp thoại thêm lỗi thủ công và lưu vào CSDL qua Controller."""
        dialog = ManualIssueDialog(self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        issue_data = dialog.get_issue_data()
        if self._session_id is not None:
            self._controller.create_manual_issue(self._session_id, issue_data)
        else:
            issue_data["id"] = 999
            current_list = self._table_model.get_issues()
            current_list.insert(0, issue_data)
            self._table_model.set_issues(current_list)
            self._update_table_stack()
            self.status_message.emit("Đã thêm lỗi thủ công (chế độ độc lập).")

    def _on_issue_created(self, issue_data: dict[str, Any]) -> None:
        """Cập nhật danh sách lỗi trên bảng sau khi tạo thành công."""
        new_id = issue_data.get("id") or issue_data.get("issue_id", 0)
        self.issue_updated.emit(int(new_id))

    def load_session_issues(self, session_id: int) -> None:
        """Kích hoạt Controller nạp danh sách lỗi của phiên phân tích."""
        self._session_id = session_id
        self.inline_notice.setVisible(False)
        self._controller.load_session_issues(session_id)

    def _on_issues_loaded(self, issues: list[dict[str, Any]], _session_id: int) -> None:
        """Cập nhật dữ liệu lỗi vào bảng khi nạp thành công từ Controller."""
        self._table_model.set_issues(issues)
        self._update_table_stack()

    def set_issues(self, issues: list[dict[str, Any]], session_id: int | None = None) -> None:
        """Nạp trực tiếp danh sách lỗi vào màn hình."""
        self._session_id = session_id
        self._table_model.set_issues(issues)
        self._update_table_stack()

    def filter_by_file(self, file_path: str) -> None:
        """Thiết lập lọc theo đường dẫn tệp tin cụ thể."""
        self.search_input.setText(file_path)
        self._on_search_changed(file_path)
