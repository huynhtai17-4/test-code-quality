"""
Cửa sổ chính của ứng dụng Desktop GUI phân tích và đánh giá chất lượng mã nguồn mở.
Tích hợp Sidebar điều hướng 188px, QStackedWidget cho 5 màn hình, thanh trạng thái
và liên kết luồng tín hiệu toàn cục theo chuẩn SKILLS.md.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

# Đảm bảo đường dẫn import hoạt động khi chạy từ thư mục bất kỳ
ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# pylint: disable=no-name-in-module,wrong-import-position
from PyQt6.QtCore import QByteArray, QSettings, QSize, Qt, QTimer
from PyQt6.QtGui import (
    QCloseEvent,
    QColor,
    QIcon,
    QKeySequence,
    QPainter,
    QPen,
    QPixmap,
    QShortcut,
)
from PyQt6.QtWidgets import (
    QButtonGroup,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from frontend import config
from frontend.network import api
from frontend.views import theme
from frontend.views.analysis_view import AnalysisView
from frontend.views.history_view import HistoryView
from frontend.views.issues_view import IssuesView
from frontend.views.projects_view import ProjectsView
from frontend.views.settings_view import SettingsView
from frontend.workers.request_worker import RequestWorker


def _paint_icon_pixmap(icon_type: str, color_hex: str, size: int = 16) -> QPixmap:
    """Vẽ icon tối giản nét mảnh 1.5px bằng QPainter cho Sidebar."""
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    pen = QPen(QColor(color_hex), 1.5)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    painter.setPen(pen)

    if icon_type == "projects":
        # Folder nét mảnh
        painter.drawLine(2, 3, 5, 3)
        painter.drawLine(5, 3, 7, 5)
        painter.drawLine(7, 5, 14, 5)
        painter.drawLine(14, 5, 14, 13)
        painter.drawLine(14, 13, 2, 13)
        painter.drawLine(2, 13, 2, 3)
    elif icon_type == "analysis":
        # Bar chart nhịp độ
        painter.drawLine(3, 13, 3, 8)
        painter.drawLine(6, 13, 6, 4)
        painter.drawLine(10, 13, 10, 7)
        painter.drawLine(13, 13, 13, 3)
        painter.drawLine(2, 14, 14, 14)
    elif icon_type == "issues":
        # Khiên / Cảnh báo
        painter.drawLine(8, 2, 14, 13)
        painter.drawLine(14, 13, 2, 13)
        painter.drawLine(2, 13, 8, 2)
        painter.drawLine(8, 5, 8, 9)
        painter.drawPoint(8, 11)
    elif icon_type == "history":
        # Đồng hồ lịch sử
        painter.drawEllipse(2, 2, 12, 12)
        painter.drawLine(8, 4, 8, 8)
        painter.drawLine(8, 8, 11, 8)
    elif icon_type == "settings":
        # Bánh răng tối giản
        painter.drawEllipse(4, 4, 8, 8)
        painter.drawLine(8, 1, 8, 3)
        painter.drawLine(8, 13, 8, 15)
        painter.drawLine(1, 8, 3, 8)
        painter.drawLine(13, 8, 15, 8)
        painter.drawLine(3, 3, 5, 5)
        painter.drawLine(11, 11, 13, 13)
        painter.drawLine(3, 13, 5, 11)
        painter.drawLine(11, 5, 13, 3)

    painter.end()
    return pixmap


def _create_sidebar_icon(icon_type: str) -> QIcon:
    """Tạo QIcon 2 trạng thái: bình thường (#64748B) và kích hoạt (#FFFFFF)."""
    icon = QIcon()
    icon.addPixmap(_paint_icon_pixmap(icon_type, "#64748B"), QIcon.Mode.Normal, QIcon.State.Off)
    icon.addPixmap(_paint_icon_pixmap(icon_type, "#FFFFFF"), QIcon.Mode.Normal, QIcon.State.On)
    return icon


class MainWindow(QMainWindow):  # pylint: disable=too-many-instance-attributes
    """
    Cửa sổ chính (MainWindow) điều phối toàn bộ luồng làm việc và giao diện người dùng.

    Bao gồm:
    - Cột điều hướng bên trái (Sidebar 188px).
    - Vùng nội dung trung tâm (QStackedWidget gồm 5 view).
    - Thanh trạng thái đáy hiển thị kết nối server và dự án đang hoạt động.
    - Hệ thống phím tắt toàn cục và quản lý lưu trữ trạng thái cửa sổ.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        """Khởi tạo cửa sổ chính và các thành phần giao diện."""
        super().__init__(parent)

        self.current_project: dict[str, Any] | None = None
        self._ping_worker: RequestWorker | None = None

        self.sidebar: QFrame | None = None
        self.lbl_logo: QLabel | None = None
        self.btn_projects: QPushButton | None = None
        self.btn_analysis: QPushButton | None = None
        self.btn_issues: QPushButton | None = None
        self.btn_history: QPushButton | None = None
        self.btn_settings: QPushButton | None = None
        self.btn_group: QButtonGroup | None = None

        self.sidebar_server_card: QFrame | None = None
        self.lbl_sidebar_server: QLabel | None = None

        self.stack: QStackedWidget | None = None
        self.projects_view: ProjectsView | None = None
        self.analysis_view: AnalysisView | None = None
        self.issues_view: IssuesView | None = None
        self.history_view: HistoryView | None = None
        self.settings_view: SettingsView | None = None

        self.lbl_connection: QLabel | None = None
        self.lbl_current_project: QLabel | None = None
        self._ping_timer: QTimer | None = None

        theme.init_app_fonts()
        self._init_window_properties()
        self._init_ui()
        self._setup_shortcuts()
        self._connect_signals()
        self._restore_window_state()

        # Khởi tạo kiểm tra kết nối máy chủ
        self._ping_timer = QTimer(self)
        self._ping_timer.timeout.connect(self.check_server_connection)
        self._ping_timer.start(30000)
        self.check_server_connection()

    def _init_window_properties(self) -> None:
        """Thiết lập kích thước và tiêu đề cửa sổ chuẩn."""
        self.setWindowTitle("Hệ thống phân tích và đánh giá chất lượng mã nguồn mở")
        self.resize(1200, 750)
        self.setMinimumSize(1100, 680)

    def _init_ui(self) -> None:
        """Khởi tạo các khối giao diện chính."""
        central_widget = QWidget(self)
        central_widget.setObjectName("CentralWidget")
        self.setCentralWidget(central_widget)

        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 1. Sidebar điều hướng
        self.sidebar = self._create_sidebar()
        main_layout.addWidget(self.sidebar)

        # 2. Vùng hiển thị StackedWidget
        self.stack = QStackedWidget(self)
        self.projects_view = ProjectsView(self)
        self.analysis_view = AnalysisView(self)
        self.issues_view = IssuesView(self)
        self.history_view = HistoryView(self)
        self.settings_view = SettingsView(self)

        self.stack.addWidget(self.projects_view)  # Index 0
        self.stack.addWidget(self.analysis_view)  # Index 1
        self.stack.addWidget(self.issues_view)    # Index 2
        self.stack.addWidget(self.history_view)   # Index 3
        self.stack.addWidget(self.settings_view)  # Index 4

        main_layout.addWidget(self.stack, 1)

        # 3. Thanh trạng thái (QStatusBar)
        self._init_status_bar()

    def _create_sidebar_server_card(self, parent: QWidget) -> QFrame:
        """Tạo thẻ tóm tắt kết nối máy chủ hiển thị ở đáy Sidebar."""
        card = QFrame(parent)
        card.setObjectName("SidebarServerCard")
        sc_layout = QVBoxLayout(card)
        sc_layout.setContentsMargins(8, 6, 8, 6)
        sc_layout.setSpacing(2)

        lbl_srv_title = QLabel("MÁY CHỦ", card)
        lbl_srv_title.setStyleSheet("color: #7E8B9B; font-size: 10px; font-weight: bold;")
        self.lbl_sidebar_server = QLabel(
            f"● {config.SERVER_HOST}:{config.SERVER_PORT}", card
        )
        self.lbl_sidebar_server.setStyleSheet(
            f"color: {theme.GRADE_F}; font-size: 11px; font-weight: 500;"
        )

        sc_layout.addWidget(lbl_srv_title)
        sc_layout.addWidget(self.lbl_sidebar_server)
        return card

    def _create_sidebar(self) -> QFrame:
        """Khởi tạo cột điều hướng bên trái cố định 188px."""
        sidebar = QFrame(self)
        sidebar.setObjectName("Sidebar")
        sidebar.setFixedWidth(theme.SIDEBAR_WIDTH)

        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(0, 0, 0, 12)
        layout.setSpacing(2)

        # Tiêu đề logo ứng dụng phong cách kỹ thuật ArtCraft
        self.lbl_logo = QLabel("Code Quality", sidebar)
        self.lbl_logo.setObjectName("SidebarLogo")
        self.lbl_logo.setStyleSheet(
            "color: #0F172A; font-size: 15px; font-weight: 700; padding: 16px 16px 12px 16px;"
        )
        layout.addWidget(self.lbl_logo)

        # Nhóm nút bấm điều hướng
        self.btn_projects = QPushButton("Dự án", sidebar)
        self.btn_analysis = QPushButton("Phân tích", sidebar)
        self.btn_issues = QPushButton("Lỗi phát hiện", sidebar)
        self.btn_history = QPushButton("Lịch sử quét", sidebar)
        self.btn_settings = QPushButton("Cài đặt", sidebar)

        self.btn_projects.setToolTip("Quản lý danh sách dự án (Ctrl+1)")
        self.btn_analysis.setToolTip("Phân tích và kiểm định chất lượng mã nguồn (Ctrl+2)")
        self.btn_issues.setToolTip("Chi tiết lỗi phát hiện và đề xuất khắc phục (Ctrl+3)")
        self.btn_history.setToolTip("Lịch sử các phiên quét và so sánh chất lượng (Ctrl+4)")
        self.btn_settings.setToolTip("Cài đặt kết nối máy chủ và trọng số đánh giá (Ctrl+5)")

        self.btn_projects.setIcon(_create_sidebar_icon("projects"))
        self.btn_analysis.setIcon(_create_sidebar_icon("analysis"))
        self.btn_issues.setIcon(_create_sidebar_icon("issues"))
        self.btn_history.setIcon(_create_sidebar_icon("history"))
        self.btn_settings.setIcon(_create_sidebar_icon("settings"))

        for btn in (
            self.btn_projects,
            self.btn_analysis,
            self.btn_issues,
            self.btn_history,
            self.btn_settings,
        ):
            btn.setIconSize(QSize(16, 16))

        nav_buttons = [
            (self.btn_projects, 0),
            (self.btn_analysis, 1),
            (self.btn_issues, 2),
            (self.btn_history, 3),
        ]

        self.btn_group = QButtonGroup(self)
        self.btn_group.setExclusive(True)

        for btn, idx in nav_buttons:
            btn.setCheckable(True)
            self.btn_group.addButton(btn, idx)
            layout.addWidget(btn)

        layout.addStretch()

        # Thẻ tóm tắt kết nối máy chủ ở đáy Sidebar
        self.sidebar_server_card = self._create_sidebar_server_card(sidebar)
        layout.addWidget(self.sidebar_server_card)

        # Đường phân cách 1px đẩy xuống đáy
        separator = QFrame(sidebar)
        separator.setObjectName("SidebarSeparator")
        separator.setFrameShape(QFrame.Shape.HLine)
        layout.addWidget(separator)

        # Nút cài đặt ở đáy
        self.btn_settings.setCheckable(True)
        self.btn_group.addButton(self.btn_settings, 4)
        layout.addWidget(self.btn_settings)

        self.btn_group.idClicked.connect(self.switch_tab)

        # Mặc định chọn nút Dự án
        self.btn_projects.setChecked(True)
        return sidebar

    def _init_status_bar(self) -> None:
        """Thiết lập thanh trạng thái ở đáy cửa sổ."""
        status_bar = self.statusBar()
        status_bar.setSizeGripEnabled(False)

        # Nhãn kết nối bên trái
        self.lbl_connection = QLabel(
            f"● Đang kết nối {config.SERVER_HOST}:{config.SERVER_PORT}...",
            status_bar,
        )
        self.lbl_connection.setStyleSheet(f"color: {theme.TEXT_MUTED}; padding-left: 14px;")
        status_bar.addWidget(self.lbl_connection)

        # Nhãn dự án hiện tại bên phải
        self.lbl_current_project = QLabel("Dự án: [Chưa chọn]", status_bar)
        self.lbl_current_project.setStyleSheet(f"color: {theme.TEXT_MUTED}; padding-right: 18px;")
        status_bar.addPermanentWidget(self.lbl_current_project)

    def _setup_shortcuts(self) -> None:
        """Đăng ký hệ thống phím tắt toàn cục."""
        shortcuts = [
            ("Ctrl+1", lambda: self.switch_tab(0)),
            ("Ctrl+2", lambda: self.switch_tab(1)),
            ("Ctrl+3", lambda: self.switch_tab(2)),
            ("Ctrl+4", lambda: self.switch_tab(3)),
            ("Ctrl+5", lambda: self.switch_tab(4)),
            ("Ctrl+N", self._on_shortcut_new_project),
            ("F5", self.refresh_current_view),
        ]
        for key_seq, callback in shortcuts:
            shortcut = QShortcut(QKeySequence(key_seq), self)
            shortcut.activated.connect(callback)

    def _connect_signals(self) -> None:
        """Liên kết luồng tín hiệu giữa các màn hình nghiệp vụ."""
        if self.projects_view is None or self.analysis_view is None:
            return
        if self.issues_view is None or self.history_view is None or self.settings_view is None:
            return

        # 1. ProjectsView -> AnalysisView
        self.projects_view.open_analysis.connect(self.on_open_analysis)

        # Khi chọn dự án trong bảng ProjectsView
        # pylint: disable=protected-access
        if self.projects_view._table_view is not None:
            sel_model = self.projects_view._table_view.selectionModel()
            if sel_model is not None:
                sel_model.selectionChanged.connect(self._on_project_selection_changed)

        # 2. AnalysisView -> IssuesView
        self.analysis_view.switch_to_issues.connect(self.on_switch_to_issues)

        # 3. HistoryView -> IssuesView
        self.history_view.open_session_issues.connect(self.on_switch_to_issues)

        # 4. Gom tín hiệu status_message từ 5 màn hình
        for view in (
            self.projects_view,
            self.analysis_view,
            self.issues_view,
            self.history_view,
            self.settings_view,
        ):
            view.status_message.connect(self._show_status_message)

    def switch_tab(self, index: int) -> None:
        """
        Chuyển đổi màn hình hiển thị trong QStackedWidget và đồng bộ nút Sidebar.

        Args:
            index: Vị trí chỉ mục của màn hình (0 đến 4).
        """
        if self.stack is None or self.btn_group is None:
            return
        if index < 0 or index >= self.stack.count():
            return

        self.stack.setCurrentIndex(index)
        btn = self.btn_group.button(index)
        if btn and not btn.isChecked():
            btn.setChecked(True)

        # Tự động nạp lịch sử nếu chuyển sang HistoryView mà đã có dự án hiện tại
        if index == 3 and self.current_project and "id" in self.current_project:
            proj_id = int(self.current_project["id"])
            # pylint: disable=protected-access
            if self.history_view and getattr(self.history_view, "_project_id", None) != proj_id:
                self.history_view.load_project_history(proj_id)

    def set_current_project(self, project: dict[str, Any] | None) -> None:
        """
        Cập nhật dự án đang được kích hoạt và hiển thị trên thanh trạng thái.

        Args:
            project: Từ điển dữ liệu dự án hoặc None nếu chưa chọn.
        """
        self.current_project = project
        if self.lbl_current_project is None:
            return
        if project and "name" in project:
            self.lbl_current_project.setText(f"Dự án: {project['name']}")
        else:
            self.lbl_current_project.setText("Dự án: [Chưa chọn]")

    def on_open_analysis(self, project: dict[str, Any]) -> None:
        """
        Xử lý khi người dùng chọn phân tích một dự án từ ProjectsView.

        Args:
            project: Thông tin dự án được chọn.
        """
        self.set_current_project(project)
        self.switch_tab(1)
        if self.analysis_view is not None:
            self.analysis_view.set_project(project)

    def on_switch_to_issues(self, session_id: int) -> None:
        """
        Chuyển sang màn hình danh sách lỗi và nạp dữ liệu phiên tương ứng.

        Args:
            session_id: Mã định danh phiên phân tích.
        """
        self.switch_tab(2)
        if self.issues_view is not None:
            self.issues_view.load_session_issues(session_id)

    def _on_project_selection_changed(self) -> None:
        """Cập nhật nhãn dự án hiện tại khi người dùng chọn một dòng dự án."""
        if self.projects_view is None:
            return
        # pylint: disable=protected-access
        selected = self.projects_view._get_selected_project()
        if selected:
            self.set_current_project(selected)

    def _on_shortcut_new_project(self) -> None:
        """Kích hoạt hộp thoại tạo mới dự án từ phím tắt Ctrl+N."""
        self.switch_tab(0)
        # pylint: disable=protected-access
        if self.projects_view is not None:
            self.projects_view._on_add_project()

    def refresh_current_view(self) -> None:
        """Gọi hàm làm mới (refresh/load) cho màn hình đang hiển thị."""
        if self.stack is None:
            return
        current_idx = self.stack.currentIndex()
        if current_idx == 0 and self.projects_view:
            self.projects_view.load_projects()
        elif current_idx == 1 and self.analysis_view and self.current_project:
            self.analysis_view.set_project(self.current_project)
        elif current_idx == 2 and self.issues_view:
            # pylint: disable=protected-access
            sid = getattr(self.issues_view, "_session_id", None)
            if sid:
                self.issues_view.load_session_issues(sid)
        elif current_idx == 3 and self.history_view:
            # pylint: disable=protected-access
            pid = getattr(self.history_view, "_project_id", None)
            if pid:
                self.history_view.load_project_history(pid)
            elif self.current_project and "id" in self.current_project:
                self.history_view.load_project_history(int(self.current_project["id"]))
        elif current_idx == 4 and self.settings_view:
            self.settings_view.load_current_configs()

        self._show_status_message("Đang làm mới dữ liệu...")

    def check_server_connection(self) -> None:
        """Kiểm tra kết nối TCP socket tới máy chủ Backend trong luồng ngầm."""
        worker = RequestWorker(api.ping_server, parent=self)
        self._ping_worker = worker

        def _on_ping_finished(res: dict[str, Any] | bool) -> None:
            if isinstance(res, dict):
                is_alive = bool(res.get("data", False))
            else:
                is_alive = bool(res)
            self.update_connection_status(is_alive)

        def _on_ping_failed(_err: str) -> None:
            self.update_connection_status(False)

        worker.finished.connect(_on_ping_finished)
        worker.failed.connect(_on_ping_failed)
        worker.start()

    def update_connection_status(self, is_alive: bool) -> None:
        """
        Cập nhật màu sắc và trạng thái kết nối trên thanh trạng thái.

        Args:
            is_alive: True nếu máy chủ backend đang phản hồi, ngược lại False.
        """
        if self.lbl_connection is None:
            return
        if is_alive:
            self.lbl_connection.setText(
                f"● Đã kết nối {config.SERVER_HOST}:{config.SERVER_PORT}"
            )
            self.lbl_connection.setStyleSheet(
                f"color: {theme.GRADE_A}; font-weight: 500; padding-left: 14px;"
            )
            if self.lbl_sidebar_server is not None:
                self.lbl_sidebar_server.setText(
                    f"● {config.SERVER_HOST}:{config.SERVER_PORT}"
                )
                self.lbl_sidebar_server.setStyleSheet(
                    f"color: {theme.GRADE_A}; font-size: 11px; font-weight: 500;"
                )
        else:
            self.lbl_connection.setText("● Mất kết nối máy chủ")
            self.lbl_connection.setStyleSheet(
                f"color: {theme.GRADE_F}; font-weight: 500; padding-left: 14px;"
            )
            if self.lbl_sidebar_server is not None:
                self.lbl_sidebar_server.setText("● Mất kết nối")
                self.lbl_sidebar_server.setStyleSheet(
                    f"color: {theme.GRADE_F}; font-size: 11px; font-weight: 500;"
                )

    def _show_status_message(self, message: str) -> None:
        """Hiển thị thông báo phản hồi nhanh trên thanh trạng thái trong 3 giây."""
        self.statusBar().showMessage(message, 3000)

    def _restore_window_state(self) -> None:
        """Khôi phục vị trí và kích thước cửa sổ từ QSettings."""
        settings = QSettings("CodeQualityAnalyzer", "DesktopGUI")
        geom = settings.value("geometry")
        if geom is not None and isinstance(geom, (bytes, QByteArray)):
            self.restoreGeometry(geom)
        state = settings.value("windowState")
        if state is not None and isinstance(state, (bytes, QByteArray)):
            self.restoreState(state)

    def closeEvent(self, event: QCloseEvent) -> None:  # pylint: disable=invalid-name
        """Lưu lại kích thước và trạng thái cửa sổ trước khi đóng."""
        if hasattr(self, "_ping_timer") and self._ping_timer and self._ping_timer.isActive():
            self._ping_timer.stop()

        if hasattr(self, "_ping_worker") and self._ping_worker:
            try:
                self._ping_worker.finished.disconnect()
                self._ping_worker.failed.disconnect()
            except (TypeError, RuntimeError):
                pass
            if self._ping_worker.isRunning():
                self._ping_worker.quit()
                self._ping_worker.wait(1000)

        settings = QSettings("CodeQualityAnalyzer", "DesktopGUI")
        settings.setValue("geometry", self.saveGeometry())
        settings.setValue("windowState", self.saveState())
        super().closeEvent(event)
