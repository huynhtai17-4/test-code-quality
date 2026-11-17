"""Data Model quản lý danh sách các phiên phân tích trong lịch sử kiểm định."""

from __future__ import annotations

import json
from typing import Any

from PyQt6.QtCore import (  # pylint: disable=no-name-in-module
    QAbstractTableModel,
    QModelIndex,
    Qt,
)
from PyQt6.QtGui import QColor, QFont  # pylint: disable=no-name-in-module

from frontend.views.theme import (
    GRADE_COLORS,
    SEV_CRITICAL,
    SEV_HIGH,
    TEXT_MAIN,
    TEXT_MUTED,
    format_datetime,
    lay_font_code,
)

_HEADERS = (
    "Mã phiên",
    "Thời gian",
    "Điểm số",
    "Xếp loại",
    "Tổng lỗi",
    "Nghiêm trọng (C / H)",
    "Khác (M / L)",
)


def _format_short_date(raw_dt: Any) -> str:
    """Định dạng ngày ngắn dd/MM cho biểu đồ."""
    if not raw_dt:
        return ""
    full_str = format_datetime(raw_dt)
    if " " in full_str:
        return full_str.split(" ")[0]
    return full_str


def _parse_summary(summary_data: Any) -> dict[str, Any]:
    """Phân tích trường summary sang dictionary an toàn."""
    if isinstance(summary_data, dict):
        return summary_data
    if isinstance(summary_data, str) and summary_data.strip():
        try:
            parsed = json.loads(summary_data)
            if isinstance(parsed, dict):
                return parsed
        except (json.JSONDecodeError, TypeError):
            pass
    return {}


def _get_severity_counts(session: dict[str, Any]) -> tuple[int, int, int, int]:
    """Trích xuất bộ (Critical, High, Medium, Low) từ session."""
    summary = _parse_summary(session.get("summary"))
    dist = summary.get("severity_distribution", {})

    crit = int(dist.get("Critical", 0))
    high = int(dist.get("High", 0))
    med = int(dist.get("Medium", 0))
    low = int(dist.get("Low", 0))

    if crit == 0 and high == 0 and session.get("security_issues_count"):
        high = int(session.get("security_issues_count") or 0)

    return crit, high, med, low


def _get_criteria_scores(session: dict[str, Any]) -> dict[str, float]:
    """Trích xuất điểm số của 5 tiêu chí từ session summary hoặc các chỉ số trực tiếp."""
    summary = _parse_summary(session.get("summary"))
    scores = summary.get("criteria_scores", {})

    return {
        "complexity": float(
            scores.get("complexity") or session.get("maintainability_index") or 0.0
        ),
        "security": float(scores.get("security") or 0.0),
        "pylint": float(scores.get("pylint") or session.get("pylint_score") or 0.0),
        "health": float(scores.get("health") or 0.0),
        "dependency": float(scores.get("dependency") or 0.0),
    }


