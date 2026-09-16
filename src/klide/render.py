"""Rendering text to a frame.

Deliberately one function. Markdown, diffs, syntax highlighting and the view set are phase 4; this
is the skeleton's static page and exists so there is something real to carry over the wire and
compare.

The font is Pillow's own bundled scalable face, reached through `ImageFont.load_default(size=...)`,
not a system font. That is what makes a reference frame reproducible: Pillow is pinned in
`uv.lock`, so the same text renders to the same bytes here, in a worktree and on a CI runner, none
of which are guaranteed to have the same fonts installed.
"""

from __future__ import annotations

from PIL import Image, ImageDraw, ImageFont

from klide.frame import Frame
from klide.panel import Panel

MARGIN = 24
FONT_SIZE = 26
LINE_HEIGHT = 34


def render_text(text: str, panel: Panel) -> Frame:
    """Draw `text` as a full-panel frame, one line per line, clipped at the bottom.

    Lines that run past the panel are not wrapped. Wrapping is a layout question and layout is
    phase 4; clipping keeps this honest about doing nothing clever.
    """
    image = Image.new("L", (panel.width, panel.height), color=255)
    draw = ImageDraw.Draw(image)
    font = ImageFont.load_default(size=FONT_SIZE)
    y = MARGIN
    for line in text.splitlines():
        if y + LINE_HEIGHT > panel.height - MARGIN:
            break
        draw.text((MARGIN, y), line, font=font, fill=0)
        y += LINE_HEIGHT
    return Frame.from_image(image, panel)
