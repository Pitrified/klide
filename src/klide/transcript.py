"""Reading a Claude Code session transcript.

D9: klide tails the JSONL file Claude Code writes per session, at
`~/.claude/projects/<project-slug>/<session-id>.jsonl`. D11: read-only, always. Nothing here opens
the file for writing, and nothing sends anything back to the session.

The format is internal to Claude Code and can change between versions, which D9 already records as
the cost of this approach. Two things follow, and they shape this module more than anything else:

- **Parse defensively and never crash the renderer.** A record shape nobody expected becomes a
  block klide can show or skip, not an exception that takes the screen down mid-session.
- **Keep the surface small.** Everything downstream sees `Turn` and `Block`, so a format change is
  a change to this file. The shapes below were read from real transcripts on 2026-09-16: records
  carry a `type` of `user`, `assistant`, `system` and others, and `message.content` is either a
  string or a list of blocks typed `text`, `thinking`, `tool_use` or `tool_result`.
"""

from __future__ import annotations

import json
import time
from collections.abc import Iterator
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any


class BlockKind(StrEnum):
    TEXT = "text"
    THINKING = "thinking"
    TOOL_USE = "tool_use"
    TOOL_RESULT = "tool_result"


class Role(StrEnum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


@dataclass(frozen=True)
class Block:
    """One piece of a turn."""

    kind: BlockKind
    text: str
    tool: str = ""

    @property
    def is_empty(self) -> bool:
        return not self.text.strip()


@dataclass(frozen=True)
class Turn:
    """One record worth showing: who spoke, and what the message held."""

    role: Role
    blocks: tuple[Block, ...]
    uuid: str = ""
    timestamp: str = ""

    @property
    def text(self) -> str:
        """Just the prose, which is what the conversation view leads with."""
        return "\n\n".join(b.text for b in self.blocks if b.kind is BlockKind.TEXT)

    @property
    def tools(self) -> tuple[str, ...]:
        return tuple(b.tool for b in self.blocks if b.kind is BlockKind.TOOL_USE and b.tool)


def _block_text(raw: dict[str, Any]) -> str:
    """Pull the readable text out of a block, whatever shape it arrived in."""
    kind = raw.get("type")
    if kind == "text":
        return str(raw.get("text", ""))
    if kind == "thinking":
        return str(raw.get("thinking", ""))
    if kind == "tool_use":
        params = raw.get("input")
        if isinstance(params, dict):
            # The interesting parameter first, since a tool line has one line to be useful in.
            for key in ("command", "file_path", "path", "pattern", "query", "description"):
                if key in params:
                    return str(params[key])
            return ", ".join(sorted(params))
        return ""
    if kind == "tool_result":
        content = raw.get("content")
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            return "\n".join(
                str(part.get("text", "")) for part in content if isinstance(part, dict)
            )
        return ""
    return ""


def parse_record(raw: dict[str, Any]) -> Turn | None:
    """Turn one JSONL record into a `Turn`, or None if it is not one worth showing.

    Most record types in the file are bookkeeping: titles, modes, queue operations, file history.
    They are skipped rather than rendered.
    """
    record_type = raw.get("type")
    if record_type not in ("user", "assistant"):
        return None
    message = raw.get("message")
    if not isinstance(message, dict):
        return None
    role_name = message.get("role", record_type)
    try:
        role = Role(role_name)
    except ValueError:
        return None

    content = message.get("content")
    blocks: list[Block] = []
    if isinstance(content, str):
        blocks.append(Block(BlockKind.TEXT, content))
    elif isinstance(content, list):
        for entry in content:
            if not isinstance(entry, dict):
                continue
            try:
                kind = BlockKind(entry.get("type", ""))
            except ValueError:
                continue
            blocks.append(
                Block(kind=kind, text=_block_text(entry), tool=str(entry.get("name", "")))
            )

    # Thinking blocks are kept even when empty. In every transcript read on 2026-09-16 (219 of
    # them) the `thinking` field was an empty string and the content sat in an opaque `signature`,
    # so klide cannot show what was thought. The block still says the assistant was working, which
    # is worth a marker on a screen someone is watching.
    blocks = [b for b in blocks if b.kind is BlockKind.THINKING or not b.is_empty]
    if not blocks:
        return None
    return Turn(
        role=role,
        blocks=tuple(blocks),
        uuid=str(raw.get("uuid", "")),
        timestamp=str(raw.get("timestamp", "")),
    )


def read(path: Path) -> list[Turn]:
    """Read a whole transcript. Malformed lines are skipped, not raised.

    A transcript is appended to while it is read, so a half-written last line is normal rather than
    a fault.
    """
    turns: list[Turn] = []
    with path.open("r", encoding="utf-8", errors="replace") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                raw = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not isinstance(raw, dict):
                continue
            turn = parse_record(raw)
            if turn is not None:
                turns.append(turn)
    return turns


class Follower:
    """Reads a growing transcript, returning whatever is new each time it is asked.

    Offset-based and reopen-free. A half-written last line is held back until its newline arrives,
    because a transcript is appended to while it is read and a partial line is normal rather than a
    fault.

    A class rather than a generator because a viewer's event loop has to poll this alongside
    everything else it is waiting on. `tail` is the generator wrapper for callers that only want
    turns.
    """

    def __init__(self, path: Path) -> None:
        self.path = path
        self._offset = 0
        self._pending = ""

    def poll(self) -> list[Turn]:
        """Every complete turn appended since the last call."""
        with self.path.open("r", encoding="utf-8", errors="replace") as handle:
            handle.seek(self._offset)
            chunk = handle.read()
            self._offset = handle.tell()
        self._pending += chunk
        *complete, self._pending = self._pending.split("\n")
        turns = []
        for line in complete:
            if not line.strip():
                continue
            try:
                raw = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(raw, dict):
                turn = parse_record(raw)
                if turn is not None:
                    turns.append(turn)
        return turns


def tail(path: Path, poll: float = 0.25, stop_after: float | None = None) -> Iterator[Turn]:
    """Yield turns as they are appended, starting from the top of the file.

    `stop_after` bounds the wait so a test or a scripted run terminates; without it this blocks
    forever, which is what a live session wants.
    """
    deadline = None if stop_after is None else time.monotonic() + stop_after
    follower = Follower(path)
    while True:
        yield from follower.poll()
        if deadline is not None and time.monotonic() >= deadline:
            return
        time.sleep(poll)
