"""Filling the AHP types from this machine.

The CLI sample in `fixtures/agents.json` is two real records, captured from
`claude agents --json` on 2026-09-19. It is here to pin the field names: they are Claude Code's
and can change under us, and a shape change should fail here rather than draw a page of empty
rows.
"""

import json
import subprocess
from pathlib import Path

import pytest

from klide.ahp import ChangeKind, ChangesetStatus, SessionStatus
from klide.extract import (
    AgentsUnavailableError,
    ReadMarks,
    branch_of,
    changeset,
    derive_status,
    list_agents,
    patch_for,
    project_of,
    session_for,
    transcript_for,
)
from klide.transcript import Block, BlockKind, Role, Turn

FIXTURES = Path(__file__).parent / "fixtures"
AGENTS = FIXTURES / "agents.json"


def assistant(text: str = "", tool: str = "", uuid: str = "u1") -> Turn:
    blocks = [Block(BlockKind.TEXT, text)] if text else []
    if tool:
        blocks.append(Block(BlockKind.TOOL_USE, "", tool))
    return Turn(role=Role.ASSISTANT, blocks=tuple(blocks), uuid=uuid)


def user(text: str = "ok", uuid: str = "u0") -> Turn:
    return Turn(role=Role.USER, blocks=(Block(BlockKind.TEXT, text),), uuid=uuid)


def test_the_captured_sample_still_has_the_fields_we_read() -> None:
    for record in json.loads(AGENTS.read_text()):
        assert set(record) >= {"cwd", "sessionId", "name", "status"}
        assert record["status"] in ("idle", "busy")


def test_list_agents_parses_the_captured_sample(tmp_path: Path) -> None:
    stub = tmp_path / "claude"
    stub.write_text(f"#!/bin/sh\ncat {AGENTS}\n")
    stub.chmod(0o755)
    agents = list_agents(binary=str(stub))
    assert [a["name"] for a in agents] == ["klide-g4-1", "klide-g4-2"]


def test_a_cli_that_is_not_there_says_so(tmp_path: Path) -> None:
    with pytest.raises(AgentsUnavailableError):
        list_agents(binary=str(tmp_path / "no-such-binary"))


def test_a_cli_that_returns_junk_says_so(tmp_path: Path) -> None:
    stub = tmp_path / "claude"
    stub.write_text("#!/bin/sh\necho not json\n")
    stub.chmod(0o755)
    with pytest.raises(AgentsUnavailableError):
        list_agents(binary=str(stub))


def test_transcript_for_finds_the_flattened_project_folder(tmp_path: Path) -> None:
    folder = tmp_path / "-home-pmn-repos-klide"
    folder.mkdir()
    (folder / "abc.jsonl").write_text("")
    agent = {"cwd": "/home/pmn/repos/klide", "sessionId": "abc"}
    assert transcript_for(agent, projects=tmp_path) == folder / "abc.jsonl"
    assert transcript_for({"cwd": "/nope", "sessionId": "abc"}, projects=tmp_path) is None


def test_rule_1_busy_is_what_the_cli_says() -> None:
    status, why = derive_status("busy", [assistant("anything?")])
    assert status is SessionStatus.IN_PROGRESS
    assert "CLI" in why


def test_rule_2_ask_user_question_means_input_needed() -> None:
    status, why = derive_status("idle", [assistant(tool="AskUserQuestion", uuid="deadbeef01")])
    assert status is SessionStatus.INPUT_NEEDED
    assert "AskUserQuestion" in why and "deadbeef" in why


def test_rule_3_a_trailing_question_mark_means_input_needed() -> None:
    status, why = derive_status("idle", [assistant("shall I push?")])
    assert status is SessionStatus.INPUT_NEEDED
    assert "question" in why


def test_rule_4_everything_else_is_idle() -> None:
    status, why = derive_status("idle", [assistant("done, four commits")])
    assert status is SessionStatus.IDLE
    assert "assistant" in why
    assert derive_status("idle", [])[0] is SessionStatus.IDLE


def test_a_question_from_the_user_is_not_the_session_asking() -> None:
    # The rules only ever read the newest turn, and only when the assistant spoke it.
    assert derive_status("idle", [assistant("done"), user("why?")])[0] is SessionStatus.IDLE


def test_input_needed_carries_in_progress() -> None:
    # AHP's bitset: 24 is 16 together with 8, so a session waiting on a person is still working.
    assert SessionStatus.IN_PROGRESS in SessionStatus.INPUT_NEEDED


