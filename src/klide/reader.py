"""The four pages as something a reader can walk: a stack, a tap and a back control.

UD2: navigation is a stack, down by tapping and up by the back control, and where the reader is
is the path they took. This replaces the swipe carousel the gesture map still describes.

U7 asked whether this lives inside the serve loop or above it, and the assessment in
`plans/07_reader_ui/00_start.md` said above: the loop does four things and three of them (draining
input, coalescing, sending what changed) have nothing to do with which page is on screen. So
`serve.run` takes a source, `Reader` is one, and the conversation-only host is another. The stack
lives here, between the loop and the pages.

A tap is answered by asking the layout which row the y coordinate landed in (UD3), which is why
the page functions return targets at all. Nothing on either side keeps a cursor.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from klide.ahp import SessionState
from klide.extract import ReadMarks, patch_for
from klide.extract import sessions as live_sessions
from klide.frame import Frame
from klide.input import Button, Direction, EventKind, InputEvent
from klide.panel import Panel
from klide.render import Metrics, render_lines
from klide.serve import LiveState, fill
from klide.text import Line
from klide.transcript import Follower, read
from klide.views import (
    Action,
    Page,
    Target,
    changes,
    conversation_page,
    one_diff,
    recap,
    sessions,
)


@dataclass(frozen=True)
class Rendered:
    """One screenful: the lines drawn, and which column line each screen row came from.

    `rows` is what turns a y coordinate back into a target. It is not always `range(offset, ...)`:
    the conversation fills from the bottom, so the rows between its header and its newest turn are
    filler that came from no line at all, and those carry -1.
    """

    lines: list[Line]
    rows: list[int]

    def line_at(self, row: int) -> int:
        return self.rows[row] if 0 <= row < len(self.rows) else -1


class Screen:
    """One page on the stack.

    Scrolling is lines from the top, which is right for three of the four pages. The conversation
    overrides it, because it is anchored to the bottom and counts in turns.
    """

    def __init__(self) -> None:
        self.offset = 0

    def page(self, metrics: Metrics) -> Page:
        raise NotImplementedError

    def poll(self) -> bool:
        """Whether the source behind this page has moved. False for a page nothing feeds."""
        return False

    def rendered(self, metrics: Metrics) -> Rendered:
        page = self.page(metrics)
        available = metrics.lines_per_screen
        start = self.offset
        lines = page.column.lines[start : start + available]
        return Rendered(lines, list(range(start, start + len(lines))))

    def scroll(self, forward: bool, metrics: Metrics) -> bool:
        """A screenful at a time, per UD4. Returns whether anything moved."""
        total = len(self.page(metrics).column.lines)
        step = max(1, metrics.lines_per_screen - 1)
        target = self.offset + step if forward else self.offset - step
        target = max(0, min(target, max(0, total - metrics.lines_per_screen)))
        if target == self.offset:
            return False
        self.offset = target
        return True

    def where(self) -> str:
        """One line for the log, so an ignored press says which page ignored it."""
        return type(self).__name__.removesuffix("Screen").lower()


class SessionsScreen(Screen):
    """Page 1."""

    def __init__(self, states: list[SessionState]) -> None:
        super().__init__()
        self.states = states

    def page(self, metrics: Metrics) -> Page:
        return sessions(self.states, metrics)


class ConversationScreen(Screen):
    """Page 2, which is the host as it already was, under a recap.

    `LiveState` keeps its meaning: an offset in turns back from the newest, and a screen filled
    from the bottom. The generic line offset above would be wrong here, so both scrolling and
    rendering are overridden rather than reused.
    """

    def __init__(self, state: SessionState, transcript: Path | None) -> None:
        super().__init__()
        self.state = state
        self.live = LiveState(turns=read(transcript) if transcript else [])
        self.follower = Follower(transcript) if transcript else None
        if self.follower is not None:
            # The transcript has just been read whole; start following from where that ended.
            self.follower.poll()

    def page(self, metrics: Metrics) -> Page:
        return conversation_page(self.state, self.live.turns, metrics)[0]

    def poll(self) -> bool:
        if self.follower is None:
            return False
        new = self.follower.poll()
        if not new:
            return False
        self.live.turns.extend(new)
        return self.live.following

    def rendered(self, metrics: Metrics) -> Rendered:
        lines = fill(self.live, metrics, session=self.state)
        head = _recap_height(self.state, metrics)
        # Only the recap is tappable, and it is always the top of the screen. Everything under it
        # is conversation, which has nothing to open.
        rows = [row if row < head else -1 for row in range(len(lines))]
        return Rendered(lines, rows)

    def scroll(self, forward: bool, metrics: Metrics) -> bool:
        return self.live.page_forward() if forward else self.live.page_back()


class ChangesScreen(Screen):
    """Page 3."""

    def __init__(self, state: SessionState) -> None:
        super().__init__()
        self.state = state
        self.stale = False

    def page(self, metrics: Metrics) -> Page:
        return changes(self.state, metrics, stale=self.stale)


class DiffScreen(Screen):
    """Page 4."""

    def __init__(self, state: SessionState, path: str, text: str) -> None:
        super().__init__()
        self.state = state
        self.path = path
        self.text = text
        self.stale = False

    def page(self, metrics: Metrics) -> Page:
        return one_diff(self.path, self.text, metrics, stale=self.stale)


def _recap_height(state: SessionState, metrics: Metrics) -> int:
    """How many lines the recap takes, which is where the conversation body starts."""
    column = metrics.column()
    recap(state, column, metrics)
    return len(column.lines)


@dataclass
class Outcome:
    """What an event did, and what to say about it when it did nothing.

    The second half is the point. A press that is correctly ignored and a press that never arrived
    look the same on a panel, which is the diary review's fifth pattern and cost a day the first
    time someone sat with the viewer.
    """

    redraw: bool
    note: str


@dataclass
class Reader:
    """The stack, and everything that moves it.

    Page 1 is always at the bottom of it, so the back control can never empty it.
    """

    metrics: Metrics
    marks: ReadMarks = field(default_factory=ReadMarks)
    stack: list[Screen] = field(default_factory=list)
    projects: Path | None = None

    @classmethod
    def over(cls, states: list[SessionState], metrics: Metrics) -> Reader:
        return cls(metrics=metrics, stack=[SessionsScreen(states)])

    @property
    def top(self) -> Screen:
        return self.stack[-1]

    @property
    def listed(self) -> list[SessionState]:
        """What page 1 is showing. Page 1 is always the bottom of the stack."""
        return self._sessions().states

    @property
    def path(self) -> str:
        return " > ".join(screen.where() for screen in self.stack)

    def poll(self) -> bool:
        return self.top.poll()

    def frame(self, panel: Panel, metrics: Metrics) -> Frame:
        return render_lines(self.top.rendered(metrics).lines, panel, metrics)

    def row_at(self, y: int) -> int:
        """Which screen row a y coordinate is in. Negative above the top margin."""
        if y < self.metrics.margin:
            return -1
        return (y - self.metrics.margin) // self.metrics.line_height

    def target_at(self, x: int, y: int) -> Target | None:
        """What a tap landed on, if anything."""
        drawn = self.top.rendered(self.metrics)
        line = drawn.line_at(self.row_at(y))
        if line < 0:
            return None
        for target in self.top.page(self.metrics).targets:
            if not target.covers(line):
                continue
            left = x - self.metrics.margin
            if left < target.x0:
                continue
            if target.x1 and left > target.x1:
                continue
            return target
        return None

    def handle(self, event: InputEvent) -> tuple[bool, str]:
        """The loop's side of it: whether to redraw, and what to log either way."""
        outcome = self.act(event)
        return outcome.redraw, outcome.note

    def act(self, event: InputEvent) -> Outcome:
        if event.kind is EventKind.BUTTON:
            if event.button is Button.PAGE_BACK:
                return self._scrolled(forward=False)
            if event.button is Button.PAGE_FORWARD:
                return self._scrolled(forward=True)
            return Outcome(False, f"no meaning for {event.button.name.lower()} on {self.path}")
        if event.kind is EventKind.SWIPE:
            # Up and down scroll, which is what a swipe on a page of text should do. Left and
            # right used to walk the carousel of views; the stack replaced that (UD2), and a swipe
            # that quietly did nothing is what the log line below exists to prevent.
            if event.direction in (Direction.UP, Direction.LEFT):
                return self._scrolled(forward=True)
            if event.direction in (Direction.DOWN, Direction.RIGHT):
                return self._scrolled(forward=False)
            return Outcome(False, f"no meaning for swipe {event.direction.name.lower()}")
        if event.kind is EventKind.TAP:
            return self._tapped(event)
        return Outcome(False, f"unknown event kind {event.kind}")

    def _scrolled(self, forward: bool) -> Outcome:
        if self.top.scroll(forward, self.metrics):
            return Outcome(True, f"scrolled {'down' if forward else 'up'} on {self.path}")
        edge = "bottom" if forward else "top"
        return Outcome(False, f"already at the {edge} of {self.path}")

    def _tapped(self, event: InputEvent) -> Outcome:
        target = self.target_at(event.x, event.y)
        if target is None:
            return Outcome(False, f"nothing to open at ({event.x},{event.y}) on {self.path}")
        if target.action is Action.BACK:
            return self.pop()
        if target.action is Action.OPEN_SESSION:
            return self.open_session(target.value)
        if target.action is Action.OPEN_CHANGES:
            return self.push(ChangesScreen(self._state()))
        if target.action is Action.OPEN_FILE:
            return self.open_file(target.value)
        # REFRESH is phase 4's; until then say so rather than looking broken.
        return Outcome(False, f"{target.action} is not wired up yet")

    def _state(self) -> SessionState:
        for screen in reversed(self.stack):
            if isinstance(screen, ConversationScreen | ChangesScreen | DiffScreen):
                return screen.state
        raise LookupError("no session on the stack")

    def push(self, screen: Screen) -> Outcome:
        self.stack.append(screen)
        return Outcome(True, f"opened {self.path}")

    def pop(self) -> Outcome:
        if len(self.stack) == 1:
            return Outcome(False, "already on the session list, nothing to go back to")
        self.stack.pop()
        return Outcome(True, f"back to {self.path}")

    def open_session(self, session_id: str) -> Outcome:
        state = next(
            (s for s in self._sessions().states if s.session_id == session_id),
            None,
        )
        if state is None:
            return Outcome(False, f"no session {session_id[:8]} on the list any more")
        transcript = self._transcript(state)
        screen = ConversationScreen(state, transcript)
        # UD12: tapping in is what marks a session read.
        self.marks.mark(session_id, screen.live.turns)
        return self.push(screen)

    def open_file(self, path: str) -> Outcome:
        state = self._state()
        text = patch_for(Path(state.cwd), path) if state.cwd else ""
        if not text:
            # A file with no patch is usually one that left the changeset between the tree being
            # drawn and the row being tapped, which is exactly what phase 4's marker is for.
            return Outcome(False, f"no diff for {path} any more")
        return self.push(DiffScreen(state, path, text))

    def _sessions(self) -> SessionsScreen:
        bottom = self.stack[0]
        assert isinstance(bottom, SessionsScreen)
        return bottom

    def _transcript(self, state: SessionState) -> Path | None:
        if self.projects is None:
            from klide.extract import PROJECTS

            root = PROJECTS
        else:
            root = self.projects
        path = root / state.cwd.replace("/", "-") / f"{state.session_id}.jsonl"
        return path if path.is_file() else None


def from_this_host(metrics: Metrics, marks: ReadMarks | None = None) -> Reader:
    """A reader over whatever sessions are running here."""
    marks = marks or ReadMarks()
    return Reader(metrics=metrics, marks=marks, stack=[SessionsScreen(live_sessions(marks))])
