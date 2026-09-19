"""The page stack, the tap and the back control.

Everything here is about where a press lands and what it opens. What the pages look like is the
`views` gate's, and what the loop around this does is `test_serve`.
"""

import json
import subprocess
from pathlib import Path

from klide.ahp import ChangesetFile, ChangesetState, FileEdit, SessionState
from klide.extract import ReadMarks
from klide.input import Button, Direction, EventKind, InputEvent
from klide.panel import KOBO_LIBRA_2
from klide.reader import (
    ChangesScreen,
    ConversationScreen,
    DiffScreen,
    Reader,
    SessionsScreen,
)
from klide.render import Metrics
from klide.views import Action, Page, sessions

METRICS = Metrics.for_panel(KOBO_LIBRA_2)


def tap(x: int, y: int) -> InputEvent:
    return InputEvent(kind=EventKind.TAP, x=x, y=y)


def press(button: Button) -> InputEvent:
    return InputEvent(kind=EventKind.BUTTON, button=button)


def a_changeset(*paths: str) -> ChangesetState:
    return ChangesetState(
        files=tuple(ChangesetFile(id=p, edit=FileEdit(path=p, added=3, removed=1)) for p in paths)
    )


def a_session(name: str, cwd: str = "", changeset: ChangesetState | None = None) -> SessionState:
    return SessionState(
        session_id=f"{name}-id",
        title=name,
        project="klide",
        branch="main",
        working_directories=(cwd,) if cwd else (),
        changeset=changeset or ChangesetState(),
    )


LIVE = [
    a_session("one", changeset=a_changeset("src/klide/views.py", "README.md")),
    a_session("two"),
]


def a_reader(projects: Path | None = None) -> Reader:
    reader = Reader.over(list(LIVE), METRICS)
    reader.projects = projects
    return reader


