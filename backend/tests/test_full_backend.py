"""Bộ kiểm thử tích hợp toàn diện cho toàn bộ hệ thống Backend.

Bao gồm:
1. Kết nối CSDL và Connection Pool.
2. Tầng Repositories (CRUD Projects, Sessions, Issues, Scoring Config).
3. Tầng Analyzer (Bandit, Pip-audit, Project Health, Aggregator, Scoring, Source Loader).
4. Tầng Services (Analysis Service Orchestrator).
5. Tầng Handlers (Project, Issue, History, Config, Analysis Handlers).
6. Tầng Router (Định tuyến Action).
7. Tầng Socket Server & Protocol (Mạng TCP đa luồng).
"""

import socket
import sys
import threading
import time
import zipfile
from pathlib import Path

# Đảm bảo import được toàn bộ package backend
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
from backend.database.connection import get_connection, test_connection
from backend.database.repositories import (
    config_repo,
    issue_repo,
    project_repo,
    session_repo,
)
from backend.handlers import (
    handle_create_issue,
    handle_create_project,
    handle_delete_history,
    handle_delete_issue,
    handle_delete_project,
    handle_get_config,
    handle_get_project,
    handle_list_history,
    handle_list_issues,
    handle_list_projects,
    handle_run_analysis,
    handle_update_config,
    handle_update_issue_status,
    handle_update_project,
)
from backend.network import protocol, router
from backend.network.socket_server import SocketServer
from backend.services.analysis_service import run_project_analysis

SAMPLE_BAD_PROJECT = ROOT_DIR / "backend" / "samples" / "bad_project"


def _check(condition: bool, message: str) -> None:
    """Hàm phụ trợ xác thực điều kiện kiểm thử."""
    if not condition:
        raise RuntimeError(f"KIỂM THỬ THẤT BẠI: {message}")


def test_section_database() -> None:
    """1. Kiểm thử kết nối CSDL và Connection Pool."""
    print("\n" + "=" * 60)
    print("[PHASE 1] KIỂM THỬ CSDL VÀ CONNECTION POOL")
    print("=" * 60)

    # 1.1 Test hàm test_connection
    conn_ok = test_connection()
    _check(conn_ok, "test_connection() trả về False!")
    print("  [OK] test_connection() thành công!")

    # 1.2 Test get_connection context manager
    with get_connection() as conn:
        _check(conn is not None and conn.is_connected(), "Không lấy được connection từ pool!")
        cursor = conn.cursor()
        cursor.execute("SELECT 1 + 1 AS result;")
        row = cursor.fetchone()
        cursor.close()
        _check(row[0] == 2, "Truy vấn SELECT 1 + 1 trả về kết quả sai!")
    print("  [OK] Context manager get_connection() hoạt động hoàn hảo!")


