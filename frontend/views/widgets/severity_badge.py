"""Widget huy hiệu mức độ nghiêm trọng (SeverityBadge) theo chuẩn SKILLS.md."""

from PyQt6.QtCore import Qt  # pylint: disable=no-name-in-module
from PyQt6.QtWidgets import QLabel  # pylint: disable=no-name-in-module

from frontend.views.theme import (
    SEV_CRITICAL,
    SEV_HIGH,
    SEV_LOW,
    SEV_MEDIUM,
)

# Cấu hình màu chữ và màu nền mờ nhạt (~12-15% alpha) cho từng mức
_BADGE_STYLES: dict[str, dict[str, str]] = {
    "Critical": {
        "text": SEV_CRITICAL,
        "bg": "#FDF2F2",
        "border": "#FBD5D5",
        "label": "Nghiêm trọng",
    },
    "High": {
        "text": SEV_HIGH,
        "bg": "#FDF4EC",
        "border": "#F8D7BE",
        "label": "Cao",
    },
    "Medium": {
        "text": SEV_MEDIUM,
        "bg": "#FEFCE8",
        "border": "#FBECA7",
        "label": "Trung bình",
    },
    "Low": {
        "text": SEV_LOW,
        "bg": "#F0F4F8",
        "border": "#D8E2EA",
        "label": "Thấp",
    },
}

_NORMALIZED_KEYS: dict[str, str] = {
    "critical": "Critical",
    "nghiêm trọng": "Critical",
    "nghiem trong": "Critical",
    "high": "High",
    "cao": "High",
    "medium": "Medium",
    "trung bình": "Medium",
    "trung binh": "Medium",
    "low": "Low",
    "thấp": "Low",
    "thap": "Low",
    "info": "Low",
}


class SeverityBadge(QLabel):  # pylint: disable=too-few-public-methods
    """
    Huy hiệu hiển thị mức độ nghiêm trọng của lỗi mã nguồn.

    - Bo góc cố định 3px, nền mờ nhạt (alpha ~15%), chữ màu đậm chuẩn.
    - Không dùng icon emoji (❌, ⚠️) theo đúng tiêu chuẩn SKILLS.md.
    """

    def __init__(
        self,
        severity: str = "Low",
        show_vietnamese: bool = True,
        parent: QLabel | None = None,
    ) -> None:
        super().__init__(parent)
        self.show_vietnamese = show_vietnamese
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setFixedHeight(22)
        self.set_severity(severity)

    def set_severity(self, severity: str) -> None:
        """Cập nhật mức độ nghiêm trọng và định dạng giao diện tương ứng."""
        clean_key = str(severity).strip().lower()
        canonical_key = _NORMALIZED_KEYS.get(clean_key, "Low")
        style_info = _BADGE_STYLES[canonical_key]

        display_text = (
            style_info["label"] if self.show_vietnamese else canonical_key
        )
        self.setText(display_text)

        self.setStyleSheet(
            f"background-color: {style_info['bg']};"
            f"color: {style_info['text']};"
            f"border: 1px solid {style_info['border']};"
            f"border-radius: 3px;"
            f"padding: 2px 8px;"
            f"font-size: 11px;"
            f"font-weight: 600;"
        )
