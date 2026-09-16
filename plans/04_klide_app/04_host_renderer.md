---
status: done
---

# Phase 4 - Host renderer and views

## Overview

The part that makes klide useful: turning a Claude Code session transcript into frames worth looking at.
Context: [`00_start.md`](00_start.md). Depends on phases 2 and 3.
Design notes in [`../02_kobo/01_ui_ux.md`](../02_kobo/01_ui_ux.md), ingestion is D9 and D10.

## Goals

1. A live transcript becomes frames.
2. The view set exists and can be navigated.
3. Streaming behaves: updates coalesce, and the panel is not asked to redraw more often than it can.

## Plan

- Tail the session JSONL, at message-level granularity (D9), read-only (D11).
- Render the views: conversation, conversation list, changed files, one diff, file tree, one file.
  Everything except the diff is a scrolling column of text, so that case comes first.
- Markdown, then syntax highlighting, then diff colouring at a bit depth that has no colour.
- Coalesce updates on the host and send dirty rectangles rather than frames, which is the K4 leaning.
- Each view gets reference frames and a comparison, so a regression in layout fails a gate instead of being noticed.

## Out of scope

- Touch navigation on real hardware.
- GPU, until something here is measurably too slow (AD6).

## Done when

- A real session renders and updates live in the simulator.
- Every view has a reference frame and the comparison gate covers them.
- Navigation works from scripted input.

## What the implementation found

`uv run klide-views` renders all six views from fixtures and gates them; `uv run klide-live`
watches a real session and streams it to the simulator. The rendering decisions are in
[`../../docs/rendering.md`](../../docs/rendering.md).

- **The transcript format was read, not assumed.** Records carry a `type` of `user`, `assistant`
  and a dozen bookkeeping kinds, and `message.content` is a string or a list of `text`, `thinking`,
  `tool_use` and `tool_result` blocks. The parser was checked against a real 2.6 MB transcript
  before anything was built on it.
- **Thinking has no content to show.** All 219 thinking blocks across both transcripts on this box
  had an empty `thinking` field, with the content in an opaque `signature`. klide shows a marker
  that the assistant was working, because that is all the transcript supports. Found by noticing
  the parser returned zero thinking blocks where a raw count said 94, and checking rather than
  assuming the parser was wrong.
- **Fonts are vendored.** Pillow's bundled face carried phases 2 and 3 and ships neither a
  monospace nor a bold, both of which code, diffs and headings need. DejaVu is in `assets/fonts`
  under the Bitstream Vera terms, which keeps references reproducible without a system font.
- **Colour does not translate, so it was not translated.** Mapping red and green to two mid greys
  gives a reader a code to decode. Diffs lead with the `+` and `-` already in the format and use
  shade only to order lines by relevance. Syntax highlighting is four shades grouped by prominence
  rather than by meaning.
- **Wrapping arrived, and immediately changed three other things.** The hand-wrapped sample pages
  from phases 2 and 3 became reflowed prose, the tests that guarded their source line lengths were
  retargeted at the laid-out lines where the invariant actually lives, and the skeleton's fact
  table had to be split out as preformatted because reflowing it destroyed its columns.
- **Streaming rests on one property, so that property is a test.** A sequence of dirty rectangles
  has to leave the panel showing exactly what sending the whole page would have. If it ever fails,
  a real device is left with stale pixels and no way to notice.
- **Dirty rectangles now have a caller**, which phase 3 explicitly left open. The rectangle is
  found by comparing the rendered pages, not by reasoning about layout, because layout reasoning
  would have to be right about wrapping.
- **Rendering a real session found two defects the fixtures could not.** Every user turn carrying
  only a tool result printed a "you" heading above nothing, and a Bash heredoc rendered as a dozen
  lines of a command nobody reads on a device. Both are fixed and tested; neither showed up in the
  synthetic fixture, which is the argument for `klide-live` existing at all.
- **The view gate uses fixtures, never the machine.** Live git state or a real transcript would
  compare a different page every run. The fixture transcript is synthetic for a second reason: the
  real ones hold actual sessions and are not ours to commit.
- **Not done.** Inline markdown emphasis and per-token highlighting, which are the same gap: a
  laid-out line carries one style. Navigation exists as scripted input from phase 3 and is not
  wired to the view set.
