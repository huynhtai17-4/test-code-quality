"""Package tạo báo cáo kiểm định mã nguồn."""

from frontend.reports.report_generator import (
    _build_html_report_content,
    _compute_dual_scores,
    _get_grade_for_score,
    _get_score_color,
)

__all__ = [
    "_build_html_report_content",
    "_compute_dual_scores",
    "_get_grade_for_score",
    "_get_score_color",
]