def test_section_repositories() -> None:
    """2. Kiểm thử tầng Repositories CRUD."""
    print("\n" + "=" * 60)
    print("[PHASE 2] KIỂM THỬ TẦNG REPOSITORIES (CRUD)")
    print("=" * 60)

    # 2.1 Project Repo
    proj_id = project_repo.create_project(
        name="Full Test Project",
        path=str(SAMPLE_BAD_PROJECT),
        description="Dự án kiểm thử tự động toàn diện",
    )
    _check(proj_id > 0, "create_project thất bại!")
    print(f"  [OK] project_repo.create_project -> ID: {proj_id}")

    proj = project_repo.get_project_by_id(proj_id)
    _check(proj is not None and proj["name"] == "Full Test Project", "get_project_by_id sai!")
    print("  [OK] project_repo.get_project_by_id thành công")

    updated = project_repo.update_project(proj_id, description="Mô tả cập nhật mới")
    _check(updated, "update_project thất bại!")
    print("  [OK] project_repo.update_project thành công")

    # 2.2 Session Repo
    sess_id = session_repo.create_session(
        project_id=proj_id,
        total_score=85.0,
        grade="B",
        status="completed",
    )
    _check(sess_id > 0, "create_session thất bại!")
    print(f"  [OK] session_repo.create_session -> ID: {sess_id}")

    session_repo.update_session_results(
        session_id=sess_id,
        total_score=87.5,
        grade="B",
        metrics={"total_issues": 10, "pylint_score": 8.5},
    )
    sess = session_repo.get_session_by_id(sess_id)
    _check(sess is not None and float(sess["total_score"]) == 87.5, "update_session_results sai!")
    print("  [OK] session_repo.update_session_results thành công")

    # 2.3 Issue Repo
    iss_id = issue_repo.create_issue(
        session_id=sess_id,
        file_path="sample.py",
        message="Lỗi kiểm thử",
        severity="high",
        tool="test_runner",
    )
    _check(iss_id > 0, "create_issue thất bại!")
    print(f"  [OK] issue_repo.create_issue -> ID: {iss_id}")

    bulk_count = issue_repo.add_issues_bulk(
        sess_id,
        [
            {
                "tool": "pylint",
                "file_path": "a.py",
                "severity": "medium",
                "message": "msg 1",
            },
            {
                "tool": "bandit",
                "file_path": "b.py",
                "severity": "low",
                "message": "msg 2",
            },
        ],
    )
    _check(bulk_count == 2, f"add_issues_bulk kỳ vọng 2, nhận {bulk_count}")
    print(f"  [OK] issue_repo.add_issues_bulk -> {bulk_count} bản ghi")

    issues = issue_repo.get_issues_by_session(sess_id)
    _check(len(issues) == 3, f"get_issues_by_session kỳ vọng 3, nhận {len(issues)}")
    print(f"  [OK] issue_repo.get_issues_by_session -> {len(issues)} bản ghi")

    up_st = issue_repo.update_issue_status(iss_id, "fixed", note="Đã sửa xong")
    _check(up_st, "update_issue_status thất bại!")
    print("  [OK] issue_repo.update_issue_status thành công")

    # 2.4 Config Repo
    configs = config_repo.get_all_configs(active_only=True)
    _check(len(configs) >= 5, "Bảng scoring_config thiếu dữ liệu mặc định!")
    first_cfg = configs[0]
    m_key = first_cfg["metric_key"]
    orig_w = float(first_cfg["weight"])

    config_repo.update_weight(m_key, 28.5)
    cfg_after = config_repo.get_config_by_key(m_key)
    _check(cfg_after is not None and float(cfg_after["weight"]) == 28.5, "update_weight sai!")
    config_repo.update_weight(m_key, orig_w)  # khôi phục
    print(f"  [OK] config_repo (get_all={len(configs)}, update_weight, restore) thành công")

    # Dọn dẹp Phase 2
    del_proj = project_repo.delete_project(proj_id)
    _check(del_proj, "Không xóa được dự án kiểm thử!")
    print("  [OK] project_repo.delete_project (cascade sessions & issues) thành công")


def test_section_analyzer() -> None:
    """3. Kiểm thử tầng Analyzer Engine."""
    print("\n" + "=" * 60)
    print("[PHASE 3] KIỂM THỬ TẦNG ANALYZER ENGINE")
    print("=" * 60)

    # 3.1 Security Bandit
    bandit_res = analyze_bandit(SAMPLE_BAD_PROJECT)
    _check(bandit_res.get("status") == "ok", "analyze_bandit thất bại!")
    print(f"  [OK] analyze_bandit: {bandit_res.get('total_issues')} lỗi phát hiện")

    # 3.2 Radon Metrics
    radon_res = metrics_radon.analyze_directory_metrics(SAMPLE_BAD_PROJECT)
    _check(radon_res.get("status") == "ok", "analyze_directory_metrics thất bại!")
    print(f"  [OK] metrics_radon: MI={radon_res.get('avg_maintainability')}, CC={radon_res.get('avg_complexity')}")

    # 3.3 Pylint Linting
    pylint_res = lint_pylint.analyze_pylint(SAMPLE_BAD_PROJECT)
    _check(pylint_res.get("status") == "ok", "analyze_pylint thất bại!")
    print(f"  [OK] lint_pylint: Score={pylint_res.get('score')}, Issues={pylint_res.get('total_issues')}")

    # 3.4 Flake8 Linting
    flake8_res = lint_flake8.analyze_flake8(SAMPLE_BAD_PROJECT)
    _check(flake8_res.get("status") == "ok", "analyze_flake8 thất bại!")
    print(f"  [OK] lint_flake8: Issues={flake8_res.get('total_issues')}")

    # 3.5 Dependency Audit
    audit_res = audit_dependencies(SAMPLE_BAD_PROJECT)
    _check(audit_res.get("status") in ("ok", "warning"), "audit_dependencies thất bại!")
    print(f"  [OK] audit_dependencies: status={audit_res.get('status')}")

    # 3.6 Project Health
    health_res = analyze_project_health(SAMPLE_BAD_PROJECT)
    _check(health_res.get("status") == "ok", "analyze_project_health thất bại!")
    print(f"  [OK] analyze_project_health: score={health_res.get('health_score')}")

    # 3.7 Aggregator
    agg_res = aggregator.aggregate_analysis_results(
        radon_data=radon_res,
        pylint_data=pylint_res,
        bandit_data=bandit_res,
        audit_data=audit_res,
        health_data=health_res,
        flake8_data=flake8_res,
    )
    _check(agg_res.get("status") == "ok", "aggregate_analysis_results thất bại!")
    print(f"  [OK] aggregator: tổng hợp {agg_res.get('total_issues_count')} lỗi")

    # 3.8 Scoring
    criteria = scoring.build_criteria_scores(
        radon_data=radon_res,
        bandit_data=bandit_res,
        pylint_data=pylint_res,
        health_data=health_res,
        audit_data=audit_res,
    )
    score_res = scoring.calculate_final_score(criteria)
    _check(0.0 <= score_res["total_score"] <= 100.0, "Điểm tổng kết ngoài phạm vi 0-100!")
    _check(score_res["grade"] in ("A", "B", "C", "D", "F"), "Xếp loại không hợp lệ!")
    print(f"  [OK] scoring: Điểm={score_res['total_score']}, Xếp loại={score_res['grade']}")

    # 3.6 Source Loader
    # Test safe zip
    tmp_dir = ROOT_DIR / "backend" / "workspace" / "test_zip_tmp"
    tmp_dir.mkdir(parents=True, exist_ok=True)
    test_zip = tmp_dir / "test.zip"
    with zipfile.ZipFile(test_zip, "w") as zf:
        zf.writestr("test_file.py", "print('hello zip')\n")

    prep_zip = source_loader.prepare_source("zip", str(test_zip), tmp_dir)
    _check(prep_zip.get("status") == "ok", "prepare_source zip thất bại!")
    print("  [OK] source_loader: Chuẩn bị mã nguồn ZIP an toàn thành công")
    source_loader.cleanup_workspace(prep_zip["working_dir"])
    source_loader.cleanup_workspace(tmp_dir)


