"""Module kiểm tra sức khỏe dự án (tệp chuẩn mực, cấu trúc và thông tin Git)."""

import json
import shutil
import subprocess  # nosec B404
from pathlib import Path
from typing import Any

_README_NAMES = frozenset({"readme.md", "readme.rst", "readme.txt", "readme"})
_LICENSE_NAMES = frozenset({"license", "license.txt", "license.md", "copying", "license.rst"})
_TEST_DIR_NAMES = frozenset({"tests", "test"})


def _check_presence(target_dir: Path) -> dict[str, bool]:
    """Kiểm tra sự tồn tại của README, LICENSE, tests và .gitignore trong thư mục gốc."""
    try:
        entries = list(target_dir.iterdir())
    except (OSError, PermissionError):
        return {
            "has_readme": False,
            "has_license": False,
            "has_tests": False,
            "has_gitignore": False,
        }

    file_names = {entry.name.lower() for entry in entries if entry.is_file()}
    dir_names = {entry.name.lower() for entry in entries if entry.is_dir()}

    has_readme = any(
        name in _README_NAMES or name.startswith("readme.")
        for name in file_names
    )
    has_license = any(
        name in _LICENSE_NAMES or name.startswith("license.")
        for name in file_names
    )
    has_tests = any(name in _TEST_DIR_NAMES for name in dir_names)
    has_gitignore = ".gitignore" in file_names

    return {
        "has_readme": has_readme,
        "has_license": has_license,
        "has_tests": has_tests,
        "has_gitignore": has_gitignore,
    }


def _run_git_cmd(git_exec: str, target_dir: Path, args: list[str], timeout: int) -> str:
    """Thực thi một lệnh git an toàn và trả về stdout nếu thành công."""
    cmd = [git_exec, "-C", str(target_dir)] + args
    try:
        res = subprocess.run(  # nosec B603
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
            shell=False,
        )
        if res.returncode == 0:
            return res.stdout.strip()
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        pass
    return ""


def _extract_git_info(target_dir: Path, timeout_seconds: int) -> dict[str, Any]:
    """Trích xuất thông tin commit, người đóng góp và ngày commit gần nhất từ Git."""
    default_info: dict[str, Any] = {
        "is_git_repo": False,
        "total_commits": 0,
        "contributors_count": 0,
        "last_commit_date": "N/A",
    }

    git_dir = target_dir / ".git"
    if not git_dir.exists():
        return default_info

    git_exec = shutil.which("git")
    if not git_exec:
        return default_info

    default_info["is_git_repo"] = True

    # 1. Tổng số commit
    commit_out = _run_git_cmd(
        git_exec,
        target_dir,
        ["rev-list", "--count", "HEAD"],
        timeout_seconds,
    )
    if commit_out.isdigit():
        default_info["total_commits"] = int(commit_out)

    # 2. Số người đóng góp
    contrib_out = _run_git_cmd(git_exec, target_dir, ["shortlog", "-sn", "--all"], timeout_seconds)
    if contrib_out:
        lines = [line.strip() for line in contrib_out.splitlines() if line.strip()]
        default_info["contributors_count"] = len(lines)

    # 3. Ngày commit gần nhất
    date_out = _run_git_cmd(
        git_exec,
        target_dir,
        ["log", "-1", "--format=%cd", "--date=short"],
        timeout_seconds,
    )
    if date_out:
        default_info["last_commit_date"] = date_out

    return default_info


def _evaluate_health(checks: dict[str, bool]) -> tuple[float, list[dict[str, Any]]]:
    """Tính toán điểm sức khỏe và sinh danh sách cảnh báo theo chuẩn issue."""
    score = 0.0
    issues: list[dict[str, Any]] = []

    if checks["has_readme"]:
        score += 30.0
    else:
        issues.append({
            "tool": "project_health",
            "file": "README.md",
            "line": 0,
            "severity": "Medium",
            "message": "Dự án thiếu file README hướng dẫn sử dụng.",
        })

    if checks["has_license"]:
        score += 20.0
    else:
        issues.append({
            "tool": "project_health",
            "file": "LICENSE",
            "line": 0,
            "severity": "Low",
            "message": "Dự án chưa khai báo giấy phép mã nguồn (LICENSE).",
        })

    if checks["has_tests"]:
        score += 30.0
    else:
        issues.append({
            "tool": "project_health",
            "file": "tests/",
            "line": 0,
            "severity": "Medium",
            "message": "Dự án chưa có thư mục viết test tự động (tests/).",
        })

    if checks["has_gitignore"]:
        score += 20.0

    return score, issues


def analyze_project_health(
    target_path: str | Path,
    timeout_seconds: int = 15,
) -> dict[str, Any]:
    """
    Phân tích sức khỏe dự án: kiểm tra tệp chuẩn mực, điểm số và thông tin Git.

    Args:
        target_path: Đường dẫn tới thư mục dự án.
        timeout_seconds: Thời gian chờ tối đa cho các lệnh git (mặc định 15s).

    Returns:
        dict chứa điểm số sức khỏe, kết quả kiểm tra từng tiêu chí, thông tin Git và issues:
        {
            "status": "ok",
            "health_score": float,
            "checks": {
                "has_readme": bool,
                "has_license": bool,
                "has_tests": bool,
                "has_gitignore": bool
            },
            "git": {
                "is_git_repo": bool,
                "total_commits": int,
                "contributors_count": int,
                "last_commit_date": str
            },
            "total_issues": int,
            "issues": list[dict]
        }
    """
    target = Path(target_path).resolve()
    target_dir = target if target.is_dir() else target.parent

    if not target_dir.exists():
        return {
            "status": "error",
            "message": f"Thư mục không tồn tại: {target_path}",
            "health_score": 0.0,
            "checks": {
                "has_readme": False,
                "has_license": False,
                "has_tests": False,
                "has_gitignore": False,
            },
            "git": {
                "is_git_repo": False,
                "total_commits": 0,
                "contributors_count": 0,
                "last_commit_date": "N/A",
            },
            "total_issues": 0,
            "issues": [],
        }

    checks = _check_presence(target_dir)
    git_info = _extract_git_info(target_dir, timeout_seconds)
    score, issues = _evaluate_health(checks)

    return {
        "status": "ok",
        "health_score": score,
        "checks": checks,
        "git": git_info,
        "total_issues": len(issues),
        "issues": issues,
    }


if __name__ == "__main__":
    sample_dir = Path(__file__).resolve().parents[1] / "samples" / "bad_project"
    print(f"[*] Đang thực hiện kiểm tra sức khỏe dự án: {sample_dir}")
    health_result = analyze_project_health(sample_dir)
    print(json.dumps(health_result, indent=2, ensure_ascii=False))
