"""Lớp điều khiển cơ sở (BaseController) cho tầng Controller theo mô hình MVC."""

from __future__ import annotations

from typing import Any, Callable

from PyQt6.QtCore import QObject, pyqtSignal  # pylint: disable=no-name-in-module

from frontend.workers.request_worker import RequestWorker


class BaseController(QObject):  # pylint: disable=too-few-public-methods
    """
    Bộ điều khiển cơ sở quản lý vòng đời luồng RequestWorker và truyền tín hiệu trạng thái.
    """

    status_message = pyqtSignal(str)
    error_occurred = pyqtSignal(str)
    loading_changed = pyqtSignal(bool)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._active_worker: RequestWorker | None = None

    def cancel_active_worker(self) -> None:
        """Hủy bỏ tác vụ nền đang thực thi nếu có."""
        if self._active_worker and self._active_worker.isRunning():
            self._active_worker.cancel()
            self._active_worker = None
            self.loading_changed.emit(False)

    def _execute_async(
        self,
        task_fn: Callable[[], Any],
        on_success: Callable[[Any], None],
        on_error: Callable[[str], None] | None = None,
        loading_status: str | None = None,
    ) -> None:
        """Thực thi một hàm đồng bộ bất đồng bộ qua RequestWorker."""
        self.cancel_active_worker()

        if loading_status:
            self.status_message.emit(loading_status)
        self.loading_changed.emit(True)

        worker = RequestWorker(task_fn, parent=self)

        def _handle_finished(result: Any) -> None:
            self._active_worker = None
            self.loading_changed.emit(False)
            on_success(result)

        def _handle_failed(err_msg: str) -> None:
            self._active_worker = None
            self.loading_changed.emit(False)
            if on_error:
                on_error(err_msg)
            else:
                self.error_occurred.emit(err_msg)

        worker.finished.connect(_handle_finished)
        worker.failed.connect(_handle_failed)

        self._active_worker = worker
        worker.start()