def test_section_services() -> None:
    """4. Kiểm thử tầng Analysis Service Orchestrator."""
    print("\n" + "=" * 60)
    print("[PHASE 4] KIỂM THỬ DỊCH VỤ ĐIỀU PHỐI (ANALYSIS_SERVICE)")
    print("=" * 60)

    proj_id = project_repo.create_project(
        name="Service Test Project",
        path=str(SAMPLE_BAD_PROJECT),
    )
    try:
        res = run_project_analysis(proj_id)
        _check(res.get("status") == "ok", f"run_project_analysis lỗi: {res.get('message')}")
        _check(res.get("session_id") is not None, "Không nhận được session_id!")
        print(f"  [OK] run_project_analysis: Session ID={res['session_id']}, "
              f"Score={res['total_score']}, Grade={res['grade']}, Issues={res['total_issues']}")

        # Kiểm tra CSDL
        sess = session_repo.get_session_by_id(res["session_id"])
        _check(sess is not None, "Không tìm thấy phiên quét trong MySQL!")
        issues = issue_repo.get_issues_by_session(res["session_id"])
        _check(len(issues) == res["total_issues"], "Số lượng lỗi trong CSDL không khớp!")
        print(f"  [OK] Đã xác minh {len(issues)} bản ghi lỗi được ghi nhận trong CSDL!")
    finally:
        project_repo.delete_project(proj_id)


