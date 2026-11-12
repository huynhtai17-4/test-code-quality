"""Kịch bản kiểm thử tự động cho Tầng nền tảng Frontend (Bước 1 - SKILLS.md)."""

import sys
from pathlib import Path

# Đảm bảo import được toàn bộ package
ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# pylint: disable=wrong-import-position,no-name-in-module
from PyQt6.QtWidgets import QApplication
import matplotlib as mpl
from frontend import config
from frontend.charts.style import (
    CHART_SEVERITY_COLORS,
    apply_chart_style,
)
from frontend.views import theme

# Khởi tạo QApplication headless nếu chưa có
_app = QApplication.instance() or QApplication(sys.argv)


def _assert(condition: bool, message: str) -> None:
    """Xác thực điều kiện kiểm thử an toàn cho Bandit."""
    if not condition:
        raise RuntimeError(f"KIỂM THỬ THẤT BẠI: {message}")


def test_config() -> None:
    """1. Kiểm tra file frontend/config.py."""
    print("[*] 1. Kiểm tra frontend/config.py...")
    _assert(config.SERVER_HOST == "127.0.0.1", "SERVER_HOST không đúng!")
    _assert(config.SERVER_PORT == 8000, "SERVER_PORT không đúng!")
    _assert(config.SOCKET_TIMEOUT == 15, "SOCKET_TIMEOUT không đúng!")
    print(
        f"    [OK] SERVER_HOST={config.SERVER_HOST}, "
        f"PORT={config.SERVER_PORT}, TIMEOUT={config.SOCKET_TIMEOUT}"
    )


def test_theme_constants() -> None:
    """2. Kiểm tra các hằng số màu và bảng ánh xạ trong frontend/views/theme.py."""
    print("[*] 2. Kiểm tra frontend/views/theme.py...")

    # Nền & chữ
    _assert(theme.WINDOW_BG == "#F3F5F8", "WINDOW_BG sai!")
    _assert(theme.SURFACE == "#FFFFFF", "SURFACE sai!")
    _assert(theme.SURFACE_ALT == "#F5F6F8", "SURFACE_ALT sai!")
    _assert(theme.HEADER_BG == "#FAFBFC", "HEADER_BG sai!")
    _assert(theme.ROW_HOVER == "#F6F8FB", "ROW_HOVER sai!")
    _assert(theme.BORDER == "#D3D8DF", "BORDER sai!")
    _assert(theme.BORDER_PANEL == "#DDE2E9", "BORDER_PANEL sai!")
    _assert(theme.BORDER_SOFT == "#EEF0F4", "BORDER_SOFT sai!")
    _assert(theme.TEXT_MAIN == "#1D232B", "TEXT_MAIN sai!")
    _assert(theme.TEXT_MUTED == "#5B6573", "TEXT_MUTED sai!")

    # Sidebar
    _assert(theme.SIDEBAR_BG == "#222B36", "SIDEBAR_BG sai!")
    _assert(theme.SIDEBAR_TEXT == "#B9C2CE", "SIDEBAR_TEXT sai!")
    _assert(theme.SIDEBAR_ACTIVE_BG == "#2F3A48", "SIDEBAR_ACTIVE_BG sai!")
    _assert(theme.SIDEBAR_ACTIVE_TEXT == "#FFFFFF", "SIDEBAR_ACTIVE_TEXT sai!")
    _assert(theme.SIDEBAR_WIDTH == 188, "SIDEBAR_WIDTH sai!")

    # Thao tác
    _assert(theme.ACCENT == "#1F5FA8", "ACCENT sai!")
    _assert(theme.ACCENT_HOVER == "#194F8C", "ACCENT_HOVER sai!")
    _assert(theme.ACCENT_SOFT == "#E8F0FA", "ACCENT_SOFT sai!")

    # Mức độ nghiêm trọng
    _assert(theme.SEV_CRITICAL == "#B42318", "SEV_CRITICAL sai!")
    _assert(theme.SEV_HIGH == "#D9622B", "SEV_HIGH sai!")
    _assert(theme.SEV_MEDIUM == "#C79A0A", "SEV_MEDIUM sai!")
    _assert(theme.SEV_LOW == "#5E7A94", "SEV_LOW sai!")

    # Xếp loại
    _assert(theme.GRADE_A == "#1E7A4C", "GRADE_A sai!")
    _assert(theme.GRADE_B == "#4C8A2E", "GRADE_B sai!")
    _assert(theme.GRADE_C == "#B38A00", "GRADE_C sai!")
    _assert(theme.GRADE_D == "#D9622B", "GRADE_D sai!")
    _assert(theme.GRADE_F == "#B42318", "GRADE_F sai!")

    # 5 tiêu chí chuẩn
    expected_criteria = {"complexity", "security", "pylint", "health", "dependency"}
    _assert(
        set(theme.TEN_TIEU_CHI.keys()) == expected_criteria,
        "TEN_TIEU_CHI không khớp 5 tiêu chí Backend!",
    )
    print(f"    [OK] Đã kiểm tra 5 tiêu chí cốt lõi: {list(theme.TEN_TIEU_CHI.keys())}")

    # Hàm nạp font code
    font_code = theme.lay_font_code(12)
    _assert(font_code is not None, "lay_font_code() trả về None!")
    print(f"    [OK] lay_font_code(12) nạp thành công phông: '{font_code.family()}'")


