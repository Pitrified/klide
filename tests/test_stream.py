"""Streaming: coalescing, and dirty rectangles that converge on the right screen."""

from pathlib import Path

from klide.device import Device
from klide.frame import Frame
from klide.panel import KOBO_LIBRA_2, Panel
from klide.render import Metrics, render_lines
from klide.stream import Coalescer, changed_rows, dirty_rectangle, pick_waveform
from klide.transcript import read
from klide.views import conversation
from klide.waveform import Waveform

PANEL = Panel(name="test", width=8, height=6, grey_levels=16, ppi=300)
FIXTURE = Path(__file__).parent / "fixtures" / "transcript.jsonl"


def frame(rows: list[list[int]], panel: Panel = PANEL) -> Frame:
    flat = [level for row in rows for level in row]
    return Frame(panel=panel, x=0, y=0, width=panel.width, height=len(rows), levels=bytes(flat))


def blank(panel: Panel = PANEL) -> Frame:
    return frame([[15] * panel.width for _ in range(panel.height)], panel)


# Finding what changed


def test_nothing_changed_is_reported_as_nothing() -> None:
    # A redraw that changes no pixels still costs a refresh and a flash on a real panel.
    assert changed_rows(blank(), blank()) is None
    assert dirty_rectangle(blank(), blank()) is None


def test_only_the_rows_that_differ_are_reported() -> None:
    new = blank()
    rows = [list(new.levels[r * 8 : (r + 1) * 8]) for r in range(6)]
    rows[3][2] = 0
    rows[4][5] = 0
    assert changed_rows(blank(), frame(rows)) == (3, 4)


def test_the_patch_is_placed_where_it_belongs() -> None:
    rows = [list(blank().levels[r * 8 : (r + 1) * 8]) for r in range(6)]
    rows[4][1] = 0
    patch = dirty_rectangle(blank(), frame(rows))
    assert patch is not None
    assert (patch.x, patch.y, patch.height) == (0, 4, 1)
    assert list(patch.levels) == rows[4]


def test_a_resized_page_is_treated_as_entirely_dirty() -> None:
    short = frame([[15] * 8 for _ in range(3)])
    assert changed_rows(short, blank()) == (0, 5)


# The property the whole approach rests on


def test_a_patch_leaves_the_panel_exactly_as_a_full_frame_would() -> None:
    """Sending rectangles has to converge on the same screen as sending the page.

    This is the check that makes the optimisation safe. If it ever fails, a real device is left
    with stale pixels and no way to notice, which is the worst failure this design can have.
    """
    metrics = Metrics.for_panel(KOBO_LIBRA_2)
    turns = read(FIXTURE)

    patched = Device(panel=KOBO_LIBRA_2)
    whole = Device(panel=KOBO_LIBRA_2)
    previous = None

    for count in range(1, len(turns) + 1):
        column = conversation(turns[:count], metrics)
        page = render_lines(column.lines, KOBO_LIBRA_2, metrics)
        whole.receive(page, Waveform.GL16)
        if previous is None:
            patched.receive(page, Waveform.GL16)
        else:
            patch = dirty_rectangle(previous, page)
            if patch is not None:
                patched.receive(patch, Waveform.GL16)
        previous = page

    assert patched.snapshot().levels == whole.snapshot().levels


def test_streaming_sends_less_than_the_whole_page() -> None:
    # If a patch were usually the whole frame there would be no point to any of this.
    metrics = Metrics.for_panel(KOBO_LIBRA_2)
    turns = read(FIXTURE)
    first = render_lines(conversation(turns[:1], metrics).lines, KOBO_LIBRA_2, metrics)
    second = render_lines(conversation(turns[:2], metrics).lines, KOBO_LIBRA_2, metrics)
    patch = dirty_rectangle(first, second)
    assert patch is not None
    assert patch.height < KOBO_LIBRA_2.height


# Which mode a patch is drawn with


def test_a_small_patch_uses_the_text_mode() -> None:
    small = Frame(panel=PANEL, x=0, y=0, width=8, height=1, levels=bytes(8))
    assert pick_waveform(small, PANEL.height) is Waveform.GL16


def test_a_patch_covering_most_of_the_screen_may_as_well_flash() -> None:
    big = Frame(panel=PANEL, x=0, y=0, width=8, height=6, levels=bytes(48))
    assert pick_waveform(big, PANEL.height) is Waveform.GC16


def test_the_fast_two_level_mode_is_never_chosen_for_text() -> None:
    # A2 goes from black and white to black and white only, and antialiased text is neither.
    for height in range(1, PANEL.height + 1):
        patch = Frame(panel=PANEL, x=0, y=0, width=8, height=height, levels=bytes(8 * height))
        assert pick_waveform(patch, PANEL.height) is not Waveform.A2


# Coalescing


def test_nothing_is_due_before_anything_changes() -> None:
    assert not Coalescer().due(now=100.0)


def test_a_change_is_sent_once_it_goes_quiet() -> None:
    c = Coalescer(quiet=0.4, deadline=2.0)
    c.changed(now=0.0)
    assert not c.due(now=0.2)
    assert c.due(now=0.5)


def test_a_busy_burst_is_sent_at_the_deadline_rather_than_never() -> None:
    # A quiet period alone never fires while the assistant is still writing, so the screen would
    # stay stale through the most interesting part.
    c = Coalescer(quiet=0.4, deadline=2.0)
    for moment in range(0, 30):
        c.changed(now=moment * 0.1)
    assert c.due(now=2.1)


def test_sending_clears_the_pending_change() -> None:
    c = Coalescer()
    c.changed(now=0.0)
    c.sent()
    assert not c.due(now=10.0)
