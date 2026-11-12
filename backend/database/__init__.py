"""Package quản lý cơ sở dữ liệu và kết nối hỗ trợ MySQL và SQLite."""

from .connection import get_connection, test_connection, get_pool

__all__ = ["get_connection", "test_connection", "get_pool"]
