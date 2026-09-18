"""Laying text out on a page.

Until now the renderer clipped anything past the right edge, silently, and the sample pages were
wrapped by hand. That was fine while every page was a constant in the source. It stops being fine
the moment the text comes from a transcript nobody wrote to fit.

Wrapping is done by measuring, not by counting characters. The body face is proportional, so a
character count is wrong by a different amount on every line, and the monospace face is used for
exactly the content where alignment carries meaning and must not be re-wrapped at all.
"""

from __future__ import annotations

from collections.abc import Sequence
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
class Run:
    """A stretch of text drawn in one style. The unit inline markup produces."""

    text: str
    style: Style
    #: Blank space to skip before drawing, in pixels. Table columns need to start at an exact x,
    #: and padding with space characters cannot do that in a proportional face: the number of
    #: spaces that fits a gap changes with what precedes it, so one row's second column starts a
    #: space further along than the next one's.
    pad: float = 0.0


@dataclass(frozen=True)
class Line:
    """One laid-out line, ready to draw.

    A list of runs rather than a string and a style, because `**bold**` and `` `code` `` happen
    inside a sentence and a line with one style cannot show them. Most lines have exactly one run;
    `Column.add` still builds those and nothing that does not need markup had to change.
    """

    runs: tuple[Run, ...]
    indent: int = 0

    @classmethod
    def of(cls, text: str, style: Style, indent: int = 0) -> Line:
        """The common case: one style for the whole line."""
        return cls((Run(text, style),), indent)

    @property
    def text(self) -> str:
        """What the line says, ignoring how it is drawn. Used by callers that count or compare."""
        return "".join(run.text for run in self.runs)

    @property
    def style(self) -> Style:
        """The first run's style, which is the whole line's style for a line that has one.

        Kept because a line's style is what decides its height and what most callers ask about.
        """
        return self.runs[0].style if self.runs else Style()


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
                self.lines.append(Line.of(_cut(raw, style, available), style, indent))
            return
        for paragraph in text.split("\n"):
            if not paragraph.strip():
                self.lines.append(Line.of("", style, indent))
                continue
            for wrapped in wrap(paragraph, style, available):
                self.lines.append(Line.of(wrapped, style, indent))

    def rich(self, runs: Sequence[Run], indent: int = 0, space: Style | None = None) -> None:
        """Add styled pieces as one paragraph, wrapped across the style boundaries.

        Wrapping cannot be done run by run, for two reasons that both come from real content. A
        line ending inside a bold phrase has to know how wide everything before it on that line
        already is. And a word can span runs, as `**bold**ness` does, so the unit being fitted is a
        word made of pieces rather than a string.

        So the runs are first split into words, each carrying its own pieces and whether a space
        preceded it, and the words are then poured into lines. A space at a line break is dropped,
        which is what makes emphasis at the end of a line wrap like any other word.

        `space` is the style the gaps *between* runs are drawn in, which the caller knows and this
        does not. It matters because a monospace space is wider than a body one, so inheriting the
        style from either neighbour leaves a visible gap on one side of every code span. Spaces
        inside a run keep that run's own style.
        """
        available = self.width - indent
        line: list[Run] = []
        used = 0.0

        def flush() -> None:
            nonlocal line, used
            if line:
                self.lines.append(Line(tuple(line), indent))
            line, used = [], 0.0

        def put(piece: Run) -> None:
            nonlocal used
            if line and line[-1].style == piece.style:
                line[-1] = Run(line[-1].text + piece.text, piece.style)
            else:
                line.append(piece)
            used += measure(piece.text, piece.style)

        for spaced, inside, pieces in _split(runs):
            width = sum(measure(piece.text, piece.style) for piece in pieces)
            # A space inside a run keeps that run's style: `uv run klide-live` is one code span and
            # its own spaces have to be monospace or it stops lining up. A space between runs takes
            # the caller's prose style, so a code span does not leave a wide gap beside it.
            if inside is not None and line and line[-1].style == inside:
                gap = inside
            else:
                gap = space or pieces[0].style
            lead = measure(" ", gap) if (spaced and line) else 0.0
            if line and used + lead + width > available:
                flush()
                lead = 0.0
            if lead:
                put(Run(" ", gap))
            if width > available:
                # A word wider than the whole line: a path, a URL, a long identifier. Broken at the
                # character rather than allowed to overflow, because the alternative is silent
                # clipping, which is the failure this module exists to remove.
                for piece in pieces:
                    for char in piece.text:
                        if used + measure(char, piece.style) > available and line:
                            flush()
                        put(Run(char, piece.style))
                continue
            for piece in pieces:
                put(piece)
        flush()

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
        self.lines.append(Line.of("", style, 0))


def measure(text: str, style: Style) -> float:
    return style.font().getlength(text)


def _split(runs: Sequence[Run]) -> list[tuple[bool, Style | None, list[Run]]]:
    """Split styled runs into words: the pieces, whether a space preceded, and that space's style.

    Splitting across the runs rather than inside each one is what keeps `**bold**ness` a single
    word and keeps the space in `a **bold** word`, both of which the obvious per-run version gets
    wrong in opposite directions. The space's own style is carried because a space inside a code
    span belongs to the span and one beside it does not.
    """
    words: list[tuple[bool, Style | None, list[Run]]] = []
    pending: list[Run] = []
    gap = False  # a space has been seen since the last word was closed
    gap_style: Style | None = None  # the style of the run it was seen in
    lead = False  # whether the word being built was preceded by one
    lead_style: Style | None = None
    for run in runs:
        buffer = ""
        for char in run.text:
            if char == " ":
                if buffer:
                    pending.append(Run(buffer, run.style))
                    buffer = ""
                if pending:
                    words.append((lead, lead_style, pending))
                    pending, lead, lead_style = [], False, None
                gap, gap_style = True, run.style
                continue
            if not pending and not buffer:
                lead, lead_style, gap = gap, gap_style, False
            buffer += char
        if buffer:
            pending.append(Run(buffer, run.style))
    if pending:
        words.append((lead, lead_style, pending))
    return words


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
