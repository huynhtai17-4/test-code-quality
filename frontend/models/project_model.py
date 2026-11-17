"""Data Model và Proxy Model quản lý danh sách dự án cho PyQt6 QTableView."""

from __future__ import annotations

from typing import Any

from PyQt6.QtCore import (  # pylint: disable=no-name-in-module
    QAbstractTableModel,
    QModelIndex,
    QObject,
    QSortFilterProxyModel,
    Qt,
)
from PyQt6.QtGui import QColor  # pylint: disable=no-name-in-module

from frontend.views import theme
from frontend.views.theme import format_datetime, lay_font_code

_HEADERS = (
    "Tên dự án",
    "Nguồn",
    "Đường dẫn / Liên kết",
    "Lần phân tích cuối",
    "Điểm số",
)


def _format_score(project: dict[str, Any]) -> str:
    """Định dạng điểm số và xếp loại: 82 (B) hoặc —."""
    score = project.get("total_score")
    if score is None:
        return "—"
    try:
        score_val = int(round(float(score)))
        grade = str(project.get("grade") or project.get("overall_grade") or "").strip().upper()
        if grade:
            return f"{score_val} ({grade})"
        return f"{score_val}"
    except (ValueError, TypeError):
        return "—"


def _format_source_type(project: dict[str, Any]) -> str:
    """Xác định loại nguồn: Thư mục hoặc GitHub."""
    raw_type = str(project.get("source_type", "")).strip().lower()
    path = str(project.get("path") or project.get("source_path") or "").strip().lower()
    if "git" in raw_type or path.startswith(("http://", "https://", "git@")):
        return "GitHub"
    return "Thư mục"


def _get_display_data(project: dict[str, Any], col: int) -> str:
    """Trích xuất chuỗi hiển thị theo từng cột dữ liệu."""
    if col == 0:
        return str(project.get("name", "—"))
    if col == 1:
        return _format_source_type(project)
    if col == 2:
        return str(project.get("path") or project.get("source_path") or "—")
    if col == 3:
        raw_time = project.get("last_analyzed_at") or project.get("completed_at")
        return format_datetime(raw_time)
    if col == 4:
        return _format_score(project)
    return "—"


class ProjectTableModel(QAbstractTableModel):
    """Data Model cho bảng hiển thị danh sách dự án (5 cột chuẩn SKILLS.md)."""

    def __init__(self, projects: list[dict[str, Any]] | None = None, parent: QObject | None = None):
        super().__init__(parent)
        self._projects: list[dict[str, Any]] = list(projects) if projects else []

    def rowCount(self, _parent: QModelIndex = QModelIndex()) -> int:  # pylint: disable=invalid-name
        """Trả về tổng số dòng trong bảng dữ liệu."""
        return len(self._projects)

    def columnCount(self, _parent: QModelIndex = QModelIndex()) -> int:  # pylint: disable=invalid-name
        """Trả về tổng số cột trong bảng dữ liệu."""
        return len(_HEADERS)

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        """Trả về dữ liệu hiển thị, phông chữ và căn lề cho từng ô trong bảng."""
        if not index.isValid() or index.row() >= len(self._projects):
            return None

        project = self._projects[index.row()]
        col = index.column()

        if role == Qt.ItemDataRole.DisplayRole:
            return _get_display_data(project, col)
        if role == Qt.ItemDataRole.FontRole:
            return lay_font_code(11) if col in (2, 3, 4) else None
        if role == Qt.ItemDataRole.TextAlignmentRole:
            align = Qt.AlignmentFlag.AlignRight if col == 4 else Qt.AlignmentFlag.AlignLeft
            return align | Qt.AlignmentFlag.AlignVCenter
        if role == Qt.ItemDataRole.ForegroundRole and col == 4:
            grade = str(project.get("grade") or project.get("overall_grade") or "").strip().upper()
            return QColor(theme.GRADE_COLORS[grade]) if grade in theme.GRADE_COLORS else None
        return project if role == Qt.ItemDataRole.UserRole else None

    def headerData(  # pylint: disable=invalid-name
        self,
        section: int,
        orientation: Qt.Orientation,
        role: int = Qt.ItemDataRole.DisplayRole,
    ) -> Any:
        """Trả về tiêu đề các cột ở phần đầu bảng."""
        if orientation == Qt.Orientation.Horizontal:
            if role == Qt.ItemDataRole.DisplayRole and 0 <= section < len(_HEADERS):
                return _HEADERS[section]
            if role == Qt.ItemDataRole.TextAlignmentRole:
                if section == 4:
                    return Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
                return Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
        return None

    def set_projects(self, projects: list[dict[str, Any]]) -> None:
        """Cập nhật dữ liệu danh sách dự án và làm mới bảng."""
        self.beginResetModel()
        self._projects = list(projects)
        self.endResetModel()

    def get_project(self, row: int) -> dict[str, Any] | None:
        """Lấy thông tin dự án tại chỉ số dòng xác định."""
        if 0 <= row < len(self._projects):
            return self._projects[row]
        return None


class ProjectFilterProxyModel(QSortFilterProxyModel):
    """Bộ lọc dữ liệu động theo từ khóa tìm kiếm và loại nguồn."""

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._search_keyword: str = ""
        self._source_filter: str = "Tất cả"

    def set_search_keyword(self, keyword: str) -> None:
        """Cập nhật từ khóa tìm kiếm."""
        self._search_keyword = str(keyword).strip().lower()
        self.invalidateFilter()

    def set_source_filter(self, source: str) -> None:
        """Cập nhật bộ lọc loại nguồn (Tất cả, Thư mục, GitHub)."""
        self._source_filter = str(source).strip()
        self.invalidateFilter()

    def filterAcceptsRow(  # pylint: disable=invalid-name
        self,
        source_row: int,
        _source_parent: QModelIndex,
    ) -> bool:
        """Kiểm tra điều kiện hiển thị của từng dòng dữ liệu."""
        model = self.sourceModel()
        if not isinstance(model, ProjectTableModel):
            return True

        project = model.get_project(source_row)
        if not project:
            return False

        if self._search_keyword:
            name = str(project.get("name", "")).lower()
            path = str(project.get("path") or project.get("source_path") or "").lower()
            if self._search_keyword not in name and self._search_keyword not in path:
                return False

        if self._source_filter not in ("Tất cả", "Tất cả nguồn"):
            stype = _format_source_type(project)
            if self._source_filter == "Thư mục cục bộ" and stype != "Thư mục":
                return False
            if self._source_filter in ("Kho mã nguồn GitHub", "GitHub") and stype != "GitHub":
                return False

        return True
