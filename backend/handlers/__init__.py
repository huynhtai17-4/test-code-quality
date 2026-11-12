"""Handlers package initialization."""

from .analysis_handler import handle_run_analysis
from .config_handler import handle_get_config, handle_update_config
from .history_handler import handle_delete_history, handle_list_history
from .issue_handler import (
    handle_create_issue,
    handle_delete_issue,
    handle_list_issues,
    handle_update_issue_status,
)
from .project_handler import (
    handle_create_project,
    handle_delete_project,
    handle_get_project,
    handle_list_projects,
    handle_update_project,
)

__all__ = [
    # Analysis Handler
    "handle_run_analysis",
    # Project Handlers
    "handle_create_project",
    "handle_list_projects",
    "handle_get_project",
    "handle_update_project",
    "handle_delete_project",
    # Issue Handlers
    "handle_list_issues",
    "handle_update_issue_status",
    "handle_delete_issue",
    "handle_create_issue",
    # History Handlers
    "handle_list_history",
    "handle_delete_history",
    # Config Handlers
    "handle_get_config",
    "handle_update_config",
]
