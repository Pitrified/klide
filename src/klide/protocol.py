"""The klide wire protocol, version 1.

Shape drawn from what the skeleton needed, as phase 2 asks, rather than from a design document.

The constraint that decided the encoding is AD5 plus R3: the simulator and the real device speak
the same protocol, and the real device is a KOReader Lua plugin. KOReader's Lua has no
`string.unpack`, so every field here is a whole number of bytes, big-endian, readable with
`string.byte` and arithmetic. That rules out a bit-packed header, and it is why the payload pads
each row to a byte boundary.

    offset  size  field
    0       4     magic, b"KLD1"
    4       1     message type
    5       1     bits per pixel
    6       2     x
    8       2     y
    10      2     width
    12      2     height
    14      4     payload length
    18      ...   payload, rows of packed pixels

A full frame is the message whose rectangle covers the panel. Phase 3's dirty rectangles are the
same message with a smaller one, which is why the coordinates are here now rather than added later.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import IO

from klide.frame import Frame
from klide.panel import Panel

MAGIC = b"KLD1"
HEADER_SIZE = 18
FRAME = 1


class ProtocolError(ValueError):
    """The bytes on the wire are not a message this version understands."""


class TruncatedMessageError(ProtocolError):
    """The stream ended part way through a message."""


@dataclass(frozen=True)
class Header:
    msg_type: int
    bits_per_pixel: int
    x: int
    y: int
    width: int
    height: int
    payload_len: int


def encode_frame(frame: Frame) -> bytes:
    """One frame as one message."""
    body = frame.packed()
    header = bytearray(MAGIC)
    header.append(FRAME)
    header.append(frame.panel.bits_per_pixel)
    for value in (frame.x, frame.y, frame.width, frame.height):
        header += value.to_bytes(2, "big")
    header += len(body).to_bytes(4, "big")
    return bytes(header) + body


def decode_header(raw: bytes) -> Header:
    if len(raw) != HEADER_SIZE:
        raise ProtocolError(f"header is {HEADER_SIZE} bytes, got {len(raw)}")
    if raw[:4] != MAGIC:
        raise ProtocolError(f"bad magic {raw[:4]!r}, expected {MAGIC!r}")
    return Header(
        msg_type=raw[4],
        bits_per_pixel=raw[5],
        x=int.from_bytes(raw[6:8], "big"),
        y=int.from_bytes(raw[8:10], "big"),
        width=int.from_bytes(raw[10:12], "big"),
        height=int.from_bytes(raw[12:14], "big"),
        payload_len=int.from_bytes(raw[14:18], "big"),
    )


def _read_exactly(stream: IO[bytes], count: int) -> bytes:
    """Read exactly `count` bytes or raise, because a short read on a socket is normal and
    silently accepting one would corrupt the frame rather than fail."""
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


def read_frame(stream: IO[bytes], panel: Panel) -> Frame:
    """Read one frame message, or raise."""
    header = decode_header(_read_exactly(stream, HEADER_SIZE))
    if header.msg_type != FRAME:
        raise ProtocolError(f"unknown message type {header.msg_type}")
    if header.bits_per_pixel != panel.bits_per_pixel:
        raise ProtocolError(
            f"message is {header.bits_per_pixel}bpp, panel {panel.name} is {panel.bits_per_pixel}"
        )
    payload = _read_exactly(stream, header.payload_len)
    return Frame.unpacked(payload, panel, header.x, header.y, header.width, header.height)