def test_section_handlers() -> None:
    """5. Kiểm thử toàn diện tầng Handlers."""
    print("\n" + "=" * 60)
    print("[PHASE 5] KIỂM THỬ TẦNG HANDLERS")
    print("=" * 60)

    # 5.1 Project Handler
    c_proj = handle_create_project({"name": "H Project", "source_path": str(SAMPLE_BAD_PROJECT)})
    _check(c_proj.get("status") == "ok", "handle_create_project thất bại!")
    pid = c_proj["data"]["project_id"]

    g_proj = handle_get_project({"project_id": pid})
    _check(g_proj.get("status") == "ok", "handle_get_project thất bại!")

    l_proj = handle_list_projects({})
    _check(
        l_proj.get("status") == "ok" and len(l_proj["data"]) >= 1,
        "handle_list_projects thất bại!",
    )

    u_proj = handle_update_project({"project_id": pid, "description": "New desc"})
    _check(u_proj.get("status") == "ok", "handle_update_project thất bại!")
    print("  [OK] project_handler (create, get, list, update) thành công")

    # 5.2 Analysis Handler
    an_res = handle_run_analysis({"project_id": pid})
    _check(an_res.get("status") == "ok", f"handle_run_analysis thất bại: {an_res.get('message')}")
    sid = an_res["data"]["session_id"]
    print(f"  [OK] analysis_handler (handle_run_analysis) thành công -> Session ID: {sid}")

    # 5.3 History Handler
    hist = handle_list_history({"project_id": pid})
    _check(hist.get("status") == "ok" and len(hist["data"]) >= 1, "handle_list_history thất bại!")
    print("  [OK] history_handler (handle_list_history) thành công")

    # 5.4 Issue Handler
    c_iss = handle_create_issue({
        "session_id": sid,
        "file": "test.py",
        "message": "Manual issue test",
        "severity": "medium",
    })
    _check(c_iss.get("status") == "ok", "handle_create_issue thất bại!")
    iid = c_iss["data"]["issue_id"]

    u_iss = handle_update_issue_status({"issue_id": iid, "status": "false_positive"})
    _check(u_iss.get("status") == "ok", "handle_update_issue_status thất bại!")

    l_iss = handle_list_issues({"session_id": sid})
    _check(l_iss.get("status") == "ok", "handle_list_issues thất bại!")

    d_iss = handle_delete_issue({"issue_id": iid})
    _check(d_iss.get("status") == "ok", "handle_delete_issue thất bại!")
    print("  [OK] issue_handler (create, update_status, list, delete) thành công")

    # 5.5 Config Handler
    g_cfg = handle_get_config({})
    _check(g_cfg.get("status") == "ok", "handle_get_config thất bại!")
    u_cfg = handle_update_config({"metric_key": "pylint", "weight": 30.0})
    _check(u_cfg.get("status") == "ok", "handle_update_config thất bại!")
    print("  [OK] config_handler (get, update) thành công")

    # Dọn dẹp
    handle_delete_history({"session_id": sid})
    handle_delete_project({"project_id": pid})
    print("  [OK] Đã dọn dẹp các bản ghi kiểm thử của Handlers")


def test_section_router_and_network() -> None:
    """6. & 7. Kiểm thử tầng Router và Live Socket Server."""
    print("\n" + "=" * 60)
    print("[PHASE 6 & 7] KIỂM THỬ ROUTER VÀ LIVE SOCKET SERVER")
    print("=" * 60)

    # 6.1 Router direct dispatch
    r1 = router.dispatch_request({"action": "config.get", "data": {}})
    _check(r1.get("status") == "ok", "router dispatch config.get thất bại!")
    r2 = router.dispatch_request({"action": "unknown.action"})
    _check(r2.get("status") == "error", "router không bắt được unknown action!")
    r3 = router.dispatch_request("invalid")
    _check(r3.get("status") == "error", "router không bắt được invalid type!")
    print("  [OK] router.dispatch_request kiểm thử 3 kịch bản thành công")

    # 7.1 Live Socket Server (sử dụng cổng tự do ngẫu nhiên tránh xung đột cổng)
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe_sock:
        probe_sock.bind(("127.0.0.1", 0))
        test_port = probe_sock.getsockname()[1]

    server = SocketServer(host="127.0.0.1", port=test_port)
    server_th = threading.Thread(target=server.start, daemon=True)
    server_th.start()
    time.sleep(0.5)

    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        client.connect(("127.0.0.1", test_port))
        # Gửi request có tiếng Việt
        req = {
            "action": "project.list",
            "data": {},
        }
        send_ok = protocol.send_json(client, req)
        _check(send_ok, "Client gửi dữ liệu thất bại!")

        resp = protocol.recv_json(client)
        _check(resp is not None and resp.get("status") == "ok", "Server phản hồi không hợp lệ!")
        print(f"  [OK] Live Socket Server nhận request TCP -> {resp.get('status')}")
    finally:
        client.close()
        server.stop()
        server_th.join(timeout=2.0)
        print("  [OK] Live Socket Server đã đóng và giải phóng cổng an toàn")


def run_full_suite() -> None:
    """Khởi chạy toàn bộ quy trình kiểm thử Backend."""
    start_time = time.time()
    print("\n" + "#" * 70)
    print("#  BẮT ĐẦU CHẠY TOÀN BỘ BÀI TEST TỔNG HỢP CHO HỆ THỐNG BACKEND  #")
    print("#" * 70)

    test_section_database()
    test_section_repositories()
    test_section_analyzer()
    test_section_services()
    test_section_handlers()
    test_section_router_and_network()

    elapsed = round(time.time() - start_time, 2)
    print("\n" + "=" * 70)
    print(f"[HOÀN TẤT] TOÀN BỘ 7 GIAI ĐOẠN KIỂM THỬ BACKEND ĐỀU ĐẠT CHUẨN 100%! ({elapsed}s)")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    run_full_suite()
