"""Module phân tích lỗ hổng bảo mật mã nguồn Python bằng Bandit."""

import json
import os
import shutil
import subprocess  # nosec B404
from pathlib import Path
from typing import Any

SEVERITY_MAP = {
    "HIGH": "High",
    "MEDIUM": "Medium",
    "LOW": "Low",
}


def _format_issue(item: dict[str, Any], target: Path) -> dict[str, Any]:
    """Bóc tách và chuẩn hóa thông tin một lỗi từ kết quả JSON của Bandit."""
    raw_filename = item.get("filename", "")
    try:
        item_path = Path(raw_filename).resolve()
        if target.is_file():
            rel_file = item_path.name
        else:
            rel_file = str(item_path.relative_to(target)).replace("\\", "/")
    except ValueError:
        rel_file = os.path.relpath(raw_filename, str(target)).replace("\\", "/")

    raw_severity = str(item.get("issue_severity", "LOW")).upper()
    mapped_severity = SEVERITY_MAP.get(raw_severity, raw_severity.capitalize())
    raw_confidence = str(item.get("issue_confidence", "")).capitalize()

    return {
        "tool": "bandit",
        "file": rel_file,
        "line": item.get("line_number"),
        "test_id": item.get("test_id", ""),
        "severity": mapped_severity,
        "confidence": raw_confidence,
        "message": item.get("issue_text", ""),
    }


def analyze_bandit(
    target_path: str | Path,
    timeout_seconds: int = 60,
) -> dict[str, Any]:
    """
    Quét bảo mật mã nguồn bằng công cụ Bandit.

    Args:
        target_path: Đường dẫn thư mục hoặc file cần quét.
        timeout_seconds: Thời gian chờ tối đa cho tiến trình quét (mặc định 60s).

    Returns:
        dict chứa trạng thái, tổng số lỗi và danh sách lỗi chi tiết:
        {
            "status": "ok" | "error",
            "total_issues": int,
            "issues": list[dict],
            "message": str (chỉ xuất hiện khi status == "error")
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

    bandit_exec = shutil.which("bandit") or "bandit"
    cmd = [bandit_exec, "-r", str(target), "-f", "json", "-q"]

    try:
        # Thực thi lệnh bandit, bảo đảm an toàn với shell=False
        process = subprocess.run(  # nosec B603
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False,
            shell=False,
        )

        stdout_content = (process.stdout or "").strip()
        if not stdout_content:
            return {
                "status": "ok",
                "total_issues": 0,
                "issues": [],
            }

        raw_data = json.loads(stdout_content)
        issues = [_format_issue(item, target) for item in raw_data.get("results", [])]

        return {
            "status": "ok",
            "total_issues": len(issues),
            "issues": issues,
        }

    except subprocess.TimeoutExpired:
        return {
            "status": "error",
            "message": f"Quá thời gian quét Bandit ({timeout_seconds} giây)",
            "total_issues": 0,
            "issues": [],
        }
    except FileNotFoundError as exc:
        return {
            "status": "error",
            "message": f"Không tìm thấy công cụ Bandit trên hệ thống: {exc}",
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
    print(f"[*] Đang thực hiện quét thử nghiệm Bandit vào: {sample_dir}")
    scan_result = analyze_bandit(sample_dir)
    print(json.dumps(scan_result, indent=2, ensure_ascii=False))
