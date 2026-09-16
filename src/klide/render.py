"""Drawing laid-out lines onto a frame.

Two layers, kept apart on purpose. `text` decides where words go; this decides what pixels they
become. Separating them is what lets a view's content be checked without rendering it, and rendered
without knowing what it means.

Sizes are in typographic points, not pixels, because the panel is 300 ppi and a pixel size picked
while looking at a desktop monitor comes out about a quarter of its apparent size on the device
(AD8). The first version of this file used 26px, which is 6.2pt: roughly half the smallest size
anyone sets a paperback in. The point of an e-reader is not straining to read it.

Faces are vendored under `assets/fonts` rather than taken from the system, so the same text renders
to the same bytes here, in a worktree and on a CI runner.
"""

from __future__ import annotations

from dataclasses import dataclass

from PIL import Image, ImageDraw

from klide.fonts import BACKGROUND, BODY_GREY, RULE, Face
from klide.frame import Frame
from klide.panel import Panel
from klide.text import Column, Line, Style

BODY_POINTS = 11.0
LINE_SPACING = 1.45
MARGIN_POINTS = 11.5

#: Monospace at the same point size reads wider than the body face and fits fewer characters a
#: line, so code is set a little smaller. Still above the 9pt floor.
MONO_POINTS = 9.5
HEADING_POINTS = 13.0


@dataclass(frozen=True)
class Metrics:
    """Every size a page needs, derived once from the panel."""

    panel: Panel
    body_px: int
    mono_px: int
    heading_px: int
    line_height: int
    margin: int

    @classmethod
    def for_panel(cls, panel: Panel, points: float = BODY_POINTS) -> Metrics:
        body_px = panel.points_to_pixels(points)
        return cls(
            panel=panel,
            body_px=body_px,
            mono_px=panel.points_to_pixels(points * MONO_POINTS / BODY_POINTS),
            heading_px=panel.points_to_pixels(points * HEADING_POINTS / BODY_POINTS),
            line_height=round(body_px * LINE_SPACING),
            margin=panel.points_to_pixels(MARGIN_POINTS),
        )

    @property
    def column_width(self) -> int:
        return self.panel.width - 2 * self.margin

    def body(self, grey: int = BODY_GREY) -> Style:
        return Style(face=Face.BODY, size_px=self.body_px, grey=grey)

    def bold(self, grey: int = BODY_GREY) -> Style:
        return Style(face=Face.BOLD, size_px=self.body_px, grey=grey)

    def heading(self, grey: int = BODY_GREY) -> Style:
        return Style(face=Face.BOLD, size_px=self.heading_px, grey=grey)

    def mono(self, grey: int = BODY_GREY) -> Style:
        return Style(face=Face.MONO, size_px=self.mono_px, grey=grey, preformatted=True)

    def column(self) -> Column:
        return Column(width=self.column_width)


def grey_to_8bit(grey: int, panel: Panel) -> int:
    """A level index to the 0-255 value Pillow draws with."""
    return grey * 255 // (panel.grey_levels - 1)


def render_lines(
    lines: list[Line], panel: Panel, metrics: Metrics | None = None, height: int | None = None
) -> Frame:
    """Draw laid-out lines as a frame, one line per line, clipped at the bottom.

    `height` larger than the panel produces a page the device pans inside without a round trip.
    """
    m = metrics or Metrics.for_panel(panel)
    canvas_height = panel.height if height is None else height
    image = Image.new("L", (panel.width, canvas_height), color=grey_to_8bit(BACKGROUND, panel))
    draw = ImageDraw.Draw(image)

    y = m.margin
    for line in lines:
        if y + m.line_height > canvas_height - m.margin:
            break
        if line.text:
            draw.text(
                (m.margin + line.indent, y),
                line.text,
                font=line.style.font(),
                fill=grey_to_8bit(line.style.grey, panel),
            )
        y += m.line_height
    return Frame.from_image(image, panel)


def page_height(lines: list[Line], panel: Panel, metrics: Metrics | None = None) -> int:
    """How tall a page has to be to hold these lines, rounded up to whole screens.

    Whole screens because the device pans a screen at a time, so a page ending mid-screen would
    leave a partial view at the bottom with nothing below it.
    """
    m = metrics or Metrics.for_panel(panel)
    needed = 2 * m.margin + len(lines) * m.line_height
    screens = max(1, -(-needed // panel.height))
    return screens * panel.height


def render_column(column: Column, panel: Panel, metrics: Metrics | None = None) -> Frame:
    """Draw a whole column as a page tall enough to hold it."""
    m = metrics or Metrics.for_panel(panel)
    return render_lines(column.lines, panel, m, height=page_height(column.lines, panel, m))


def rule(metrics: Metrics) -> Line:
    """A horizontal rule, drawn as a run of box characters.

    Text rather than a rectangle so it sits on the line grid like everything else, and in the
    lightest readable grey because it separates rather than says anything.
    """
    style = Style(face=Face.MONO, size_px=metrics.mono_px, grey=RULE, preformatted=True)
    count = int(metrics.column_width / style.font().getlength("─"))
    return Line("─" * max(1, count), style)


def render_text(
    text: str, panel: Panel, height: int | None = None, points: float | None = None
) -> Frame:
    """Draw plain text as a frame, wrapped to the column.

    The simple path, kept for the walking skeleton and the scripted session, which want a page of
    text and nothing else. Unlike phase 2's version this wraps rather than clipping.
    """
    m = Metrics.for_panel(panel, BODY_POINTS if points is None else points)
    column = m.column()
    column.add(text, m.body())
    return render_lines(column.lines, panel, m, height=height)
