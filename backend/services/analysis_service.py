"""Module điều phối quy trình phân tích mã nguồn và lưu trữ kết quả phân tích."""

import json
import logging
import sys
from pathlib import Path
from typing import Any

# Đảm bảo đường dẫn import hoạt động khi chạy trực tiếp file này
ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# pylint: disable=wrong-import-position
from backend.analyzer import (
    aggregator,
    lint_flake8,
    lint_pylint,
    metrics_radon,
    scoring,
    source_loader,
)
from backend.analyzer.dependency_audit import audit_dependencies
from backend.analyzer.project_health import analyze_project_health
from backend.analyzer.security_bandit import analyze_bandit
from backend.database.repositories import (
    config_repo,
    issue_repo,
    project_repo,
    session_repo,
)

logger = logging.getLogger(__name__)


def _detect_source_type(source_path: str) -> str:
    """Tự động suy đoán loại nguồn dựa trên đường dẫn hoặc liên kết."""
    clean_path = str(source_path).strip().lower()
    if clean_path.endswith(".zip"):
        return "zip"
    if clean_path.startswith(("http://", "https://", "git@")):
        return "github"
    return "local_dir"


def _load_weights_from_db() -> dict[str, float]:
    """Nạp bảng trọng số từ cơ sở dữ liệu và ánh xạ sang tiêu chí chuẩn."""
    key_mapping = {
        "maintainability": "complexity",
        "complexity": "complexity",
        "security": "security",
        "code_style": "pylint",
        "pylint": "pylint",
        "project_health": "health",
        "health": "health",
        "dependency": "dependency",
    }
    weights: dict[str, float] = {}
    try:
        configs = config_repo.get_all_configs(active_only=True)
        for item in configs:
            raw_key = str(item.get("metric_key", "")).strip()
            target_key = key_mapping.get(raw_key, raw_key)
            weights[target_key] = float(item.get("weight", 0.0))
    except Exception as exc:  # pylint: disable=broad-exception-caught
        logger.warning("Không thể nạp trọng số từ CSDL (%s), dùng mặc định.", exc)
    return weights


