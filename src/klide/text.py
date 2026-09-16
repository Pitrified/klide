"""Laying text out on a page.

Until now the renderer clipped anything past the right edge, silently, and the sample pages were
wrapped by hand. That was fine while every page was a constant in the source. It stops being fine
the moment the text comes from a transcript nobody wrote to fit.

Wrapping is done by measuring, not by counting characters. The body face is proportional, so a
character count is wrong by a different amount on every line, and the monospace face is used for
exactly the content where alignment carries meaning and must not be re-wrapped at all.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from PIL import ImageFont

from klide.fonts import BODY_GREY, Face, load


@dataclass(frozen=True)
class Style:
    """How one run of text is drawn. The unit layout works in."""

    face: Face = Face.BODY
    size_px: int = 0
    grey: int = BODY_GREY
    #: Monospace content whose alignment means something: code, diffs, tree drawings. Long lines
    #: are cut rather than folded, because folding a diff line makes it lie about its structure.
    preformatted: bool = False

    def font(self) -> ImageFont.FreeTypeFont:
        return load(self.face, self.size_px)


@dataclass(frozen=True)
class Line:
    """One laid-out line, ready to draw."""

    text: str
    style: Style
    indent: int = 0


@dataclass
class Column:
    """A column of a fixed width that lines are poured into.

    It knows its width and nothing about where it sits, so the same column code lays out a
    conversation, a diff or a file listing.
    """

    width: int
    lines: list[Line] = field(default_factory=list)

    def add(self, text: str, style: Style, indent: int = 0) -> None:
        """Add text, wrapped to fit, or cut if it is preformatted."""
        available = self.width - indent
        if style.preformatted:
            for raw in text.split("\n"):
                self.lines.append(Line(_cut(raw, style, available), style, indent))
            return
        for paragraph in text.split("\n"):
            if not paragraph.strip():
                self.lines.append(Line("", style, indent))
                continue
            for wrapped in wrap(paragraph, style, available):
                self.lines.append(Line(wrapped, style, indent))

    def paragraphs(self, text: str, style: Style, indent: int = 0) -> None:
        """Add prose, reflowing it.

        Unlike `add`, a single newline inside a block is treated as a soft break and the lines are
        joined before wrapping, so the panel decides where lines end rather than whoever typed the
        source. A blank line still separates paragraphs. This is what prose wants; `add` stays
        line-oriented because data, listings and anything numbered need their own lines kept.
        """
        for block in text.split("\n\n"):
            joined = " ".join(part.strip() for part in block.split("\n") if part.strip())
            if not joined:
                continue
            self.add(joined, style, indent)
            self.blank(style)
        if self.lines and not self.lines[-1].text:
            self.lines.pop()

    def blank(self, style: Style) -> None:
        self.lines.append(Line("", style, 0))


def measure(text: str, style: Style) -> float:
    return style.font().getlength(text)


def wrap(text: str, style: Style, width: int) -> list[str]:
    """Greedy wrap on spaces, measured in pixels.

    A word longer than the line is broken rather than allowed to overflow, because the alternative
    is silent clipping, which is the failure this module exists to remove. URLs and long paths are
    the realistic case.
    """
    font = style.font()
    out: list[str] = []
    current = ""
    for word in text.split(" "):
        candidate = f"{current} {word}" if current else word
        if font.getlength(candidate) <= width:
            current = candidate
            continue
        if current:
            out.append(current)
        if font.getlength(word) <= width:
            current = word
            continue
        # The word alone does not fit. Break it across lines at the character level.
        piece = ""
        for char in word:
            if font.getlength(piece + char) > width and piece:
                out.append(piece)
                piece = char
            else:
                piece += char
        current = piece
    if current:
        out.append(current)
    return out or [""]


def _cut(text: str, style: Style, width: int) -> str:
    """Trim a preformatted line to fit, marking that something was removed.

    Preformatted lines are not wrapped, so the honest options are to cut or to let the frame lie.
    Cutting with a visible marker is the one that tells the reader they are missing something.
    """
    font = style.font()
    if font.getlength(text) <= width:
        return text
    ellipsis = "…"
    room = width - font.getlength(ellipsis)
    kept = ""
    for char in text:
        if font.getlength(kept + char) > room:
            break
        kept += char
    return kept + ellipsis
