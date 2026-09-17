#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""klide viewer: the simulator's screen, in a browser.

Run it next to the klide host and open the page. Nothing to install on either side: the block above
is PEP 723 inline script metadata, so `uv run` builds the environment, and the page needs only a
browser.

    uv run klide_viewer.py --host localhost --port 5000    # then open the URL it prints
    ./klide_viewer.py --host 100.126.229.25                # the shebang runs uv for you

If the browser is on a different machine from the viewer, forward the viewer's HTTP port rather than
copying anything:

    ssh -L 8000:localhost:8000 <the machine running this>

`requires-python` is a floor and nothing more. It used to be a narrow pinned range because this was
a tkinter window and tkinter needs a Tcl/Tk the interpreter can find, which is a property of the
build rather than of the code. That is the whole reason this is a browser page now; the history is
in V4 in `plans/04_klide_app/05_viewer.md`, and the short version is that three successive Python
pins each failed on a different machine and the fourth attempt would have been the same mistake.
A browser is already on every machine that has a screen.

`dependencies` is empty and should stay that way. The standard library is the whole budget: this
file has to be runnable by copying it somewhere and typing one command.

Why it is a separate file rather than part of klide, and why it duplicates the protocol:

The host klide runs on is usually headless, and may be one nobody gives us root on, so the screen
has to be shown somewhere else. Once the viewer reaches the host over a socket it is simply a klide
client, which is exactly what the Kobo will be. Writing it against the protocol specification rather
than importing the code that defines the protocol is the only way to find out whether the
specification is implementable by someone else. A protocol only one codebase can speak has not been
shown to be a protocol.

The duplication is held to the contract by a test in the repo, `tests/test_viewer.py`, which decodes
this file's output against klide's encoder. If the two drift apart, a gate fails.

What it is for: every other check in klide compares its output against a reference klide produced,
so they catch a change and cannot catch a decision that was wrong when the reference was written.
A person looking at the screen is the only judgement that does not come from inside the system.
"""

from __future__ import annotations

import argparse
import base64
import json
import queue
import socket
import sys
import threading
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

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
#: one discrete step settled on release rather than anything smooth (A8). In panel pixels.
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


def take_message(buffer: bytearray) -> tuple[int, bytes] | None:
    """Pull one complete message out of `buffer`, or return None and leave it untouched.

    TCP delivers a megabyte frame in whatever pieces it likes, so "read a message" is not an
    operation the socket offers; this is. Bytes accumulate in the buffer across reads and a message
    is consumed only once all of it has arrived.
    """
    if len(buffer) < HEADER_SIZE:
        return None
    if buffer[:4] != MAGIC:
        raise ProtocolError(f"bad magic {bytes(buffer[:4])!r}, expected {MAGIC!r}")
    body_len = int.from_bytes(buffer[5:9], "big")
    if len(buffer) < HEADER_SIZE + body_len:
        return None
    msg_type = buffer[4]
    body = bytes(buffer[HEADER_SIZE : HEADER_SIZE + body_len])
    del buffer[: HEADER_SIZE + body_len]
    return msg_type, body


class Screen:
    """The panel's framebuffer, as the viewer knows it.

    The viewer holds the whole screen and paints patches into it, for the same reason the device
    does: what arrives is a rectangle, and what is shown is everything that has arrived so far.
    It is kept here rather than only in the browser so that reloading the page, or opening it after
    the host has already drawn, shows the screen as it stands instead of a blank one.
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

    def whole(self, waveform: str = "gc16") -> Patch:
        """The screen as one patch, for a browser that has just arrived."""
        return Patch(0, 0, self.width, self.height, waveform, 0, bytes(self.levels))


def as_event(patch: Patch) -> bytes:
    """One patch as a server-sent event.

    Levels go over as one byte per pixel rather than the packed two-per-byte of the wire format.
    That doubles a full screen to about 2 MB, which costs something once per page load and nothing
    afterwards, since every later patch is a small rectangle. The trade is that the browser does no
    unpacking: the bytes are already what `ImageData` wants, give or take the multiply.
    """
    payload = {
        "x": patch.x,
        "y": patch.y,
        "w": patch.width,
        "h": patch.height,
        "mode": patch.waveform,
        "page": patch.page_id,
        "levels": base64.b64encode(patch.levels).decode("ascii"),
    }
    return b"data: " + json.dumps(payload).encode("ascii") + b"\n\n"


