"""A scripted session: input goes in, a frame comes out for every step.

This is what phase 3 means by the simulator being drivable without a person. Each step names
itself, does one thing, and leaves the screen in a state that gets written to a file and compared
against a reference. An agent changing the client logic sees which step's screen moved.

The script deliberately mixes the three kinds of step, because the difference between them is the
design question the client exists to answer:

- **Forwarded.** The device sends a gesture, the host renders and sends a page back. One round trip
  on top of the refresh.
- **Local.** The device answers from what it already holds, panning inside a page or redisplaying
  a cached one. A refresh, no round trip.
- **Neither.** Sleep, resume and losing the host, which involve no gesture at all.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from klide.device import Device, DeviceAsleepError, PageNotCachedError, Refresh
from klide.frame import Frame
from klide.host import HostLink
from klide.input import Direction, InputEvent
from klide.panel import Panel
from klide.protocol import ProtocolError
from klide.render import render_text
from klide.simulator import DeviceLink, display
from klide.waveform import Waveform

PAGE_SCREENS = 3
CONVERSATION_ID = 1
DIFF_ID = 2

# Hand-wrapped to fit the panel at the body text size, because the renderer does not wrap yet.
# Wrapping is layout and layout is phase 4; until then, text that runs past the right edge is
# clipped silently, which a test guards against.
INTROS = {
    CONVERSATION_ID: (
        "conversation",
        "A page taller than the screen. The\n"
        "device holds all of it and shows one\n"
        "screen at a time, so a page turn is\n"
        "answered on the device rather than by\n"
        "asking the host for another picture.",
    ),
    DIFF_ID: (
        "changed files",
        "The second view, sent because the\n"
        "device forwarded a swipe. This one\n"
        "arrives over the wire, which is the\n"
        "round trip a local answer avoids.",
    ),
}


# Enough numbered lines to fill a page of PAGE_SCREENS screens. A page whose last screen is blank
# makes a weak reference: the comparison passes on empty space rather than on content.
PAGE_LINES = 140


def page_text(page_id: int) -> str:
    """Numbered lines, so panning visibly moves the text and the step that clamps shows it."""
    title, intro = INTROS[page_id]
    lines = "\n".join(f"{i:3d}  line {i} of {title}" for i in range(PAGE_LINES))
    return f"{title}\n\n{intro}\n\n{lines}"


def render_page(page_id: int, panel: Panel) -> Frame:
    """A page several screens tall, which the device pans inside locally."""
    return render_text(page_text(page_id), panel, height=panel.height * PAGE_SCREENS)


Action = Callable[["Device", "DeviceLink"], None]


@dataclass(frozen=True)
class Step:
    """One named thing that happens, and the screen it leaves behind."""

    name: str
    act: Action
    note: str


def _forward(event: InputEvent) -> Action:
    """A gesture the client does not answer itself: send it and draw what comes back."""

    def act(device: Device, link: DeviceLink) -> None:
        link.send_input(event)
        link.receive_into(device)

    return act


def _pan(delta: int) -> Action:
    def act(device: Device, link: DeviceLink) -> None:
        device.pan(delta)

    return act


def _show_cached(page_id: int) -> Action:
    def act(device: Device, link: DeviceLink) -> None:
        device.show_cached(page_id)

    return act


def _sleep(device: Device, link: DeviceLink) -> None:
    device.sleep()


def _resume(device: Device, link: DeviceLink) -> None:
    device.resume()


def _lose_the_host(device: Device, link: DeviceLink) -> None:
    """Actually drop the connection, rather than only telling the device it dropped.

    Closing the socket is what makes this step worth running: the host's read fails, its script
    ends, and the device is left holding the last page with no way to ask for another.
    """
    link.close()
    device.disconnect()


def script(panel: Panel) -> list[Step]:
    """The steps, in order. Each one writes a frame."""
    screen = panel.height
    return [
        Step(
            "01-opened",
            _forward(InputEvent.tap(panel.width // 2, panel.height // 2)),
            "the host sends the first page, taller than the screen",
        ),
        Step("02-page-forward", _pan(screen), "the page-turn button, answered on the device"),
        Step(
            "03-page-forward-again",
            _pan(screen * 5),
            "a page turn that overshoots the end, so panning clamps instead of running past it",
        ),
        Step("04-page-back", _pan(-screen), "back up, still without asking the host"),
        Step(
            "05-switch-view",
            _forward(InputEvent.swipe(Direction.UP)),
            "a view change, which the host owns, so this one costs a round trip",
        ),
        Step(
            "06-back-to-cached",
            _show_cached(CONVERSATION_ID),
            "the first page again, from the cache, with no round trip",
        ),
        Step("07-asleep", _sleep, "suspended; the framebuffer survives"),
        Step("08-resumed", _resume, "awake, repainted from the cache with a flash"),
        Step(
            "09-disconnected",
            _lose_the_host,
            "the host is gone; the device keeps the page and draws its own banner",
        ),
    ]


def _wanted_page(event: InputEvent) -> int:
    """A swipe up or down changes view; anything else opens the conversation."""
    if event.direction in (Direction.UP, Direction.DOWN):
        return DIFF_ID
    return CONVERSATION_ID


def host_side(panel: Panel) -> Callable[[HostLink], None]:
    """The host's half of the script: answer each forwarded gesture with a page.

    It stops when the device closes the connection, which reaches it as a failed read. That is the
    normal end of a session rather than a fault, so it is caught here and nowhere else.
    """

    def run(link: HostLink) -> None:
        try:
            while True:
                page_id = _wanted_page(link.read_input())
                link.send_frame(render_page(page_id, panel), Waveform.GL16, page_id)
        except (ProtocolError, ConnectionError, OSError):
            return

    return run


@dataclass(frozen=True)
class StepResult:
    """What one step did: the screen it left, and what it cost the panel."""

    step: Step
    path: Path
    refreshes: list[Refresh]


def run_session(
    device: Device, link: DeviceLink, steps: list[Step], out_dir: Path
) -> list[StepResult]:
    """Run every step, writing the screen after each one.

    The refreshes a step caused are recorded as it runs. Reconstructing them afterwards from the
    device's history does not work, because the history has no step boundaries in it.
    """
    results: list[StepResult] = []
    for step in steps:
        before = len(device.history)
        step.act(device, link)
        results.append(
            StepResult(
                step=step,
                path=display(device.snapshot(), out_dir / f"{step.name}.png"),
                refreshes=device.history[before:],
            )
        )
    return results


def refresh_ledger(device: Device, results: list[StepResult]) -> str:
    """What each step cost the panel, as text.

    The images cannot carry this. Changing the refresh policy changes which waveform each update
    uses and how often the panel flashes, and none of that moves a pixel in a simulator that does
    not model ghosting (A2). Without this the gate would pass a client that had doubled its refresh
    budget. It is stored and compared exactly like a reference frame.
    """
    lines = []
    for result in results:
        if not result.refreshes:
            lines.append(f"{result.step.name}  no refresh")
            continue
        for refresh in result.refreshes:
            where = "local" if refresh.local else "from-host"
            lines.append(
                f"{result.step.name}  {refresh.mode.waveform.value}  {where}  "
                f"{refresh.mode.milliseconds}ms"
            )
    lines.append(f"total  {device.elapsed_ms}ms  refreshes {len(device.history)}")
    return "\n".join(lines) + "\n"


# The command


def run_and_capture(
    panel: Panel, socket_path: Path, out_dir: Path
) -> tuple[Device, list[StepResult]]:
    """Run the whole script with a real host on the other end of a real socket."""
    from concurrent.futures import ThreadPoolExecutor

    from klide.host import serve_script
    from klide.simulator import connect

    device = Device(panel=panel)
    steps = script(panel)
    with ThreadPoolExecutor(max_workers=1) as pool:
        serving = pool.submit(serve_script, socket_path, host_side(panel))
        with connect(socket_path, panel) as link:
            written = run_session(device, link, steps, out_dir)
        serving.result()
    return device, written


def report(device: Device) -> list[str]:
    """What the run cost, in the simulator's own claimed terms.

    Printed rather than asserted. These numbers move whenever the client's redraw policy changes,
    which is the point: a change that doubles the refresh budget shows up here. They are claims
    sourced from FBInk, not measurements of a Libra 2, and `waveform` says so at more length.
    """
    forwarded = sum(1 for r in device.history if not r.local)
    local = sum(1 for r in device.history if r.local)
    flashes = sum(1 for r in device.history if r.mode.flashes)
    modes = ", ".join(sorted({r.mode.waveform.value for r in device.history}))
    return [
        f"refreshes {len(device.history)} ({forwarded} from the host, {local} answered locally)",
        f"full refreshes {flashes}, modes used: {modes}",
        f"claimed panel time {device.elapsed_ms} ms",
        f"cached pages {sorted(device.pages)} of at most {device.cache_pages}",
    ]


def main(argv: list[str] | None = None) -> int:
    import argparse
    import tempfile

    from klide.compare import (
        ReferenceMissingError,
        compare,
        load_reference,
        save_frame,
        write_difference,
    )
    from klide.frame import Frame as _Frame
    from klide.panel import KOBO_LIBRA_2

    root = Path(__file__).resolve().parents[2]
    parser = argparse.ArgumentParser(description="Run the scripted simulator session.")
    parser.add_argument(
        "--update", action="store_true", help="write references instead of comparing"
    )
    args = parser.parse_args(argv)

    panel = KOBO_LIBRA_2
    out_dir = root / "build" / "frames" / "session"
    reference_dir = root / "tests" / "references" / "session"

    try:
        with tempfile.TemporaryDirectory(prefix="klide-") as tmp:
            device, written = run_and_capture(panel, Path(tmp) / "klide.sock", out_dir)
    except (PageNotCachedError, DeviceAsleepError) as broken:
        # A gate's failure has to say what to do, not raise (see meta/gates.md). A client that
        # cannot answer its own script is a client fault, so it is reported as one.
        print(f"session: the device could not complete the script: {broken}")
        print("session: the client logic changed in a way the script does not survive")
        return 1

    for line in report(device):
        print(f"session: {line}")

    failures = 0
    for result in written:
        step, produced = result.step, result.path
        reference_path = reference_dir / f"{step.name}.png"
        actual: _Frame = load_reference(produced, panel)
        if args.update:
            save_frame(actual, reference_path)
            continue
        try:
            expected = load_reference(reference_path, panel)
        except ReferenceMissingError as missing:
            print(f"session: {missing}")
            failures += 1
            continue
        comparison = compare(actual, expected, step.name)
        if not comparison.matched:
            failures += 1
            difference = out_dir / f"{step.name}.diff.png"
            write_difference(actual, expected, difference)
            print(f"session: {comparison.summary()}")
            print(f"session:   {step.note}")
            print(f"session:   difference {difference.relative_to(root)}, differing pixels in red")

    ledger = refresh_ledger(device, written)
    ledger_path = reference_dir / "refreshes.txt"
    if args.update:
        ledger_path.parent.mkdir(parents=True, exist_ok=True)
        ledger_path.write_text(ledger)
        print(f"session: wrote {len(written)} references to {reference_dir.relative_to(root)}")
        return 0
    if not ledger_path.exists():
        print(f"session: no refresh ledger at {ledger_path.relative_to(root)}; run with --update")
        failures += 1
    elif ledger_path.read_text() != ledger:
        failures += 1
        produced = out_dir / "refreshes.txt"
        produced.parent.mkdir(parents=True, exist_ok=True)
        produced.write_text(ledger)
        print("session: the refresh ledger changed, so the redraw policy moved")
        print(f"session:   expected {ledger_path.relative_to(root)}")
        print(f"session:   got      {produced.relative_to(root)}")
    if failures:
        print(f"session: {failures} finding(s) across {len(written)} steps and the ledger")
        print("session: if the change was intended, re-run with --update and review the diffs")
        return 1
    print(f"session: {len(written)} steps match their references")
    return 0
