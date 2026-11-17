"""Bộ điều khiển quản lý nghiệp vụ phân tích và xuất báo cáo (AnalysisController)."""

from __future__ import annotations

import logging
from typing import Any

from PyQt6.QtCore import pyqtSignal  # pylint: disable=no-name-in-module

from frontend.controllers.base_controller import BaseController
from frontend.network import api
from frontend.workers.analysis_worker import AnalysisWorker

logger = logging.getLogger(__name__)


class AnalysisController(BaseController):
    """Điều phối toàn bộ logic chạy phân tích luồng ngầm và xuất báo cáo cho AnalysisView."""

    analysis_progress = pyqtSignal(str, int)
    analysis_finished = pyqtSignal(dict)
    analysis_failed = pyqtSignal(str)
    report_exported = pyqtSignal(str)

    def __init__(self, parent: Any = None) -> None:
        super().__init__(parent)
        self._analysis_worker: AnalysisWorker | None = None

    def start_analysis(self, project_id: int) -> None:
        """Khởi động luồng chạy phân tích mã nguồn thời gian thực."""
        self.cancel_analysis()

        self.status_message.emit("Đang khởi tạo phiên phân tích...")
        self.loading_changed.emit(True)

        worker = AnalysisWorker(project_id, self)
        worker.progress.connect(self._on_progress)
        worker.finished.connect(self._on_finished)
        worker.failed.connect(self._on_failed)

        self._analysis_worker = worker
        worker.start()

    def cancel_analysis(self) -> None:
        """Hủy bỏ phiên phân tích đang chạy."""
        if self._analysis_worker and self._analysis_worker.isRunning():
            self._analysis_worker.cancel()
            self._analysis_worker = None
            self.loading_changed.emit(False)
            self.status_message.emit("Đã hủy quá trình phân tích.")

    def _on_progress(self, msg: str, pct: int) -> None:
        """Chuyển tiếp tín hiệu tiến độ phân tích."""
        self.analysis_progress.emit(msg, pct)
        self.status_message.emit(f"[{pct}%] {msg}")

    def _on_finished(self, response: dict[str, Any]) -> None:
        """Xử lý khi hoàn tất phân tích thành công."""
        self._analysis_worker = None
        self.loading_changed.emit(False)
        self.analysis_finished.emit(response)
        self.status_message.emit("Quá trình phân tích hoàn tất.")

    def _on_failed(self, error_msg: str) -> None:
        """Xử lý khi phân tích gặp sự cố."""
        self._analysis_worker = None
        self.loading_changed.emit(False)
        self.analysis_failed.emit(error_msg)
        self.status_message.emit(f"Phân tích thất bại: {error_msg}")

    def save_report_file(self, file_path: str, html_content: str) -> None:
        """Lưu nội dung báo cáo HTML vào tệp tin chỉ định."""
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(html_content)
            self.report_exported.emit(file_path)
            self.status_message.emit(f"Đã xuất báo cáo thành công: {file_path}")
        except OSError as err:
            logger.error("Lỗi khi lưu tệp báo cáo: %s", err)
            self.error_occurred.emit(f"Không thể ghi tệp báo cáo: {err}")

    @staticmethod
    def collect_critical_high_issues(
        session_id: int | None,
        data: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """Lọc và trả về danh sách lỗi Critical / High từ dữ liệu hoặc API."""
        raw_issues = data.get("issues")
        if not raw_issues and session_id:
            try:
                res = api.list_issues(int(session_id))
                if isinstance(res, dict) and res.get("status") == "ok":
                    raw_issues = res.get("data", [])
            except Exception as exc:  # pylint: disable=broad-exception-caught
                logger.debug("Không thể lấy danh sách issues từ API: %s", exc)

        crit_high: list[dict[str, Any]] = []
        if isinstance(raw_issues, list):
            for it in raw_issues:
                sev = str(it.get("severity") or "").capitalize()
                if sev in ("Critical", "High"):
                    crit_high.append(it)
        return crit_high
