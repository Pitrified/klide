"""The host side of the wire.

Two ways in, one protocol. A unix socket for anything on this machine, which is what the gates use
because it needs no port and cannot collide. TCP for anything that is not, which is the viewer on a
PC today (phase 5) and the Kobo over Tailscale later (D8).

The difference is two lines of socket setup. Everything above `listen` is the same, which is the
point: the viewer is not a special case, it is the first client that happens not to be local.

Phase 2 sent one frame and closed. Phase 3 needs the connection to stay open, because input travels
the other way and a device that has to reconnect to report a swipe is not a design anyone would
ship.
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


#: Where a TCP host listens by default. Above 1024 so an unprivileged user can bind it, which AD10
#: requires: klide has to run on a host we may not administer.
DEFAULT_PORT = 5000

#: A unix socket path, or a host and port.
Address = Path | tuple[str, int]


def _listener(address: Address) -> socket.socket:
    """Open a listening socket for either kind of address."""
    if isinstance(address, Path):
        address.parent.mkdir(parents=True, exist_ok=True)
        address.unlink(missing_ok=True)
        server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        server.bind(str(address))
        return server
    host, port = address
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # Without this a viewer that reconnects within the TIME_WAIT window is refused, which during a
    # feedback session is every second or third restart.
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((host, port))
    return server


@contextmanager
def serve(
    address: Address, timeout: float = 10.0, read_timeout: float | None = None
) -> Iterator[HostLink]:
    """Bind, accept one device, and hold the connection open for the block.

    One device at a time. Several conversations are several pages to the same screen, not several
    screens, so nothing yet needs a second client.

    The two timeouts are separate because they answer different questions, and conflating them was
    a real bug. `timeout` is how long to wait for a device to connect. `read_timeout` is how long a
    read on the connection may block, and for a live session the answer is forever: a person can
    look at a page for an hour without pressing anything, and that is not a fault. When both were
    one number, a host told to wait two hours for a viewer also stopped two hours after the last
    press, which was measured rather than guessed: it died at 7200.5 seconds.

    A dead connection is still noticed, by the host's own writes failing, which is the direction
    that carries traffic anyway.
    """
    with closing(_listener(address)) as server:
        server.listen(1)
        server.settimeout(timeout)
        conn, _ = server.accept()
        conn.settimeout(read_timeout)
        link = HostLink(conn)
        try:
            yield link
        finally:
            link.close()
            if isinstance(address, Path):
                address.unlink(missing_ok=True)


def serve_once(frame: Frame, socket_path: Address, timeout: float = 10.0) -> None:
    """Send one frame to the first device that connects, then close.

    Kept because the walking skeleton is the frame gate and there is no reason for that check to
    grow a session.
    """
    with serve(socket_path, timeout, read_timeout=timeout) as link:
        link.send_frame(frame)


def serve_script(
    socket_path: Address, script: Callable[[HostLink], None], timeout: float = 10.0
) -> None:
    """Run `script` against one connected device. The scripted session's host side."""
    with serve(socket_path, timeout, read_timeout=timeout) as link:
        script(link)
