"""Kịch bản kiểm thử tự động cho Màn hình Phân tích và Canvas Biểu đồ (Bước 4.2 - SKILLS.md)."""

import os
import sys
import tempfile
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# pylint: disable=wrong-import-position,no-name-in-module
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication

from frontend.charts.chart_canvas import AnalysisChartCanvas
from frontend.views.analysis_view import (
    AnalysisView,
    FileSummaryTableModel,
)

_APP = QApplication.instance() or QApplication(["test_analysis_view"])


def _assert(condition: bool, message: str) -> None:
    """Xác thực điều kiện an toàn cho Bandit."""
    if not condition:
        raise RuntimeError(f"KIỂM THỬ THẤT BẠI: {message}")


def test_chart_canvas() -> None:
    """1. Kiểm tra AnalysisChartCanvas và các hàm vẽ biểu đồ."""
    print("[*] 1. Kiểm tra AnalysisChartCanvas...")
    canvas = AnalysisChartCanvas()

    # Empty
    canvas.draw_empty("Chưa có dữ liệu")

    # Donut pie
    dist = {"Critical": 3, "High": 8, "Medium": 15, "Low": 20}
    canvas.draw_severity_pie(dist)

    # Empty pie
    canvas.draw_severity_pie({})

    # Radar
    scores = {
        "complexity": 75.0,
        "security": 90.0,
        "pylint": 65.0,
        "health": 80.0,
        "dependency": 85.0,
    }
    canvas.draw_criteria_radar(scores)

    # Barh
    top_files = [
        {"file": "app.py", "total_issues": 12},
        {"file": "helpers.py", "total_issues": 8},
        {"file": "models/user.py", "total_issues": 5},
    ]
    canvas.draw_top_risk_bar(top_files)

    # Xuất ảnh PNG
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
        tmp_path = tmp.name

    try:
        saved = canvas.save_chart(tmp_path)
        _assert(saved, "save_chart thất bại")
        _assert(os.path.exists(tmp_path), "File ảnh chưa được tạo")
        _assert(os.path.getsize(tmp_path) > 100, "File ảnh rỗng hoặc không hợp lệ")

        # Kiểm tra xuất Base64 PNG
        b64_str = canvas.export_base64_png()
        _assert(isinstance(b64_str, str) and len(b64_str) > 100, "export_base64_png thất bại")
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

    print("    [OK] AnalysisChartCanvas vẽ Donut, Radar, Cột ngang và xuất ảnh PNG chuẩn xác")


def test_file_summary_table_model() -> None:
    """2. Kiểm tra FileSummaryTableModel."""
    print("[*] 2. Kiểm tra FileSummaryTableModel...")
    files: list[dict[str, Any]] = [
        {
            "file": "utils.py",
            "total_issues": 5,
            "critical_count": 0,
            "high_count": 1,
            "medium_count": 2,
            "low_count": 2,
            "cc": 3.2,
            "mi": 75.0,
        },
        {
            "file": "auth.py",
            "total_issues": 14,
            "critical_count": 3,
            "high_count": 5,
            "medium_count": 4,
            "low_count": 2,
            "cc": 8.7,
            "mi": 45.2,
        },
    ]

    model = FileSummaryTableModel(files)
    _assert(model.rowCount() == 2, f"rowCount sai: {model.rowCount()}")
    _assert(model.columnCount() == 8, f"columnCount sai: {model.columnCount()}")

    # File có Critical cao nhất (auth.py) phải được sắp xếp lên đầu (row 0)
    idx_top_file = model.index(0, 0)
    top_file_name = model.data(idx_top_file)
    _assert(top_file_name == "auth.py", f"Sắp xếp ưu tiên sai: {top_file_name}")

    # Font code cho cột 0
    font = model.data(idx_top_file, Qt.ItemDataRole.FontRole)
    _assert(font is not None, "Cột 0 phải có phông code")

    # Kiểm tra cột CC và MI
    idx_cc = model.index(0, 6)
    idx_mi = model.index(0, 7)
    _assert(model.data(idx_cc) == "8.7", f"CC sai: {model.data(idx_cc)}")
    _assert(model.data(idx_mi) == "45.2", f"MI sai: {model.data(idx_mi)}")

    print("    [OK] FileSummaryTableModel 8 cột hiển thị đúng và tự động ưu tiên tệp nguy cơ cao")


