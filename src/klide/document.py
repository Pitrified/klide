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

Markdown is handled at block level only: headings, paragraphs, bullets, quotes and fenced code.
Inline emphasis is not parsed, so `**bold**` renders with its asterisks. That is a real gap, and
the reason it is a gap rather than a feature is that a line currently carries one style, and
inline runs would need the layout to carry several. Worth doing when something needs it.
"""

from __future__ import annotations

import re

from pygments import lex
from pygments.lexer import Lexer
from pygments.lexers import get_lexer_by_name, guess_lexer
from pygments.token import Token, _TokenType
from pygments.util import ClassNotFound

from klide.fonts import BODY_GREY, FAINT, INK, MUTED, STRONG
from klide.render import Metrics
from klide.text import Column

FENCE = re.compile(r"^\s*```\s*(\S*)\s*$")
HEADING = re.compile(r"^(#{1,6})\s+(.*)$")
BULLET = re.compile(r"^(\s*)[-*+]\s+(.*)$")
NUMBERED = re.compile(r"^(\s*)(\d+)[.)]\s+(.*)$")
QUOTE = re.compile(r"^\s*>\s?(.*)$")


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

        heading = HEADING.match(line)
        if heading:
            column.blank(metrics.body())
            column.add(heading.group(2), metrics.heading(STRONG))
            index += 1
            continue

        bullet = BULLET.match(line)
        if bullet:
            column.add(f"• {bullet.group(2)}", metrics.body(), indent=metrics.body_px)
            index += 1
            continue

        numbered = NUMBERED.match(line)
        if numbered:
            column.add(
                f"{numbered.group(2)}. {numbered.group(3)}",
                metrics.body(),
                indent=metrics.body_px,
            )
            index += 1
            continue

        quote = QUOTE.match(line)
        if quote:
            column.add(quote.group(1), metrics.body(MUTED), indent=metrics.body_px)
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
            paragraph.append(nxt)
            index += 1
        column.add(" ".join(p.strip() for p in paragraph), metrics.body())


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
