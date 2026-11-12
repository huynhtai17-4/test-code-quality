"""Module hợp nhất và phân tích tổng hợp kết quả chất lượng mã nguồn bằng Pandas."""

import json
from pathlib import Path
from typing import Any

import pandas as pd

_VALID_SEVERITIES = ("Critical", "High", "Medium", "Low")
_SEVERITY_MAPPING = {
    "CRITICAL": "Critical",
    "HIGH": "High",
    "MEDIUM": "Medium",
    "LOW": "Low",
    "INFO": "Low",
}


def _normalize_issues(*issue_lists: list[dict[str, Any]]) -> pd.DataFrame:
    """Gom toàn bộ issues vào một danh sách phẳng và nạp vào pandas.DataFrame."""
    flat_rows: list[dict[str, Any]] = []

    for issue_list in issue_lists:
        for item in issue_list:
            if not isinstance(item, dict):
                continue
            raw_sev = str(item.get("severity", "Low")).strip().upper()
            mapped_sev = _SEVERITY_MAPPING.get(raw_sev, "Low")

            raw_file = str(item.get("file", "")).replace("\\", "/")
            raw_line = item.get("line")
            try:
                line_no = int(raw_line) if raw_line is not None else 0
            except (ValueError, TypeError):
                line_no = 0

            flat_rows.append({
                "file": raw_file,
                "line": line_no,
                "tool": str(item.get("tool", "unknown")),
                "severity": mapped_sev,
                "message": str(item.get("message", "")),
                "test_id": str(item.get("test_id", "")),
            })

    columns = ["file", "line", "tool", "severity", "message", "test_id"]
    if not flat_rows:
        return pd.DataFrame(columns=columns)
    return pd.DataFrame(flat_rows, columns=columns)


def _build_severity_distribution(df_issues: pd.DataFrame) -> dict[str, int]:
    """Sử dụng Pandas tính phân bố số lượng lỗi theo 4 mức độ nghiêm trọng."""
    counts: dict[str, int] = {sev: 0 for sev in _VALID_SEVERITIES}
    if not df_issues.empty and "severity" in df_issues.columns:
        series_counts = df_issues["severity"].value_counts()
        for sev in _VALID_SEVERITIES:
            counts[sev] = int(series_counts.get(sev, 0))
    return counts


def _extract_radon_df(radon_data: dict[str, Any]) -> pd.DataFrame:
    """Trích xuất thông tin chỉ số cc và mi từ kết quả Radon thành DataFrame."""
    rows: list[dict[str, Any]] = []
    files_info = radon_data.get("files")

    if isinstance(files_info, list):
        for item in files_info:
            if isinstance(item, dict) and "file" in item:
                rows.append({
                    "file": str(item["file"]).replace("\\", "/"),
                    "cc": item.get("cc") or item.get("complexity"),
                    "mi": item.get("mi") or item.get("maintainability_index"),
                })
    elif isinstance(files_info, dict):
        for fname, metrics in files_info.items():
            if isinstance(metrics, dict):
                rows.append({
                    "file": str(fname).replace("\\", "/"),
                    "cc": metrics.get("cc") or metrics.get("complexity"),
                    "mi": metrics.get("mi") or metrics.get("maintainability_index"),
                })

    if not rows:
        return pd.DataFrame(columns=["file", "cc", "mi"])
    return pd.DataFrame(rows)


def _clean_records(df: pd.DataFrame) -> list[dict[str, Any]]:
    """Chuyển đổi DataFrame sang list[dict], thay thế các giá trị NaN bằng None."""
    return [
        {k: (None if pd.isna(v) else v) for k, v in row.items()}
        for row in df.to_dict(orient="records")
    ]


