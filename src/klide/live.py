"""Watch a real Claude Code session and put it on the simulator.

This is the first thing in the repo that reads something nobody wrote for it: a live transcript,
in a format internal to Claude Code, growing while it is read (D9). Everything before it rendered
constants.

It is not a gate and cannot be. What it shows depends on whatever session it watches, so nothing
here has a reference frame; the deterministic checks over the same code paths are the `views` gate
and the streaming tests. What this command is for is the last item phase 4 asks for, a real session
rendering and updating live, and for looking at klide with real content in it.

Read-only throughout (D11). It opens the transcript for reading and never writes to it, and
nothing it does can reach the session it is watching.
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

from klide.compare import save_frame
from klide.device import Device
from klide.frame import Frame
from klide.host import DEFAULT_PORT, serve
from klide.panel import KOBO_LIBRA_2, Panel
from klide.render import Metrics
from klide.serve import LiveState, render
from klide.serve import run as serve_live
from klide.stream import Coalescer, dirty_rectangle, pick_waveform
from klide.transcript import Turn, read, tail

ROOT = Path(__file__).resolve().parents[2]
PROJECTS = Path.home() / ".claude" / "projects"
ARTIFACTS = ROOT / "build" / "frames" / "live"


class NoTranscriptError(FileNotFoundError):
    """No session transcript was found to watch."""


def project_slug(project: Path) -> str:
    """Claude Code's directory name for a project: its absolute path with separators flattened."""
    return str(project.resolve()).replace("/", "-")


def newest_transcript(project: Path) -> Path:
    """The most recently written transcript for a project.

    Most recent rather than largest: the one being written to now is the one worth watching, and a
    long finished session is not.
    """
    folder = PROJECTS / project_slug(project)
    if not folder.is_dir():
        raise NoTranscriptError(f"no transcripts for {project} (looked in {folder})")
    files = sorted(folder.glob("*.jsonl"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not files:
        raise NoTranscriptError(f"no .jsonl transcripts in {folder}")
    return files[0]


def page_for(turns: list[Turn], panel: Panel, metrics: Metrics, cap: int | None) -> Frame:
    """Render the conversation the way the live loop does, so `--once` shows what it would show.

    The screen fills from the bottom with as many recent turns as fit. A long session lays out to
    dozens of screens and the reader of a second screen wants what just happened, not the whole
    history; the conversation list view is where a whole session gets opened deliberately.
    """
    return render(LiveState(turns=list(turns), cap=cap), panel, metrics)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--transcript", type=Path, help="a .jsonl to watch (default: newest for this project)"
    )
    parser.add_argument("--project", type=Path, default=ROOT, help="project to find a session for")
    parser.add_argument(
        "--seconds", type=float, default=None, help="how long to watch (default: until stopped)"
    )
    parser.add_argument(
        "--turns",
        type=int,
        default=None,
        help="stop filling after this many turns; the default is however many fit the screen",
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="render the transcript as it stands and exit, without watching",
    )
    parser.add_argument(
        "--serve",
        action="store_true",
        help="serve a viewer over TCP instead of writing frames to disk",
    )
    parser.add_argument("--bind", default="0.0.0.0", help="address to listen on with --serve")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument(
        "--wait", type=float, default=300.0, help="how long to wait for a viewer to connect"
    )
    args = parser.parse_args(argv)

    panel = KOBO_LIBRA_2
    metrics = Metrics.for_panel(panel)
    device = Device(panel=panel)

    try:
        path = args.transcript or newest_transcript(args.project)
    except NoTranscriptError as missing:
        print(f"live: {missing}", file=sys.stderr)
        return 1
    print(f"live: watching {path}")

    if args.serve:
        return _serve(path, panel, metrics, args)

    if args.once:
        existing = read(path)
        page = page_for(existing, panel, metrics, args.turns)
        device.receive(page, pick_waveform(page, panel.height))
        out = ARTIFACTS / "live.png"
        save_frame(device.snapshot(), out)
        print(f"live: {len(existing)} turns, wrote {out.relative_to(ROOT)}")
        return 0

    coalescer = Coalescer()
    turns: list[Turn] = []
    previous: Frame | None = None
    sent = 0
    started = time.monotonic()

    for turn in tail(path, poll=0.25, stop_after=args.seconds):
        turns.append(turn)
        coalescer.changed()
        if not coalescer.due():
            continue
        previous, sent = _send(device, turns, panel, metrics, args, previous, sent)
        coalescer.sent()

    # Whatever arrived in the last quiet period still deserves a frame.
    if coalescer.pending:
        previous, sent = _send(device, turns, panel, metrics, args, previous, sent)

    elapsed = time.monotonic() - started
    print(
        f"live: {len(turns)} turns in {elapsed:.0f}s, {sent} updates sent, "
        f"{device.elapsed_ms} ms of claimed panel time"
    )
    print(f"live: frames in {ARTIFACTS.relative_to(ROOT)}")
    return 0


def _serve(path: Path, panel: Panel, metrics: Metrics, args: argparse.Namespace) -> int:
    """Wait for a viewer and stream the session to it."""
    where = f"{args.bind}:{args.port}"
    print(f"live: waiting for a viewer on {where} (up to {args.wait:.0f}s)")
    print("live: in another terminal on this machine, run")
    print(f"live:   uv run viewer/klide_viewer.py --port {args.port}")
    print("live: then open the URL it prints, forwarding that port if you are elsewhere")
    try:
        with serve((args.bind, args.port), timeout=args.wait) as link:
            print("live: viewer connected")
            state = serve_live(link, path, panel, metrics, cap=args.turns, seconds=args.seconds)
    except TimeoutError:
        print(f"live: no viewer connected within {args.wait:.0f}s", file=sys.stderr)
        return 1
    print(f"live: viewer gone, {len(state.turns)} turns seen")
    return 0


def _send(
    device: Device,
    turns: list[Turn],
    panel: Panel,
    metrics: Metrics,
    args: argparse.Namespace,
    previous: Frame | None,
    sent: int,
) -> tuple[Frame, int]:
    """Draw the current page, sending only what changed."""
    page = page_for(turns, panel, metrics, args.turns)
    patch = page if previous is None else dirty_rectangle(previous, page)
    if patch is None:
        return page, sent
    device.receive(patch, pick_waveform(patch, panel.height))
    save_frame(device.snapshot(), ARTIFACTS / f"{sent:03d}.png")
    share = patch.height * 100 // panel.height
    print(f"live: update {sent}, {len(turns)} turns, patch {patch.height}px ({share}% of screen)")
    return page, sent + 1


if __name__ == "__main__":
    sys.exit(main())
