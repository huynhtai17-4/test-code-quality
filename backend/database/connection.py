"""Module quản lý kết nối cơ sở dữ liệu hỗ trợ Dual-DB (MySQL và SQLite).

Cung cấp context manager get_connection() và hàm test_connection() tự động
nhận diện cấu hình CSDL từ backend.config hoặc tự động chuyển hướng an toàn.
"""

import logging
import sqlite3
import sys
import threading
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Generator, Optional

ROOT_DIR = Path(__file__).resolve().parents[2]
BACKEND_DIR = Path(__file__).resolve().parents[1]
for path in (ROOT_DIR, BACKEND_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

# pylint: disable=wrong-import-position,ungrouped-imports
try:
    from backend.config import DB_CONFIG, DB_TYPE, SQLITE_PATH
except ImportError:
    from config import DB_CONFIG, DB_TYPE, SQLITE_PATH

from backend.database.sqlite_adapter import (
    SQLiteConnectionWrapper,
    init_sqlite_db,
)

try:
    import mysql.connector
    from mysql.connector import errorcode
    from mysql.connector.pooling import MySQLConnectionPool
except ImportError:
    mysql = None  # type: ignore # pylint: disable=invalid-name
    errorcode = None  # type: ignore
    MySQLConnectionPool = None  # type: ignore

logger = logging.getLogger(__name__)

POOL_SIZE: int = 5
POOL_NAME: str = "code_quality_pool"

_POOL_LOCK = threading.Lock()
_POOL_STATE: dict[str, Any] = {"pool": None}
_ACTIVE_DB_TYPE: Optional[str] = DB_TYPE if DB_TYPE in ("sqlite", "mysql") else None
_SQLITE_INITIALIZED = False


def set_active_db_type(db_type: str) -> None:
    """Thiết lập loại cơ sở dữ liệu chủ động ('sqlite' hoặc 'mysql')."""
    global _ACTIVE_DB_TYPE  # pylint: disable=global-statement
    with _POOL_LOCK:
        _ACTIVE_DB_TYPE = db_type.lower()


def get_active_db_type() -> str:
    """Xác định loại cơ sở dữ liệu hiện tại ('sqlite' hoặc 'mysql')."""
    global _ACTIVE_DB_TYPE  # pylint: disable=global-statement
    if _ACTIVE_DB_TYPE in ("sqlite", "mysql"):
        return _ACTIVE_DB_TYPE

    # Tự động phát hiện: Thử kết nối MySQL trước
    if mysql is not None and DB_CONFIG.get("database"):
        try:
            conn = mysql.connector.connect(**DB_CONFIG)
            if conn.is_connected():
                conn.close()
                _ACTIVE_DB_TYPE = "mysql"
                return "mysql"
        except (mysql.connector.Error, RuntimeError, OSError) as exc:
            logger.debug("MySQL auto-detection probe failed: %s", exc)

    # Nếu MySQL không khả dụng hoặc không cấu hình, chuyển sang SQLite
    _ACTIVE_DB_TYPE = "sqlite"
    return "sqlite"


def _ensure_sqlite_ready() -> Path:
    """Đảm bảo cơ sở dữ liệu SQLite đã được tạo bảng và nạp cấu hình mặc định."""
    global _SQLITE_INITIALIZED  # pylint: disable=global-statement
    db_path = Path(SQLITE_PATH).resolve()
    if not _SQLITE_INITIALIZED:
        init_sqlite_db(db_path)
        _SQLITE_INITIALIZED = True
    return db_path


def get_pool() -> Any:
    """
    Khởi tạo hoặc trả về MySQLConnectionPool hiện có cho MySQL.

    Raises:
        RuntimeError: Khi CSDL hiện tại là SQLite hoặc MySQL chưa cài đặt.
    """
    if mysql is None or MySQLConnectionPool is None:
        raise RuntimeError("mysql-connector-python chưa được cài đặt!")

    pool = _POOL_STATE["pool"]
    if pool is None:
        with _POOL_LOCK:
            pool = _POOL_STATE["pool"]
            if pool is None:
                pool = MySQLConnectionPool(
                    pool_name=POOL_NAME,
                    pool_size=POOL_SIZE,
                    pool_reset_session=True,
                    **DB_CONFIG,
                )
                _POOL_STATE["pool"] = pool
    return pool


@contextmanager
def get_connection() -> Generator[Any, None, None]:
    """
    Context manager cung cấp kết nối CSDL an toàn theo luồng (MySQL hoặc SQLite).
    """
    db_type = get_active_db_type()

    if db_type == "sqlite":
        db_path = _ensure_sqlite_ready()
        raw_conn = sqlite3.connect(str(db_path), timeout=30.0, check_same_thread=False)
        raw_conn.execute("PRAGMA foreign_keys = ON;")
        conn_wrapper = SQLiteConnectionWrapper(raw_conn)
        try:
            yield conn_wrapper
        finally:
            conn_wrapper.close()
    else:
        conn = None
        try:
            pool = get_pool()
            conn = pool.get_connection()
            yield conn
        finally:
            if conn is not None:
                conn.close()


def _print_mysql_error(err: Any, target_host: str, target_port: int,
                       target_user: str, target_db: str) -> None:
    """In thông báo chi tiết theo mã lỗi kết nối MySQL."""
    print("[-] Kết nối MySQL thất bại!")
    print("--------------------------------------------------")
    if errorcode and err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
        print(
            f"-> NGUYÊN NHÂN: Sai tên đăng nhập (user='{target_user}') "
            "hoặc mật khẩu (password)."
        )
    elif errorcode and err.errno == errorcode.ER_BAD_DB_ERROR:
        print(f"-> NGUYÊN NHÂN: Cơ sở dữ liệu '{target_db}' chưa tồn tại trên MySQL Server.")
        print(
            f"   Gợi ý: Hãy tạo database trước: "
            f"CREATE DATABASE `{target_db}` CHARACTER SET utf8mb4;"
        )
    elif errorcode and err.errno in (errorcode.CR_CONN_HOST_ERROR, errorcode.CR_CONNECTION_ERROR):
        print(
            f"-> NGUYÊN NHÂN: Không thể kết nối tới MySQL Server "
            f"tại {target_host}:{target_port}."
        )
        print(
            "   Gợi ý: Kiểm tra xem MySQL Server đã được bật chưa, "
            "hoặc kiểm tra lại PORT trong file .env."
        )
    else:
        print(f"-> NGUYÊN NHÂN: Lỗi kết nối MySQL: {err}")
    print("==================================================")


def _test_sqlite(db_path: Path) -> bool:
    """Kiểm tra hoạt động kết nối cơ sở dữ liệu SQLite."""
    print("    - Loại CSDL   : SQLite (File-based DB)")
    print(f"    - Đường dẫn   : {db_path}")
    print("==================================================")
    try:
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT 1 + 1 AS result;")
            res = cur.fetchone()
            cur.close()
            if res and res[0] == 2:
                print("[+] Kết nối SQLite thành công và sẵn sàng!")
                print("==================================================")
                return True
        return False
    except (sqlite3.Error, RuntimeError, OSError) as exc:
        print(f"[-] Kiểm tra kết nối SQLite thất bại: {exc}")
        print("==================================================")
        return False


def _test_mysql() -> bool:
    """Kiểm tra hoạt động kết nối cơ sở dữ liệu MySQL và Connection Pool."""
    target_host = DB_CONFIG.get("host", "127.0.0.1")
    target_port = DB_CONFIG.get("port", 3306)
    target_user = DB_CONFIG.get("user", "root")
    target_db = DB_CONFIG.get("database", "")

    print(f"    - Host    : {target_host}:{target_port}")
    print(f"    - User    : {target_user}")
    print(f"    - Database: {target_db}")
    print("==================================================")

    conn = None
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        if not conn.is_connected():
            print("[-] Không thể thiết lập kết nối tới MySQL Server.")
            print("==================================================")
            return False

        server_version = getattr(conn, "server_info", None) or "Unknown"
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT DATABASE(), VERSION();")
            current_db, full_version = cursor.fetchone()
        finally:
            cursor.close()

        print("[+] Kết nối MySQL thành công!")
        print(f"    - Phiên bản MySQL : {full_version} (Server info: {server_version})")
        print(f"    - CSDL hiện tại   : {current_db}")

        pool = get_pool()
        with get_connection() as pool_conn:
            if pool_conn.is_connected():
                print(
                    f"[+] Khởi tạo Connection Pool '{pool.pool_name}' thành công! "
                    f"(Kích thước: {POOL_SIZE})"
                )

        print("==================================================")
        return True

    except (mysql.connector.Error, RuntimeError, OSError) as exc:
        if mysql and isinstance(exc, mysql.connector.Error):
            _print_mysql_error(exc, target_host, target_port, target_user, target_db)
        else:
            print(f"[-] Đã xảy ra lỗi không xác định: {exc}")
            print("==================================================")
        return False
    finally:
        if conn is not None and hasattr(conn, "is_connected") and conn.is_connected():
            conn.close()


def test_connection() -> bool:
    """Kiểm tra kết nối và tính sẵn sàng của cơ sở dữ liệu hiện hành (MySQL/SQLite)."""
    db_type = get_active_db_type()

    print("==================================================")
    print(f"[*] Bắt đầu kiểm tra kết nối CSDL ({db_type.upper()}):")

    if db_type == "sqlite":
        db_path = _ensure_sqlite_ready()
        return _test_sqlite(db_path)

    return _test_mysql()


if __name__ == "__main__":
    test_connection()
