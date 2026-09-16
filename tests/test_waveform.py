"""The refresh model is a set of claims, and these tests pin what kind of claims they are.

None of this checks a Libra 2. It checks that the ordering the FBInk documentation gives is the
ordering the simulator uses, and that every number carries its provenance, so a later calibration
against real hardware replaces something labelled rather than something assumed.
"""

import pytest

from klide.waveform import FBINK_CLAIMS, UnknownModeError, Waveform, get_mode, mode_for


def test_every_mode_says_where_its_number_came_from() -> None:
    for mode in FBINK_CLAIMS.values():
        assert "not measured on a Libra 2" in mode.source


def test_the_fast_modes_are_faster_than_the_full_one() -> None:
    # The ordering is the trustworthy part. The absolute values are not.
    assert get_mode(Waveform.A2).milliseconds < get_mode(Waveform.DU).milliseconds
    assert get_mode(Waveform.DU).milliseconds < get_mode(Waveform.GC16).milliseconds


def test_only_the_full_mode_flashes() -> None:
    assert get_mode(Waveform.GC16).flashes
    assert not any(get_mode(w).flashes for w in (Waveform.A2, Waveform.DU, Waveform.GL16))


def test_the_two_level_modes_cannot_carry_greyscale() -> None:
    assert get_mode(Waveform.A2).grey_levels == 2
    assert get_mode(Waveform.DU).grey_levels == 2
    assert get_mode(Waveform.GL16).grey_levels == 16


def test_an_unknown_mode_names_the_known_ones() -> None:
    with pytest.raises(UnknownModeError, match="gc16"):
        get_mode("gc42")


def test_black_and_white_content_gets_the_fast_mode() -> None:
    assert mode_for(levels_used=2, since_flash=0, flash_every=8).waveform is Waveform.A2


def test_greyscale_content_gets_the_text_mode() -> None:
    assert mode_for(levels_used=16, since_flash=0, flash_every=8).waveform is Waveform.GL16


def test_a_due_flash_wins_over_the_cheap_mode() -> None:
    assert mode_for(levels_used=2, since_flash=8, flash_every=8).waveform is Waveform.GC16