class Bridge:
    """Between the klide socket and however many browser tabs are watching.

    A reader thread, which is safe here in a way it was not in the tkinter version: nothing in this
    process draws anything, so there is no toolkit with a thread affinity to violate.
    """

    def __init__(self, sock: socket.socket, width: int, height: int) -> None:
        self.sock = sock
        self.screen = Screen(width, height)
        self.lock = threading.Lock()
        self.subscribers: set[queue.Queue[bytes | None]] = set()
        self.gone: str | None = None
        threading.Thread(target=self._read, daemon=True).start()

    def subscribe(self) -> queue.Queue[bytes | None]:
        """A new watcher, started off with the screen as it stands."""
        outbox: queue.Queue[bytes | None] = queue.Queue()
        with self.lock:
            outbox.put(as_event(self.screen.whole()))
            self.subscribers.add(outbox)
        return outbox

    def unsubscribe(self, outbox: queue.Queue[bytes | None]) -> None:
        with self.lock:
            self.subscribers.discard(outbox)

    def send(self, payload: bytes) -> None:
        """An input event, back to the host."""
        try:
            self.sock.sendall(payload)
        except OSError as broken:
            self._finish(str(broken))

    def _read(self) -> None:
        incoming = bytearray()
        try:
            while True:
                chunk = self.sock.recv(1 << 16)
                if not chunk:
                    self._finish("host closed the connection")
                    return
                incoming += chunk
                while True:
                    message = take_message(incoming)
                    if message is None:
                        break
                    msg_type, body = message
                    if msg_type == FRAME:
                        self._publish(decode_frame(body))
        except (OSError, ProtocolError) as ended:
            self._finish(str(ended))

    def _publish(self, patch: Patch) -> None:
        with self.lock:
            self.screen.apply(patch)
            event = as_event(patch)
            for outbox in self.subscribers:
                outbox.put(event)

    def _finish(self, why: str) -> None:
        with self.lock:
            if self.gone is not None:
                return
            self.gone = why
            for outbox in self.subscribers:
                outbox.put(None)
        print(f"viewer: host disconnected: {why}", file=sys.stderr)


