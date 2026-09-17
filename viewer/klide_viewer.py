#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.13,<3.14"
# dependencies = []
# ///
"""klide viewer: a window onto the simulator, running wherever you have a screen.

Copy this one file to the machine with the display and run it. Nothing to install: the block above
is PEP 723 inline script metadata, so `uv run` fetches the interpreter and builds the environment.

    uv run klide_viewer.py --host 100.126.229.25          # over Tailscale, direct
    uv run klide_viewer.py --host localhost --port 5000   # through ssh -L
    ./klide_viewer.py --host ...                          # the shebang runs uv for you

`requires-python` names 3.13 and bounds it below 3.14, and both halves are doing work. tkinter is
in the standard library but needs a Tcl/Tk the interpreter can find, and uv's standalone CPythons
are not alike: the 3.13 builds carry Tcl/Tk 9.0 and run, while the 3.14 build resolved on another
machine reported Tk 8.6 and died with `Can't find a usable init.tcl`, having searched for a library
directory its own distribution does not contain.

The upper bound is the part that was missing first time round. `>=3.13` alone is satisfied by 3.14,
so uv took the newest it could and landed straight back on the broken one. This is a specific,
dated observation about two builds rather than a rule about Python versions, and it is the kind of
thing that comes back: if a future 3.13 build breaks the same way, the failure below says so and
names the interpreter it used.

`dependencies` is empty and should stay that way. The standard library and tkinter are the whole
budget: this file has to be runnable by copying it to whatever machine currently has a screen.

Why it is a separate file rather than part of klide, and why it duplicates the protocol:

The host klide runs on is usually headless, and may be one nobody gives us root on, so the window
has to open somewhere else. Once the viewer is on another machine it has to reach the host over the
network, and once it does that it is simply a klide client, which is exactly what the Kobo will be.
Writing it against the protocol specification rather than importing the code that defines the
protocol is the only way to find out whether the specification is implementable by someone else.
A protocol only one codebase can speak has not been shown to be a protocol.

The duplication is held to the contract by a test in the repo, `tests/test_viewer.py`, which
decodes this file's output against klide's encoder. If the two drift apart, a gate fails.

What it is for: every other check in klide compares its output against a reference klide produced,
so they catch a change and cannot catch a decision that was wrong when the reference was written.
A person looking at the screen is the only judgement that does not come from inside the system.
"""

from __future__ import annotations

import argparse
import base64
import queue
import socket
import sys
import threading
import time
import tkinter as tk
from dataclasses import dataclass

# The protocol, version 2. Transcribed from docs/protocol.md, not imported.
MAGIC = b"KLD2"
HEADER_SIZE = 9
FRAME_BODY_SIZE = 12
FRAME = 1
INPUT = 2

# Refresh modes, by their wire code. Appending is safe, reordering is not.
WAVEFORMS = ("a2", "du", "gl16", "gc16")

# What each mode claims to cost, in milliseconds. A second copy of klide's `waveform.FBINK_CLAIMS`,
# sourced from FBInk's own documentation and not measured on a Libra 2. The conformance test pins
# this table to klide's, so the two cannot drift.
CLAIMED_MS = {"a2": 120, "du": 260, "gl16": 450, "gc16": 450}

# Input event codes.
TAP, SWIPE, BUTTON = 1, 2, 3
DIR_NONE, DIR_LEFT, DIR_RIGHT, DIR_UP, DIR_DOWN = 0, 1, 2, 3, 4
BTN_NONE, BTN_PAGE_BACK, BTN_PAGE_FORWARD = 0, 1, 2

#: A drag shorter than this is a tap. The panel cannot track a finger continuously, so a drag is
#: one discrete step settled on release rather than anything smooth (A8).
DRAG_THRESHOLD_PX = 40


class ProtocolError(ValueError):
    """The bytes on the wire are not a message this viewer understands."""


@dataclass(frozen=True)
class Patch:
    """One frame message: a rectangle of 4-bit grey levels, and how to draw it."""

    x: int
    y: int
    width: int
    height: int
    waveform: str
    page_id: int
    levels: bytes


def encode_input(kind: int, direction: int = 0, button: int = 0, x: int = 0, y: int = 0) -> bytes:
    """One input event, device to host."""
    body = bytes([kind, direction, button, 0]) + _u16(x) + _u16(y)
    return MAGIC + bytes([INPUT]) + len(body).to_bytes(4, "big") + body


