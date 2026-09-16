"""The client logic that AD4 puts on the simulator so the device client is later a port."""

import pytest

from klide.device import Device, DeviceAsleepError, PageNotCachedError
from klide.frame import Frame
from klide.panel import Panel
from klide.render import render_text
from klide.waveform import Waveform

PANEL = Panel(name="test", width=8, height=4, grey_levels=16, ppi=300)
WHITE = 15


def solid(level: int, panel: Panel = PANEL, height: int | None = None) -> Frame:
    h = panel.height if height is None else height
    return Frame(
        panel=panel, x=0, y=0, width=panel.width, height=h, levels=bytes([level] * panel.width * h)
    )


def test_a_new_device_shows_white() -> None:
    assert set(Device(panel=PANEL).snapshot().levels) == {WHITE}


def test_a_received_page_is_drawn_and_cached() -> None:
    device = Device(panel=PANEL)
    device.receive(solid(3), Waveform.GL16, page_id=1)
    assert set(device.snapshot().levels) == {3}
    assert device.current_page == 1
    assert 1 in device.pages


def test_a_rectangle_with_no_page_id_is_drawn_and_forgotten() -> None:
    device = Device(panel=PANEL)
    patch = Frame(panel=PANEL, x=2, y=1, width=2, height=1, levels=bytes([0, 0]))
    device.receive(patch, Waveform.A2)
    assert device.pages == {}
    row = device.snapshot().levels[PANEL.width : 2 * PANEL.width]
    assert list(row) == [WHITE, WHITE, 0, 0, WHITE, WHITE, WHITE, WHITE]


def test_a_rectangle_is_clipped_to_the_panel_rather_than_overflowing() -> None:
    device = Device(panel=PANEL)
    patch = Frame(panel=PANEL, x=6, y=3, width=4, height=4, levels=bytes(16))
    device.receive(patch, Waveform.A2)
    assert len(device.snapshot().levels) == PANEL.width * PANEL.height


def test_the_cache_is_bounded_and_evicts_the_least_recently_used() -> None:
    device = Device(panel=PANEL, cache_pages=2)
    for page_id in (1, 2, 3):
        device.receive(solid(page_id), Waveform.GL16, page_id=page_id)
    assert sorted(device.pages) == [2, 3]


def test_touching_a_cached_page_keeps_it_from_being_evicted() -> None:
    device = Device(panel=PANEL, cache_pages=2)
    device.receive(solid(1), Waveform.GL16, page_id=1)
    device.receive(solid(2), Waveform.GL16, page_id=2)
    device.show_cached(1)
    device.receive(solid(3), Waveform.GL16, page_id=3)
    assert sorted(device.pages) == [1, 3]


def test_showing_a_cached_page_costs_no_round_trip() -> None:
    device = Device(panel=PANEL)
    device.receive(solid(3), Waveform.GL16, page_id=1)
    device.receive(solid(7), Waveform.GL16, page_id=2)
    device.show_cached(1)
    assert set(device.snapshot().levels) == {3}
    assert device.history[-1].local


def test_an_evicted_page_says_so_instead_of_drawing_nothing() -> None:
    device = Device(panel=PANEL, cache_pages=1)
    device.receive(solid(1), Waveform.GL16, page_id=1)
    device.receive(solid(2), Waveform.GL16, page_id=2)
    with pytest.raises(PageNotCachedError, match="page 1 is not cached"):
        device.show_cached(1)


def test_panning_moves_inside_a_page_taller_than_the_screen() -> None:
    tall = Frame(
        panel=PANEL,
        x=0,
        y=0,
        width=PANEL.width,
        height=PANEL.height * 2,
        levels=bytes([1] * PANEL.width * PANEL.height + [9] * PANEL.width * PANEL.height),
    )
    device = Device(panel=PANEL)
    device.receive(tall, Waveform.GL16, page_id=1)
    assert set(device.snapshot().levels) == {1}
    assert device.pan(PANEL.height) == PANEL.height
    assert set(device.snapshot().levels) == {9}


def test_panning_clamps_at_both_ends() -> None:
    tall = solid(2, height=PANEL.height * 2)
    device = Device(panel=PANEL)
    device.receive(tall, Waveform.GL16, page_id=1)
    assert device.pan(PANEL.height * 10) == PANEL.height
    assert device.pan(-PANEL.height * 10) == 0


def test_panning_with_no_page_says_so() -> None:
    with pytest.raises(PageNotCachedError, match="nothing to pan"):
        Device(panel=PANEL).pan(10)


def test_drawing_while_asleep_is_refused() -> None:
    device = Device(panel=PANEL)
    device.sleep()
    with pytest.raises(DeviceAsleepError):
        device.receive(solid(1), Waveform.GL16, page_id=1)


def test_sleep_keeps_the_framebuffer_and_resume_repaints_with_a_flash() -> None:
    device = Device(panel=PANEL)
    device.receive(solid(4), Waveform.GL16, page_id=1)
    device.sleep()
    assert set(device.snapshot().levels) == {4}
    device.resume()
    assert not device.asleep
    assert device.history[-1].mode.flashes


def test_disconnecting_keeps_the_page_and_draws_a_banner() -> None:
    # K6: a stale frame with a visible warning beats a blank screen, and the client draws the
    # warning itself because the host is by definition gone.
    panel = Panel(name="wide", width=400, height=200, grey_levels=16, ppi=300)
    device = Device(panel=panel)
    device.receive(render_text("kept text", panel), Waveform.GL16, page_id=1)
    before = device.snapshot().levels
    device.disconnect()
    after = device.snapshot().levels
    assert not device.connected
    top_changed = before[: panel.width * 56] != after[: panel.width * 56]
    bottom_kept = before[panel.width * 56 :] == after[panel.width * 56 :]
    assert top_changed and bottom_kept


def test_claimed_time_accumulates_per_refresh() -> None:
    device = Device(panel=PANEL)
    device.receive(solid(1), Waveform.A2, page_id=1)
    device.receive(solid(2), Waveform.GC16, page_id=2)
    assert device.elapsed_ms == 120 + 450


def test_a_flash_resets_the_partial_count_and_partials_raise_it() -> None:
    device = Device(panel=PANEL)
    device.receive(solid(1), Waveform.A2, page_id=1)
    device.receive(solid(2), Waveform.A2, page_id=2)
    assert device.since_flash == 2
    device.receive(solid(3), Waveform.GC16, page_id=3)
    assert device.since_flash == 0


def test_a_full_refresh_falls_due_after_the_configured_number_of_partials() -> None:
    device = Device(panel=PANEL, flash_every=3)
    tall = solid(2, height=PANEL.height * 4)
    device.receive(tall, Waveform.GL16, page_id=1)
    modes = []
    for _ in range(4):
        device.pan(1)
        modes.append(device.history[-1].mode.flashes)
    assert modes == [False, False, True, False]
