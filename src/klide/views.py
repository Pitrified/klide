"""The six views, and what each one puts on a page.

The set comes from the UI notes: conversation, conversation list, changed files, one diff, file
tree, one file. Everything except the diff is a scrolling column of text, which is why that case
was built first and the diff last.

A view takes plain data and returns a `Column`. It does not fetch anything, render anything, or
know how tall the page will be. That is what makes a view checkable without a panel: a test can
read the lines and their styles, and the frame comparison covers what they look like afterwards.

Every view opens with the same header line, so a reader glancing at the screen knows which of the
six they are looking at without reading the content.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from klide.document import code, markdown
from klide.document import diff as lay_diff
from klide.fonts import FAINT, INK, MUTED, STRONG
from klide.render import Metrics, rule
from klide.text import Column, Line
from klide.transcript import BlockKind, Role, Turn


class View(StrEnum):
    """The six. Ordered as the swipe map walks them."""

    CONVERSATION = "conversation"
    CONVERSATIONS = "conversations"
    CHANGED_FILES = "changed-files"
    DIFF = "diff"
    FILE_TREE = "file-tree"
    FILE = "file"


@dataclass(frozen=True)
class Session:
    """One conversation, as the list view needs it."""

    name: str
    turns: int
    updated: str
    current: bool = False


@dataclass(frozen=True)
class ChangedFile:
    """One entry in the changed files view."""

    path: str
    added: int
    removed: int


def _header(title: str, subtitle: str, column: Column, metrics: Metrics) -> None:
    column.add(title, metrics.heading(STRONG))
    if subtitle:
        column.add(subtitle, metrics.body(MUTED))
    column.lines.append(rule(metrics))
    column.blank(metrics.body())


#: What a turn is labelled with. The label carries the role, so the body does not have to repeat it
#: and a reader can skim the left edge to find where an answer starts.
_ROLE_LABEL = {Role.USER: "you", Role.ASSISTANT: "claude", Role.SYSTEM: "system"}


def conversation(turns: list[Turn], metrics: Metrics, title: str = "conversation") -> Column:
    """The main view: a transcript as something to read.

    Tool calls are one line each, not folded out. On a screen this size the useful thing is that a
    tool ran and what it touched, and a reader who wants the output has the file open on the other
    machine. Tool results are skipped for the same reason: they are usually long and rarely the
    thing being followed.
    """
    column = metrics.column()
    _header(title, f"{len(turns)} turns", column, metrics)

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
        if turn.role is not spoken:
            # Only when the speaker changes. A run of assistant turns is one answer as far as a
            # reader is concerned, and a label above each would be five headings for one thought.
            column.lines.insert(
                before, Line(_ROLE_LABEL.get(turn.role, turn.role.value), metrics.bold(MUTED))
            )
            spoken = turn.role
        column.blank(metrics.body())
    return column


def _tool_line(tool: str, detail: str) -> str:
    """One line for one tool call, however many lines its argument had.

    A heredoc or a multi-line script is a normal Bash argument and would otherwise fill the screen
    with a command nobody is reading on this device. The first line plus a marker says what ran and
    that there was more of it.
    """
    label = tool or "tool"
    first, _, rest = detail.partition("\n")
    return f"{label}  {first}{' …' if rest.strip() else ''}"


def conversations(sessions: list[Session], metrics: Metrics) -> Column:
    """Which conversations exist, and which one is on screen.

    One file per session means this view is nearly free (D9), which is why "multiple conversations"
    was listed as a requirement rather than a stretch.
    """
    column = metrics.column()
    _header("conversations", f"{len(sessions)} sessions", column, metrics)
    for session in sessions:
        marker = "▶ " if session.current else "  "
        column.add(
            f"{marker}{session.name}",
            metrics.body(INK if session.current else MUTED),
        )
        column.add(
            f"   {session.turns} turns, {session.updated}",
            metrics.body(FAINT),
            indent=metrics.body_px,
        )
    return column


def changed_files(files: list[ChangedFile], metrics: Metrics) -> Column:
    """What the session has touched, with how much.

    The counts are the point of this view: it answers "how big is this change" before you open
    anything. They are set in monospace so the columns line up down the page.
    """
    column = metrics.column()
    total_added = sum(f.added for f in files)
    total_removed = sum(f.removed for f in files)
    _header(
        "changed files",
        f"{len(files)} files, +{total_added} -{total_removed}",
        column,
        metrics,
    )
    for entry in files:
        column.add(f"+{entry.added:<5d} -{entry.removed:<5d} {entry.path}", metrics.mono(INK))
    return column


def one_diff(path: str, text: str, metrics: Metrics) -> Column:
    """A single file's diff, the one view whose alignment carries meaning."""
    column = metrics.column()
    _header("diff", path, column, metrics)
    lay_diff(text, column, metrics)
    return column


def file_tree(paths: list[str], metrics: Metrics) -> Column:
    """The project as a tree.

    Drawn from a flat list of paths rather than by walking a directory, so the view stays a pure
    function of its input and the gate has something deterministic to compare.
    """
    column = metrics.column()
    _header("files", f"{len(paths)} paths", column, metrics)
    seen: set[str] = set()
    for path in sorted(paths):
        parts = path.split("/")
        for depth, part in enumerate(parts[:-1]):
            prefix = "/".join(parts[: depth + 1])
            if prefix in seen:
                continue
            seen.add(prefix)
            column.add(f"{'  ' * depth}{part}/", metrics.mono(MUTED))
        column.add(f"{'  ' * (len(parts) - 1)}{parts[-1]}", metrics.mono(INK))
    return column


def one_file(path: str, text: str, metrics: Metrics, language: str = "") -> Column:
    """One file, with line numbers, highlighted by shade.

    Numbers let a reader quote a line to someone on the other machine, which is most of what this
    view is for. They are added after highlighting, so the number never changes the shade.
    """
    column = metrics.column()
    lines = text.split("\n")
    _header("file", f"{path}, {len(lines)} lines", column, metrics)
    code(text, column, metrics, language=language, gutter=True)
    return column
