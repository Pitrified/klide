"""Serve a live session to a viewer over TCP.

The host half of phase 5. It tails a real transcript, renders it, sends what changed, and reacts to
what the person at the other end presses. The viewer is `viewer/klide_viewer.py`, which ships as one
file to whatever machine has a screen.

This is not a gate and cannot be one: what it shows depends on a session nobody wrote for it, and
who presses what depends on a person. The deterministic checks over the same code are the `views`
gate, the streaming tests and the viewer conformance test.

One loop, polling three things, because a person pressing a button should not wait behind a
transcript poll:

- the transcript, for new turns
- the input queue, for presses the reader thread has taken off the socket
- the coalescer, for whether what has arrived is settled enough to be worth a refresh
"""

from __future__ import annotations

import queue
import sys
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path

from klide.frame import Frame
from klide.host import HostLink
from klide.input import Button, Direction, EventKind, InputEvent
from klide.panel import Panel
from klide.protocol import ProtocolError
from klide.render import Metrics, render_lines
from klide.stream import Coalescer, dirty_rectangle, pick_waveform
from klide.text import Line
from klide.transcript import Follower, Turn
from klide.views import conversation, lay_conversation


@dataclass
class LiveState:
    """What the viewer is looking at.

    `offset` counts turns back from the newest, and the bottom of the screen sits there. Zero means
    the live tail; pressing back walks into history and new turns stop scrolling the view out from
    under the reader.

    There is no window size. A fixed count of turns left the bottom two thirds of the panel blank
    whenever the recent turns were short shell calls, which is what a person sitting with it said
    first. The screen is filled instead: as many turns as fit, newest at the bottom, the oldest
    clipped at the top the way a terminal clips. `shown` is how many that turned out to be on the
    last render, and it is what a page turn moves by, so a press moves by a screenful whatever a
    screenful happens to be.
    """

    offset: int = 0
    turns: list[Turn] = field(default_factory=list)
    shown: int = 0
    #: A ceiling on how far back the fill will reach, for tests and for the browser harness. None
    #: means however many fit.
    cap: int | None = None

    @property
    def following(self) -> bool:
        return self.offset == 0

    def page_back(self) -> bool:
        """Older turns. Returns whether anything moved."""
        step = max(1, self.shown)
        room = max(0, len(self.turns) - self.shown)
        if self.offset >= room:
            return False
        self.offset = min(room, self.offset + step)
        return True

    def page_forward(self) -> bool:
        if self.offset == 0:
            return False
        self.offset = max(0, self.offset - max(1, self.shown))
        return True


class InputReader(threading.Thread):
    """Takes input events off the socket so the main loop never blocks on the person."""

    def __init__(self, link: HostLink, inbox: queue.Queue[InputEvent | None]) -> None:
        super().__init__(daemon=True)
        self.link = link
        self.inbox = inbox

    def run(self) -> None:
        try:
            while True:
                self.inbox.put(self.link.read_input())
        except (ProtocolError, ConnectionError, OSError):
            self.inbox.put(None)  # the viewer closed


def apply_event(event: InputEvent, state: LiveState) -> bool:
    """What a press does. Returns whether the screen needs redrawing.

    Deliberately small. The gesture map in the UI notes is provisional, and this phase exists to
    find out what a person actually reaches for rather than to implement a guess in full.
    """
    if event.kind is EventKind.BUTTON:
        if event.button is Button.PAGE_BACK:
            return state.page_back()
        if event.button is Button.PAGE_FORWARD:
            return state.page_forward()
        return False
    if event.kind is EventKind.SWIPE:
        if event.direction in (Direction.LEFT, Direction.UP):
            return state.page_back()
        if event.direction in (Direction.RIGHT, Direction.DOWN):
            return state.page_forward()
        return False
    if event.kind is EventKind.TAP:
        # A tap returns to the live tail, which is the one thing a reader who has wandered into
        # history always wants next.
        if state.offset:
            state.offset = 0
            return True
    return False


def describe(event: InputEvent) -> str:
    """An input event in words, for the log."""
    if event.kind is EventKind.BUTTON:
        return f"button {event.button.name.lower()}"
    if event.kind is EventKind.SWIPE:
        return f"swipe {event.direction.name.lower()}"
    if event.kind is EventKind.TAP:
        return f"tap at ({event.x},{event.y})"
    return str(event.kind)


