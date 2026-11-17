"""Component giao diện hỗ trợ điều chỉnh trọng số đánh giá chất lượng mã nguồn."""

from __future__ import annotations

from typing import Any

from PyQt6.QtCore import Qt  # pylint: disable=no-name-in-module
from PyQt6.QtWidgets import (  # pylint: disable=no-name-in-module
    QDoubleSpinBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from frontend.views.theme import (
    BORDER_SOFT,
    TEN_TIEU_CHI,
    TEXT_MAIN,
    TEXT_MUTED,
    TRONG_SO_MAC_DINH,
)

_CRITERIA_SUBTITLES: dict[str, str] = {
    "complexity": "Độ phức tạp Cyclomatic & chỉ số bảo trì (Radon CC/MI)",
    "security": "Lỗ hổng bảo mật & mã độc tiềm ẩn (Bandit)",
    "pylint": "Quy chuẩn cú pháp, cấu trúc & PEP8 (Pylint)",
    "health": "Tần suất commit, hoạt động & tài liệu (Git Health)",
    "dependency": "Lỗ hổng an toàn trong các thư viện phụ thuộc (CVE)",
}


def create_separator() -> QFrame:
    """Tạo đường phân cách mỏng 1px phẳng theo chuẩn giao diện."""
    line = QFrame()
    line.setFrameShape(QFrame.Shape.HLine)
    line.setFrameShadow(QFrame.Shadow.Plain)
    line.setStyleSheet(f"color: {BORDER_SOFT}; background-color: {BORDER_SOFT}; max-height: 1px;")
    return line


def create_criterion_row(
    key: str, on_changed: Any
) -> tuple[QWidget, QDoubleSpinBox]:
    """Tạo một dòng cấu hình cho từng tiêu chí đánh giá chất lượng."""
    row_widget = QWidget()
    row_layout = QHBoxLayout(row_widget)
    row_layout.setContentsMargins(0, 4, 0, 4)
    row_layout.setSpacing(12)

    name_col = QVBoxLayout()
    name_col.setSpacing(2)
    name_lbl = QLabel(TEN_TIEU_CHI.get(key, key))
    name_lbl.setStyleSheet(f"font-size: 13px; font-weight: 600; color: {TEXT_MAIN};")
    sub_lbl = QLabel(_CRITERIA_SUBTITLES.get(key, ""))
    sub_lbl.setStyleSheet(f"font-size: 11px; color: {TEXT_MUTED};")
    name_col.addWidget(name_lbl)
    name_col.addWidget(sub_lbl)

    stepper = QFrame()
    stepper.setObjectName("CriteriaStepper")
    stepper.setFixedSize(116, 30)
    stepper_layout = QHBoxLayout(stepper)
    stepper_layout.setContentsMargins(0, 0, 0, 0)
    stepper_layout.setSpacing(0)

    btn_minus = QPushButton("−")
    btn_minus.setObjectName("StepperMinus")
    btn_minus.setFixedSize(30, 30)
    btn_minus.setCursor(Qt.CursorShape.PointingHandCursor)

    spin = QDoubleSpinBox()
    spin.setObjectName("StepperSpin")
    spin.setRange(0.00, 1.00)
    spin.setSingleStep(0.05)
    spin.setDecimals(2)
    spin.setValue(TRONG_SO_MAC_DINH.get(key, 0.20))
    spin.valueChanged.connect(on_changed)
    spin.setFixedSize(56, 30)
    spin.setAlignment(Qt.AlignmentFlag.AlignCenter)

    btn_plus = QPushButton("+")
    btn_plus.setObjectName("StepperPlus")
    btn_plus.setFixedSize(30, 30)
    btn_plus.setCursor(Qt.CursorShape.PointingHandCursor)

    btn_minus.clicked.connect(
        lambda checked=False, s=spin: s.setValue(max(0.0, round(s.value() - 0.05, 2)))
    )
    btn_plus.clicked.connect(
        lambda checked=False, s=spin: s.setValue(min(1.0, round(s.value() + 0.05, 2)))
    )

    stepper_layout.addWidget(btn_minus)
    stepper_layout.addWidget(spin)
    stepper_layout.addWidget(btn_plus)

    row_layout.addLayout(name_col, 1)
    row_layout.addWidget(stepper, 0, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
    return row_widget, spin


def create_total_weights_card(lbl_val: QLabel, lbl_status: QLabel) -> QFrame:
    """Tạo thẻ tóm tắt và kiểm tra tính hợp lệ của tổng 5 trọng số."""
    card = QFrame()
    card.setStyleSheet(
        "background-color: #F8FAFC; border: 1px solid #E2E5E9; border-radius: 4px;"
    )
    box = QHBoxLayout(card)
    box.setContentsMargins(12, 10, 12, 10)
    box.setSpacing(14)

    lbl_val.setStyleSheet(
        f"font-size: 13px; font-weight: 600; color: {TEXT_MAIN}; "
        "background: transparent; border: none;"
    )
    lbl_status.setStyleSheet("font-size: 13px; background: transparent; border: none;")

    box.addWidget(lbl_val)
    box.addWidget(lbl_status, 1)
    return card
