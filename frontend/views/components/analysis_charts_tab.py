"""Component giao diện Tab biểu đồ phân tích trực quan (AnalysisChartsTab)."""

from __future__ import annotations

from typing import Any

from PyQt6.QtCore import Qt, pyqtSignal  # pylint: disable=no-name-in-module
from PyQt6.QtWidgets import (  # pylint: disable=no-name-in-module
    QHBoxLayout,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from frontend.charts.chart_canvas import AnalysisChartCanvas
from frontend.views.widgets.panel import Panel


class AnalysisChartsTab(QWidget):
    """Tab 3: Hiển thị 2 biểu đồ phân tích (Đa giác tiêu chí và Top tệp tin rủi ro cao)."""

    save_chart_clicked = pyqtSignal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._canvas_radar: AnalysisChartCanvas | None = None
        self._canvas_top_risk: AnalysisChartCanvas | None = None
        self._init_ui()

    def _init_ui(self) -> None:
        """Khởi tạo bố cục nhúng 2 canvas biểu đồ."""
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

        action_row = QHBoxLayout()
        action_row.addStretch()
        btn_save = QPushButton("Lưu ảnh biểu đồ (PNG)", container)
        btn_save.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_save.clicked.connect(self.save_chart_clicked.emit)
        action_row.addWidget(btn_save)
        v_layout.addLayout(action_row)

        scroll.setWidget(container)
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(scroll)

    def draw_charts(
        self,
        crit_scores: dict[str, float],
        top_files: list[dict[str, Any]],
    ) -> None:
        """Vẽ biểu đồ đa giác và top tệp tin rủi ro."""
        if self._canvas_radar:
            self._canvas_radar.draw_criteria_radar(crit_scores)
        if self._canvas_top_risk:
            self._canvas_top_risk.draw_top_risk_bar(top_files)

    def get_radar_canvas(self) -> AnalysisChartCanvas | None:
        """Lấy tham chiếu tới canvas đa giác tiêu chí."""
        return self._canvas_radar

    def get_top_risk_canvas(self) -> AnalysisChartCanvas | None:
        """Lấy tham chiếu tới canvas top tệp tin rủi ro."""
        return self._canvas_top_risk
