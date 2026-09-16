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

# Sizes are in typographic points, not pixels, because the panel is 300 ppi and a pixel size
# picked while looking at a desktop monitor comes out about a quarter of its apparent size on the
# device. The first version of this file used 26px, which is 6.2pt: roughly half the smallest size
# anyone sets a paperback in. The point of an e-reader is not straining to read it.
BODY_POINTS = 11.0
LINE_SPACING = 1.45
MARGIN_POINTS = 11.5


def render_text(
    text: str, panel: Panel, height: int | None = None, points: float | None = None
) -> Frame:
    """Draw `text` one line per line, clipped at the bottom.

    `height` defaults to the panel's own, which is the ordinary full-screen frame. Passing a larger
    one renders a page taller than the screen, which the device holds and pans inside without a
    round trip. That is the taller page buffer from the UI notes, and the renderer's only part in
    it is agreeing to draw past the bottom of the panel.

    `points` overrides the body size. The UI notes want discrete text-size steps rather than a
    smooth zoom, since the panel cannot track a pinch continuously, so the size is a parameter the
    host re-renders at rather than something the device scales.

    Lines that run past the right edge are not wrapped. Wrapping is a layout question and layout is
    phase 4; clipping keeps this honest about doing nothing clever.
    """
    canvas_height = panel.height if height is None else height
    font_px = panel.points_to_pixels(BODY_POINTS if points is None else points)
    line_height = round(font_px * LINE_SPACING)
    margin = panel.points_to_pixels(MARGIN_POINTS)

    image = Image.new("L", (panel.width, canvas_height), color=255)
    draw = ImageDraw.Draw(image)
    font = ImageFont.load_default(size=font_px)
    y = margin
    for line in text.splitlines():
        if y + line_height > canvas_height - margin:
            break
        draw.text((margin, y), line, font=font, fill=0)
        y += line_height
    return Frame.from_image(image, panel)
