"""Màn hình Lịch sử & So sánh các phiên phân tích (HistoryView) theo chuẩn SKILLS.md."""

import sys
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# pylint: disable=wrong-import-position,no-name-in-module
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from PyQt6.QtCore import (
    QItemSelection,
    QModelIndex,
    pyqtSignal,
)
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QStackedLayout,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from frontend.charts.style import (
    CHART_ACCENT,
    CHART_TEXT_MUTED,
    apply_chart_style,
)
from frontend.models.history_model import (
    HistoryTableModel,
    _format_short_date,
)
from frontend.network import api
from frontend.views.dialogs.comparison_dialog import ComparisonDialog
from frontend.views.theme import (
    SURFACE,
    TEXT_MUTED,
)
from frontend.views.widgets.empty_state import EmptyState
from frontend.views.widgets.inline_notice import InlineNotice
from frontend.views.widgets.page_header import PageHeader
from frontend.views.widgets.panel import Panel
from frontend.views.widgets.pill_badge_delegate import PillBadgeDelegate
from frontend.views.widgets.table_utils import chuan_hoa_bang
from frontend.workers.request_worker import RequestWorker


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
        self.table_view.setItemDelegateForColumn(3, PillBadgeDelegate("grade", self.table_view))
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
        elif len(sessions) < 2:
            if self.chart_frame is not None:
                self.chart_frame.hide()
            self.content_stack.setCurrentIndex(0)
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
