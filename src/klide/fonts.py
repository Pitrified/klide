"""The three faces klide draws with, and the greys it draws them in.

Faces are vendored under `assets/fonts` rather than taken from the system, because a reference
frame is only a gate if the same text renders to the same bytes everywhere. See that folder's
README for the licence and the reasoning.

Greys rather than colours: the panel has sixteen levels and no hue, so everything syntax
highlighting and diffs would normally say with colour has to be said with weight, face, indentation
or shade. There are fewer usable shades than that suggests. Mid greys on e-ink are dithered and
read as muddy at text sizes, so the palette below deliberately uses the dark end for anything that
has to be read and reserves light greys for rules and backgrounds.
"""

from __future__ import annotations

from enum import Enum
from functools import lru_cache
from pathlib import Path

from PIL import ImageFont

FONT_DIR = Path(__file__).resolve().parents[2] / "assets" / "fonts"


class MissingFontError(FileNotFoundError):
    """A vendored font is not where it should be."""


class Face(Enum):
    """Why three: body text, something to make a heading stand out, and a monospace for anything
    whose alignment carries meaning, which is code and diffs."""

    BODY = "DejaVuSans.ttf"
    BOLD = "DejaVuSans-Bold.ttf"
    MONO = "DejaVuSansMono.ttf"


# Grey levels, 0 black to 15 white. Named by what they are for, not by how dark they are, so that
# changing one is a decision about a role rather than about a number.
INK = 0
STRONG = 0
BODY_GREY = 2
MUTED = 6
FAINT = 9
RULE = 11
BACKGROUND = 15


@lru_cache(maxsize=32)
def load(face: Face, size_px: int) -> ImageFont.FreeTypeFont:
    """Load a vendored face at a pixel size, cached because layout asks for the same few often."""
    path = FONT_DIR / face.value
    if not path.exists():
        raise MissingFontError(f"vendored font missing: {path}")
    return ImageFont.truetype(str(path), size_px)
