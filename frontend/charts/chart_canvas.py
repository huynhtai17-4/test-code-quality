"""Canvas tích hợp Matplotlib hiển thị các loại biểu đồ trực quan (SKILLS.md)."""

import logging
import math
import sys
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# pylint: disable=wrong-import-position,no-name-in-module
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from PyQt6.QtWidgets import QVBoxLayout, QWidget

from frontend.charts.style import (
    CHART_ACCENT,
    CHART_SEVERITY_COLORS,
    CHART_TEXT_MUTED,
    TEN_TIEU_CHI,
    apply_chart_style,
)

logger = logging.getLogger(__name__)


class AnalysisChartCanvas(QWidget):
    """
    Widget nhúng Matplotlib phẳng cho màn hình Phân tích.

    Cung cấp các phương thức vẽ:
    - Donut phân bố mức độ lỗi (Critical/High/Medium/Low).
    - Đa giác Radar 5 tiêu chí chấm điểm (thang 0-100).
    - Biểu đồ cột ngang Top 5 file có nguy cơ cao nhất.
    - Xuất ảnh đồ thị PNG chất lượng cao.
    """

    def __init__(
        self,
        parent: QWidget | None = None,
        width: float = 4.6,
        height: float = 3.2,
        dpi: int = 100,
    ) -> None:
        super().__init__(parent)
        apply_chart_style()

        self.fig = Figure(figsize=(width, height), dpi=dpi)
        self.canvas = FigureCanvasQTAgg(self.fig)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.canvas)

        self.draw_empty("Chưa có dữ liệu biểu đồ")

    def draw_empty(self, message: str = "Chưa có dữ liệu biểu đồ") -> None:
        """Hiển thị dòng chữ thông báo giữa canvas khi chưa có dữ liệu."""
        self.fig.clear()
        ax = self.fig.add_subplot(111)
        ax.axis("off")
        ax.text(
            0.5,
            0.5,
            message,
            ha="center",
            va="center",
            color=CHART_TEXT_MUTED,
            fontsize=11,
            transform=ax.transAxes,
        )
        self.canvas.draw()

    def draw_severity_pie(self, distribution: dict[str, int]) -> None:
        """Vẽ biểu đồ hình vành khuyên (Donut) phân bố 4 mức độ nghiêm trọng của lỗi."""
        self.fig.clear()
        total = sum(distribution.values()) if distribution else 0
        if total <= 0:
            self.draw_empty("Chưa ghi nhận lỗi nào trong dự án")
            return

        levels = ("Critical", "High", "Medium", "Low")
        labels_vi = ("Nghiêm trọng", "Cao", "Trung bình", "Thấp")
        counts = [int(distribution.get(lvl, 0)) for lvl in levels]
        colors = [CHART_SEVERITY_COLORS[lvl] for lvl in levels]

        active_labels: list[str] = []
        active_counts: list[int] = []
        active_colors: list[str] = []

        for lbl, cnt, clr in zip(labels_vi, counts, colors):
            if cnt > 0:
                pct = (cnt / total) * 100
                active_labels.append(f"{lbl}\n{cnt} ({pct:.1f}%)")
                active_counts.append(cnt)
                active_colors.append(clr)

        ax = self.fig.add_subplot(111)
        ax.pie(
            active_counts,
            labels=active_labels,
            colors=active_colors,
            startangle=140,
            wedgeprops={"width": 0.45, "edgecolor": "#FFFFFF", "linewidth": 1.5},
            textprops={"color": CHART_TEXT_MUTED, "fontsize": 9},
        )
        ax.set_title("Phân bố mức độ lỗi", pad=10)
        self.canvas.draw()

    def draw_criteria_radar(self, criteria_scores: dict[str, float]) -> None:
        """Vẽ biểu đồ Radar đa giác 5 tiêu chí đánh giá chất lượng (thang điểm 0–100)."""
        self.fig.clear()
        if not criteria_scores:
            self.draw_empty("Chưa có điểm tiêu chí")
            return

        keys = ("complexity", "security", "pylint", "health", "dependency")
        labels = [TEN_TIEU_CHI.get(k, k) for k in keys]
        raw_vals = [float(criteria_scores.get(k, 0.0)) for k in keys]

        num_vars = len(keys)
        angles = [n / float(num_vars) * 2 * math.pi for n in range(num_vars)]
        angles += angles[:1]
        values = raw_vals + raw_vals[:1]

        ax = self.fig.add_subplot(111, polar=True)
        ax.set_theta_offset(math.pi / 2)
        ax.set_theta_direction(-1)

        ax.set_xticks(angles[:-1])
        ax.set_xticklabels(labels, fontsize=9, color=CHART_TEXT_MUTED)

        ax.set_rlabel_position(0)
        ax.set_yticks([20, 40, 60, 80, 100])
        ax.set_yticklabels(["20", "40", "60", "80", "100"], fontsize=8, color=CHART_TEXT_MUTED)
        ax.set_ylim(0, 100)

        ax.plot(angles, values, color=CHART_ACCENT, linewidth=2, linestyle="solid")
        ax.fill(angles, values, color=CHART_ACCENT, alpha=0.15)
        ax.set_title("Đa giác 5 tiêu chí kiểm định", pad=14)

        self.canvas.draw()

    def draw_top_risk_bar(self, top_files: list[dict[str, Any]]) -> None:
        """Vẽ biểu đồ cột ngang cho Top 5 tệp tin rủi ro cao nhất."""
        self.fig.clear()
        if not top_files:
            self.draw_empty("Chưa có thống kê tệp tin rủi ro")
            return

        top5 = top_files[:5]
        names: list[str] = []
        counts: list[int] = []

        for item in top5:
            raw_name = str(item.get("file", "unknown")).replace("\\", "/")
            short_name = raw_name if len(raw_name) <= 24 else f"...{raw_name[-21:]}"
            names.append(short_name)
            counts.append(int(item.get("total_issues", 0)))

        ax = self.fig.add_subplot(111)
        y_pos = list(range(len(names)))
        bars = ax.barh(y_pos, counts, color=CHART_ACCENT, height=0.55, edgecolor="none")
        ax.set_yticks(y_pos)
        ax.set_yticklabels(names, fontsize=9, color=CHART_TEXT_MUTED)
        ax.invert_yaxis()
        ax.set_xlabel("Số lượng lỗi", fontsize=9, color=CHART_TEXT_MUTED)
        ax.set_title("Top 5 tệp tin rủi ro cao nhất", pad=10)
        ax.bar_label(bars, padding=4, fontsize=9, color=CHART_TEXT_MUTED)

        self.canvas.draw()

    def save_chart(self, file_path: str) -> bool:
        """Xuất đồ thị hiện tại ra tệp tin ảnh PNG độ phân giải cao."""
        try:
            self.fig.savefig(file_path, dpi=300, bbox_inches="tight")
            return True
        except Exception as exc:  # pylint: disable=broad-exception-caught
            logger.error("Lỗi khi lưu biểu đồ ra tệp: %s", exc)
            return False
