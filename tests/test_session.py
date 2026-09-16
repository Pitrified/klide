"""The scripted session, end to end over a real socket."""

import pytest

from klide.device import Device
from klide.panel import KOBO_LIBRA_2
from klide.session import (
    CONVERSATION_ID,
    DIFF_ID,
    PAGE_SCREENS,
    StepResult,
    refresh_ledger,
    report,
    run_and_capture,
    script,
)

Run = tuple[Device, list[StepResult]]


@pytest.fixture(scope="module")
def run(tmp_path_factory: pytest.TempPathFactory) -> Run:
    """One session for the whole module.

    A full-panel session is a second of work and every test here asks a different question about
    the same run, so running it once keeps the suite quick enough that an agent will still run it.
    """
    tmp = tmp_path_factory.mktemp("session")
    return run_and_capture(KOBO_LIBRA_2, tmp / "klide.sock", tmp / "out")


def test_every_step_produces_a_frame(run: Run) -> None:
    _device, written = run
    assert len(written) == len(script(KOBO_LIBRA_2))
    for result in written:
        assert result.path.exists(), result.step.name
        assert result.path.stat().st_size > 0


def test_most_steps_are_answered_without_the_host(run: Run) -> None:
    # The point of the client logic: only the two view changes cost a round trip.
    device, _ = run
    forwarded = [r for r in device.history if not r.local]
    assert len(forwarded) == 2
    assert len(device.history) > len(forwarded)


def test_both_pages_end_up_cached(run: Run) -> None:
    device, _ = run
    assert sorted(device.pages) == [CONVERSATION_ID, DIFF_ID]


def test_sleeping_costs_no_refresh_and_resuming_costs_a_flash(run: Run) -> None:
    device, _ = run
    assert sum(1 for r in device.history if r.mode.flashes) == 1


def test_the_session_ends_with_the_host_gone(run: Run) -> None:
    device, _ = run
    assert not device.connected


def test_the_report_says_the_numbers_are_claims(run: Run) -> None:
    device, _ = run
    lines = report(device)
    assert any("claimed panel time" in line for line in lines)


def test_a_page_is_taller_than_the_screen_so_panning_has_somewhere_to_go() -> None:
    from klide.session import render_page

    page = render_page(CONVERSATION_ID, KOBO_LIBRA_2)
    assert page.height == KOBO_LIBRA_2.height * PAGE_SCREENS
    assert page.height > KOBO_LIBRA_2.height


def test_the_refresh_ledger_records_each_step_separately(run: Run) -> None:
    # It is recorded during the run, not reconstructed afterwards: the device's history carries no
    # step boundaries, so rebuilding it from the end attributes everything to the first step.
    device, written = run
    ledger = refresh_ledger(device, written)
    assert "01-opened  gl16  from-host" in ledger
    assert "07-asleep  no refresh" in ledger
    assert "08-resumed  gc16  local" in ledger


def test_the_ledger_moves_when_the_redraw_policy_does(run: Run) -> None:
    # The gap this closes: a refresh policy change moves no pixels in a simulator that does not
    # model ghosting, so without the ledger the image comparison would pass a doubled budget.
    device, written = run
    greedy = Device(panel=KOBO_LIBRA_2, flash_every=1)
    for result in written:
        for refresh in result.refreshes:
            greedy.elapsed_ms += refresh.mode.milliseconds
    assert refresh_ledger(device, written) != refresh_ledger(greedy, written)
