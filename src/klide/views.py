"""The four pages a reader walks, and what each one puts on a page.

The set was six views built from a rough list. It is now the four pages of `plans/07_reader_ui`:
the session list, one conversation, the changed files as a tree, and one file's diff. Two of the
six folded into the tree (UD8) and `one_file` stays here with no route to it (U5).

A view takes plain data and returns a `Page`: a `Column` and the targets in it. It does not fetch
anything, render anything, or know how tall the page will be. That is what makes a view checkable
without a panel: a test can read the lines and their styles, and the frame comparison covers what
they look like afterwards.

Targets are here rather than in the navigation because the layout is what knows where things
landed (UD3). A target names the lines it covers, so a tap at a y coordinate maps back to the row
the reader was pointing at without either side keeping a cursor.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

from klide.ahp import ChangesetState, ChangesetStatus, SessionState
from klide.document import code, markdown
from klide.document import diff as lay_diff
from klide.fonts import FAINT, INK, MUTED, STRONG
from klide.render import Metrics, rule
from klide.text import Column, Line, Run, Style
from klide.transcript import BlockKind, Role, Turn


class View(StrEnum):
    """What the gate renders. The four pages, plus the two cases worth a reference of their own."""

    SESSIONS = "sessions"
    CONVERSATION = "conversation"
    CHANGES = "changes"
    CHANGES_EMPTY = "changes-empty"
    DIFF = "diff"
    FILE = "file"


class Action(StrEnum):
    """What tapping a target does. Phase 2 owns what each one means to the stack."""

    BACK = "back"
    OPEN_SESSION = "open-session"
    OPEN_CHANGES = "open-changes"
    OPEN_FILE = "open-file"
    REFRESH = "refresh"


@dataclass(frozen=True)
class Target:
    """Something on the page a tap can land on.

    `line` and `span` are indices into the column, not pixels, because the column is laid out
    before anyone knows how tall a line will be drawn or where the page will be scrolled to.
    Turning them into a y range is the renderer's job and the scroll position's.

    `x0` and `x1` are pixels from the left margin, and `x1` of zero means "to the right edge". Only
    the controls that share a line with something else need them; a whole row leaves them at zero.
    """

    action: Action
    line: int
    span: int = 1
    value: str = ""
    x0: float = 0.0
    x1: float = 0.0

    def covers(self, line: int) -> bool:
        return self.line <= line < self.line + self.span


@dataclass(frozen=True)
class Page:
    """A laid-out page: the lines, and what can be tapped in them."""

    column: Column
    targets: tuple[Target, ...] = ()

    @property
    def lines(self) -> list[Line]:
        return self.column.lines


#: What the back control says. Text rather than a glyph alone: it is the one control on every page
#: and a reader should not have to learn it.
BACK = "\u2190 back"

#: What a page says when the changeset behind it has moved (UD7). It is also the refresh control
#: (UD9), so it is a word and not a dot: something to be tapped has a minimum size that something
#: to be read does not.
STALE = "\u25cf stale, tap to refresh"


def _right(column: Column, metrics: Metrics, left: str, style: Style, right: str) -> float:
    """One line with something at the left margin and something against the right edge.

    Returns where the right-hand piece starts, which is what makes it a tap target. Placed by
    measuring and padding rather than by counting spaces: the body face is proportional, so the
    number of spaces that fills a gap depends on what precedes it.
    """
    right_style = metrics.body(MUTED)
    right_width = right_style.font().getlength(right)
    start = max(style.font().getlength(left), column.width - right_width)
    column.lines.append(
        Line((Run(left, style), Run(right, right_style, pad=start - style.font().getlength(left))))
    )
    return start


def _header(title: str, subtitle: str, column: Column, metrics: Metrics) -> None:
    column.add(title, metrics.heading(STRONG))
    if subtitle:
        column.add(subtitle, metrics.body(MUTED))
    column.lines.append(rule(metrics))
    column.blank(metrics.body())


def recap(
    state: SessionState, column: Column, metrics: Metrics, stale: bool = False
) -> list[Target]:
    """The strip pages 2 and 3 open with: who, where, and how big the change is.

    Two lines and a rule. The back control shares the first of them (UD11), so it costs no vertical
    space of its own; what it costs instead is the width of the first line, which is why the title
    is the thing that shares it and the longer second line does not.

    The diff totals are the only part of this a tap means anything on (UD10).
    """
    targets: list[Target] = []
    title_style = metrics.heading(STRONG)
    at = _right(column, metrics, state.title or state.session_id[:8], title_style, BACK)
    targets.append(Target(Action.BACK, line=len(column.lines) - 1, x0=at))

    change = state.changeset
    where = f"{state.project}@{state.branch}" if state.branch else state.project
    if change.status is ChangesetStatus.ERROR:
        totals = "no diff"
    elif change.is_empty:
        totals = "clean"
    else:
        totals = f"+{change.added} -{change.removed} in {len(change.files)}"
    prefix = f"{where}   "
    body = metrics.body(MUTED)
    column.lines.append(Line((Run(prefix, body), Run(totals, metrics.bold(INK)))))
    targets.append(
        Target(
            Action.OPEN_CHANGES,
            line=len(column.lines) - 1,
            x0=body.font().getlength(prefix),
        )
    )

    if stale:
        column.add(STALE, metrics.bold(INK))
        targets.append(Target(Action.REFRESH, line=len(column.lines) - 1))
    column.lines.append(rule(metrics))
    column.blank(metrics.body())
    return targets


#: What a turn is labelled with. The label carries the role, so the body does not have to repeat it
#: and a reader can skim the left edge to find where an answer starts.
_ROLE_LABEL = {Role.USER: "you", Role.ASSISTANT: "claude", Role.SYSTEM: "system"}


def conversation(
    turns: list[Turn],
    metrics: Metrics,
    title: str = "conversation",
    subtitle: str | None = None,
    state: SessionState | None = None,
) -> Column:
    """The main view, for callers that only want the lines."""
    return lay_conversation(turns, metrics, title, subtitle, state)[0]


def conversation_page(
    state: SessionState, turns: list[Turn], metrics: Metrics
) -> tuple[Page, list[int]]:
    """Page 2: the recap, then the conversation, and where each turn began.

    The starts are what lets the loop fill the screen from the bottom, so they come back out of
    here the way they came out of `lay_conversation` before there was a page around it.
    """
    column, starts = lay_conversation(turns, metrics, state=state)
    return Page(column, tuple(_recap_targets(state, metrics, column))), starts


def _recap_targets(state: SessionState, metrics: Metrics, column: Column) -> list[Target]:
    """The recap's targets, recovered after the fact.

    `lay_conversation` writes the recap itself, because whether a turn gets a speaker label
    depends on laying the whole column out in one go. Rather than thread the targets back through
    that, the recap is laid out a second time into a throwaway column: it is four lines, and the
    alternative is a return value every caller of `lay_conversation` would have to carry.
    """
    scratch = Column(width=column.width)
    return recap(state, scratch, metrics)


def lay_conversation(
    turns: list[Turn],
    metrics: Metrics,
    title: str = "conversation",
    subtitle: str | None = None,
    state: SessionState | None = None,
) -> tuple[Column, list[int]]:
    """The main view, and where in the column each turn began.

    The starts are what lets a caller fill a screen from the bottom: it lays out more turns than
    fit, keeps the last screenful of lines, and needs to know how many turns that covered. Doing it
    this way rather than laying out one turn at a time keeps the speaker labels right, since
    whether a turn is labelled depends on the turn before it.

    Tool calls are one line each, not folded out. On a screen this size the useful thing is that a
    tool ran and what it touched, and a reader who wants the output has the file open on the other
    machine. Tool results are skipped for the same reason: they are usually long and rarely the
    thing being followed.
    """
    column = metrics.column()
    if state is not None:
        recap(state, column, metrics)
    else:
        _header(title, f"{len(turns)} turns" if subtitle is None else subtitle, column, metrics)

    starts: list[int] = []
    spoken: Role | None = None
    for turn in turns:
        before = len(column.lines)
        for block in turn.blocks:
            if block.kind is BlockKind.TEXT:
                markdown(block.text, column, metrics)
            elif block.kind is BlockKind.THINKING:
                # The transcript carries no readable thinking text, only a signature, so this is a
                # marker that the assistant was working rather than a summary of what it thought.
                column.add("thinking", metrics.body(FAINT), indent=metrics.body_px)
            elif block.kind is BlockKind.TOOL_USE:
                column.add(_tool_line(block.tool, block.text), metrics.mono(MUTED))
        if len(column.lines) == before:
            # Nothing to show. A turn carrying only a tool result is most of the user turns in a
            # real session, and labelling each one "you" above nothing fills the screen with
            # headings for content that was deliberately left out.
            continue
        starts.append(before)
        if turn.role is not spoken:
            # Only when the speaker changes. A run of assistant turns is one answer as far as a
            # reader is concerned, and a label above each would be five headings for one thought.
            column.lines.insert(
                before,
                Line.of(_ROLE_LABEL.get(turn.role, turn.role.value), metrics.bold(MUTED)),
            )
            spoken = turn.role
        column.blank(metrics.body())
    return column, starts


def _tool_line(tool: str, detail: str) -> str:
    """One line for one tool call, however many lines its argument had.

    A heredoc or a multi-line script is a normal Bash argument and would otherwise fill the screen
    with a command nobody is reading on this device. The first line plus a marker says what ran and
    that there was more of it.
    """
    label = tool or "tool"
    first, _, rest = detail.partition("\n")
    return f"{label}  {first}{' …' if rest.strip() else ''}"


def sessions(states: list[SessionState], metrics: Metrics) -> Page:
    """Page 1: which conversations exist, where they are, and which ones want something.

    No bullet marker and no current-session arrow. The reader is holding a second screen, so the
    session they are "in" is not a thing this device knows; what it knows is which ones have
    stopped and asked, and which ones have written since they last looked.
    """
    column = metrics.column()
    _header("sessions", f"{len(states)} live", column, metrics)
    targets: list[Target] = []
    for state in states:
        start = len(column.lines)
        marks = []
        if state.needs_input:
            marks.append("needs input")
        if state.unread:
            marks.append("unread")
        column.add(state.title or state.session_id[:8], metrics.bold(INK if marks else MUTED))
        where = f"{state.project}@{state.branch}" if state.branch else state.project
        detail = f"{where}   {', '.join(marks)}" if marks else where
        column.add(detail, metrics.body(FAINT), indent=metrics.body_px)
        targets.append(
            Target(
                Action.OPEN_SESSION,
                line=start,
                span=len(column.lines) - start,
                value=state.session_id,
            )
        )
        # The gap between rows is outside the target on purpose: a tap that lands between two
        # sessions opens neither, which is better than opening whichever one the rounding favours.
        column.blank(metrics.body())
    if not states:
        column.add("no sessions on this host", metrics.body(FAINT))
    return Page(column, tuple(targets))


@dataclass(frozen=True)
class ChangesetFileRow:
    """One file on page 3: its name, its counts, and the path a tap on it opens."""

    name: str
    path: str
    added: int
    removed: int
    binary: bool = False


@dataclass
class _Node:
    """A folder while the tree is being built. Files first, then the folders under it."""

    files: list[ChangesetFileRow] = field(default_factory=list)
    folders: dict[str, _Node] = field(default_factory=dict)


def _tree(change: ChangesetState) -> _Node:
    root = _Node()
    for entry in change.files:
        parts = entry.id.split("/")
        node = root
        for part in parts[:-1]:
            node = node.folders.setdefault(part, _Node())
        node.files.append(
            ChangesetFileRow(
                name=parts[-1],
                path=entry.id,
                added=entry.edit.added,
                removed=entry.edit.removed,
                binary=entry.edit.binary,
            )
        )
    return root


def _collapse(name: str, node: _Node) -> tuple[str, _Node]:
    """Fold a folder that holds one folder and nothing else onto one row.

    `src/` then `klide/` on two rows spends two lines and two indents to say one thing, and the
    column is 48 monospace characters wide. `src/klide/` says it once.
    """
    while not node.files and len(node.folders) == 1:
        child, under = next(iter(node.folders.items()))
        name, node = f"{name}/{child}", under
    return name, node


def _counts(added: int, removed: int, binary: bool) -> str:
    return "binary" if binary else f"+{added} -{removed}"


def _walk(node: _Node, depth: int, column: Column, metrics: Metrics, targets: list[Target]) -> None:
    """One folder's rows, then the folders under it. Files before folders, each sorted."""
    pad = "  " * depth
    for row in sorted(node.files, key=lambda f: f.name):
        mono = metrics.mono(INK)
        left = f"{pad}{row.name}"
        counts = _counts(row.added, row.removed, row.binary)
        width = mono.font().getlength(left)
        gap = max(mono.font().getlength(" "), column.width - width - mono.font().getlength(counts))
        column.lines.append(Line((Run(left, mono), Run(counts, metrics.mono(MUTED), pad=gap))))
        targets.append(Target(Action.OPEN_FILE, line=len(column.lines) - 1, value=row.path))
    for name, under in sorted(node.folders.items()):
        name, under = _collapse(name, under)
        column.add(f"{pad}{name}/", metrics.mono(MUTED))
        _walk(under, depth + 1, column, metrics, targets)


