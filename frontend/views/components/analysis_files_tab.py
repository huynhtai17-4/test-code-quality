"""Component giao diện Tab thống kê chi tiết theo từng tệp tin (AnalysisFilesTab)."""

from __future__ import annotations

from PyQt6.QtCore import QAbstractItemModel  # pylint: disable=no-name-in-module
from PyQt6.QtWidgets import (  # pylint: disable=no-name-in-module
    QTableView,
    QVBoxLayout,
    QWidget,
)

from frontend.views.widgets.panel import Panel
from frontend.views.widgets.table_utils import chuan_hoa_bang


# pylint: disable=too-few-public-methods
class AnalysisFilesTab(QWidget):
    """Tab 2: Hiển thị bảng tổng kết các chỉ số kỹ thuật và số lỗi theo từng file."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.table = QTableView(self)
        self._init_ui()

    def _init_ui(self) -> None:
        """Khởi tạo bố cục bảng tệp tin trong Panel."""
        v_layout = QVBoxLayout(self)
        v_layout.setContentsMargins(16, 16, 16, 16)
        v_layout.setSpacing(10)

        panel = Panel(self)
        p_layout = QVBoxLayout(panel)
        p_layout.setContentsMargins(0, 0, 0, 0)

        chuan_hoa_bang(self.table, cot_gian=0, cot_so=(1, 2, 3, 4, 5, 6, 7))
        self.table.setSelectionMode(QTableView.SelectionMode.SingleSelection)
        self.table.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        self.table.setSortingEnabled(True)

        p_layout.addWidget(self.table)
        v_layout.addWidget(panel)

    def set_model(self, model: QAbstractItemModel) -> None:
        """Thiết lập Data Model hoặc Proxy Model cho bảng tệp tin."""
        self.table.setModel(model)
