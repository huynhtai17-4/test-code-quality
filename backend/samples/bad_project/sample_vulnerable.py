"""Tập tin mã nguồn mẫu chứa lỗi bảo mật để kiểm thử Bandit."""

import hashlib
import os
import subprocess

# B105: Hardcoded password
DATABASE_PASSWORD = "super_secret_password_123"


def execute_system_command(user_input: str) -> None:
    """B605 / B602: Thực thi lệnh hệ thống không an toàn."""
    os.system(f"ping {user_input}")
    subprocess.Popen(user_input, shell=True)  # nosec B602 for test


def calculate_insecure_hash(content: str) -> str:
    """B324: Sử dụng thuật toán băm yếu MD5."""
    return hashlib.md5(content.encode()).hexdigest()


def evaluate_expression(expr: str):
    """B307: Sử dụng hàm eval nguy hiểm."""
    return eval(expr)

