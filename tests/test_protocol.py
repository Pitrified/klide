import io

import pytest

from klide.frame import Frame
from klide.input import Button, Direction, EventKind, InputEvent
from klide.panel import KOBO_LIBRA_2, Panel
from klide.protocol import (
    FRAME,
    HEADER_SIZE,
    INPUT,
    MAGIC,
    WAVEFORM_CODES,
    ProtocolError,
    TruncatedMessageError,
    decode_header,
    encode_frame,
    encode_input,
    read_frame,
    read_input,
    read_message,
)
from klide.waveform import Waveform

TINY = Panel(name="tiny", width=4, height=2, grey_levels=16)
LEVELS = bytes([0xA, 0xB, 0xC, 0xD, 1, 2, 3, 4])


def a_frame(x: int = 0, y: int = 0) -> Frame:
    return Frame(panel=TINY, x=x, y=y, width=4, height=2, levels=LEVELS)


def test_the_common_header_is_nine_bytes() -> None:
    message = encode_frame(a_frame())
    header = decode_header(message[:HEADER_SIZE])
    assert message[:4] == MAGIC
    assert header.msg_type == FRAME
    assert header.body_len == len(message) - HEADER_SIZE


def test_every_field_lands_on_a_byte_boundary_so_lua_can_read_it() -> None:
    # The real client is a KOReader Lua plugin with no string.unpack (R3), so the header has to be
    # readable with string.byte and arithmetic. Reading it that way here is the check.
    message = encode_frame(a_frame(x=258, y=1))
    body = list(message[HEADER_SIZE:])
    assert body[4] * 256 + body[5] == 258  # x
    assert body[6] * 256 + body[7] == 1  # y


def test_bad_magic_is_refused() -> None:
    with pytest.raises(ProtocolError, match="bad magic"):
        decode_header(b"XXXX" + bytes(HEADER_SIZE - 4))


def test_short_header_is_refused() -> None:
    with pytest.raises(ProtocolError, match="header is 9 bytes"):
        decode_header(MAGIC)


def test_frame_survives_the_wire() -> None:
    stream = io.BytesIO(encode_frame(a_frame(x=3, y=5), Waveform.GC16, page_id=7))
    frame, waveform, page_id = read_frame(stream, TINY)
    assert frame.levels == LEVELS
    assert (frame.x, frame.y) == (3, 5)
    assert waveform is Waveform.GC16
    assert page_id == 7


def test_a_page_id_of_zero_means_the_rectangle_belongs_to_no_page() -> None:
    stream = io.BytesIO(encode_frame(a_frame()))
    _frame, _waveform, page_id = read_frame(stream, TINY)
    assert page_id == 0


def test_input_survives_the_wire() -> None:
    sent = InputEvent.swipe(Direction.UP, x=100, y=200)
    assert read_input(io.BytesIO(encode_input(sent))) == sent


def test_a_button_press_survives_the_wire() -> None:
    sent = InputEvent.press(Button.PAGE_FORWARD)
    received = read_input(io.BytesIO(encode_input(sent)))
    assert received.button is Button.PAGE_FORWARD
    assert received.kind is EventKind.BUTTON


def test_the_two_message_types_are_told_apart() -> None:
    stream = io.BytesIO(encode_input(InputEvent.tap(1, 2)) + encode_frame(a_frame()))
    assert read_message(stream)[0] == INPUT
    assert read_message(stream)[0] == FRAME


def test_reading_the_wrong_type_raises_rather_than_misparsing() -> None:
    with pytest.raises(ProtocolError, match="expected a frame"):
        read_frame(io.BytesIO(encode_input(InputEvent.tap(1, 2))), TINY)
    with pytest.raises(ProtocolError, match="expected an input event"):
        read_input(io.BytesIO(encode_frame(a_frame())))


def test_a_truncated_payload_raises_rather_than_producing_a_short_frame() -> None:
    stream = io.BytesIO(encode_frame(a_frame())[:-1])
    with pytest.raises(TruncatedMessageError):
        read_frame(stream, TINY)


def test_a_depth_mismatch_is_refused_rather_than_misread() -> None:
    stream = io.BytesIO(encode_frame(a_frame()))
    two_level = Panel(name="mono", width=4, height=2, grey_levels=2)
    with pytest.raises(ProtocolError, match="bpp"):
        read_frame(stream, two_level)


def test_an_unknown_input_code_is_refused() -> None:
    body = bytes([99, 0, 0, 0, 0, 0, 0, 0])
    message = MAGIC + bytes([INPUT]) + len(body).to_bytes(4, "big") + body
    with pytest.raises(ProtocolError, match="unknown input code"):
        read_input(io.BytesIO(message))


def test_a_coordinate_too_large_for_two_bytes_is_refused_when_encoding() -> None:
    with pytest.raises(ProtocolError, match="does not fit two bytes"):
        encode_input(InputEvent.tap(70000, 0))


def test_waveform_codes_are_positional_so_reordering_them_would_break_clients() -> None:
    # Appending is safe; reordering silently changes what every existing client draws. The test is
    # here so a reorder fails rather than being noticed on a device.
    assert WAVEFORM_CODES == (Waveform.A2, Waveform.DU, Waveform.GL16, Waveform.GC16)


def test_a_full_panel_frame_fits_the_header_coordinate_fields() -> None:
    # Two bytes per coordinate caps a panel at 65535, which the Libra 2 is comfortably under.
    assert KOBO_LIBRA_2.width < 1 << 16
    assert KOBO_LIBRA_2.height < 1 << 16
    # A page buffer several screens tall has to fit too, since it travels as one frame.
    assert KOBO_LIBRA_2.height * 3 < 1 << 16
