"""Màn hình Quản lý Dự án (ProjectsView) và các thành phần liên quan theo chuẩn SKILLS.md."""

import sys
from pathlib import Path
from typing import Any

# Đảm bảo đường dẫn import hoạt động từ thư mục gốc
ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# pylint: disable=wrong-import-position,no-name-in-module
from PyQt6.QtCore import (
    QAbstractTableModel,
    QModelIndex,
    QObject,
    QSortFilterProxyModel,
    Qt,
    pyqtSignal,
)
from PyQt6.QtWidgets import (
    QApplication,
    QComboBox,
    QDialog,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMenu,
    QMessageBox,
    QPushButton,
    QStackedLayout,
    QTableView,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from PyQt6.QtGui import QColor  # pylint: disable=no-name-in-module
from frontend.network import api
from frontend.views import theme
from frontend.views.theme import (
    SURFACE,
    TEXT_MAIN,
    TEXT_MUTED,
    format_datetime,
    lay_font_code,
    load_stylesheet,
)
from frontend.views.widgets.empty_state import EmptyState
from frontend.views.widgets.inline_notice import InlineNotice
from frontend.views.widgets.page_header import PageHeader
from frontend.views.widgets.panel import Panel
from frontend.views.widgets.table_utils import chuan_hoa_bang
from frontend.workers.request_worker import RequestWorker

_HEADERS = (
    "Tên dự án",
    "Nguồn",
    "Đường dẫn / Liên kết",
    "Lần phân tích cuối",
    "Điểm số",
)

_format_datetime = format_datetime


def _format_score(project: dict[str, Any]) -> str:
    """Định dạng điểm số và xếp loại: 82 (B) hoặc —."""
    score = project.get("total_score")
    if score is None:
        return "—"
    try:
        score_val = int(round(float(score)))
        grade = str(project.get("grade") or project.get("overall_grade") or "").strip().upper()
        if grade:
            return f"{score_val} ({grade})"
        return f"{score_val}"
    except (ValueError, TypeError):
        return "—"


def _format_source_type(project: dict[str, Any]) -> str:
    """Xác định loại nguồn: Thư mục hoặc GitHub."""
    raw_type = str(project.get("source_type", "")).strip().lower()
    path = str(project.get("path") or project.get("source_path") or "").strip().lower()
    if "git" in raw_type or path.startswith(("http://", "https://", "git@")):
        return "GitHub"
    return "Thư mục"


def _get_display_data(project: dict[str, Any], col: int) -> str:
    """Trích xuất chuỗi hiển thị theo từng cột dữ liệu."""
    if col == 0:
        return str(project.get("name", "—"))
    if col == 1:
        return _format_source_type(project)
    if col == 2:
        return str(project.get("path") or project.get("source_path") or "—")
    if col == 3:
        raw_time = project.get("last_analyzed_at") or project.get("completed_at")
        return _format_datetime(raw_time)
    if col == 4:
        return _format_score(project)
    return "—"


class ProjectTableModel(QAbstractTableModel):
    """Data Model cho bảng hiển thị danh sách dự án (5 cột chuẩn SKILLS.md)."""

    def __init__(self, projects: list[dict[str, Any]] | None = None, parent: QObject | None = None):
        super().__init__(parent)
        self._projects: list[dict[str, Any]] = list(projects) if projects else []

    def rowCount(self, _parent: QModelIndex = QModelIndex()) -> int:  # pylint: disable=invalid-name
        """Trả về tổng số dòng trong bảng dữ liệu."""
        return len(self._projects)

    def columnCount(self, _parent: QModelIndex = QModelIndex()) -> int:  # pylint: disable=invalid-name
        """Trả về tổng số cột trong bảng dữ liệu."""
        return len(_HEADERS)

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        """Trả về dữ liệu hiển thị, phông chữ và căn lề cho từng ô trong bảng."""
        if not index.isValid() or index.row() >= len(self._projects):
            return None

        project = self._projects[index.row()]
        col = index.column()

        if role == Qt.ItemDataRole.DisplayRole:
            return _get_display_data(project, col)
        if role == Qt.ItemDataRole.FontRole:
            return lay_font_code(11) if col in (2, 3, 4) else None
        if role == Qt.ItemDataRole.TextAlignmentRole:
            align = Qt.AlignmentFlag.AlignRight if col == 4 else Qt.AlignmentFlag.AlignLeft
            return align | Qt.AlignmentFlag.AlignVCenter
        if role == Qt.ItemDataRole.ForegroundRole and col == 4:
            grade = str(project.get("grade") or project.get("overall_grade") or "").strip().upper()
            return QColor(theme.GRADE_COLORS[grade]) if grade in theme.GRADE_COLORS else None

        return project if role == Qt.ItemDataRole.UserRole else None

    def headerData(  # pylint: disable=invalid-name
        self,
        section: int,
        orientation: Qt.Orientation,
        role: int = Qt.ItemDataRole.DisplayRole,
    ) -> Any:
        """Trả về tiêu đề các cột ở phần đầu bảng."""
        if orientation == Qt.Orientation.Horizontal:
            if role == Qt.ItemDataRole.DisplayRole and 0 <= section < len(_HEADERS):
                return _HEADERS[section]
            if role == Qt.ItemDataRole.TextAlignmentRole:
                if section == 4:
                    return Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
                return Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
        return None

    def set_projects(self, projects: list[dict[str, Any]]) -> None:
        """Cập nhật dữ liệu danh sách dự án và làm mới bảng."""
        self.beginResetModel()
        self._projects = list(projects)
        self.endResetModel()

    def get_project(self, row: int) -> dict[str, Any] | None:
        """Lấy thông tin dự án tại chỉ số dòng xác định."""
        if 0 <= row < len(self._projects):
            return self._projects[row]
        return None


class ProjectFilterProxyModel(QSortFilterProxyModel):
    """Bộ lọc dữ liệu động theo từ khóa tìm kiếm và loại nguồn."""

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._search_keyword: str = ""
        self._source_filter: str = "Tất cả"

    def set_search_keyword(self, keyword: str) -> None:
        """Cập nhật từ khóa tìm kiếm."""
        self._search_keyword = str(keyword).strip().lower()
        self.invalidateFilter()

    def set_source_filter(self, source: str) -> None:
        """Cập nhật bộ lọc loại nguồn (Tất cả, Thư mục, GitHub)."""
        self._source_filter = str(source).strip()
        self.invalidateFilter()

    def filterAcceptsRow(  # pylint: disable=invalid-name
        self,
        source_row: int,
        _source_parent: QModelIndex,
    ) -> bool:
        """Kiểm tra điều kiện hiển thị của từng dòng dữ liệu."""
        model = self.sourceModel()
        if not isinstance(model, ProjectTableModel):
            return True

        project = model.get_project(source_row)
        if not project:
            return False

        if self._search_keyword:
            name = str(project.get("name", "")).lower()
            path = str(project.get("path") or project.get("source_path") or "").lower()
            if self._search_keyword not in name and self._search_keyword not in path:
                return False

        if self._source_filter not in ("Tất cả", "Tất cả nguồn"):
            stype = _format_source_type(project)
            if self._source_filter == "Thư mục cục bộ" and stype != "Thư mục":
                return False
            if self._source_filter in ("Kho mã nguồn GitHub", "GitHub") and stype != "GitHub":
                return False

        return True


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


# pylint: disable=too-many-instance-attributes,too-few-public-methods
class ProjectsView(QWidget):
    """Màn hình chính quản lý danh sách và điều phối các thao tác Dự án."""

    open_analysis = pyqtSignal(dict)
    status_message = pyqtSignal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._active_worker: RequestWorker | None = None

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
        """Gọi API nạp danh sách dự án bất đồng bộ bằng RequestWorker."""
        self.status_message.emit("Đang tải danh sách dự án...")
        self._active_worker = RequestWorker(api.list_projects)
        self._active_worker.finished.connect(self._on_projects_loaded)
        self._active_worker.failed.connect(self._on_projects_failed)
        self._active_worker.start()

    def _on_projects_loaded(self, response: dict[str, Any]) -> None:
        """Xử lý khi nạp dữ liệu từ máy chủ thành công."""
        if self._notice:
            self._notice.hide()
        projects = response.get("data", [])
        if not isinstance(projects, list):
            projects = []

        self._table_model.set_projects(projects)
        if self._lbl_count:
            self._lbl_count.setText(f"Tổng số: {len(projects)} dự án")

        if self._stack_layout:
            if projects:
                self._stack_layout.setCurrentIndex(0)
                self.status_message.emit(f"Đã tải {len(projects)} dự án.")
            else:
                self._stack_layout.setCurrentIndex(1)
                self.status_message.emit("Chưa có dự án nào.")

    def _on_projects_failed(self, error_msg: str) -> None:
        """Hiển thị thông báo lỗi khi không thể giao tiếp với Socket Backend."""
        if self._notice:
            self._notice.set_notice(
                f"Không thể kết nối máy chủ: {error_msg}",
                "error",
                "Thử lại",
            )
            self._notice.show()
        self.status_message.emit("Lỗi kết nối máy chủ.")

    def _on_add_project(self) -> None:
        """Mở hộp thoại thêm mới dự án."""
        dialog = ProjectDialog(parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.get_data()
            self.status_message.emit(f"Đang thêm dự án '{data['name']}'...")
            worker = RequestWorker(
                api.create_project,
                name=data["name"],
                path=data["path"],
                desc=data["description"],
                source_type=data["source_type"],
            )
            worker.finished.connect(lambda _res: self.load_projects())
            worker.failed.connect(
                lambda err: self._notice and self._notice.set_notice(
                    f"Lỗi thêm dự án: {err}", "error"
                )
            )
            self._active_worker = worker
            worker.start()

    def _on_edit_project(self) -> None:
        """Mở hộp thoại chỉnh sửa thông tin dự án đang chọn."""
        proj = self._get_selected_project()
        if not proj:
            return

        dialog = ProjectDialog(project=proj, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.get_data()
            proj_id = int(proj["id"])
            self.status_message.emit(f"Đang cập nhật dự án '{data['name']}'...")
            worker = RequestWorker(
                api.update_project,
                project_id=proj_id,
                name=data["name"],
                path=data["path"],
                description=data["description"],
                source_type=data["source_type"],
            )
            worker.finished.connect(lambda _res: self.load_projects())
            worker.failed.connect(
                lambda err: self._notice and self._notice.set_notice(
                    f"Lỗi cập nhật: {err}", "error"
                )
            )
            self._active_worker = worker
            worker.start()

    def _on_delete_project(self) -> None:
        """Xác nhận và xóa dự án cùng toàn bộ dữ liệu phân tích."""
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
            self.status_message.emit(f"Đang xóa dự án '{proj_name}'...")
            worker = RequestWorker(api.delete_project, project_id=proj_id)
            worker.finished.connect(lambda _res: self.load_projects())
            worker.failed.connect(
                lambda err: self._notice and self._notice.set_notice(
                    f"Lỗi xóa dự án: {err}", "error"
                )
            )
            self._active_worker = worker
            worker.start()

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


def main() -> None:
    """Hàm chạy thử độc lập giao diện ProjectsView."""
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)

    app.setStyleSheet(load_stylesheet())

    window = QWidget()
    window.setWindowTitle("Kiểm tra Màn hình Quản lý Dự án (ProjectsView) - SKILLS.md")
    window.resize(1100, 680)

    v_layout = QVBoxLayout(window)
    v_layout.setContentsMargins(0, 0, 0, 0)

    view = ProjectsView(window)
    v_layout.addWidget(view)

    # Nếu không kết nối được server, tự động nạp dữ liệu mẫu để kiểm tra layout
    if not api.ping_server(timeout=0.3):
        mock_data = [
            {
                "id": 1,
                "name": "flask",
                "path": "https://github.com/pallets/flask",
                "source_type": "github",
                "description": "The Python micro framework for building web applications.",
                "last_analyzed_at": "2026-11-09 14:32:00",
                "total_score": 82.0,
                "grade": "B",
            },
            {
                "id": 2,
                "name": "bad_project",
                "path": "d:/Python/Đồ-Án/backend/samples/bad_project",
                "source_type": "local",
                "description": "Dự án mẫu kiểm thử chứa lỗi bảo mật và vi phạm PEP8.",
                "last_analyzed_at": None,
                "total_score": None,
                "grade": None,
            },
            {
                "id": 3,
                "name": "ShopEngine-Service",
                "path": "d:/Python/ShopEngine",
                "source_type": "local",
                "description": "Backend dịch vụ thanh toán và xử lý đơn hàng.",
                "last_analyzed_at": "2026-11-08 09:15:00",
                "total_score": 91.5,
                "grade": "A",
            },
        ]
        view._on_projects_loaded({"status": "ok", "data": mock_data})  # pylint: disable=protected-access

    window.show()

    if "--test" in sys.argv:
        app.processEvents()
        print("ProjectsView initialized and tested successfully!")
        sys.exit(0)

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
