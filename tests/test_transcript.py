"""Reading a Claude Code transcript.

The fixture is synthetic. The real transcripts on this box hold actual sessions, which are neither
ours to commit nor stable enough to compare against, so the fixture copies their record shapes
instead of their content.
"""

import json
from pathlib import Path

from klide.transcript import BlockKind, Role, parse_record, read, tail

FIXTURE = Path(__file__).parent / "fixtures" / "transcript.jsonl"


def test_the_fixture_parses() -> None:
    turns = read(FIXTURE)
    assert [t.role for t in turns] == [
        Role.USER,
        Role.ASSISTANT,
        Role.ASSISTANT,
        Role.USER,
        Role.ASSISTANT,
        Role.ASSISTANT,
    ]


def test_bookkeeping_records_are_skipped() -> None:
    # Most record types in a real file are titles, modes, queue operations and file history.
    assert parse_record({"type": "custom-title", "title": "x"}) is None
    assert parse_record({"type": "file-history-snapshot"}) is None


def test_a_string_content_becomes_one_text_block() -> None:
    turn = parse_record({"type": "user", "message": {"role": "user", "content": "hello"}})
    assert turn is not None
    assert turn.blocks[0].kind is BlockKind.TEXT
    assert turn.blocks[0].text == "hello"


def test_a_tool_use_keeps_the_tool_name_and_its_most_useful_argument() -> None:
    turn = parse_record(
        {
            "type": "assistant",
            "message": {
                "role": "assistant",
                "content": [
                    {"type": "tool_use", "name": "Bash", "input": {"command": "ls -la", "x": 1}}
                ],
            },
        }
    )
    assert turn is not None
    assert turn.tools == ("Bash",)
    assert turn.blocks[0].text == "ls -la"


def test_a_thinking_block_survives_even_though_it_carries_no_text() -> None:
    # Every thinking block in every transcript read on 2026-09-16 (219 of them) had an empty
    # `thinking` field, with the content in an opaque signature. The block is kept as a marker that
    # the assistant was working, which is worth showing on a screen someone is watching.
    turn = parse_record(
        {
            "type": "assistant",
            "message": {
                "role": "assistant",
                "content": [{"type": "thinking", "thinking": "", "signature": "opaque"}],
            },
        }
    )
    assert turn is not None
    assert turn.blocks[0].kind is BlockKind.THINKING
    assert turn.blocks[0].text == ""


def test_an_unknown_block_type_is_skipped_rather_than_raising() -> None:
    # The format is internal to Claude Code and can change between versions (D9). A shape nobody
    # expected must not take the screen down mid-session.
    turn = parse_record(
        {
            "type": "assistant",
            "message": {
                "role": "assistant",
                "content": [
                    {"type": "something_new", "text": "?"},
                    {"type": "text", "text": "still here"},
                ],
            },
        }
    )
    assert turn is not None
    assert [b.text for b in turn.blocks] == ["still here"]


def test_a_turn_with_nothing_worth_showing_is_dropped() -> None:
    assert parse_record({"type": "user", "message": {"role": "user", "content": []}}) is None


def test_malformed_lines_are_skipped_not_raised(tmp_path: Path) -> None:
    # A transcript is appended to while it is read, so a half-written last line is normal.
    path = tmp_path / "t.jsonl"
    good = json.dumps({"type": "user", "message": {"role": "user", "content": "kept"}})
    path.write_text(f'{good}\nnot json at all\n{{"half": \n')
    turns = read(path)
    assert len(turns) == 1
    assert turns[0].text == "kept"


def test_turn_text_joins_only_the_prose() -> None:
    turns = read(FIXTURE)
    answer = turns[1]
    assert "Legibility" in answer.text
    assert answer.blocks[0].kind is BlockKind.THINKING


def test_tail_yields_turns_appended_after_it_started(tmp_path: Path) -> None:
    path = tmp_path / "live.jsonl"
    path.write_text(
        json.dumps({"type": "user", "message": {"role": "user", "content": "one"}}) + "\n"
    )
    with path.open("a") as handle:
        handle.write(
            json.dumps({"type": "assistant", "message": {"role": "assistant", "content": "two"}})
            + "\n"
        )
    seen = [t.text for t in tail(path, poll=0.01, stop_after=0.0)]
    assert seen == ["one", "two"]


def test_tail_does_not_yield_a_half_written_line(tmp_path: Path) -> None:
    path = tmp_path / "partial.jsonl"
    complete = json.dumps({"type": "user", "message": {"role": "user", "content": "done"}})
    path.write_text(f"{complete}\n" + '{"type": "user", "message": {"role": "user", "cont')
    seen = [t.text for t in tail(path, poll=0.01, stop_after=0.0)]
    assert seen == ["done"]
