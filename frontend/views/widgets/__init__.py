"""Package các Widget dùng chung cho giao diện Desktop PyQt6 theo chuẩn SKILLS.md."""

from frontend.views.widgets.empty_state import EmptyState
from frontend.views.widgets.grade_label import GradeLabel
from frontend.views.widgets.inline_notice import InlineNotice
from frontend.views.widgets.page_header import PageHeader
from frontend.views.widgets.panel import Panel
from frontend.views.widgets.pill_badge_delegate import PillBadgeDelegate
from frontend.views.widgets.score_bar import ScoreBar
from frontend.views.widgets.severity_badge import SeverityBadge
from frontend.views.widgets.status_dot import StatusDot
from frontend.views.widgets.table_utils import chuan_hoa_bang

__all__ = [
    "SeverityBadge",
    "StatusDot",
    "ScoreBar",
    "GradeLabel",
    "EmptyState",
    "InlineNotice",
    "PageHeader",
    "Panel",
    "PillBadgeDelegate",
    "chuan_hoa_bang",
]
