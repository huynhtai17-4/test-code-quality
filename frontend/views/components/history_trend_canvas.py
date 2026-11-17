"""Component vẽ đồ thị xu hướng điểm số các phiên phân tích qua Matplotlib."""

from __future__ import annotations

from typing import Any

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from PyQt6.QtWidgets import QVBoxLayout, QWidget  # pylint: disable=no-name-in-module

from frontend.charts.style import (
    CHART_ACCENT,
    CHART_TEXT_MUTED,
    apply_chart_style,
)
from frontend.models.history_model import _format_short_date
from frontend.views.theme import SURFACE


def _extract_trend_data(
    sessions: list[dict[str, Any]],
) -> tuple[list[int], list[float], list[str]]:
    """Trích xuất tọa độ X, điểm Y và nhãn ngày tháng theo trật tự thời gian."""
    chrono = sorted(
        sessions,
        key=lambda s: (
            str(s.get("started_at") or s.get("completed_at") or ""),
            int(s.get("id") or 0),
        ),
    )
    labels = [
        f"#{s.get('id', '')}\n{_format_short_date(s.get('started_at') or s.get('completed_at'))}"
        for s in chrono
    ]
    scores = [float(s.get("total_score") or 0.0) for s in chrono]
    return list(range(len(scores))), scores, labels


class HistoryTrendCanvas(QWidget):
    """Widget nhúng FigureCanvasQTAgg vẽ biểu đồ xu hướng điểm số theo thời gian."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        apply_chart_style()

        self.fig = Figure(figsize=(7.5, 2.0), dpi=100)
        self.fig.patch.set_facecolor(SURFACE)
        self.canvas = FigureCanvasQTAgg(self.fig)
        self.ax = self.fig.add_subplot(111)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.canvas)
        self.setFixedHeight(190)

    def draw_empty(self, message: str) -> None:
        """Hiển thị thông điệp nhẹ nhàng ở giữa khi chưa đủ số phiên để vẽ đường."""
        self.ax.clear()
        self.ax.set_facecolor(SURFACE)
        self.ax.text(
            x=0.5,
            y=0.5,
            s=message,
            horizontalalignment="center",
            verticalalignment="center",
            transform=self.ax.transAxes,
            color=CHART_TEXT_MUTED,
            fontsize=11,
        )
        self.ax.set_xticks([])
        self.ax.set_yticks([])
        self.canvas.draw()

    def draw_trend(self, sessions: list[dict[str, Any]]) -> None:
        """Vẽ biểu đồ đường xu hướng từ danh sách các phiên quét."""
        if len(sessions) < 2:
            self.draw_empty("Cần ít nhất 2 phiên phân tích để vẽ biểu đồ xu hướng")
            return

        x_coords, scores, labels = _extract_trend_data(sessions)

        self.ax.clear()
        self.ax.set_facecolor(SURFACE)

        self.ax.plot(
            x_coords,
            scores,
            color=CHART_ACCENT,
            linewidth=2.0,
            marker="o",
            markersize=5.5,
            markerfacecolor="#FFFFFF",
            markeredgecolor=CHART_ACCENT,
            markeredgewidth=2.0,
            zorder=3,
        )

        for idx in (0, -1):
            self.ax.annotate(
                f"{scores[idx]:.1f}",
                xy=(x_coords[idx], scores[idx]),
                xytext=(0, 7),
                textcoords="offset points",
                ha="center",
                fontsize=9,
                fontweight="semibold",
                color=CHART_ACCENT,
            )

        self.ax.set_ylim(-5, 108)
        self.ax.set_yticks([0, 25, 50, 75, 100])
        self.ax.set_xticks(x_coords)
        self.ax.set_xticklabels(labels, fontsize=8)

        self.canvas.draw()
