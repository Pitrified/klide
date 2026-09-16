import pytest
from PIL import Image

from klide.frame import Frame, FrameDepthError, FrameSizeError
from klide.panel import KOBO_LIBRA_2, Panel

TINY = Panel(name="tiny", width=4, height=2, grey_levels=16)


def a_frame(levels: bytes, panel: Panel = TINY) -> Frame:
    return Frame(panel=panel, x=0, y=0, width=panel.width, height=panel.height, levels=levels)


def test_levels_must_fill_the_rectangle() -> None:
    with pytest.raises(FrameSizeError, match="needs 8 bytes, got 3"):
        a_frame(bytes([1, 2, 3]))


def test_levels_must_fit_the_bit_depth() -> None:
    with pytest.raises(FrameDepthError, match="16 grey levels"):
        a_frame(bytes([0, 0, 0, 16, 0, 0, 0, 0]))


def test_packing_puts_the_first_pixel_in_the_high_nibble() -> None:
    frame = a_frame(bytes([0xA, 0xB, 0xC, 0xD, 1, 2, 3, 4]))
    assert frame.packed() == bytes([0xAB, 0xCD, 0x12, 0x34])


def test_odd_width_pads_each_row_to_a_whole_byte() -> None:
    panel = Panel(name="odd", width=3, height=2, grey_levels=16)
    frame = a_frame(bytes([1, 2, 3, 4, 5, 6]), panel)
    assert frame.row_bytes == 2
    assert frame.packed() == bytes([0x12, 0x30, 0x45, 0x60])


def test_packing_roundtrips() -> None:
    frame = a_frame(bytes([0xA, 0xB, 0xC, 0xD, 1, 2, 3, 4]))
    back = Frame.unpacked(frame.packed(), TINY, 0, 0, TINY.width, TINY.height)
    assert back.levels == frame.levels


def test_odd_width_roundtrips_without_the_padding_leaking_in() -> None:
    panel = Panel(name="odd", width=3, height=2, grey_levels=16)
    frame = a_frame(bytes([1, 2, 3, 4, 5, 6]), panel)
    back = Frame.unpacked(frame.packed(), panel, 0, 0, panel.width, panel.height)
    assert back.levels == frame.levels


def test_unpacking_rejects_a_payload_of_the_wrong_size() -> None:
    with pytest.raises(FrameSizeError, match="packs to 4 bytes, got 3"):
        Frame.unpacked(bytes(3), TINY, 0, 0, TINY.width, TINY.height)


def test_from_image_shifts_rather_than_quantises() -> None:
    img = Image.frombytes("L", (4, 2), bytes([0, 17, 34, 255, 128, 129, 130, 143]))
    frame = Frame.from_image(img, TINY)
    # A right shift of four: 0->0, 17->1, 34->2, 255->15, and 128..143 all land on 8.
    assert list(frame.levels) == [0, 1, 2, 15, 8, 8, 8, 8]


def test_image_roundtrip_is_lossless_which_is_what_lets_references_be_pngs() -> None:
    frame = a_frame(bytes(range(8)))
    assert Frame.from_image(frame.to_image(), TINY).levels == frame.levels


def test_full_panel_is_the_rectangle_covering_the_panel() -> None:
    panel = KOBO_LIBRA_2
    full = Frame(panel, 0, 0, panel.width, panel.height, bytes(panel.width * panel.height))
    assert full.is_full_panel
    patch = Frame(panel, 10, 10, 4, 2, bytes(8))
    assert not patch.is_full_panel
