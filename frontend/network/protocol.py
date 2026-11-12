"""Giao thức mạng TCP: Đóng gói và bóc tách gói tin chống phân mảnh phía Frontend."""

import json
import logging
import socket
import struct
from typing import Any

HEADER_FORMAT = ">I"
HEADER_SIZE = struct.calcsize(HEADER_FORMAT)  # 4 bytes
MAX_PAYLOAD_SIZE = 100 * 1024 * 1024  # 100 MB giới hạn an toàn chống tràn bộ nhớ

logger = logging.getLogger(__name__)


def recv_exact(sock: socket.socket, num_bytes: int) -> bytes | None:
    """
    Đọc chính xác num_bytes từ socket để khắc phục hiện tượng cắt dính/phân mảnh TCP.

    Args:
        sock: Đối tượng TCP socket đang kết nối.
        num_bytes: Số byte chính xác cần nhận.

    Returns:
        bytes: Đủ số byte yêu cầu hoặc None nếu ngắt kết nối.
    """
    if num_bytes <= 0:
        return b"" if num_bytes == 0 else None

    buf = bytearray(num_bytes)
    view = memoryview(buf)
    offset = 0

    while offset < num_bytes:
        try:
            chunk_size = min(num_bytes - offset, 65536)
            n_bytes = sock.recv_into(view[offset:], chunk_size)
            if n_bytes == 0:
                return None
            offset += n_bytes
        except (ConnectionError, OSError) as exc:
            logger.debug("Lỗi nhận dữ liệu socket frontend: %s", exc)
            return None

    return bytes(buf)


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
        wire_packet = struct.pack(HEADER_FORMAT, len(raw_data)) + raw_data
        sock.sendall(wire_packet)
        return True
    except (ConnectionError, BrokenPipeError, OSError) as exc:
        logger.error("Lỗi khi gửi dữ liệu qua socket frontend: %s", exc)
        return False


def recv_bytes(
    sock: socket.socket,
    max_payload_size: int = MAX_PAYLOAD_SIZE,
) -> bytes | None:
    """
    Nhận dữ liệu nhị phân có tiền tố 4 byte độ dài.

    Args:
        sock: Đối tượng TCP socket.
        max_payload_size: Giới hạn kích thước gói tối đa cho phép.

    Returns:
        bytes: Dữ liệu nhị phân nhận được hoặc None nếu lỗi.
    """
    header = recv_exact(sock, HEADER_SIZE)
    if not header:
        return None

    try:
        (expected_len,) = struct.unpack(HEADER_FORMAT, header)
    except struct.error as exc:
        logger.error("Không thể giải mã độ dài gói tin frontend: %s", exc)
        return None

    if expected_len > max_payload_size:
        logger.error(
            "Kích thước gói tin (%d bytes) vượt quá giới hạn an toàn (%d bytes)",
            expected_len,
            max_payload_size,
        )
        return None

    return recv_exact(sock, expected_len)


def send_json(sock: socket.socket, data: Any) -> bool:
    """
    Chuyển đối tượng Python thành JSON UTF-8 và gửi qua socket.

    Args:
        sock: Đối tượng TCP socket.
        data: Dữ liệu cần tuần tự hóa và gửi.

    Returns:
        bool: True nếu gửi thành công, False nếu thất bại.
    """
    try:
        json_bytes = json.dumps(data, ensure_ascii=False).encode("utf-8")
        return send_bytes(sock, json_bytes)
    except (TypeError, ValueError) as exc:
        logger.error("Lỗi tuần tự hóa JSON khi gửi: %s", exc)
        return False


def recv_json(
    sock: socket.socket,
    max_payload_size: int = MAX_PAYLOAD_SIZE,
) -> dict[str, Any] | None:
    """
    Nhận gói tin và giải mã thành đối tượng JSON dictionary.

    Args:
        sock: Đối tượng TCP socket.
        max_payload_size: Giới hạn kích thước gói.

    Returns:
        dict: Dữ liệu JSON đối tượng nhận được, hoặc None nếu lỗi.
    """
    raw_data = recv_bytes(sock, max_payload_size=max_payload_size)
    if raw_data is None:
        return None

    try:
        json_str = raw_data.decode("utf-8")
        obj = json.loads(json_str)
        if isinstance(obj, dict):
            return obj
        logger.warning("Dữ liệu nhận được không phải là JSON dict: %s", type(obj))
        return {"data": obj}
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        logger.error("Lỗi giải mã gói tin JSON: %s", exc)
        return None
