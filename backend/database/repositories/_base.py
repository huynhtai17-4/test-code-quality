"""Shared database query helpers using parameterized SQL and get_connection()."""

from typing import Any, Optional

from backend.database.connection import get_connection


def fetch_all(sql: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
    """Thực thi câu lệnh SELECT trả về danh sách các bản ghi dạng dict."""
    with get_connection() as conn:
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute(sql, params)
            return list(cursor.fetchall())
        finally:
            cursor.close()


def fetch_one(sql: str, params: tuple[Any, ...] = ()) -> Optional[dict[str, Any]]:
    """Thực thi câu lệnh SELECT trả về một bản ghi dạng dict hoặc None."""
    with get_connection() as conn:
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute(sql, params)
            return cursor.fetchone()
        finally:
            cursor.close()


def execute_insert(sql: str, params: tuple[Any, ...] = ()) -> int:
    """Thực thi câu lệnh INSERT có tham số hóa và trả về lastrowid."""
    with get_connection() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute(sql, params)
            conn.commit()
            return int(cursor.lastrowid)
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()


def execute_write(sql: str, params: tuple[Any, ...] = ()) -> int:
    """Thực thi câu lệnh UPDATE/DELETE có tham số hóa và trả về số dòng ảnh hưởng."""
    with get_connection() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute(sql, params)
            conn.commit()
            return int(cursor.rowcount)
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()


def execute_many(sql: str, rows: list[tuple[Any, ...]]) -> int:
    """Thực thi câu lệnh ghi hàng loạt trong một transaction và trả về rowcount."""
    if not rows:
        return 0

    with get_connection() as conn:
        cursor = conn.cursor()
        try:
            cursor.executemany(sql, rows)
            conn.commit()
            return int(cursor.rowcount)
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()