def _u16(value: int) -> bytes:
    if not 0 <= value < 1 << 16:
        raise ProtocolError(f"{value} does not fit two bytes")
    return value.to_bytes(2, "big")


def decode_frame(body: bytes) -> Patch:
    """A frame body into a patch. Rows are padded to a whole byte, two pixels per byte."""
    if len(body) < FRAME_BODY_SIZE:
        raise ProtocolError(f"frame body is at least {FRAME_BODY_SIZE} bytes, got {len(body)}")
    bits = body[0]
    if bits != 4:
        raise ProtocolError(f"this viewer reads 4bpp only, got {bits}")
    code = body[1]
    if code >= len(WAVEFORMS):
        raise ProtocolError(f"unknown refresh mode code {code}")
    page_id, x, y, width, height = (int.from_bytes(body[i : i + 2], "big") for i in range(2, 12, 2))
    row_bytes = (width + 1) // 2
    payload = body[FRAME_BODY_SIZE:]
    expected = row_bytes * height
    if len(payload) != expected:
        raise ProtocolError(f"{width}x{height} packs to {expected} bytes, got {len(payload)}")
    levels = bytearray()
    for row in range(height):
        line = payload[row * row_bytes : (row + 1) * row_bytes]
        wide = bytearray(len(line) * 2)
        wide[0::2] = bytes(b >> 4 for b in line)
        wide[1::2] = bytes(b & 0x0F for b in line)
        levels += wide[:width]
    return Patch(x, y, width, height, WAVEFORMS[code], page_id, bytes(levels))


def read_message(stream: object) -> tuple[int, bytes]:
    """Read one message, returning its type and body. `stream` is a binary file object."""
    header = _read_exactly(stream, HEADER_SIZE)
    if header[:4] != MAGIC:
        raise ProtocolError(f"bad magic {header[:4]!r}, expected {MAGIC!r}")
    return header[4], _read_exactly(stream, int.from_bytes(header[5:9], "big"))


def _read_exactly(stream: object, count: int) -> bytes:
    chunks = []
    remaining = count
    while remaining:
        chunk = stream.read(remaining)  # type: ignore[attr-defined]
        if not chunk:
            raise ProtocolError(f"stream ended after {count - remaining} of {count} bytes")
        chunks.append(chunk)
        remaining -= len(chunk)
    return b"".join(chunks)


def to_pgm(levels: bytes, width: int, height: int) -> bytes:
    """A greyscale image Tk can read, built without any imaging library.

    Tk's photo image reads PGM natively, so a header and the bytes are the whole conversion. Levels
    are spread from 0-15 to 0-255 by multiplying by 17, which is exact.
    """
    body = bytes(level * 17 for level in levels)
    return b"P5\n%d %d\n255\n" % (width, height) + body


class Screen:
    """The panel's framebuffer, as the viewer knows it.

    The viewer holds the whole screen and paints patches into it, for the same reason the device
    does: what arrives is a rectangle, and what is shown is everything that has arrived so far.
    """

    def __init__(self, width: int, height: int) -> None:
        self.width = width
        self.height = height
        self.levels = bytearray([15] * (width * height))

    def apply(self, patch: Patch) -> None:
        for row in range(patch.height):
            dst_y = patch.y + row
            if not 0 <= dst_y < self.height:
                continue
            start = max(0, -patch.x)
            end = min(patch.width, self.width - patch.x)
            if end <= start:
                continue
            src = row * patch.width
            dst = dst_y * self.width + patch.x
            self.levels[dst + start : dst + end] = patch.levels[src + start : src + end]

    def pgm(self) -> bytes:
        return to_pgm(bytes(self.levels), self.width, self.height)


class Reader(threading.Thread):
    """Reads the socket and posts patches to the UI thread through a queue.

    A thread rather than an event loop integration, because tkinter owns the main loop and a
    blocking read cannot live in it.
    """

    def __init__(self, sock: socket.socket, inbox: queue.Queue[tuple[str, object]]) -> None:
        super().__init__(daemon=True)
        self.sock = sock
        self.inbox = inbox

    def run(self) -> None:
        stream = self.sock.makefile("rb")
        try:
            while True:
                msg_type, body = read_message(stream)
                if msg_type == FRAME:
                    self.inbox.put(("frame", decode_frame(body)))
        except Exception as ended:  # noqa: BLE001 - any failure here means the host is gone
            self.inbox.put(("gone", str(ended)))