PAGE = """<!doctype html>
<meta charset="utf-8">
<title>klide viewer</title>
<style>
  body { margin: 0; background: #2b2b2b; color: #ddd;
         font: 13px/1.4 ui-monospace, SFMono-Regular, Menlo, monospace; }
  header { padding: 8px 12px; background: #1d1d1d; display: flex; gap: 14px; align-items: center;
           flex-wrap: wrap; position: sticky; top: 0; }
  button { font: inherit; background: #3a3a3a; color: #ddd; border: 1px solid #555;
           border-radius: 3px; padding: 3px 9px; cursor: pointer; }
  button.on { background: #6a6a2a; }
  input[type=number] { font: inherit; width: 5em; background: #3a3a3a; color: #ddd;
                       border: 1px solid #555; border-radius: 3px; padding: 2px 4px; }
  #wrap { padding: 16px; display: flex; gap: 20px; align-items: flex-start; }
  #panel { display: block; background: #fff; box-shadow: 0 0 0 1px #000, 0 6px 24px #0008;
           touch-action: none; }
  #status { padding: 6px 12px; background: #1d1d1d; color: #9a9a9a; white-space: pre-wrap; }
  #ruler { height: 10px; background: #6a6a2a; margin-top: 4px; }
  aside { max-width: 20em; color: #9a9a9a; }
</style>
<header>
  <button id="back">&#9664; page</button>
  <button id="forward">page &#9654;</button>
  <span>scale</span>
  <button data-scale="1">1:1</button>
  <button data-scale="2">1:2</button>
  <button data-scale="3">1:3</button>
  <button data-scale="4">1:4</button>
  <button id="true-size">true size</button>
  <span>monitor ppi <input type="number" id="ppi" min="30" max="1200" step="1"></span>
  <button id="honest">honest refresh</button>
</header>
<div id="wrap">
  <canvas id="panel"></canvas>
  <aside>
    <p>The two buttons at the top left are the device's physical page-turn buttons; the left and
    right arrow keys do the same. Click the panel for a tap, drag and release for a swipe. Space
    toggles honest refresh.</p>
    <p><b>True size.</b> A browser cannot know how big your monitor is, so this uses the number in
    the box. To make it real, hold a ruler to the bar below and set the number until the bar
    measures 100 mm.</p>
    <div id="ruler"></div>
  </aside>
</div>
<div id="status">connecting</div>
<script>
const CONFIG = __CONFIG__;
const canvas = document.getElementById("panel");
const ctx = canvas.getContext("2d");
canvas.width = CONFIG.width;
canvas.height = CONFIG.height;

let scale = 3;
// On by default. A redraw then takes the hundreds of milliseconds a real panel claims, which is
// what makes a design that redraws too often feel as bad here as it would on the device. The
// switch is there because clicking between views to check a layout wants the fast version (V2).
let honest = true;
let lastMode = "-";
let monitorPpi = Number(localStorage.getItem("klide.ppi")) || Math.round(96 * devicePixelRatio);
document.getElementById("ppi").value = monitorPpi;

// Patches arrive as fast as the host sends them; honest mode plays them at the speed the panel
// claims it can refresh. Without the queue an honest run would just drop the backlog on screen at
// once, which is the thing it exists to prevent.
const pending = [];
let busy = false;

function bytesOf(b64) {
  const raw = atob(b64);
  const out = new Uint8Array(raw.length);
  for (let i = 0; i < raw.length; i++) out[i] = raw.charCodeAt(i);
  return out;
}

function paint(patch) {
  const levels = bytesOf(patch.levels);
  const image = ctx.createImageData(patch.w, patch.h);
  const data = image.data;
  for (let i = 0; i < levels.length; i++) {
    const grey = levels[i] * 17;  // 0-15 spread over 0-255, exactly
    const o = i * 4;
    data[o] = grey; data[o + 1] = grey; data[o + 2] = grey; data[o + 3] = 255;
  }
  ctx.putImageData(image, patch.x, patch.y);
  lastMode = patch.mode;
  showStatus();
}

function step() {
  if (busy || pending.length === 0) return;
  const patch = pending.shift();
  paint(patch);
  if (!honest) { step(); return; }
  busy = true;
  setTimeout(() => { busy = false; step(); }, CONFIG.claimed[patch.mode] || 0);
}

function resize() {
  canvas.style.width = (CONFIG.width / scale) + "px";
  canvas.style.height = (CONFIG.height / scale) + "px";
  showStatus();
}

function showStatus() {
  const mm = CONFIG.width / CONFIG.ppi * 25.4;
  const shown = CONFIG.ppi / scale;
  const claimed = CONFIG.claimed[lastMode];
  document.getElementById("status").textContent =
    `1:${scale}  panel ${CONFIG.width}x${CONFIG.height} at ${CONFIG.ppi} ppi`
    + ` (${mm.toFixed(0)} mm wide)`
    + `   shown at ${shown.toFixed(0)} ppi on an assumed ${monitorPpi} ppi monitor`
    + `   refresh ${lastMode}${claimed ? " " + claimed + "ms claimed" : ""}`
    + `   ${honest ? "honest" : "fast"}`;
}

function setRuler() {
  const cssPx = 100 / 25.4 * monitorPpi / devicePixelRatio;
  document.getElementById("ruler").style.width = cssPx + "px";
}

for (const button of document.querySelectorAll("button[data-scale]")) {
  button.onclick = () => { scale = Number(button.dataset.scale); resize(); };
}
document.getElementById("true-size").onclick = () => {
  // Only whole-number downscaling looks right, so this lands near the true size rather than on it,
  // and the status line says what it actually achieved.
  scale = Math.max(1, Math.round(CONFIG.ppi / (monitorPpi / devicePixelRatio)));
  resize();
};
document.getElementById("ppi").oninput = (event) => {
  monitorPpi = Number(event.target.value) || monitorPpi;
  localStorage.setItem("klide.ppi", monitorPpi);
  setRuler();
  showStatus();
};
const honestButton = document.getElementById("honest");
function toggleHonest() {
  honest = !honest;
  honestButton.classList.toggle("on", honest);
  showStatus();
  step();
}
honestButton.onclick = toggleHonest;
honestButton.classList.toggle("on", honest);

document.getElementById("back").onclick = () => send({kind: "button", button: "back"});
document.getElementById("forward").onclick = () => send({kind: "button", button: "forward"});

function send(event) {
  fetch("input", {method: "POST", body: JSON.stringify(event)});
}

// Panel coordinates, not page ones: the canvas is drawn at whatever scale is chosen.
function panelXY(event) {
  const box = canvas.getBoundingClientRect();
  const x = (event.clientX - box.left) / box.width * CONFIG.width;
  const y = (event.clientY - box.top) / box.height * CONFIG.height;
  return [Math.min(CONFIG.width - 1, Math.max(0, Math.round(x))),
          Math.min(CONFIG.height - 1, Math.max(0, Math.round(y)))];
}

let press = null;
canvas.onpointerdown = (event) => {
  press = panelXY(event);
  canvas.setPointerCapture(event.pointerId);
};
canvas.onpointerup = (event) => {
  if (!press) return;
  const [x0, y0] = press, [x1, y1] = panelXY(event);
  press = null;
  const dx = x1 - x0, dy = y1 - y0;
  if (Math.max(Math.abs(dx), Math.abs(dy)) < CONFIG.dragThreshold) {
    send({kind: "tap", x: x0, y: y0});
    return;
  }
  const direction = Math.abs(dx) > Math.abs(dy)
    ? (dx < 0 ? "left" : "right")
    : (dy < 0 ? "up" : "down");
  send({kind: "swipe", direction: direction});
};

addEventListener("keydown", (event) => {
  if (event.key === "ArrowLeft") send({kind: "button", button: "back"});
  else if (event.key === "ArrowRight") send({kind: "button", button: "forward"});
  else if (event.key === " ") { event.preventDefault(); toggleHonest(); }
});

const stream = new EventSource("frames");
stream.onmessage = (event) => { pending.push(JSON.parse(event.data)); step(); };
stream.onerror = () => {
  document.getElementById("status").textContent = "host disconnected, or the viewer stopped";
  stream.close();
};

resize();
setRuler();
</script>
"""

