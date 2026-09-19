"""The data model the reader UI reads, named after the Agent Host Protocol.

UD1: AHP's state model, not its transport. [AHP](https://github.com/microsoft/agent-host-protocol)
is Microsoft's, published August 2026: a host process owns agent sessions and synchronises them to
clients over JSON-RPC, with an initial snapshot and ordered action envelopes over immutable state.
Claude Code does not serve it, checked against 2.1.273, so an extractor exists either way and the
only question was what vocabulary it fills in. Taking AHP's settles two names this repo was about
to argue over: the read bit, and what a diff is scoped to.

Nothing here speaks JSON-RPC and nothing here is a reducer. The types are frozen because the
pages are functions of them, and a page that can be rebuilt from its inputs is one a gate can
check.

Field names are AHP's, spelled the way Python spells things: `workingDirectories` is
`working_directories`. Where AHP has a field with no local source it is absent rather than
invented, which is why there is no `annotations`, no `activeClients` and no `terminals`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntFlag, StrEnum


class SessionStatus(IntFlag):
    """AHP's session status bitset, with its values.

    The gaps and the overlap are AHP's, not a transcription error: `INPUT_NEEDED` is 24, which is
    16 together with `IN_PROGRESS`, so a session waiting on a person is still in progress. Bit 4
    alone has no name in the specification, so it is never set on its own here.
    """

    IDLE = 1
    ERROR = 2
    IN_PROGRESS = 8
    INPUT_NEEDED = 24
    IS_READ = 32
    IS_ARCHIVED = 64


class Lifecycle(StrEnum):
    """Whether the session exists yet. Everything local is `READY` by the time it is listed."""

    CREATING = "creating"
    READY = "ready"
    FAILED = "failed"


class ChangeKind(StrEnum):
    """What a changeset is scoped to.

    UD5 and U6: only `UNCOMMITTED` is produced today. The other two are here because they are the
    reason the field exists, and because a cycle between them is wanted later; a field with one
    value is cheaper to widen than a boolean to replace.
    """

    SESSION = "session"
    BRANCH = "branch"
    UNCOMMITTED = "uncommitted"


class ChangesetStatus(StrEnum):
    COMPUTING = "computing"
    READY = "ready"
    ERROR = "error"


@dataclass(frozen=True)
class FileEdit:
    """What happened to one file. AHP's `FileEdit`, reduced to what a diff on a small screen needs.

    `added` and `removed` are zero for a binary file, which `git` reports as `-` rather than a
    count; `binary` is what tells that apart from a file whose changes cancel out.
    """

    path: str
    added: int = 0
    removed: int = 0
    binary: bool = False
    old_path: str = ""

    @property
    def renamed(self) -> bool:
        return bool(self.old_path) and self.old_path != self.path


@dataclass(frozen=True)
class ChangesetFile:
    """One row of a changeset. AHP's `id` plus `edit`; `reviewed` is theirs and unused here.

    The patch text is not on it. Page 3 lists every touched file and page 4 shows one, so reading
    every patch to draw the list would be work for the screens nobody opened.
    """

    id: str
    edit: FileEdit
    reviewed: bool = False


@dataclass(frozen=True)
class ChangesetState:
    """The diff behind pages 2, 3 and 4.

    `revision` is not AHP's. It counts how many times the extractor has seen this changeset change,
    and it is what lets a page drawn earlier notice that it is stale (UD7) without comparing whole
    file lists.
    """

    change_kind: ChangeKind = ChangeKind.UNCOMMITTED
    status: ChangesetStatus = ChangesetStatus.READY
    files: tuple[ChangesetFile, ...] = ()
    error: str = ""
    revision: int = 0

    @property
    def added(self) -> int:
        return sum(f.edit.added for f in self.files)

    @property
    def removed(self) -> int:
        return sum(f.edit.removed for f in self.files)

    @property
    def is_empty(self) -> bool:
        return not self.files


@dataclass(frozen=True)
class SessionState:
    """One Claude Code session, as page 1 lists it and pages 2 to 4 head themselves with.

    `project` is AHP's; here it is the repository the session was started in, which is what the
    recap shows. `working_directories` is the plural AHP carries, and the local source gives one.
    """

    session_id: str
    title: str = ""
    project: str = ""
    branch: str = ""
    working_directories: tuple[str, ...] = ()
    status: SessionStatus = SessionStatus.IDLE
    lifecycle: Lifecycle = Lifecycle.READY
    provider: str = "claude-code"
    #: Why `status` says what it says, in one line, per UD6. Kept on the state rather than only
    #: logged so a test can assert the reason and not just the conclusion.
    activity: str = ""
    turns: int = 0
    changeset: ChangesetState = field(default_factory=ChangesetState)

    @property
    def cwd(self) -> str:
        return self.working_directories[0] if self.working_directories else ""

    @property
    def needs_input(self) -> bool:
        return SessionStatus.INPUT_NEEDED in self.status

    @property
    def unread(self) -> bool:
        """Unread since Claude wrote, which is the state page 1 was specified with."""
        return SessionStatus.IS_READ not in self.status
