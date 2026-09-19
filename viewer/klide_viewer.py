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
import struct
import sys
import threading
import zlib
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

#: How many lines a second the page may forward to this log before it starts dropping them. A
#: person clicking cannot reach this; a loop can, and a loop in the logging is what would make the
#: log useless exactly when it is needed.
LOG_PER_SECOND = 20

#: A drag shorter than this is a tap. The panel cannot track a finger continuously, so a drag is
#: one discrete step settled on release rather than anything smooth (A8). In panel pixels.
DRAG_THRESHOLD_PX = 40


def log(line: str) -> None:
    """Say what just happened, on stderr, unbuffered.

    The viewer is an instrument, so it says what it did rather than leaving someone to infer it
    from whether the screen moved. The first version printed nothing per event, and when a button
    appeared to do nothing there was no way to tell where the event had stopped: in the browser, in
    this process, or at the host. All three looked identical, and two of the three log files were
    empty because the little that was printed went to a buffered stdout.
    """
    print(f"viewer: {line}", file=sys.stderr, flush=True)


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


#: 4-bit levels widened to 8-bit samples. A `bytes.translate` table rather than a loop, because
#: this runs over two million pixels per full frame and a Python loop there is the difference
#: between a few milliseconds and a few hundred. Multiplying by 17 is exact: 15 becomes 255.
WIDEN = bytes(min(255, value * 17) for value in range(256))


def to_png(levels: bytes, width: int, height: int) -> bytes:
    """An 8-bit greyscale PNG, written with the standard library and nothing else.

    Why a PNG rather than the pixels: a panel of rendered text is mostly one colour and deflates
    about forty-fold, and this goes over a link that may be an SSH tunnel to another machine. The
    first version sent one byte per pixel base64-encoded, which is 2.8 MB for a full screen and took
    a person several seconds per press. The same screen is about 65 KB like this.

    A browser also decodes a PNG natively, which replaces a two-million-iteration loop over
    `ImageData` in the page with one `drawImage`.

    PNG is written by hand because the viewer ships as one file with no dependencies, and the format
    is four chunks: a signature, a header, the deflated scanlines, and an end marker. Each scanline
    carries a leading filter byte, zero here, meaning the row is stored as it is.
    """
    wide = levels.translate(WIDEN)
    raw = b"".join(b"\x00" + wide[row * width : (row + 1) * width] for row in range(height))
    header = struct.pack(">IIBBBBB", width, height, 8, 0, 0, 0, 0)
    return (
        b"\x89PNG\r\n\x1a\n"
        + _chunk(b"IHDR", header)
        + _chunk(b"IDAT", zlib.compress(raw, 6))
        + _chunk(b"IEND", b"")
    )


def _chunk(kind: bytes, data: bytes) -> bytes:
    """Length, type, data, and a CRC over the type and data. The whole of PNG's framing."""
    return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data))


def as_event(patch: Patch) -> bytes:
    """One patch as a server-sent event: where to put it, how it refreshes, and a PNG of it."""
    payload = {
        "x": patch.x,
        "y": patch.y,
        "w": patch.width,
        "h": patch.height,
        "mode": patch.waveform,
        "page": patch.page_id,
        "png": base64.b64encode(to_png(patch.levels, patch.width, patch.height)).decode("ascii"),
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
            log(f"a browser is watching, {len(self.subscribers)} now")
        return outbox

    def unsubscribe(self, outbox: queue.Queue[bytes | None]) -> None:
        with self.lock:
            self.subscribers.discard(outbox)
            log(f"a browser stopped watching, {len(self.subscribers)} left")

    def send(self, payload: bytes, what: str) -> None:
        """An input event, back to the host."""
        try:
            self.sock.sendall(payload)
        except OSError as broken:
            self._finish(str(broken))
            return
        log(f"sent {what} to the host, {len(payload)} bytes")

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
            log(
                f"frame {patch.width}x{patch.height} at ({patch.x},{patch.y}) {patch.waveform}"
                f" to {len(self.subscribers)} watching"
            )

    def _finish(self, why: str) -> None:
        with self.lock:
            if self.gone is not None:
                return
            self.gone = why
            for outbox in self.subscribers:
                outbox.put(None)
        log(f"host disconnected: {why}")


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
  .controls { display: flex; gap: 14px; align-items: center; flex-wrap: wrap; }
  /* Reading mode. What is left is the panel, the two page buttons and the way back; everything
     that exists to diagnose the viewer rather than to read what is on the panel goes away, and the
     panel takes whatever room the window has. Meant for a phone or a second monitor, where the
     page is being looked at rather than worked on. */
  body.reading { display: flex; flex-direction: column; height: 100dvh; overflow: hidden; }
  body.reading .diagnostic { display: none; }
  body.reading #wrap { flex: 1; min-height: 0; padding: 0;
                       justify-content: center; align-items: center; }
  body.reading #panel { box-shadow: 0 0 0 1px #000; }
