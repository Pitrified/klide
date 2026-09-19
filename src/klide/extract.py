"""Filling the AHP types from this machine.

Three local sources, and nothing else. `claude agents --json` lists the live sessions, the
transcripts under `~/.claude/projects` say what each one has been doing, and `git` in each
session's working directory says what has changed. Read-only throughout (D11): nothing here writes
to a transcript, and nothing it does can reach the session it is describing.

## The derivation rule, in prose

Written before it was implemented, because a rule that is sometimes wrong is fine and a rule that
is sometimes wrong and unwritten is the pattern the 2026-09-18 review named. UD6 also asks that
every conclusion say which turn it came from, which is what `SessionState.activity` carries.

The CLI reports two statuses, `busy` and `idle`, and page 1 was specified with two more. So:

1. `busy` is `IN_PROGRESS`. The CLI knows this and nothing here second-guesses it.
2. Otherwise, if the newest turn is the assistant's and it called `AskUserQuestion`, the session is
   `INPUT_NEEDED`. This is the only signal in the transcript that says outright that Claude stopped
   to ask something.
3. Otherwise, if the newest turn is the assistant's and its prose ends in a question mark, the
   session is `INPUT_NEEDED`. Weaker than rule 2 and knowingly so: a turn can end in a rhetorical
   question, and a turn that asks for something without a question mark is missed. The reason line
   says which rule fired, so a wrong call is visible rather than silent.
4. Otherwise `IDLE`.

What this cannot see: a permission prompt. A session stopped on a tool approval never reaches the
transcript, and the CLI reports it as `idle` like any other wait. That is a known hole, not an
oversight, and closing it needs a source none of the three provides.

Read is separate from all of that, because it is about the reader rather than the session. Per
UD12 it is per host, per session, and tapping into a conversation marks it read: `ReadMarks`
records the newest turn the reader has seen, and a session counts as unread when the assistant has
written past that mark. In memory, because the device holds no durable state (K5) and a host that
restarts showing everything as unread is the harmless direction to be wrong in.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from klide.ahp import (
    ChangeKind,
    ChangesetFile,
    ChangesetState,
    ChangesetStatus,
    FileEdit,
    SessionState,
    SessionStatus,
)
from klide.transcript import Role, Turn, read

PROJECTS = Path.home() / ".claude" / "projects"

#: How long `claude agents --json` takes, measured on this box on 2026-09-19: 0.22 s, three runs,
#: five live sessions. That is the answer to U4's "is a subprocess per poll acceptable": not at the
#: rate a transcript is polled (0.25 s in `serve`), comfortably at the rate a list of sessions
#: changes. `AGENTS_POLL` is that slower cadence, and the transcripts keep their own.
AGENTS_POLL = 5.0


class AgentsUnavailableError(RuntimeError):
    """`claude agents --json` could not be run, or did not return a list of sessions."""


def _run(args: list[str], cwd: Path | None = None) -> str:
    """A command, or an empty string if it failed.

    Swallowing the failure is right here and only here: every caller is asking a question about a
    directory that may not be a repository, and "no answer" is a real answer to that. The one thing
    that must not happen is a page failing to draw because a session was started somewhere odd.
    """
    try:
        done = subprocess.run(args, cwd=cwd, capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.SubprocessError):
        return ""
    return done.stdout if done.returncode == 0 else ""


def list_agents(binary: str = "claude") -> list[dict[str, Any]]:
    """The live sessions, as the CLI reports them.

    Returned raw so the pinning test can compare against a captured sample: the field names below
    are someone else's and can change under us, and a shape change should fail a test rather than
    quietly produce a page of empty rows.
    """
    try:
        done = subprocess.run(
            [binary, "agents", "--json"], capture_output=True, text=True, timeout=30
        )
    except (OSError, subprocess.SubprocessError) as failed:
        raise AgentsUnavailableError(f"could not run {binary} agents --json: {failed}") from failed
    if done.returncode != 0:
        raise AgentsUnavailableError(
            f"{binary} agents --json exited {done.returncode}: {done.stderr.strip()}"
        )
    try:
        parsed = json.loads(done.stdout)
    except json.JSONDecodeError as bad:
        raise AgentsUnavailableError(f"{binary} agents --json returned non-JSON: {bad}") from bad
    if not isinstance(parsed, list):
        raise AgentsUnavailableError(
            f"{binary} agents --json returned {type(parsed).__name__}, expected a list"
        )
    return [entry for entry in parsed if isinstance(entry, dict)]


def transcript_for(agent: dict[str, Any], projects: Path = PROJECTS) -> Path | None:
    """Where the CLI's session id lands on disk.

    Claude Code's folder per project is the absolute path with separators flattened, and the file
    in it is the session id, so this is a lookup rather than a search.
    """
    session_id = str(agent.get("sessionId", ""))
    cwd = str(agent.get("cwd", ""))
    if not session_id or not cwd:
        return None
    path = projects / cwd.replace("/", "-") / f"{session_id}.jsonl"
    return path if path.is_file() else None


def derive_status(reported: str, turns: list[Turn]) -> tuple[SessionStatus, str]:
    """Rules 1 to 4 of the module docstring, and the line that says which one fired."""
    if reported == "busy":
        return SessionStatus.IN_PROGRESS, "busy, as the CLI reports it"
    if not turns:
        return SessionStatus.IDLE, "idle, no turns in the transcript"

    last = turns[-1]
    where = f"turn {last.uuid[:8] or '?'}"
    if last.role is Role.ASSISTANT:
        if "AskUserQuestion" in last.tools:
            return SessionStatus.INPUT_NEEDED, f"input needed: AskUserQuestion in {where}"
        if last.text.rstrip().endswith("?"):
            return SessionStatus.INPUT_NEEDED, f"input needed: {where} ends in a question"
    return SessionStatus.IDLE, f"idle, last spoke {last.role.value} in {where}"


class ReadMarks:
    """Which sessions the reader has opened, per host and per session (UD12).

    In memory on purpose. K5 leaves no durable state on the device, and the host is the only other
    place it could live; a restart that shows everything as unread costs one glance, while a
    restart that shows everything as read hides the thing page 1 exists for.
    """

    def __init__(self) -> None:
        self._seen: dict[str, str] = {}

    def mark(self, session_id: str, turns: list[Turn]) -> None:
        """Called when the reader taps into a conversation."""
        self._seen[session_id] = turns[-1].uuid if turns else ""

    def is_read(self, session_id: str, turns: list[Turn]) -> bool:
        """Read when the reader has seen the newest turn, or when Claude has not written since.

        A user turn arriving does not make a session unread. The state page 1 was specified with is
        "unread since Claude wrote", so what matters is whether the assistant has spoken past the
        mark.
        """
        if session_id not in self._seen:
            return False
        mark = self._seen[session_id]
        after = _after(turns, mark)
        return not any(turn.role is Role.ASSISTANT for turn in after)


def _after(turns: list[Turn], uuid: str) -> list[Turn]:
    """The turns past a mark. An unknown mark means the whole transcript is past it."""
    for index, turn in enumerate(turns):
        if turn.uuid and turn.uuid == uuid:
            return turns[index + 1 :]
    return turns


def _numstat(line: str) -> FileEdit | None:
    """One `git diff --numstat` row. Binary files report `-` where the counts go."""
    parts = line.split("\t")
    if len(parts) < 3:
        return None
    added, removed, path = parts[0], parts[1], parts[2]
    binary = added == "-" or removed == "-"
    return FileEdit(
        path=path,
        added=0 if binary else int(added),
        removed=0 if binary else int(removed),
        binary=binary,
    )


def changeset(cwd: Path, revision: int = 0) -> ChangesetState:
    """What is uncommitted in a working directory: the tree plus the index, against `HEAD` (UD5).

    One `git diff` for the whole list and no patch text, because page 3 lists every touched file
    and page 4 opens one. Reading every patch to draw the list is work for screens nobody opened;
    `patch_for` is what page 4 calls.
    """
    if not cwd.is_dir():
        return ChangesetState(status=ChangesetStatus.ERROR, error=f"no such directory: {cwd}")
    if not _run(["git", "rev-parse", "--git-dir"], cwd=cwd):
        return ChangesetState(status=ChangesetStatus.ERROR, error=f"not a git repository: {cwd}")

    out = _run(["git", "diff", "HEAD", "--numstat"], cwd=cwd)
    files: list[ChangesetFile] = []
    for line in out.splitlines():
        edit = _numstat(line)
        if edit is not None:
            files.append(ChangesetFile(id=edit.path, edit=edit))
    return ChangesetState(
        change_kind=ChangeKind.UNCOMMITTED,
        status=ChangesetStatus.READY,
        files=tuple(sorted(files, key=lambda f: f.id)),
        revision=revision,
    )


def patch_for(cwd: Path, path: str) -> str:
    """One file's diff, which is page 4's whole content."""
    return _run(["git", "diff", "HEAD", "--", path], cwd=cwd)


def branch_of(cwd: Path) -> str:
    """The current branch, or the short commit when the head is detached."""
    name = _run(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=cwd).strip()
    if name and name != "HEAD":
        return name
    return _run(["git", "rev-parse", "--short", "HEAD"], cwd=cwd).strip()


def project_of(cwd: Path) -> str:
    """The repository name, which is what the recap shows, falling back to the directory name."""
    top = _run(["git", "rev-parse", "--show-toplevel"], cwd=cwd).strip()
    return Path(top).name if top else cwd.name


def session_for(
    agent: dict[str, Any],
    marks: ReadMarks | None = None,
    projects: Path = PROJECTS,
    with_changeset: bool = True,
) -> SessionState:
    """One CLI record plus its transcript and its repository, as a `SessionState`."""
    session_id = str(agent.get("sessionId", ""))
    cwd = Path(str(agent.get("cwd", "")))
    path = transcript_for(agent, projects)
    turns = read(path) if path is not None else []

    status, why = derive_status(str(agent.get("status", "")), turns)
    if marks is not None and marks.is_read(session_id, turns):
        status |= SessionStatus.IS_READ

    return SessionState(
        session_id=session_id,
        title=str(agent.get("name", "")) or session_id[:8],
        project=project_of(cwd),
        branch=branch_of(cwd),
        working_directories=(str(cwd),),
        status=status,
        activity=why,
        turns=len(turns),
        changeset=changeset(cwd) if with_changeset else ChangesetState(),
    )


def sessions(
    marks: ReadMarks | None = None,
    projects: Path = PROJECTS,
    binary: str = "claude",
    with_changeset: bool = True,
) -> list[SessionState]:
    """Page 1, as data. Newest first, which is the order a reader glances down."""
    found = [session_for(a, marks, projects, with_changeset) for a in list_agents(binary)]
    return sorted(found, key=lambda s: s.title)


def main(argv: list[str] | None = None) -> int:
    """Print what the extractor sees, so it can be read without a panel."""
    parser = argparse.ArgumentParser(description="what the reader UI would show, as text")
    parser.add_argument("--no-git", action="store_true", help="skip the changeset per session")
    parser.add_argument("--diff", metavar="PATH", help="print one file's patch and exit")
    parser.add_argument("--cwd", type=Path, default=Path.cwd(), help="repository for --diff")
    args = parser.parse_args(argv)

    if args.diff:
        sys.stdout.write(patch_for(args.cwd, args.diff))
        return 0

    try:
        found = sessions(with_changeset=not args.no_git)
    except AgentsUnavailableError as missing:
        print(f"extract: {missing}", file=sys.stderr)
        return 1

    for state in found:
        marks = []
        if state.needs_input:
            marks.append("needs input")
        if state.unread:
            marks.append("unread")
        flags = f"  [{', '.join(marks)}]" if marks else ""
        print(f"{state.title}  {state.project}@{state.branch}  {state.turns} turns{flags}")
        # UD6: the derivation says which rule fired and which turn it read, every time.
        print(f"    status: {state.status!r} - {state.activity}")
        change = state.changeset
        if change.status is ChangesetStatus.ERROR:
            print(f"    changeset: {change.error}")
        elif change.is_empty:
            print(f"    changeset: clean ({change.change_kind})")
        else:
            print(
                f"    changeset: {len(change.files)} files, "
                f"+{change.added} -{change.removed} ({change.change_kind})"
            )
            for entry in change.files:
                mark = " (binary)" if entry.edit.binary else ""
                print(f"      +{entry.edit.added:<5d} -{entry.edit.removed:<5d} {entry.id}{mark}")
    print(f"extract: {len(found)} sessions")
    return 0


if __name__ == "__main__":
    sys.exit(main())