def test_analysis_view_ui() -> None:
    """3. Kiểm tra AnalysisView UI và cập nhật kết quả."""
    print("[*] 3. Kiểm tra AnalysisView...")
    view = AnalysisView()

    mock_project = {
        "id": 1,
        "session_id": 100,
        "name": "Flask-Demo",
        "total_score": 85.0,
        "grade": "B",
        "quality_score": 80.0,
        "security_score": 92.5,
        "total_files": 42,
        "total_loc": 3500,
        "total_issues": 12,
        "criteria_scores": {
            "complexity": 80.0,
            "security": 90.0,
            "pylint": 75.0,
            "health": 85.0,
            "dependency": 95.0,
            "malware": 92.5,
        },
        "severity_distribution": {
            "Critical": 1,
            "High": 3,
            "Medium": 5,
            "Low": 3,
        },
        "top_risk_files": [
            {"file": "app.py", "total_issues": 8, "critical_count": 1, "high_count": 3},
        ],
        "issues": [
            {
                "file_path": "backend/auth.py",
                "line_number": 42,
                "severity": "Critical",
                "tool": "malware_ast",
                "rule_code": "MAL-01",
                "message": "Phát hiện eval() mã động nguy hiểm",
                "code_snippet": "eval(user_input)",
                "remediation": "Tránh dùng eval() và chuyển sang ast.literal_eval()",
            }
        ],
    }

    # Nạp dự án có kết quả
    view.set_project(mock_project)

    stack = getattr(view, "_score_stack")
    _assert(stack.currentIndex() == 0, "Có kết quả phải hiển thị State 0")

    lbl_title = getattr(view, "_lbl_title")
    _assert(lbl_title.text() == "Flask-Demo", "Tên dự án không khớp")

    # Kiểm tra 2 thẻ chỉ số phẳng: Chất lượng Code & An toàn Bảo mật
    lbl_qual = getattr(view, "_lbl_quality_val")
    lbl_sec = getattr(view, "_lbl_security_val")
    _assert(lbl_qual is not None and "80 / 100" in lbl_qual.text(), "Chất lượng Code sai")
    _assert(lbl_sec is not None and "92.5 / 100" in lbl_sec.text(), "An toàn Bảo mật sai")

    # Kiểm tra 6 thanh tiêu chí
    score_bars = getattr(view, "_score_bars")
    _assert(len(score_bars) == 6, f"Phải có 6 thanh tiêu chí, hiện có: {len(score_bars)}")
    _assert("malware" in score_bars, "Thiếu tiêu chí malware trong ScoreBars")

    # Kiểm tra nút Xuất báo cáo HTML
    btn_export = getattr(view, "_btn_export_html")
    _assert(btn_export is not None and not btn_export.isHidden(), "Nút Xuất báo cáo phải hiển thị")

    # Kiểm tra hàm tạo báo cáo HTML
    html_report = view.generate_html_report()
    _assert(isinstance(html_report, str) and len(html_report) > 500, "Báo cáo HTML rỗng")
    _assert("@media print" in html_report, "HTML thiếu cấu hình @media print")
    _assert("Phát hiện mã độc" in html_report, "HTML thiếu tiêu chí malware")
    _assert("Chất lượng Code" in html_report, "HTML thiếu thẻ Chất lượng Code")
    _assert("An toàn Bảo mật" in html_report, "HTML thiếu thẻ An toàn Bảo mật")
    _assert("backend/auth.py:42" in html_report, "HTML thiếu vị trí lỗi")
    _assert("eval(user_input)" in html_report, "HTML thiếu trích đoạn mã nguồn")
    _assert("ast.literal_eval" in html_report, "HTML thiếu đề xuất khắc phục")

    # Kiểm tra phát tín hiệu switch_to_issues
    issues_sessions: list[int] = []
    view.switch_to_issues.connect(issues_sessions.append)
    view._on_jump_to_issues()  # pylint: disable=protected-access

    _assert(len(issues_sessions) == 1, "Tín hiệu switch_to_issues không được phát")
    _assert(issues_sessions[0] == 100, f"Session ID sai: {issues_sessions[0]}")

    print("    [OK] AnalysisView hiển thị thẻ điểm, cập nhật dữ liệu và phát tín hiệu hoàn hảo")


def main() -> None:
    """Chạy toàn bộ bài kiểm thử Bước 4.2."""
    print("=" * 65)
    print("  KIỂM THỬ MÀN HÌNH PHÂN TÍCH & BIỂU ĐỒ BƯỚC 4.2 (SKILLS.MD)  ")
    print("=" * 65)
    test_chart_canvas()
    test_file_summary_table_model()
    test_analysis_view_ui()
    print("=" * 65)
    print("  [PASSED] MÀN HÌNH PHÂN TÍCH ĐÃ ĐẠT CHUẨN KỸ THUẬT 100%!  ")
    print("=" * 65)


if __name__ == "__main__":
    main()
