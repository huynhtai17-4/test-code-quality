"""Data Model quản lý bảng tổng kết chi tiết từng tệp tin trong phiên phân tích."""

from __future__ import annotations

from typing import Any

from PyQt6.QtCore import (  # pylint: disable=no-name-in-module
    QAbstractTableModel,
    QModelIndex,
    QObject,
    Qt,
)
from PyQt6.QtGui import QColor  # pylint: disable=no-name-in-module

_FILE_HEADERS = (
    "Tên tệp tin",
    "Tổng lỗi",
    "Nghiêm trọng",
    "Cao",
    "Trung bình",
    "Thấp",
    "Độ phức tạp (CC)",
    "Bảo trì (MI)",
)


def _extract_metric_str(val: Any) -> str:
    """Định dạng giá trị số CC hoặc MI."""
    return f"{val:.1f}" if isinstance(val, (int, float)) else "—"


def _format_count_or_dash(val: Any) -> str:
    """Hiển thị số lượng hoặc gạch ngang nếu là 0."""
    try:
        n = int(val)
        return str(n) if n > 0 else "—"
    except (ValueError, TypeError):
        return "—"


def _get_display_value(file_info: dict[str, Any], col: int) -> str:
    """Trích xuất chuỗi hiển thị theo từng cột dữ liệu."""
    extractors = (
        lambda x: str(x.get("file", "—")),
        lambda x: str(x.get("total_issues", 0)),
        lambda x: _format_count_or_dash(x.get("critical_count")),
        lambda x: _format_count_or_dash(x.get("high_count")),
        lambda x: _format_count_or_dash(x.get("medium_count")),
        lambda x: _format_count_or_dash(x.get("low_count")),
        lambda x: _extract_metric_str(x.get("cc")),
        lambda x: _extract_metric_str(x.get("mi")),
    )
    if 0 <= col < len(extractors):
        return extractors[col](file_info)
    return "—"


class FileSummaryTableModel(QAbstractTableModel):
    """Mô hình dữ liệu bảng tổng kết theo từng file mã nguồn (8 cột chuẩn)."""

    def __init__(self, files: list[dict[str, Any]] | None = None, parent: QObject | None = None):
        super().__init__(parent)
        self._files: list[dict[str, Any]] = []
        if files:
            self.set_files(files)

    def rowCount(self, _parent: QModelIndex = QModelIndex()) -> int:  # pylint: disable=invalid-name
        """Trả về số lượng dòng trong bảng."""
        return len(self._files)

    def columnCount(self, _parent: QModelIndex = QModelIndex()) -> int:  # pylint: disable=invalid-name
        """Trả về số lượng cột của bảng."""
        return len(_FILE_HEADERS)

    def data(  # pylint: disable=too-many-return-statements
        self,
        index: QModelIndex,
        role: int = Qt.ItemDataRole.DisplayRole,
    ) -> Any:
        """Trả về dữ liệu hiển thị, phông chữ và căn lề cho từng ô."""
        if not index.isValid() or index.row() >= len(self._files):
            return None

        file_info = self._files[index.row()]
        col = index.column()

        if role == Qt.ItemDataRole.DisplayRole:
            return _get_display_value(file_info, col)

        if role == Qt.ItemDataRole.ForegroundRole:
            return self._get_cell_color(file_info, col)

        if role == Qt.ItemDataRole.FontRole:
            from frontend.views.theme import lay_font_code  # pylint: disable=import-outside-toplevel
            return lay_font_code(11)

        if role == Qt.ItemDataRole.TextAlignmentRole:
            align_left = Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
            return align_left if col == 0 else Qt.AlignmentFlag.AlignCenter

        if role == Qt.ItemDataRole.UserRole:
            return file_info

        return None

    @staticmethod
    def _get_cell_color(  # pylint: disable=too-many-return-statements,too-many-branches
        file_info: dict[str, Any],
        col: int,
    ) -> QColor | None:
        """Tính toán màu sắc chữ cho từng ô dữ liệu kỹ thuật."""
        if col == 1:
            cnt = int(file_info.get("total_issues", 0))
            return QColor("#0F172A") if cnt > 0 else QColor("#94A3B8")
        if col == 2:
            crit = int(file_info.get("critical_count", 0))
            return QColor("#DC2626") if crit > 0 else QColor("#94A3B8")
        if col == 3:
            high = int(file_info.get("high_count", 0))
            return QColor("#EA580C") if high > 0 else QColor("#94A3B8")
        if col == 4:
            med = int(file_info.get("medium_count", 0))
            return QColor("#D97706") if med > 0 else QColor("#94A3B8")
        if col == 5:
            low = int(file_info.get("low_count", 0))
            return QColor("#2563EB") if low > 0 else QColor("#94A3B8")
        if col == 6:
            cc_val = file_info.get("cc")
            if isinstance(cc_val, (int, float)):
                if cc_val >= 15:
                    return QColor("#DC2626")
                if cc_val >= 10:
                    return QColor("#D97706")
                return QColor("#0F172A")
            return QColor("#94A3B8")
        if col == 7:
            mi_val = file_info.get("mi")
            if isinstance(mi_val, (int, float)):
                if mi_val < 50:
                    return QColor("#DC2626")
                if mi_val < 65:
                    return QColor("#D97706")
                return QColor("#059669")
            return QColor("#94A3B8")
        return None

    def headerData(  # pylint: disable=invalid-name
        self,
        section: int,
        orientation: Qt.Orientation,
        role: int = Qt.ItemDataRole.DisplayRole,
    ) -> Any:
        """Trả về tiêu đề các cột ở phần đầu bảng."""
        if orientation == Qt.Orientation.Horizontal and role == Qt.ItemDataRole.DisplayRole:
            if 0 <= section < len(_FILE_HEADERS):
                return _FILE_HEADERS[section]
        return None

    def set_files(self, files: list[dict[str, Any]]) -> None:
        """Cập nhật dữ liệu danh sách tệp và sắp xếp ưu tiên lỗi Critical/High lên đầu."""
        self.beginResetModel()
        sorted_files = sorted(
            files,
            key=lambda x: (
                int(x.get("critical_count", 0)),
                int(x.get("high_count", 0)),
                int(x.get("total_issues", 0)),
            ),
            reverse=True,
        )
        self._files = sorted_files
        self.endResetModel()

    def get_file(self, row: int) -> dict[str, Any] | None:
        """Lấy thông tin tệp tin tại dòng chỉ định."""
        if 0 <= row < len(self._files):
            return self._files[row]
        return None