def row_of(reader: Reader, line: int) -> int:
    """The y coordinate at the middle of a screen row, which is where a thumb lands."""
    return int(METRICS.margin + line * METRICS.line_height + METRICS.line_height // 2)


def line_of(action: Action, value: str = "") -> int:
    return line_of_in(sessions(LIVE, METRICS), action, value)


def line_of_in(page: Page, action: Action, value: str = "") -> int:
    """Which column line a target sits on, which is what a test needs to aim a tap at."""
    for target in page.targets:
        if target.action is action and (not value or target.value == value):
            return target.line
    raise LookupError(f"no {action} target on the page")


def test_the_stack_starts_on_the_session_list() -> None:
    reader = a_reader()
    assert reader.path == "sessions"
    assert isinstance(reader.top, SessionsScreen)


def test_a_tap_on_a_row_opens_that_row() -> None:
    reader = a_reader()
    assert reader.act(tap(100, row_of(reader, line_of(Action.OPEN_SESSION, "two-id")))).redraw
    assert isinstance(reader.top, ConversationScreen)
    assert reader.top.state.title == "two"


def test_a_tap_on_the_first_row_does_not_open_the_second(tmp_path: Path) -> None:
    reader = a_reader()
    reader.act(tap(100, row_of(reader, line_of(Action.OPEN_SESSION, "one-id"))))
    assert isinstance(reader.top, ConversationScreen)
    assert reader.top.state.title == "one"


def test_a_tap_in_the_gap_between_two_rows_opens_neither() -> None:
    reader = a_reader()
    gap = line_of(Action.OPEN_SESSION, "two-id") - 1
    outcome = reader.act(tap(100, row_of(reader, gap)))
    assert not outcome.redraw
    assert "nothing to open" in outcome.note
    assert isinstance(reader.top, SessionsScreen)


def test_a_tap_above_the_top_margin_opens_nothing() -> None:
    reader = a_reader()
    assert not reader.act(tap(100, 2)).redraw


def test_the_last_row_is_reachable() -> None:
    reader = a_reader()
    last = line_of(Action.OPEN_SESSION, "two-id")
    assert reader.act(tap(100, row_of(reader, last))).redraw


def test_the_back_control_pops_the_stack() -> None:
    reader = a_reader()
    reader.act(tap(100, row_of(reader, line_of(Action.OPEN_SESSION, "one-id"))))
    back = next(t for t in reader.top.page(METRICS).targets if t.action is Action.BACK)
    assert reader.act(tap(KOBO_LIBRA_2.width - 60, row_of(reader, back.line))).redraw
    assert reader.path == "sessions"


def test_the_back_control_is_only_the_right_hand_end_of_its_line() -> None:
    # It shares the recap's first line (UD11), so a tap on the title is not a tap on it.
    reader = a_reader()
    reader.act(tap(100, row_of(reader, line_of(Action.OPEN_SESSION, "one-id"))))
    outcome = reader.act(tap(METRICS.margin + 5, row_of(reader, 0)))
    assert not outcome.redraw
    assert reader.path == "sessions > conversation"


def test_back_from_the_session_list_says_so_rather_than_emptying_the_stack() -> None:
    reader = a_reader()
    outcome = reader.pop()
    assert not outcome.redraw and "nothing to go back to" in outcome.note
    assert reader.path == "sessions"


def test_the_totals_in_the_recap_open_the_changes() -> None:
    reader = a_reader()
    reader.act(tap(100, row_of(reader, line_of(Action.OPEN_SESSION, "one-id"))))
    totals = next(t for t in reader.top.page(METRICS).targets if t.action is Action.OPEN_CHANGES)
    x = int(METRICS.margin + totals.x0 + 10)
    assert reader.act(tap(x, row_of(reader, totals.line))).redraw
    assert reader.path == "sessions > conversation > changes"


def test_the_rest_of_the_recap_is_not_a_target() -> None:
    # UD10: only the totals.
    reader = a_reader()
    reader.act(tap(100, row_of(reader, line_of(Action.OPEN_SESSION, "one-id"))))
    assert not reader.act(tap(METRICS.margin + 2, row_of(reader, 1))).redraw


def test_walking_all_four_pages_and_back(tmp_path: Path) -> None:
    repo = _a_repo(tmp_path)
    state = a_session("one", cwd=str(repo), changeset=a_changeset("kept.txt"))
    reader = Reader.over([state], METRICS)

    reader.act(
        tap(100, row_of(reader, line_of_in(sessions([state], METRICS), Action.OPEN_SESSION)))
    )
    totals = next(t for t in reader.top.page(METRICS).targets if t.action is Action.OPEN_CHANGES)
    reader.act(tap(int(METRICS.margin + totals.x0 + 10), row_of(reader, totals.line)))
    row = next(t for t in reader.top.page(METRICS).targets if t.action is Action.OPEN_FILE)
    assert reader.act(tap(100, row_of(reader, row.line))).redraw
    assert reader.path == "sessions > conversation > changes > diff"
    assert isinstance(reader.top, DiffScreen)
    assert "+three" in reader.top.text

    for expected in ("changes", "conversation", "sessions"):
        reader.pop()
        assert reader.path.endswith(expected)


def test_a_file_that_left_the_changeset_says_so(tmp_path: Path) -> None:
    repo = _a_repo(tmp_path, dirty=False)
    state = a_session("one", cwd=str(repo), changeset=a_changeset("kept.txt"))
    reader = Reader.over([state], METRICS)
    reader.push(ChangesScreen(state))
    outcome = reader.open_file("kept.txt")
    assert not outcome.redraw and "no diff" in outcome.note


def test_the_buttons_scroll_whatever_is_on_screen() -> None:
    many = [a_session(f"s{i}") for i in range(40)]
    reader = Reader.over(many, METRICS)
    assert reader.act(press(Button.PAGE_FORWARD)).redraw
    assert reader.top.offset > 0
    assert reader.act(press(Button.PAGE_BACK)).redraw
    assert reader.top.offset == 0


def test_a_press_at_the_edge_says_why_it_did_nothing() -> None:
    reader = a_reader()
    outcome = reader.act(press(Button.PAGE_BACK))
    assert not outcome.redraw
    assert "already at the top" in outcome.note and "sessions" in outcome.note


def test_a_short_page_cannot_be_scrolled() -> None:
    reader = a_reader()
    assert not reader.act(press(Button.PAGE_FORWARD)).redraw


def test_a_swipe_scrolls_and_does_not_walk_a_carousel() -> None:
    many = [a_session(f"s{i}") for i in range(40)]
    reader = Reader.over(many, METRICS)
    assert reader.act(InputEvent(kind=EventKind.SWIPE, direction=Direction.UP)).redraw
    assert isinstance(reader.top, SessionsScreen)


def test_every_ignored_event_leaves_a_reason() -> None:
    reader = a_reader()
    events = [
        tap(5, 5),
        press(Button.NONE),
        InputEvent(kind=EventKind.SWIPE, direction=Direction.NONE),
        press(Button.PAGE_BACK),
    ]
    for event in events:
        redraw, note = reader.handle(event)
        assert not redraw
        assert note.strip()


def test_tapping_into_a_session_marks_it_read(tmp_path: Path) -> None:
    marks = ReadMarks()
    reader = Reader(metrics=METRICS, marks=marks, stack=[SessionsScreen(list(LIVE))])
    reader.open_session("one-id")
    assert marks.is_read("one-id", [])


def test_a_session_that_left_the_list_is_refused(tmp_path: Path) -> None:
    reader = a_reader()
    outcome = reader.open_session("gone-id")
    assert not outcome.redraw and "no session" in outcome.note


def test_the_conversation_finds_its_transcript(tmp_path: Path) -> None:
    projects = tmp_path / "projects"
    cwd = "/home/pmn/repos/klide"
    folder = projects / cwd.replace("/", "-")
    folder.mkdir(parents=True)
    (folder / "one-id.jsonl").write_text(
        json.dumps({"type": "user", "uuid": "a", "message": {"role": "user", "content": "hello"}})
        + "\n"
    )
    reader = Reader.over([a_session("one", cwd=cwd)], METRICS)
    reader.projects = projects
    reader.open_session("one-id")
    assert isinstance(reader.top, ConversationScreen)
    assert [t.text for t in reader.top.live.turns] == ["hello"]


def _a_repo(tmp_path: Path, dirty: bool = True) -> Path:
    def git(*args: str) -> None:
        subprocess.run(["git", *args], cwd=tmp_path, check=True, capture_output=True)

    git("init", "-q", "-b", "main")
    git("config", "user.email", "t@example.com")
    git("config", "user.name", "t")
    (tmp_path / "kept.txt").write_text("one\ntwo\n")
    git("add", "-A")
    git("commit", "-qm", "first")
    if dirty:
        (tmp_path / "kept.txt").write_text("one\ntwo\nthree\n")
    return tmp_path
