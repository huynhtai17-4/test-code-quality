"""Module đo lường độ phức tạp (CC) và chỉ số bảo trì (MI) bằng Radon."""

import os
from pathlib import Path
from typing import Any

import radon.complexity as radon_cc
import radon.metrics as radon_mi
import radon.raw as radon_raw

_IGNORE_DIRS = frozenset({
    ".git",
    ".hg",
    ".svn",
    "__pycache__",
    ".venv",
    "venv",
    "env",
    ".env",
    "node_modules",
    ".pytest_cache",
    ".mypy_cache",
})


def _rank_to_severity(rank: str) -> str:
    """Chuyển đổi xếp hạng Radon sang mức độ nghiêm trọng chuẩn."""
    rank_upper = str(rank).upper()
    if rank_upper in ("E", "F"):
        return "Critical"
    if rank_upper == "D":
        return "High"
    if rank_upper == "C":
        return "Medium"
    return "Low"


def _analyze_cc(source_code: str, rel_path: str) -> tuple[float, list[dict[str, Any]]]:
    """Đo Cyclomatic Complexity và phát hiện các khối mã có độ phức tạp cao."""
    issues: list[dict[str, Any]] = []
    try:
        cc_blocks = radon_cc.cc_visit(source_code)
    except Exception as exc:  # pylint: disable=broad-exception-caught
        return 1.0, [{
            "tool": "radon",
            "file": rel_path,
            "line": 1,
            "severity": "Low",
            "message": f"Lỗi cú pháp khi phân tích CC: {exc}",
            "rule_code": "RADON_PARSE_ERR",
            "test_id": "RADON_PARSE_ERR",
        }]

    complexities = [block.complexity for block in cc_blocks]
    avg_cc = round(float(sum(complexities) / len(complexities)), 2) if complexities else 1.0

    for block in cc_blocks:
        rank = getattr(block, "rank", radon_cc.cc_rank(block.complexity))
        if block.complexity >= 11 or rank in ("C", "D", "E", "F"):
            type_label = "Lớp" if getattr(block, "letter", "M") == "C" else "Hàm"
            issues.append({
                "tool": "radon",
                "file": rel_path,
                "line": getattr(block, "lineno", 1),
                "severity": _rank_to_severity(rank),
                "message": (
                    f"{type_label} '{block.name}' có độ phức tạp cao "
                    f"(CC = {block.complexity}, Hạng {rank})"
                ),
                "rule_code": f"RADON_CC_{rank}",
                "test_id": f"RADON_CC_{rank}",
            })
    return avg_cc, issues


def _analyze_mi(source_code: str, rel_path: str) -> tuple[float, list[dict[str, Any]]]:
    """Đo Maintainability Index (MI) và phát hiện file có chỉ số kém."""
    issues: list[dict[str, Any]] = []
    try:
        score = float(radon_mi.mi_visit(source_code, multi=True))
        mi_score = round(max(0.0, min(100.0, score)), 2)
        rank = radon_mi.mi_rank(mi_score)
    except Exception:  # pylint: disable=broad-exception-caught
        return 100.0, []

    if rank == "C" or mi_score < 10.0:
        issues.append({
            "tool": "radon",
            "file": rel_path,
            "line": 1,
            "severity": "High",
            "message": f"Chỉ số bảo trì mã nguồn rất kém (MI = {mi_score}, Hạng {rank})",
            "rule_code": "RADON_MI_POOR",
            "test_id": "RADON_MI_POOR",
        })
    elif rank == "B" or mi_score < 20.0:
        issues.append({
            "tool": "radon",
            "file": rel_path,
            "line": 1,
            "severity": "Medium",
            "message": f"Chỉ số bảo trì mã nguồn trung bình (MI = {mi_score}, Hạng {rank})",
            "rule_code": "RADON_MI_MED",
            "test_id": "RADON_MI_MED",
        })
    return mi_score, issues


