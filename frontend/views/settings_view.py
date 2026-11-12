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
    QApplication,
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
from frontend.network import api
from frontend.views.theme import (
    BORDER_SOFT,
    GRADE_A,
    GRADE_F,
    SEV_CRITICAL,
    TEN_TIEU_CHI,
    TEXT_MAIN,
    TEXT_MUTED,
    TRONG_SO_MAC_DINH,
    load_stylesheet,
)
from frontend.views.widgets.page_header import PageHeader
from frontend.views.widgets.panel import Panel
from frontend.workers.request_worker import RequestWorker

_CRITERIA_KEYS = ("complexity", "security", "pylint", "health", "dependency")

_CRITERIA_SUBTITLES: dict[str, str] = {
    "complexity": "Độ phức tạp Cyclomatic & chỉ số bảo trì (Radon CC/MI)",
    "security": "Lỗ hổng bảo mật & mã độc tiềm ẩn (Bandit)",
    "pylint": "Quy chuẩn cú pháp, cấu trúc & PEP8 (Pylint)",
    "health": "Tần suất commit, hoạt động & tài liệu (Git Health)",
    "dependency": "Lỗ hổng an toàn trong các thư viện phụ thuộc (CVE)",
}

_BACKEND_KEY_MAP = {
    "radon_mi": "complexity",
    "radon_cc": "complexity",
    "bandit": "security",
    "pylint": "pylint",
    "pip_audit": "dependency",
    "pip-audit": "dependency",
}


def _create_separator() -> QFrame:
    """Tạo đường phân cách mỏng 1px phẳng theo chuẩn giao diện."""
    line = QFrame()
    line.setFrameShape(QFrame.Shape.HLine)
    line.setFrameShadow(QFrame.Shadow.Plain)
    line.setStyleSheet(f"color: {BORDER_SOFT}; background-color: {BORDER_SOFT}; max-height: 1px;")
    return line