</style>
<header>
  <button id="back">&#9664; page</button>
  <button id="forward">page &#9654;</button>
  <button id="mode">reading</button>
  <span class="controls diagnostic">
    <span>scale</span>
    <button data-scale="1">1:1</button>
    <button data-scale="2">1:2</button>
    <button data-scale="3">1:3</button>
    <button data-scale="4">1:4</button>
    <button id="true-size">true size</button>
    <span>monitor ppi <input type="number" id="ppi" min="30" max="1200" step="1"></span>
    <button id="honest">honest refresh</button>
  </span>
</header>
<div id="wrap">
  <canvas id="panel"></canvas>
  <aside class="diagnostic">
    <p>The two buttons at the top left are the device's physical page-turn buttons; the left and
    right arrow keys do the same. Click the panel for a tap, drag and release for a swipe. Space
    toggles honest refresh.</p>
    <p><b>True size.</b> A browser cannot know how big your monitor is, so this uses the number in
    the box. To make it real, hold a ruler to the bar below and set the number until the bar
    measures 100 mm. The status line then says what the panel measures, which the same ruler
    checks.</p>
    <p>At true size the browser is resampling 1264 columns into a few hundred, so the text is
    softer than it would be on a 300 ppi panel. The size is honest; the sharpness is not.</p>
    <div id="ruler"></div>
  </aside>
</div>
<div id="status" class="diagnostic">connecting</div>
<script>
const CONFIG = __CONFIG__;

// Everything the page does worth knowing about goes through here, to two places at once. The
// console is for a person with devtools open and for a driving browser, which reads it directly.
// The POST is so the same line lands in the viewer's own log next to the host's, which is what
// makes this readable without devtools and readable by me while someone else drives the page.
//
// Both guards exist because a log that floods is a log nobody reads. The forwarding is capped, and
// says so once when it stops rather than going quiet; and a failure to forward is reported to the
// console only, since reporting it anywhere else is the loop this is avoiding.
let saidThisSecond = 0;
let saidSecond = 0;
function say(line) {
  console.log("klide: " + line);
  const now = Math.floor(Date.now() / 1000);
  if (now !== saidSecond) { saidSecond = now; saidThisSecond = 0; }
  saidThisSecond++;
  if (saidThisSecond === CONFIG.logPerSecond) line = line + " (further lines this second dropped)";
  if (saidThisSecond > CONFIG.logPerSecond) return;
  fetch("log", {method: "POST", body: line})
    .then((response) => response.text())  // drained, or the browser reports the request aborted
    .catch((failure) => console.log("klide: could not forward a log line: " + failure));
}

// Before anything else, so a failure in the code below is reported rather than leaving the page
// merely inert. A thrown error stops the rest of this script, which unattaches every handler after
// the throw and looks exactly like a page whose buttons do nothing.
addEventListener("error", (event) => {
  say(`page error: ${event.message} at ${event.filename}:${event.lineno}:${event.colno}`);
});
addEventListener("unhandledrejection", (event) => {
  say(`unhandled rejection: ${event.reason}`);
});