class HistoryTableModel(QAbstractTableModel):
    """
    Model dữ liệu hiển thị danh sách các phiên quét trong lịch sử.

    Bao gồm 7 cột:
    0: Mã phiên (#ID)
    1: Thời gian (dd/MM/yyyy HH:mm)
    2: Điểm số (ví dụ: 79.3 / 100)
    3: Xếp loại (A, B, C, D, F kèm màu GRADE_*)
    4: Tổng lỗi
    5: Nghiêm trọng (C: X | H: Y)
    6: Khác (M: X | L: Y)
    """

    def __init__(self, sessions: list[dict[str, Any]] | None = None) -> None:
        super().__init__()
        self._sessions: list[dict[str, Any]] = []
        self._font_code: QFont = lay_font_code(11)
        if sessions:
            self.set_sessions(sessions)

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:  # pylint: disable=invalid-name
        """Số dòng trong bảng dữ liệu."""
        if parent.isValid():
            return 0
        return len(self._sessions)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:  # pylint: disable=invalid-name
        """Số lượng 7 cột dữ liệu lịch sử."""
        return 0 if parent.isValid() else len(_HEADERS)

    def headerData(  # pylint: disable=invalid-name
        self,
        section: int,
        orientation: Qt.Orientation,
        role: int = Qt.ItemDataRole.DisplayRole,
    ) -> Any:
        """Cung cấp tiêu đề cột theo phương ngang."""
        if orientation == Qt.Orientation.Horizontal and role == Qt.ItemDataRole.DisplayRole:
            if 0 <= section < len(_HEADERS):
                return _HEADERS[section]
        return None

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        """Cung cấp nội dung, màu sắc, phông chữ và căn lề cho các ô."""
        if not index.isValid() or not 0 <= index.row() < len(self._sessions):
            return None

        session = self._sessions[index.row()]
        col = index.column()
        result: Any = None

        if role == Qt.ItemDataRole.DisplayRole:
            result = self._get_display_data(session, col)
        elif role == Qt.ItemDataRole.ForegroundRole:
            result = self._get_foreground_color(session, col)
        elif role == Qt.ItemDataRole.FontRole and col in (0, 5, 6):
            result = self._font_code
        elif role == Qt.ItemDataRole.TextAlignmentRole:
            if col in (2, 4):
                result = int(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            elif col in (0, 3, 5, 6):
                result = int(Qt.AlignmentFlag.AlignCenter)
        elif role == Qt.ItemDataRole.UserRole:
            result = session

        return result

    @staticmethod
    def _get_display_data(session: dict[str, Any], col: int) -> str:
        """Trích xuất nội dung văn bản hiển thị theo cột."""
        crit, high, med, low = _get_severity_counts(session)

        extractors = (
            lambda s: f"#{s.get('id', '—')}",
            lambda s: format_datetime(s.get("started_at") or s.get("completed_at")),
            lambda s: (
                f"{float(s['total_score']):.1f} / 100" if s.get("total_score") is not None else "—"
            ),
            lambda s: str(s.get("grade") or "—").upper(),
            lambda s: str(s.get("total_issues") if s.get("total_issues") is not None else 0),
            lambda _s: f"C: {crit} | H: {high}",
            lambda _s: f"M: {med} | L: {low}",
        )
        if 0 <= col < len(extractors):
            return extractors[col](session)
        return ""

    @staticmethod
    def _get_foreground_color(session: dict[str, Any], col: int) -> QColor | None:
        """Cung cấp màu sắc chữ trực quan theo xếp loại hoặc mức độ nghiêm trọng."""
        if col == 3:
            grade = str(session.get("grade") or "").upper()
            return QColor(GRADE_COLORS.get(grade, TEXT_MAIN))
        if col == 5:
            crit, high, _, _ = _get_severity_counts(session)
            if crit > 0:
                return QColor(SEV_CRITICAL)
            if high > 0:
                return QColor(SEV_HIGH)
            return QColor(TEXT_MUTED)
        return None

    def set_sessions(self, sessions: list[dict[str, Any]]) -> None:
        """Nạp danh sách phiên quét mới và tự động sắp xếp mới nhất lên đầu."""
        self.beginResetModel()
        self._sessions = list(sessions)
        self._sessions.sort(
            key=lambda item: (
                str(item.get("started_at") or item.get("completed_at") or ""),
                int(item.get("id") or 0),
            ),
            reverse=True,
        )
        self.endResetModel()

    def get_sessions(self) -> list[dict[str, Any]]:
        """Lấy danh sách phiên quét hiện tại."""
        return list(self._sessions)

    def get_session(self, row: int) -> dict[str, Any] | None:
        """Lấy bản ghi phiên quét tại vị trí chỉ định."""
        if 0 <= row < len(self._sessions):
            return self._sessions[row]
        return None

    def remove_session(self, session_id: int) -> bool:
        """Xóa một phiên quét khỏi model theo session_id."""
        for row_idx, item in enumerate(self._sessions):
            if item.get("id") == session_id:
                self.beginRemoveRows(QModelIndex(), row_idx, row_idx)
                self._sessions.pop(row_idx)
                self.endRemoveRows()
                return True
        return False