def _create_criterion_row(
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


def _create_total_weights_card(lbl_val: QLabel, lbl_status: QLabel) -> QFrame:
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


class SettingsView(QWidget):  # pylint: disable=too-many-instance-attributes
    """
    Màn hình Cài đặt hệ thống (SettingsView).

    Quản lý cấu hình kết nối TCP Socket Server và bảng trọng số chấm điểm chất lượng mã nguồn.
    """

    status_message = pyqtSignal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._active_worker: RequestWorker | None = None

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
        layout.addWidget(_create_separator())

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
        layout.addWidget(_create_separator())

        form_layout = QVBoxLayout()
        form_layout.setSpacing(8)

        for idx, key in enumerate(_CRITERIA_KEYS):
            row_widget, spin = _create_criterion_row(key, self._on_weight_changed)
            self.weight_spins[key] = spin
            form_layout.addWidget(row_widget)

            if idx < len(_CRITERIA_KEYS) - 1:
                form_layout.addWidget(_create_separator())

        layout.addLayout(form_layout)
        layout.addWidget(_create_total_weights_card(self.lbl_total_value, self.lbl_total_status))
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
        """Thực hiện kiểm tra kết nối mạng tới Socket Server qua RequestWorker."""
        host = self.ip_edit.text().strip() or config.SERVER_HOST
        port = self.port_spin.value()

        self.btn_ping.setEnabled(False)
        self.lbl_ping_result.setText("Đang kiểm tra kết nối...")
        self.lbl_ping_result.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 13px;")

        def _do_ping() -> dict[str, Any]:
            is_ok = api.ping_server(host=host, port=port, timeout=3.0)
            return {"status": "ok" if is_ok else "error"}

        worker = RequestWorker(_do_ping, parent=self)
        self._active_worker = worker

        def _on_finished(_res: dict[str, Any]) -> None:
            self.btn_ping.setEnabled(True)
            self.lbl_ping_result.setText("● Kết nối thành công tới máy chủ")
            self.lbl_ping_result.setStyleSheet(f"color: {GRADE_A}; font-size: 13px;")
            self.status_message.emit("Kết nối máy chủ Backend thành công.")

        def _on_failed(_err: str) -> None:
            self.btn_ping.setEnabled(True)
            self.lbl_ping_result.setText(
                "● Không thể kết nối tới máy chủ (kiểm tra lại cổng và tiến trình Backend)"
            )
            self.lbl_ping_result.setStyleSheet(f"color: {GRADE_F}; font-size: 13px;")
            self.status_message.emit("Không thể kết nối tới máy chủ.")

        worker.finished.connect(_on_finished)
        worker.failed.connect(_on_failed)
        worker.start()

    def _on_reset_clicked(self) -> None:
        """Khôi phục các ô trọng số về giá trị mặc định chuẩn."""
        for key in _CRITERIA_KEYS:
            if key in self.weight_spins:
                self.weight_spins[key].setValue(TRONG_SO_MAC_DINH.get(key, 0.20))
        self.status_message.emit("Đã khôi phục trọng số về giá trị mặc định.")

    def _on_save_clicked(self) -> None:
        """Lưu các giá trị trọng số vào cơ sở dữ liệu qua RequestWorker."""
        weights_dict = {key: spin.value() for key, spin in self.weight_spins.items()}

        self.btn_save.setEnabled(False)
        worker = RequestWorker(api.update_config, weights_dict, parent=self)
        self._active_worker = worker

        def _on_finished(_res: dict[str, Any]) -> None:
            self.btn_save.setEnabled(True)
            self.status_message.emit("Đã lưu cấu hình trọng số thành công.")

        def _on_failed(err_msg: str) -> None:
            self.btn_save.setEnabled(True)
            self.status_message.emit(f"Lỗi khi lưu cấu hình trọng số: {err_msg}")

        worker.finished.connect(_on_finished)
        worker.failed.connect(_on_failed)
        worker.start()

    def load_current_configs(self) -> None:
        """Tải cấu hình trọng số thực tế từ backend và cập nhật các ô nhập liệu."""
        worker = RequestWorker(api.get_config, parent=self)
        self._active_worker = worker

        def _on_loaded(res: dict[str, Any]) -> None:
            configs = res.get("data")
            if isinstance(configs, list):
                for item in configs:
                    raw_key = str(item.get("metric_key") or "").strip().lower()
                    target_key = _BACKEND_KEY_MAP.get(raw_key, raw_key)
                    raw_val = item.get("weight")
                    if target_key in self.weight_spins and raw_val is not None:
                        val = float(raw_val)
                        if val > 1.0:
                            val /= 100.0
                        self.weight_spins[target_key].setValue(val)
                self.status_message.emit("Đã nạp cấu hình trọng số từ máy chủ.")

        def _on_failed(_err: str) -> None:
            self.status_message.emit("Không thể đọc cấu hình trọng số từ máy chủ.")

        worker.finished.connect(_on_loaded)
        worker.failed.connect(_on_failed)
        worker.start()

    def get_weights(self) -> dict[str, float]:
        """Lấy từ điển trọng số hiện tại của 5 tiêu chí."""
        return {key: spin.value() for key, spin in self.weight_spins.items()}

    def set_weights(self, weights: dict[str, float]) -> None:
        """Thiết lập trọng số thủ công cho các tiêu chí."""
        for key, val in weights.items():
            if key in self.weight_spins:
                self.weight_spins[key].setValue(float(val))


def main() -> None:
    """Hàm chạy thử độc lập màn hình Cài đặt trong cửa sổ 1100x700."""
    app = QApplication(sys.argv)
    qss = load_stylesheet()
    if qss:
        app.setStyleSheet(qss)

    settings_window = SettingsView()
    settings_window.setWindowTitle("Code Quality & Security Analyzer - Cài đặt hệ thống")
    settings_window.resize(1100, 700)
    settings_window.status_message.connect(lambda text: print(f"[Settings Status] {text}"))
    settings_window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