// Two canvases, and the split is the point.
//
// `panel` is the framebuffer at the device's own size. Patches land in it and nothing else touches
// it, so what it holds is exactly what the panel holds.
//
// `canvas` is what you look at, sized in real screen pixels for the scale chosen. The panel is
// resampled into it rather than handed to CSS to squeeze, because a browser's default downscale of
// a non-integer ratio is a cheap filter: at 1:2.75 it drops some stems of a letter and doubles
// others, which reads as jagged rather than merely soft. Text at 300 ppi shown at 109 ppi has to
// lose detail; it should lose it evenly.
const panel = document.createElement("canvas");
panel.width = CONFIG.width;
panel.height = CONFIG.height;
const pctx = panel.getContext("2d");

const canvas = document.getElementById("panel");
const ctx = canvas.getContext("2d");

let scale = 3;
let trueSize = false;
// Reading mode hides the instruments and fits the panel to the window; `fit` is what keeps it
// fitted when the window changes, which is most of the time on a phone that gets turned.
let reading = false;
let fit = false;
let beforeReading = {scale: scale, trueSize: trueSize};
// On by default. A redraw then takes the hundreds of milliseconds a real panel claims, which is
// what makes a design that redraws too often feel as bad here as it would on the device. The
// switch is there because clicking between views to check a layout wants the fast version (V2).
let honest = true;
let lastMode = "-";
let sent = "nothing sent yet";
let monitorPpi = Number(localStorage.getItem("klide.ppi")) || Math.round(96 * devicePixelRatio);
document.getElementById("ppi").value = monitorPpi;

// Patches arrive as fast as the host sends them; honest mode plays them at the speed the panel
// claims it can refresh. Without the queue an honest run would just drop the backlog on screen at
// once, which is the thing it exists to prevent.
const pending = [];
let busy = false;
let painted = 0;

function decode(b64) {
  return new Promise((resolve, reject) => {
    const image = new Image();
    image.onload = () => resolve(image);
    image.onerror = () => reject(new Error("the frame png would not decode"));
    image.src = "data:image/png;base64," + b64;
  });
}

async function paint(patch) {
  // drawImage rather than a loop over ImageData: the frame arrives as a PNG, so the decoding is
  // the browser's and the page does no per-pixel work at all.
  pctx.drawImage(await decode(patch.png), patch.x, patch.y);
  await present();
  painted++;
  lastMode = patch.mode;
  say(`painted ${patch.w}x${patch.h} at (${patch.x},${patch.y}) ${patch.mode},`
      + ` ${pending.length} waiting`);
  showStatus();
}

// `drawing` and `busy` are different waits and both are needed. `drawing` covers decoding a PNG,
// which is asynchronous and must not overlap itself or patches would land out of order. `busy` is
// the refresh the panel claims, which is a deliberate delay rather than work.
let drawing = false;
async function step() {
  if (drawing || busy || pending.length === 0) return;
  drawing = true;
  let patch;
  try {
    patch = pending.shift();
    await paint(patch);
  } catch (failure) {
    say(`could not paint a frame: ${failure}`);
    return;
  } finally {
    drawing = false;
  }
  if (honest) {
    busy = true;
    setTimeout(() => { busy = false; step(); }, CONFIG.claimed[patch.mode] || 0);
    return;
  }
  step();
}

