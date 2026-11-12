"""Views package initialization."""

from frontend.views.analysis_view import (
    AnalysisView,
    FileSummaryTableModel,
)
from frontend.views.history_view import (
    ComparisonDialog,
    HistoryTableModel,
    HistoryView,
)
from frontend.views.issues_view import (
    IssueFilterProxyModel,
    IssueTableModel,
    IssuesView,
    ManualIssueDialog,
)
from frontend.views.projects_view import (
    ProjectDialog,
    ProjectTableModel,
    ProjectsView,
)
from frontend.views.settings_view import SettingsView

__all__ = [
    "AnalysisView",
    "ComparisonDialog",
    "FileSummaryTableModel",
    "HistoryTableModel",
    "HistoryView",
    "IssueFilterProxyModel",
    "IssueTableModel",
    "IssuesView",
    "ManualIssueDialog",
    "ProjectDialog",
    "ProjectTableModel",
    "ProjectsView",
    "SettingsView",
]
