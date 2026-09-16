"""The klide wire protocol, version 2.

Version 1 carried one message type in one fixed header. Phase 3 needs a second type travelling the
other way, and a refresh mode on each frame, so the header split into a common part and a
type-specific body. That is the change; everything about how fields are encoded is unchanged and
was already decided by the client that does not exist yet.

The constraint that decided the encoding is AD5 plus R3: the simulator and the real device speak
the same protocol, and the real device is a KOReader Lua plugin. KOReader's Lua has no
`string.unpack`, so every field is a whole number of bytes, big-endian, readable with `string.byte`
and arithmetic. That rules out a bit-packed header, and it is why the payload pads each row to a
byte boundary.

    common header, 9 bytes
    offset  size  field
    0       4     magic, b"KLD2"
    4       1     message type
    5       4     body length

    frame body, host to device, 12 bytes then pixels
    0       1     bits per pixel
    1       1     refresh mode
    2       2     page id, 0 for a rectangle that belongs to no page
    4       2     x
    6       2     y
    8       2     width
    10      2     height
    12      ...   rows of packed pixels

    input body, device to host, 8 bytes
    0       1     event kind
    1       1     direction
    2       1     button
    3       1     reserved, zero
    4       2     x
    6       2     y

A full frame is the message whose rectangle covers the panel, and a dirty rectangle is the same
message with a smaller one. There is one message type for both.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import IO

from klide.frame import Frame
from klide.input import Button, Direction, EventKind, InputEvent
from klide.panel import Panel
from klide.waveform import Waveform

MAGIC = b"KLD2"
HEADER_SIZE = 9
FRAME_BODY_SIZE = 12
INPUT_BODY_SIZE = 8

FRAME = 1
INPUT = 2

# Byte codes for the wire. Appending is safe, reordering is not, which is why this is an explicit
# tuple rather than whatever order the enum happens to have.
WAVEFORM_CODES: tuple[Waveform, ...] = (Waveform.A2, Waveform.DU, Waveform.GL16, Waveform.GC16)


class ProtocolError(ValueError):
    """The bytes on the wire are not a message this version understands."""


class TruncatedMessageError(ProtocolError):
    """The stream ended part way through a message."""


@dataclass(frozen=True)
class Header:
    msg_type: int
    body_len: int


def _u16(value: int, field: str) -> bytes:
    if not 0 <= value < 1 << 16:
        raise ProtocolError(f"{field}={value} does not fit two bytes")
    return value.to_bytes(2, "big")


def _header(msg_type: int, body: bytes) -> bytes:
    return MAGIC + bytes([msg_type]) + len(body).to_bytes(4, "big") + body


def encode_frame(frame: Frame, waveform: Waveform = Waveform.GL16, page_id: int = 0) -> bytes:
    """One frame as one message, carrying the mode the panel should draw it with.

    `page_id` names the page this belongs to, so the device can cache it and recognise it later.
    Zero means the message is a rectangle that belongs to no page and is drawn and forgotten.
    """
    if waveform not in WAVEFORM_CODES:
        raise ProtocolError(f"waveform {waveform!r} has no wire code")
    body = bytearray()
    body.append(frame.panel.bits_per_pixel)
    body.append(WAVEFORM_CODES.index(waveform))
    body += _u16(page_id, "page_id")
    body += _u16(frame.x, "x")
    body += _u16(frame.y, "y")
    body += _u16(frame.width, "width")
    body += _u16(frame.height, "height")
    body += frame.packed()
    return _header(FRAME, bytes(body))


def encode_input(event: InputEvent) -> bytes:
    """One input event as one message, device to host."""
    body = (
        bytes([event.kind, event.direction, event.button, 0])
        + _u16(event.x, "x")
        + _u16(event.y, "y")
    )
    return _header(INPUT, body)


def decode_header(raw: bytes) -> Header:
    if len(raw) != HEADER_SIZE:
        raise ProtocolError(f"header is {HEADER_SIZE} bytes, got {len(raw)}")
    if raw[:4] != MAGIC:
        raise ProtocolError(f"bad magic {raw[:4]!r}, expected {MAGIC!r}")
    return Header(msg_type=raw[4], body_len=int.from_bytes(raw[5:9], "big"))


def decode_frame(body: bytes, panel: Panel) -> tuple[Frame, Waveform, int]:
    if len(body) < FRAME_BODY_SIZE:
        raise ProtocolError(f"frame body is at least {FRAME_BODY_SIZE} bytes, got {len(body)}")
    bits_per_pixel = body[0]
    if bits_per_pixel != panel.bits_per_pixel:
        raise ProtocolError(
            f"message is {bits_per_pixel}bpp, panel {panel.name} is {panel.bits_per_pixel}"
        )
    code = body[1]
    if code >= len(WAVEFORM_CODES):
        raise ProtocolError(f"unknown refresh mode code {code}")
    page_id, x, y, width, height = (int.from_bytes(body[i : i + 2], "big") for i in range(2, 12, 2))
    frame = Frame.unpacked(body[FRAME_BODY_SIZE:], panel, x, y, width, height)
    return frame, WAVEFORM_CODES[code], page_id


def decode_input(body: bytes) -> InputEvent:
    if len(body) != INPUT_BODY_SIZE:
        raise ProtocolError(f"input body is {INPUT_BODY_SIZE} bytes, got {len(body)}")
    try:
        kind = EventKind(body[0])
        direction = Direction(body[1])
        button = Button(body[2])
    except ValueError as bad:
        raise ProtocolError(f"unknown input code: {bad}") from None
    return InputEvent(
        kind=kind,
        direction=direction,
        button=button,
        x=int.from_bytes(body[4:6], "big"),
        y=int.from_bytes(body[6:8], "big"),
    )


def _read_exactly(stream: IO[bytes], count: int) -> bytes:
    """Read exactly `count` bytes or raise, because a short read on a socket is normal and
    silently accepting one would corrupt the message rather than fail."""
    chunks: list[bytes] = []
    remaining = count
    while remaining:
        chunk = stream.read(remaining)
        if not chunk:
            raise TruncatedMessageError(
                f"wanted {count} bytes, stream ended after {count - remaining}"
            )
        chunks.append(chunk)
        remaining -= len(chunk)
    return b"".join(chunks)


def read_message(stream: IO[bytes]) -> tuple[int, bytes]:
    """Read one message, returning its type and its body."""
    header = decode_header(_read_exactly(stream, HEADER_SIZE))
    return header.msg_type, _read_exactly(stream, header.body_len)


def read_frame(stream: IO[bytes], panel: Panel) -> tuple[Frame, Waveform, int]:
    """Read one frame message, or raise if the next message is something else."""
    msg_type, body = read_message(stream)
    if msg_type != FRAME:
        raise ProtocolError(f"expected a frame, got message type {msg_type}")
    return decode_frame(body, panel)


def read_input(stream: IO[bytes]) -> InputEvent:
    """Read one input message, or raise if the next message is something else."""
    msg_type, body = read_message(stream)
    if msg_type != INPUT:
        raise ProtocolError(f"expected an input event, got message type {msg_type}")
    return decode_input(body)
