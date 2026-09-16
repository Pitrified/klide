"""Frames, and the packing the wire uses.

A frame is a rectangle of grey levels at the panel's own bit depth, which for the Libra 2 is four
bits. Holding levels rather than 8-bit greys means a comparison is exact at the depth the panel
actually shows, instead of at a depth the host invented and the device would have thrown away.
"""

from __future__ import annotations

from dataclasses import dataclass

from PIL import Image

from klide.panel import Panel


class FrameSizeError(ValueError):
    """Pixel data does not match the rectangle it claims to fill."""


class FrameDepthError(ValueError):
    """A level falls outside what the panel's bit depth can carry."""


class UnsupportedDepthError(NotImplementedError):
    """Only four bits per pixel is packed so far.

    The Libra 2 is the only registered panel and it is 4bpp. A 1bpp Kindle panel is the case that
    would force the general version; the change is in `packed` and `unpacked` and nowhere else.
    """


@dataclass(frozen=True)
class Frame:
    """A rectangle of grey levels, one byte per pixel, each below `panel.grey_levels`.

    `x` and `y` place it on the panel. A full frame is the rectangle covering the whole panel, so a
    partial update later is the same type with a smaller rectangle rather than a new one.
    """

    panel: Panel
    x: int
    y: int
    width: int
    height: int
    levels: bytes

    def __post_init__(self) -> None:
        expected = self.width * self.height
        if len(self.levels) != expected:
            raise FrameSizeError(
                f"{self.width}x{self.height} needs {expected} bytes, got {len(self.levels)}"
            )
        if self.levels and max(self.levels) >= self.panel.grey_levels:
            raise FrameDepthError(
                f"level {max(self.levels)} does not fit {self.panel.grey_levels} grey levels"
            )

    @property
    def is_full_panel(self) -> bool:
        return (self.x, self.y, self.width, self.height) == (
            0,
            0,
            self.panel.width,
            self.panel.height,
        )

    @property
    def row_bytes(self) -> int:
        """Packed bytes per row. Rows are padded to a whole byte so the other end can walk the
        payload a row at a time without carrying a bit offset across rows, which matters because
        that end is Lua (R3)."""
        per_byte = 8 // self.panel.bits_per_pixel
        return (self.width + per_byte - 1) // per_byte

    @classmethod
    def from_image(cls, image: Image.Image, panel: Panel, x: int = 0, y: int = 0) -> Frame:
        """Take an 8-bit greyscale image down to the panel's depth.

        The reduction is a right shift, not `Image.quantize`. Phase 1 measured quantize costing
        more than the rendering that fed it, and a shift is exact because the levels are evenly
        spaced.
        """
        if image.mode != "L":
            image = image.convert("L")
        shift = 8 - panel.bits_per_pixel
        return cls(
            panel=panel,
            x=x,
            y=y,
            width=image.width,
            height=image.height,
            levels=image.point(lambda v: v >> shift).tobytes(),
        )

    def to_image(self) -> Image.Image:
        """Back to an 8-bit greyscale image, for writing a file a person can open.

        Levels are spread across the full range so the darkest is 0 and the lightest is 255,
        which is what the panel shows and what makes a saved frame look right.
        """
        top = self.panel.grey_levels - 1
        table = bytes(min(255, v * 255 // top) for v in range(256))
        img = Image.frombytes("L", (self.width, self.height), self.levels)
        return img.point(table)

    def packed(self) -> bytes:
        """Two pixels per byte, high nibble first, rows padded to a whole byte."""
        if self.panel.bits_per_pixel != 4:
            raise UnsupportedDepthError(
                f"packing is 4bpp only, panel is {self.panel.bits_per_pixel}"
            )
        out = bytearray(self.row_bytes * self.height)
        for row in range(self.height):
            line = self.levels[row * self.width : (row + 1) * self.width]
            if len(line) % 2:
                line += b"\x00"
            dst = row * self.row_bytes
            out[dst : dst + len(line) // 2] = bytes(
                (hi << 4) | lo for hi, lo in zip(line[0::2], line[1::2], strict=True)
            )
        return bytes(out)

    @classmethod
    def unpacked(cls, data: bytes, panel: Panel, x: int, y: int, width: int, height: int) -> Frame:
        """Inverse of `packed`."""
        if panel.bits_per_pixel != 4:
            raise UnsupportedDepthError(f"packing is 4bpp only, panel is {panel.bits_per_pixel}")
        row_bytes = (width + 1) // 2
        expected = row_bytes * height
        if len(data) != expected:
            raise FrameSizeError(f"{width}x{height} packs to {expected} bytes, got {len(data)}")
        levels = bytearray()
        for row in range(height):
            line = data[row * row_bytes : (row + 1) * row_bytes]
            wide = bytearray(len(line) * 2)
            wide[0::2] = bytes(b >> 4 for b in line)
            wide[1::2] = bytes(b & 0x0F for b in line)
            levels += wide[:width]
        return cls(panel=panel, x=x, y=y, width=width, height=height, levels=bytes(levels))
