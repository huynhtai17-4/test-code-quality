"""Màn hình Quản lý Dự án (ProjectsView) và các thành phần liên quan theo chuẩn SKILLS.md."""

import sys
from pathlib import Path
from typing import Any

# Đảm bảo đường dẫn import hoạt động từ thư mục gốc
ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# pylint: disable=wrong-import-position,no-name-in-module
from PyQt6.QtCore import QModelIndex, Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMenu,
    QMessageBox,
    QPushButton,
    QStackedLayout,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from frontend.models.project_model import (
    ProjectFilterProxyModel,
    ProjectTableModel,
)
from frontend.controllers.project_controller import ProjectController
from frontend.views.dialogs.project_dialog import ProjectDialog
from frontend.views.theme import TEXT_MUTED
from frontend.views.widgets.empty_state import EmptyState
from frontend.views.widgets.inline_notice import InlineNotice
from frontend.views.widgets.page_header import PageHeader
from frontend.views.widgets.panel import Panel
from frontend.views.widgets.table_utils import chuan_hoa_bang


# pylint: disable=too-many-instance-attributes,too-few-public-methods
class ProjectsView(QWidget):
    """Màn hình chính quản lý danh sách và điều phối các thao tác Dự án."""

    open_analysis = pyqtSignal(dict)
    status_message = pyqtSignal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._controller = ProjectController(self)
        self._controller.projects_loaded.connect(self._on_projects_loaded)
        self._controller.error_occurred.connect(self._on_projects_failed)
        self._controller.status_message.connect(self.status_message.emit)

        self._table_model = ProjectTableModel([], self)
        self._proxy_model = ProjectFilterProxyModel(self)
        self._proxy_model.setSourceModel(self._table_model)

        self._notice: InlineNotice | None = None
        self._search_input: QLineEdit | None = None
        self._source_combo: QComboBox | None = None
        self._table_view: QTableView | None = None
        self._stack_layout: QStackedLayout | None = None
        self._empty_state: EmptyState | None = None
        self._btn_analyze: QPushButton | None = None
        self._btn_edit: QPushButton | None = None
        self._btn_delete: QPushButton | None = None
        self._lbl_count: QLabel | None = None

        self._setup_ui()
        self.load_projects()

    def _setup_ui(self) -> None:
        """Khởi tạo toàn bộ giao diện màn hình Dự án."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 28, 32, 24)
        layout.setSpacing(16)

        # 1. Thanh tiêu đề trên cùng (PageHeader)
        layout.addWidget(self._create_header_bar())

        # 2. Thanh tìm kiếm và bộ lọc (khoảng cách thoáng với bảng)
        layout.addWidget(self._create_filter_bar())
        layout.addSpacing(6)

        # 3. Thông báo nội dòng (Lỗi / Mất kết nối)
        self._notice = InlineNotice("", "error", "Thử lại", self)
        self._notice.retry_clicked.connect(self.load_projects)
        self._notice.hide()
        layout.addWidget(self._notice)

        # 4. Khu vực trung tâm: Bảng dữ liệu trong Panel hoặc EmptyState
        stack_container = QWidget(self)
        self._stack_layout = QStackedLayout(stack_container)
        self._stack_layout.setContentsMargins(0, 0, 0, 0)

        table_panel = Panel(self)
        panel_layout = QVBoxLayout(table_panel)
        panel_layout.setContentsMargins(0, 0, 0, 0)

        self._table_view = self._create_table_view()
        panel_layout.addWidget(self._table_view)
        self._stack_layout.addWidget(table_panel)

        self._empty_state = EmptyState(
            title="Chưa có dự án nào",
            description="Thêm dự án đầu tiên để bắt đầu phân tích chất lượng và an toàn mã nguồn.",
            action_text="Thêm dự án",
            parent=self,
        )
        self._empty_state.action_clicked.connect(self._on_add_project)
        self._stack_layout.addWidget(self._empty_state)

        layout.addWidget(stack_container, stretch=1)

        # 5. Thanh thao tác theo dòng (Sửa, Xóa, Phân tích)
        layout.addWidget(self._create_action_bar())

    def _create_header_bar(self) -> QWidget:
        """Tạo thanh tiêu đề chính và nút Thêm dự án theo chuẩn ArtCraft."""
        header = PageHeader(
            title="Dự án",
            subtitle="Quản lý và kiểm định chất lượng các kho mã nguồn mở",
            parent=self,
        )

        btn_reload = QPushButton("Làm mới", self)
        btn_reload.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_reload.clicked.connect(self.load_projects)

        btn_add = QPushButton("+ Thêm dự án", self)
        btn_add.setProperty("role", "primary")
        btn_add.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_add.clicked.connect(self._on_add_project)

        header.them_nut_phai(btn_reload)
        header.them_nut_phai(btn_add)
        return header

    def _create_filter_bar(self) -> QWidget:
        """Tạo thanh công cụ lọc và tìm kiếm với khoảng cách viền thoáng."""
        toolbar = QWidget(self)
        h_layout = QHBoxLayout(toolbar)
        h_layout.setContentsMargins(0, 0, 0, 8)
        h_layout.setSpacing(10)

        self._search_input = QLineEdit(toolbar)
        self._search_input.setPlaceholderText("Tìm theo tên hoặc đường dẫn...")
        self._search_input.setFixedHeight(36)
        self._search_input.textChanged.connect(self._proxy_model.set_search_keyword)

        self._source_combo = QComboBox(toolbar)
        self._source_combo.addItems(["Tất cả nguồn", "Thư mục cục bộ", "Kho mã nguồn GitHub"])
        self._source_combo.setFixedHeight(36)
        self._source_combo.currentTextChanged.connect(self._proxy_model.set_source_filter)

        h_layout.addWidget(self._search_input, stretch=1)
        h_layout.addWidget(self._source_combo)
        return toolbar

    def _create_table_view(self) -> QTableView:
        """Khởi tạo và cấu hình bảng hiển thị dự án theo chuẩn ArtCraft."""
        table = QTableView(self)
        table.setModel(self._proxy_model)
        chuan_hoa_bang(table, cot_gian=2, cot_so=(4,))

        table.doubleClicked.connect(self._on_row_double_clicked)
        table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        table.customContextMenuRequested.connect(self._show_context_menu)

        selection_model = table.selectionModel()
        if selection_model:
            selection_model.selectionChanged.connect(self._on_selection_changed)

        return table

    def _create_action_bar(self) -> QWidget:
        """Tạo thanh hành động ở chân bảng."""
        action_bar = QWidget(self)
        h_layout = QHBoxLayout(action_bar)
        h_layout.setContentsMargins(0, 4, 0, 0)
        h_layout.setSpacing(10)

        self._btn_analyze = QPushButton("Phân tích", action_bar)
        self._btn_analyze.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_analyze.clicked.connect(self._on_analyze_project)

        self._btn_edit = QPushButton("Sửa", action_bar)
        self._btn_edit.clicked.connect(self._on_edit_project)

        self._btn_delete = QPushButton("Xóa dự án", action_bar)
        self._btn_delete.setProperty("role", "danger")
        self._btn_delete.clicked.connect(self._on_delete_project)

        self._lbl_count = QLabel("Tổng số: 0 dự án", action_bar)
        self._lbl_count.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 12px;")

        self._btn_analyze.setEnabled(False)
        self._btn_edit.setEnabled(False)
        self._btn_delete.setEnabled(False)

        h_layout.addWidget(self._btn_analyze)
        h_layout.addWidget(self._btn_edit)
        h_layout.addWidget(self._btn_delete)
        h_layout.addStretch()
        h_layout.addWidget(self._lbl_count)
        return action_bar

    def _get_selected_project(self) -> dict[str, Any] | None:
        """Lấy bản ghi dự án hiện đang được chọn trên bảng."""
        if not self._table_view:
            return None
        selection = self._table_view.selectionModel()
        if not selection or not selection.hasSelection():
            return None
        indexes = selection.selectedRows()
        if not indexes:
            return None
        source_index = self._proxy_model.mapToSource(indexes[0])
        return self._table_model.get_project(source_index.row())

    def _on_selection_changed(self) -> None:
        """Kích hoạt các nút hành động khi có dòng được chọn."""
        has_sel = self._get_selected_project() is not None
        if self._btn_analyze:
            self._btn_analyze.setEnabled(has_sel)
            self._btn_analyze.setProperty("role", "primary" if has_sel else "")
            self._btn_analyze.style().unpolish(self._btn_analyze)
            self._btn_analyze.style().polish(self._btn_analyze)
        if self._btn_edit:
            self._btn_edit.setEnabled(has_sel)
        if self._btn_delete:
            self._btn_delete.setEnabled(has_sel)

    def load_projects(self) -> None:
        """Kích hoạt Controller nạp danh sách dự án từ máy chủ."""
        self._controller.load_projects()

    def _on_projects_loaded(self, projects: list[dict[str, Any]]) -> None:
        """Xử lý cập nhật giao diện khi dữ liệu dự án tải về thành công."""
        if self._notice:
            self._notice.hide()

        self._table_model.set_projects(projects)
        if self._lbl_count:
            self._lbl_count.setText(f"Tổng số: {len(projects)} dự án")

        if self._stack_layout:
            if projects:
                self._stack_layout.setCurrentIndex(0)
            else:
                self._stack_layout.setCurrentIndex(1)

    def _on_projects_failed(self, error_msg: str) -> None:
        """Hiển thị thông báo lỗi trên giao diện khi gọi API thất bại."""
        if self._notice:
            self._notice.set_notice(
                f"Không thể kết nối máy chủ: {error_msg}",
                "error",
                "Thử lại",
            )
            self._notice.show()

    def _on_add_project(self) -> None:
        """Hiển thị hộp thoại thêm mới và gửi dữ liệu tới Controller."""
        dialog = ProjectDialog(parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.get_data()
            self._controller.create_project(data)

    def _on_edit_project(self) -> None:
        """Hiển thị hộp thoại chỉnh sửa và gửi dữ liệu tới Controller."""
        proj = self._get_selected_project()
        if not proj:
            return

        dialog = ProjectDialog(project=proj, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.get_data()
            self._controller.update_project(int(proj["id"]), data)

    def _on_delete_project(self) -> None:
        """Hiển thị xác nhận xóa và yêu cầu Controller thực hiện xóa dự án."""
        proj = self._get_selected_project()
        if not proj:
            return

        proj_name = proj.get("name", "Dự án")
        proj_id = int(proj["id"])

        confirm = QMessageBox(self)
        confirm.setWindowTitle("Xác nhận xóa dự án")
        confirm.setText(
            f"Xóa dự án <b>{proj_name}</b> và toàn bộ dữ liệu phân tích liên quan?"
        )
        confirm.setInformativeText("Thao tác này không thể hoàn tác.")

        btn_delete = confirm.addButton("Xóa dự án", QMessageBox.ButtonRole.DestructiveRole)
        btn_delete.setProperty("role", "danger-solid")
        btn_keep = confirm.addButton("Giữ lại", QMessageBox.ButtonRole.RejectRole)
        confirm.setDefaultButton(btn_keep)

        confirm.exec()
        if confirm.clickedButton() == btn_delete:
            self._controller.delete_project(proj_id, proj_name)

    def _on_analyze_project(self) -> None:
        """Kích hoạt hành động chuyển tab phân tích cho dự án đang chọn."""
        proj = self._get_selected_project()
        if proj:
            self.open_analysis.emit(proj)
            self.status_message.emit(f"Mở phiên phân tích cho dự án: {proj.get('name')}")

    def _on_row_double_clicked(self, _index: QModelIndex) -> None:
        """Nhấp đúp chuột vào một dòng để kích hoạt phân tích ngay."""
        self._on_analyze_project()

    def _show_context_menu(self, pos: Any) -> None:
        """Hiển thị menu ngữ cảnh chuột phải trên bảng."""
        if not self._table_view:
            return
        proj = self._get_selected_project()
        if not proj:
            return

        menu = QMenu(self)
        act_analyze = menu.addAction("Phân tích dự án")
        act_edit = menu.addAction("Chỉnh sửa thông tin")
        menu.addSeparator()
        act_delete = menu.addAction("Xóa dự án")

        action = menu.exec(self._table_view.viewport().mapToGlobal(pos))
        if action == act_analyze:
            self._on_analyze_project()
        elif action == act_edit:
            self._on_edit_project()
        elif action == act_delete:
            self._on_delete_project()
