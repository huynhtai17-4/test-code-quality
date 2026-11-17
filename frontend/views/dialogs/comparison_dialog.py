"""Hộp thoại so sánh chi tiết điểm số giữa hai phiên phân tích."""

from __future__ import annotations

from typing import Any

from PyQt6.QtCore import Qt  # pylint: disable=no-name-in-module
from PyQt6.QtGui import (  # pylint: disable=no-name-in-module
    QColor,
    QKeySequence,
    QShortcut,
)
from PyQt6.QtWidgets import (  # pylint: disable=no-name-in-module
    QAbstractItemView,
    QDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from frontend.charts.style import TEN_TIEU_CHI
from frontend.models.history_model import _get_criteria_scores
from frontend.views.theme import (
    GRADE_A,
    GRADE_F,
    TEXT_MUTED,
    format_datetime,
)


def _format_delta(diff: float) -> tuple[str, QColor]:
    """Tạo chuỗi ký tự hiển thị độ lệch kèm màu sắc trực quan."""
    if diff > 0.001:
        return f"▲ +{diff:.2f}", QColor(GRADE_A)
    if diff < -0.001:
        return f"▼ {diff:.2f}", QColor(GRADE_F)
    return "— 0.00", QColor(TEXT_MUTED)


class ComparisonDialog(QDialog):  # pylint: disable=too-few-public-methods
    """
    Hộp thoại đối chiếu kết quả chi tiết giữa hai phiên quét được chọn.

    Hiển thị độ lệch delta theo từng tiêu chí kèm mũi tên chỉ hướng và màu sắc.
    """

    def __init__(
        self,
        session_a: dict[str, Any],
        session_b: dict[str, Any],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("So sánh kết quả giữa hai phiên phân tích")
        self.setModal(True)
        self.resize(680, 420)

        # Xác định phiên cũ hơn và phiên mới hơn dựa theo thời gian/ID
        self.old_sess, self.new_sess = self._order_sessions(session_a, session_b)
        self._init_ui()

    @staticmethod
    def _order_sessions(
        s1: dict[str, Any],
        s2: dict[str, Any],
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        """Phân loại phiên quét cũ hơn và mới hơn."""
        t1 = str(s1.get("started_at") or s1.get("completed_at") or "")
        t2 = str(s2.get("started_at") or s2.get("completed_at") or "")
        if t1 and t2 and t1 < t2:
            return s1, s2
        if s1.get("id", 0) < s2.get("id", 0):
            return s1, s2
        return s2, s1

    def _init_ui(self) -> None:
        """Xây dựng bảng đối chiếu và nút đóng."""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 18, 20, 18)
        main_layout.setSpacing(14)

        desc_lbl = QLabel(
            "Đối chiếu điểm số các tiêu chí chất lượng mã nguồn giữa hai lần kiểm định:"
        )
        desc_lbl.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 13px;")
        main_layout.addWidget(desc_lbl)

        table = self._build_comparison_table()
        main_layout.addWidget(table, 1)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        btn_close = QPushButton("Đóng")
        btn_close.setProperty("role", "primary")
        btn_close.clicked.connect(self.accept)

        shortcut_esc = QShortcut(QKeySequence("Esc"), self)
        shortcut_esc.activated.connect(self.accept)

        shortcut_enter = QShortcut(QKeySequence("Return"), self)
        shortcut_enter.activated.connect(self.accept)

        btn_layout.addWidget(btn_close)
        main_layout.addLayout(btn_layout)

    def _get_comparison_headers(self) -> list[str]:
        """Tạo danh sách tiêu đề 4 cột cho bảng so sánh."""
        old_id = self.old_sess.get("id", "—")
        new_id = self.new_sess.get("id", "—")
        old_dt = format_datetime(
            self.old_sess.get("started_at") or self.old_sess.get("completed_at")
        )
        new_dt = format_datetime(
            self.new_sess.get("started_at") or self.new_sess.get("completed_at")
        )
        return [
            "Tiêu chí đánh giá",
            f"Phiên cũ (#{old_id} · {old_dt})",
            f"Phiên mới (#{new_id} · {new_dt})",
            "Độ lệch (Δ)",
        ]

    def _build_comparison_table(self) -> QTableWidget:
        """Tạo bảng đối chiếu 6 dòng x 4 cột."""
        headers = self._get_comparison_headers()
        table = QTableWidget(6, 4)
        table.setHorizontalHeaderLabels(headers)
        table.verticalHeader().setVisible(False)
        table.setAlternatingRowColors(True)
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)

        header_view = table.horizontalHeader()
        header_view.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        for i in range(1, 4):
            header_view.setSectionResizeMode(i, QHeaderView.ResizeMode.ResizeToContents)

        old_scores = _get_criteria_scores(self.old_sess)
        new_scores = _get_criteria_scores(self.new_sess)

        criteria_keys = ["complexity", "security", "pylint", "health", "dependency"]
        for row, key in enumerate(criteria_keys):
            v_old = old_scores.get(key, 0.0)
            v_new = new_scores.get(key, 0.0)
            self._fill_comparison_row(
                table,
                row,
                TEN_TIEU_CHI.get(key, key),
                (f"{v_old:.1f}", f"{v_new:.1f}"),
                v_new - v_old,
            )

        self._fill_total_row(table)
        return table

    def _fill_total_row(self, table: QTableWidget) -> None:
        """Điền dòng điểm tổng kết."""
        tot_old = float(self.old_sess.get("total_score") or 0.0)
        tot_new = float(self.new_sess.get("total_score") or 0.0)
        grd_old = str(self.old_sess.get("grade") or "—").upper()
        grd_new = str(self.new_sess.get("grade") or "—").upper()
        self._fill_comparison_row(
            table,
            5,
            "Điểm tổng kết",
            (f"{tot_old:.1f} ({grd_old})", f"{tot_new:.1f} ({grd_new})"),
            tot_new - tot_old,
        )

    @staticmethod
    def _fill_comparison_row(
        table: QTableWidget,
        row: int,
        name: str,
        texts: tuple[str, str],
        diff: float,
    ) -> None:
        """Điền dữ liệu đối chiếu và định dạng độ lệch màu sắc cho từng dòng."""
        delta_str, delta_color = _format_delta(diff)

        item_name = QTableWidgetItem(name)
        item_old = QTableWidgetItem(texts[0])
        item_new = QTableWidgetItem(texts[1])
        item_delta = QTableWidgetItem(delta_str)

        align_r = int(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        item_old.setTextAlignment(align_r)
        item_new.setTextAlignment(align_r)
        item_delta.setTextAlignment(align_r)
        item_delta.setForeground(delta_color)

        if row == 5:
            font = item_name.font()
            font.setBold(True)
            for itm in (item_name, item_old, item_new, item_delta):
                itm.setFont(font)

        table.setItem(row, 0, item_name)
        table.setItem(row, 1, item_old)
        table.setItem(row, 2, item_new)
        table.setItem(row, 3, item_delta)