class Viewer:
    """The window."""

    def __init__(self, sock: socket.socket, width: int, height: int, ppi: int) -> None:
        self.sock = sock
        self.screen = Screen(width, height)
        self.ppi = ppi
        self.inbox: queue.Queue[tuple[str, object]] = queue.Queue()
        self.scale = 3
        self.honest = True
        self.busy_until = 0.0
        self.press: tuple[int, int] | None = None
        self.last_mode = "-"

        self.root = tk.Tk()
        self.root.title("klide viewer")
        self._build()
        Reader(sock, self.inbox).start()
        self.root.after(30, self._pump)

    # Layout

    def _build(self) -> None:
        bar = tk.Frame(self.root)
        bar.pack(side=tk.TOP, fill=tk.X)

        tk.Button(bar, text="◀ page", command=lambda: self._press(BTN_PAGE_BACK)).pack(side=tk.LEFT)
        tk.Button(bar, text="page ▶", command=lambda: self._press(BTN_PAGE_FORWARD)).pack(
            side=tk.LEFT
        )

        tk.Label(bar, text="  scale ").pack(side=tk.LEFT)
        for factor in (1, 2, 3, 4):
            tk.Button(
                bar, text=f"1:{factor}", width=3, command=lambda f=factor: self._set_scale(f)
            ).pack(side=tk.LEFT)
        tk.Button(bar, text="true size", command=self._true_size).pack(side=tk.LEFT)

        self.honest_var = tk.BooleanVar(value=True)
        tk.Checkbutton(
            bar,
            text="honest refresh",
            variable=self.honest_var,
            command=self._toggle_honest,
        ).pack(side=tk.LEFT, padx=8)

        self.status = tk.Label(self.root, text="connecting", anchor="w", font=("TkFixedFont", 9))
        self.status.pack(side=tk.BOTTOM, fill=tk.X)

        self.canvas = tk.Canvas(self.root, highlightthickness=0, bg="#888888")
        self.canvas.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        self.canvas.bind("<ButtonPress-1>", self._on_press)
        self.canvas.bind("<ButtonRelease-1>", self._on_release)
        self.root.bind("<Left>", lambda _e: self._press(BTN_PAGE_BACK))
        self.root.bind("<Right>", lambda _e: self._press(BTN_PAGE_FORWARD))
        self.root.bind("<space>", lambda _e: self._toggle_honest(flip=True))

        self.photo: tk.PhotoImage | None = None
        self._redraw()

    # Controls

    def _set_scale(self, factor: int) -> None:
        self.scale = max(1, factor)
        self._redraw()

    def _true_size(self) -> None:
        """Show the panel at roughly its physical size on this monitor.

        Only integer downscaling is available, so this lands near the right size rather than on it,
        and the status line says what it actually achieved. Being approximate and saying so beats
        being wrong and silent, which is how the 6.2pt text survived three phases.
        """
        monitor_ppi = self.root.winfo_fpixels("1i")
        self.scale = max(1, round(self.ppi / monitor_ppi))
        self._redraw()

    def _toggle_honest(self, flip: bool = False) -> None:
        if flip:
            self.honest_var.set(not self.honest_var.get())
        self.honest = self.honest_var.get()
        self._status()

    # Input, sent to the host

    def _send(self, payload: bytes) -> None:
        try:
            self.sock.sendall(payload)
        except OSError as gone:
            self.status.config(text=f"host gone: {gone}")

    def _press(self, button: int) -> None:
        self._send(encode_input(BUTTON, button=button))

    def _on_press(self, event: tk.Event) -> None:
        self.press = (event.x, event.y)

    def _on_release(self, event: tk.Event) -> None:
        """A short drag is a swipe, anything shorter is a tap. Settled on release (A8)."""
        if self.press is None:
            return
        start_x, start_y = self.press
        self.press = None
        dx, dy = event.x - start_x, event.y - start_y
        if max(abs(dx), abs(dy)) < DRAG_THRESHOLD_PX:
            panel_x = min(self.screen.width - 1, max(0, start_x * self.scale))
            panel_y = min(self.screen.height - 1, max(0, start_y * self.scale))
            self._send(encode_input(TAP, x=panel_x, y=panel_y))
            return
        if abs(dx) > abs(dy):
            direction = DIR_LEFT if dx < 0 else DIR_RIGHT
        else:
            direction = DIR_UP if dy < 0 else DIR_DOWN
        self._send(encode_input(SWIPE, direction=direction))

    # Frames, from the host

    def _pump(self) -> None:
        """Take what has arrived, respecting the refresh delay when honest mode is on."""
        now = time.monotonic()
        if now >= self.busy_until:
            try:
                kind, payload = self.inbox.get_nowait()
            except queue.Empty:
                pass
            else:
                if kind == "gone":
                    self.status.config(text=f"host disconnected: {payload}")
                else:
                    self.screen.apply(payload)
                    self.last_mode = payload.waveform
                    if self.honest:
                        self.busy_until = now + CLAIMED_MS[payload.waveform] / 1000
                    self._redraw()
        self.root.after(30, self._pump)

    def _redraw(self) -> None:
        image = tk.PhotoImage(data=base64.b64encode(self.screen.pgm()))
        if self.scale > 1:
            image = image.subsample(self.scale)
        self.photo = image  # a PhotoImage is collected the moment nothing holds it
        self.canvas.delete("all")
        self.canvas.config(width=image.width(), height=image.height())
        self.canvas.create_image(0, 0, anchor=tk.NW, image=image)
        self._status()

    def _status(self) -> None:
        monitor_ppi = self.root.winfo_fpixels("1i")
        shown_ppi = self.ppi / self.scale
        physical = self.screen.width / self.ppi * 25.4
        refresh = f"{self.last_mode} {CLAIMED_MS.get(self.last_mode, 0)}ms claimed"
        self.status.config(
            text=(
                f"1:{self.scale}  panel {self.screen.width}x{self.screen.height} at {self.ppi} ppi"
                f" ({physical:.0f} mm wide)   shown at {shown_ppi:.0f} ppi on a"
                f" {monitor_ppi:.0f} ppi monitor   refresh {refresh}"
                f"   {'honest' if self.honest else 'fast'}"
            )
        )

    def run(self) -> None:
        self.root.mainloop()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="A window onto the klide simulator.")
    parser.add_argument("--host", default="localhost")
    parser.add_argument("--port", type=int, default=5000)
    parser.add_argument("--width", type=int, default=1264, help="panel width in pixels")
    parser.add_argument("--height", type=int, default=1680, help="panel height in pixels")
    parser.add_argument("--ppi", type=int, default=300, help="panel density")
    args = parser.parse_args(argv)

    sock = socket.socket()
    try:
        sock.connect((args.host, args.port))
    except OSError as refused:
        print(f"viewer: cannot reach {args.host}:{args.port}: {refused}", file=sys.stderr)
        print("viewer: is the klide host running, and is the port forwarded?", file=sys.stderr)
        return 1
    print(f"viewer: connected to {args.host}:{args.port}")
    try:
        viewer = Viewer(sock, args.width, args.height, args.ppi)
    except tk.TclError as broken:
        _explain_tk_failure(broken)
        return 1
    viewer.run()
    return 0


