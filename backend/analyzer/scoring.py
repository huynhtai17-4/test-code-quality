"""Module tính điểm chất lượng mã nguồn và xếp loại sử dụng NumPy."""

import json
from pathlib import Path
from typing import Any

import numpy as np

CRITERIA_KEYS = ("complexity", "security", "pylint", "health", "dependency")

DEFAULT_WEIGHTS: dict[str, float] = {
    "complexity": 0.25,
    "security": 0.25,
    "pylint": 0.20,
    "health": 0.15,
    "dependency": 0.15,
}

PENALTY_COEFFICIENTS = np.array([10.0, 5.0, 2.0, 0.5], dtype=float)
SEVERITY_ORDER = ("Critical", "High", "Medium", "Low")


def calculate_security_score(severity_counts: dict[str, int]) -> float:
    """
    Tính điểm bảo mật (0.0 - 100.0) dựa trên vector nhân vô hướng hệ số phạt của NumPy.

    Công thức: max(0.0, 100.0 - (10*Critical + 5*High + 2*Medium + 0.5*Low))
    """
    counts = np.array(
        [max(0, int(severity_counts.get(sev, 0))) for sev in SEVERITY_ORDER],
        dtype=float,
    )
    penalty = float(np.dot(counts, PENALTY_COEFFICIENTS))
    return float(np.clip(100.0 - penalty, 0.0, 100.0))


def calculate_dependency_score(dependency_counts: dict[str, int]) -> float:
    """Tính điểm phụ thuộc (0.0 - 100.0) dựa trên trừ lùi các lỗ hổng CVE."""
    return calculate_security_score(dependency_counts)


def determine_grade(score: float) -> str:
    """
    Xếp loại chất lượng mã nguồn dựa trên thang điểm tổng kết (A, B, C, D, F).

    A >= 90.0, B >= 75.0, C >= 60.0, D >= 40.0, còn lại F.
    """
    bounded_score = float(np.clip(score, 0.0, 100.0))
    if bounded_score >= 90.0:
        return "A"
    if bounded_score >= 75.0:
        return "B"
    if bounded_score >= 60.0:
        return "C"
    if bounded_score >= 40.0:
        return "D"
    return "F"


def _count_issues_by_severity(issues: list[dict[str, Any]]) -> dict[str, int]:
    """Đếm số lượng lỗi theo từng mức độ nghiêm trọng từ danh sách issue."""
    counts = {sev: 0 for sev in SEVERITY_ORDER}
    for item in issues:
        if not isinstance(item, dict):
            continue
        raw_sev = str(item.get("severity", "Low")).strip().capitalize()
        if raw_sev in counts:
            counts[raw_sev] += 1
        elif raw_sev.upper() == "CRITICAL":
            counts["Critical"] += 1
        elif raw_sev.upper() == "HIGH":
            counts["High"] += 1
        elif raw_sev.upper() == "MEDIUM":
            counts["Medium"] += 1
        else:
            counts["Low"] += 1
    return counts


def _extract_complexity_score(radon_data: dict[str, Any]) -> float:
    """Trích xuất và chuẩn hóa điểm độ phức tạp / bảo trì từ kết quả Radon (0 - 100)."""
    mi_raw = radon_data.get("avg_maintainability")
    if mi_raw is not None:
        score = float(mi_raw)
    else:
        files = radon_data.get("files") or []
        mi_values = [
            float(f["mi"]) for f in files
            if isinstance(f, dict) and f.get("mi") is not None
        ]
        score = float(np.mean(mi_values)) if mi_values else 100.0
    return float(np.clip(score, 0.0, 100.0))


def build_criteria_scores(
    radon_data: dict[str, Any],
    bandit_data: dict[str, Any],
    pylint_data: dict[str, Any],
    health_data: dict[str, Any],
    audit_data: dict[str, Any],
) -> dict[str, float]:
    """
    Chuẩn hóa và tính toán điểm cho 5 tiêu chí thành phần về thang 0 - 100.

    - complexity: Lấy từ avg_maintainability của Radon (MI vốn từ 0-100).
    - security: Trừ lùi từ lỗi Bandit qua calculate_security_score.
    - pylint: Điểm Pylint thang 10 nhân 10.
    - health: Điểm health_score từ module project_health (0-100).
    - dependency: Trừ lùi từ lỗi Pip-audit qua calculate_dependency_score.
    """
    complexity_score = _extract_complexity_score(radon_data)

    bandit_counts = _count_issues_by_severity(bandit_data.get("issues", []))
    security_score = calculate_security_score(bandit_counts)

    pylint_raw = pylint_data.get("score", pylint_data.get("pylint_score", 10.0))
    pylint_score = float(np.clip(float(pylint_raw) * 10.0, 0.0, 100.0))

    health_raw = health_data.get("health_score", 100.0)
    health_score = float(np.clip(float(health_raw), 0.0, 100.0))

    audit_counts = _count_issues_by_severity(audit_data.get("issues", []))
    dependency_score = calculate_dependency_score(audit_counts)

    return {
        "complexity": round(complexity_score, 2),
        "security": round(security_score, 2),
        "pylint": round(pylint_score, 2),
        "health": round(health_score, 2),
        "dependency": round(dependency_score, 2),
    }


