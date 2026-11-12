"""Handler xử lý yêu cầu chạy phân tích mã nguồn qua analysis_service."""

import sys
from pathlib import Path
from typing import Any

# Đảm bảo đường dẫn import hoạt động khi chạy trực tiếp file này
ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# pylint: disable=wrong-import-position
from backend.handlers._base import error_response, success_response
from backend.services import run_project_analysis


def handle_run_analysis(data: dict[str, Any]) -> dict[str, Any]:
    """
    Xử lý yêu cầu chạy phân tích mã nguồn dự án qua analysis_service.

    Args:
        data: Dữ liệu yêu cầu chứa 'project_id' (bắt buộc) và 'workspace_root' (tùy chọn).

    Returns:
        dict: Phản hồi chuẩn {"status": "ok", "data": ...} hoặc {"status": "error", "message": ...}.
    """
    try:
        raw_id = data.get("project_id")
        if raw_id is None:
            return error_response("project_id không hợp lệ hoặc bị thiếu")

        try:
            project_id = int(raw_id)
            if project_id <= 0:
                return error_response("project_id không hợp lệ hoặc bị thiếu")
        except (ValueError, TypeError):
            return error_response("project_id không hợp lệ hoặc bị thiếu")

        workspace_root = data.get("workspace_root")
        result = run_project_analysis(project_id=project_id, workspace_root=workspace_root)

        if result.get("status") == "ok":
            return success_response(result)

        error_msg = result.get("message") or "Lỗi phân tích mã nguồn"
        return error_response(error_msg)

    except Exception as exc:  # pylint: disable=broad-exception-caught
        return error_response(f"Lỗi không mong muốn khi phân tích: {exc}")


def _test_analysis_handler() -> None:
    """Kịch bản kiểm thử độc lập cho analysis_handler."""
    import pprint  # pylint: disable=import-outside-toplevel
    from backend.database.repositories import project_repo  # pylint: disable=import-outside-toplevel

    sample_path = ROOT_DIR / "backend" / "samples" / "bad_project"
    print(f"[*] Thư mục mẫu: {sample_path}")
    if not sample_path.exists():
        print("[-] Không tìm thấy thư mục mẫu!")
        return

    # 1. Tạo dự án mẫu
    proj_id = project_repo.create_project(
        name="Analysis Handler Test Project",
        path=str(sample_path),
        description="Dự án kiểm thử analysis_handler",
    )
    print(f"[+] Đã tạo dự án tạm: Project ID = {proj_id}")

    try:
        # 2. Gọi handle_run_analysis
        print("[*] Đang thực thi handle_run_analysis()...")
        response = handle_run_analysis({"project_id": proj_id})
        print("\n========== KẾT QUẢ TỪ ANALYSIS_HANDLER ==========")
        pprint.pprint(response)

        if response.get("status") == "ok":
            print("[PASSED] Phân tích thành công thông qua handler!")
        else:
            print(f"[FAILED] Handler báo lỗi: {response.get('message')}")

    finally:
        # 3. Dọn dẹp
        print(f"\n[*] Dọn dẹp dự án kiểm thử ID = {proj_id}...")
        project_repo.delete_project(proj_id)
        print("[+] Đã dọn dẹp hoàn tất.")


if __name__ == "__main__":
    _test_analysis_handler()
