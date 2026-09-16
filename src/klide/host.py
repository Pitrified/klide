"""The host side of the wire.

A unix socket, because the skeleton's two ends are two processes on one machine and the phase says
the protocol matters and the socket does not, yet. The real device connects outward over TCP
(Tailscale, LAN or USB networking), which changes the two lines that create the socket and nothing
above them.
"""

from __future__ import annotations

import socket
from contextlib import closing
from pathlib import Path

from klide.frame import Frame
from klide.protocol import encode_frame


def serve_once(frame: Frame, socket_path: Path, timeout: float = 10.0) -> None:
    """Bind, accept one client, send one frame, close.

    One shot on purpose: the skeleton proves a frame crosses the wire, and a connection that stays
    open for a stream of them is phase 3, where there is something to stream.
    """
    socket_path.parent.mkdir(parents=True, exist_ok=True)
    socket_path.unlink(missing_ok=True)
    message = encode_frame(frame)
    with closing(socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)) as server:
        server.bind(str(socket_path))
        server.listen(1)
        server.settimeout(timeout)
        conn, _ = server.accept()
        with closing(conn):
            conn.sendall(message)
    socket_path.unlink(missing_ok=True)