def _build_file_summary(
    df_issues: pd.DataFrame,
    df_radon: pd.DataFrame,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Nhóm theo file, ghép nối chỉ số Radon và trích xuất danh sách Top rủi ro."""
    count_cols = ["total_issues", "critical_count", "high_count", "medium_count", "low_count"]

    if df_issues.empty:
        if df_radon.empty:
            return [], []
        base = df_radon.copy()
        for col in count_cols:
            base[col] = 0
    else:
        total_by_file = df_issues.groupby("file").size().reset_index(name="total_issues")
        crosstab = (
            pd.crosstab(df_issues["file"], df_issues["severity"])
            .reindex(columns=list(_VALID_SEVERITIES), fill_value=0)
            .reset_index()
            .rename(columns={
                "Critical": "critical_count",
                "High": "high_count",
                "Medium": "medium_count",
                "Low": "low_count",
            })
        )
        stats = pd.merge(total_by_file, crosstab, on="file", how="left")
        if not df_radon.empty:
            base = pd.merge(stats, df_radon, on="file", how="outer")
        else:
            base = stats.copy()
            base["cc"] = None
            base["mi"] = None

    for col in count_cols:
        if col in base.columns:
            base[col] = base[col].fillna(0).astype(int)
        else:
            base[col] = 0

    sorted_df = base.sort_values(
        by=["critical_count", "high_count", "total_issues"],
        ascending=[False, False, False],
    )
    top_5 = sorted_df.head(5).copy()

    return _clean_records(sorted_df), _clean_records(top_5)


def aggregate_analysis_results(
    radon_data: dict[str, Any],
    pylint_data: dict[str, Any],
    bandit_data: dict[str, Any],
    audit_data: dict[str, Any],
    health_data: dict[str, Any],
    flake8_data: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Hợp nhất và phân tích kết quả từ các module phân tích bằng Pandas.

    Args:
        radon_data: Kết quả đo độ phức tạp và chỉ số bảo trì từ Radon.
        pylint_data: Kết quả phân tích tĩnh và linting từ Pylint.
        bandit_data: Kết quả quét lỗ hổng bảo mật từ Bandit.
        audit_data: Kết quả kiểm tra CVE phụ thuộc từ Pip-audit.
        health_data: Kết quả kiểm tra sức khỏe và cấu trúc dự án.
        flake8_data: Kết quả phân tích phong cách PEP 8 từ Flake8 (tùy chọn).

    Returns:
        dict tổng hợp thống kê mức độ nghiêm trọng, file summary và top rủi ro.
    """
    issue_lists = [
        pylint_data.get("issues", []),
        bandit_data.get("issues", []),
        audit_data.get("issues", []),
        health_data.get("issues", []),
        radon_data.get("issues", []),
    ]
    if flake8_data and isinstance(flake8_data, dict):
        issue_lists.append(flake8_data.get("issues", []))

    df_issues = _normalize_issues(*issue_lists)

    df_radon = _extract_radon_df(radon_data)
    severity_dist = _build_severity_distribution(df_issues)
    file_summary, top_risk_files = _build_file_summary(df_issues, df_radon)

    all_issues = df_issues.to_dict(orient="records") if not df_issues.empty else []

    return {
        "status": "ok",
        "total_issues_count": len(all_issues),
        "all_issues": all_issues,
        "severity_distribution": severity_dist,
        "file_summary": file_summary,
        "top_risk_files": top_risk_files,
    }


def _default_radon_result(_path: Path) -> dict[str, Any]:
    return {
        "status": "ok",
        "files": [{"file": "sample_vulnerable.py", "cc": 4.2, "mi": 65.0}],
    }


def _default_pylint_result(_path: Path) -> dict[str, Any]:
    return {
        "status": "ok",
        "issues": [
            {
                "tool": "pylint",
                "file": "sample_vulnerable.py",
                "line": 1,
                "severity": "Low",
                "message": "Missing module docstring (C0114)",
            }
        ],
    }


def _run_sample_aggregation() -> None:
    """Hàm phụ trợ cho khối __main__ để thực thi quét thử và in kết quả."""
    import sys  # pylint: disable=import-outside-toplevel
    root_dir = Path(__file__).resolve().parents[2]
    if str(root_dir) not in sys.path:
        sys.path.insert(0, str(root_dir))

    from backend.analyzer.dependency_audit import audit_dependencies  # pylint: disable=import-outside-toplevel
    from backend.analyzer.lint_flake8 import analyze_flake8  # pylint: disable=import-outside-toplevel
    from backend.analyzer.lint_pylint import analyze_pylint  # pylint: disable=import-outside-toplevel
    from backend.analyzer.metrics_radon import analyze_radon  # pylint: disable=import-outside-toplevel
    from backend.analyzer.project_health import analyze_project_health  # pylint: disable=import-outside-toplevel
    from backend.analyzer.security_bandit import analyze_bandit  # pylint: disable=import-outside-toplevel

    sample_dir = Path(__file__).resolve().parents[1] / "samples" / "bad_project"
    print(f"[*] Đang chạy tích hợp các analyzer trên: {sample_dir}")

    aggregated = aggregate_analysis_results(
        radon_data=analyze_radon(sample_dir),
        pylint_data=analyze_pylint(sample_dir),
        bandit_data=analyze_bandit(sample_dir),
        audit_data=audit_dependencies(sample_dir),
        health_data=analyze_project_health(sample_dir),
        flake8_data=analyze_flake8(sample_dir),
    )

    print("\n========== BẢNG PHÂN BỐ MỨC ĐỘ LỖI ==========")
    print(json.dumps(aggregated["severity_distribution"], indent=2))

    print("\n========== TOP 5 FILE CÓ RỦI RO CAO NHẤT ==========")
    for idx, item in enumerate(aggregated["top_risk_files"], 1):
        print(
            f"{idx}. File: {item['file']} | Tổng lỗi: {item['total_issues']} "
            f"(Critical: {item['critical_count']}, High: {item['high_count']}, "
            f"Medium: {item['medium_count']}, Low: {item['low_count']}) "
            f"| CC: {item.get('cc')} | MI: {item.get('mi')}"
        )


if __name__ == "__main__":
    _run_sample_aggregation()
