# Rendering

How klide turns a conversation into something readable on a 300 ppi panel with sixteen greys and
no colour. Built in app phase 4.

## The layers

Four, and the split is what makes any of it checkable.

    transcript  a Claude Code JSONL becomes Turns and Blocks
    document    markdown, code and diffs become styled lines
    text        lines are wrapped or cut to the column, by measuring
    render      lines become pixels

A view sits on top and is a pure function: data in, a `Column` of styled lines out. It fetches
nothing and renders nothing. That is why `tests/test_views.py` can ask whether a heading is a
heading without drawing anything, and why the `views` gate can check what the page looks like
without knowing what it means.

## Type

Sizes are typographic points converted through `Panel.ppi` (AD8), never pixels.

| role | size | face |
| --- | --- | --- |
| heading | 13 pt | DejaVu Sans Bold |
| body | 11 pt | DejaVu Sans |
| code, diffs, listings | 9.5 pt | DejaVu Sans Mono |

Body is 11 pt because that is book body size, giving 23 lines and about 51 characters a screen at
an x-height of 2.03 mm. Monospace is set smaller because at the same point size it reads wider and
fits fewer characters a line; 9.5 pt is still above the 9 pt floor a test holds.

Faces are vendored under `assets/fonts` rather than loaded from the system. A reference frame is
only a gate if the same text renders to the same bytes here, in a worktree and on a runner, and no
runner is guaranteed to have a given font. Pillow's bundled face carried phases 2 and 3, and phase
4 needed a monospace and a bold, which Pillow ships neither of.

## Greys

Sixteen levels, no hue. Everything colour would normally carry has to be said with face, shade,
indentation, or a marker the format already has.

| name | level | used for |
| --- | --- | --- |
| ink / strong | 0 | code, added diff lines, the current item |
| body | 2 | body text, diff context |
| muted | 6 | labels, strings, removed diff lines, quotes |
| faint | 9 | comments, diff headers, the thinking marker |
| rule | 11 | horizontal rules |
| background | 15 | the page |

Fewer shades than the panel has, on purpose. Mid greys dither on e-ink and stop being
distinguishable at text size, so the palette uses the dark end for anything that has to be read and
keeps the light end for things that separate rather than say anything.

## Why diffs are not recoloured

The obvious translation is red to one grey and green to another. That gives a reader two mid
shades to tell apart at a glance, which is a code to decode rather than something to read.

Diffs instead lead with the `+` and `-` the format already carries, which a reader does not have to
learn, and use shade only to order lines by how much they matter: an added line in the darkest ink,
context at normal reading weight, a removed line lighter because it is the half going away. Weight
is not available, because the vendored monospace has no bold.

A diff is the one view whose alignment carries meaning, so its lines are never wrapped. A line too
long for the column is cut with an ellipsis, because folding it would make one line look like two
and lie about the change.

## Wrapping

By measuring, not by counting characters. The body face is proportional, so a character count is
wrong by a different amount on every line.

Prose is reflowed: a single newline inside a paragraph is a soft break and the panel decides where
lines end. Preformatted content is not, because code, diffs and listings mean something by their
line breaks. A word longer than the column is broken rather than allowed to overflow; a long path
or URL is the realistic case, and the alternative is the silent clipping this replaced.

## Streaming

A growing transcript is not redrawn whole. Two limits decide when anything is sent, because either
alone behaves badly: a quiet period alone never fires while the assistant is still writing, and a
deadline alone fires mid-burst and spends refreshes on states nobody reads.

What gets sent is the rectangle that changed, found by comparing the new page against the old one
rather than by reasoning about layout. Layout reasoning would have to be right about wrapping, and
being wrong would leave stale pixels on a device with no way to notice. The property that makes
this safe is a test: a sequence of dirty rectangles has to leave the panel showing exactly what
sending the whole page would have.

A2 is never chosen for text despite being the fastest mode. It goes from black and white to black
and white only, and antialiased text is neither.

## Known gaps

Both are the same gap seen twice, and both are cheap to describe and not cheap to fix.

**Inline emphasis is not parsed.** `**bold**` renders with its asterisks. Markdown is handled at
block level: headings, paragraphs, bullets, quotes and fenced code.

**Highlighting is per line, not per token.** A line takes the shade of its most prominent token,
which is enough to tell a comment from a statement at a glance and is what highlighting is for at
this size.

Both exist because a laid-out line carries one style. Runs within a line would need `Line` to hold
a list of styled spans and the renderer to advance an x position across them. Worth doing when
something needs it, which nothing does yet.

**Thinking has no content to show.** Every thinking block in every transcript read on 2026-09-16
(219 of them) had an empty `thinking` field with the content in an opaque signature. The
conversation view shows a marker that the assistant was working, which is all the transcript
supports.
