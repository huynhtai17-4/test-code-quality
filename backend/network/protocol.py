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
