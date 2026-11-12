"""Module phân tích quy chuẩn phong cách mã nguồn PEP 8 bằng Flake8."""

import os
import shutil
import subprocess  # nosec B404
import sys
from pathlib import Path
from typing import Any


def _map_flake8_severity(code: str) -> str:
    """Ánh xạ mã lỗi Flake8 sang mức độ nghiêm trọng chuẩn (High, Medium, Low)."""
    code_upper = str(code).upper()
    if code_upper.startswith(("E9", "F82", "F7")):
        return "High"
    if code_upper.startswith(("F", "C")):
        return "Medium"
    if code_upper.startswith(("E", "W")):
        return "Low"
    return "Low"


def _format_flake8_issue(line: str, target: Path) -> dict[str, Any] | None:
    """Phân tách một dòng định dạng path:::row:::col:::code:::text."""
    parts = line.strip().split(":::")
    if len(parts) < 5:
        return None

    raw_path, raw_row, raw_col, code, text = parts[0], parts[1], parts[2], parts[3], parts[4]

    try:
        item_path = Path(raw_path).resolve()
        if target.is_file():
            rel_file = item_path.name
        else:
            rel_file = str(item_path.relative_to(target)).replace("\\", "/")
    except ValueError:
        rel_file = os.path.relpath(raw_path, str(target)).replace("\\", "/")

    try:
        line_no = int(raw_row)
    except ValueError:
        line_no = 1

    try:
        col_no = int(raw_col)
    except ValueError:
        col_no = 1

    severity = _map_flake8_severity(code)

    return {
        "tool": "flake8",
        "file": rel_file,
        "line": line_no,
        "column_number": col_no,
        "severity": severity,
        "message": f"{code}: {text}",
        "rule_code": code,
        "test_id": code,
        "category": "code_style",
    }


def analyze_flake8(
    target_path: str | Path,
    timeout_seconds: int = 60,
) -> dict[str, Any]:
    """
    Quét quy chuẩn mã nguồn bằng công cụ Flake8.

    Args:
        target_path: Thư mục hoặc file cần kiểm tra.
        timeout_seconds: Thời gian chờ tối đa.

    Returns:
        dict chứa trạng thái, tổng số lỗi và danh sách chi tiết:
        {
            "status": "ok" | "error",
            "total_issues": int,
            "issues": list[dict],
            "message": str (chỉ có khi lỗi hoặc flake8 chưa cài đặt)
        }
    """
    target = Path(target_path).resolve()
    if not target.exists():
        return {
            "status": "error",
            "message": f"Đường dẫn không tồn tại: {target_path}",
            "total_issues": 0,
            "issues": [],
        }

    fmt = "--format=%(path)s:::%(row)d:::%(col)d:::%(code)s:::%(text)s"
    flake8_exec = shutil.which("flake8")
    if flake8_exec:
        cmd = [flake8_exec, str(target), fmt]
    else:
        cmd = [sys.executable, "-m", "flake8", str(target), fmt]

    try:
        proc = subprocess.run(  # nosec B603
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False,
        )

        stdout_text = (proc.stdout or "").strip()
        issues: list[dict[str, Any]] = []

        if stdout_text:
            for line in stdout_text.splitlines():
                parsed = _format_flake8_issue(line, target)
                if parsed:
                    issues.append(parsed)

        return {
            "status": "ok",
            "total_issues": len(issues),
            "issues": issues,
        }

    except FileNotFoundError:
        return {
            "status": "ok",
            "total_issues": 0,
            "issues": [],
            "message": "Flake8 chưa được cài đặt trong môi trường hiện tại.",
        }
    except subprocess.TimeoutExpired:
        return {
            "status": "error",
            "message": f"Quá thời gian quét Flake8 ({timeout_seconds} giây)",
            "total_issues": 0,
            "issues": [],
        }
    except Exception as exc:  # pylint: disable=broad-exception-caught
        return {
            "status": "error",
            "message": str(exc),
            "total_issues": 0,
            "issues": [],
        }


if __name__ == "__main__":
    sample_dir = Path(__file__).resolve().parents[1] / "samples" / "bad_project"
    print(f"[*] Đang thực hiện kiểm tra Flake8 trên: {sample_dir}")
    res = analyze_flake8(sample_dir)
    print(f"[+] Status: {res['status']}")
    print(f"[+] Issues found: {res['total_issues']}")
    for item in res["issues"]:
        print(f"    - [{item['severity']}] {item['file']}:{item['line']} - {item['message']}")