async function present() {
  // The panel, resampled once into however many real screen pixels it is being shown in.
  const cssWidth = CONFIG.width / scale;
  const cssHeight = CONFIG.height / scale;
  const width = Math.max(1, Math.round(cssWidth * devicePixelRatio));
  const height = Math.max(1, Math.round(cssHeight * devicePixelRatio));
  if (canvas.width !== width || canvas.height !== height) {
    canvas.width = width;
    canvas.height = height;
  }
  // Sized from the integer backing store, not from the fractional ideal. Setting a 459 pixel
  // canvas to a width of 459.27 css pixels makes the compositor resample it a second time, by a
  // factor of 1.0006, which is enough to make stems uneven without being enough to see as a size
  // difference. One canvas pixel has to land on exactly one device pixel.
  canvas.style.width = width / devicePixelRatio + "px";
  canvas.style.height = height / devicePixelRatio + "px";
  if (width === panel.width && height === panel.height) {
    ctx.drawImage(panel, 0, 0);  // 1:1, so no resampling at all and the pixels are the device's
    return;
  }
  // resizeQuality "high" is a proper area resample rather than the browser's default when a
  // canvas is squeezed by CSS. Both engines support the option; if one ever stops, the catch
  // falls back to the old behaviour rather than showing nothing.
  try {
    const fitted = await createImageBitmap(panel, {
      resizeWidth: width,
      resizeHeight: height,
      resizeQuality: "high",
    });
    ctx.drawImage(fitted, 0, 0);
    fitted.close();
  } catch (failure) {
    ctx.imageSmoothingEnabled = true;
    ctx.imageSmoothingQuality = "high";
    ctx.drawImage(panel, 0, 0, panel.width, panel.height, 0, 0, width, height);
    say(`resampling fell back: ${failure}`);
  }
}

async function resize() {
  await present();
  showStatus();
}

function showStatus() {
  const mm = CONFIG.width / CONFIG.ppi * 25.4;
  // What the panel actually measures on the glass right now, so it can be checked with the same
  // ruler that calibrated the number. Millimetres rather than a density, because a density cannot
  // be held against a ruler.
  const shownMm = CONFIG.width / scale * devicePixelRatio / monitorPpi * 25.4;
  const claimed = CONFIG.claimed[lastMode];
  const ratio = Number.isInteger(scale) ? `1:${scale}` : `1:${scale.toFixed(2)}`;
  document.getElementById("status").textContent =
    `${ratio}  panel ${CONFIG.width}x${CONFIG.height} at ${CONFIG.ppi} ppi`
    + ` (${mm.toFixed(0)} mm wide)`
    + `   shown ${shownMm.toFixed(0)} mm wide on an assumed ${monitorPpi} ppi monitor`
    + `   refresh ${lastMode}${claimed ? " " + claimed + "ms claimed" : ""}`
    + `   ${honest ? "honest" : "fast"}   ${sent}`;
}

function setRuler() {
  const cssPx = 100 / 25.4 * monitorPpi / devicePixelRatio;
  document.getElementById("ruler").style.width = cssPx + "px";
}

for (const button of document.querySelectorAll("button[data-scale]")) {
  button.onclick = () => {
    trueSize = false;
    fit = false;
    scale = Number(button.dataset.scale);
    say(`scale 1:${scale}`);
    resize();
  };
}
function fitTrueSize() {
  // Exactly the panel's physical size, not the nearest whole-number scale.
  //
  // This rounded to an integer until 2026-09-17, which was a tkinter limitation carried over
  // without noticing: its photo images only subsample by whole numbers. CSS has no such rule, so
  // the panel can be the size it really is. On a 110 ppi monitor the rounding was showing a 107 mm
  // panel at 97 mm, and judging whether text is too small is the one thing this view is for.
  //
  // The cost is that the browser resamples 1264 columns into about 460, so the text is softer than
  // an e-ink panel at 300 ppi. Nothing on a 110 ppi monitor can show 300 ppi detail; what this does
  // show honestly is size.
  trueSize = true;
  fit = false;
  scale = CONFIG.ppi / monitorPpi * devicePixelRatio;
  say(`true size at an assumed ${monitorPpi} ppi is 1:${scale.toFixed(2)}`);
  resize();
}
document.getElementById("true-size").onclick = fitTrueSize;
document.getElementById("ppi").oninput = (event) => {
  monitorPpi = Number(event.target.value) || monitorPpi;
  localStorage.setItem("klide.ppi", monitorPpi);
  setRuler();
  if (trueSize) fitTrueSize();  // the number is what true size means, so re-fit rather than drift
  showStatus();
};
function fitToWindow() {
  // One scale for both axes, so the panel keeps its shape. The larger of the two ratios is the
  // one that fits: it shrinks to whichever dimension runs out first, and the other has room left
  // over, which is where the centring in the CSS puts the slack.
  fit = true;
  trueSize = false;
  // Floored, and measured with the fractional rect rather than the rounded `clientHeight`: the
  // header is not a whole number of pixels tall, so the room under it is not either, and
  // `present()` rounds the canvas to whole device pixels. Rounding both up puts a fraction of a
  // pixel of panel under the bottom edge of the window.
  const room = document.getElementById("wrap").getBoundingClientRect();
  const wide = Math.max(1, Math.floor(room.width));
  const tall = Math.max(1, Math.floor(room.height));
  scale = Math.max(CONFIG.width / wide, CONFIG.height / tall);
  say(`fitted to ${wide}x${tall} css px at 1:${scale.toFixed(2)}`);
  resize();
}

