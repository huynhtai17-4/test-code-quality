"""Package chứa các Dialog modal giao diện người dùng."""

from frontend.views.dialogs.comparison_dialog import ComparisonDialog
from frontend.views.dialogs.manual_issue_dialog import ManualIssueDialog
from frontend.views.dialogs.project_dialog import ProjectDialog

__all__ = [
    "ComparisonDialog",
    "ManualIssueDialog",
    "ProjectDialog",
]