def changes(state: SessionState, metrics: Metrics, stale: bool = False) -> Page:
    """Page 3: only the files the diff touches, as a tree, with the counts on the row.

    This replaces both the flat changed-files list and the tree of every path (UD8). The counts
    are set in monospace and pushed to the right edge by measurement, so they line up down the
    page whatever the names do.
    """
    column = metrics.column()
    targets = recap(state, column, metrics, stale=stale)
    change = state.changeset
    if change.status is ChangesetStatus.ERROR:
        column.add(change.error, metrics.body(FAINT))
        return Page(column, tuple(targets))
    if change.is_empty:
        # The state this repo is in most of the time, so it is designed for rather than discovered.
        column.add("nothing uncommitted", metrics.body(FAINT))
        return Page(column, tuple(targets))
    _walk(_tree(change), 0, column, metrics, targets)
    return Page(column, tuple(targets))


def trim_left(path: str, style: Style, available: float) -> str:
    """A path cut from the left until it fits, with a leading ellipsis to say it was cut.

    From the left because the end of a path is the part that identifies the file. Measured rather
    than counted: the header face is proportional, so a character budget is wrong by a different
    amount for every path.
    """
    if style.font().getlength(path) <= available:
        return path
    parts = path.split("/")
    while len(parts) > 1:
        parts = parts[1:]
        candidate = "\u2026/" + "/".join(parts)
        if style.font().getlength(candidate) <= available:
            return candidate
    cut = parts[-1]
    while cut and style.font().getlength("\u2026" + cut) > available:
        cut = cut[1:]
    return "\u2026" + cut


