import io

import pytest

from klide.frame import Frame
from klide.panel import KOBO_LIBRA_2, Panel
from klide.protocol import (
    HEADER_SIZE,
    MAGIC,
    ProtocolError,
    TruncatedMessageError,
    decode_header,
    encode_frame,
    read_frame,
)

TINY = Panel(name="tiny", width=4, height=2, grey_levels=16)
LEVELS = bytes([0xA, 0xB, 0xC, 0xD, 1, 2, 3, 4])


def a_frame(x: int = 0, y: int = 0) -> Frame:
    return Frame(panel=TINY, x=x, y=y, width=4, height=2, levels=LEVELS)


def test_header_is_eighteen_bytes_of_whole_fields() -> None:
    message = encode_frame(a_frame(x=7, y=9))
    header = decode_header(message[:HEADER_SIZE])
    assert message[:4] == MAGIC
    assert (header.x, header.y, header.width, header.height) == (7, 9, 4, 2)
    assert header.bits_per_pixel == 4
    assert header.payload_len == len(message) - HEADER_SIZE


def test_every_field_lands_on_a_byte_boundary_so_lua_can_read_it() -> None:
    # The real client is a KOReader Lua plugin with no string.unpack (R3), so the header has to be
    # readable with string.byte and arithmetic. Reading it that way here is the check.
    raw = encode_frame(a_frame(x=258, y=1))[:HEADER_SIZE]
    byte = list(raw)
    assert byte[6] * 256 + byte[7] == 258
    assert byte[8] * 256 + byte[9] == 1


def test_bad_magic_is_refused() -> None:
    with pytest.raises(ProtocolError, match="bad magic"):
        decode_header(b"XXXX" + bytes(HEADER_SIZE - 4))


def test_short_header_is_refused() -> None:
    with pytest.raises(ProtocolError, match="header is 18 bytes"):
        decode_header(MAGIC)


def test_frame_survives_the_wire() -> None:
    stream = io.BytesIO(encode_frame(a_frame(x=3, y=5)))
    received = read_frame(stream, TINY)
    assert received.levels == LEVELS
    assert (received.x, received.y) == (3, 5)


def test_a_truncated_payload_raises_rather_than_producing_a_short_frame() -> None:
    stream = io.BytesIO(encode_frame(a_frame())[:-1])
    with pytest.raises(TruncatedMessageError):
        read_frame(stream, TINY)


def test_a_depth_mismatch_is_refused_rather_than_misread() -> None:
    stream = io.BytesIO(encode_frame(a_frame()))
    two_level = Panel(name="mono", width=4, height=2, grey_levels=2)
    with pytest.raises(ProtocolError, match="bpp"):
        read_frame(stream, two_level)


def test_a_full_panel_frame_fits_the_header_coordinate_fields() -> None:
    # Two bytes per coordinate caps a panel at 65535, which the Libra 2 is comfortably under.
    assert KOBO_LIBRA_2.width < 1 << 16
    assert KOBO_LIBRA_2.height < 1 << 16
