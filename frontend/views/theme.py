"""Hệ thống Token thiết kế và hằng số giao diện cho Desktop PyQt6."""

import datetime
from pathlib import Path
from typing import Any
from PyQt6.QtGui import QFont, QFontDatabase  # pylint: disable=no-name-in-module
from PyQt6.QtWidgets import QApplication  # pylint: disable=no-name-in-module

from frontend.charts.style import TEN_TIEU_CHI

# ── 1. Nền & Chữ ──────────────────────────────────────────────────
WINDOW_BG: str = "#F3F5F8"
SURFACE: str = "#FFFFFF"
SURFACE_ALT: str = "#F5F6F8"
HEADER_BG: str = "#FAFBFC"
ROW_HOVER: str = "#F6F8FB"
BORDER: str = "#D3D8DF"
BORDER_PANEL: str = "#DDE2E9"
BORDER_SOFT: str = "#EEF0F4"
TEXT_MAIN: str = "#1D232B"
TEXT_MUTED: str = "#5B6573"

# ── 2. Sidebar ─────────────────────────────────────────────────────
SIDEBAR_BG: str = "#222B36"
SIDEBAR_TEXT: str = "#B9C2CE"
SIDEBAR_ACTIVE_BG: str = "#2F3A48"
SIDEBAR_ACTIVE_TEXT: str = "#FFFFFF"
SIDEBAR_WIDTH: int = 188

# ── 3. Accent ──────────────────────────────────────────────────────
ACCENT: str = "#1F5FA8"
ACCENT_HOVER: str = "#194F8C"
ACCENT_SOFT: str = "#E8F0FA"

# ── 4. Mức nghiêm trọng ───────────────────────────────────────────
SEV_CRITICAL: str = "#B42318"
SEV_HIGH: str = "#D9622B"
SEV_MEDIUM: str = "#C79A0A"
SEV_LOW: str = "#5E7A94"

# ── 5. Xếp loại ───────────────────────────────────────────────────
GRADE_A: str = "#1E7A4C"
GRADE_B: str = "#4C8A2E"
GRADE_C: str = "#B38A00"
GRADE_D: str = "#D9622B"
GRADE_F: str = "#B42318"

# ── 6. Trạng thái lỗi ─────────────────────────────────────────────
STATUS_OPEN: str = "#B42318"
STATUS_IN_PROGRESS: str = "#C79A0A"
STATUS_FIXED: str = "#1E7A4C"
STATUS_IGNORED: str = "#8A94A1"

# ── Trọng số mặc định ─────────────────────────────────────────────
TRONG_SO_MAC_DINH: dict[str, float] = {
    "complexity": 0.25,
    "security": 0.25,
    "pylint": 0.20,
    "health": 0.15,
    "dependency": 0.15,
}

# ── Bảng tra cứu ──────────────────────────────────────────────────
SEVERITY_COLORS: dict[str, str] = {
    "Critical": SEV_CRITICAL,
    "High": SEV_HIGH,
    "Medium": SEV_MEDIUM,
    "Low": SEV_LOW,
}

GRADE_COLORS: dict[str, str] = {
    "A": GRADE_A,
    "B": GRADE_B,
    "C": GRADE_C,
    "D": GRADE_D,
    "F": GRADE_F,
}

STATUS_COLORS: dict[str, str] = {
    "open": STATUS_OPEN,
    "in_progress": STATUS_IN_PROGRESS,
    "fixed": STATUS_FIXED,
    "ignored": STATUS_IGNORED,
    "false_positive": STATUS_IGNORED,
}

STATUS_LABELS: dict[str, str] = {
    "open": "Chưa sửa",
    "in_progress": "Đang sửa",
    "fixed": "Đã sửa",
    "ignored": "Báo sai",
    "false_positive": "Báo sai",
}


_REGISTERED_FONTS: bool = False