def _convert_issues_for_db(raw_issues: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Chuyển đổi danh sách lỗi sang cấu trúc bảng issues trong CSDL."""
    db_issues: list[dict[str, Any]] = []
    category_map = {
        "bandit": "security",
        "pip-audit": "dependency",
        "project_health": "health",
        "radon": "complexity",
        "pylint": "code_style",
        "flake8": "code_style",
    }

    for item in raw_issues:
        raw_sev = str(item.get("severity", "medium")).strip().lower()
        if raw_sev not in {"info", "low", "medium", "high", "critical"}:
            raw_sev = "medium"

        tool = str(item.get("tool") or "unknown").strip()
        file_path = str(item.get("file_path") or item.get("file") or ".").replace("\\", "/")
        rule_code = item.get("rule_code") or item.get("test_id") or ""
        line_no = item.get("line_number")
        if line_no is None and "line" in item:
            line_no = item["line"]

        category = item.get("category") or category_map.get(tool, "quality")

        db_issues.append({
            "tool": tool,
            "rule_code": rule_code,
            "severity": raw_sev,
            "category": category,
            "file_path": file_path,
            "line_number": line_no,
            "column_number": item.get("column_number"),
            "message": str(item.get("message", "")),
            "status": item.get("status", "open"),
            "note": item.get("note"),
        })
    return db_issues


def _run_analyzers(
    working_dir: Path,
) -> tuple[
    dict[str, Any],
    dict[str, Any],
    dict[str, Any],
    dict[str, Any],
    dict[str, Any],
    dict[str, Any],
]:
    """Thực thi các bộ quét mã nguồn thực tế trên thư mục làm việc."""
    # 1. Radon
    radon_data = metrics_radon.analyze_directory_metrics(working_dir)

    # 2. Pylint
    pylint_data = lint_pylint.analyze_pylint(working_dir)

    # 3. Bandit
    bandit_data = analyze_bandit(working_dir)

    # 4. Pip-audit
    audit_data = audit_dependencies(working_dir)

    # 5. Project Health
    health_data = analyze_project_health(working_dir)

    # 6. Flake8
    flake8_data = lint_flake8.analyze_flake8(working_dir)

    return radon_data, pylint_data, bandit_data, audit_data, health_data, flake8_data


def _perform_scan_and_aggregation(
    working_dir: Path,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    """Chạy quét các bộ công cụ, tổng hợp kết quả và tính điểm."""
    radon_data, pylint_data, bandit_data, audit_data, health_data, flake8_data = _run_analyzers(
        working_dir
    )

    aggregated = aggregator.aggregate_analysis_results(
        radon_data=radon_data,
        pylint_data=pylint_data,
        bandit_data=bandit_data,
        audit_data=audit_data,
        health_data=health_data,
        flake8_data=flake8_data,
    )

    weights = _load_weights_from_db()
    criteria_scores = scoring.build_criteria_scores(
        radon_data=radon_data,
        bandit_data=bandit_data,
        pylint_data=pylint_data,
        health_data=health_data,
        audit_data=audit_data,
    )
    score_res = scoring.calculate_final_score(criteria_scores, weights)

    total_files = len(aggregated.get("file_summary", [])) or int(radon_data.get("total_files", 0))
    total_loc = int(radon_data.get("total_loc", 0))
    aggregated["total_files"] = total_files
    aggregated["total_loc"] = total_loc

    return aggregated, score_res, pylint_data


def _persist_results(
    project_id: int,
    aggregated: dict[str, Any],
    score_res: dict[str, Any],
    pylint_data: dict[str, Any],
) -> int:
    """Lưu trữ kết quả phân tích vào MySQL (phiên quét và các lỗi)."""
    total_score = float(score_res["total_score"])
    grade = str(score_res["grade"])
    criteria = score_res["criteria_scores"]
    severity_dist = aggregated.get("severity_distribution", {})

    summary_payload = {
        "total_score": total_score,
        "grade": grade,
        "criteria_scores": criteria,
        "severity_distribution": severity_dist,
        "top_risk_files": aggregated.get("top_risk_files", []),
        "weights_used": score_res.get("weights_used", {}),
        "total_files": aggregated.get("total_files", len(aggregated.get("file_summary", []))),
        "total_loc": aggregated.get("total_loc", 0),
    }
    summary_json = json.dumps(summary_payload, ensure_ascii=False)

    session_id = session_repo.create_session(
        project_id=project_id,
        total_score=total_score,
        grade=grade,
        summary=summary_json,
        status="completed",
    )

    metric_update = {
        "total_files": len(aggregated.get("file_summary", [])),
        "total_issues": int(aggregated.get("total_issues_count", 0)),
        "maintainability_index": criteria.get("complexity"),
        "pylint_score": (
            pylint_data.get("score")
            or pylint_data.get("pylint_score")
        ),
        "security_issues_count": (
            severity_dist.get("Critical", 0) + severity_dist.get("High", 0)
        ),
        "summary": summary_json,
    }
    valid_metrics = {k: v for k, v in metric_update.items() if v is not None}
    session_repo.update_session_results(
        session_id=session_id,
        total_score=total_score,
        grade=grade,
        status="completed",
        metrics=valid_metrics,
    )

    db_issues = _convert_issues_for_db(aggregated.get("all_issues", []))
    if db_issues:
        issue_repo.bulk_create_issues(session_id, db_issues)

    return session_id


def run_project_analysis(
    project_id: int,
    workspace_root: str | Path | None = None,
) -> dict[str, Any]:
    """
    Điều phối toàn bộ quy trình phân tích mã nguồn và lưu kết quả vào MySQL.

    Args:
        project_id: ID của dự án cần phân tích trong bảng projects.
        workspace_root: Thư mục chứa workspace tạm thời (tùy chọn).

    Returns:
        dict: Kết quả phân tích chuẩn hoặc thông báo lỗi.
    """
    try:
        # Bước 1 (Lấy thông tin dự án)
        project = project_repo.get_project_by_id(project_id)
        if not project:
            return {"status": "error", "message": "Dự án không tồn tại"}

        source_path = project.get("source_path") or project.get("path") or ""
        source_type = project.get("source_type") or _detect_source_type(source_path)

        # Bước 2 (Chuẩn bị mã nguồn)
        prep_res = source_loader.prepare_source(source_type, source_path, workspace_root)
        if prep_res.get("status") != "ok":
            return {
                "status": "error",
                "message": prep_res.get("message", "Lỗi chuẩn bị mã nguồn"),
            }

        working_dir = Path(prep_res["working_dir"]).resolve()
        cleanup_needed = bool(prep_res.get("cleanup_needed", False))

        # Bước 3, 4, 5 trong khối try...finally
        try:
            aggregated, score_res, pylint_data = _perform_scan_and_aggregation(
                working_dir
            )

            # Bước 5 (Lưu trữ CSDL)
            session_id = _persist_results(project_id, aggregated, score_res, pylint_data)

            return {
                "status": "ok",
                "session_id": session_id,
                "project_id": project_id,
                "total_score": float(score_res["total_score"]),
                "grade": str(score_res["grade"]),
                "criteria_scores": score_res["criteria_scores"],
                "severity_distribution": aggregated.get("severity_distribution", {}),
                "top_risk_files": aggregated.get("top_risk_files", []),
                "file_summary": aggregated.get("file_summary", []),
                "total_issues": int(aggregated.get("total_issues_count", 0)),
                "total_files": aggregated.get("total_files", len(aggregated.get("file_summary", []))),
                "total_loc": int(aggregated.get("total_loc", 0)),
            }

        finally:
            # Bước 6 (Dọn dẹp)
            if cleanup_needed and working_dir.exists():
                source_loader.cleanup_workspace(working_dir)

    except Exception as exc:  # pylint: disable=broad-exception-caught
        logger.exception("Lỗi trong quá trình phân tích dự án %s", project_id)
        return {"status": "error", "message": str(exc)}


def _run_test_service() -> None:
    """Kịch bản kiểm thử tích hợp cho tầng điều phối analysis_service."""
    import pprint  # pylint: disable=import-outside-toplevel

    sample_bad_project = ROOT_DIR / "backend" / "samples" / "bad_project"
    print(f"[*] Thư mục dự án mẫu: {sample_bad_project}")
    if not sample_bad_project.exists():
        print(f"[-] Không tìm thấy thư mục mẫu: {sample_bad_project}")
        return

    # 1. Tạo dự án mẫu trong database
    test_proj_name = "Test Bad Project - Integration Analysis"
    proj_id = project_repo.create_project(
        name=test_proj_name,
        path=str(sample_bad_project),
        description="Dự án mẫu kiểm thử tự động tầng analysis_service",
    )
    print(f"[+] Đã tạo dự án mẫu thành công! Project ID = {proj_id}")

    try:
        # 2. Chạy quy trình phân tích
        print("\n[*] Đang thực thi quy trình phân tích run_project_analysis()...")
        result = run_project_analysis(proj_id)

        print("\n========== KẾT QUẢ PHÂN TÍCH TRẢ VỀ ==========")
        pprint.pprint(result)

        if result.get("status") != "ok":
            print(f"[-] Quá trình phân tích thất bại: {result.get('message')}")
            return

        session_id = result["session_id"]

        # 3. Kiểm tra CSDL xem session và issues đã được lưu chưa
        print(f"\n[*] Kiểm tra CSDL cho Session ID = {session_id}...")
        session_record = session_repo.get_session_by_id(session_id)
        if session_record:
            print("[+] Bản ghi session trong MySQL:")
            print(f"    - ID           : {session_record['id']}")
            print(f"    - Status       : {session_record['status']}")
            print(f"    - Total Score  : {session_record['total_score']}")
            print(f"    - Grade        : {session_record['grade']}")
            print(f"    - Total Issues : {session_record['total_issues']}")
            print(f"    - Security Cnt : {session_record['security_issues_count']}")
        else:
            print("[-] Không tìm thấy session trong CSDL!")

        saved_issues = issue_repo.get_issues_by_session(session_id)
        print(f"[+] Số lượng lỗi đã lưu trong bảng issues: {len(saved_issues)}")
        if saved_issues:
            print("    - 3 lỗi đầu tiên:")
            for issue in saved_issues[:3]:
                print(
                    f"      * [{issue['tool'].upper()}][{issue['severity'].upper()}] "
                    f"{issue['file_path']}:{issue['line_number']} - {issue['message'][:60]}..."
                )

    finally:
        # 4. Dọn dẹp dự án mẫu
        print(f"\n[*] Dọn dẹp dữ liệu kiểm thử (Xóa Project ID = {proj_id})...")
        deleted = project_repo.delete_project(proj_id)
        print(f"[+] Dọn dẹp hoàn tất: {deleted}")


if __name__ == "__main__":
    _run_test_service()
