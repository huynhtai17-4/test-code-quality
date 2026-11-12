"""Package tầng giao tiếp mạng TCP cho ứng dụng Frontend Desktop."""

from frontend.network import api, protocol
from frontend.network.socket_client import SocketClient

__all__ = [
    "api",
    "protocol",
    "SocketClient",
]
