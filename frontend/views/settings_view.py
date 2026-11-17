"""Màn hình Cài đặt hệ thống (SettingsView) theo chuẩn kỹ thuật SKILLS.md."""

import sys
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# pylint: disable=wrong-import-position,no-name-in-module
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QDoubleSpinBox,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from frontend import config
from frontend.controllers.settings_controller import SettingsController
from frontend.views.components.settings_stepper import (
    create_criterion_row,
    create_separator,
    create_total_weights_card,
)
from frontend.views.theme import (
    GRADE_A,
    GRADE_F,
    SEV_CRITICAL,
    TEXT_MAIN,
    TEXT_MUTED,
    TRONG_SO_MAC_DINH,
)
from frontend.views.widgets.page_header import PageHeader
from frontend.views.widgets.panel import Panel

_CRITERIA_KEYS = ("complexity", "security", "pylint", "health", "dependency")

_BACKEND_KEY_MAP = {
    "radon_mi": "complexity",
    "radon_cc": "complexity",
    "bandit": "security",
    "pylint": "pylint",
    "pip_audit": "dependency",
    "pip-audit": "dependency",
}


class SettingsView(QWidget):  # pylint: disable=too-many-instance-attributes
    """
    Màn hình Cài đặt hệ thống (SettingsView).

    Quản lý cấu hình kết nối TCP Socket Server và bảng trọng số chấm điểm chất lượng mã nguồn.
    """

    status_message = pyqtSignal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._controller = SettingsController(self)
        self._controller.ping_result.connect(self._on_ping_result)
        self._controller.configs_loaded.connect(self._on_configs_loaded)
        self._controller.configs_saved.connect(self._on_configs_saved)
        self._controller.status_message.connect(self.status_message.emit)

        self.ip_edit = QLineEdit(config.SERVER_HOST)
        self.port_spin = QSpinBox()
        self.port_spin.setObjectName("PortSpin")
        self.btn_ping = QPushButton("Kiểm tra kết nối")
        self.lbl_ping_result = QLabel("")

        self.weight_spins: dict[str, QDoubleSpinBox] = {}
        self.lbl_total_value = QLabel("Tổng hiện tại: 1.00")
        self.lbl_total_status = QLabel("● Tổng trọng số hợp lệ (1.00)")

        self.btn_reset = QPushButton("Khôi phục mặc định")
        self.btn_save = QPushButton("Lưu thay đổi")

        self._init_ui()
        self._on_weight_changed()

    def _init_ui(self) -> None:
        """Xây dựng bố cục giao diện trong QScrollArea phẳng căn lề trái."""
        self.setObjectName("SettingsView")
        self.setStyleSheet(
            "QWidget#SettingsView, QWidget#SettingsContent { background-color: #F4F5F7; }"
        )

        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea(self)
        scroll.setObjectName("SettingsScroll")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet(
            "QScrollArea#SettingsScroll, "
            "QScrollArea#SettingsScroll > QWidget, "
            "QScrollArea#SettingsScroll > QWidget > QWidget { "
            "background-color: #F4F5F7; border: none; }"
        )

        content_widget = QWidget()
        content_widget.setObjectName("SettingsContent")
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(32, 28, 32, 28)
        content_layout.setSpacing(16)
        content_layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)

        form_container = QWidget()
        form_container.setObjectName("SettingsFormContainer")
        form_container.setMaximumWidth(720)
        form_layout = QVBoxLayout(form_container)
        form_layout.setContentsMargins(0, 0, 0, 0)
        form_layout.setSpacing(16)

        header = PageHeader(
            title="Cài đặt",
            subtitle="Thiết lập kết nối máy chủ phân tích và cấu hình trọng số đánh giá",
            parent=form_container,
        )
        form_layout.addWidget(header)
        form_layout.addWidget(self._create_server_section())
        form_layout.addWidget(self._create_weights_section())
        form_layout.addLayout(self._create_action_buttons())

        content_layout.addWidget(form_container)
        scroll.setWidget(content_widget)
        root_layout.addWidget(scroll)

    def _create_server_section(self) -> QWidget:
        """Tạo thẻ Panel cấu hình kết nối máy chủ Socket."""
        panel = Panel()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(20, 18, 20, 20)
        layout.setSpacing(14)

        header_box = QVBoxLayout()
        header_box.setSpacing(4)
        title_lbl = QLabel("KẾT NỐI MÁY CHỦ")
        title_lbl.setStyleSheet(
            f"font-size: 13px; font-weight: 700; color: {TEXT_MAIN}; letter-spacing: 0.5px;"
        )
        desc_lbl = QLabel(
            "Cấu hình địa chỉ IP và cổng giao tiếp TCP Socket với máy chủ Backend phân tích"
        )
        desc_lbl.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 12px;")
        header_box.addWidget(title_lbl)
        header_box.addWidget(desc_lbl)
        layout.addLayout(header_box)
        layout.addWidget(create_separator())

        form = QFormLayout()
        form.setSpacing(12)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)

        self.ip_edit.setPlaceholderText("ví dụ: 127.0.0.1")
        self.port_spin.setRange(1024, 65535)
        self.port_spin.setValue(config.SERVER_PORT)

        form.addRow("Địa chỉ IP:", self.ip_edit)
        form.addRow("Cổng kết nối:", self.port_spin)
        layout.addLayout(form)

        ping_layout = QHBoxLayout()
        ping_layout.setSpacing(12)

        self.btn_ping.clicked.connect(self._on_ping_clicked)
        self.lbl_ping_result.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 12px;")

        ping_layout.addWidget(self.btn_ping)
        ping_layout.addWidget(self.lbl_ping_result, 1)
        layout.addLayout(ping_layout)

        return panel

    def _create_weights_section(self) -> QWidget:
        """Tạo thẻ Panel thiết lập trọng số các tiêu chí đánh giá."""
        panel = Panel()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(20, 18, 20, 20)
        layout.setSpacing(14)

        header_box = QVBoxLayout()
        header_box.setSpacing(4)
        title_lbl = QLabel("TRỌNG SỐ TIÊU CHÍ ĐÁNH GIÁ")
        title_lbl.setStyleSheet(
            f"font-size: 13px; font-weight: 700; color: {TEXT_MAIN}; letter-spacing: 0.5px;"
        )
        desc_lbl = QLabel(
            "Điều chỉnh tỷ trọng đóng góp của từng tiêu chí vào điểm tổng kết (thang 0–100). "
            "Tổng 5 trọng số phải bằng đúng 1.00."
        )
        desc_lbl.setWordWrap(True)
        desc_lbl.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 12px;")
        header_box.addWidget(title_lbl)
        header_box.addWidget(desc_lbl)
        layout.addLayout(header_box)
        layout.addWidget(create_separator())

        form_layout = QVBoxLayout()
        form_layout.setSpacing(8)

        for idx, key in enumerate(_CRITERIA_KEYS):
            row_widget, spin = create_criterion_row(key, self._on_weight_changed)
            self.weight_spins[key] = spin
            form_layout.addWidget(row_widget)

            if idx < len(_CRITERIA_KEYS) - 1:
                form_layout.addWidget(create_separator())

        layout.addLayout(form_layout)
        layout.addWidget(create_total_weights_card(self.lbl_total_value, self.lbl_total_status))
        return panel

    def _create_action_buttons(self) -> QHBoxLayout:
        """Tạo hàng nút thao tác lưu cấu hình và khôi phục mặc định."""
        layout = QHBoxLayout()
        layout.setSpacing(12)

        self.btn_reset.clicked.connect(self._on_reset_clicked)

        self.btn_save.setProperty("role", "primary")
        self.btn_save.clicked.connect(self._on_save_clicked)

        layout.addWidget(self.btn_reset)
        layout.addStretch()
        layout.addWidget(self.btn_save)

        return layout

    def _on_weight_changed(self) -> None:
        """Tính toán tổng trọng số và xác thực điều kiện bật nút Lưu."""
        total = round(sum(spin.value() for spin in self.weight_spins.values()), 2)
        self.lbl_total_value.setText(f"Tổng hiện tại: {total:.2f}")

        if abs(total - 1.00) <= 0.001:
            self.lbl_total_status.setText("● Tổng trọng số hợp lệ (1.00)")
            self.lbl_total_status.setStyleSheet(
                f"color: {GRADE_A}; font-size: 13px; background: transparent; border: none;"
            )
            self.btn_save.setEnabled(True)
        else:
            self.lbl_total_status.setText(
                f"Tổng trọng số đang là {total:.2f}. Cần bằng đúng 1.00 để lưu."
            )
            self.lbl_total_status.setStyleSheet(
                f"color: {SEV_CRITICAL}; font-size: 13px; background: transparent; border: none;"
            )
            self.btn_save.setEnabled(False)

    def _on_ping_clicked(self) -> None:
        """Thực hiện kiểm tra kết nối mạng tới Socket Server qua Controller."""
        host = self.ip_edit.text().strip() or config.SERVER_HOST
        port = self.port_spin.value()

        self.btn_ping.setEnabled(False)
        self.lbl_ping_result.setText("Đang kiểm tra kết nối...")
        self.lbl_ping_result.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 13px;")
        self._controller.ping_server(host, port)

    def _on_ping_result(self, is_ok: bool, message: str) -> None:
        """Cập nhật giao diện kết quả kiểm tra kết nối."""
        self.btn_ping.setEnabled(True)
        self.lbl_ping_result.setText(message)
        color = GRADE_A if is_ok else GRADE_F
        self.lbl_ping_result.setStyleSheet(f"color: {color}; font-size: 13px;")

    def _on_reset_clicked(self) -> None:
        """Khôi phục các ô trọng số về giá trị mặc định chuẩn."""
        for key in _CRITERIA_KEYS:
            if key in self.weight_spins:
                self.weight_spins[key].setValue(TRONG_SO_MAC_DINH.get(key, 0.20))
        self.status_message.emit("Đã khôi phục trọng số về giá trị mặc định.")

    def _on_save_clicked(self) -> None:
        """Lưu các giá trị trọng số vào cơ sở dữ liệu qua Controller."""
        weights_dict = {key: spin.value() for key, spin in self.weight_spins.items()}
        self.btn_save.setEnabled(False)
        self._controller.save_configs(weights_dict)

    def _on_configs_saved(self, _success: bool, _message: str) -> None:
        """Khôi phục trạng thái nút lưu sau khi Controller xử lý xong."""
        self.btn_save.setEnabled(True)

    def load_current_configs(self) -> None:
        """Kích hoạt Controller tải cấu hình trọng số từ backend."""
        self._controller.load_current_configs()

    def _on_configs_loaded(self, configs: list[dict[str, Any]]) -> None:
        """Cập nhật các ô nhập liệu theo dữ liệu từ Controller."""
        for item in configs:
            raw_key = str(item.get("metric_key") or "").strip().lower()
            target_key = _BACKEND_KEY_MAP.get(raw_key, raw_key)
            raw_val = item.get("weight")
            if target_key in self.weight_spins and raw_val is not None:
                val = float(raw_val)
                if val > 1.0:
                    val /= 100.0
                self.weight_spins[target_key].setValue(val)

    def get_weights(self) -> dict[str, float]:
        """Lấy từ điển trọng số hiện tại của 5 tiêu chí."""
        return {key: spin.value() for key, spin in self.weight_spins.items()}

    def set_weights(self, weights: dict[str, float]) -> None:
        """Thiết lập trọng số thủ công cho các tiêu chí."""
        for key, val in weights.items():
            if key in self.weight_spins:
                self.weight_spins[key].setValue(val)
