"""Màn hình Phân tích chi tiết chất lượng mã nguồn (AnalysisView) theo SKILLS.md."""

import datetime
import html
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
    QAbstractTableModel,
    QModelIndex,
    QObject,
    QSortFilterProxyModel,
    Qt,
    pyqtSignal,
)
from PyQt6.QtGui import QColor
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
from frontend.network import api
from frontend.views.issues_view import _prepare_snippet_lines
from frontend.views.theme import (
    BORDER_SOFT,
    GRADE_A,
    GRADE_B,
    GRADE_C,
    GRADE_D,
    GRADE_F,
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
from frontend.workers.analysis_worker import AnalysisWorker

_CRITERIA_SPECS = (
    (
        "complexity",
        "Độ phức tạp & bảo trì",
        "Radon CC & MI (Độ phức tạp Cyclomatic & chỉ số bảo trì mã nguồn)",
    ),
    (
        "security",
        "An toàn bảo mật",
        "Bandit SAST (Quét lỗ hổng an toàn, SQLi, hardcoded credentials)",
    ),
    (
        "pylint",
        "Quy chuẩn mã nguồn",
        "Pylint (Quy chuẩn cấu trúc PEP8, chuẩn cú pháp và thiết kế)",
    ),
    (
        "health",
        "Sức khỏe & Git",
        "Git Health (Tần suất commit, hoạt động phát triển và tài liệu)",
    ),
    (
        "dependency",
        "Thư viện & CVE",
        "Pip-audit (Kiểm tra lỗ hổng đã công bố CVE trong các thư viện phụ thuộc)",
    ),
    (
        "malware",
        "Phát hiện mã độc & AST",
        "Malware AST (Phát hiện thực thi động eval/exec, backdoor, entropy cao & shell)",
    ),
)


def _get_score_color(score: float) -> str:
    """Trả về mã màu chuẩn theo thang điểm (A-F)."""
    if score >= 90.0:
        return GRADE_A
    if score >= 75.0:
        return GRADE_B
    if score >= 60.0:
        return GRADE_C
    if score >= 40.0:
        return GRADE_D
    return GRADE_F


def _get_grade_for_score(score: float) -> str:
    """Xếp loại ký tự A, B, C, D, F theo điểm số."""
    if score >= 90.0:
        return "A"
    if score >= 75.0:
        return "B"
    if score >= 60.0:
        return "C"
    if score >= 40.0:
        return "D"
    return "F"


def _compute_dual_scores(
    crit_scores: dict[str, float],
    raw_q: Any,
    raw_s: Any,
    fallback: float,
) -> tuple[float, float]:
    """Tính toán hoặc trích xuất fallback cho cặp chỉ số quality & security."""
    if raw_q is None:
        q_vals = [
            float(crit_scores[k])
            for k in ("complexity", "pylint", "health")
            if k in crit_scores
        ]
        q_score = (sum(q_vals) / len(q_vals)) if q_vals else fallback
    else:
        q_score = float(raw_q)

    if raw_s is None:
        s_vals = [
            float(crit_scores[k])
            for k in ("security", "dependency", "malware")
            if k in crit_scores
        ]
        s_score = (sum(s_vals) / len(s_vals)) if s_vals else fallback
    else:
        s_score = float(raw_s)

    return q_score, s_score


def _render_crit_table(crit_scores: dict[str, float]) -> str:
    """Tạo các hàng HTML cho bảng 6 tiêu chí kiểm định."""
    crit_rows = []
    for key, name, desc in _CRITERIA_SPECS:
        val = float(crit_scores.get(key, 0.0))
        clr = _get_score_color(val)
        grd = _get_grade_for_score(val)
        crit_rows.append(
            f'<tr><td style="font-weight: 600; color: #0F172A;">{html.escape(name)}</td>'
            f'<td style="color: #64748B;">{html.escape(desc)}</td>'
            f'<td><div style="font-weight: 700; margin-bottom: 4px;">{val:.1f} / 100</div>'
            f'<div class="progress-bar-bg">'
            f'<div class="progress-bar-fill" style="width: {min(100.0, max(0.0, val)):.1f}%; '
            f'background-color: {clr};"></div></div></td>'
            f'<td style="font-weight: 700; color: {clr}; font-size: 14px;">{grd}</td></tr>'
        )
    return "\n".join(crit_rows)


def _render_charts_section(radar_b64: str, risk_b64: str) -> str:
    """Tạo khối HTML nhúng biểu đồ radar đa giác và top tệp tin rủi ro."""
    if not (radar_b64 or risk_b64):
        return ""
    charts_section = (
        '<div class="section-title">Biểu đồ Phân tích Trực quan</div>'
        '<div class="charts-grid">'
    )
    if radar_b64:
        charts_section += (
            f'<div class="chart-box"><div style="font-size: 13px; font-weight: 600; '
            f'color: #475569; margin-bottom: 8px;">Đa giác Tiêu chí Kiểm định</div>'
            f'<img src="data:image/png;base64,{radar_b64}" alt="Đa giác tiêu chí" /></div>'
        )
    if risk_b64:
        charts_section += (
            f'<div class="chart-box"><div style="font-size: 13px; font-weight: 600; '
            f'color: #475569; margin-bottom: 8px;">Top Tệp tin Nguy cơ Cao nhất</div>'
            f'<img src="data:image/png;base64,{risk_b64}" alt="Top tệp tin rủi ro" /></div>'
        )
    charts_section += '</div>'
    return charts_section


def _render_snippet_html(snippet_raw: Any, line_val: Any) -> str:
    """Tạo khối HTML cho trích đoạn code snippet với đánh số dòng."""
    if not snippet_raw:
        return ""
    try:
        t_line = int(line_val) if line_val is not None else 0
    except (ValueError, TypeError):
        t_line = 0
    lines = _prepare_snippet_lines(snippet_raw, t_line)
    lines_rendered = []
    if t_line > 0:
        for ln, l_text in lines:
            esc = html.escape(l_text)
            if ln == t_line:
                lines_rendered.append(f'<span class="err-line">{esc}</span>')
            else:
                lines_rendered.append(esc)
    else:
        for _, l_text in lines:
            lines_rendered.append(html.escape(l_text))
    return f'<pre class="code-snippet"><code>{"\n".join(lines_rendered)}</code></pre>'


def _render_issues_section(crit_high_issues: list[dict[str, Any]]) -> str:  # pylint: disable=too-many-locals
    """Tạo HTML danh sách sự cố Critical/High kèm code snippet & remediation."""
    if not crit_high_issues:
        return (
            '<div style="padding: 16px 20px; background: #F0FDF4; border: 1px solid #DCFCE7; '
            'border-radius: 6px; color: #166534; font-size: 13px;">'
            '✓ Tuyệt vời! Không ghi nhận lỗ hổng nghiêm trọng (Critical) hoặc mức cao (High) nào.'
            '</div>'
        )

    cards = []
    for issue in crit_high_issues:
        sev = str(issue.get("severity") or "Critical").capitalize()
        is_crit = sev == "Critical"
        sev_class = "" if is_crit else "high-sev"
        badge_class = "badge-critical" if is_crit else "badge-high"
        sev_title = "Nghiêm trọng (Critical)" if is_crit else "Mức cao (High)"

        fpath = str(issue.get("file_path") or issue.get("file") or "—")
        line_val = issue.get("line_number")
        if line_val is None:
            line_val = issue.get("line")
        loc_disp = f"{fpath}:{line_val}" if line_val else fpath

        tool_disp = str(issue.get("tool") or "").upper()
        rule_disp = str(issue.get("rule_code") or issue.get("test_id") or "").strip()
        meta_str = f"Công cụ: {tool_disp}"
        if rule_disp:
            meta_str += f" · Mã kiểm tra: {rule_disp}"

        msg = str(issue.get("message") or "")
        remed = str(issue.get("remediation") or "").strip()

        snippet_html = _render_snippet_html(issue.get("code_snippet"), line_val)
        remediation_html = ""
        if remed:
            remediation_html = (
                f'<div class="remediation-box">'
                f'<strong>Hướng dẫn khắc phục:</strong> {html.escape(remed)}'
                f'</div>'
            )

        card_html = (
            f'<div class="issue-card {sev_class}">'
            f'<div class="issue-header">'
            f'<div><span class="issue-badge {badge_class}">{sev_title}</span> '
            f'<span class="issue-location">{html.escape(loc_disp)}</span></div>'
            f'<span style="font-size: 12px; color: #64748B;">{html.escape(meta_str)}</span>'
            f'</div>'
            f'<div class="issue-msg">{html.escape(msg)}</div>'
            f'{snippet_html}'
            f'{remediation_html}'
            f'</div>'
        )
        cards.append(card_html)

    return "\n".join(cards)


def _build_html_report_content(  # pylint: disable=too-many-locals
    report_meta: dict[str, Any],
    crit_scores: dict[str, float],
    radar_b64: str,
    risk_b64: str,
    crit_high_issues: list[dict[str, Any]],
) -> str:
    """Tạo tài liệu HTML báo cáo hoàn chỉnh độc lập hỗ trợ Ctrl+P xuất PDF."""
    now_str = datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    proj_esc = html.escape(str(report_meta.get("project_name", "Dự án")))
    session_id = report_meta.get("session_id")
    session_str = f"#{session_id}" if session_id else "Chưa lưu"

    total_score = float(report_meta.get("total_score", 0.0))
    grade = str(report_meta.get("grade", "A"))
    quality_score = float(report_meta.get("quality_score", 0.0))
    security_score = float(report_meta.get("security_score", 0.0))

    tot_color = _get_score_color(total_score)
    qual_color = _get_score_color(quality_score)
    sec_color = _get_score_color(security_score)

    crit_table_html = _render_crit_table(crit_scores)
    charts_section = _render_charts_section(radar_b64, risk_b64)
    issues_section_content = _render_issues_section(crit_high_issues)

    sev_dist = report_meta.get("sev_dist", {})
    crit_cnt = sev_dist.get("Critical", 0)
    high_cnt = sev_dist.get("High", 0)
    med_cnt = sev_dist.get("Medium", 0)
    low_cnt = sev_dist.get("Low", 0)

    files_text = str(report_meta.get("files_text", "—"))
    loc_text = str(report_meta.get("loc_text", "—"))
    issues_text = str(report_meta.get("issues_text", "0"))

    return f"""<!DOCTYPE html>
<html lang="vi">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<title>Báo Cáo Kiểm Định - {proj_esc}</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
    background-color: #F8FAFC; color: #1E293B; line-height: 1.5; padding: 30px;
  }}
  .report-container {{
    max-width: 1000px; margin: 0 auto; background: #FFFFFF; border: 1px solid #E2E8F0;
    border-radius: 8px; padding: 36px; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
  }}
  .header-section {{
    display: flex; justify-content: space-between; align-items: flex-start;
    border-bottom: 2px solid #E2E8F0; padding-bottom: 20px; margin-bottom: 24px;
  }}
  .header-title h1 {{ font-size: 20px; font-weight: 700; color: #0F172A; margin-bottom: 4px; }}
  .header-title .subtitle {{ font-size: 13px; color: #64748B; }}
  .meta-badge {{ text-align: right; font-size: 12px; color: #64748B; line-height: 1.6; }}
  .no-print-banner {{
    background: #EFF6FF; border: 1px solid #BFDBFE; color: #1D4ED8; padding: 10px 16px;
    border-radius: 6px; margin-bottom: 20px; font-size: 13px; text-align: center;
  }}
  .summary-grid {{
    display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; margin-bottom: 24px;
  }}
  .summary-card {{
    background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 8px; padding: 18px; text-align: center;
  }}
  .summary-card .card-label {{
    font-size: 11px; font-weight: 600; color: #64748B; text-transform: uppercase;
    letter-spacing: 0.5px; margin-bottom: 6px;
  }}
  .summary-card .card-value {{ font-size: 26px; font-weight: 800; margin-bottom: 2px; }}
  .summary-card .card-sub {{ font-size: 11px; color: #94A3B8; }}
  .stats-strip {{
    display: flex; justify-content: space-around; background: #F8FAFC; border: 1px solid #EEF2F6;
    border-radius: 6px; padding: 12px; margin-bottom: 28px;
  }}
  .stat-item {{ text-align: center; }}
  .stat-item .val {{ font-size: 16px; font-weight: 700; color: #0F172A; }}
  .stat-item .lbl {{ font-size: 11px; color: #64748B; }}
  .section-title {{
    font-size: 15px; font-weight: 700; color: #0F172A; margin: 28px 0 14px 0;
    padding-bottom: 6px; border-bottom: 1px solid #E2E8F0;
  }}
  .charts-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 18px; margin-bottom: 28px; }}
  .chart-box {{
    background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 8px; padding: 14px; text-align: center;
  }}
  .chart-box img {{ max-width: 100%; height: auto; border-radius: 4px; }}
  table.report-table {{ width: 100%; border-collapse: collapse; margin-bottom: 24px; font-size: 13px; }}
  table.report-table th, table.report-table td {{
    padding: 10px 12px; text-align: left; border-bottom: 1px solid #E2E8F0;
  }}
  table.report-table th {{
    background: #F8FAFC; color: #475569; font-weight: 600; font-size: 11px;
    text-transform: uppercase; letter-spacing: 0.5px;
  }}
  .progress-bar-bg {{
    background: #E2E8F0; border-radius: 4px; height: 6px; width: 100%; overflow: hidden; margin-top: 4px;
  }}
  .progress-bar-fill {{ height: 100%; border-radius: 4px; }}
  .issue-card {{
    border: 1px solid #E2E8F0; border-left: 4px solid #B42318; border-radius: 6px;
    padding: 14px; margin-bottom: 14px; background: #FFFFFF; page-break-inside: avoid;
  }}
  .issue-card.high-sev {{ border-left-color: #D9622B; }}
  .issue-header {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px; }}
  .issue-badge {{
    font-size: 11px; font-weight: 700; padding: 2px 7px; border-radius: 4px; color: #FFFFFF; display: inline-block;
  }}
  .badge-critical {{ background: #B42318; }}
  .badge-high {{ background: #D9622B; }}
  .issue-location {{
    font-family: ui-monospace, SFMono-Regular, "Geist Mono", Consolas, monospace;
    font-size: 12px; font-weight: 600; color: #0F172A; margin-left: 6px;
  }}
  .issue-msg {{ font-size: 13px; color: #334155; margin-bottom: 8px; line-height: 1.4; }}
  pre.code-snippet {{
    background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 4px; padding: 8px 10px;
    font-family: ui-monospace, SFMono-Regular, "Geist Mono", Consolas, monospace; font-size: 11px;
    color: #1E293B; overflow-x: auto; margin: 8px 0; line-height: 1.45;
  }}
  pre.code-snippet .err-line {{
    background: #FDECEC; color: #B42318; font-weight: 600; display: block; margin: 0 -10px; padding: 0 10px;
  }}
  .remediation-box {{
    background: #F0FDF4; border: 1px solid #DCFCE7; border-radius: 4px; padding: 8px 10px;
    font-size: 12px; color: #166534; margin-top: 6px;
  }}
  @media print {{
    body {{ background: #FFFFFF; padding: 0; -webkit-print-color-adjust: exact; print-color-adjust: exact; }}
    .report-container {{ border: none; box-shadow: none; padding: 0; max-width: 100%; }}
    .no-print {{ display: none !important; }}
    .page-break {{ page-break-before: always; }}
    .issue-card {{ page-break-inside: avoid; }}
    @page {{ size: A4; margin: 12mm 15mm; }}
  }}
</style>
</head>
<body>
<div class="report-container">
  <div class="no-print no-print-banner">
    📄 <b>Báo cáo kỹ thuật độc lập</b> · Nhấn phím <b>Ctrl + P</b> để in hoặc xuất PDF chuẩn tài liệu.
  </div>

  <div class="header-section">
    <div class="header-title">
      <h1>Báo Cáo Kiểm Định Chất Lượng & An Toàn Mã Nguồn</h1>
      <div class="subtitle">Dự án: <b>{proj_esc}</b> · Hệ thống đánh giá tự động đa tầng</div>
    </div>
    <div class="meta-badge">
      <div>Phiên quét: <b>{session_str}</b></div>
      <div>Thời gian xuất: {now_str}</div>
    </div>
  </div>

  <div class="summary-grid">
    <div class="summary-card">
      <div class="card-label">Xếp loại & Tổng điểm</div>
      <div class="card-value" style="color: {tot_color};">
        {grade} <span style="font-size: 20px;">({total_score:.1f})</span>
      </div>
      <div class="card-sub">Thang điểm tổng hợp 0–100</div>
    </div>
    <div class="summary-card">
      <div class="card-label">Chất lượng Code</div>
      <div class="card-value" style="color: {qual_color};">{quality_score:.1f}</div>
      <div class="card-sub">Cấu trúc, PEP8, độ phức tạp</div>
    </div>
    <div class="summary-card">
      <div class="card-label">An toàn Bảo mật</div>
      <div class="card-value" style="color: {sec_color};">{security_score:.1f}</div>
      <div class="card-sub">SAST, CVE, hành vi mã độc</div>
    </div>
  </div>

  <div class="stats-strip">
    <div class="stat-item"><div class="val">{files_text}</div><div class="lbl">Tệp tin</div></div>
    <div class="stat-item"><div class="val">{loc_text}</div><div class="lbl">Dòng mã (LOC)</div></div>
    <div class="stat-item"><div class="val">{issues_text}</div><div class="lbl">Tổng số lỗi</div></div>
    <div class="stat-item">
      <div class="val" style="color: #B42318;">{crit_cnt}</div>
      <div class="lbl">Nghiêm trọng</div>
    </div>
    <div class="stat-item">
      <div class="val" style="color: #D9622B;">{high_cnt}</div>
      <div class="lbl">Mức cao</div>
    </div>
    <div class="stat-item">
      <div class="val" style="color: #C79A0A;">{med_cnt}</div>
      <div class="lbl">Trung bình</div>
    </div>
    <div class="stat-item">
      <div class="val" style="color: #5E7A94;">{low_cnt}</div>
      <div class="lbl">Mức thấp</div>
    </div>
  </div>

  <div class="section-title">Điểm số Chi tiết 6 Tiêu chí Kiểm định</div>
  <table class="report-table">
    <thead>
      <tr>
        <th style="width: 24%;">Tiêu chí</th>
        <th style="width: 46%;">Mô tả & Công cụ đo lường</th>
        <th style="width: 18%;">Điểm / 100</th>
        <th style="width: 12%;">Hạng</th>
      </tr>
    </thead>
    <tbody>
      {crit_table_html}
    </tbody>
  </table>

  {charts_section}

  <div class="section-title">Danh sách Sự cố Bảo mật Nguy cơ Cao (Critical & High)</div>
  {issues_section_content}

  <div style="margin-top: 36px; padding-top: 14px; border-top: 1px solid #E2E8F0; text-align: center; font-size: 11px; color: #94A3B8;">
    Báo cáo kỹ thuật được tạo tự động bởi Hệ thống Phân tích Chất lượng Mã Nguồn Desktop.
  </div>
</div>
</body>
</html>
"""


_FILE_HEADERS = (
    "Tên tệp tin",
    "Tổng lỗi",
    "Nghiêm trọng",
    "Cao",
    "Trung bình",
    "Thấp",
    "Độ phức tạp (CC)",
    "Bảo trì (MI)",
)


def _extract_metric_str(val: Any) -> str:
    """Định dạng giá trị số CC hoặc MI."""
    return f"{val:.1f}" if isinstance(val, (int, float)) else "—"


def _format_count_or_dash(val: Any) -> str:
    """Hiển thị số lượng hoặc gạch ngang nếu là 0."""
    try:
        n = int(val)
        return str(n) if n > 0 else "—"
    except (ValueError, TypeError):
        return "—"


def _get_display_value(file_info: dict[str, Any], col: int) -> str:
    """Trích xuất chuỗi hiển thị theo từng cột dữ liệu."""
    extractors = (
        lambda x: str(x.get("file", "—")),
        lambda x: str(x.get("total_issues", 0)),
        lambda x: _format_count_or_dash(x.get("critical_count")),
        lambda x: _format_count_or_dash(x.get("high_count")),
        lambda x: _format_count_or_dash(x.get("medium_count")),
        lambda x: _format_count_or_dash(x.get("low_count")),
        lambda x: _extract_metric_str(x.get("cc")),
        lambda x: _extract_metric_str(x.get("mi")),
    )
    if 0 <= col < len(extractors):
        return extractors[col](file_info)
    return "—"


class FileSummaryTableModel(QAbstractTableModel):
    """Mô hình dữ liệu bảng tổng kết theo từng file mã nguồn (8 cột chuẩn)."""

    def __init__(self, files: list[dict[str, Any]] | None = None, parent: QObject | None = None):
        super().__init__(parent)
        self._files: list[dict[str, Any]] = []
        if files:
            self.set_files(files)

    def rowCount(self, _parent: QModelIndex = QModelIndex()) -> int:  # pylint: disable=invalid-name
        """Trả về số lượng dòng trong bảng."""
        return len(self._files)

    def columnCount(self, _parent: QModelIndex = QModelIndex()) -> int:  # pylint: disable=invalid-name
        """Trả về số lượng cột của bảng."""
        return len(_FILE_HEADERS)

    def data(  # pylint: disable=too-many-return-statements
        self,
        index: QModelIndex,
        role: int = Qt.ItemDataRole.DisplayRole,
    ) -> Any:
        """Trả về dữ liệu hiển thị, phông chữ và căn lề cho từng ô."""
        if not index.isValid() or index.row() >= len(self._files):
            return None

        file_info = self._files[index.row()]
        col = index.column()

        if role == Qt.ItemDataRole.DisplayRole:
            return _get_display_value(file_info, col)

        if role == Qt.ItemDataRole.ForegroundRole:
            return self._get_cell_color(file_info, col)

        if role == Qt.ItemDataRole.FontRole:
            return lay_font_code(11)

        if role == Qt.ItemDataRole.TextAlignmentRole:
            align_left = Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
            return align_left if col == 0 else Qt.AlignmentFlag.AlignCenter

        if role == Qt.ItemDataRole.UserRole:
            return file_info

        return None

    @staticmethod
    def _get_cell_color(  # pylint: disable=too-many-return-statements,too-many-branches
        file_info: dict[str, Any],
        col: int,
    ) -> QColor | None:
        """Tính toán màu sắc chữ cho từng ô dữ liệu kỹ thuật."""
        if col == 1:
            cnt = int(file_info.get("total_issues", 0))
            return QColor("#0F172A") if cnt > 0 else QColor("#94A3B8")
        if col == 2:
            crit = int(file_info.get("critical_count", 0))
            return QColor("#DC2626") if crit > 0 else QColor("#94A3B8")
        if col == 3:
            high = int(file_info.get("high_count", 0))
            return QColor("#EA580C") if high > 0 else QColor("#94A3B8")
        if col == 4:
            med = int(file_info.get("medium_count", 0))
            return QColor("#D97706") if med > 0 else QColor("#94A3B8")
        if col == 5:
            low = int(file_info.get("low_count", 0))
            return QColor("#2563EB") if low > 0 else QColor("#94A3B8")
        if col == 6:
            cc_val = file_info.get("cc")
            if isinstance(cc_val, (int, float)):
                if cc_val >= 15:
                    return QColor("#DC2626")
                if cc_val >= 10:
                    return QColor("#D97706")
                return QColor("#0F172A")
            return QColor("#94A3B8")
        if col == 7:
            mi_val = file_info.get("mi")
            if isinstance(mi_val, (int, float)):
                if mi_val < 50:
                    return QColor("#DC2626")
                if mi_val < 65:
                    return QColor("#D97706")
                return QColor("#059669")
            return QColor("#94A3B8")
        return None

    def headerData(  # pylint: disable=invalid-name
        self,
        section: int,
        orientation: Qt.Orientation,
        role: int = Qt.ItemDataRole.DisplayRole,
    ) -> Any:
        """Trả về tiêu đề các cột ở phần đầu bảng."""
        if orientation == Qt.Orientation.Horizontal and role == Qt.ItemDataRole.DisplayRole:
            if 0 <= section < len(_FILE_HEADERS):
                return _FILE_HEADERS[section]
        return None

    def set_files(self, files: list[dict[str, Any]]) -> None:
        """Cập nhật dữ liệu danh sách tệp và sắp xếp ưu tiên lỗi Critical/High lên đầu."""
        self.beginResetModel()
        sorted_files = sorted(
            files,
            key=lambda x: (
                int(x.get("critical_count", 0)),
                int(x.get("high_count", 0)),
                int(x.get("total_issues", 0)),
            ),
            reverse=True,
        )
        self._files = sorted_files
        self.endResetModel()

    def get_file(self, row: int) -> dict[str, Any] | None:
        """Lấy thông tin tệp tin tại dòng chỉ định."""
        if 0 <= row < len(self._files):
            return self._files[row]
        return None


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
        self._worker: AnalysisWorker | None = None

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

        self._worker = AnalysisWorker(self._project_id, self)
        self._worker.progress.connect(self._on_analysis_progress)
        self._worker.finished.connect(self._on_analysis_finished)
        self._worker.failed.connect(self._on_analysis_failed)
        self._worker.start()

    def _cancel_scan(self) -> None:
        """Hủy tiến trình phân tích theo lệnh người dùng."""
        if self._worker:
            self._worker.cancel()
            self.status_message.emit("Đã gửi lệnh hủy phân tích...")

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
        try:
            with open(file_path, "w", encoding="utf-8") as f_out:
                f_out.write(html_content)
            self.status_message.emit(f"Đã xuất báo cáo HTML thành công: {file_path}")
        except OSError as exc:
            logger.error("Lỗi khi ghi tệp báo cáo HTML: %s", exc)
            self.status_message.emit(f"Xuất báo cáo thất bại: {exc}")

    def _collect_critical_high_issues(self, data: dict[str, Any]) -> list[dict[str, Any]]:
        """Lọc và trả về danh sách lỗi Critical / High từ dữ liệu hoặc API."""
        raw_issues = data.get("issues")
        if not raw_issues and self._session_id:
            try:
                res = api.list_issues(int(self._session_id))
                if isinstance(res, dict) and res.get("status") == "ok":
                    raw_issues = res.get("data", [])
            except Exception as exc:  # pylint: disable=broad-exception-caught
                logger.debug("Không thể lấy danh sách issues từ API: %s", exc)

        crit_high: list[dict[str, Any]] = []
        if isinstance(raw_issues, list):
            for it in raw_issues:
                sev = str(it.get("severity") or "").capitalize()
                if sev in ("Critical", "High"):
                    crit_high.append(it)
        return crit_high

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
