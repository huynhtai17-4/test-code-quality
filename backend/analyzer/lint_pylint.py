"""Module phân tích chất lượng cú pháp và chấm điểm mã nguồn bằng Pylint."""

import contextlib
import io
import json
import os
import shutil
import subprocess  # nosec B404
import sys
from pathlib import Path
from typing import Any

SEVERITY_TYPE_MAP = {
    "fatal": "Critical",
    "error": "High",
    "warning": "Medium",
    "refactor": "Low",
    "convention": "Low",
    "info": "Low",
}


def _format_pylint_issue(item: dict[str, Any], target: Path) -> dict[str, Any]:
    """Chuẩn hóa một lỗi từ đầu ra của Pylint sang schema thống nhất."""
    raw_path = item.get("path", "")
    try:
        item_path = Path(raw_path).resolve()
        if target.is_file():
            rel_file = item_path.name
        else:
            rel_file = str(item_path.relative_to(target)).replace("\\", "/")
    except ValueError:
        rel_file = os.path.relpath(raw_path, str(target)).replace("\\", "/")

    raw_type = str(item.get("type", "convention")).lower()
    severity = SEVERITY_TYPE_MAP.get(raw_type, "Low")
    msg_id = item.get("message-id") or item.get("symbol") or ""

    return {
        "tool": "pylint",
        "file": rel_file,
        "line": item.get("line"),
        "column_number": item.get("column"),
        "severity": severity,
        "message": f"{item.get('message', '')} ({msg_id})" if msg_id else item.get("message", ""),
        "rule_code": msg_id,
        "test_id": msg_id,
        "category": "code_style",
    }


def _run_pylint_inprocess(target: Path) -> tuple[float, list[dict[str, Any]]]:
    """Thực thi Pylint trực tiếp qua Python API để đạt tốc độ cao."""
    from pylint.lint import Run  # pylint: disable=import-outside-toplevel
    from pylint.reporters.json_reporter import JSONReporter  # pylint: disable=import-outside-toplevel

    out_stream = io.StringIO()
    devnull = io.StringIO()

    args = [str(target), "--exit-zero"]
    # Tắt thông báo rác hoặc kiểm tra bảo mật trùng lặp
    with contextlib.redirect_stdout(devnull), contextlib.redirect_stderr(devnull):
        runner = Run(args, reporter=JSONReporter(out_stream), exit=False)

    score = 10.0
    if hasattr(runner, "linter") and hasattr(runner.linter, "stats"):
        stats = runner.linter.stats
        if hasattr(stats, "global_note") and stats.global_note is not None:
            score = float(stats.global_note)

    raw_text = out_stream.getvalue().strip()
    raw_issues: list[dict[str, Any]] = json.loads(raw_text) if raw_text else []
    return score, raw_issues


def _run_pylint_subprocess(
    target: Path,
    timeout_seconds: int = 120,
) -> tuple[float, list[dict[str, Any]]]:
    """Thực thi Pylint qua tiến trình con độc lập như phương án dự phòng."""
    pylint_exec = shutil.which("pylint") or sys.executable
    if pylint_exec == sys.executable:
        cmd = [sys.executable, "-m", "pylint", str(target), "-f", "json", "--exit-zero"]
    else:
        cmd = [pylint_exec, str(target), "-f", "json", "--exit-zero"]

    proc = subprocess.run(  # nosec B603
        cmd,
        capture_output=True,
        text=True,
        timeout=timeout_seconds,
        check=False,
    )
    raw_text = (proc.stdout or "").strip()
    raw_issues: list[dict[str, Any]] = json.loads(raw_text) if raw_text else []

    # Tính điểm ước lượng theo công thức trừ lùi Pylint nếu không lấy được qua JSON
    total_penalties = 0.0
    for issue in raw_issues:
        itype = str(issue.get("type", "")).lower()
        if itype == "fatal":
            total_penalties += 10.0
        elif itype == "error":
            total_penalties += 5.0
        elif itype == "warning":
            total_penalties += 1.0
        else:
            total_penalties += 0.5
    score = max(0.0, 10.0 - min(10.0, total_penalties * 0.5))
    return score, raw_issues


def analyze_pylint(
    target_path: str | Path,
    timeout_seconds: int = 120,
) -> dict[str, Any]:
    """
    Quét mã nguồn và tính điểm chất lượng tĩnh bằng Pylint.

    Args:
        target_path: Đường dẫn thư mục hoặc file cần quét.
        timeout_seconds: Thời gian chờ tối đa cho phân tích.

    Returns:
        dict: Kết quả chuẩn gồm trạng thái, điểm số Pylint (0-10) và danh sách lỗi:
        {
            "status": "ok" | "error",
            "score": float,
            "pylint_score": float,
            "total_issues": int,
            "issues": list[dict],
        }
    """
    target = Path(target_path).resolve()
    if not target.exists():
        return {
            "status": "error",
            "message": f"Đường dẫn không tồn tại: {target_path}",
            "score": 10.0,
            "pylint_score": 10.0,
            "total_issues": 0,
            "issues": [],
        }

    try:
        try:
            score, raw_issues = _run_pylint_inprocess(target)
        except Exception:  # pylint: disable=broad-exception-caught
            score, raw_issues = _run_pylint_subprocess(target, timeout_seconds=timeout_seconds)

        score = round(max(0.0, min(10.0, float(score))), 2)
        formatted_issues = [_format_pylint_issue(item, target) for item in raw_issues]

        return {
            "status": "ok",
            "score": score,
            "pylint_score": score,
            "total_issues": len(formatted_issues),
            "issues": formatted_issues,
        }

    except subprocess.TimeoutExpired:
        return {
            "status": "error",
            "message": f"Quá thời gian quét Pylint ({timeout_seconds} giây)",
            "score": 0.0,
            "pylint_score": 0.0,
            "total_issues": 0,
            "issues": [],
        }
    except Exception as exc:  # pylint: disable=broad-exception-caught
        return {
            "status": "error",
            "message": str(exc),
            "score": 0.0,
            "pylint_score": 0.0,
            "total_issues": 0,
            "issues": [],
        }


if __name__ == "__main__":
    sample_dir = Path(__file__).resolve().parents[1] / "samples" / "bad_project"
    print(f"[*] Đang thực hiện phân tích Pylint trên: {sample_dir}")
    res = analyze_pylint(sample_dir)
    print(f"[+] Status: {res['status']}")
    print(f"[+] Score: {res['score']} / 10.0")
    print(f"[+] Issues found: {res['total_issues']}")
    for iss in res["issues"][:3]:
        print(f"    - [{iss['severity']}] {iss['file']}:{iss['line']} - {iss['message']}")