def _explain_tk_failure(broken: tk.TclError) -> None:
    """Say which of the two failures this is, because the remedies are opposites.

    An earlier version printed one message for both and sent someone with a perfectly good display
    off to check `$DISPLAY`. Tcl says which it is; use that rather than guessing.
    """
    detail = str(broken)
    print(f"viewer: cannot open a window: {detail}", file=sys.stderr)
    print(f"viewer: running on {sys.executable}", file=sys.stderr)
    if "init.tcl" in detail or "Tcl wasn" in detail:
        print(
            "viewer: this interpreter has tkinter but no Tcl library it can find,",
            file=sys.stderr,
        )
        print(
            "viewer: which is a property of the interpreter, not of this machine.",
            file=sys.stderr,
        )
        print(
            "viewer: ask uv for one whose Tk works, and say so here if it does not:",
            file=sys.stderr,
        )
        print(
            "viewer:   uv run --python 3.13 klide_viewer.py --host ... --port ...",
            file=sys.stderr,
        )
        return
    print("viewer: there is no display to open a window on.", file=sys.stderr)
    print(
        "viewer: this runs on the machine with the screen, not on the klide host.",
        file=sys.stderr,
    )
    print("viewer: check that `echo $DISPLAY` prints something.", file=sys.stderr)


if __name__ == "__main__":
    sys.exit(main())
