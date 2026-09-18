"""Turning content into laid-out lines: markdown, code and diffs.

The constraint that shapes all three is that the panel has sixteen greys and no hue. Everything
syntax highlighting and diff colouring normally say with colour has to be said some other way:
with face, with weight, with a marker in the margin, or with one of the few greys that stays
readable when dithered.

That rules out the obvious translation. Mapping red to one mid grey and green to another gives two
shades a reader cannot tell apart at a glance and has to decode rather than read. Diffs lead with
the `+` and `-` the format already carries, and use shade only to order lines by how much they
matter: an added line in the darkest ink, context at normal reading weight, a removed line lighter
because it is the half going away.

Markdown is handled at block level and inline: headings, paragraphs, bullets, quotes, fenced code
and tables, with bold, code spans and links inside a line. Inline used to be missing, on the
grounds that a line carried one style; a person reading real messages on the panel found the
asterisks and backticks first, so `Line` carries runs now.

Two things are deliberately not rendered. Italic is dropped rather than faked: no italic face is
vendored, and drawing it bold would be a lie about which words were emphasised. Link URLs are
dropped and the link text kept, because the device has no browser and a URL costs most of a
47-character line.
"""

from __future__ import annotations

import re

from pygments import lex
from pygments.lexer import Lexer
from pygments.lexers import get_lexer_by_name, guess_lexer
from pygments.token import Token, _TokenType
from pygments.util import ClassNotFound

from klide.fonts import BODY_GREY, FAINT, INK, MUTED, STRONG
from klide.render import Metrics, rule
from klide.text import Column, Line, Run, Style, measure

FENCE = re.compile(r"^\s*```\s*(\S*)\s*$")
HEADING = re.compile(r"^(#{1,6})\s+(.*)$")
BULLET = re.compile(r"^(\s*)[-*+]\s+(.*)$")
NUMBERED = re.compile(r"^(\s*)(\d+)[.)]\s+(.*)$")
QUOTE = re.compile(r"^\s*>\s?(.*)$")
ROW = re.compile(r"^\s*\|(.+)\|\s*$")
DIVIDER = re.compile(r"^\s*\|[\s:|-]+\|\s*$")

#: Bold, code spans, links and italic, in that order, because `**` has to be tried before `*` and a
#: code span has to win over anything inside it. Italic is matched only to strip its markers.
#: Underscore emphasis is deliberately not matched: `klide_viewer` and `__init__` are far more
#: common in this content than `_emphasis_`, and the false positives would be constant.
INLINE = re.compile(
    r"\*\*(?P<bold>.+?)\*\*"
    r"|`(?P<code>[^`]+)`"
    r"|\[(?P<link>[^\]]+)\]\([^)]*\)"
    r"|\*(?P<italic>[^*\s][^*]*)\*"
)


def inline(text: str, base: Style, strong: Style, code: Style) -> list[Run]:
    """Split a line of markdown into styled runs.

    The caller passes the three styles rather than deriving them, because the same parsing serves a
    paragraph, a heading and a quote, and each wants its own weights and greys.
    """
    runs: list[Run] = []
    at = 0
    for match in INLINE.finditer(text):
        if match.start() > at:
            runs.append(Run(text[at : match.start()], base))
        if match.group("bold") is not None:
            runs.append(Run(match.group("bold"), strong))
        elif match.group("code") is not None:
            runs.append(Run(match.group("code"), code))
        elif match.group("link") is not None:
            runs.append(Run(match.group("link"), base))
        else:
            runs.append(Run(match.group("italic"), base))
        at = match.end()
    if at < len(text):
        runs.append(Run(text[at:], base))
    return runs or [Run(text, base)]