def init_app_fonts(app: Any | None = None) -> str:
    """
    Đăng ký toàn bộ phông chữ kỹ thuật từ thư mục frontend/assets/fonts/.

    Ưu tiên áp dụng Geist Mono làm phông mặc định toàn cục cho ứng dụng.
    """
    global _REGISTERED_FONTS  # pylint: disable=global-statement
    fonts_dir = Path(__file__).resolve().parent.parent / "assets" / "fonts"

    if not _REGISTERED_FONTS and fonts_dir.exists():
        for font_file in sorted(fonts_dir.glob("*.ttf")):
            if "[" in font_file.name:
                continue
            try:
                QFontDatabase.addApplicationFont(str(font_file))
            except (RuntimeError, OSError) as err:
                _ = str(err)
        _REGISTERED_FONTS = True

    available: set[str] = set()
    try:
        available = set(QFontDatabase.families())
    except (RuntimeError, OSError) as err:
        available = set()
        _ = str(err)

    chosen_family = "monospace"
    for candidate in ("Geist Mono", "JetBrains Mono", "Cascadia Mono", "Consolas"):
        if candidate in available:
            chosen_family = candidate
            break

    target_app = app or QApplication.instance()
    if target_app is not None:
        try:
            global_font = QFont(chosen_family, 10)
            global_font.setStyleHint(QFont.StyleHint.Monospace)
            target_app.setFont(global_font)
        except (RuntimeError, TypeError) as err:
            _ = str(err)

    return chosen_family


def lay_font_code(co: int = 12) -> QFont:
    """
    Nạp phông chữ đơn cách (monospace) an toàn chống crash cho code, số dòng, đường dẫn.

    Ưu tiên nạp Geist Mono nếu có, kế tiếp JetBrains Mono -> Cascadia Mono -> Consolas.
    """
    font_family = init_app_fonts()

    font = QFont(font_family)
    try:
        point_size = int(co) if isinstance(co, (int, float)) and co > 0 else 12
    except (ValueError, TypeError):
        point_size = 12
    font.setPointSize(point_size)
    font.setStyleHint(QFont.StyleHint.Monospace)
    return font


def load_stylesheet() -> str:
    """Nạp nội dung file stylesheet QSS cho toàn bộ ứng dụng."""
    qss_path = Path(__file__).resolve().parent / "style.qss"
    if not qss_path.exists():
        return ""
    try:
        with open(qss_path, "r", encoding="utf-8") as file:
            content = file.read()
            assets_dir = Path(__file__).resolve().parent / "assets"
            chevron_path = (assets_dir / "chevron_down.png").as_posix()
            return content.replace("__CHEVRON_DOWN_PATH__", chevron_path)
    except OSError:
        return ""


def format_datetime(raw_dt: Any) -> str:
    """Định dạng chuỗi ngày giờ sang dd/MM/yyyy HH:mm hoặc —."""
    if not raw_dt:
        return "—"
    dt_str = str(raw_dt).strip()
    if not dt_str:
        return "—"
    try:
        if "T" in dt_str:
            clean_str = dt_str.split(".", maxsplit=1)[0]
            dt_obj = datetime.datetime.fromisoformat(clean_str)
            return dt_obj.strftime("%d/%m/%Y %H:%M")
        if " " in dt_str:
            clean_str = dt_str.split(".", maxsplit=1)[0]
            dt_obj = datetime.datetime.strptime(clean_str, "%Y-%m-%d %H:%M:%S")
            return dt_obj.strftime("%d/%m/%Y %H:%M")
    except (ValueError, TypeError):
        pass
    return dt_str[:16]


__all__ = [
    "WINDOW_BG",
    "SURFACE",
    "SURFACE_ALT",
    "HEADER_BG",
    "ROW_HOVER",
    "BORDER",
    "BORDER_PANEL",
    "BORDER_SOFT",
    "TEXT_MAIN",
    "TEXT_MUTED",
    "SIDEBAR_BG",
    "SIDEBAR_TEXT",
    "SIDEBAR_ACTIVE_BG",
    "SIDEBAR_ACTIVE_TEXT",
    "SIDEBAR_WIDTH",
    "ACCENT",
    "ACCENT_HOVER",
    "ACCENT_SOFT",
    "SEV_CRITICAL",
    "SEV_HIGH",
    "SEV_MEDIUM",
    "SEV_LOW",
    "SEVERITY_COLORS",
    "GRADE_A",
    "GRADE_B",
    "GRADE_C",
    "GRADE_D",
    "GRADE_F",
    "GRADE_COLORS",
    "STATUS_OPEN",
    "STATUS_IN_PROGRESS",
    "STATUS_FIXED",
    "STATUS_IGNORED",
    "STATUS_COLORS",
    "STATUS_LABELS",
    "TEN_TIEU_CHI",
    "TRONG_SO_MAC_DINH",
    "format_datetime",
    "lay_font_code",
    "load_stylesheet",
]
