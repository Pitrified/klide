"""The end-to-end path, exercised in process.

`scripts/gates/frames.py` runs the same loop as the shipped command; these tests cover the parts
of it that a single pass-or-fail gate cannot show, and keep the socket path under test.
"""

from pathlib import Path

from klide.panel import KOBO_LIBRA_2
from klide.render import render_text
from klide.skeleton import PAGE, run_once


def test_a_frame_survives_the_socket_unchanged(tmp_path: Path) -> None:
    received = run_once(KOBO_LIBRA_2, tmp_path / "klide.sock")
    rendered = render_text(PAGE, KOBO_LIBRA_2)
    assert received.levels == rendered.levels
    assert received.is_full_panel


def test_rendering_is_deterministic_which_is_what_a_zero_tolerance_gate_rests_on() -> None:
    assert render_text(PAGE, KOBO_LIBRA_2).levels == render_text(PAGE, KOBO_LIBRA_2).levels


def test_text_past_the_bottom_is_clipped_rather_than_overflowing() -> None:
    tall = "\n".join(f"line {i}" for i in range(500))
    frame = render_text(tall, KOBO_LIBRA_2)
    assert frame.is_full_panel
    assert len(frame.levels) == KOBO_LIBRA_2.width * KOBO_LIBRA_2.height


def test_an_empty_page_renders_a_blank_panel() -> None:
    frame = render_text("", KOBO_LIBRA_2)
    assert set(frame.levels) == {KOBO_LIBRA_2.grey_levels - 1}