def test_stylesheet() -> None:
    """3. Kiểm tra file stylesheet frontend/views/style.qss."""
    print("[*] 3. Kiểm tra frontend/views/style.qss...")
    qss_content = theme.load_stylesheet()
    _assert(len(qss_content) > 100, "style.qss rỗng hoặc không nạp được!")

    # Kiểm tra các quy tắc quan trọng trong SKILLS.md
    _assert("QTableView" in qss_content, "Thiếu định kiểu QTableView trong style.qss!")
    _assert('role="primary"' in qss_content, "Thiếu role primary button!")
    _assert('role="danger"' in qss_content, "Thiếu role danger button!")
    _assert("#Sidebar" in qss_content, "Thiếu định kiểu #Sidebar!")
    _assert("border: 2px solid #1F5FA8;" in qss_content, "Thiếu viền focus 2px solid #1F5FA8!")
    _assert("height: 6px;" in qss_content, "Thanh tiến độ không đúng 6px mảnh!")
    print(
        f"    [OK] style.qss nạp thành công ({len(qss_content)} ký tự) "
        "và chứa đủ các token chuẩn"
    )


def test_chart_style() -> None:
    """4. Kiểm tra cấu hình Matplotlib trong frontend/charts/style.py."""
    print("[*] 4. Kiểm tra frontend/charts/style.py...")
    apply_chart_style()

    _assert(mpl.rcParams["figure.facecolor"] == "#FFFFFF", "figure.facecolor không phải #FFFFFF!")
    _assert(mpl.rcParams["axes.facecolor"] == "#FFFFFF", "axes.facecolor không phải #FFFFFF!")
    _assert(mpl.rcParams["axes.spines.top"] is False, "axes.spines.top chưa tắt!")
    _assert(mpl.rcParams["axes.spines.right"] is False, "axes.spines.right chưa tắt!")
    _assert(mpl.rcParams["axes.titlelocation"] == "left", "axes.titlelocation không phải left!")
    _assert(mpl.rcParams["grid.color"] == "#E4E7EC", "grid.color không phải #E4E7EC!")
    _assert(len(CHART_SEVERITY_COLORS) == 4, "CHART_SEVERITY_COLORS phải đủ 4 mức!")
    print("    [OK] apply_chart_style() cấu hình Matplotlib phẳng chuẩn xác 100%")


def run_all() -> None:
    """Chạy toàn bộ các bước kiểm tra nền tảng."""
    print("=" * 65)
    print("  KIỂM THỬ NỀN TẢNG FRONTEND BƯỚC 1 (SKILLS.MD)  ")
    print("=" * 65)

    test_config()
    test_theme_constants()
    test_stylesheet()
    test_chart_style()

    print("=" * 65)
    print("  [PASSED] TẤT CẢ 4 TỆP NỀN TẢNG ĐÃ ĐẠT CHUẨN KỸ THUẬT 100%!  ")
    print("=" * 65)


if __name__ == "__main__":
    run_all()
