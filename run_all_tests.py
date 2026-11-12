"""
Bộ chạy kiểm thử tự động toàn diện (Test Runner) cho Hệ thống Đánh giá Chất lượng Mã nguồn.

Tự động thực thi toàn bộ quy trình kiểm thử và chất lượng mã nguồn:
1. Backend Unit & Integration Tests (pytest backend/tests/)
2. Frontend UI & Component Tests (pytest frontend/tests/)
3. Desktop Client End-to-End Test (frontend/tests/test_desktop_e2e.py)
4. Code Quality & PEP8 Static Analysis (pylint backend/ frontend/)
5. Security Vulnerability Scan (bandit -r backend/ frontend/ -c .bandit)
"""

from __future__ import annotations

import subprocess  # nosec B404
import sys
import time
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent


def _run_step(title: str, cmd: list[str]) -> tuple[bool, str, float]:
    """Thực thi một bước kiểm thử và ghi nhận thời gian, kết quả."""
    print(f"\n[*] Đang thực hiện: {title} ...")
    start_time = time.time()
    try:
        proc = subprocess.run(  # nosec B603
            cmd,
            cwd=str(ROOT_DIR),
            capture_output=True,
            text=True,
            check=False,
        )
        elapsed = time.time() - start_time
        success = proc.returncode == 0
        output = proc.stdout if success else (proc.stdout + "\n" + proc.stderr)
        return success, output.strip(), elapsed
    except (OSError, RuntimeError) as exc:
        elapsed = time.time() - start_time
        return False, str(exc), elapsed


def main() -> int:
    """Hàm điều phối kiểm thử chính."""
    print("=" * 70)
    print("   HỆ THỐNG PHÂN TÍCH VÀ ĐÁNH GIÁ CHẤT LƯỢNG MÃ NGUỒN MỞ")
    print("      QUY TRÌNH KIỂM THỬ TOÀN DIỆN & ĐÁNH GIÁ CHẤT LƯỢNG")
    print("=" * 70)

    steps = [
        (
            "1. Kiểm thử Backend (8 bài test)",
            [sys.executable, "-m", "pytest", "backend/tests/", "-q"],
        ),
        (
            "2. Kiểm thử Frontend UI (43 bài test)",
            [sys.executable, "-m", "pytest", "frontend/tests/", "-q"],
        ),
        (
            "3. Kiểm thử Desktop E2E Workflow",
            [sys.executable, "frontend/tests/test_desktop_e2e.py"],
        ),
        (
            "4. Đánh giá chất lượng mã nguồn (Pylint)",
            [sys.executable, "-m", "pylint", "backend/", "frontend/"],
        ),
        (
            "5. Quét lỗ hổng an toàn bảo mật (Bandit)",
            [sys.executable, "-m", "bandit", "-r", "backend/", "frontend/", "-c", ".bandit"],
        ),
    ]

    results: list[tuple[str, bool, str, float]] = []
    total_start = time.time()
    all_passed = True

    for name, cmd in steps:
        ok, out, duration = _run_step(name, cmd)
        results.append((name, ok, out, duration))
        status_label = "[PASSED]" if ok else "[FAILED]"
        print(f"    -> {status_label} hoàn thành trong {duration:.2f}s")
        if not ok:
            all_passed = False
            print("\n" + "-" * 50)
            print(f"Chi tiết lỗi bước '{name}':")
            print(out)
            print("-" * 50)

    total_time = time.time() - total_start

    print("\n" + "=" * 70)
    print("               BẢNG TỔNG KẾT KẾT QUẢ KIỂM THỬ")
    print("=" * 70)
    for name, ok, _, duration in results:
        status_mark = "✔ ĐẠT (100%)" if ok else "✘ THẤT BẠI"
        print(f"  {name:<45} | {status_mark:<12} | {duration:6.2f}s")
    print("-" * 70)
    print(f"  Tổng thời gian thực thi: {total_time:.2f}s")

    if all_passed:
        print("\n[SUCCESS] Tất cả 5 hạng mục kiểm định chất lượng đều đạt 100%!")
        print("          Dự án sẵn sàng vận hành và triển khai.\n")
        return 0

    print("\n[FAILED] Có bước kiểm thử không đạt yêu cầu. Vui lòng rà soát lại lỗi.\n")
    return 1


if __name__ == "__main__":
    sys.exit(main())
