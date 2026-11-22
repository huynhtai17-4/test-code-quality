"""Data Model và Proxy Model quản lý danh sách lỗi mã nguồn cho PyQt6 QTableView."""

from __future__ import annotations

import re
from typing import Any

from PyQt6.QtCore import (  # pylint: disable=no-name-in-module
    QAbstractTableModel,
    QModelIndex,
    QSortFilterProxyModel,
    Qt,
)
from PyQt6.QtGui import QColor, QFont  # pylint: disable=no-name-in-module

from frontend.views.theme import (
    SEVERITY_COLORS,
    STATUS_FIXED,
    STATUS_IGNORED,
    STATUS_IN_PROGRESS,
    STATUS_OPEN,
    TEXT_MAIN,
    lay_font_code,
)

_HEADERS = (
    "Tệp : Dòng",
    "Mức độ",
    "Trạng thái",
    "Công cụ",
    "Mô tả tóm tắt",
)

_SEVERITY_TITLES: dict[str, str] = {
    "critical": "Critical",
    "high": "High",
    "medium": "Medium",
    "low": "Low",
    "info": "Low",
}

_STATUS_DISPLAY_MAP: dict[str, str] = {
    "open": "● Chưa sửa",
    "in_progress": "● Đang sửa",
    "fixed": "● Đã sửa",
    "ignored": "● Báo sai",
    "false_positive": "● Báo sai",
}

_TOOL_DISPLAY_MAP: dict[str, str] = {
    "bandit": "Bandit",
    "pylint": "Pylint",
    "radon": "Radon",
    "pip-audit": "Pip-audit",
    "pip_audit": "Pip-audit",
    "malware_ast": "Mã độc & AST",
    "malware": "Mã độc & AST",
    "manual": "Manual",
}


def _normalize_severity(sev: Any) -> str:
    """Chuẩn hóa chuỗi mức độ nghiêm trọng."""
    raw = str(sev or "medium").strip().lower()
    return _SEVERITY_TITLES.get(raw, "Medium")


def _normalize_status(st: Any) -> str:
    """Chuẩn hóa mã trạng thái lỗi về 4 nhóm chuẩn."""
    raw = str(st or "open").strip().lower()
    if raw == "false_positive":
        return "ignored"
    if raw in ("open", "in_progress", "fixed", "ignored"):
        return raw
    return "open"


def _format_location(issue: dict[str, Any]) -> str:
    """Định dạng vị trí tệp và dòng dạng filename.py:42."""
    file_path = str(issue.get("file_path") or issue.get("file") or "").strip()
    line_no = issue.get("line_number")
    if line_no is None:
        line_no = issue.get("line")
    if line_no is not None and str(line_no).strip():
        return f"{file_path}:{line_no}"
    return file_path or "—"


def _prepare_snippet_lines(snippet_raw: Any, target_line: int) -> list[tuple[int, str]]:
    """Chuẩn hóa code snippet thành danh sách các cặp (số dòng, nội dung hiển thị)."""
    if isinstance(snippet_raw, str):
        raw_lines = snippet_raw.splitlines()
    elif isinstance(snippet_raw, (list, tuple)):
        raw_lines = list(snippet_raw)
    elif isinstance(snippet_raw, dict):
        raw_lines = snippet_raw.get("lines", [])
        if isinstance(raw_lines, str):
            raw_lines = raw_lines.splitlines()
    else:
        raw_lines = []

    result: list[tuple[int, str]] = []
    start_line = max(1, target_line - 3) if target_line > 0 else 1

    for idx, item in enumerate(raw_lines):
        if isinstance(item, (list, tuple)) and len(item) == 2:
            try:
                ln = int(item[0])
                txt = str(item[1])
                result.append((ln, f"{ln} | {txt}"))
                continue
            except (ValueError, TypeError):
                pass
        line_str = str(item)
        match = re.match(r"^\s*(\d+)\s*[|:]\s*(.*)$", line_str)
        if match:
            ln = int(match.group(1))
            content = match.group(2)
            result.append((ln, f"{ln} | {content}"))
        else:
            ln = start_line + idx
            result.append((ln, f"{ln} | {line_str}"))
    return result


