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


def render_text(text: str, panel: Panel, height: int | None = None) -> Frame:
    """Draw `text` one line per line, clipped at the bottom.

    `height` defaults to the panel's own, which is the ordinary full-screen frame. Passing a larger
    one renders a page taller than the screen, which the device holds and pans inside without a
    round trip. That is the taller page buffer from the UI notes, and the renderer's only part in
    it is agreeing to draw past the bottom of the panel.

    Lines that run past the right edge are not wrapped. Wrapping is a layout question and layout is
    phase 4; clipping keeps this honest about doing nothing clever.
    """
    canvas_height = panel.height if height is None else height
    image = Image.new("L", (panel.width, canvas_height), color=255)
    draw = ImageDraw.Draw(image)
    font = ImageFont.load_default(size=FONT_SIZE)
    y = MARGIN
    for line in text.splitlines():
        if y + LINE_HEIGHT > canvas_height - MARGIN:
            break
        draw.text((MARGIN, y), line, font=font, fill=0)
        y += LINE_HEIGHT
    return Frame.from_image(image, panel)
