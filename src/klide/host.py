"""The host side of the wire.

A unix socket, because both ends are processes on one machine. The real device connects outward
over TCP (Tailscale, LAN or USB networking), which changes the lines that create the socket and
nothing above them.

Phase 2 sent one frame and closed. Phase 3 needs the connection to stay open, because input
travels the other way and a device that has to reconnect to report a swipe is not a design anyone
would ship.
"""

from __future__ import annotations

import socket
from collections.abc import Callable, Iterator
from contextlib import closing, contextmanager
from pathlib import Path

from klide.frame import Frame
from klide.input import InputEvent
from klide.protocol import encode_frame, read_input
from klide.waveform import Waveform


class HostLink:
    """A connection to one device, for as long as it lasts."""

    def __init__(self, conn: socket.socket) -> None:
        self._conn = conn
        self._stream = conn.makefile("rb")

    def send_frame(
        self, frame: Frame, waveform: Waveform = Waveform.GL16, page_id: int = 0
    ) -> None:
        self._conn.sendall(encode_frame(frame, waveform, page_id))

    def read_input(self) -> InputEvent:
        """Block until the device reports a gesture or a press."""
        return read_input(self._stream)

    def close(self) -> None:
        self._stream.close()
        self._conn.close()


@contextmanager
def serve(socket_path: Path, timeout: float = 10.0) -> Iterator[HostLink]:
    """Bind, accept one device, and hold the connection open for the block.

    One device at a time. Several conversations are several pages to the same screen, not several
    screens, so nothing yet needs a second client.
    """
    socket_path.parent.mkdir(parents=True, exist_ok=True)
    socket_path.unlink(missing_ok=True)
    with closing(socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)) as server:
        server.bind(str(socket_path))
        server.listen(1)
        server.settimeout(timeout)
        conn, _ = server.accept()
        conn.settimeout(timeout)
        link = HostLink(conn)
        try:
            yield link
        finally:
            link.close()
            socket_path.unlink(missing_ok=True)


def serve_once(frame: Frame, socket_path: Path, timeout: float = 10.0) -> None:
    """Send one frame to the first device that connects, then close.

    Kept because the walking skeleton is the frame gate and there is no reason for that check to
    grow a session.
    """
    with serve(socket_path, timeout) as link:
        link.send_frame(frame)


def serve_script(
    socket_path: Path, script: Callable[[HostLink], None], timeout: float = 10.0
) -> None:
    """Run `script` against one connected device. The scripted session's host side."""
    with serve(socket_path, timeout) as link:
        script(link)