class IssueTableModel(QAbstractTableModel):
    """
    Model bảng dữ liệu danh sách lỗi (IssueTableModel).

    Quản lý 5 cột chuẩn:
    0: Tệp : Dòng (font monospace)
    1: Mức độ (Critical, High, Medium, Low với màu SEV_*)
    2: Trạng thái (● Chưa sửa, ● Đang sửa, ● Đã sửa, ● Báo sai với màu STATUS_*)
    3: Công cụ (Bandit, Pylint, Radon, Pip-audit, Manual)
    4: Mô tả tóm tắt (Tiêu đề lỗi hoặc thông điệp cảnh báo)
    """

    def __init__(self, issues: list[dict[str, Any]] | None = None) -> None:
        super().__init__()
        self._issues: list[dict[str, Any]] = list(issues or [])
        self._font_code: QFont = lay_font_code(11)

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:  # pylint: disable=invalid-name
        """Số dòng dữ liệu trong bảng."""
        if parent.isValid():
            return 0
        return len(self._issues)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:  # pylint: disable=invalid-name
        """Số cột dữ liệu cố định (5 cột)."""
        if parent.isValid():
            return 0
        return len(_HEADERS)

    def headerData(  # pylint: disable=invalid-name
        self,
        section: int,
        orientation: Qt.Orientation,
        role: int = Qt.ItemDataRole.DisplayRole,
    ) -> Any:
        """Tiêu đề các cột dữ liệu."""
        if orientation == Qt.Orientation.Horizontal and role == Qt.ItemDataRole.DisplayRole:
            if 0 <= section < len(_HEADERS):
                return _HEADERS[section]
        return None

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        """Cung cấp dữ liệu, màu sắc và phông chữ cho từng ô."""
        if not index.isValid() or not 0 <= index.row() < len(self._issues):
            return None

        issue = self._issues[index.row()]
        col = index.column()
        result: Any = None

        if role == Qt.ItemDataRole.DisplayRole:
            result = self._get_display_data(issue, col)
        elif role == Qt.ItemDataRole.ForegroundRole:
            result = self._get_foreground_color(issue, col)
        elif role == Qt.ItemDataRole.FontRole and col == 0:
            result = self._font_code
        elif role == Qt.ItemDataRole.UserRole:
            result = issue
        elif role == Qt.ItemDataRole.ToolTipRole:
            result = str(issue.get("message") or "")

        return result

    @staticmethod
    def _get_display_data(issue: dict[str, Any], col: int) -> str:
        """Trích xuất chuỗi hiển thị theo cột."""
        extractors = (
            _format_location,
            lambda it: _normalize_severity(it.get("severity")),
            lambda it: _STATUS_DISPLAY_MAP.get(_normalize_status(it.get("status")), "● Chưa sửa"),
            lambda it: _TOOL_DISPLAY_MAP.get(
                str(it.get("tool") or "").strip().lower(),
                str(it.get("tool") or "").capitalize(),
            ),
            lambda it: (str(it.get("message") or "").strip().splitlines() or [""])[0],
        )
        if 0 <= col < len(extractors):
            return extractors[col](issue)
        return ""

    @staticmethod
    def _get_foreground_color(issue: dict[str, Any], col: int) -> QColor | None:
        """Lấy màu chữ theo mức độ hoặc trạng thái lỗi."""
        if col == 1:
            sev_title = _normalize_severity(issue.get("severity"))
            return QColor(SEVERITY_COLORS.get(sev_title, TEXT_MAIN))
        if col == 2:
            st_key = _normalize_status(issue.get("status"))
            color_map = {
                "open": STATUS_OPEN,
                "in_progress": STATUS_IN_PROGRESS,
                "fixed": STATUS_FIXED,
                "ignored": STATUS_IGNORED,
            }
            return QColor(color_map.get(st_key, TEXT_MAIN))
        return None

    def set_issues(self, issues: list[dict[str, Any]]) -> None:
        """Cập nhật toàn bộ danh sách lỗi và vẽ lại bảng."""
        self.beginResetModel()
        self._issues = list(issues)
        self.endResetModel()

    def get_issues(self) -> list[dict[str, Any]]:
        """Lấy danh sách lỗi hiện tại."""
        return list(self._issues)

    def get_issue(self, row: int) -> dict[str, Any] | None:
        """Lấy bản ghi lỗi tại vị trí dòng chỉ định."""
        if 0 <= row < len(self._issues):
            return self._issues[row]
        return None

    def update_issue_fields(
        self,
        issue_id: int,
        status: str | None = None,
        note: str | None = None,
        ai_analysis: str | None = None,
        ai_triage: str | None = None,
        ai_patch: str | None = None,
    ) -> bool:
        """Cập nhật trường trạng thái, ghi chú hoặc thông tin AI của lỗi theo ID."""
        for row_idx, item in enumerate(self._issues):
            curr_id = item.get("id") if item.get("id") is not None else item.get("issue_id")
            if curr_id == issue_id:
                if status is not None:
                    item["status"] = _normalize_status(status)
                if note is not None:
                    item["note"] = note
                if ai_analysis is not None:
                    item["ai_analysis"] = ai_analysis
                if ai_triage is not None:
                    item["ai_triage"] = ai_triage
                if ai_patch is not None:
                    item["ai_patch"] = ai_patch
                top_left = self.index(row_idx, 0)
                bottom_right = self.index(row_idx, len(_HEADERS) - 1)
                self.dataChanged.emit(top_left, bottom_right)
                return True
        return False

    def remove_issue(self, issue_id: int) -> bool:
        """Xóa một lỗi khỏi danh sách dữ liệu."""
        for row_idx, item in enumerate(self._issues):
            curr_id = item.get("id") if item.get("id") is not None else item.get("issue_id")
            if curr_id == issue_id:
                self.beginRemoveRows(QModelIndex(), row_idx, row_idx)
                self._issues.pop(row_idx)
                self.endRemoveRows()
                return True
        return False


