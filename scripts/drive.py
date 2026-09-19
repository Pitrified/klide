#!/usr/bin/env python3
"""Drive the klide viewer in a real browser, by hand.

    uv run python scripts/drive.py --do "shot before" --do "click #back" --do "wait 1"

Not a gate. `scripts/check.sh` does not run this and CI does not either, which is deliberate: it
needs a browser downloaded (`uv run playwright install chromium`, once), and what it checks is
whether a person can use the thing, which is a question with no reference frame to compare against.
Whether a stricter version of it should become a gate is V5 in `plans/04_klide_app/05_viewer.md`.

What it is for: the viewer's page had never run anywhere its author could see it. The page-turn
buttons did nothing when clicked, every server-side probe said the path worked, and there was no
way to tell where between the click and the socket the event stopped. Four things had to be read
together to find out, and they lived in four places. This puts them in one stream, in time order:

    browser  klide: sending button back
    viewer:  http "POST /input HTTP/1.1" 200 -
    viewer:  sent button back to the host, 17 bytes
    host:    serve: button page_back -> redraw, now 6 turns back of 1273
    viewer:  frame 1264x773 at (0,58) gl16 to 1 watching

Screenshots go to build/browser/ so the page can be looked at rather than described. Nothing is
compared against a reference: this is an instrument, and the judgement is a person's.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import threading
import time
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

try:
    from playwright.sync_api import ConsoleMessage, Page, Request, sync_playwright
except ImportError:  # pragma: no cover - the message is the point
    print("drive: playwright is not installed. From the repo root:", file=sys.stderr)
    print("drive:   uv add --dev playwright", file=sys.stderr)
    print("drive:   uv run playwright install chromium", file=sys.stderr)
    raise SystemExit(1) from None

ROOT = Path(__file__).resolve().parents[1]
SHOTS = ROOT / "build" / "browser"

START = time.monotonic()


def out(source: str, line: str) -> None:
    """One line of the single stream, stamped from the start of the run.

    Everything gets the same shape, because the point is to read four sources as one sequence and
    anything that formats itself differently has to be mentally re-sorted.
    """
    print(f"{time.monotonic() - START:6.2f}  {source:8s} {line}", flush=True)


def pump(stream: object, source: str) -> None:
    """Forward a subprocess's output into the stream as it arrives."""
    for raw in iter(stream.readline, ""):  # type: ignore[attr-defined]
        out(source, raw.rstrip())


@contextmanager
def background(name: str, command: list[str]) -> Iterator[subprocess.Popen[str]]:
    """A klide process, its output folded into the stream, stopped on the way out."""
    process = subprocess.Popen(
        command,
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )
    threading.Thread(target=pump, args=(process.stdout, name), daemon=True).start()
    try:
        yield process
    finally:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()


class Driver:
    """The verbs, one method each. Adding one is adding a method and a line to `run`."""

    def __init__(self, page: Page, width: int, height: int) -> None:
        self.page = page
        self.width = width
        self.height = height

    def run(self, action: str) -> None:
        verb, _, rest = action.strip().partition(" ")
        rest = rest.strip()
        out("do", action)
        if verb == "click":
            self.page.click(rest)
        elif verb == "key":
            self.page.keyboard.press(rest)
        elif verb == "tap":
            x, y = (int(n) for n in rest.split())
            self.drag_or_tap(x, y, x, y)
        elif verb == "drag":
            x0, y0, x1, y1 = (int(n) for n in rest.split())
            self.drag_or_tap(x0, y0, x1, y1)
        elif verb == "wait":
            time.sleep(float(rest))
        elif verb == "shot":
            self.shot(rest)
        elif verb == "text":
            out("text", f"{rest}: {self.page.inner_text(rest)}")
        elif verb == "eval":
            out("eval", f"{rest} -> {self.page.evaluate(rest)!r}")
        else:
            raise SystemExit(f"drive: no such action {verb!r} in {action!r}")

    def drag_or_tap(self, x0: int, y0: int, x1: int, y1: int) -> None:
        """Press and release on the canvas, in panel coordinates rather than page ones.

        The canvas is drawn at whatever scale is chosen, so a click at panel (600, 800) is
        somewhere else on the page. Converting here means an action can name a place on the device
        without knowing how the page is scaled, which is the coordinate system everything else in
        klide uses.
        """
        box = self.page.locator("#panel").bounding_box()
        if box is None:
            raise SystemExit("drive: the canvas is not on the page")

        def place(x: int, y: int) -> tuple[float, float]:
            return (
                box["x"] + x / self.width * box["width"],
                box["y"] + y / self.height * box["height"],
            )

        self.page.mouse.move(*place(x0, y0))
        self.page.mouse.down()
        self.page.mouse.move(*place(x1, y1))
        self.page.mouse.up()

    def shot(self, name: str) -> None:
        """The whole page and the panel alone, so either can be looked at."""
        SHOTS.mkdir(parents=True, exist_ok=True)
        whole = SHOTS / f"{name}.png"
        panel = SHOTS / f"{name}-panel.png"
        self.page.screenshot(path=whole, full_page=True)
        self.page.locator("#panel").screenshot(path=panel)
        out("shot", f"{whole.relative_to(ROOT)} and {panel.relative_to(ROOT)}")


