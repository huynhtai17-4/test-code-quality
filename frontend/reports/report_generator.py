"""Bộ sinh báo cáo kiểm định chất lượng mã nguồn dạng tài liệu HTML/PDF độc lập."""

from __future__ import annotations

import datetime
import html
from typing import Any

from frontend.models.issue_model import _prepare_snippet_lines
from frontend.views.theme import (
    GRADE_A,
    GRADE_B,
    GRADE_C,
    GRADE_D,
    GRADE_F,
)

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
