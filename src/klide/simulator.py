"""The simulator: the device, as far as the host can tell.

Headless (AD2). It receives frames and writes them out as image files, which is what makes the
output something an agent can check rather than something a person has to look at. The viewer that
AD2 puts on top of this is a separate, thin thing and is not needed to verify anything.

The panel and the client logic are in `device`; this module is the socket between that and the
host, plus writing the screen to a file.
"""

from __future__ import annotations

import socket
import time
from collections.abc import Iterator
from contextlib import closing, contextmanager
from pathlib import Path

from klide.compare import save_frame
from klide.device import Device
from klide.frame import Frame
from klide.input import InputEvent
from klide.panel import Panel
from klide.protocol import encode_input, read_frame
from klide.waveform import Waveform


class ConnectTimeout(TimeoutError):
    """The host's socket never appeared."""


class DeviceLink:
    """A connection to the host, for as long as it lasts."""

    def __init__(self, sock: socket.socket, panel: Panel) -> None:
        self._sock = sock
        self._stream = sock.makefile("rb")
        self._panel = panel
        self._closed = False

    def receive_frame(self) -> tuple[Frame, Waveform, int]:
        """Block until the host sends a frame."""
        return read_frame(self._stream, self._panel)

    def receive_into(self, device: Device) -> tuple[Frame, Waveform, int]:
        """Take the next frame and draw it, which is what a client's read loop does."""
        frame, waveform, page_id = self.receive_frame()
        device.receive(frame, waveform, page_id)
        return frame, waveform, page_id

    def send_input(self, event: InputEvent) -> None:
        """Forward a gesture the client chose not to answer locally."""
        self._sock.sendall(encode_input(event))

    def close(self) -> None:
        """Idempotent, because a session that drops the host deliberately closes it once and the
        surrounding context manager closes it again."""
        if self._closed:
            return
        self._closed = True
        self._stream.close()
        self._sock.close()


def _connect(socket_path: Path, timeout: float) -> socket.socket:
    """Connect, retrying while the host is still binding.

    The retry loop is here because the host binds its socket concurrently with this call, so a
    first connect can legitimately arrive early. It is not papering over a race in the protocol.
    """
    deadline = time.monotonic() + timeout
    while True:
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        try:
            sock.connect(str(socket_path))
        except (FileNotFoundError, ConnectionRefusedError):
            sock.close()
            if time.monotonic() > deadline:
                raise ConnectTimeout(f"no host socket at {socket_path} after {timeout}s") from None
            time.sleep(0.01)
        else:
            sock.settimeout(timeout)
            return sock


@contextmanager
def connect(socket_path: Path, panel: Panel, timeout: float = 10.0) -> Iterator[DeviceLink]:
    """Open a connection to the host and hold it for the block."""
    sock = _connect(socket_path, timeout)
    link = DeviceLink(sock, panel)
    try:
        yield link
    finally:
        link.close()


def receive_once(socket_path: Path, panel: Panel, timeout: float = 10.0) -> Frame:
    """Connect, read one frame, disconnect. The walking skeleton's device side."""
    with closing(_connect(socket_path, timeout)) as sock, closing(sock.makefile("rb")) as stream:
        frame, _waveform, _page = read_frame(stream, panel)
        return frame


def display(frame: Frame, out_path: Path) -> Path:
    """Draw the frame, which for a headless panel means writing the file."""
    save_frame(frame, out_path)
    return out_path
