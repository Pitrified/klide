"""The end-to-end path, exercised in process.

`scripts/gates/frames.py` runs the same loop as the shipped command; these tests cover the parts
of it that a single pass-or-fail gate cannot show, and keep the socket path under test.
"""

from pathlib import Path

from klide.panel import KOBO_LIBRA_2, Panel
from klide.render import render_text
from klide.skeleton import PAGE, render_skeleton_page, run_once
from klide.text import measure


def test_a_frame_survives_the_socket_unchanged(tmp_path: Path) -> None:
    received = run_once(KOBO_LIBRA_2, tmp_path / "klide.sock")
    rendered = render_skeleton_page(KOBO_LIBRA_2)
    assert received.levels == rendered.levels
    assert received.is_full_panel


def test_rendering_is_deterministic_which_is_what_a_zero_tolerance_gate_rests_on() -> None:
    assert render_skeleton_page(KOBO_LIBRA_2).levels == render_skeleton_page(KOBO_LIBRA_2).levels


def test_text_past_the_bottom_is_clipped_rather_than_overflowing() -> None:
    tall = "\n".join(f"line {i}" for i in range(500))
    frame = render_text(tall, KOBO_LIBRA_2)
    assert frame.is_full_panel
    assert len(frame.levels) == KOBO_LIBRA_2.width * KOBO_LIBRA_2.height


def test_an_empty_page_renders_a_blank_panel() -> None:
    frame = render_text("", KOBO_LIBRA_2)
    assert set(frame.levels) == {KOBO_LIBRA_2.grey_levels - 1}


def test_body_text_is_readable_at_the_panel_s_real_size() -> None:
    """The regression this exists to stop.

    The first version of the renderer used a 26 pixel font, chosen while looking at a scaled-down
    frame on a desktop monitor. On a 300 ppi panel that is 6.2 pt, about half the smallest size
    anyone sets a paperback in. Avoiding eye strain is the reason for using an e-reader at all, so
    the floor is a test rather than a note.
    """
    from klide.render import BODY_POINTS

    assert BODY_POINTS >= 9.0, "body text below 9 pt is not comfortable reading"


def test_a_screen_holds_a_sensible_number_of_lines() -> None:
    """A second angle on the same thing: point size is only half of legibility, line count is the
    other half. Forty-eight lines on a 142 mm screen is a wall of text whatever the font size."""
    from klide.render import BODY_POINTS, LINE_SPACING, MARGIN_POINTS

    panel = KOBO_LIBRA_2
    line_height = round(panel.points_to_pixels(BODY_POINTS) * LINE_SPACING)
    usable = panel.height - 2 * panel.points_to_pixels(MARGIN_POINTS)
    lines = usable // line_height
    assert 18 <= lines <= 32, f"{lines} lines per screen is outside comfortable reading"


def test_points_need_a_real_ppi_to_mean_anything() -> None:
    assert KOBO_LIBRA_2.ppi == 300
    assert KOBO_LIBRA_2.points_to_pixels(72) == 300


def _overflowing_lines(text: str, panel: Panel) -> list[str]:
    """Laid-out lines that would still be drawn past the right edge.

    Since phase 4 the renderer wraps, so this should always be empty. It is kept because the
    failure it catches is silent: before wrapping existed, raising the font size pushed every line
    past the edge and nothing complained. Preformatted content is still cut rather than wrapped,
    so this is the check that the cutting works.
    """
    from klide.render import Metrics, render_text  # noqa: F401

    metrics = Metrics.for_panel(panel)
    column = metrics.column()
    column.add(text, metrics.body())
    return [
        line.text
        for line in column.lines
        if measure(line.text, line.style) > metrics.column_width - line.indent
    ]


def test_the_skeleton_page_fits_the_panel_width() -> None:
    assert _overflowing_lines(PAGE, KOBO_LIBRA_2) == []


def test_the_session_pages_fit_the_panel_width() -> None:
    from klide.session import CONVERSATION_ID, DIFF_ID, page_text

    for page_id in (CONVERSATION_ID, DIFF_ID):
        assert _overflowing_lines(page_text(page_id), KOBO_LIBRA_2) == [], f"page {page_id}"


def test_every_view_lays_out_inside_the_column() -> None:
    """The same invariant for the real views, which is where it actually matters."""
    from klide.render import Metrics
    from klide.viewcmd import build

    metrics = Metrics.for_panel(KOBO_LIBRA_2)
    for view, column in build().items():
        for line in column.lines:
            width = measure(line.text, line.style)
            assert width <= metrics.column_width - line.indent + 1, f"{view.value}: {line.text!r}"
