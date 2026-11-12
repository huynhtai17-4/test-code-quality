"""Adapter layer for SQLite database compatibility.

Provides SQLiteConnectionWrapper and SQLiteCursorWrapper to emulate MySQL-like
connection semantics, including dictionary cursor, lastrowid, parameter
normalization (%s -> ?), and SQL dialect compatibility.
"""

import re
import sqlite3
from pathlib import Path
from typing import Any, Optional


def normalize_sql(sql: str) -> str:
    """
    Chuẩn hóa câu lệnh SQL từ cú pháp MySQL sang SQLite.

    - Thay thế placeholder `%s` bằng `?`.
    - Thay thế hàm MySQL `NOW()` bằng `CURRENT_TIMESTAMP`.
    - Thay thế `ORDER BY FIELD(severity, ...)` bằng chuẩn ANSI `CASE ... END`.
    - Thay thế `INSERT IGNORE` bằng `INSERT OR IGNORE`.
    """
    if not sql:
        return sql

    # 1. Chuyển đổi %s sang ? (không thay thế %% nếu có)
    norm = re.sub(r"(?<!%)\%s", "?", sql)

    # 2. Chuyển đổi hàm thời gian NOW()
    norm = re.sub(r"\bNOW\(\)", "CURRENT_TIMESTAMP", norm, flags=re.IGNORECASE)

    # 3. Chuyển đổi hàm ORDER BY FIELD(...) đặc thù của MySQL
    field_pattern = (
        r"ORDER\s+BY\s+FIELD\s*\(\s*severity\s*,\s*"
        r"'critical'\s*,\s*'high'\s*,\s*'medium'\s*,\s*'low'\s*,\s*'info'\s*\)"
    )
    ansi_order = (
        "ORDER BY CASE severity "
        "WHEN 'critical' THEN 1 "
        "WHEN 'high' THEN 2 "
        "WHEN 'medium' THEN 3 "
        "WHEN 'low' THEN 4 "
        "WHEN 'info' THEN 5 "
        "ELSE 6 END"
    )
    norm = re.sub(field_pattern, ansi_order, norm, flags=re.IGNORECASE)

    # 4. Chuyển đổi INSERT IGNORE sang INSERT OR IGNORE
    norm = re.sub(r"\bINSERT\s+IGNORE\b", "INSERT OR IGNORE", norm, flags=re.IGNORECASE)

    return norm


class SQLiteCursorWrapper:
    """Lớp bao bọc sqlite3.Cursor để tương thích với mysql.connector cursor."""

    def __init__(self, raw_cursor: sqlite3.Cursor, dictionary: bool = False) -> None:
        self._cursor = raw_cursor
        self._dictionary = dictionary

    @property
    def description(self) -> Any:
        """Thuộc tính mô tả các cột của kết quả truy vấn."""
        return self._cursor.description

    @property
    def lastrowid(self) -> Optional[int]:
        """ID của bản ghi vừa chèn."""
        return self._cursor.lastrowid

    @property
    def rowcount(self) -> int:
        """Số dòng bị ảnh hưởng bởi câu lệnh ghi gần nhất."""
        return self._cursor.rowcount

    def execute(self, sql: str, params: Any = ()) -> "SQLiteCursorWrapper":
        """Thực thi câu lệnh SQL có tham số hóa và tự động chuẩn hóa cú pháp."""
        norm_sql = normalize_sql(sql)
        clean_params = tuple(params) if isinstance(params, (list, tuple)) else params
        self._cursor.execute(norm_sql, clean_params)
        return self

    def executemany(self, sql: str, rows: list[Any]) -> "SQLiteCursorWrapper":
        """Thực thi câu lệnh SQL ghi hàng loạt có chuẩn hóa cú pháp."""
        norm_sql = normalize_sql(sql)
        self._cursor.executemany(norm_sql, rows)
        return self

    def fetchone(self) -> Optional[Any]:
        """Lấy một bản ghi từ tập kết quả."""
        row = self._cursor.fetchone()
        if row is None:
            return None
        if self._dictionary and self._cursor.description:
            col_names = [col[0] for col in self._cursor.description]
            return {col_names[idx]: row[idx] for idx in range(len(col_names))}
        return row

    def fetchall(self) -> list[Any]:
        """Lấy toàn bộ bản ghi từ tập kết quả."""
        rows = self._cursor.fetchall()
        if not rows:
            return []
        if self._dictionary and self._cursor.description:
            col_names = [col[0] for col in self._cursor.description]
            return [
                {col_names[idx]: row[idx] for idx in range(len(col_names))}
                for row in rows
            ]
        return rows

    def fetchmany(self, size: Optional[int] = None) -> list[Any]:
        """Lấy một số lượng bản ghi nhất định từ tập kết quả."""
        rows = self._cursor.fetchmany(size) if size is not None else self._cursor.fetchmany()
        if not rows:
            return []
        if self._dictionary and self._cursor.description:
            col_names = [col[0] for col in self._cursor.description]
            return [
                {col_names[idx]: row[idx] for idx in range(len(col_names))}
                for row in rows
            ]
        return rows

    def close(self) -> None:
        """Đóng con trỏ truy vấn."""
        try:
            self._cursor.close()
        except Exception:  # pylint: disable=broad-exception-caught # nosec B110
            pass

    def __iter__(self) -> Any:
        """Hỗ trợ duyệt tuần tự qua cursor."""
        while True:
            row = self.fetchone()
            if row is None:
                break
            yield row