def explain(moved: bool, state: LiveState) -> str:
    """Why a press did nothing, when it did nothing.

    A press that is correctly ignored and a press that never arrived look the same on the screen,
    which is exactly what happened the first time someone sat with the viewer: the page buttons
    appeared dead, and the reason was a transcript with no page to turn to.
    """
    if moved:
        return f"redraw, now {state.offset} turns back of {len(state.turns)}"
    if state.offset == 0 and len(state.turns) <= state.shown:
        return f"nothing to page to: all {len(state.turns)} turns are on the screen already"
    if state.offset == 0:
        return f"already at the live tail of {len(state.turns)} turns"
    return f"already at the oldest of {len(state.turns)} turns"


def title_for(state: LiveState) -> str:
    """What the header says. Named so a test can ask without rendering a panel.

    A reader who has paged back needs to see that they have, otherwise a quiet session and a stale
    screen look the same.
    """
    return "live" if state.following else f"history, {state.offset} back"


def fill(state: LiveState, metrics: Metrics) -> list[Line]:
    """The screen: a header at the top, and as many turns as fit sitting on the bottom margin.

    More turns are laid out than will fit and the last screenful of lines is kept, rather than
    turns being measured one at a time. Laying out the whole set at once is what keeps the speaker
    labels right, since whether a turn is labelled depends on the turn before it, and it makes the
    oldest turn on screen clip at the top instead of vanishing.

    The candidate set doubles until it overflows, so the work is proportional to what ends up on
    screen and not to the fifteen hundred turns behind it.
    """
    subtitle = f"{len(state.turns)} turns"
    title = title_for(state)
    head = len(conversation([], metrics, title=title, subtitle=subtitle).lines)
    available = max(0, metrics.lines_per_screen - head)

    end = len(state.turns) - state.offset
    take = 8
    body: list[Line] = []
    starts: list[int] = []
    while True:
        start = max(0, end - min(take, state.cap or take))
        column, starts = lay_conversation(state.turns[start:end], metrics, title, subtitle)
        body = column.lines[head:]
        reached_all = start == 0 or (state.cap is not None and take >= state.cap)
        if len(body) >= available or reached_all:
            break
        take *= 2

    while body and not body[-1].text:
        # The view puts a blank line after every turn. Keeping it would leave the newest line
        # floating one line above the bottom margin, which is the one place it must not float.
        body.pop()
    tail = body[-available:] if available else []
    cut = len(body) - len(tail)
    ends = [start - head for start in starts[1:]] + [len(body)]
    state.shown = sum(1 for stop in ends if stop > cut)

    blank = Line.of("", metrics.body())
    return column.lines[:head] + [blank] * (available - len(tail)) + tail


def render(state: LiveState, panel: Panel, metrics: Metrics) -> Frame:
    return render_lines(fill(state, metrics), panel, metrics)


def run(
    link: HostLink,
    transcript: Path,
    panel: Panel,
    metrics: Metrics,
    cap: int | None = None,
    seconds: float | None = None,
    tick: float = 0.05,
) -> LiveState:
    """Serve one viewer until it disconnects, or until `seconds` runs out."""
    state = LiveState(cap=cap)
    follower = Follower(transcript)
    coalescer = Coalescer()
    inbox: queue.Queue[InputEvent | None] = queue.Queue()
    InputReader(link, inbox).start()

    previous: Frame | None = None
    deadline = None if seconds is None else time.monotonic() + seconds

    def push() -> bool:
        """Send what changed. Returns False once the viewer has gone.

        A viewer is closed by a person, so its socket dying is the normal end of a session rather
        than a fault. Letting a broken pipe out of here would end a feedback sitting with a
        traceback, which is the wrong impression to leave with someone whose job is to tell us how
        it felt.
        """
        nonlocal previous
        page = render(state, panel, metrics)
        patch = page if previous is None else dirty_rectangle(previous, page)
        previous = page
        if patch is None:
            return True
        try:
            link.send_frame(patch, pick_waveform(patch, panel.height))
        except (BrokenPipeError, ConnectionError, OSError) as gone:
            # Say why. A silent swallow here would turn "the viewer closed" and "the frame was too
            # big to send before the socket timed out" into the same blank ending.
            print(f"serve: stopped sending: {gone}")
            return False
        return True

    if not push():  # something on screen before anything happens
        return state

    while True:
        if deadline is not None and time.monotonic() >= deadline:
            return state

        new = follower.poll()
        if new:
            state.turns.extend(new)
            if state.following:
                coalescer.changed()

        redraw = False
        try:
            while True:
                event = inbox.get_nowait()
                if event is None:
                    return state
                moved = apply_event(event, state)
                print(
                    f"serve: {describe(event)} -> {explain(moved, state)}",
                    file=sys.stderr,
                    flush=True,
                )
                redraw = moved or redraw
        except queue.Empty:
            pass

        # A press is answered at once; new content waits until it has settled.
        if redraw or coalescer.due():
            if not push():
                return state
            coalescer.sent()

        time.sleep(tick)