def markdown(text: str, column: Column, metrics: Metrics) -> None:
    """Lay markdown out into a column, at block level."""
    lines = text.split("\n")
    index = 0
    while index < len(lines):
        line = lines[index]

        fence = FENCE.match(line)
        if fence:
            language = fence.group(1)
            index += 1
            body: list[str] = []
            while index < len(lines) and not FENCE.match(lines[index]):
                body.append(lines[index])
                index += 1
            index += 1  # the closing fence
            code("\n".join(body), column, metrics, language=language)
            continue

        if DIVIDER.match(line) and index and ROW.match(lines[index - 1]):
            index += 1  # consumed with the table below, which starts at its header row
            continue

        if ROW.match(line) and index + 1 < len(lines) and DIVIDER.match(lines[index + 1]):
            rows = [_cells(line)]
            index += 2
            while index < len(lines) and ROW.match(lines[index]):
                rows.append(_cells(lines[index]))
                index += 1
            table(rows, column, metrics)
            continue

        heading = HEADING.match(line)
        if heading:
            column.blank(metrics.body())
            style = metrics.heading(STRONG)
            column.rich(
                inline(heading.group(2), style, style, metrics.code_span(STRONG)), space=style
            )
            index += 1
            continue

        bullet = BULLET.match(line)
        if bullet:
            column.rich(
                _prose(f"• {bullet.group(2)}", metrics),
                indent=metrics.body_px,
                space=metrics.body(),
            )
            index += 1
            continue

        numbered = NUMBERED.match(line)
        if numbered:
            column.rich(
                _prose(f"{numbered.group(2)}. {numbered.group(3)}", metrics),
                indent=metrics.body_px,
                space=metrics.body(),
            )
            index += 1
            continue

        quote = QUOTE.match(line)
        if quote:
            column.rich(
                inline(
                    quote.group(1),
                    metrics.body(MUTED),
                    metrics.bold(MUTED),
                    metrics.code_span(MUTED),
                ),
                indent=metrics.body_px,
                space=metrics.body(MUTED),
            )
            index += 1
            continue

        if not line.strip():
            column.blank(metrics.body())
            index += 1
            continue

        # A paragraph runs until a blank line or a block that starts something else.
        paragraph = [line]
        index += 1
        while index < len(lines) and lines[index].strip():
            nxt = lines[index]
            if FENCE.match(nxt) or HEADING.match(nxt) or BULLET.match(nxt) or QUOTE.match(nxt):
                break
            if ROW.match(nxt):
                break
            paragraph.append(nxt)
            index += 1
        column.rich(_prose(" ".join(p.strip() for p in paragraph), metrics), space=metrics.body())


def _prose(text: str, metrics: Metrics) -> list[Run]:
    """Ordinary body text, with its inline markup."""
    return inline(text, metrics.body(), metrics.bold(), metrics.code_span(INK))


#: Token classes, grouped by how much they should stand out rather than by what they mean. Four
#: groups, because more shades than that stop being distinguishable on a dithered panel.
_STRONG_TOKENS = (Token.Keyword, Token.Name.Function, Token.Name.Class, Token.Operator.Word)
_MUTED_TOKENS = (Token.Literal.String, Token.Literal.Number)
_FAINT_TOKENS = (Token.Comment,)


def _is_a(token: _TokenType, parent: _TokenType) -> bool:
    """Whether `token` is `parent` or one of its subtypes.

    Pygments spells this `token in parent`, which reads backwards and which its type stubs describe
    as a string membership test. A token type is a tuple of names, so being a subtype is being
    prefixed by the parent, and saying that outright is both correct and legible.
    """
    return tuple(token[: len(parent)]) == tuple(parent)


def _token_grey(token: _TokenType) -> int:
    for group, grey in ((_STRONG_TOKENS, STRONG), (_MUTED_TOKENS, MUTED), (_FAINT_TOKENS, FAINT)):
        if any(_is_a(token, member) for member in group):
            return grey
    return INK


def lexer_for(text: str, language: str = "") -> Lexer | None:
    """The lexer to use, or None if pygments cannot work out what this is."""
    try:
        return get_lexer_by_name(language) if language else guess_lexer(text)
    except ClassNotFound:
        return None


def line_grey(line: str, lexer: Lexer | None) -> int:
    """The shade one line of code is set in: that of its most prominent token.

    Per line rather than per token, because a laid-out line carries one style. It is enough to tell
    a comment from a statement at a glance, which is what highlighting is for on a page this size.
    Per-token shading needs run-level styling, the same gap as inline markdown emphasis.
    """
    if lexer is None or not line.strip():
        return INK
    greys = [_token_grey(token) for token, value in lex(line, lexer) if value.strip()]
    return min(greys) if greys else INK


