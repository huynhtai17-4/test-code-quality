"""Luồng chạy ngầm thực thi kiểm định mã nguồn toàn diện (AnalysisWorker) kế thừa QThread."""

import concurrent.futures
from typing import Any
from PyQt6.QtCore import QObject, QThread, pyqtSignal  # pylint: disable=no-name-in-module

from frontend.network import api

_STAGES = (
    (15, "Đang nạp cấu trúc thư mục và tệp tin mã nguồn..."),
    (35, "Đang quét lỗ hổng an toàn bảo mật (Bandit)..."),
    (55, "Đang kiểm định độ phức tạp tính toán và bảo trì..."),
    (75, "Đang kiểm tra thư viện phụ thuộc và cơ sở dữ liệu CVE..."),
    (90, "Đang tổng hợp điểm số và xếp loại chất lượng..."),
)


class AnalysisWorker(QThread):
    """
    Luồng phụ trách khởi chạy và theo dõi tiến trình phân tích dự án (analysis.run).

    - Cung cấp thanh tiến trình động kèm thông điệp từng giai đoạn kiểm định.
    - Hỗ trợ dừng / hủy tiến trình theo yêu cầu của người dùng (cancel).
    """

    started = pyqtSignal()
    progress = pyqtSignal(str, int)
    finished = pyqtSignal(dict)
    failed = pyqtSignal(str)

    def __init__(self, project_id: int, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.project_id = int(project_id)
        self.is_cancelled = False

    def cancel(self) -> None:
        """Đánh dấu cờ yêu cầu dừng / hủy tiến trình phân tích."""
        self.is_cancelled = True

    def run(self) -> None:
        """Thực thi gọi phân tích và điều phối thanh tiến trình liên tục."""
        self.started.emit()
        self.progress.emit("Khởi tạo kết nối tới máy chủ phân tích...", 5)

        if self.is_cancelled:
            self._handle_cancel()
            return

        executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
        try:
            future = executor.submit(api.run_analysis, self.project_id)
            current_stage_idx = 0

            while not future.done():
                if self.is_cancelled:
                    future.cancel()
                    self._handle_cancel()
                    return

                # Cập nhật thông điệp tiến trình theo chu kỳ
                if current_stage_idx < len(_STAGES):
                    pct, msg = _STAGES[current_stage_idx]
                    self.progress.emit(msg, pct)
                    current_stage_idx += 1

                # Chờ nhẹ 0.3s trước khi kiểm tra lại
                try:
                    result = future.result(timeout=0.3)
                    self._dispatch_result(result)
                    return
                except concurrent.futures.TimeoutError:
                    continue
                except Exception as exc:  # pylint: disable=broad-exception-caught
                    self.failed.emit(f"Sự cố luồng thực thi: {exc}")
                    return

            # Khi future hoàn thành ngay trong lần lặp
            try:
                result = future.result()
                self._dispatch_result(result)
            except Exception as exc:  # pylint: disable=broad-exception-caught
                self.failed.emit(f"Sự cố luồng thực thi: {exc}")
        finally:
            executor.shutdown(wait=False, cancel_futures=True)

    def _handle_cancel(self) -> None:
        """Thông báo trạng thái khi người dùng chủ động hủy."""
        self.progress.emit("Tiến trình phân tích đã bị hủy.", 0)

    def _dispatch_result(self, result: dict[str, Any]) -> None:
        """Phân phối kết quả thành công hoặc lỗi về giao diện."""
        if self.is_cancelled:
            self._handle_cancel()
            return

        if isinstance(result, dict) and result.get("status") == "ok":
            self.progress.emit("Hoàn thành phân tích mã nguồn thành công!", 100)
            self.finished.emit(result)
        elif isinstance(result, dict) and result.get("status") == "error":
            error_msg = str(result.get("message") or "Lỗi phân tích dự án từ máy chủ")
            self.failed.emit(error_msg)
        else:
            payload = result if isinstance(result, dict) else {"status": "ok", "data": result}
            self.finished.emit(payload)
