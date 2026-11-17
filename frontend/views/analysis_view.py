"""Màn hình Phân tích chi tiết chất lượng mã nguồn (AnalysisView) theo SKILLS.md."""

import json
import logging
import re
import sys
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

logger = logging.getLogger(__name__)

# pylint: disable=wrong-import-position,no-name-in-module,too-many-lines
from PyQt6.QtCore import (
    QSortFilterProxyModel,
    Qt,
    pyqtSignal,
)
from PyQt6.QtWidgets import (
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QStackedLayout,
    QTableView,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from frontend.charts.chart_canvas import AnalysisChartCanvas
from frontend.models.file_summary_model import FileSummaryTableModel
from frontend.controllers.analysis_controller import AnalysisController
from frontend.reports.report_generator import (
    _build_html_report_content,
    _compute_dual_scores,
    _get_grade_for_score,
    _get_score_color,
)
from frontend.views.theme import (
    BORDER_SOFT,
    SURFACE,
    SURFACE_ALT,
    TEXT_MAIN,
    TEXT_MUTED,
    lay_font_code,
)
from frontend.views.widgets.empty_state import EmptyState
from frontend.views.widgets.grade_label import GradeLabel
from frontend.views.widgets.inline_notice import InlineNotice
from frontend.views.widgets.page_header import PageHeader
from frontend.views.widgets.panel import Panel
from frontend.views.widgets.score_bar import ScoreBar
from frontend.views.widgets.severity_badge import SeverityBadge
from frontend.views.widgets.table_utils import chuan_hoa_bang


# pylint: disable=too-many-instance-attributes,too-few-public-methods
class AnalysisView(QWidget):
    """Màn hình Phân tích chất lượng mã nguồn chuyên sâu (AnalysisView)."""

    switch_to_issues = pyqtSignal(int)
    status_message = pyqtSignal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._project_id: int | None = None
        self._project_name: str = "Chưa chọn dự án"
        self._session_id: int | None = None
        self._controller = AnalysisController(self)
        self._controller.analysis_progress.connect(self._on_analysis_progress)
        self._controller.analysis_finished.connect(self._on_analysis_finished)
        self._controller.analysis_failed.connect(self._on_analysis_failed)
        self._controller.status_message.connect(self.status_message.emit)
        self._controller.error_occurred.connect(self._on_analysis_failed)

        self._lbl_title: QLabel | None = None
        self._lbl_meta: QLabel | None = None
        self._btn_reanalyze: QPushButton | None = None
        self._btn_export_html: QPushButton | None = None
        self._current_data: dict[str, Any] = {}
        self._lbl_quality_val: QLabel | None = None
        self._lbl_security_val: QLabel | None = None
        self._notice: InlineNotice | None = None

        self._score_stack: QStackedLayout | None = None
        self._grade_label: GradeLabel | None = None
        self._score_bars: dict[str, ScoreBar] = {}

        self._lbl_scanning_step: QLabel | None = None
        self._progress_bar: QProgressBar | None = None
        self._btn_cancel_scan: QPushButton | None = None

        self._lbl_crit_cnt: QLabel | None = None
        self._lbl_high_cnt: QLabel | None = None
        self._lbl_med_cnt: QLabel | None = None
        self._lbl_low_cnt: QLabel | None = None

        self._lbl_loc: QLabel | None = None
        self._lbl_files: QLabel | None = None
        self._lbl_issues: QLabel | None = None

        self._file_table_model = FileSummaryTableModel([], self)
        self._proxy_model = QSortFilterProxyModel(self)
        self._proxy_model.setSourceModel(self._file_table_model)

        self._canvas_radar: AnalysisChartCanvas | None = None
        self._canvas_top_risk: AnalysisChartCanvas | None = None
        self._tab_widget: QTabWidget | None = None
        self._score_container: QWidget | None = None

        self._setup_ui()

    def _setup_ui(self) -> None:
        """Khởi tạo bố cục các khối giao diện phân tích theo chuẩn ArtCraft."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 28, 32, 24)
        layout.setSpacing(16)

        layout.addWidget(self._create_header_bar())

        self._notice = InlineNotice("", "error", "Thử lại", self)
        self._notice.retry_clicked.connect(self.start_analysis)
        self._notice.hide()
        layout.addWidget(self._notice)

        score_container = QWidget(self)
        self._score_container = score_container
        self._score_stack = QStackedLayout(score_container)
        self._score_stack.setContentsMargins(0, 0, 0, 0)

        self._score_stack.addWidget(self._create_results_block())
        self._score_stack.addWidget(self._create_scanning_block())
        self._score_stack.addWidget(self._create_empty_block())
        self._score_stack.setCurrentIndex(2)
        layout.addWidget(score_container)

        self._tab_widget = QTabWidget(self)
        self._tab_widget.addTab(self._create_overview_tab(), "Tổng quan")
        self._tab_widget.addTab(self._create_files_tab(), "Theo tệp tin")
        self._tab_widget.addTab(self._create_charts_tab(), "Biểu đồ")
        layout.addWidget(self._tab_widget, stretch=1)
        self._tab_widget.hide()

    def _create_header_bar(self) -> QWidget:
        """Tạo thanh tiêu đề và nút Phân tích lại."""
        header = PageHeader(
            title=self._project_name,
            subtitle="Chưa có phiên phân tích nào",
            parent=self,
        )
        self._lbl_title = header.lbl_title
        self._lbl_meta = header.lbl_subtitle

        self._btn_export_html = QPushButton("Xuất báo cáo", self)
        self._btn_export_html.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_export_html.clicked.connect(self._on_export_html_report)
        header.them_nut_phai(self._btn_export_html)
        self._btn_export_html.hide()

        self._btn_reanalyze = QPushButton("Phân tích lại", self)
        self._btn_reanalyze.setProperty("role", "primary")
        self._btn_reanalyze.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_reanalyze.clicked.connect(self.start_analysis)

        header.them_nut_phai(self._btn_reanalyze)
        self._btn_reanalyze.hide()
        return header

    def _create_flat_metric_card(
        self,
        title: str,
        subtitle: str,
        parent: QWidget,
    ) -> tuple[QFrame, QLabel]:
        """Tạo thẻ chỉ số phẳng nền SURFACE, viền BORDER_SOFT, bo góc 6px."""
        card = QFrame(parent)
        card.setStyleSheet(
            f"QFrame {{ background-color: {SURFACE}; border: 1px solid {BORDER_SOFT}; "
            f"border-radius: 6px; }} QLabel {{ border: none; background: transparent; }}"
        )
        vbox = QVBoxLayout(card)
        vbox.setContentsMargins(12, 8, 12, 8)
        vbox.setSpacing(2)

        lbl_title = QLabel(title, card)
        lbl_title.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 11px; font-weight: 600;")

        lbl_score = QLabel("— / 100", card)
        lbl_score.setFont(lay_font_code(14))
        lbl_score.setStyleSheet(f"color: {TEXT_MAIN}; font-weight: bold;")

        lbl_sub = QLabel(subtitle, card)
        lbl_sub.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 10px;")

        vbox.addWidget(lbl_title)
        vbox.addWidget(lbl_score)
        vbox.addWidget(lbl_sub)
        return card, lbl_score

    def _create_results_block(self) -> QWidget:
        """Tạo khối hiển thị điểm tổng, 2 thẻ chỉ số phẳng và 6 thanh tiêu chí (State 0)."""
        card = QFrame(self)
        card.setStyleSheet(
            f"QFrame {{ background-color: {SURFACE};"
            f" border: 1px solid {BORDER_SOFT}; border-radius: 6px; }}"
        )
        h_layout = QHBoxLayout(card)
        h_layout.setContentsMargins(20, 16, 20, 16)
        h_layout.setSpacing(20)

        left_col = QWidget(card)
        left_col.setFixedWidth(160)
        left_layout = QVBoxLayout(left_col)
        left_layout.setContentsMargins(0, 0, 0, 0)
        self._grade_label = GradeLabel("A", 100.0, left_col)
        left_layout.addWidget(self._grade_label, alignment=Qt.AlignmentFlag.AlignCenter)
        h_layout.addWidget(left_col)

        # Cột 2 thẻ chỉ số phẳng: Chất lượng Code & An toàn Bảo mật
        dual_col = QWidget(card)
        dual_col.setFixedWidth(240)
        dual_layout = QVBoxLayout(dual_col)
        dual_layout.setContentsMargins(0, 0, 0, 0)
        dual_layout.setSpacing(10)

        card_qual, self._lbl_quality_val = self._create_flat_metric_card(
            "Chất lượng Code",
            "Cấu trúc, PEP8, độ phức tạp",
            dual_col,
        )
        card_sec, self._lbl_security_val = self._create_flat_metric_card(
            "An toàn Bảo mật",
            "SAST, CVE, hành vi mã độc",
            dual_col,
        )
        dual_layout.addWidget(card_qual)
        dual_layout.addWidget(card_sec)
        h_layout.addWidget(dual_col)

        v_line = QFrame(card)
        v_line.setFixedWidth(1)
        v_line.setStyleSheet(f"background-color: {BORDER_SOFT}; border: none;")
        h_layout.addWidget(v_line)

        right_col = QWidget(card)
        right_layout = QVBoxLayout(right_col)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(8)

        criteria_keys = (
            "complexity",
            "security",
            "pylint",
            "health",
            "dependency",
            "malware",
        )
        for key in criteria_keys:
            score_bar = ScoreBar(key, score=0.0, parent=right_col)
            self._score_bars[key] = score_bar
            right_layout.addWidget(score_bar)

        h_layout.addWidget(right_col, stretch=1)
        return card

    def _create_scanning_block(self) -> QWidget:
        """Tạo khối tiến trình đang quét động thời gian thực (State 1)."""
        card = QFrame(self)
        card.setStyleSheet(
            f"QFrame {{ background-color: {SURFACE};"
            f" border: 1px solid {BORDER_SOFT}; border-radius: 4px; }}"
        )
        v_layout = QVBoxLayout(card)
        v_layout.setContentsMargins(32, 24, 32, 24)
        v_layout.setSpacing(12)
        v_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        lbl_scan_tag = QLabel("ĐANG TIẾN HÀNH KIỂM ĐỊNH MÃ NGUỒN", card)
        lbl_scan_tag.setStyleSheet("color: #1F5FA8; font-weight: 600; font-size: 12px;")

        self._lbl_scanning_step = QLabel("Đang chuẩn bị phiên quét...", card)
        self._lbl_scanning_step.setStyleSheet(
            f"color: {TEXT_MAIN}; font-size: 14px; font-weight: 500;"
        )

        self._progress_bar = QProgressBar(card)
        self._progress_bar.setRange(0, 100)
        self._progress_bar.setValue(0)
        self._progress_bar.setFixedHeight(8)
        self._progress_bar.setTextVisible(False)
        self._progress_bar.setStyleSheet(
            f"QProgressBar {{ background-color: {SURFACE_ALT}; border: none; border-radius: 4px; }}"
            f"QProgressBar::chunk {{ background-color: #1F5FA8; border-radius: 4px; }}"
        )

        self._btn_cancel_scan = QPushButton("Hủy phân tích", card)
        self._btn_cancel_scan.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_cancel_scan.clicked.connect(self._cancel_scan)

        v_layout.addWidget(lbl_scan_tag, alignment=Qt.AlignmentFlag.AlignCenter)
        v_layout.addWidget(self._lbl_scanning_step, alignment=Qt.AlignmentFlag.AlignCenter)
        v_layout.addWidget(self._progress_bar)
        v_layout.addWidget(self._btn_cancel_scan, alignment=Qt.AlignmentFlag.AlignCenter)
        return card

    def _create_empty_block(self) -> QWidget:
        """Tạo khối trạng thái rỗng khi dự án chưa được phân tích (State 2)."""
        empty = EmptyState(
            title="Dự án này chưa được phân tích",
            description=(
                "Bấm 'Bắt đầu phân tích' để kiểm tra toàn diện chất lượng, "
                "quy chuẩn PEP8 và an toàn mã nguồn."
            ),
            action_text="Bắt đầu phân tích",
            parent=self,
        )
        empty.action_clicked.connect(self.start_analysis)
        return empty

    def _create_severity_row(self, container: QWidget) -> QHBoxLayout:
        """Tạo hàng 4 thẻ mức độ lỗi."""
        sev_row = QHBoxLayout()
        sev_row.setSpacing(14)

        self._lbl_crit_cnt = QLabel("0", container)
        self._lbl_high_cnt = QLabel("0", container)
        self._lbl_med_cnt = QLabel("0", container)
        self._lbl_low_cnt = QLabel("0", container)

        levels = (
            ("Critical", self._lbl_crit_cnt),
            ("High", self._lbl_high_cnt),
            ("Medium", self._lbl_med_cnt),
            ("Low", self._lbl_low_cnt),
        )
        for lvl, lbl_w in levels:
            cell = QFrame(container)
            cell.setObjectName("StatCard")
            cell.setStyleSheet(
                f"QFrame#StatCard {{ background-color: {SURFACE};"
                f" border: 1px solid {BORDER_SOFT}; border-radius: 6px; }}"
                f"QLabel {{ border: none; background: transparent; }}"
            )
            c_layout = QVBoxLayout(cell)
            c_layout.setContentsMargins(14, 12, 14, 12)
            c_layout.setSpacing(8)
            c_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

            badge = SeverityBadge(lvl, show_vietnamese=True, parent=cell)
            lbl_w.setStyleSheet(
                f"font-size: 24px; font-weight: bold; color: {TEXT_MAIN};"
                f" border: none; background: transparent;"
            )

            c_layout.addWidget(badge)
            c_layout.addWidget(lbl_w)
            sev_row.addWidget(cell)
        return sev_row

    def _create_metrics_row(self, container: QWidget) -> QHBoxLayout:
        """Tạo hàng thống kê số lượng file, LOC và tổng lỗi."""
        info_row = QHBoxLayout()
        info_row.setSpacing(14)

        self._lbl_files = QLabel("—", container)
        self._lbl_loc = QLabel("—", container)
        self._lbl_issues = QLabel("—", container)

        metrics = (
            ("Tổng số tệp tin", self._lbl_files),
            ("Tổng số dòng mã", self._lbl_loc),
            ("Tổng số lỗi phát hiện", self._lbl_issues),
        )
        for title, val_lbl in metrics:
            item_box = QFrame(container)
            item_box.setObjectName("StatCard")
            item_box.setStyleSheet(
                f"QFrame#StatCard {{ background-color: {SURFACE};"
                f" border: 1px solid {BORDER_SOFT}; border-radius: 6px; }}"
                f"QLabel {{ border: none; background: transparent; }}"
            )
            i_layout = QVBoxLayout(item_box)
            i_layout.setContentsMargins(16, 12, 16, 12)
            i_layout.setSpacing(6)

            lbl_t = QLabel(title, item_box)
            lbl_t.setStyleSheet(
                f"color: {TEXT_MUTED}; font-size: 12px; font-weight: 500;"
                f" border: none; background: transparent;"
            )
            val_lbl.setStyleSheet(
                f"font-size: 24px; font-weight: bold; color: {TEXT_MAIN};"
                f" border: none; background: transparent;"
            )

            i_layout.addWidget(lbl_t)
            i_layout.addWidget(val_lbl)
            info_row.addWidget(item_box)
        return info_row

    def _create_overview_tab(self) -> QWidget:
        """Tạo giao diện Tab 1: Tổng quan chỉ số."""
        container = QWidget(self)
        v_layout = QVBoxLayout(container)
        v_layout.setContentsMargins(16, 16, 16, 16)
        v_layout.setSpacing(16)

        v_layout.addLayout(self._create_severity_row(container))
        v_layout.addLayout(self._create_metrics_row(container))

        jump_bar = QHBoxLayout()
        jump_bar.addStretch()
        btn_jump = QPushButton("Xem toàn bộ danh sách lỗi trong bảng Issues →", container)
        btn_jump.setProperty("role", "primary")
        btn_jump.setFixedHeight(34)
        btn_jump.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_jump.clicked.connect(self._on_jump_to_issues)
        jump_bar.addWidget(btn_jump)
        v_layout.addLayout(jump_bar)
        v_layout.addStretch()

        return container

    def _create_files_tab(self) -> QWidget:
        """Tạo giao diện Tab 2: Thống kê chi tiết theo tệp tin trong Panel."""
        container = QWidget(self)
        v_layout = QVBoxLayout(container)
        v_layout.setContentsMargins(16, 16, 16, 16)
        v_layout.setSpacing(10)

        panel = Panel(container)
        p_layout = QVBoxLayout(panel)
        p_layout.setContentsMargins(0, 0, 0, 0)

        table = QTableView(panel)
        table.setModel(self._proxy_model)
        chuan_hoa_bang(table, cot_gian=0, cot_so=(1, 2, 3, 4, 5, 6, 7))
        table.setSelectionMode(QTableView.SelectionMode.SingleSelection)
        table.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        table.setSortingEnabled(True)

        p_layout.addWidget(table)
        v_layout.addWidget(panel)
        return container

    def _create_charts_tab(self) -> QWidget:
        """Tạo giao diện Tab 3: Nhúng biểu đồ Matplotlib phẳng."""
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("border: none; background: transparent;")

        container = QWidget()
        v_layout = QVBoxLayout(container)
        v_layout.setContentsMargins(16, 16, 16, 16)
        v_layout.setSpacing(16)

        charts_row = QHBoxLayout()
        charts_row.setSpacing(16)

        radar_panel = Panel(container)
        rp_layout = QVBoxLayout(radar_panel)
        rp_layout.setContentsMargins(12, 12, 12, 12)
        self._canvas_radar = AnalysisChartCanvas(radar_panel, width=4.8, height=3.6)
        rp_layout.addWidget(self._canvas_radar)

        risk_panel = Panel(container)
        rk_layout = QVBoxLayout(risk_panel)
        rk_layout.setContentsMargins(12, 12, 12, 12)
        self._canvas_top_risk = AnalysisChartCanvas(risk_panel, width=5.2, height=3.6)
        rk_layout.addWidget(self._canvas_top_risk)

        charts_row.addWidget(radar_panel, 1)
        charts_row.addWidget(risk_panel, 1)
        v_layout.addLayout(charts_row)

        btn_bar = QHBoxLayout()
        btn_bar.addStretch()

        btn_save = QPushButton("Lưu ảnh biểu đồ (PNG)", container)
        btn_save.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_save.clicked.connect(self._save_charts_image)
        btn_bar.addWidget(btn_save)

        v_layout.addLayout(btn_bar)
        scroll.setWidget(container)
        return scroll

    def set_project(self, project: dict[str, Any]) -> None:
        """Nạp dự án vào màn hình phân tích."""
        self._project_id = int(project["id"])
        self._project_name = str(project.get("name", "Dự án"))

        if self._lbl_title:
            self._lbl_title.setText(self._project_name)

        if project.get("total_score") is not None:
            self.load_session_data(project)
        else:
            if self._score_stack:
                self._score_stack.setCurrentIndex(2)
            if hasattr(self, "_tab_widget") and self._tab_widget:
                self._tab_widget.hide()
            if self._btn_reanalyze:
                self._btn_reanalyze.hide()
            if self._btn_export_html:
                self._btn_export_html.hide()
            if self._lbl_meta:
                self._lbl_meta.setText("Chưa có phiên phân tích nào")
            if self._notice:
                self._notice.hide()

    def _update_severity_labels(self, sev_dist: dict[str, int]) -> None:
        """Cập nhật các số liệu lỗi trên giao diện."""
        if self._lbl_crit_cnt:
            self._lbl_crit_cnt.setText(str(sev_dist.get("Critical", 0)))
        if self._lbl_high_cnt:
            self._lbl_high_cnt.setText(str(sev_dist.get("High", 0)))
        if self._lbl_med_cnt:
            self._lbl_med_cnt.setText(str(sev_dist.get("Medium", 0)))
        if self._lbl_low_cnt:
            self._lbl_low_cnt.setText(str(sev_dist.get("Low", 0)))

    def _update_overview_counts(  # pylint: disable=too-many-branches
        self,
        data: dict[str, Any],
        total_issues: int,
    ) -> None:
        """Cập nhật các chỉ số tổng quan."""
        if self._lbl_meta:
            self._lbl_meta.setText(f"Lần phân tích cuối: Vừa xong · {total_issues} lỗi phát hiện")
        if self._lbl_issues:
            self._lbl_issues.setText(str(total_issues))

        loc_val = data.get("total_loc")
        files_val = data.get("total_files")

        # Trích xuất fallback từ summary nếu có
        summary = data.get("summary")
        if (loc_val is None or files_val is None) and summary:
            if isinstance(summary, str):
                try:
                    s_dict = json.loads(summary)
                    if loc_val is None:
                        loc_val = s_dict.get("total_loc")
                    if files_val is None:
                        files_val = s_dict.get("total_files")
                except (json.JSONDecodeError, TypeError, KeyError) as err:
                    logger.debug("Bỏ qua lỗi trích xuất summary: %s", err)
            elif isinstance(summary, dict):
                if loc_val is None:
                    loc_val = summary.get("total_loc")
                if files_val is None:
                    files_val = summary.get("total_files")

        if files_val is None:
            flist = data.get("file_summary") or data.get("top_risk_files")
            if isinstance(flist, list) and flist:
                files_val = len(flist)

        if self._lbl_loc:
            if isinstance(loc_val, (int, float)) and loc_val > 0:
                self._lbl_loc.setText(f"{int(loc_val):,}")
            else:
                self._lbl_loc.setText("—")

        if self._lbl_files:
            self._lbl_files.setText(str(files_val) if files_val is not None else "—")

    @staticmethod
    def _set_metric_score_label(label: QLabel | None, score: float) -> None:
        """Cập nhật giá trị và màu sắc theo thang điểm."""
        if not label:
            return
        bounded = max(0.0, min(100.0, float(score)))
        color = _get_score_color(bounded)
        score_text = f"{int(bounded)}" if bounded.is_integer() else f"{bounded:.1f}"
        label.setText(f"{score_text} / 100")
        label.setStyleSheet(f"color: {color}; font-weight: bold; font-size: 14px;")

    def load_session_data(self, data: dict[str, Any]) -> None:
        """Cập nhật toàn bộ giao diện từ kết quả phân tích."""
        if self._notice:
            self._notice.hide()

        self._current_data = dict(data)
        self._session_id = data.get("session_id") or data.get("id")
        score = float(data.get("total_score", 0.0))
        grade = str(data.get("grade") or _get_grade_for_score(score))

        if self._score_stack:
            self._score_stack.setCurrentIndex(0)
        if hasattr(self, "_tab_widget") and self._tab_widget:
            self._tab_widget.show()
        if self._btn_export_html:
            self._btn_export_html.show()
        if self._btn_reanalyze:
            self._btn_reanalyze.setText("Phân tích lại")
            self._btn_reanalyze.show()

        if self._grade_label:
            self._grade_label.set_grade_and_score(grade, score)

        crit_scores = data.get("criteria_scores", {})
        q_score, s_score = _compute_dual_scores(
            crit_scores, data.get("quality_score"), data.get("security_score"), score
        )
        self._set_metric_score_label(self._lbl_quality_val, q_score)
        self._set_metric_score_label(self._lbl_security_val, s_score)

        for key, score_bar_item in self._score_bars.items():
            val = float(crit_scores.get(key, 0.0))
            score_bar_item.set_score(val, animate=True)

        sev_dist = data.get("severity_distribution", {})
        self._update_severity_labels(sev_dist)

        total_issues = data.get("total_issues", sum(sev_dist.values()))
        self._update_overview_counts(data, total_issues)

        all_files = data.get("file_summary") or data.get("top_risk_files", [])
        self._file_table_model.set_files(all_files)

        top_files = data.get("top_risk_files") or all_files[:5]
        if self._canvas_radar:
            self._canvas_radar.draw_criteria_radar(crit_scores)
        if self._canvas_top_risk:
            self._canvas_top_risk.draw_top_risk_bar(top_files)

    def start_analysis(self) -> None:
        """Khởi động luồng phân tích bất đồng bộ cho dự án hiện tại."""
        if not self._project_id:
            if self._notice:
                self._notice.set_notice("Vui lòng chọn một dự án trước khi phân tích.", "warning")
                self._notice.show()
            return

        if self._score_stack:
            self._score_stack.setCurrentIndex(1)
        if hasattr(self, "_tab_widget") and self._tab_widget:
            self._tab_widget.hide()
        if self._btn_export_html:
            self._btn_export_html.hide()
        if self._progress_bar:
            self._progress_bar.setValue(5)
        if self._lbl_scanning_step:
            self._lbl_scanning_step.setText("Khởi tạo kết nối tới máy chủ phân tích...")

        self.status_message.emit(f"Bắt đầu phân tích dự án '{self._project_name}'...")
        self._controller.start_analysis(self._project_id)

    def _cancel_scan(self) -> None:
        """Hủy tiến trình phân tích theo lệnh người dùng."""
        self._controller.cancel_analysis()

    def _on_analysis_progress(self, msg: str, pct: int) -> None:
        """Cập nhật giao diện theo từng bước phân tích."""
        if self._lbl_scanning_step:
            self._lbl_scanning_step.setText(msg)
        if self._progress_bar:
            self._progress_bar.setValue(pct)

    def _on_analysis_finished(self, response: dict[str, Any]) -> None:
        """Xử lý kết quả phân tích hoàn tất từ Backend."""
        data = response.get("data", response)
        self.load_session_data(data)
        self.status_message.emit("Hoàn thành phân tích dự án thành công!")

    def _on_analysis_failed(self, error_msg: str) -> None:
        """Xử lý khi tiến trình phân tích gặp lỗi."""
        if self._score_stack:
            self._score_stack.setCurrentIndex(2)
        if self._btn_export_html:
            self._btn_export_html.hide()
        if self._notice:
            self._notice.set_notice(f"Phân tích thất bại: {error_msg}", "error", "Thử lại")
            self._notice.show()
        self.status_message.emit("Phân tích thất bại.")

    def _on_jump_to_issues(self) -> None:
        """Phát tín hiệu chuyển tab sang màn hình Issues."""
        if self._session_id:
            self.switch_to_issues.emit(int(self._session_id))
        else:
            self.status_message.emit("Chưa có phiên phân tích để xem lỗi.")

    def _save_charts_image(self) -> None:
        """Hộp thoại lưu ảnh biểu đồ PNG."""
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Lưu biểu đồ phân tích",
            "analysis_chart.png",
            "Ảnh PNG (*.png)",
        )
        if file_path and self._canvas_radar:
            if self._canvas_radar.save_chart(file_path):
                self.status_message.emit(f"Đã lưu biểu đồ thành công: {file_path}")
            else:
                self.status_message.emit("Lưu biểu đồ thất bại.")

    def _on_export_html_report(self) -> None:
        """Hộp thoại lưu báo cáo HTML độc lập chuẩn kỹ thuật."""
        safe_name = re.sub(r"[^\w\-]", "_", self._project_name.lower())
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Xuất báo cáo HTML",
            f"bao_cao_{safe_name}.html",
            "Trang web HTML (*.html)",
        )
        if not file_path:
            return

        html_content = self.generate_html_report()
        self._controller.save_report_file(file_path, html_content)

    def _collect_critical_high_issues(self, data: dict[str, Any]) -> list[dict[str, Any]]:
        """Lọc và trả về danh sách lỗi Critical / High từ dữ liệu hoặc Controller."""
        return self._controller.collect_critical_high_issues(self._session_id, data)

    def generate_html_report(self) -> str:
        """Tạo mã nguồn HTML báo cáo kỹ thuật độc lập hỗ trợ in ấn (Ctrl+P xuất PDF)."""
        data = self._current_data or {}
        score = float(data.get("total_score", 0.0))
        grade = str(data.get("grade") or _get_grade_for_score(score))
        crit_scores = data.get("criteria_scores", {})
        q_score, s_score = _compute_dual_scores(
            crit_scores, data.get("quality_score"), data.get("security_score"), score
        )

        crit_high = self._collect_critical_high_issues(data)
        report_meta = {
            "project_name": self._project_name,
            "session_id": self._session_id,
            "total_score": score,
            "grade": grade,
            "quality_score": q_score,
            "security_score": s_score,
            "loc_text": self._lbl_loc.text() if self._lbl_loc else "—",
            "files_text": self._lbl_files.text() if self._lbl_files else "—",
            "issues_text": self._lbl_issues.text() if self._lbl_issues else "0",
            "sev_dist": data.get("severity_distribution", {}),
        }
        radar_b64 = self._canvas_radar.export_base64_png() if self._canvas_radar else ""
        risk_b64 = self._canvas_top_risk.export_base64_png() if self._canvas_top_risk else ""

        return _build_html_report_content(
            report_meta, crit_scores, radar_b64, risk_b64, crit_high
        )
