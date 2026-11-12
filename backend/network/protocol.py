"""Module giao thức mạng TCP: Đóng gói và bóc tách gói tin chống phân mảnh (Framing Protocol)."""

import datetime
import json
import logging
import socket
import struct
from decimal import Decimal
from typing import Any, Optional

HEADER_FORMAT = ">I"
HEADER_SIZE = struct.calcsize(HEADER_FORMAT)  # 4 bytes
MAX_PAYLOAD_SIZE = 100 * 1024 * 1024  # 100 MB giới hạn an toàn chống DoS/tràn bộ nhớ

logger = logging.getLogger(__name__)


def _json_default(obj: Any) -> Any:
    """Hàm phụ trợ chuyển đổi kiểu dữ liệu CSDL (Decimal, datetime) sang JSON an toàn."""
    if isinstance(obj, Decimal):
        return float(obj)
    if isinstance(obj, (datetime.date, datetime.datetime)):
        return obj.isoformat()
    return str(obj)


def recv_exact(sock: socket.socket, num_bytes: int) -> Optional[bytes]:
    """
    Đọc chính xác num_bytes từ socket để khắc phục hiện tượng cắt dính/phân mảnh TCP.

    Args:
        sock: Đối tượng TCP socket đang kết nối.
        num_bytes: Số byte chính xác cần nhận.

    Returns:
        bytes: Đủ số byte yêu cầu.
        None: Nếu kết nối bị đóng hoặc xảy ra lỗi ngắt quãng.
    """
    if num_bytes < 0:
        return None
    if num_bytes == 0:
        return b""

    chunks: list[bytes] = []
    received = 0

    while received < num_bytes:
        try:
            chunk = sock.recv(min(num_bytes - received, 65536))
            if not chunk:
                # Đối tác đã đóng kết nối
                return None
            chunks.append(chunk)
            received += len(chunk)
        except (ConnectionError, OSError) as exc:
            logger.debug("Lỗi nhận dữ liệu socket: %s", exc)
            return None

    return b"".join(chunks)


def send_bytes(sock: socket.socket, raw_data: bytes) -> bool:
    """
    Gửi dữ liệu nhị phân với tiền tố 4 byte độ dài (big-endian).

    Args:
        sock: Đối tượng TCP socket.
        raw_data: Mảng byte cần gửi.

    Returns:
        bool: True nếu gửi thành công, False nếu xảy ra lỗi đường truyền.
    """
    try:
        header = struct.pack(HEADER_FORMAT, len(raw_data))
        sock.sendall(header + raw_data)
        return True
    except (ConnectionError, BrokenPipeError, OSError) as exc:
        logger.error("Lỗi khi gửi dữ liệu qua socket: %s", exc)
        return False


def recv_bytes(
    sock: socket.socket,
    max_payload_size: int = MAX_PAYLOAD_SIZE,
) -> Optional[bytes]:
    """
    Nhận dữ liệu nhị phân có tiền tố 4 byte độ dài.

    Args:
        sock: Đối tượng TCP socket.
        max_payload_size: Giới hạn kích thước gói tối đa cho phép.

    Returns:
        bytes: Dữ liệu nhị phân nhận được.
        None: Nếu kết nối bị ngắt hoặc vượt quá kích thước cho phép.
    """
    length_bytes = recv_exact(sock, HEADER_SIZE)
    if length_bytes is None:
        return None

    (payload_length,) = struct.unpack(HEADER_FORMAT, length_bytes)
    if payload_length > max_payload_size:
        logger.warning(
            "Kích thước gói tin (%d bytes) vượt quá giới hạn cho phép (%d bytes)",
            payload_length,
            max_payload_size,
        )
        return None

    return recv_exact(sock, payload_length)