# Names on the wire between the page and this process. Spelled out rather than numeric because
# nothing here is performance-sensitive and a readable POST body is easier to check by hand.
DIRECTIONS = {"left": DIR_LEFT, "right": DIR_RIGHT, "up": DIR_UP, "down": DIR_DOWN}
BUTTONS = {"back": BTN_PAGE_BACK, "forward": BTN_PAGE_FORWARD}


def input_from_json(payload: dict[str, Any]) -> bytes:
    """One event from the page, as protocol bytes. Raises on anything it does not recognise."""
    kind = payload.get("kind")
    if kind == "tap":
        return encode_input(TAP, x=int(payload["x"]), y=int(payload["y"]))
    if kind == "swipe":
        direction = DIRECTIONS.get(payload.get("direction", ""))
        if direction is None:
            raise ProtocolError(f"unknown swipe direction {payload.get('direction')!r}")
        return encode_input(SWIPE, direction=direction)
    if kind == "button":
        button = BUTTONS.get(payload.get("button", ""))
        if button is None:
            raise ProtocolError(f"unknown button {payload.get('button')!r}")
        return encode_input(BUTTON, button=button)
    raise ProtocolError(f"unknown event kind {kind!r}")


def page_for(width: int, height: int, ppi: int) -> bytes:
    config = {
        "width": width,
        "height": height,
        "ppi": ppi,
        "claimed": CLAIMED_MS,
        "dragThreshold": DRAG_THRESHOLD_PX,
    }
    return PAGE.replace("__CONFIG__", json.dumps(config)).encode("utf-8")


def handler_for(bridge: Bridge, page: bytes) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def do_GET(self) -> None:  # noqa: N802 - the name is http.server's
            if self.path in ("/", "/index.html"):
                self._body(page, "text/html; charset=utf-8")
            elif self.path == "/frames":
                self._frames()
            else:
                self.send_error(404)

        def do_POST(self) -> None:  # noqa: N802 - the name is http.server's
            if self.path != "/input":
                self.send_error(404)
                return
            length = int(self.headers.get("Content-Length", 0))
            try:
                bridge.send(input_from_json(json.loads(self.rfile.read(length))))
            except (ProtocolError, ValueError, KeyError) as bad:
                self.send_error(400, str(bad))
                return
            self._body(b"", "text/plain")

        def _body(self, payload: bytes, content_type: str) -> None:
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def _frames(self) -> None:
            """The event stream. One queue per watcher, ended by a None when the host goes."""
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Connection", "close")
            self.end_headers()
            self.close_connection = True
            outbox = bridge.subscribe()
            try:
                while True:
                    event = outbox.get()
                    if event is None:
                        return
                    self.wfile.write(event)
                    self.wfile.flush()
            except (BrokenPipeError, ConnectionResetError):
                pass  # the tab was closed, which is not news
            finally:
                bridge.unsubscribe(outbox)

        def log_message(self, fmt: str, *args: object) -> None:
            pass  # one line per frame would bury anything worth reading

    return Handler


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="The klide simulator's screen, in a browser.")
    parser.add_argument("--host", default="localhost", help="where klide is serving")
    parser.add_argument("--port", type=int, default=5000, help="klide's port")
    parser.add_argument("--http-port", type=int, default=8000, help="port to serve the page on")
    parser.add_argument("--bind", default="127.0.0.1", help="address to serve the page on")
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

    bridge = Bridge(sock, args.width, args.height)
    server = ThreadingHTTPServer(
        (args.bind, args.http_port),
        handler_for(bridge, page_for(args.width, args.height, args.ppi)),
    )
    print(f"viewer: open http://{args.bind}:{args.http_port}/")
    if args.bind == "127.0.0.1":
        print(
            f"viewer: from another machine, ssh -L {args.http_port}:localhost:{args.http_port} here"
        )
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nviewer: stopped")
    finally:
        sock.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
