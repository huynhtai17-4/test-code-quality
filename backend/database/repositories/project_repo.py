"""Repository xử lý các thao tác CRUD cho bảng projects."""

from typing import Any, Optional

from ._base import execute_insert, execute_write, fetch_all, fetch_one

_ALLOWED_UPDATE_FIELDS = frozenset({"name", "path", "description", "language"})


def create_project(
    name: str,
    path: str,
    description: Optional[str] = None,
    language: str = "python",
) -> int:
    """Thêm dự án mới vào bảng projects và trả về ID vừa tạo."""
    sql = """
        INSERT INTO projects (name, path, description, language)
        VALUES (%s, %s, %s, %s)
    """
    return execute_insert(sql, (name, path, description, language))


def get_all_projects() -> list[dict[str, Any]]:
    """Lấy danh sách toàn bộ dự án, sắp xếp theo thời gian cập nhật mới nhất."""
    sql = """
        SELECT id, name, path, description, language, created_at, updated_at
        FROM projects
        ORDER BY updated_at DESC, id DESC
    """
    return fetch_all(sql)


def get_project_by_id(project_id: int) -> Optional[dict[str, Any]]:
    """Lấy thông tin chi tiết của một dự án theo ID."""
    sql = """
        SELECT id, name, path, description, language, created_at, updated_at
        FROM projects
        WHERE id = %s
    """
    return fetch_one(sql, (project_id,))


def update_project(project_id: int, **fields: Any) -> bool:
    """
    Cập nhật thông tin dự án theo ID.

    Chỉ chấp nhận các trường hợp lệ: name, path, description, language.
    Trả về True nếu có bản ghi được cập nhật.
    """
    if not fields:
        return False

    invalid_fields = set(fields.keys()) - _ALLOWED_UPDATE_FIELDS
    if invalid_fields:
        raise ValueError(f"Trường cập nhật không hợp lệ: {', '.join(sorted(invalid_fields))}")

    sql = """
        UPDATE projects
        SET name = CASE WHEN %s THEN %s ELSE name END,
            path = CASE WHEN %s THEN %s ELSE path END,
            description = CASE WHEN %s THEN %s ELSE description END,
            language = CASE WHEN %s THEN %s ELSE language END
        WHERE id = %s
    """
    params = (
        "name" in fields,
        fields.get("name"),
        "path" in fields,
        fields.get("path"),
        "description" in fields,
        fields.get("description"),
        "language" in fields,
        fields.get("language"),
        project_id,
    )
    return execute_write(sql, params) > 0


def delete_project(project_id: int) -> bool:
    """Xóa dự án theo ID (tự động xóa kèm các phiên quét và lỗi liên quan)."""
    return execute_write("DELETE FROM projects WHERE id = %s", (project_id,)) > 0
