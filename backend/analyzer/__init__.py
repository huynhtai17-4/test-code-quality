"""Module phân tích chất lượng và bảo mật mã nguồn."""

from .aggregator import aggregate_analysis_results
from .dependency_audit import audit_dependencies
from .project_health import analyze_project_health
from .scoring import (
    build_criteria_scores,
    calculate_final_score,
    calculate_security_score,
    determine_grade,
)
from .security_bandit import analyze_bandit
from .source_loader import (
    cleanup_workspace,
    clone_git_repo,
    extract_zip_safe,
    prepare_source,
)

__all__ = [
    "analyze_bandit",
    "audit_dependencies",
    "analyze_project_health",
    "aggregate_analysis_results",
    "calculate_security_score",
    "calculate_final_score",
    "determine_grade",
    "build_criteria_scores",
    "extract_zip_safe",
    "clone_git_repo",
    "prepare_source",
    "cleanup_workspace",
]
