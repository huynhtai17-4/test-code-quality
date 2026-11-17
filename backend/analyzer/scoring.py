"""Module tính điểm chất lượng mã nguồn và xếp loại sử dụng NumPy."""

from __future__ import annotations

from typing import Any

import numpy as np

CRITERIA_KEYS = ("complexity", "security", "pylint", "health", "dependency", "malware")
QUALITY_KEYS = ("complexity", "pylint", "health")
SECURITY_KEYS = ("security", "dependency", "malware")

DEFAULT_WEIGHTS: dict[str, float] = {
    "complexity": 0.20,
    "security": 0.20,
    "pylint": 0.15,
    "health": 0.15,
    "dependency": 0.15,
    "malware": 0.15,
}

PENALTY_COEFFICIENTS = np.array([10.0, 5.0, 2.0, 0.5], dtype=float)
SEVERITY_ORDER = ("Critical", "High", "Medium", "Low")


def calculate_security_score(severity_counts: dict[str, int]) -> float:
    """Tính điểm bảo mật (0.0 - 100.0) dựa trên vector nhân vô hướng hệ số phạt của NumPy.

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


def calculate_malware_score(malware_counts: dict[str, int]) -> float:
    """Tính điểm phát hiện mã độc AST (0.0 - 100.0) dựa trên trừ lùi hệ số phạt NumPy."""
    return calculate_security_score(malware_counts)


def determine_grade(score: float) -> str:
    """Xếp loại chất lượng mã nguồn dựa trên thang điểm tổng kết (A, B, C, D, F).

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
    malware_data: dict[str, Any] | None = None,
) -> dict[str, float]:
    """Chuẩn hóa và tính toán điểm cho 6 tiêu chí thành phần về thang 0 - 100.

    - complexity: Lấy từ avg_maintainability của Radon (MI vốn từ 0-100).
    - security: Trừ lùi từ lỗi Bandit qua calculate_security_score.
    - pylint: Điểm Pylint thang 10 nhân 10.
    - health: Điểm health_score từ module project_health (0-100).
    - dependency: Trừ lùi từ lỗi Pip-audit qua calculate_dependency_score.
    - malware: Trừ lùi từ lỗi mã độc AST qua calculate_malware_score.
    """
    pylint_val = float(pylint_data.get("score", pylint_data.get("pylint_score", 10.0)))
    health_val = float(health_data.get("health_score", 100.0))
    malware_score = (
        calculate_malware_score(_count_issues_by_severity(malware_data.get("issues", [])))
        if malware_data and isinstance(malware_data, dict)
        else 100.0
    )

    return {
        "complexity": round(_extract_complexity_score(radon_data), 2),
        "security": round(calculate_security_score(_count_issues_by_severity(bandit_data.get("issues", []))), 2),
        "pylint": round(float(np.clip(pylint_val * 10.0, 0.0, 100.0)), 2),
        "health": round(float(np.clip(health_val, 0.0, 100.0)), 2),
        "dependency": round(calculate_dependency_score(_count_issues_by_severity(audit_data.get("issues", []))), 2),
        "malware": round(malware_score, 2),
    }


def _prepare_vectors(
    criteria_scores: dict[str, float],
    weights_dict: dict[str, float],
) -> tuple[np.ndarray, np.ndarray]:
    """Tạo các vector scores và weights tương ứng theo thứ tự chuẩn CRITERIA_KEYS."""
    scores_list: list[float] = []
    weights_list: list[float] = []

    for key in CRITERIA_KEYS:
        default_score = 100.0 if key == "malware" else 0.0
        score_val = float(criteria_scores.get(key, default_score))
        weight_val = float(weights_dict.get(key, DEFAULT_WEIGHTS.get(key, 0.15)))
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


def calculate_quality_score(
    criteria_scores: dict[str, float],
    weights_dict: dict[str, float] | None = None,
) -> float:
    """Tính điểm chất lượng mã nguồn tổng hợp từ complexity, pylint và health (thang 0-100)."""
    weights = weights_dict if weights_dict else DEFAULT_WEIGHTS
    scores = np.array([float(criteria_scores.get(k, 100.0)) for k in QUALITY_KEYS], dtype=float)
    raw_w = np.array(
        [max(0.0, float(weights.get(k, DEFAULT_WEIGHTS.get(k, 0.15)))) for k in QUALITY_KEYS],
        dtype=float,
    )
    sum_w = float(np.sum(raw_w))
    norm_w = raw_w / sum_w if sum_w > 0 else np.ones(len(QUALITY_KEYS), dtype=float) / len(QUALITY_KEYS)
    return float(np.clip(np.dot(scores, norm_w), 0.0, 100.0))


def calculate_security_group_score(
    criteria_scores: dict[str, float],
    weights_dict: dict[str, float] | None = None,
) -> float:
    """Tính điểm an toàn bảo mật tổng hợp từ security (Bandit), dependency và malware (thang 0-100)."""
    weights = weights_dict if weights_dict else DEFAULT_WEIGHTS
    scores = np.array([float(criteria_scores.get(k, 100.0)) for k in SECURITY_KEYS], dtype=float)
    raw_w = np.array(
        [max(0.0, float(weights.get(k, DEFAULT_WEIGHTS.get(k, 0.15)))) for k in SECURITY_KEYS],
        dtype=float,
    )
    sum_w = float(np.sum(raw_w))
    norm_w = raw_w / sum_w if sum_w > 0 else np.ones(len(SECURITY_KEYS), dtype=float) / len(SECURITY_KEYS)
    return float(np.clip(np.dot(scores, norm_w), 0.0, 100.0))


def calculate_final_score(
    criteria_scores: dict[str, float],
    weights_config: dict[str, float] | None = None,
) -> dict[str, Any]:
    """Tính điểm chất lượng tổng hợp cốt lõi và 2 hệ điểm Quality / Security bằng vector NumPy.

    Args:
        criteria_scores: Điểm của 6 tiêu chí (complexity, security, pylint, health, dependency, malware).
        weights_config: Bảng trọng số tùy chỉnh (fallback về DEFAULT_WEIGHTS nếu rỗng).

    Returns:
        dict chứa điểm tổng kết, chất lượng, bảo mật, xếp loại, điểm thành phần và trọng số đã dùng.
    """
    raw_weights = weights_config if weights_config else DEFAULT_WEIGHTS
    scores_vec, normalized_weights = _prepare_vectors(criteria_scores, raw_weights)

    total_score = float(np.clip(np.dot(scores_vec, normalized_weights), 0.0, 100.0))
    rounded_total = round(total_score, 2)
    grade = determine_grade(rounded_total)

    quality_score = calculate_quality_score(criteria_scores, raw_weights)
    security_score = calculate_security_group_score(criteria_scores, raw_weights)

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
        "quality_score": round(quality_score, 2),
        "security_score": round(security_score, 2),
        "grade": grade,
        "criteria_scores": normalized_criteria,
        "weights_used": weights_used,
    }
