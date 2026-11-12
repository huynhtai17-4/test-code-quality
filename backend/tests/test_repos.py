"""Kiểm thử nhanh tầng Repositories (project_repo và config_repo)."""

import sys
from pathlib import Path

# Đảm bảo import được từ thư mục gốc dự án khi chạy trực tiếp file này
ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from backend.database.repositories import config_repo, project_repo  # pylint: disable=wrong-import-position


def _check(condition: bool, message: str) -> None:
    """Hàm xác thực kiểm thử an toàn, không kích hoạt Bandit B101."""
    if not condition:
        raise AssertionError(f"KIỂM THỬ THẤT BẠI: {message}")


def test_repositories_quick() -> None:
    """Thực hiện kịch bản kiểm thử CRUD dự án và đọc cấu hình trọng số mặc định."""
    project_id = None
    try:
        # 1. Thêm 1 dự án mẫu "Test Project"
        project_id = project_repo.create_project(
            name="Test Project",
            path="d:/tmp/test_project",
            description="Dự án mẫu phục vụ kiểm thử tầng Repositories",
        )
        _check(project_id > 0, "Không tạo được dự án mẫu!")
        print(f"[+] Đã tạo dự án mẫu 'Test Project' với ID = {project_id}")

        # 2. Lấy danh sách dự án và kiểm tra dự án vừa thêm có tồn tại không
        projects = project_repo.get_all_projects()
        matched = [p for p in projects if p["id"] == project_id and p["name"] == "Test Project"]
        _check(len(matched) == 1, "Không tìm thấy 'Test Project' trong get_all_projects()!")
        print(f"[+] Xác nhận 'Test Project' tồn tại trong danh sách ({len(projects)} dự án).")

        # 3. Đọc 5 trọng số mặc định trong bảng scoring_config
        configs = config_repo.get_all_configs()
        _check(len(configs) >= 5, f"Kỳ vọng ít nhất 5 trọng số, nhận được {len(configs)}")
        print(f"[+] Đọc được {len(configs)} trọng số chấm điểm từ scoring_config:")
        for cfg in configs:
            print(
                f"    - {cfg['metric_key']} ({cfg['metric_name']}): "
                f"weight={cfg['weight']}%, active={bool(cfg['is_active'])}"
            )
    finally:
        # 4. Xóa dự án mẫu vừa tạo để dọn dẹp CSDL
        if project_id is not None:
            deleted = project_repo.delete_project(project_id)
            _check(deleted is True, f"Không thể xóa dự án mẫu ID = {project_id}")
            print(f"[+] Đã xóa dự án mẫu ID = {project_id} để dọn dẹp CSDL.")


if __name__ == "__main__":
    test_repositories_quick()
    print("[OK] Hoàn thành kiểm thử nhanh tầng Repositories!")
