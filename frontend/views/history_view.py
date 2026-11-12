"""Màn hình Lịch sử & So sánh các phiên phân tích (HistoryView) theo chuẩn SKILLS.md."""

import json
import sys
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# pylint: disable=wrong-import-position,no-name-in-module,too-many-lines
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from PyQt6.QtCore import (
    QAbstractTableModel,
    QItemSelection,
    QModelIndex,
    Qt,
    pyqtSignal,
)
from PyQt6.QtGui import QColor, QFont, QKeySequence, QShortcut
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QDialog,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QStackedLayout,
    QTableWidget,
    QTableWidgetItem,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from frontend.charts.style import (
    CHART_ACCENT,
    CHART_TEXT_MUTED,
    TEN_TIEU_CHI,
    apply_chart_style,
)
from frontend.network import api
from frontend.views.theme import (
    GRADE_A,
    GRADE_COLORS,
    GRADE_F,
    SEV_CRITICAL,
    SEV_HIGH,
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
    "Mã phiên",
    "Thời gian",
    "Điểm số",
    "Xếp loại",
    "Tổng lỗi",
    "Nghiêm trọng (C / H)",
    "Khác (M / L)",
)

_format_datetime = format_datetime


def _format_short_date(raw_dt: Any) -> str:
    """Định dạng ngày ngắn dd/MM cho biểu đồ."""
    if not raw_dt:
        return ""
    full_str = _format_datetime(raw_dt)
    if " " in full_str:
        return full_str.split(" ")[0]
    return full_str


def _parse_summary(summary_data: Any) -> dict[str, Any]:
    """Phân tích trường summary sang dictionary an toàn."""
    if isinstance(summary_data, dict):
        return summary_data
    if isinstance(summary_data, str) and summary_data.strip():
        try:
            parsed = json.loads(summary_data)
            if isinstance(parsed, dict):
                return parsed
        except (json.JSONDecodeError, TypeError):
            pass
    return {}


def _get_severity_counts(session: dict[str, Any]) -> tuple[int, int, int, int]:
    """Trích xuất bộ (Critical, High, Medium, Low) từ session."""
    summary = _parse_summary(session.get("summary"))
    dist = summary.get("severity_distribution", {})

    crit = int(dist.get("Critical", 0))
    high = int(dist.get("High", 0))
    med = int(dist.get("Medium", 0))
    low = int(dist.get("Low", 0))

    if crit == 0 and high == 0 and session.get("security_issues_count"):
        high = int(session.get("security_issues_count") or 0)

    return crit, high, med, low


def _get_criteria_scores(session: dict[str, Any]) -> dict[str, float]:
    """Trích xuất điểm số của 5 tiêu chí từ session summary hoặc các chỉ số trực tiếp."""
    summary = _parse_summary(session.get("summary"))
    scores = summary.get("criteria_scores", {})

    return {
        "complexity": float(
            scores.get("complexity") or session.get("maintainability_index") or 0.0
        ),
        "security": float(scores.get("security") or 0.0),
        "pylint": float(scores.get("pylint") or session.get("pylint_score") or 0.0),
        "health": float(scores.get("health") or 0.0),
        "dependency": float(scores.get("dependency") or 0.0),
    }