const modeButton = document.getElementById("mode");
function toggleReading() {
  reading = !reading;
  document.body.classList.toggle("reading", reading);
  modeButton.textContent = reading ? "diagnostics" : "reading";
  if (reading) {
    beforeReading = {scale: scale, trueSize: trueSize};
    say("reading mode");
    fitToWindow();
    return;
  }
  // Back to whatever was being looked at before, rather than to a default: the scale was chosen
  // for a reason and reading mode is a detour from it.
  fit = false;
  scale = beforeReading.scale;
  trueSize = beforeReading.trueSize;
  say(`diagnostics, back to 1:${scale.toFixed(2)}`);
  resize();
}
modeButton.onclick = toggleReading;

// A phone turned sideways, a window dragged wider, a desktop zoom: all of them change how much
// room there is, and a fit that only happened once would be wrong from then on.
addEventListener("resize", () => { if (fit) fitToWindow(); else resize(); });

const honestButton = document.getElementById("honest");
function toggleHonest() {
  honest = !honest;
  honestButton.classList.toggle("on", honest);
  say(honest ? "honest refresh on" : "honest refresh off, drawing as fast as it arrives");
  showStatus();
  step();
}
honestButton.onclick = toggleHonest;
honestButton.classList.toggle("on", honest);

document.getElementById("back").onclick = () => send({kind: "button", button: "back"});
document.getElementById("forward").onclick = () => send({kind: "button", button: "forward"});

function send(event) {
  const what = event.kind + (event.button ? " " + event.button : "")
             + (event.direction ? " " + event.direction : "");
  say(`sending ${what}`);
  const before = painted;
  fetch("input", {method: "POST", body: JSON.stringify(event)})
    .then(async (response) => {
      await response.text();  // drained, or the browser reports the request aborted
      sent = response.ok ? "sent " + what : "input refused: " + response.status + " " + what;
      say(`${what} answered ${response.status}`);
      showStatus();
      if (response.ok) watchForChange(what, before);
    })
    .catch((failure) => {
      sent = "input failed: " + failure;
      say(`${what} never left the browser: ${failure}`);
      showStatus();
    });
}

