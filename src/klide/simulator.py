"""The simulator: the device, as far as the host can tell.

Headless (AD2). It receives frames and writes them out as image files, which is what makes the
output something an agent can check rather than something a person has to look at. The viewer that
AD2 puts on top of this is a separate, thin thing and is not needed to verify anything.

What it stands in for grows with the phases. Today it is the panel receiving a frame. AD3 adds
refresh modes, partial update latency, touch and the page-turn buttons; AD4 adds the client's own
cache, taller page buffer and disconnect overlay, so that the device client is later a port of
something already working.
"""

from __future__ import annotations

import socket
import time
from contextlib import closing
from pathlib import Path

from klide.compare import save_frame
from klide.frame import Frame
from klide.panel import Panel
from klide.protocol import read_frame


class ConnectTimeout(TimeoutError):
    """The host's socket never appeared."""


def receive_once(socket_path: Path, panel: Panel, timeout: float = 10.0) -> Frame:
    """Connect, read one frame, disconnect.

    The retry loop is here because the host binds its socket concurrently with this call, so a
    first connect can legitimately arrive early. It is not papering over a race in the protocol.
    """
    deadline = time.monotonic() + timeout
    while True:
        try:
            client = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            client.connect(str(socket_path))
            break
        except (FileNotFoundError, ConnectionRefusedError):
            client.close()
            if time.monotonic() > deadline:
                raise ConnectTimeout(f"no host socket at {socket_path} after {timeout}s") from None
            time.sleep(0.01)
    with closing(client), closing(client.makefile("rb")) as stream:
        return read_frame(stream, panel)


def display(frame: Frame, out_path: Path) -> Path:
    """Draw the frame, which for a headless panel means writing the file."""
    save_frame(frame, out_path)
    return out_path
