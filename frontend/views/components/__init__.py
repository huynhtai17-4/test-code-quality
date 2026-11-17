"""Package chứa các Component giao diện con độc lập cho PyQt6 Views."""

from frontend.views.components.analysis_charts_tab import AnalysisChartsTab
from frontend.views.components.analysis_files_tab import AnalysisFilesTab
from frontend.views.components.analysis_overview_tab import AnalysisOverviewTab
from frontend.views.components.analysis_scanning_block import AnalysisScanningBlock
from frontend.views.components.analysis_score_block import AnalysisScoreBlock
from frontend.views.components.history_trend_canvas import HistoryTrendCanvas
from frontend.views.components.issue_detail_panel import IssueDetailPanel
from frontend.views.components.settings_stepper import (
    create_criterion_row,
    create_separator,
    create_total_weights_card,
)

__all__ = [
    "AnalysisChartsTab",
    "AnalysisFilesTab",
    "AnalysisOverviewTab",
    "AnalysisScanningBlock",
    "AnalysisScoreBlock",
    "HistoryTrendCanvas",
    "IssueDetailPanel",
    "create_criterion_row",
    "create_separator",
    "create_total_weights_card",
]