// A press the host correctly ignores and a press that never arrived look identical on the panel:
// nothing moves either way. Pressing page-forward at the live tail is the ordinary case of the
// first, and it is what made the buttons look dead. So when a press draws nothing, say so.
//
// The wait has to clear the slowest legitimate redraw: the host rendering and coalescing, the
// frame crossing whatever link this is, and an honest refresh playing out the mode it claims.
// Measured at about 0.35s end to end on one machine. Two seconds is headroom for a tunnel, and the
// first version of this was wrong for exactly that reason: it was set at 1.2s while a full screen
// was 2.8 MB, so it fired before every redraw rather than only when there was none.
function watchForChange(what, before) {
  setTimeout(() => {
    if (painted !== before) return;
    sent = `${what}: no change`;
    say(`${what} changed nothing on the panel`);
    showStatus();
  }, 2000 + (honest ? CONFIG.claimed.gc16 : 0));
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
stream.onopen = () => say("frame stream open");
stream.onmessage = (event) => { pending.push(JSON.parse(event.data)); step(); };
stream.onerror = () => {
  document.getElementById("status").textContent = "host disconnected, or the viewer stopped";
  say("frame stream closed");
  stream.close();
};

resize();
setRuler();
say(`ready, panel ${CONFIG.width}x${CONFIG.height} at 1:${scale},`
    + ` assuming a ${monitorPpi} ppi monitor at devicePixelRatio ${devicePixelRatio}`);
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


def describe(payload: dict[str, Any]) -> str:
    """An input event in words, for the log."""
    kind = payload.get("kind")
    if kind == "tap":
        return f"tap at ({payload.get('x')},{payload.get('y')})"
    if kind == "swipe":
        return f"swipe {payload.get('direction')}"
    if kind == "button":
        return f"button {payload.get('button')}"
    return str(kind)


def page_for(width: int, height: int, ppi: int) -> bytes:
    config = {
        "width": width,
        "height": height,
        "ppi": ppi,
        "claimed": CLAIMED_MS,
        "dragThreshold": DRAG_THRESHOLD_PX,
        "logPerSecond": LOG_PER_SECOND,
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
            if self.path == "/log":
                self._from_the_page()
                return
            if self.path != "/input":
                self.send_error(404)
                return
            length = int(self.headers.get("Content-Length", 0))
            try:
                payload = json.loads(self.rfile.read(length))
                bridge.send(input_from_json(payload), describe(payload))
            except (ProtocolError, ValueError, KeyError) as bad:
                log(f"refused an event from the browser: {bad}")
                self.send_error(400, str(bad))
                return
            self._body(b"", "text/plain")

        def _from_the_page(self) -> None:
            """One log line from the browser, into the same log as everything else.

            Kept to one line and one length limit, because this is the one route whose content is
            written by a page rather than by this process.
            """
            length = min(int(self.headers.get("Content-Length", 0)), 2000)
            line = self.rfile.read(length).decode("utf-8", "replace").replace("\n", " ")
            log(f"browser: {line}")
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
            """Every request the browser makes, except the frame stream.

            The stream is one long-lived request and says so when it opens and closes, so logging
            it here would add nothing. Everything else is logged because the question that could
            not be answered the first time someone used this was whether a click had reached the
            server at all.
            """
            request = str(args[0] if args else "")
            # /frames is one long-lived request that announces itself when it opens and closes, and
            # /log has already written the line it carried. Logging either here would double them.
            if "/frames" not in request and "/log" not in request:
                log(f"http {fmt % args}")

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
        log(f"cannot reach {args.host}:{args.port}: {refused}")
        log("is the klide host running, and is the port forwarded?")
        return 1
    log(f"connected to {args.host}:{args.port}")

    bridge = Bridge(sock, args.width, args.height)
    try:
        server = ThreadingHTTPServer(
            (args.bind, args.http_port),
            handler_for(bridge, page_for(args.width, args.height, args.ppi)),
        )
    except OSError as taken:
        # Almost always a viewer somebody forgot to stop. The traceback this used to raise named
        # the socket call rather than the situation, which is the wrong end of the problem.
        log(f"cannot serve on {args.bind}:{args.http_port}: {taken}")
        log("another viewer is probably still running. Find it with:")
        log("  pgrep -af klide_viewer")
        log(f"then stop it, or start this one on --http-port {args.http_port + 1}")
        sock.close()
        return 1
    log(f"open http://{args.bind}:{args.http_port}/")
    if args.bind == "127.0.0.1":
        log(f"from another machine, ssh -L {args.http_port}:localhost:{args.http_port} here")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        log("stopped")
    finally:
        sock.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
