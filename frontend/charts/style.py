"""Module cấu hình thẩm mỹ đồng bộ cho biểu đồ Matplotlib (SKILLS.md)."""

from typing import Any
import matplotlib as mpl

# Bảng ánh xạ 5 tiêu chí chấm điểm chất lượng mã nguồn
TEN_TIEU_CHI: dict[str, str] = {
    "complexity": "Độ phức tạp & bảo trì",
    "security": "An toàn bảo mật",
    "pylint": "Quy chuẩn mã nguồn",
    "health": "Sức khỏe & Git",
    "dependency": "Thư viện & CVE",
}

# Bảng màu chuẩn dùng cho biểu đồ
CHART_SEVERITY_COLORS: dict[str, str] = {
    "Critical": "#B42318",
    "High": "#D9622B",
    "Medium": "#C79A0A",
    "Low": "#5E7A94",
}

CHART_SEVERITY_LIST: list[str] = ["#B42318", "#D9622B", "#C79A0A", "#5E7A94"]
CHART_ACCENT: str = "#1F5FA8"
CHART_ACCENT_HOVER: str = "#194F8C"
CHART_ACCENT_SOFT: str = "#E8F0FA"
CHART_SURFACE: str = "#FFFFFF"
CHART_BORDER: str = "#D3D8DF"
CHART_GRID: str = "#E4E7EC"
CHART_TEXT_MUTED: str = "#5B6573"


def apply_chart_style() -> None:
    """
    Áp dụng cấu hình giao diện phẳng cho Matplotlib đồng bộ với ứng dụng Desktop.

    - Nền trắng #FFFFFF, viền trục xám nhạt #D3D8DF.
    - Bỏ viền trên (spines.top) và viền phải (spines.right).
    - Đường lưới mảnh #E4E7EC, tiêu đề căn trái (titlelocation = 'left').
    - Phông chữ sans-serif chuẩn hệ thống (Segoe UI, SF Pro, Noto Sans).
    """
    config: dict[str, Any] = {
        "figure.facecolor": CHART_SURFACE,
        "axes.facecolor": CHART_SURFACE,
        "axes.edgecolor": CHART_BORDER,
        "axes.labelcolor": CHART_TEXT_MUTED,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.grid": True,
        "axes.axisbelow": True,
        "grid.color": CHART_GRID,
        "grid.linewidth": 0.8,
        "xtick.color": CHART_TEXT_MUTED,
        "ytick.color": CHART_TEXT_MUTED,
        "font.family": "sans-serif",
        "font.sans-serif": ["Segoe UI", "SF Pro Text", "Noto Sans", "DejaVu Sans"],
        "font.size": 10,
        "axes.titlesize": 11,
        "axes.titleweight": "semibold",
        "axes.titlelocation": "left",
        "legend.frameon": False,
        "figure.constrained_layout.use": True,
    }
    mpl.rcParams.update(config)


if __name__ == "__main__":
    apply_chart_style()
    print("[+] Đã áp dụng thành công cấu hình Matplotlib theo SKILLS.md!")
    print(f"    - figure.facecolor : {mpl.rcParams['figure.facecolor']}")
    print(f"    - axes.spines.top  : {mpl.rcParams['axes.spines.top']}")
    print(f"    - axes.titlelocation: {mpl.rcParams['axes.titlelocation']}")
