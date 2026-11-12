"""Delegate vẽ huy hiệu dạng viên thuốc (Pill Badge) theo phong cách ArtCraft cho QTableView."""

from PyQt6.QtCore import QModelIndex, QRectF, Qt  # pylint: disable=no-name-in-module
from PyQt6.QtGui import (  # pylint: disable=no-name-in-module
    QBrush,
    QColor,
    QFont,
    QPainter,
    QPen,
)
from PyQt6.QtWidgets import (  # pylint: disable=no-name-in-module
    QStyle,
    QStyledItemDelegate,
    QStyleOptionViewItem,
)

from frontend.views.theme import lay_font_code

_SEV_PILL_CONFIG: dict[str, dict[str, str]] = {
    "Critical": {"bg": "#FEE2E2", "border": "#FCA5A5", "text": "#991B1B"},
    "High": {"bg": "#FFEDD5", "border": "#FDBA74", "text": "#9A3412"},
    "Medium": {"bg": "#FEF3C7", "border": "#FCD34D", "text": "#92400E"},
    "Low": {"bg": "#E0F2FE", "border": "#BAE6FD", "text": "#075985"},
}

_STATUS_PILL_CONFIG: dict[str, dict[str, str]] = {
    "chưa sửa": {"bg": "#F1F5F9", "border": "#CBD5E1", "text": "#475569", "icon": "•"},
    "đang sửa": {"bg": "#EFF6FF", "border": "#BFDBFE", "text": "#1D4ED8", "icon": "⚙"},
    "đã sửa": {"bg": "#ECFDF5", "border": "#A7F3D0", "text": "#047857", "icon": "✔"},
    "báo sai": {"bg": "#F3F4F6", "border": "#E5E7EB", "text": "#6B7280", "icon": "✕"},
}

_TOOL_PILL_CONFIG: dict[str, dict[str, str]] = {
    "pip-audit": {"bg": "#F8FAFC", "border": "#E2E8F0", "text": "#334155"},
    "bandit": {"bg": "#FFF1F2", "border": "#FFE4E6", "text": "#BE123C"},
    "radon": {"bg": "#F0FDF4", "border": "#DCFCE7", "text": "#15803D"},
    "pylint": {"bg": "#EFF6FF", "border": "#DBEAFE", "text": "#1D4ED8"},
    "flake8": {"bg": "#FAF5FF", "border": "#F3E8FF", "text": "#6B21A8"},
}

_GRADE_PILL_CONFIG: dict[str, dict[str, str]] = {
    "A": {"bg": "#ECFDF5", "border": "#A7F3D0", "text": "#047857"},
    "B": {"bg": "#EFF6FF", "border": "#BFDBFE", "text": "#1D4ED8"},
    "C": {"bg": "#FEF3C7", "border": "#FCD34D", "text": "#92400E"},
    "D": {"bg": "#FFEDD5", "border": "#FDBA74", "text": "#9A3412"},
    "F": {"bg": "#FEE2E2", "border": "#FCA5A5", "text": "#991B1B"},
}


class PillBadgeDelegate(QStyledItemDelegate):  # pylint: disable=too-few-public-methods
    """
    Delegate tùy biến vẽ các ô Mức độ, Trạng thái và Công cụ thành huy hiệu pill.

    - Nền bo góc 4px với viền nhẹ và màu chữ tương phản cao.
    - Duy trì hiệu ứng hover và selection của bảng.
    """

    def __init__(self, mode: str = "severity", parent: object | None = None) -> None:
        super().__init__(parent)  # type: ignore[arg-type]
        self.mode = mode
        self._font_badge: QFont = lay_font_code(10)
        self._font_badge.setBold(True)

    def paint(  # pylint: disable=too-many-locals
        self,
        painter: QPainter | None,
        option: QStyleOptionViewItem,
        index: QModelIndex,
    ) -> None:
        """Vẽ ô hiển thị dạng viên thuốc hoặc mặc định."""
        if painter is None:
            return

        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # 1. Vẽ nền hàng (hover hoặc select)
        if option.state & QStyle.StateFlag.State_Selected:
            painter.fillRect(option.rect, QColor("#F1F5F9"))
        elif option.state & QStyle.StateFlag.State_MouseOver:
            painter.fillRect(option.rect, QColor("#F8FAFC"))

        # 2. Vẽ đường kẻ ngang phân cách hàng
        painter.setPen(QPen(QColor("#F1F5F9"), 1))
        p1 = option.rect.bottomLeft()
        p2 = option.rect.bottomRight()
        painter.drawLine(p1.x(), p1.y(), p2.x(), p2.y())

        text = str(index.data(Qt.ItemDataRole.DisplayRole) or "").strip()
        pill_cfg = self._get_config_for_text(text)

        if not pill_cfg:
            painter.restore()
            super().paint(painter, option, index)
            return

        # 3. Tính toán kích thước huy hiệu pill
        painter.setFont(self._font_badge)
        metrics = painter.fontMetrics()
        text_w = metrics.horizontalAdvance(text)
        pill_w = max(text_w + 16, 60)
        pill_h = 22

        cell_rect = option.rect
        pill_x = cell_rect.x() + 8
        pill_y = cell_rect.y() + (cell_rect.height() - pill_h) / 2
        pill_rect = QRectF(pill_x, pill_y, pill_w, pill_h)

        # 4. Vẽ nền và viền pill
        painter.setBrush(QBrush(QColor(pill_cfg["bg"])))
        painter.setPen(QPen(QColor(pill_cfg["border"]), 1))
        painter.drawRoundedRect(pill_rect, 4.0, 4.0)

        # 5. Vẽ chữ căn giữa trong pill
        painter.setPen(QPen(QColor(pill_cfg["text"])))
        painter.drawText(pill_rect, Qt.AlignmentFlag.AlignCenter, text)

        painter.restore()

    def _get_config_for_text(self, text: str) -> dict[str, str] | None:
        """Trích xuất bảng cấu hình màu sắc tương ứng."""
        clean = text.lower().replace("•", "").replace("⚙", "").replace("✔", "").replace("✕", "").strip()

        if self.mode == "severity":
            for k, cfg in _SEV_PILL_CONFIG.items():
                if k.lower() == clean:
                    return cfg
        elif self.mode == "status":
            for k, cfg in _STATUS_PILL_CONFIG.items():
                if k in clean:
                    return cfg
        elif self.mode == "tool":
            for k, cfg in _TOOL_PILL_CONFIG.items():
                if k in clean:
                    return cfg
        elif self.mode == "grade":
            upper_clean = text.strip().upper()
            if upper_clean in _GRADE_PILL_CONFIG:
                return _GRADE_PILL_CONFIG[upper_clean]

        return None
