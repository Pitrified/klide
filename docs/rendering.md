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

## The reading view

A screen holds as many turns as fit, and no fixed number of them.

It used to hold six. A count cannot know how tall a turn is, so six short shell calls left the
bottom two thirds of the panel blank, which is what the first person to sit with the viewer said
about it. The fill lays out more turns than will fit, keeps the last screenful of lines, and pads
above them, so the newest line sits on the bottom margin and older ones move up as it arrives. The
oldest turn on screen is clipped at the top rather than dropped, the way a terminal clips.

Laying out the whole candidate set at once, rather than measuring turns one at a time, is what
keeps the speaker labels right: whether a turn is labelled depends on the turn before it. The
candidate set doubles until it overflows, so the work is proportional to what ends up on screen
rather than to the length of the session.

A page turn moves by however many turns were showing, which is what makes a press a screenful
whatever a screenful happens to be that time.

This costs nothing extra on the panel, which is worth stating because it sounds as though it
should. Shifting every line up on each new turn means the whole text area changes, and a
full-screen redraw is the expensive kind. But the view already slid when the six-turn window did:
measured patches were 1264x1041 to 1264x1517 before the change and 1264x1512 after, against a 1680
tall screen.

What a reader who has paged back sees next is still open. Live mode was the target, and scrolling
is a separate question.

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

## Markdown

Block level and inline: headings, paragraphs, bullets, numbered lists, quotes, fenced code, tables,
and within a line `**bold**`, `` `code spans` `` and links.

Inline used to be missing, and the note here said it was worth doing when something needed it.
Something did, immediately: the first person to read a real message on the panel saw the asterisks
and backticks before anything else. A laid-out line holds a list of styled runs now, and wrapping
spans them, which is what that was waiting on.

Two things are deliberately not rendered, and both are decisions rather than gaps. **Italic** is
dropped rather than faked, because no italic face is vendored and drawing it bold would be a lie
about which words were emphasised. **Link URLs** are dropped and the text kept, because the device
has no browser and a URL costs most of a 47-character line.

Tables get real columns when there are two of them and the widths work out, with the header in bold
over a rule. Anything wider becomes one block per row, the first cell in bold and the rest indented
beneath it. Width decides which, not a preference: 47 characters does not hold three columns of
anything worth reading.

## Known gaps

**Highlighting is per line, not per token.** A line takes the shade of its most prominent token,
which is enough to tell a comment from a statement at a glance and is what highlighting is for at
this size.

This used to share a cause with inline emphasis, that a laid-out line carried one style. That cause
is gone: a line holds runs now and the renderer advances an x position across them, so per-token
shading is a decision rather than a limitation. It stays per line because nothing has asked for
more, and because sixteen greys on a dithered panel do not hold many distinguishable shades.

**Thinking has no content to show.** Every thinking block in every transcript read on 2026-09-16
(219 of them) had an empty `thinking` field with the content in an opaque signature. The
conversation view shows a marker that the assistant was working, which is all the transcript
supports.
