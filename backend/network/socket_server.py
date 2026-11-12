"""Module TCP Socket Server đa luồng xử lý các kết nối từ client."""

import logging
import socket
import sys
import threading
import time
from pathlib import Path
from typing import Optional

# Đảm bảo đường dẫn import hoạt động khi chạy trực tiếp file này
ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# pylint: disable=wrong-import-position
from backend.config import SERVER_HOST, SERVER_PORT
from backend.network import protocol, router

logger = logging.getLogger(__name__)


class SocketServer:
    """TCP Socket Server đa luồng xử lý đồng thời nhiều kết nối từ Frontend/Client."""

    def __init__(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
    ) -> None:
        """Khởi tạo cấu hình máy chủ socket từ tham số hoặc backend.config."""
        self.host: str = host if host is not None else SERVER_HOST
        self.port: int = port if port is not None else SERVER_PORT
        self.is_running: bool = False
        self.server_sock: Optional[socket.socket] = None
        self._lock = threading.Lock()

    def handle_client(
        self,
        client_sock: socket.socket,
        client_addr: tuple[str, int],
    ) -> None:
        """
        Xử lý từng kết nối client độc lập trong một luồng riêng biệt.

        Args:
            client_sock: Socket kết nối với client.
            client_addr: Địa chỉ (host, port) của client.
        """
        logger.info("[+] Client kết nối từ %s:%s", client_addr[0], client_addr[1])
        try:
            while self.is_running:
                request = protocol.recv_json(client_sock)
                if request is None:
                    # Client đã ngắt kết nối an toàn
                    logger.info("[-] Client %s:%s đã ngắt kết nối", client_addr[0], client_addr[1])
                    break

                response = router.dispatch_request(request)
                send_ok = protocol.send_json(client_sock, response)
                if not send_ok:
                    logger.warning(
                        "Không thể gửi phản hồi tới client %s:%s",
                        client_addr[0],
                        client_addr[1],
                    )
                    break
        except Exception as exc:  # pylint: disable=broad-exception-caught
            logger.error("Lỗi giao tiếp với client %s:%s: %s", client_addr[0], client_addr[1], exc)
        finally:
            try:
                client_sock.close()
            except OSError:
                pass
            logger.debug("Đã đóng kết nối client %s:%s", client_addr[0], client_addr[1])

    def start(self) -> None:
        """
        Khởi động máy chủ TCP socket và lắng nghe các kết nối đến.

        Tạo luồng daemon mới cho mỗi client kết nối.
        """
        self.server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        try:
            self.server_sock.bind((self.host, self.port))
            # Nếu port được truyền là 0, cập nhật lại port thực tế được gán bởi HĐH
            if self.port == 0:
                self.port = self.server_sock.getsockname()[1]
            self.server_sock.listen(10)
            self.server_sock.settimeout(1.0)
            self.is_running = True
            print(f"[+] Server đang lắng nghe tại {self.host}:{self.port}...")
            logger.info("Server đã khởi động tại %s:%s", self.host, self.port)

            while self.is_running:
                try:
                    client_sock, client_addr = self.server_sock.accept()
                except (TimeoutError, socket.timeout):
                    continue
                except OSError:
                    # Socket đã bị đóng khi stop()
                    break

                thread = threading.Thread(
                    target=self.handle_client,
                    args=(client_sock, client_addr),
                    daemon=True,
                )
                thread.start()

        except KeyboardInterrupt:
            print("\n[*] Đang tắt server do nhận tín hiệu ngắt (Ctrl+C)...")
        except OSError as exc:
            logger.error("Lỗi socket/port (%s): %s", self.port, exc)
            raise
        except Exception as exc:  # pylint: disable=broad-exception-caught
            logger.error("Lỗi máy chủ socket: %s", exc)
            raise
        finally:
            self.stop()

    def stop(self) -> None:
        """Dừng máy chủ và giải phóng socket."""
        with self._lock:
            if not self.is_running and self.server_sock is None:
                return
            self.is_running = False
            if self.server_sock:
                try:
                    self.server_sock.close()
                except OSError:
                    pass
                self.server_sock = None
            logger.info("Máy chủ socket đã dừng thành công.")


def _run_server_test() -> None:
    """Kịch bản kiểm thử độc lập cho SocketServer."""
    test_port = 8899
    server = SocketServer(host="127.0.0.1", port=test_port)

    # 1. Khởi động server trên một thread nền
    server_thread = threading.Thread(target=server.start, daemon=True)
    server_thread.start()

    # Chờ server khởi động và mở socket
    time.sleep(0.5)

    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        # 2. Client kết nối tới server
        print(f"[*] Client đang kết nối tới 127.0.0.1:{server.port}...")
        client.connect(("127.0.0.1", server.port))
        print("[+] Kết nối client thành công!")

        # 3. Client gửi request config.get
        test_request = {"action": "config.get", "data": {}}
        print(f"[*] Client gửi request: {test_request}")
        send_ok = protocol.send_json(client, test_request)
        if not send_ok:
            raise RuntimeError("Client gửi dữ liệu thất bại!")

        # 4. Client nhận response
        response = protocol.recv_json(client)
        print(f"[+] Client nhận được phản hồi: {response}")

        if not response or response.get("status") != "ok":
            raise RuntimeError("Phản hồi từ server không đạt yêu cầu status: ok!")

        configs = response.get("data", [])
        print(
            f"[PASSED] Xác nhận server hoạt động chuẩn xác, "
            f"nhận được {len(configs)} tiêu chí cấu hình!"
        )

    finally:
        # 5. Đóng client và dừng server
        client.close()
        server.stop()
        server_thread.join(timeout=2.0)
        print("[+] Đã đóng kết nối client và dừng server thành công!")


if __name__ == "__main__":
    _run_server_test()