class SQLiteConnectionWrapper:
    """Lớp bao bọc sqlite3.Connection để tương thích giao diện kết nối MySQL."""

    def __init__(self, raw_conn: sqlite3.Connection) -> None:
        self._conn = raw_conn
        self._closed = False

    def cursor(self, dictionary: bool = False) -> SQLiteCursorWrapper:
        """Tạo con trỏ truy vấn mới hỗ trợ chế độ dictionary."""
        return SQLiteCursorWrapper(self._conn.cursor(), dictionary=dictionary)

    def commit(self) -> None:
        """Cam kết transaction hiện tại."""
        self._conn.commit()

    def rollback(self) -> None:
        """Hoàn tác transaction hiện tại."""
        self._conn.rollback()

    def close(self) -> None:
        """Đóng kết nối SQLite."""
        if not self._closed:
            self._closed = True
            try:
                self._conn.close()
            except Exception:  # pylint: disable=broad-exception-caught # nosec B110
                pass

    def is_connected(self) -> bool:
        """Kiểm tra kết nối đang mở và sẵn sàng hoạt động."""
        if self._closed:
            return False
        try:
            cur = self._conn.cursor()
            cur.execute("SELECT 1;")
            cur.fetchone()
            cur.close()
            return True
        except Exception:  # pylint: disable=broad-exception-caught
            return False

    def execute(self, sql: str, params: Any = ()) -> SQLiteCursorWrapper:
        """Phương thức tiện ích thực thi trực tiếp trên connection."""
        cur = self.cursor()
        cur.execute(sql, params)
        return cur


def init_sqlite_db(
    db_path: Path | str,
    schema_path: Optional[Path | str] = None,
) -> None:
    """
    Khởi tạo cơ sở dữ liệu SQLite và nạp bảng DDL từ schema nếu chưa tồn tại.
    """
    target_path = Path(db_path).resolve()
    target_path.parent.mkdir(parents=True, exist_ok=True)

    default_schema = (
        Path(__file__).resolve().parent / "schema_sqlite.sql"
        if schema_path is None
        else Path(schema_path)
    )

    conn = sqlite3.connect(str(target_path), timeout=30.0)
    try:
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.execute("PRAGMA journal_mode = WAL;")

        # Kiểm tra xem bảng projects đã tồn tại chưa
        cur = conn.cursor()
        cur.execute(
            "SELECT count(*) FROM sqlite_master WHERE type='table' AND name='projects';"
        )
        table_exists = cur.fetchone()[0] > 0
        cur.close()

        if not table_exists and default_schema.exists():
            schema_sql = default_schema.read_text(encoding="utf-8")
            conn.executescript(schema_sql)
            conn.commit()
    finally:
        conn.close()