def _analyze_file(
    file_path: Path,
    base_dir: Path,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Phân tích độ phức tạp và chỉ số bảo trì cho một file Python cụ thể."""
    if file_path == base_dir:
        rel_path = file_path.name
    else:
        rel_path = str(file_path.relative_to(base_dir)).replace("\\", "/")

    try:
        source_code = file_path.read_text(encoding="utf-8", errors="replace")
    except Exception as exc:  # pylint: disable=broad-exception-caught
        return {
            "file": rel_path,
            "cc": 1.0,
            "complexity": 1.0,
            "mi": 50.0,
            "maintainability_index": 50.0,
            "loc": 0,
        }, [{
            "tool": "radon",
            "file": rel_path,
            "line": 1,
            "severity": "Low",
            "message": f"Không thể đọc file: {exc}",
            "rule_code": "RADON_READ_ERR",
            "test_id": "RADON_READ_ERR",
        }]

    avg_cc, cc_issues = _analyze_cc(source_code, rel_path)
    mi_score, mi_issues = _analyze_mi(source_code, rel_path)

    try:
        loc = radon_raw.analyze(source_code).loc
    except Exception:  # pylint: disable=broad-exception-caught
        loc = len(source_code.splitlines())

    file_info = {
        "file": rel_path,
        "cc": avg_cc,
        "complexity": avg_cc,
        "mi": mi_score,
        "maintainability_index": mi_score,
        "loc": loc,
    }

    return file_info, cc_issues + mi_issues


def _find_py_files(target: Path) -> list[Path]:
    """Tìm kiếm đệ quy toàn bộ file Python trong đường dẫn mục tiêu."""
    if target.is_file():
        return [target] if target.suffix.lower() == ".py" else []

    py_files: list[Path] = []
    for root, dirs, files in os.walk(target):
        dirs[:] = [d for d in dirs if d not in _IGNORE_DIRS]
        for file_name in files:
            if file_name.endswith(".py"):
                py_files.append(Path(root) / file_name)
    return py_files


def analyze_directory_metrics(target_path: str | Path) -> dict[str, Any]:
    """
    Phân tích toàn diện chỉ số CC và MI cho toàn bộ file Python trong thư mục.

    Args:
        target_path: Đường dẫn thư mục hoặc file cần đo lường.

    Returns:
        dict chứa trạng thái, điểm bảo trì trung bình, thống kê file và danh sách lỗi.
    """
    target = Path(target_path).resolve()
    if not target.exists():
        return {
            "status": "error",
            "message": f"Đường dẫn không tồn tại: {target_path}",
            "avg_maintainability": 100.0,
            "avg_complexity": 1.0,
            "files": [],
            "issues": [],
        }

    py_files = _find_py_files(target)
    if not py_files:
        return {
            "status": "ok",
            "avg_maintainability": 100.0,
            "avg_complexity": 1.0,
            "total_files": 0,
            "total_loc": 0,
            "files": [],
            "issues": [],
        }

    base_dir = target if target.is_dir() else target.parent
    files_info: list[dict[str, Any]] = []
    all_issues: list[dict[str, Any]] = []

    for py_file in py_files:
        info, issues = _analyze_file(py_file, base_dir)
        files_info.append(info)
        all_issues.extend(issues)

    avg_mi = round(float(sum(f["mi"] for f in files_info) / len(files_info)), 2)
    avg_cc = round(float(sum(f["cc"] for f in files_info) / len(files_info)), 2)

    return {
        "status": "ok",
        "avg_maintainability": avg_mi,
        "avg_complexity": avg_cc,
        "total_files": len(files_info),
        "total_loc": sum(f["loc"] for f in files_info),
        "files": files_info,
        "issues": all_issues,
    }


def analyze_radon(target_path: str | Path) -> dict[str, Any]:
    """Bí danh tương thích với quy ước analyze_<tool> cho Radon."""
    return analyze_directory_metrics(target_path)
