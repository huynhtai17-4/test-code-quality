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

# pylint: disable=wrong-import-position,no-name-in-module
from PyQt6.QtCore import (
    QSortFilterProxyModel,
    Qt,
    pyqtSignal,
)
from PyQt6.QtWidgets import (
    QFileDialog,
    QPushButton,
    QScrollArea,
    QStackedLayout,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from frontend.controllers.analysis_controller import AnalysisController
from frontend.models.file_summary_model import FileSummaryTableModel
from frontend.reports.report_generator import (
    _build_html_report_content,
    _compute_dual_scores,
    _get_grade_for_score,
)
from frontend.views.components.analysis_charts_tab import AnalysisChartsTab
from frontend.views.components.analysis_files_tab import AnalysisFilesTab
from frontend.views.components.analysis_overview_tab import AnalysisOverviewTab
from frontend.views.components.analysis_scanning_block import AnalysisScanningBlock
from frontend.views.components.analysis_score_block import AnalysisScoreBlock
from frontend.views.widgets.empty_state import EmptyState
from frontend.views.widgets.inline_notice import InlineNotice
from frontend.views.widgets.page_header import PageHeader


# pylint: disable=too-many-instance-attributes
class AnalysisView(QWidget):
    """Màn hình Phân tích chất lượng mã nguồn chuyên sâu (AnalysisView)."""

    analysis_completed = pyqtSignal(dict)
    switch_to_issues = pyqtSignal(int)
    status_message = pyqtSignal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._project_id: int | None = None
        self._project_name: str = "Chưa chọn dự án"
        self._session_id: int | None = None
        self._current_data: dict[str, Any] = {}

        self._controller = AnalysisController(self)
        self._controller.analysis_progress.connect(self._on_analysis_progress)
        self._controller.analysis_finished.connect(self._on_analysis_finished)
        self._controller.analysis_failed.connect(self._on_analysis_failed)
        self._controller.status_message.connect(self.status_message.emit)
        self._controller.error_occurred.connect(self._on_analysis_failed)

        self._header: PageHeader | None = None
        self._btn_reanalyze: QPushButton | None = None
        self._btn_export_html: QPushButton | None = None
        self._notice: InlineNotice | None = None
        self._score_stack: QStackedLayout | None = None
        self._tab_widget: QTabWidget | None = None

        # Components con
        self._score_block = AnalysisScoreBlock(self)
        self._scanning_block = AnalysisScanningBlock(self)
        self._overview_tab = AnalysisOverviewTab(self)
        self._files_tab = AnalysisFilesTab(self)
        self._charts_tab = AnalysisChartsTab(self)

        self._file_table_model = FileSummaryTableModel([], self)
        self._proxy_model = QSortFilterProxyModel(self)
        self._proxy_model.setSourceModel(self._file_table_model)
        self._files_tab.set_model(self._proxy_model)

        self._setup_ui()

    def _setup_ui(self) -> None:
        """Khởi tạo bố cục cuộn dọc và gắn các component con."""
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)

        scroll_area = QScrollArea(self)
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet("border: none; background: transparent;")

        content_widget = QWidget()
        layout = QVBoxLayout(content_widget)
        layout.setContentsMargins(32, 28, 32, 28)
        layout.setSpacing(20)

        self._header = self._create_header_bar()
        layout.addWidget(self._header)

        self._notice = InlineNotice(parent=content_widget)
        self._notice.hide()
        layout.addWidget(self._notice)

        # QStackedLayout: 0=Results, 1=Scanning, 2=Empty
        self._score_stack = QStackedLayout()
        self._score_stack.addWidget(self._score_block)
        self._score_stack.addWidget(self._scanning_block)
        empty_block = self._create_empty_block()
        self._score_stack.addWidget(empty_block)
        self._score_stack.setCurrentIndex(2)

        stack_container = QWidget(content_widget)
        stack_container.setLayout(self._score_stack)
        layout.addWidget(stack_container)

        # Tab Widget
        self._tab_widget = QTabWidget(content_widget)
        self._tab_widget.addTab(self._overview_tab, "Tổng quan")
        self._tab_widget.addTab(self._files_tab, "Theo tệp tin")
        self._tab_widget.addTab(self._charts_tab, "Biểu đồ")
        self._tab_widget.hide()
        layout.addWidget(self._tab_widget, stretch=1)

        # Liên kết sự kiện của components
        self._scanning_block.cancel_requested.connect(self._cancel_scan)
        self._overview_tab.jump_to_issues_requested.connect(self._on_jump_to_issues)
        self._charts_tab.save_chart_clicked.connect(self._save_charts_image)

        scroll_area.setWidget(content_widget)
        root_layout.addWidget(scroll_area)

    def _create_header_bar(self) -> PageHeader:
        """Tạo thanh tiêu đề chuẩn PageHeader với các nút tác vụ."""
        header = PageHeader(
            title=self._project_name,
            subtitle="Chưa có dữ liệu phân tích",
            parent=self,
        )

        self._btn_export_html = QPushButton("Xuất báo cáo", self)
        self._btn_export_html.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_export_html.clicked.connect(self._on_export_html_report)
        header.them_nut_phai(self._btn_export_html)
        self._btn_export_html.hide()

        self._btn_reanalyze = QPushButton("Bắt đầu phân tích", self)
        self._btn_reanalyze.setProperty("role", "primary")
        self._btn_reanalyze.setStyleSheet(
            "QPushButton {"
            "  background-color: #0F172A;"
            "  color: #FFFFFF;"
            "  border: 1px solid #0F172A;"
            "  border-radius: 4px;"
            "  padding: 6px 18px;"
            "  font-weight: 600;"
            "  font-size: 13px;"
            "  min-height: 32px;"
            "}"
            "QPushButton:hover {"
            "  background-color: #1E293B;"
            "  border-color: #1E293B;"
            "}"
        )
        self._btn_reanalyze.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_reanalyze.clicked.connect(self.start_analysis)
        header.them_nut_phai(self._btn_reanalyze)
        self._btn_reanalyze.show()

        return header

    def _create_empty_block(self) -> QWidget:
        """Tạo khối trạng thái rỗng khi dự án chưa được phân tích."""
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

    def set_project(self, project: dict[str, Any]) -> None:
        """Thiết lập thông tin dự án mục tiêu cho màn hình phân tích."""
        self._project_id = project.get("id")
        self._project_name = project.get("name") or "Dự án không tên"
        if self._header:
            self._header.set_title(self._project_name)
            project_path = project.get("path", "—")
            self._header.set_subtitle(f"Mã dự án #{self._project_id} · Đường dẫn: {project_path}")

        latest_session = project.get("latest_session")
        if latest_session and isinstance(latest_session, dict):
            if self._btn_reanalyze:
                self._btn_reanalyze.setText("Phân tích lại")
                self._btn_reanalyze.show()
            self.load_session_data(latest_session)
        else:
            if self._btn_reanalyze:
                self._btn_reanalyze.setText("Bắt đầu phân tích")
                self._btn_reanalyze.show()
            if self._score_stack:
                self._score_stack.setCurrentIndex(2)
            if self._tab_widget:
                self._tab_widget.hide()
            if self._btn_export_html:
                self._btn_export_html.hide()

    def load_session_data(self, data: dict[str, Any]) -> None:  # pylint: disable=too-many-locals
        """Nạp dữ liệu phiên phân tích vào các components giao diện."""
        if not data:
            return

        self._current_data = data
        self._session_id = data.get("id") or data.get("session_id")

        if self._btn_reanalyze:
            self._btn_reanalyze.show()
        if self._btn_export_html:
            self._btn_export_html.show()
        if self._notice:
            self._notice.hide()
        if self._score_stack:
            self._score_stack.setCurrentIndex(0)
        if self._tab_widget:
            self._tab_widget.show()

        total_score = float(data.get("total_score") or data.get("score") or 0.0)
        overall_grade = str(data.get("grade") or _get_grade_for_score(total_score))

        summary = data.get("summary")
        if isinstance(summary, str):
            try:
                summary = json.loads(summary)
            except (json.JSONDecodeError, TypeError):
                summary = {}
        elif not isinstance(summary, dict):
            summary = {}

        crit_scores = summary.get("criteria_scores") or data.get("criteria_scores") or {}
        if not crit_scores:
            sec_cnt = float(data.get("security_issues_count") or 0.0)
            crit_scores = {
                "complexity": float(data.get("maintainability_index") or 0.0),
                "security": max(0.0, 100.0 - sec_cnt * 10) if sec_cnt else 100.0,
                "pylint": float(data.get("pylint_score") or 0.0) * 10.0,
                "health": 80.0,
                "dependency": 90.0,
                "malware": 100.0,
            }

        quality_score, security_score = _compute_dual_scores(
            crit_scores,
            summary.get("quality_score") or data.get("quality_score"),
            summary.get("security_score") or data.get("security_score"),
            total_score,
        )

        self._score_block.update_scores(
            total_score,
            overall_grade,
            quality_score,
            security_score,
            crit_scores,
        )

        sev_dist = summary.get("severity_distribution") or data.get("severity_distribution") or {}
        self._overview_tab.update_severity_labels(sev_dist)

        total_files = (
            summary.get("total_files")
            or data.get("total_files")
            or data.get("files_count")
            or len(summary.get("file_summary", []))
            or len(data.get("file_summary", []))
        )
        total_loc = (
            summary.get("total_loc")
            or data.get("total_loc")
            or data.get("loc")
        )
        total_issues = (
            data.get("total_issues")
            or summary.get("total_issues")
            or data.get("total_issues_count")
            or (sum(int(v) for v in sev_dist.values()) if sev_dist else 0)
        )
        self._overview_tab.update_overview_counts(
            total_files,
            total_loc,
            total_issues,
        )

        all_files = (
            summary.get("file_summary")
            or summary.get("file_metrics")
            or data.get("file_summary")
            or data.get("file_metrics")
            or data.get("files")
            or []
        )
        self._file_table_model.set_files(all_files)

        top_files = summary.get("top_risk_files") or data.get("top_risk_files") or all_files[:5]
        self._charts_tab.draw_charts(crit_scores, top_files)

        session_review = (
            summary.get("session_review")
            or data.get("session_review")
            or {}
        )
        self._overview_tab.update_ai_review(session_review)

    def start_analysis(self) -> None:
        """Khởi động luồng phân tích bất đồng bộ cho dự án hiện tại."""
        if not self._project_id:
            if self._notice:
                self._notice.set_notice("Vui lòng chọn một dự án trước khi phân tích.", "warning")
                self._notice.show()
            return

        if self._score_stack:
            self._score_stack.setCurrentIndex(1)
        if self._tab_widget:
            self._tab_widget.hide()
        if self._btn_export_html:
            self._btn_export_html.hide()

        self._scanning_block.reset()
        self.status_message.emit(f"Bắt đầu phân tích dự án '{self._project_name}'...")
        self._controller.start_analysis(self._project_id)

    def _cancel_scan(self) -> None:
        """Hủy tiến trình phân tích theo lệnh người dùng."""
        self._controller.cancel_analysis()

    def _on_analysis_progress(self, msg: str, pct: int) -> None:
        """Cập nhật giao diện theo từng bước phân tích."""
        self._scanning_block.set_progress(msg, pct)

    def _on_analysis_finished(self, response: dict[str, Any]) -> None:
        """Xử lý kết quả phân tích hoàn tất từ Backend."""
        data = response.get("data", response)
        self.load_session_data(data)
        self.analysis_completed.emit(data)
        self.status_message.emit("Hoàn thành phân tích dự án thành công!")

    def _on_analysis_failed(self, error_msg: str) -> None:
        """Xử lý khi tiến trình phân tích gặp lỗi."""
        if self._btn_reanalyze:
            self._btn_reanalyze.setText("Bắt đầu phân tích")
            self._btn_reanalyze.show()
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
        radar_canvas = self._charts_tab.get_radar_canvas()
        if file_path and radar_canvas:
            if radar_canvas.save_chart(file_path):
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
        """Tạo mã nguồn HTML báo cáo kỹ thuật hoàn chỉnh độc lập."""
        # pylint: disable=too-many-locals
        data = self._current_data
        summary = data.get("summary", {})
        if isinstance(summary, str):
            try:
                summary = json.loads(summary)
            except (json.JSONDecodeError, TypeError):
                summary = {}
        elif not isinstance(summary, dict):
            summary = {}

        tot_score = float(data.get("total_score") or data.get("score") or 0.0)
        grade = str(data.get("grade") or _get_grade_for_score(tot_score))
        crit_scores = summary.get("criteria_scores", {})
        qual_score, sec_score = _compute_dual_scores(
            crit_scores,
            summary.get("quality_score"),
            summary.get("security_score"),
            tot_score,
        )

        radar_b64 = ""
        risk_b64 = ""
        radar_canvas = self._charts_tab.get_radar_canvas()
        top_risk_canvas = self._charts_tab.get_top_risk_canvas()
        if radar_canvas:
            radar_b64 = radar_canvas.to_base64_png()
        if top_risk_canvas:
            risk_b64 = top_risk_canvas.to_base64_png()

        crit_high_issues = self._collect_critical_high_issues(data)
        sev_dist = summary.get("severity_distribution", {})
        files_str, loc_str, issues_str = self._overview_tab.get_display_stats()

        session_review = summary.get("session_review")
        if not session_review and isinstance(data.get("session_review"), dict):
            session_review = data.get("session_review")

        report_meta = {
            "project_name": self._project_name,
            "session_id": self._session_id,
            "total_score": tot_score,
            "grade": grade,
            "quality_score": qual_score,
            "security_score": sec_score,
            "sev_dist": sev_dist,
            "files_text": files_str,
            "loc_text": loc_str,
            "issues_text": issues_str,
            "session_review": session_review or {},
        }

        return _build_html_report_content(
            report_meta=report_meta,
            crit_scores=crit_scores,
            radar_b64=radar_b64,
            risk_b64=risk_b64,
            crit_high_issues=crit_high_issues,
        )
