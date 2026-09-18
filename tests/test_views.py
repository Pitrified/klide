"""The six views and the document layer they are built from.

These check content and style, not pixels. What the pages look like is the `views` gate's job; the
split is what lets a layout question be asked without rendering anything.
"""

import re
from pathlib import Path

from klide.document import code, diff, lexer_for, line_grey, markdown
from klide.fonts import FAINT, INK, MUTED, Face
from klide.panel import KOBO_LIBRA_2
from klide.render import Metrics
from klide.text import Column, measure
from klide.transcript import Block, BlockKind, Role, Turn, read
from klide.viewcmd import CHANGED, SESSIONS, TREE, build
from klide.views import View, conversation

FIXTURE = Path(__file__).parent / "fixtures" / "transcript.jsonl"

METRICS = Metrics.for_panel(KOBO_LIBRA_2)


def texts(column: Column) -> list[str]:
    return [line.text for line in column.lines]


# Markdown


def test_a_heading_is_set_in_the_heading_face() -> None:
    column = METRICS.column()
    markdown("# Legibility", column, METRICS)
    heading = next(line for line in column.lines if line.text == "Legibility")
    assert heading.style.face is Face.BOLD
    assert heading.style.size_px > METRICS.body_px


def test_the_hashes_do_not_survive_into_the_page() -> None:
    column = METRICS.column()
    markdown("## Legibility", column, METRICS)
    assert "## Legibility" not in texts(column)


def test_a_bullet_gets_a_bullet_and_an_indent() -> None:
    column = METRICS.column()
    markdown("- one thing", column, METRICS)
    line = next(line for line in column.lines if line.text)
    assert line.text.startswith("•")
    assert line.indent > 0


def test_a_paragraph_is_joined_then_wrapped() -> None:
    # Markdown paragraphs are soft-wrapped in the source; the panel decides where lines break.
    column = METRICS.column()
    markdown("one\ntwo\nthree", column, METRICS)
    assert [t for t in texts(column) if t] == ["one two three"]


def test_a_fenced_block_becomes_monospace() -> None:
    column = METRICS.column()
    markdown("```python\nx = 1\n```", column, METRICS)
    line = next(line for line in column.lines if "x = 1" in line.text)
    assert line.style.face is Face.MONO
    assert line.style.preformatted


def test_a_quote_loses_its_marker_and_is_muted() -> None:
    column = METRICS.column()
    markdown("> quoted", column, METRICS)
    line = next(line for line in column.lines if line.text)
    assert line.text == "quoted"
    assert line.style.grey == MUTED


def test_inline_emphasis_is_drawn_rather_than_spelled_out() -> None:
    """The gap a person found first, by reading a real message on the panel.

    This test used to assert the opposite and call it a known gap: a laid-out line carried one
    style, so the asterisks survived. They are the first thing anyone sees.
    """
    column = METRICS.column()
    markdown("a **bold** word", column, METRICS)
    line = column.lines[0]
    assert line.text == "a bold word", "the markers are consumed, not drawn"
    bold = [run for run in line.runs if run.style.face is Face.BOLD]
    assert [run.text for run in bold] == ["bold"]


def test_a_code_span_is_monospace_but_still_wraps_with_its_sentence() -> None:
    # Monospace like a code block, not preformatted like one: a span is part of a sentence and has
    # to wrap with it rather than being cut when the line runs out.
    column = METRICS.column()
    markdown("run `uv run klide-live` to watch", column, METRICS)
    spans = [run for run in column.lines[0].runs if run.style.face is Face.MONO]
    assert [run.text for run in spans] == ["uv run klide-live"]
    assert not spans[0].style.preformatted


def test_a_link_keeps_its_text_and_drops_its_url() -> None:
    # There is no browser on the device and nothing to click, so a URL is noise costing most of a
    # line. Recorded as a decision rather than left to be rediscovered.
    column = METRICS.column()
    markdown("see [the protocol](https://example.com/docs/protocol.md) for why", column, METRICS)
    assert column.lines[0].text == "see the protocol for why"


def test_italic_markers_are_removed_even_though_there_is_no_italic_face() -> None:
    # Only three faces are vendored. Drawing italic as bold would be a lie about which words were
    # emphasised, so the markers go and the text stays body weight.
    column = METRICS.column()
    markdown("a *quiet* word", column, METRICS)
    line = column.lines[0]
    assert line.text == "a quiet word"
    assert all(run.style.face is Face.BODY for run in line.runs)


