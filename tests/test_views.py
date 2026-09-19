"""The four pages and the document layer they are built from.

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
from klide.viewcmd import CHANGESET, CURRENT, LIVE, build
from klide.views import BACK, STALE, Action, View, conversation, one_diff

FIXTURE = Path(__file__).parent / "fixtures" / "transcript.jsonl"

METRICS = Metrics.for_panel(KOBO_LIBRA_2)


def texts(column: Column) -> list[str]:
    return [line.text for line in column.lines]


def page_texts(view: View) -> list[str]:
    return texts(build()[view].column)


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


def test_every_page_builds_and_opens_in_bold() -> None:
    pages = build()
    assert set(pages) == set(View)
    for view, page in pages.items():
        assert page.lines, view
        assert page.lines[0].style.face is Face.BOLD


def test_the_conversation_labels_who_is_speaking() -> None:
    pages = build()
    lines = texts(pages[View.CONVERSATION].column)
    assert "you" in lines
    assert "claude" in lines


def test_a_thinking_block_shows_as_a_marker_with_no_content() -> None:
    turn = Turn(role=Role.ASSISTANT, blocks=(Block(BlockKind.THINKING, ""),))
    column = conversation([turn], METRICS)
    assert "thinking" in texts(column)


def test_tool_calls_appear_as_one_line_each() -> None:
    pages = build()
    lines = texts(pages[View.CONVERSATION].column)
    assert any("Bash" in line and "klide-skeleton" in line for line in lines)


def test_tool_results_are_not_rendered() -> None:
    # They are usually long and rarely the thing being followed on a second screen.
    pages = build()
    lines = " ".join(texts(pages[View.CONVERSATION].column))
    assert "wrote reference tests/references/skeleton.png" not in lines


def test_a_session_row_carries_the_repo_and_the_state() -> None:
    lines = page_texts(View.SESSIONS)
    waiting = next(s for s in LIVE if s.needs_input)
    detail = lines[lines.index(waiting.title) + 1]
    assert waiting.project in detail and "needs input" in detail and "unread" in detail


def test_the_session_list_has_no_bullet_marker() -> None:
    # The specification asked for a list with no bullet points, and the old view had an arrow
    # marking the current conversation, which a second screen has no way to know.
    assert not any(line.startswith(("\u25b6", "\u2022")) for line in page_texts(View.SESSIONS))


def test_every_session_row_is_a_target_covering_its_own_lines() -> None:
    page = build()[View.SESSIONS]
    opens = [t for t in page.targets if t.action is Action.OPEN_SESSION]
    assert [t.value for t in opens] == [s.session_id for s in LIVE]
    for target in opens:
        assert page.lines[target.line].text in {s.title for s in LIVE}
        # The blank line between rows is outside the span, so a tap in the gap opens neither.
        assert not page.lines[target.line + target.span - 1].text == ""


def test_the_recap_carries_the_name_repo_branch_and_totals() -> None:
    lines = page_texts(View.CHANGES)
    assert lines[0].startswith(CURRENT.title)
    assert f"{CURRENT.project}@{CURRENT.branch}" in lines[1]
    assert f"+{CHANGESET.added} -{CHANGESET.removed}" in lines[1]


def test_the_back_control_shares_the_first_line_of_the_recap() -> None:
    # UD11: it costs width, not a line of its own.
    page = build()[View.CHANGES]
    back = next(t for t in page.targets if t.action is Action.BACK)
    assert back.line == 0
    assert page.lines[0].text == CURRENT.title + BACK
    assert back.x0 > 0


def test_only_the_totals_are_tappable_in_the_recap() -> None:
    # UD10. The rest of the strip is text on every page.
    page = build()[View.CHANGES]
    on_the_recap = [t for t in page.targets if t.line <= 1]
    assert {t.action for t in on_the_recap} == {Action.BACK, Action.OPEN_CHANGES}


def test_the_tree_shows_each_folder_once_and_folds_single_child_folders() -> None:
    lines = page_texts(View.CHANGES)
    assert any(line == "src/klide/" for line in lines)
    assert "src/" not in lines and "  klide/" not in lines


def test_every_file_in_the_changeset_is_a_row_and_a_target() -> None:
    page = build()[View.CHANGES]
    opens = [t for t in page.targets if t.action is Action.OPEN_FILE]
    assert sorted(t.value for t in opens) == sorted(f.id for f in CHANGESET.files)


def test_a_file_row_carries_its_counts() -> None:
    page = build()[View.CHANGES]
    target = next(t for t in page.targets if t.value == "src/klide/render.py")
    assert page.lines[target.line].text.endswith("+61 -28")


def test_a_binary_file_says_binary_rather_than_zero() -> None:
    page = build()[View.CHANGES]
    target = next(t for t in page.targets if t.value.endswith(".png"))
    assert page.lines[target.line].text.endswith("binary")


def test_an_empty_changeset_says_so_rather_than_drawing_nothing() -> None:
    assert "nothing uncommitted" in page_texts(View.CHANGES_EMPTY)
    assert "clean" in page_texts(View.CHANGES_EMPTY)[1]


def test_the_stale_marker_is_itself_the_refresh_target() -> None:
    # UD9: the page that says it is out of date is also the way to fix it.
    page = build()[View.CHANGES_EMPTY]
    refresh = next(t for t in page.targets if t.action is Action.REFRESH)
    assert page.lines[refresh.line].text == STALE


def test_a_page_that_is_not_stale_has_no_refresh_target() -> None:
    assert not [t for t in build()[View.CHANGES].targets if t.action is Action.REFRESH]


def test_a_long_path_is_trimmed_from_the_left() -> None:
    page = build()[View.DIFF]
    head = page.lines[0].text
    assert head.startswith("\u2026/") and head.endswith(BACK)
    assert "render.py" in head


def test_a_short_path_is_not_trimmed() -> None:
    page = one_diff("a.py", "", METRICS)
    assert page.lines[0].text == "a.py" + BACK


def test_page_four_is_the_path_alone_not_the_whole_recap() -> None:
    # The reader arrived from a tree that already showed them the repo and the branch, and the
    # diff is the view whose alignment carries meaning, so it gets the room.
    page = build()[View.DIFF]
    assert CURRENT.project + "@" not in " ".join(texts(page.column)[:2])


def test_the_patch_header_is_not_drawn_twice() -> None:
    # The page is titled with the path; `diff --git`, `index`, `---` and `+++` name it four more
    # times, which is a fifth of a twenty-line screen.
    lines = page_texts(View.DIFF)
    assert not any(line.startswith(("diff --git", "index ", "--- ", "+++ ")) for line in lines)
    assert any(line.startswith("@@") for line in lines)


def test_the_unrouted_file_view_has_no_targets() -> None:
    # U5: it stays in place with nothing routing to it, rather than being deleted.
    assert build()[View.FILE].targets == ()


def test_the_file_view_numbers_its_lines() -> None:
    lines = [t for t in page_texts(View.FILE) if t.strip()]
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