def test_an_unopened_session_is_unread() -> None:
    marks = ReadMarks()
    assert not marks.is_read("s", [assistant("hello", uuid="a")])


def test_tapping_in_marks_it_read() -> None:
    marks = ReadMarks()
    turns = [assistant("hello", uuid="a")]
    marks.mark("s", turns)
    assert marks.is_read("s", turns)


def test_claude_writing_again_makes_it_unread() -> None:
    marks = ReadMarks()
    turns = [assistant("hello", uuid="a")]
    marks.mark("s", turns)
    turns.append(assistant("and another thing", uuid="b"))
    assert not marks.is_read("s", turns)


def test_the_user_speaking_does_not_make_it_unread() -> None:
    # "Unread since Claude wrote" is the state page 1 was specified with.
    marks = ReadMarks()
    turns = [assistant("hello", uuid="a")]
    marks.mark("s", turns)
    turns.append(user("thanks", uuid="b"))
    assert marks.is_read("s", turns)


def git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=repo, capture_output=True, text=True, check=True
    ).stdout


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    git(tmp_path, "init", "-q", "-b", "trunk")
    git(tmp_path, "config", "user.email", "t@example.com")
    git(tmp_path, "config", "user.name", "t")
    (tmp_path / "kept.txt").write_text("one\ntwo\n")
    git(tmp_path, "add", "-A")
    git(tmp_path, "commit", "-qm", "first")
    return tmp_path


def test_a_clean_repository_has_an_empty_changeset(repo: Path) -> None:
    state = changeset(repo)
    assert state.status is ChangesetStatus.READY
    assert state.is_empty and state.added == 0 and state.removed == 0
    assert state.change_kind is ChangeKind.UNCOMMITTED


def test_the_changeset_matches_numstat_run_by_hand(repo: Path) -> None:
    (repo / "kept.txt").write_text("one\ntwo\nthree\n")
    (repo / "staged.txt").write_text("new\n")
    git(repo, "add", "staged.txt")

    state = changeset(repo)
    by_hand = {
        line.split("\t")[2]: (int(line.split("\t")[0]), int(line.split("\t")[1]))
        for line in git(repo, "diff", "HEAD", "--numstat").splitlines()
    }
    assert {f.id: (f.edit.added, f.edit.removed) for f in state.files} == by_hand
    # Working tree plus index against HEAD (UD5): the staged file and the unstaged edit, both.
    assert set(by_hand) == {"kept.txt", "staged.txt"}


def test_a_binary_file_counts_as_zero_and_says_so(repo: Path) -> None:
    (repo / "blob.bin").write_bytes(bytes(range(256)))
    git(repo, "add", "blob.bin")
    entry = next(f for f in changeset(repo).files if f.id == "blob.bin")
    assert entry.edit.binary and entry.edit.added == 0


def test_a_directory_that_is_not_a_repository_is_an_error_not_a_crash(tmp_path: Path) -> None:
    state = changeset(tmp_path / "nowhere")
    assert state.status is ChangesetStatus.ERROR and "no such directory" in state.error


def test_the_patch_is_the_one_file(repo: Path) -> None:
    (repo / "kept.txt").write_text("one\ntwo\nthree\n")
    (repo / "other.txt").write_text("x\n")
    git(repo, "add", "-A")
    patch = patch_for(repo, "kept.txt")
    assert "+three" in patch and "other.txt" not in patch


def test_branch_and_project(repo: Path) -> None:
    assert branch_of(repo) == "trunk"
    assert project_of(repo) == repo.name


def test_a_session_state_from_a_record_and_a_transcript(tmp_path: Path, repo: Path) -> None:
    projects = tmp_path / "projects"
    folder = projects / str(repo).replace("/", "-")
    folder.mkdir(parents=True)
    (folder / "sid.jsonl").write_text(
        json.dumps(
            {
                "type": "assistant",
                "uuid": "abcdef12",
                "message": {"role": "assistant", "content": [{"type": "text", "text": "ready?"}]},
            }
        )
        + "\n"
    )
    agent = {"cwd": str(repo), "sessionId": "sid", "name": "demo", "status": "idle"}

    state = session_for(agent, ReadMarks(), projects=projects)
    assert state.title == "demo"
    assert state.project == repo.name and state.branch == "trunk"
    assert state.needs_input and state.unread
    assert state.turns == 1
    assert state.changeset.is_empty