def test_underscores_in_identifiers_are_left_alone() -> None:
    """Why underscore emphasis is not parsed at all.

    This content is full of `klide_viewer` and `__init__`, and far emptier of `_emphasis_`. Parsing
    underscores would mangle the common case to serve the rare one.
    """
    column = METRICS.column()
    markdown("klide_viewer.py defines __init__ and _pump", column, METRICS)
    assert column.lines[0].text == "klide_viewer.py defines __init__ and _pump"


def test_emphasis_wraps_across_a_line_break_like_any_other_word() -> None:
    # The reason wrapping had to be rewritten to span runs: a line ending inside bold text has to
    # know how wide everything before it already is.
    column = METRICS.column()
    markdown("word " * 20 + "**bold at the end of a long paragraph**", column, METRICS)
    assert len(column.lines) > 1
    for line in column.lines:
        width = sum(measure(run.text, run.style) for run in line.runs)
        assert width <= column.width, f"{line.text!r} overflows by {width - column.width:.0f}px"
    assert "bold at the end of a long paragraph" in " ".join(texts(column))


# Code


def test_a_comment_is_fainter_than_a_statement() -> None:
    lexer = lexer_for("x = 1", "python")
    assert line_grey("# a comment", lexer) == FAINT
    assert line_grey("x = 1", lexer) == INK


def test_a_line_takes_the_shade_of_its_most_prominent_token() -> None:
    lexer = lexer_for("x = 1", "python")
    # The string is muted, but the assignment around it is not, so the line reads as code.
    assert line_grey('x = "text"', lexer) == INK
    assert line_grey('"""just a docstring"""', lexer) == MUTED


def test_an_unknown_language_still_lays_out() -> None:
    column = METRICS.column()
    code("!!! not any language !!!", column, METRICS, language="nonexistent-language")
    assert any(line.text for line in column.lines)


def test_the_gutter_is_added_after_highlighting_not_before() -> None:
    # A number in front of the source would be lexed as part of it and shade the whole line.
    plain = METRICS.column()
    code("# a comment", plain, METRICS, language="python")
    numbered = METRICS.column()
    code("# a comment", numbered, METRICS, language="python", gutter=True)
    assert numbered.lines[0].style.grey == plain.lines[0].style.grey
    assert numbered.lines[0].text.startswith("1  ")


# Diffs


def test_a_diff_orders_lines_by_how_much_they_matter() -> None:
    column = METRICS.column()
    diff(" context\n-removed\n+added", column, METRICS)
    by_text = {line.text: line.style.grey for line in column.lines if line.text}
    assert by_text["+added"] < by_text[" context"] < by_text["-removed"]


def test_every_diff_line_is_monospace_and_unwrapped() -> None:
    column = METRICS.column()
    diff(" a\n-b\n+c\n@@ -1 +1 @@", column, METRICS)
    for line in column.lines:
        if line.text:
            assert line.style.face is Face.MONO
            assert line.style.preformatted


def test_a_long_diff_line_is_cut_rather_than_folded() -> None:
    # A folded diff line looks like two lines and lies about the change.
    column = METRICS.column()
    diff("+" + "x" * 400, column, METRICS)
    lines = [line for line in column.lines if line.text]
    assert len(lines) == 1
    assert lines[0].text.endswith("…")


# The views


def test_every_view_builds_and_starts_with_its_own_name() -> None:
    columns = build()
    assert set(columns) == set(View)
    for view, column in columns.items():
        assert column.lines, view
        assert column.lines[0].style.face is Face.BOLD


def test_the_conversation_labels_who_is_speaking() -> None:
    columns = build()
    lines = texts(columns[View.CONVERSATION])
    assert "you" in lines
    assert "claude" in lines


def test_a_thinking_block_shows_as_a_marker_with_no_content() -> None:
    turn = Turn(role=Role.ASSISTANT, blocks=(Block(BlockKind.THINKING, ""),))
    column = conversation([turn], METRICS)
    assert "thinking" in texts(column)


def test_tool_calls_appear_as_one_line_each() -> None:
    columns = build()
    lines = texts(columns[View.CONVERSATION])
    assert any("Bash" in line and "klide-skeleton" in line for line in lines)


def test_tool_results_are_not_rendered() -> None:
    # They are usually long and rarely the thing being followed on a second screen.
    columns = build()
    lines = " ".join(texts(columns[View.CONVERSATION]))
    assert "wrote reference tests/references/skeleton.png" not in lines


def test_the_current_conversation_is_marked_and_darker() -> None:
    columns = build()
    current = next(s for s in SESSIONS if s.current)
    line = next(line for line in columns[View.CONVERSATIONS].lines if current.name in line.text)
    assert line.text.startswith("▶")
    assert line.style.grey == INK