class HistoryTableModel(QAbstractTableModel):
    """
    Model dữ liệu hiển thị danh sách các phiên quét trong lịch sử.

    Bao gồm 7 cột:
    0: Mã phiên (#ID)
    1: Thời gian (dd/MM/yyyy HH:mm)
    2: Điểm số (ví dụ: 79.3 / 100)
    3: Xếp loại (A, B, C, D, F kèm màu GRADE_*)
    4: Tổng lỗi
    5: Nghiêm trọng (C: X | H: Y)
    6: Khác (M: X | L: Y)
    """

    def __init__(self, sessions: list[dict[str, Any]] | None = None) -> None:
        super().__init__()
        self._sessions: list[dict[str, Any]] = []
        self._font_code: QFont = lay_font_code(11)
        if sessions:
            self.set_sessions(sessions)

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:  # pylint: disable=invalid-name
        """Số dòng trong bảng dữ liệu."""
        if parent.isValid():
            return 0
        return len(self._sessions)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:  # pylint: disable=invalid-name
        """Số lượng 7 cột dữ liệu lịch sử."""
        return 0 if parent.isValid() else len(_HEADERS)

    def headerData(  # pylint: disable=invalid-name
        self,
        section: int,
        orientation: Qt.Orientation,
        role: int = Qt.ItemDataRole.DisplayRole,
    ) -> Any:
        """Cung cấp tiêu đề cột theo phương ngang."""
        if orientation == Qt.Orientation.Horizontal and role == Qt.ItemDataRole.DisplayRole:
            if 0 <= section < len(_HEADERS):
                return _HEADERS[section]
        return None

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        """Cung cấp nội dung, màu sắc, phông chữ và căn lề cho các ô."""
        if not index.isValid() or not 0 <= index.row() < len(self._sessions):
            return None

        session = self._sessions[index.row()]
        col = index.column()
        result: Any = None

        if role == Qt.ItemDataRole.DisplayRole:
            result = self._get_display_data(session, col)
        elif role == Qt.ItemDataRole.ForegroundRole:
            result = self._get_foreground_color(session, col)
        elif role == Qt.ItemDataRole.FontRole and col in (0, 5, 6):
            result = self._font_code
        elif role == Qt.ItemDataRole.TextAlignmentRole:
            if col in (2, 4):
                result = int(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            elif col in (0, 3, 5, 6):
                result = int(Qt.AlignmentFlag.AlignCenter)
        elif role == Qt.ItemDataRole.UserRole:
            result = session

        return result

    @staticmethod
    def _get_display_data(session: dict[str, Any], col: int) -> str:
        """Trích xuất nội dung văn bản hiển thị theo cột."""
        crit, high, med, low = _get_severity_counts(session)

        extractors = (
            lambda s: f"#{s.get('id', '—')}",
            lambda s: _format_datetime(s.get("started_at") or s.get("completed_at")),
            lambda s: (
                f"{float(s['total_score']):.1f} / 100" if s.get("total_score") is not None else "—"
            ),
            lambda s: str(s.get("grade") or "—").upper(),
            lambda s: str(s.get("total_issues") if s.get("total_issues") is not None else 0),
            lambda _s: f"C: {crit} | H: {high}",
            lambda _s: f"M: {med} | L: {low}",
        )
        if 0 <= col < len(extractors):
            return extractors[col](session)
        return ""

    @staticmethod
    def _get_foreground_color(session: dict[str, Any], col: int) -> QColor | None:
        """Cung cấp màu sắc chữ trực quan theo xếp loại hoặc mức độ nghiêm trọng."""
        if col == 3:
            grade = str(session.get("grade") or "").upper()
            return QColor(GRADE_COLORS.get(grade, TEXT_MAIN))
        if col == 5:
            crit, high, _, _ = _get_severity_counts(session)
            if crit > 0:
                return QColor(SEV_CRITICAL)
            if high > 0:
                return QColor(SEV_HIGH)
            return QColor(TEXT_MUTED)
        return None

    def set_sessions(self, sessions: list[dict[str, Any]]) -> None:
        """Nạp danh sách phiên quét mới và tự động sắp xếp mới nhất lên đầu."""
        self.beginResetModel()
        self._sessions = list(sessions)
        self._sessions.sort(
            key=lambda item: (
                str(item.get("started_at") or item.get("completed_at") or ""),
                int(item.get("id") or 0),
            ),
            reverse=True,
        )
        self.endResetModel()

    def get_sessions(self) -> list[dict[str, Any]]:
        """Lấy danh sách phiên quét hiện tại."""
        return list(self._sessions)

    def get_session(self, row: int) -> dict[str, Any] | None:
        """Lấy bản ghi phiên quét tại vị trí chỉ định."""
        if 0 <= row < len(self._sessions):
            return self._sessions[row]
        return None

    def remove_session(self, session_id: int) -> bool:
        """Xóa một phiên quét khỏi model theo session_id."""
        for row_idx, item in enumerate(self._sessions):
            if item.get("id") == session_id:
                self.beginRemoveRows(QModelIndex(), row_idx, row_idx)
                self._sessions.pop(row_idx)
                self.endRemoveRows()
                return True
        return False


def _format_delta(diff: float) -> tuple[str, QColor]:
    """Tạo chuỗi ký tự hiển thị độ lệch kèm màu sắc trực quan."""
    if diff > 0.001:
        return f"▲ +{diff:.2f}", QColor(GRADE_A)
    if diff < -0.001:
        return f"▼ {diff:.2f}", QColor(GRADE_F)
    return "— 0.00", QColor(TEXT_MUTED)


class ComparisonDialog(QDialog):  # pylint: disable=too-few-public-methods
    """
    Hộp thoại đối chiếu kết quả chi tiết giữa hai phiên quét được chọn.

    Hiển thị độ lệch delta theo từng tiêu chí kèm mũi tên chỉ hướng và màu sắc.
    """

    def __init__(
        self,
        session_a: dict[str, Any],
        session_b: dict[str, Any],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("So sánh kết quả giữa hai phiên phân tích")
        self.setModal(True)
        self.resize(680, 420)

        # Xác định phiên cũ hơn và phiên mới hơn dựa theo thời gian/ID
        self.old_sess, self.new_sess = self._order_sessions(session_a, session_b)
        self._init_ui()

    @staticmethod
    def _order_sessions(
        s1: dict[str, Any],
        s2: dict[str, Any],
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        """Phân loại phiên quét cũ hơn và mới hơn."""
        t1 = str(s1.get("started_at") or s1.get("completed_at") or "")
        t2 = str(s2.get("started_at") or s2.get("completed_at") or "")
        if t1 and t2 and t1 < t2:
            return s1, s2
        if s1.get("id", 0) < s2.get("id", 0):
            return s1, s2
        return s2, s1

    def _init_ui(self) -> None:
        """Xây dựng bảng đối chiếu và nút đóng."""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 18, 20, 18)
        main_layout.setSpacing(14)

        desc_lbl = QLabel(
            "Đối chiếu điểm số các tiêu chí chất lượng mã nguồn giữa hai lần kiểm định:"
        )
        desc_lbl.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 13px;")
        main_layout.addWidget(desc_lbl)

        table = self._build_comparison_table()
        main_layout.addWidget(table, 1)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        btn_close = QPushButton("Đóng")
        btn_close.setProperty("role", "primary")
        btn_close.clicked.connect(self.accept)

        shortcut_esc = QShortcut(QKeySequence("Esc"), self)
        shortcut_esc.activated.connect(self.accept)

        shortcut_enter = QShortcut(QKeySequence("Return"), self)
        shortcut_enter.activated.connect(self.accept)

        btn_layout.addWidget(btn_close)
        main_layout.addLayout(btn_layout)

    def _get_comparison_headers(self) -> list[str]:
        """Tạo danh sách tiêu đề 4 cột cho bảng so sánh."""
        old_id = self.old_sess.get("id", "—")
        new_id = self.new_sess.get("id", "—")
        old_dt = _format_datetime(
            self.old_sess.get("started_at") or self.old_sess.get("completed_at")
        )
        new_dt = _format_datetime(
            self.new_sess.get("started_at") or self.new_sess.get("completed_at")
        )
        return [
            "Tiêu chí đánh giá",
            f"Phiên cũ (#{old_id} · {old_dt})",
            f"Phiên mới (#{new_id} · {new_dt})",
            "Độ lệch (Δ)",
        ]

    def _build_comparison_table(self) -> QTableWidget:
        """Tạo bảng đối chiếu 6 dòng x 4 cột."""
        headers = self._get_comparison_headers()
        table = QTableWidget(6, 4)
        table.setHorizontalHeaderLabels(headers)
        table.verticalHeader().setVisible(False)
        table.setAlternatingRowColors(True)
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)

        header_view = table.horizontalHeader()
        header_view.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        for i in range(1, 4):
            header_view.setSectionResizeMode(i, QHeaderView.ResizeMode.ResizeToContents)

        old_scores = _get_criteria_scores(self.old_sess)
        new_scores = _get_criteria_scores(self.new_sess)

        criteria_keys = ["complexity", "security", "pylint", "health", "dependency"]
        for row, key in enumerate(criteria_keys):
            v_old = old_scores.get(key, 0.0)
            v_new = new_scores.get(key, 0.0)
            self._fill_comparison_row(
                table,
                row,
                TEN_TIEU_CHI.get(key, key),
                (f"{v_old:.1f}", f"{v_new:.1f}"),
                v_new - v_old,
            )

        self._fill_total_row(table)
        return table

    def _fill_total_row(self, table: QTableWidget) -> None:
        """Điền dòng điểm tổng kết."""
        tot_old = float(self.old_sess.get("total_score") or 0.0)
        tot_new = float(self.new_sess.get("total_score") or 0.0)
        grd_old = str(self.old_sess.get("grade") or "—").upper()
        grd_new = str(self.new_sess.get("grade") or "—").upper()
        self._fill_comparison_row(
            table,
            5,
            "Điểm tổng kết",
            (f"{tot_old:.1f} ({grd_old})", f"{tot_new:.1f} ({grd_new})"),
            tot_new - tot_old,
        )

    @staticmethod
    def _fill_comparison_row(
        table: QTableWidget,
        row: int,
        name: str,
        texts: tuple[str, str],
        diff: float,
    ) -> None:
        """Điền dữ liệu đối chiếu và định dạng độ lệch màu sắc cho từng dòng."""
        delta_str, delta_color = _format_delta(diff)

        item_name = QTableWidgetItem(name)
        item_old = QTableWidgetItem(texts[0])
        item_new = QTableWidgetItem(texts[1])
        item_delta = QTableWidgetItem(delta_str)

        align_r = int(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        item_old.setTextAlignment(align_r)
        item_new.setTextAlignment(align_r)
        item_delta.setTextAlignment(align_r)
        item_delta.setForeground(delta_color)

        if row == 5:
            font = item_name.font()
            font.setBold(True)
            for itm in (item_name, item_old, item_new, item_delta):
                itm.setFont(font)

        table.setItem(row, 0, item_name)
        table.setItem(row, 1, item_old)
        table.setItem(row, 2, item_new)
        table.setItem(row, 3, item_delta)


def _extract_trend_data(
    sessions: list[dict[str, Any]],
) -> tuple[list[int], list[float], list[str]]:
    """Trích xuất tọa độ X, điểm Y và nhãn ngày tháng theo trật tự thời gian."""
    chrono = sorted(
        sessions,
        key=lambda s: (
            str(s.get("started_at") or s.get("completed_at") or ""),
            int(s.get("id") or 0),
        ),
    )
    labels = [
        f"#{s.get('id', '')}\n{_format_short_date(s.get('started_at') or s.get('completed_at'))}"
        for s in chrono
    ]
    scores = [float(s.get("total_score") or 0.0) for s in chrono]
    return list(range(len(scores))), scores, labels


class HistoryTrendCanvas(QWidget):
    """Widget nhúng FigureCanvasQTAgg vẽ biểu đồ xu hướng điểm số theo thời gian."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        apply_chart_style()

        self.fig = Figure(figsize=(7.5, 2.0), dpi=100)
        self.fig.patch.set_facecolor(SURFACE)
        self.canvas = FigureCanvasQTAgg(self.fig)
        self.ax = self.fig.add_subplot(111)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.canvas)
        self.setFixedHeight(190)

    def draw_empty(self, message: str) -> None:
        """Hiển thị thông điệp nhẹ nhàng ở giữa khi chưa đủ số phiên để vẽ đường."""
        self.ax.clear()
        self.ax.set_facecolor(SURFACE)
        self.ax.text(
            x=0.5,
            y=0.5,
            s=message,
            horizontalalignment="center",
            verticalalignment="center",
            transform=self.ax.transAxes,
            color=CHART_TEXT_MUTED,
            fontsize=11,
        )
        self.ax.set_xticks([])
        self.ax.set_yticks([])
        self.canvas.draw()

    def draw_trend(self, sessions: list[dict[str, Any]]) -> None:
        """Vẽ biểu đồ đường xu hướng từ danh sách các phiên quét."""
        if len(sessions) < 2:
            self.draw_empty("Cần ít nhất 2 phiên phân tích để vẽ biểu đồ xu hướng")
            return

        x_coords, scores, labels = _extract_trend_data(sessions)

        self.ax.clear()
        self.ax.set_facecolor(SURFACE)

        self.ax.plot(
            x_coords,
            scores,
            color=CHART_ACCENT,
            linewidth=2.0,
            marker="o",
            markersize=5.5,
            markerfacecolor="#FFFFFF",
            markeredgecolor=CHART_ACCENT,
            markeredgewidth=2.0,
            zorder=3,
        )

        for idx in (0, -1):
            self.ax.annotate(
                f"{scores[idx]:.1f}",
                xy=(x_coords[idx], scores[idx]),
                xytext=(0, 7),
                textcoords="offset points",
                ha="center",
                fontsize=9,
                fontweight="semibold",
                color=CHART_ACCENT,
            )

        self.ax.set_ylim(-5, 108)
        self.ax.set_yticks([0, 25, 50, 75, 100])
        self.ax.set_xticks(x_coords)
        self.ax.set_xticklabels(labels, fontsize=8)

        self.canvas.draw()


class HistoryView(QWidget):  # pylint: disable=too-many-instance-attributes
    """
    Màn hình Lịch sử phân tích & So sánh chất lượng mã nguồn (HistoryView).

    Tích hợp biểu đồ đường xu hướng phía trên và bảng lịch sử thao tác phía dưới.
    """

    open_session_issues = pyqtSignal(int)
    status_message = pyqtSignal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._project_id: int | None = None
        self._active_worker: RequestWorker | None = None

        self._table_model = HistoryTableModel()
        self.table_view = QTableView()
        self.trend_canvas = HistoryTrendCanvas(self)

        self.empty_state = EmptyState(
            title="Chưa có lịch sử phân tích",
            description="Dự án này chưa có phiên kiểm định nào. Hãy chạy phân tích để ghi nhận.",
        )
        self.content_stack = QStackedLayout()

        self.lbl_count = QLabel("Tổng số phiên: 0")
        self.btn_compare = QPushButton("So sánh 2 phiên")
        self.btn_view_issues = QPushButton("Xem chi tiết lỗi")
        self.btn_delete = QPushButton("Xóa phiên quét")

        self.inline_notice = InlineNotice(parent=self)
        self.inline_notice.setVisible(False)
        self.chart_frame: QFrame | None = None

        self._init_ui()

    def _init_ui(self) -> None:
        """Xây dựng bố cục giao diện hoàn chỉnh theo chuẩn ArtCraft."""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(32, 28, 32, 24)
        main_layout.setSpacing(16)

        # 1. Tiêu đề màn hình chuẩn PageHeader và các nút thao tác
        header = PageHeader(
            title="Lịch sử quét",
            subtitle="Theo dõi xu hướng chất lượng và so sánh kết quả giữa các phiên kiểm định",
            parent=self,
        )

        self.btn_compare.setEnabled(False)
        self.btn_compare.clicked.connect(self._on_compare_clicked)

        self.btn_view_issues.setEnabled(False)
        self.btn_view_issues.clicked.connect(self._on_view_issues_clicked)

        self.btn_delete.setProperty("role", "danger")
        self.btn_delete.setEnabled(False)
        self.btn_delete.clicked.connect(self._on_delete_clicked)

        header.them_nut_phai(self.btn_compare)
        header.them_nut_phai(self.btn_view_issues)
        header.them_nut_phai(self.btn_delete)
        main_layout.addWidget(header)

        main_layout.addWidget(self.inline_notice)

        # 2. Phần biểu đồ xu hướng (đặt trong Panel)
        chart_frame = Panel(self)
        self.chart_frame = chart_frame
        chart_layout = QVBoxLayout(chart_frame)
        chart_layout.setContentsMargins(16, 14, 16, 12)
        chart_layout.setSpacing(6)

        lbl_chart_title = QLabel("Xu hướng điểm số chất lượng qua các phiên kiểm định", chart_frame)
        lbl_chart_title.setStyleSheet("font-size: 13px; font-weight: 600; color: #0F172A; border: none;")
        chart_layout.addWidget(lbl_chart_title)
        chart_layout.addWidget(self.trend_canvas)

        chart_frame.hide()
        main_layout.addWidget(chart_frame)

        # 3. Phần dưới: Bảng dữ liệu và thông tin tổng số phiên
        content_container = self._create_table_section()
        main_layout.addWidget(content_container, 1)

    def _create_table_section(self) -> QWidget:
        """Tạo khu vực bảng dữ liệu và chân trang theo chuẩn ArtCraft."""
        container = QWidget()
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(10)

        # Cài đặt bảng QTableView
        self.table_view.setModel(self._table_model)
        chuan_hoa_bang(self.table_view, cot_gian=1, cot_so=(2, 4, 5, 6))
        self.table_view.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.table_view.doubleClicked.connect(self._on_row_double_clicked)

        sel_model = self.table_view.selectionModel()
        if sel_model:
            sel_model.selectionChanged.connect(self._on_selection_changed)

        table_panel = Panel(self)
        panel_layout = QVBoxLayout(table_panel)
        panel_layout.setContentsMargins(0, 0, 0, 0)
        panel_layout.addWidget(self.table_view)

        self.content_stack.addWidget(table_panel)
        self.content_stack.addWidget(self.empty_state)
        container_layout.addLayout(self.content_stack, 1)

        # Chân trang hiển thị số lượng phiên
        footer_layout = QHBoxLayout()
        footer_layout.setContentsMargins(0, 4, 0, 0)
        self.lbl_count.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 12px; font-family: 'JetBrains Mono', monospace;")
        footer_layout.addStretch()
        footer_layout.addWidget(self.lbl_count)
        container_layout.addLayout(footer_layout)

        return container

    def _on_selection_changed(
        self,
        _selected: QItemSelection,
        _deselected: QItemSelection,
    ) -> None:
        """Cập nhật trạng thái enable/disable của các nút thao tác theo số dòng chọn."""
        selected_indexes = self.table_view.selectionModel().selectedRows()
        count = len(selected_indexes)

        self.btn_compare.setEnabled(count == 2)
        self.btn_view_issues.setEnabled(count == 1)
        self.btn_delete.setEnabled(count >= 1)

    def _on_compare_clicked(self) -> None:
        """Mở hộp thoại so sánh giữa 2 phiên quét đang được chọn."""
        selected_indexes = self.table_view.selectionModel().selectedRows()
        if len(selected_indexes) != 2:
            return

        sess_1 = self._table_model.get_session(selected_indexes[0].row())
        sess_2 = self._table_model.get_session(selected_indexes[1].row())

        if sess_1 and sess_2:
            dialog = ComparisonDialog(sess_1, sess_2, self)
            dialog.exec()

    def _on_view_issues_clicked(self) -> None:
        """Chuyển sang màn hình Issues cho phiên đang được chọn."""
        selected_indexes = self.table_view.selectionModel().selectedRows()
        if len(selected_indexes) != 1:
            return

        sess = self._table_model.get_session(selected_indexes[0].row())
        if sess and sess.get("id") is not None:
            sid = int(sess["id"])
            self.open_session_issues.emit(sid)
            self.status_message.emit(f"Chuyển đến danh sách lỗi của phiên #{sid}.")

    def _on_row_double_clicked(self, index: QModelIndex) -> None:
        """Nhấp đúp chuột vào một phiên để chuyển nhanh sang xem lỗi."""
        sess = self._table_model.get_session(index.row())
        if sess and sess.get("id") is not None:
            sid = int(sess["id"])
            self.open_session_issues.emit(sid)
            self.status_message.emit(f"Chuyển đến danh sách lỗi của phiên #{sid}.")

    def _on_delete_clicked(self) -> None:
        """Xác nhận và xóa một hoặc nhiều phiên quét khỏi cơ sở dữ liệu."""
        selected_indexes = self.table_view.selectionModel().selectedRows()
        if not selected_indexes:
            return

        count = len(selected_indexes)
        confirm = QMessageBox.question(
            self,
            "Xác nhận xóa phiên quét",
            f"Bạn có chắc chắn muốn xóa {count} phiên quét đã chọn khỏi hệ thống?\n"
            "Toàn bộ kết quả điểm số và danh sách lỗi liên quan sẽ bị xóa vĩnh viễn.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return

        deleted_ids: list[int] = []
        for idx in selected_indexes:
            sess = self._table_model.get_session(idx.row())
            if sess and sess.get("id") is not None:
                deleted_ids.append(int(sess["id"]))

        for sid in deleted_ids:
            self._table_model.remove_session(sid)

        self._update_view_state()

        if self._project_id is not None and deleted_ids:
            def _delete_job() -> dict[str, Any]:
                for sid in deleted_ids:
                    api.delete_history(sid)
                return {"status": "ok", "deleted_count": len(deleted_ids)}

            worker = RequestWorker(_delete_job, parent=self)
            self._active_worker = worker
            worker.finished.connect(
                lambda: self.status_message.emit(
                    f"Đã xóa thành công {len(deleted_ids)} phiên quét."
                )
            )
            worker.failed.connect(
                lambda err: self.status_message.emit(
                    f"Lỗi khi xóa phiên quét trên máy chủ: {err}"
                )
            )
            worker.start()
        else:
            self.status_message.emit(f"Đã xóa thành công {len(deleted_ids)} phiên quét.")

    def _update_view_state(self) -> None:
        """Cập nhật biểu đồ, nhãn số lượng và trạng thái rỗng."""
        sessions = self._table_model.get_sessions()
        self.lbl_count.setText(f"Tổng số phiên: {len(sessions)}")

        if not sessions:
            if self.chart_frame is not None:
                self.chart_frame.hide()
            self.content_stack.setCurrentIndex(1)
            self.trend_canvas.draw_empty("Chưa có phiên phân tích nào")
        else:
            if self.chart_frame is not None:
                self.chart_frame.show()
            self.content_stack.setCurrentIndex(0)
            self.trend_canvas.draw_trend(sessions)

    def load_project_history(self, project_id: int) -> None:
        """Tải lịch sử quét của dự án từ backend qua RequestWorker."""
        self._project_id = project_id
        self.inline_notice.setVisible(False)

        worker = RequestWorker(api.list_history, project_id, parent=self)
        self._active_worker = worker

        def _on_loaded(res: dict[str, Any]) -> None:
            sessions = res.get("data")
            if isinstance(sessions, list):
                self._table_model.set_sessions(sessions)
                self._update_view_state()
                self.status_message.emit(f"Đã tải {len(sessions)} phiên quét trong lịch sử.")

        def _on_failed(err_msg: str) -> None:
            self.inline_notice.show_notice(
                f"Lỗi khi tải lịch sử quét: {err_msg}",
                notice_type="error",
                action_text="Thử lại",
            )
            try:
                self.inline_notice.retry_clicked.disconnect()
            except (TypeError, RuntimeError):
                pass
            self.inline_notice.retry_clicked.connect(lambda: self.load_project_history(project_id))
            self.status_message.emit("Không thể tải lịch sử phiên quét.")

        worker.finished.connect(_on_loaded)
        worker.failed.connect(_on_failed)
        worker.start()

    def set_sessions(self, sessions: list[dict[str, Any]], project_id: int | None = None) -> None:
        """Nạp trực tiếp danh sách phiên quét vào màn hình (hỗ trợ kiểm thử/chạy độc lập)."""
        self._project_id = project_id
        self._table_model.set_sessions(sessions)
        self._update_view_state()


def _get_mock_history_sessions() -> list[dict[str, Any]]:
    """Tạo 5 phiên quét mẫu cách nhau vài ngày (điểm tăng từ 45.0 Hạng F lên 79.3 Hạng B)."""
    return [
        {
            "id": 1,
            "project_id": 1,
            "status": "completed",
            "total_files": 42,
            "total_loc": 5200,
            "total_issues": 48,
            "total_score": 45.0,
            "grade": "F",
            "started_at": "2026-11-01 09:15:00",
            "completed_at": "2026-11-01 09:16:30",
            "summary": json.dumps({
                "criteria_scores": {
                    "complexity": 40.0,
                    "security": 42.0,
                    "pylint": 38.0,
                    "health": 60.0,
                    "dependency": 50.0,
                },
                "severity_distribution": {
                    "Critical": 8,
                    "High": 14,
                    "Medium": 16,
                    "Low": 10,
                },
            }),
        },
        {
            "id": 2,
            "project_id": 1,
            "status": "completed",
            "total_files": 43,
            "total_loc": 5350,
            "total_issues": 32,
            "total_score": 58.5,
            "grade": "D",
            "started_at": "2026-11-03 14:20:00",
            "completed_at": "2026-11-03 14:21:40",
            "summary": json.dumps({
                "criteria_scores": {
                    "complexity": 52.0,
                    "security": 55.0,
                    "pylint": 50.0,
                    "health": 70.0,
                    "dependency": 68.0,
                },
                "severity_distribution": {
                    "Critical": 4,
                    "High": 9,
                    "Medium": 12,
                    "Low": 7,
                },
            }),
        },
        {
            "id": 3,
            "project_id": 1,
            "status": "completed",
            "total_files": 44,
            "total_loc": 5420,
            "total_issues": 21,
            "total_score": 68.0,
            "grade": "C",
            "started_at": "2026-11-05 10:45:00",
            "completed_at": "2026-11-05 10:46:15",
            "summary": json.dumps({
                "criteria_scores": {
                    "complexity": 64.0,
                    "security": 68.0,
                    "pylint": 60.0,
                    "health": 75.0,
                    "dependency": 76.0,
                },
                "severity_distribution": {
                    "Critical": 2,
                    "High": 5,
                    "Medium": 9,
                    "Low": 5,
                },
            }),
        },
        {
            "id": 4,
            "project_id": 1,
            "status": "completed",
            "total_files": 45,
            "total_loc": 5500,
            "total_issues": 14,
            "total_score": 74.2,
            "grade": "C",
            "started_at": "2026-11-07 16:30:00",
            "completed_at": "2026-11-07 16:31:25",
            "summary": json.dumps({
                "criteria_scores": {
                    "complexity": 70.0,
                    "security": 76.0,
                    "pylint": 68.0,
                    "health": 80.0,
                    "dependency": 80.0,
                },
                "severity_distribution": {
                    "Critical": 1,
                    "High": 3,
                    "Medium": 6,
                    "Low": 4,
                },
            }),
        },
        {
            "id": 5,
            "project_id": 1,
            "status": "completed",
            "total_files": 45,
            "total_loc": 5540,
            "total_issues": 8,
            "total_score": 79.3,
            "grade": "B",
            "started_at": "2026-11-09 11:00:00",
            "completed_at": "2026-11-09 11:01:18",
            "summary": json.dumps({
                "criteria_scores": {
                    "complexity": 76.0,
                    "security": 84.0,
                    "pylint": 74.0,
                    "health": 82.0,
                    "dependency": 82.0,
                },
                "severity_distribution": {
                    "Critical": 0,
                    "High": 2,
                    "Medium": 4,
                    "Low": 2,
                },
            }),
        },
    ]


def main() -> None:
    """Hàm chạy thử độc lập màn hình Lịch sử & So sánh trong cửa sổ 1100x700."""
    app = QApplication(sys.argv)
    stylesheet = load_stylesheet()
    if stylesheet:
        app.setStyleSheet(stylesheet)

    view = HistoryView()
    view.setWindowTitle("Code Quality & Security Analyzer - Lịch sử quét & So sánh")
    view.resize(1100, 700)

    mock_history = _get_mock_history_sessions()
    view.set_sessions(mock_history)

    view.status_message.connect(lambda msg: print(f"[Status] {msg}"))
    view.open_session_issues.connect(lambda sid: print(f"[Action] Mở phiên sự cố #{sid}"))
    view.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