def watch(page: Page) -> None:
    """Everything the browser has to say, into the same stream.

    Console and page errors are separate events in Playwright and an uncaught exception raises
    `pageerror` without necessarily reaching `console`, so both are listened for. A failed request
    is listened for because a POST that never arrives is the failure this was built to find, and it
    is invisible from both ends otherwise.
    """
    page.on("console", lambda message: out("browser", console_line(message)))
    page.on("pageerror", lambda error: out("browser", f"UNCAUGHT {error}"))
    page.on("requestfailed", lambda request: out("browser", request_line(request)))


def console_line(message: ConsoleMessage) -> str:
    text = message.text
    if message.type in ("error", "warning"):
        return f"{message.type.upper()} {text}"
    return text


def request_line(request: Request) -> str:
    failure = request.failure or "no reason given"
    return f"REQUEST FAILED {request.method} {request.url}: {failure}"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Drive the klide viewer in a browser.")
    parser.add_argument("--do", action="append", default=[], metavar="ACTION", help="an action")
    parser.add_argument(
        "--url", help="drive a viewer already running here, rather than starting one"
    )
    parser.add_argument("--port", type=int, default=5100, help="klide's port, when starting one")
    parser.add_argument("--http-port", type=int, default=8100, help="the viewer's port")
    parser.add_argument("--transcript", help="a .jsonl for the host to render")
    parser.add_argument(
        "--pages",
        action="store_true",
        help="start the host on the session list, so the whole four-page walk can be driven",
    )
    parser.add_argument(
        "--turns",
        type=int,
        default=None,
        help="cap how far back the host fills; the default is however many fit the screen",
    )
    parser.add_argument("--headed", action="store_true", help="show the browser window")
    parser.add_argument(
        "--browser",
        default="chromium",
        choices=("chromium", "firefox", "webkit"),
        help="which engine to drive; a bug in one is invisible to the others",
    )
    parser.add_argument("--width", type=int, default=1264, help="panel width in pixels")
    parser.add_argument("--height", type=int, default=1680, help="panel height in pixels")
    parser.add_argument("--settle", type=float, default=2.0, help="seconds to wait after loading")
    args = parser.parse_args(argv)

    if args.url:
        drive(args, args.url)
        return 0

    host = ["uv", "run", "klide-live", "--serve", "--port", str(args.port)]
    if args.pages:
        host += ["--pages"]
    if args.turns is not None:
        host += ["--turns", str(args.turns)]
    if args.transcript:
        host += ["--transcript", args.transcript]
    viewer = [
        "uv", "run", "viewer/klide_viewer.py",
        "--port", str(args.port),
        "--http-port", str(args.http_port),
    ]  # fmt: skip
    with background("host:", host):
        time.sleep(3)  # the host binds before the viewer can connect to it
        with background("viewer:", viewer):
            time.sleep(2)
            drive(args, f"http://127.0.0.1:{args.http_port}/")
    return 0


def drive(args: argparse.Namespace, url: str) -> None:
    with sync_playwright() as playwright:
        engine = getattr(playwright, args.browser)
        browser = engine.launch(headless=not args.headed)
        out("drive", f"{args.browser} {browser.version}")
        page = browser.new_page(viewport={"width": 1400, "height": 1000})
        watch(page)
        out("drive", f"opening {url}")
        page.goto(url, wait_until="domcontentloaded")
        time.sleep(args.settle)  # the first frame is a megabyte and arrives over the event stream

        driver = Driver(page, args.width, args.height)
        try:
            for action in args.do:
                driver.run(action)
        finally:
            time.sleep(0.5)  # let anything in flight say so before the log stops
            browser.close()


if __name__ == "__main__":
    sys.exit(main())