def code(
    text: str,
    column: Column,
    metrics: Metrics,
    language: str = "",
    gutter: bool = False,
) -> None:
    """Lay code out in monospace, highlighted by shade.

    `gutter` prefixes line numbers. They are added after the line is lexed, never before: a number
    in front of the source would be lexed as part of it and shade the whole line as a literal.
    """
    if not text.strip():
        return
    lexer = lexer_for(text, language)
    lines = text.split("\n")
    width = len(str(len(lines)))
    for number, line in enumerate(lines, start=1):
        grey = line_grey(line, lexer)
        shown = f"{number:>{width}}  {line}" if gutter else line
        column.add(shown, metrics.mono(grey), indent=metrics.body_px // 2)


#: The leading character is the primary signal, because it is already in the format and a reader
#: does not have to learn it. Shade only reinforces: an added line is set in the darkest ink and a
#: removed line lighter, since it is the half that is going away. Only two shades are used for the
#: body of a diff, because more become a code to decode rather than something to read. Weight is
#: not available here, since the vendored monospace has no bold.
_DIFF_ADDED = "+"
_DIFF_REMOVED = "-"


def diff(text: str, column: Column, metrics: Metrics) -> None:
    """Lay a unified diff out without colour.

    A diff is the one view where alignment carries meaning, so every line is monospace and none is
    wrapped. Long lines are cut with a marker rather than folded, because a folded diff line looks
    like two lines and lies about the change.
    """
    for line in text.split("\n"):
        if line.startswith(("diff ", "index ", "--- ", "+++ ")):
            column.add(line, metrics.mono(FAINT))
        elif line.startswith("@@"):
            column.blank(metrics.body())
            column.add(line, metrics.mono(MUTED))
        elif line.startswith(_DIFF_ADDED):
            column.add(line, metrics.mono(INK))
        elif line.startswith(_DIFF_REMOVED):
            column.add(line, metrics.mono(MUTED))
        else:
            column.add(line, metrics.mono(BODY_GREY))


def _cells(row: str) -> list[str]:
    """The cells of one markdown table row, without the outer pipes."""
    inner = ROW.match(row)
    return [cell.strip() for cell in (inner.group(1) if inner else row).split("|")]


def table(rows: list[list[str]], column: Column, metrics: Metrics) -> None:
    """A markdown table, as columns if they fit and as stacked rows if they do not.

    A 47-character line does not hold three columns of anything worth reading, so width decides the
    shape rather than a preference. Two columns get real columns with the header in bold and a rule
    under it. Anything wider, or anything whose columns cannot be made to fit, becomes one block per
    row: the first cell in bold on its own line and the rest indented beneath it, which is what a
    narrow screen usually does with a wide table and which works for any number of columns.
    """
    if not rows:
        return
    widths = _fit(rows, column.width, metrics)
    column.blank(metrics.body())
    if widths is None:
        _stacked(rows, column, metrics)
        column.blank(metrics.body())
        return

    header, *body = rows
    _row(header, widths, column, metrics, strong=True)
    column.lines.append(rule(metrics))
    for index, row in enumerate(body):
        if index:
            # A blank line between rows. Without it two rows that each wrap to two lines read as
            # one four-line block, which is how the first render of a real table looked.
            column.blank(metrics.body())
        _row(row, widths, column, metrics, strong=False)
    column.blank(metrics.body())


def _fit(rows: list[list[str]], width: int, metrics: Metrics) -> list[int] | None:
    """Column widths in pixels, or None when this table should be stacked instead.

    Widths are proportional to the widest cell in each column, then clamped so no column falls
    below a quarter of the page: a column two words wide that wraps every cell is worse than the
    stacked form.
    """
    count = max(len(row) for row in rows)
    if count != 2:
        return None
    gap = metrics.body_px
    available = width - gap
    wanted = [
        max(measure(row[i], metrics.body()) for row in rows if i < len(row)) for i in range(count)
    ]
    total = sum(wanted) or 1
    widths = [max(available // 4, round(available * part / total)) for part in wanted]
    over = sum(widths) - available
    if over > 0:
        widths[max(range(count), key=lambda i: widths[i])] -= over
    if min(widths) < available // 4:
        return None
    return widths


def _row(
    cells: list[str], widths: list[int], column: Column, metrics: Metrics, strong: bool
) -> None:
    """One table row, its cells wrapped inside their own column and kept side by side.

    Each cell is laid out into a column of its own width, then the results are zipped back together
    so a cell that took three lines does not push its neighbour down.
    """
    gap = metrics.body_px
    base = metrics.bold() if strong else metrics.body()
    laid: list[list[Line]] = []
    for index, width in enumerate(widths):
        cell = Column(width=width)
        text = cells[index] if index < len(cells) else ""
        cell.rich(inline(text, base, metrics.bold(), metrics.code_span(INK)), space=base)
        laid.append(cell.lines or [Line.of("", base)])
    for depth in range(max(len(lines) for lines in laid)):
        runs: list[Run] = []
        used = 0.0
        for index, lines in enumerate(laid):
            start = sum(widths[:index]) + gap * index
            if depth >= len(lines):
                continue
            first = True
            for run in lines[depth].runs:
                runs.append(Run(run.text, run.style, pad=max(0.0, start - used) if first else 0.0))
                used = max(used, start) + measure(run.text, run.style)
                first = False
        column.lines.append(Line(tuple(runs)))


def _stacked(rows: list[list[str]], column: Column, metrics: Metrics) -> None:
    """A table too wide for columns: one block per row, headed by its first cell."""
    header, *body = rows
    for row in body:
        column.rich(
            inline(row[0], metrics.bold(), metrics.bold(), metrics.code_span(INK)),
            space=metrics.bold(),
        )
        for index, cell in enumerate(row[1:], start=1):
            label = header[index] if index < len(header) else ""
            text = f"{label}: {cell}" if label else cell
            column.rich(_prose(text, metrics), indent=metrics.body_px, space=metrics.body())
        column.blank(metrics.body())