def test_changed_files_totals_the_counts() -> None:
    columns = build()
    added = sum(f.added for f in CHANGED)
    assert any(f"+{added}" in line for line in texts(columns[View.CHANGED_FILES]))


def test_the_file_tree_shows_each_directory_once() -> None:
    columns = build()
    lines = texts(columns[View.FILE_TREE])
    assert lines.count("src/") == 1
    assert any(line.strip() == "klide/" for line in lines)
    assert len(TREE) > 0


def test_the_file_view_numbers_its_lines() -> None:
    columns = build()
    lines = [t for t in texts(columns[View.FILE]) if t.strip()]
    assert any(line.lstrip().startswith("1 ") or line.lstrip().startswith("1  ") for line in lines)


def test_a_turn_with_nothing_to_show_gets_no_heading() -> None:
    # A turn carrying only a tool result is most of the user turns in a real session. Labelling
    # each one above nothing fills the screen with headings for content deliberately left out.
    turn = Turn(role=Role.USER, blocks=(Block(BlockKind.TOOL_RESULT, "output nobody reads"),))
    assert texts(conversation([turn], METRICS)).count("you") == 0


def test_the_label_appears_once_per_run_of_the_same_speaker() -> None:
    # A run of assistant turns is one answer as far as a reader is concerned.
    turns = [
        Turn(role=Role.ASSISTANT, blocks=(Block(BlockKind.TEXT, f"part {i}"),)) for i in range(3)
    ]
    assert texts(conversation(turns, METRICS)).count("claude") == 1


def test_the_label_returns_when_the_speaker_changes() -> None:
    turns = [
        Turn(role=Role.ASSISTANT, blocks=(Block(BlockKind.TEXT, "a"),)),
        Turn(role=Role.USER, blocks=(Block(BlockKind.TEXT, "b"),)),
        Turn(role=Role.ASSISTANT, blocks=(Block(BlockKind.TEXT, "c"),)),
    ]
    lines = texts(conversation(turns, METRICS))
    assert lines.count("claude") == 2
    assert lines.count("you") == 1


def test_a_multi_line_tool_argument_collapses_to_one_line() -> None:
    # A heredoc is a normal Bash argument and would otherwise fill the screen with a command
    # nobody is reading on this device.
    turn = Turn(
        role=Role.ASSISTANT,
        blocks=(Block(BlockKind.TOOL_USE, "python3 - <<'PY'\nimport os\nPY", tool="Bash"),),
    )
    lines = [t for t in texts(conversation([turn], METRICS)) if "Bash" in t]
    assert len(lines) == 1
    assert lines[0].endswith("…")


def test_a_single_line_tool_argument_gains_no_marker() -> None:
    turn = Turn(role=Role.ASSISTANT, blocks=(Block(BlockKind.TOOL_USE, "ls -la", tool="Bash"),))
    line = next(t for t in texts(conversation([turn], METRICS)) if "Bash" in t)
    assert line == "Bash  ls -la"


def test_the_fixture_exercises_every_construct_the_renderer_supports() -> None:
    """A reference gate covers exactly what its fixture contains, and nothing else.

    Two design faults shipped behind green gates for this reason. Body text rendered at 6.2 pt for
    three phases, and markdown was rendered at block level only, so bold showed its asterisks and a
    table was reflowed into prose. Both were found by a person reading a screen, because the
    fixture had no small text and no table for a reference to differ from.

    This does not check that any of it renders well. It checks that the `views` gate is looking at
    a page where a change to any of these would move a pixel.
    """
    source = "\n".join(
        block.text
        for turn in read(FIXTURE)
        for block in turn.blocks
        if block.kind is BlockKind.TEXT
    )
    constructs = {
        "heading": re.compile(r"^#{1,6}\s+\S", re.M),
        "bullet": re.compile(r"^\s*[-*+]\s+\S", re.M),
        "fenced code": re.compile(r"^\s*```", re.M),
        "table row": re.compile(r"^\s*\|.+\|\s*$", re.M),
        "table divider": re.compile(r"^\s*\|[\s:|-]+\|\s*$", re.M),
        "bold": re.compile(r"\*\*[^*]+\*\*"),
        "code span": re.compile(r"`[^`\n]+`"),
        "link": re.compile(r"\[[^\]]+\]\([^)]*\)"),
        "italic": re.compile(r"(?<!\*)\*[^*\s][^*]*\*(?!\*)"),
        "underscored identifier": re.compile(r"\w_\w"),
    }
    missing = sorted(name for name, pattern in constructs.items() if not pattern.search(source))
    assert not missing, (
        f"{FIXTURE.name} no longer exercises: {', '.join(missing)}. The views gate would pass a "
        "renderer that broke them. Add content that uses them rather than deleting this check."
    )