def _prepare_vectors(
    criteria_scores: dict[str, float],
    weights_dict: dict[str, float],
) -> tuple[np.ndarray, np.ndarray]:
    """Tạo các vector scores và weights tương ứng theo thứ tự chuẩn CRITERIA_KEYS."""
    scores_list: list[float] = []
    weights_list: list[float] = []

    for key in CRITERIA_KEYS:
        score_val = float(criteria_scores.get(key, 0.0))
        weight_val = float(weights_dict.get(key, DEFAULT_WEIGHTS.get(key, 0.2)))
        scores_list.append(score_val)
        weights_list.append(max(0.0, weight_val))

    scores_vec = np.array(scores_list, dtype=float)
    weights_vec = np.array(weights_list, dtype=float)

    sum_weights = float(np.sum(weights_vec))
    if sum_weights > 0:
        normalized_weights = weights_vec / sum_weights
    else:
        normalized_weights = np.ones(len(CRITERIA_KEYS), dtype=float) / len(CRITERIA_KEYS)

    return scores_vec, normalized_weights


def calculate_final_score(
    criteria_scores: dict[str, float],
    weights_config: dict[str, float] | None = None,
) -> dict[str, Any]:
    """
    Tính điểm chất lượng tổng hợp cốt lõi bằng tích vô hướng vector NumPy.

    Args:
        criteria_scores: Điểm của 5 tiêu chí (complexity, security, pylint, health, dependency).
        weights_config: Bảng trọng số tùy chỉnh (tự động fallback về DEFAULT_WEIGHTS nếu rỗng).

    Returns:
        dict chứa điểm tổng kết, xếp loại, điểm thành phần và trọng số đã áp dụng:
        {
            "total_score": float,
            "grade": str,
            "criteria_scores": dict[str, float],
            "weights_used": dict[str, float]
        }
    """
    raw_weights = weights_config if weights_config else DEFAULT_WEIGHTS
    scores_vec, normalized_weights = _prepare_vectors(criteria_scores, raw_weights)

    # Tính điểm tổng bằng tích vô hướng vector (np.dot)
    total_score = float(np.clip(np.dot(scores_vec, normalized_weights), 0.0, 100.0))
    rounded_total = round(total_score, 2)
    grade = determine_grade(rounded_total)

    weights_used = {
        key: round(float(normalized_weights[i]), 4)
        for i, key in enumerate(CRITERIA_KEYS)
    }

    normalized_criteria = {
        key: round(float(scores_vec[i]), 2)
        for i, key in enumerate(CRITERIA_KEYS)
    }

    return {
        "total_score": rounded_total,
        "grade": grade,
        "criteria_scores": normalized_criteria,
        "weights_used": weights_used,
    }


def _run_sample_scoring() -> None:
    """Hàm phụ trợ cho khối __main__ chạy thử nghiệm chấm điểm với dữ liệu thực tế."""
    import sys  # pylint: disable=import-outside-toplevel
    root_dir = Path(__file__).resolve().parents[2]
    if str(root_dir) not in sys.path:
        sys.path.insert(0, str(root_dir))

    from backend.analyzer.dependency_audit import audit_dependencies  # pylint: disable=import-outside-toplevel
    from backend.analyzer.project_health import analyze_project_health  # pylint: disable=import-outside-toplevel
    from backend.analyzer.security_bandit import analyze_bandit  # pylint: disable=import-outside-toplevel

    sample_dir = Path(__file__).resolve().parents[1] / "samples" / "bad_project"
    print(f"[*] Thu thập dữ liệu phân tích từ: {sample_dir}")

    bandit_res = analyze_bandit(sample_dir)
    audit_res = audit_dependencies(sample_dir)
    health_res = analyze_project_health(sample_dir)
    radon_res = {"status": "ok", "avg_maintainability": 65.0}
    pylint_res = {"status": "ok", "score": 7.2}

    criteria = build_criteria_scores(
        radon_data=radon_res,
        bandit_data=bandit_res,
        pylint_data=pylint_res,
        health_data=health_res,
        audit_data=audit_res,
    )

    result = calculate_final_score(criteria)

    print("\n========== KẾT QUẢ CHẤM ĐIỂM TỔNG KẾT (NUMPY) ==========")
    print(f"Điểm tổng kết : {result['total_score']} / 100")
    print(f"Xếp loại      : Hạng {result['grade']}")
    print("\nĐiểm thành phần (Criteria Scores):")
    for k, v in result["criteria_scores"].items():
        print(f"  - {k:<12}: {v:>6.2f} / 100")
    print("\nTrọng số áp dụng (Weights Used):")
    for k, v in result["weights_used"].items():
        print(f"  - {k:<12}: {v*100:>5.1f}%")

    print("\nToàn bộ kết quả JSON:")
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    _run_sample_scoring()