def one_diff(
    path: str, text: str, metrics: Metrics, stale: bool = False, back: bool = True
) -> Page:
    """Page 4: one file's diff, under its path and nothing else.

    The path alone at the top, not the recap: the reader arrived here from a tree that already
    showed them the repo and the branch, and the diff is the one view whose alignment carries
    meaning and so wants the room.
    """
    column = metrics.column()
    targets: list[Target] = []
    style = metrics.heading(STRONG)
    if back:
        room = column.width - metrics.body(MUTED).font().getlength(BACK) - metrics.body_px
        at = _right(column, metrics, trim_left(path, style, room), style, BACK)
        targets.append(Target(Action.BACK, line=len(column.lines) - 1, x0=at))
    else:
        column.add(trim_left(path, style, column.width), style)
    if stale:
        column.add(STALE, metrics.bold(INK))
        targets.append(Target(Action.REFRESH, line=len(column.lines) - 1))
    column.lines.append(rule(metrics))
    column.blank(metrics.body())
    lay_diff(text, column, metrics)
    return Page(column, tuple(targets))


def one_file(path: str, text: str, metrics: Metrics, language: str = "") -> Page:
    """One file, with line numbers, highlighted by shade.

    Numbers let a reader quote a line to someone on the other machine, which is most of what this
    view is for. They are added after highlighting, so the number never changes the shade.
    """
    column = metrics.column()
    lines = text.split("\n")
    _header("file", f"{path}, {len(lines)} lines", column, metrics)
    code(text, column, metrics, language=language, gutter=True)
    # No targets: nothing routes here (U5). Whole-file browsing is deferred, and this stays so
    # that the decision to defer it is visible rather than a deletion nobody records.
    return Page(column)