class IssueFilterProxyModel(QSortFilterProxyModel):
    """
    Bộ lọc đa tiêu chí thời gian thực cho danh sách lỗi.

    Hỗ trợ lọc đồng thời theo: Mức độ, Trạng thái, Công cụ và Từ khóa tìm kiếm.
    """

    def __init__(self, parent: Any = None) -> None:
        super().__init__(parent)
        self._filter_severity: str = "all"
        self._filter_status: str = "all"
        self._filter_tool: str = "all"
        self._filter_text: str = ""

    def set_severity_filter(self, severity: str) -> None:
        """Thiết lập bộ lọc mức độ ('all', 'critical', 'high', 'medium', 'low')."""
        norm = str(severity or "all").strip().lower()
        if self._filter_severity != norm:
            self._filter_severity = norm
            self.invalidateFilter()

    def set_status_filter(self, status: str) -> None:
        """Thiết lập bộ lọc trạng thái ('all', 'open', 'in_progress', 'fixed', 'ignored')."""
        norm = _normalize_status(status) if status != "all" else "all"
        if self._filter_status != norm:
            self._filter_status = norm
            self.invalidateFilter()

    def set_tool_filter(self, tool: str) -> None:
        """Thiết lập bộ lọc công cụ ('all', 'bandit', 'pylint', 'radon', 'pip-audit', 'manual')."""
        norm = str(tool or "all").strip().lower().replace("_", "-")
        if self._filter_tool != norm:
            self._filter_tool = norm
            self.invalidateFilter()

    def set_search_text(self, text: str) -> None:
        """Thiết lập từ khóa tìm kiếm (lọc theo file, mã lỗi hoặc mô tả)."""
        norm = str(text or "").strip().lower()
        if self._filter_text != norm:
            self._filter_text = norm
            self.invalidateFilter()

    def filterAcceptsRow(  # pylint: disable=invalid-name
        self,
        source_row: int,
        source_parent: QModelIndex,
    ) -> bool:
        """Đánh giá xem dòng dữ liệu nguồn có thỏa mãn toàn bộ bộ lọc hay không."""
        source_model = self.sourceModel()
        if not source_model:
            return False

        idx = source_model.index(source_row, 0, source_parent)
        issue = source_model.data(idx, Qt.ItemDataRole.UserRole)
        if not isinstance(issue, dict):
            return False

        return (
            self._matches_severity(issue)
            and self._matches_status(issue)
            and self._matches_tool(issue)
            and self._matches_search(issue)
        )

    def _matches_severity(self, issue: dict[str, Any]) -> bool:
        """Kiểm tra điều kiện lọc mức độ nghiêm trọng."""
        if self._filter_severity == "all":
            return True
        raw_sev = str(issue.get("severity") or "").strip().lower()
        return raw_sev == self._filter_severity

    def _matches_status(self, issue: dict[str, Any]) -> bool:
        """Kiểm tra điều kiện lọc trạng thái."""
        if self._filter_status == "all":
            return True
        st = _normalize_status(issue.get("status"))
        return st == self._filter_status

    def _matches_tool(self, issue: dict[str, Any]) -> bool:
        """Kiểm tra điều kiện lọc công cụ phát hiện."""
        if self._filter_tool == "all":
            return True
        tool = str(issue.get("tool") or "").strip().lower().replace("_", "-")
        return tool == self._filter_tool

    def _matches_search(self, issue: dict[str, Any]) -> bool:
        """Kiểm tra điều kiện từ khóa tìm kiếm."""
        if not self._filter_text:
            return True
        file_path = str(issue.get("file_path") or "").lower()
        msg = str(issue.get("message") or "").lower()
        rule = str(issue.get("rule_code") or "").lower()
        tool = str(issue.get("tool") or "").lower()
        return (
            self._filter_text in file_path
            or self._filter_text in msg
            or self._filter_text in rule
            or self._filter_text in tool
        )

    def lessThan(self, left: QModelIndex, right: QModelIndex) -> bool:  # pylint: disable=invalid-name
        """Hỗ trợ sắp xếp thông minh theo mức độ nghiêm trọng hoặc chuỗi ký tự."""
        if left.column() == 1:
            src = self.sourceModel()
            issue_l = src.data(left, Qt.ItemDataRole.UserRole) if src else None
            issue_r = src.data(right, Qt.ItemDataRole.UserRole) if src else None
            if isinstance(issue_l, dict) and isinstance(issue_r, dict):
                sev_ranks = {"critical": 0, "high": 1, "medium": 2, "low": 3}
                rank_l = sev_ranks.get(str(issue_l.get("severity", "")).lower(), 9)
                rank_r = sev_ranks.get(str(issue_r.get("severity", "")).lower(), 9)
                return rank_l < rank_r
        return super().lessThan(left, right)