def send_json(sock: socket.socket, data: dict[str, Any]) -> bool:
    """
    Chuyển đổi dictionary thành chuỗi JSON UTF-8 và gửi kèm 4 byte độ dài.

    Args:
        sock: Đối tượng TCP socket.
        data: Dữ liệu dictionary cần truyền tải.

    Returns:
        bool: True nếu gửi thành công, False nếu lỗi.
    """
    try:
        json_bytes = json.dumps(
            data,
            ensure_ascii=False,
            default=_json_default,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        logger.error("Lỗi tuần tự hóa JSON: %s", exc)
        return False

    return send_bytes(sock, json_bytes)


def recv_json(sock: socket.socket) -> Optional[dict[str, Any]]:
    """
    Nhận và giải mã gói tin JSON UTF-8 từ TCP socket.

    Args:
        sock: Đối tượng TCP socket.

    Returns:
        dict: Dữ liệu JSON đã parse thành công.
        None: Nếu kết nối bị đóng hoặc dữ liệu JSON không hợp lệ.
    """
    raw_payload = recv_bytes(sock)
    if raw_payload is None:
        return None

    try:
        decoded_text = raw_payload.decode("utf-8")
        parsed = json.loads(decoded_text)
        if isinstance(parsed, dict):
            return parsed
        return {"data": parsed}
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        logger.error("Lỗi giải mã gói tin JSON: %s", exc)
        return None


def _run_protocol_test() -> None:
    """Kiểm thử loopback socket xác thực hoạt động của các hàm protocol."""
    print("[*] Khởi tạo socket.socketpair() để kiểm thử giao thức mạng...")
    sock_sender, sock_receiver = socket.socketpair()

    try:
        # 1. Kiểm thử gửi và nhận JSON có dấu tiếng Việt
        sample_dict = {
            "action": "test",
            "message": "Chào Antigravity! Kiểm tra tiếng Việt: ă, â, đ, ê, ô, ơ, ư",
            "status": "ok",
            "issue_count": 42,
            "score": 95.5,
        }

        print("\n[+] Test 1: Gửi gói tin JSON UTF-8...")
        send_ok = send_json(sock_sender, sample_dict)
        print(f"    - Gửi thành công: {send_ok}")
        if not send_ok:
            raise AssertionError("send_json thất bại!")

        received_dict = recv_json(sock_receiver)
        print(f"    - Dữ liệu nhận được: {received_dict}")
        if received_dict != sample_dict:
            raise AssertionError("Dữ liệu JSON nhận được không khớp 100%!")
        print("    [PASSED] Dữ liệu JSON nhận được khớp chính xác 100%!")

        # 2. Kiểm thử gửi và nhận dữ liệu nhị phân (Binary raw bytes)
        sample_bytes = b"PK\x03\x04" + b"X" * 1024 + b"\x00\xff\xfe\xfd"
        print("\n[+] Test 2: Gửi gói tin nhị phân raw bytes (1032 bytes)...")
        send_raw_ok = send_bytes(sock_sender, sample_bytes)
        print(f"    - Gửi thành công: {send_raw_ok}")
        if not send_raw_ok:
            raise AssertionError("send_bytes thất bại!")

        received_bytes = recv_bytes(sock_receiver)
        print(f"    - Số byte nhận được: {len(received_bytes) if received_bytes else 0}")
        if received_bytes != sample_bytes:
            raise AssertionError("Dữ liệu nhị phân nhận được không khớp!")
        print("    [PASSED] Dữ liệu nhị phân nhận được khớp chính xác 100%!")

        # 3. Kiểm thử đóng kết nối
        print("\n[+] Test 3: Kiểm thử xử lý ngắt kết nối an toàn...")
        sock_sender.close()
        closed_res = recv_json(sock_receiver)
        if closed_res is not None:
            raise AssertionError("Khi kết nối đóng, recv_json phải trả về None!")
        print("    [PASSED] Trả về None an toàn khi đối tác đóng kết nối!")

        print("\n[SUCCESS] Toàn bộ kịch bản kiểm thử protocol.py đã hoàn thành thành công!")

    finally:
        sock_sender.close()
        sock_receiver.close()


if __name__ == "__main__":
    _run_protocol_test()
