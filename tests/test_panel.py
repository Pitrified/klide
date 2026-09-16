import pytest

from klide.panel import KOBO_LIBRA_2, UnknownPanelError, get_panel


def test_libra_2_matches_the_recorded_device_specs() -> None:
    assert (KOBO_LIBRA_2.width, KOBO_LIBRA_2.height) == (1264, 1680)
    assert KOBO_LIBRA_2.grey_levels == 16


def test_sixteen_grey_levels_pack_into_four_bits() -> None:
    assert KOBO_LIBRA_2.bits_per_pixel == 4
    assert KOBO_LIBRA_2.frame_bytes == 1264 * 1680 // 2


def test_lookup_by_name() -> None:
    assert get_panel("kobo-libra-2") is KOBO_LIBRA_2


def test_unknown_panel_names_the_known_ones() -> None:
    with pytest.raises(UnknownPanelError, match="kobo-libra-2"):
        get_panel("kobo-libra-3")
