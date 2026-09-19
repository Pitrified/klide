---
status: draft
---

# Phase 4 - live where it helps, stale where it does not

## Overview

What moves under the reader and what does not, per UD7, and the marker that keeps holding still from
becoming lying.

## Goals

- Page 1's state column updating in place while the reader looks at it.
- Pages 3 and 4 frozen once drawn, marked when the changeset behind them has moved, and redrawn
  by tapping that marker.
- Page 2 unchanged: live at the tail, frozen once paged back.

## Plan

1. Page 1 updates as a dirty rectangle over the state column rather than a full page. The streaming
   machinery in [`../../src/klide/stream.py`](../../src/klide/stream.py) already sends only what
   changed, so this is a question of what the page is a function of, not of new transport.
2. A revision on the changeset, bumped when the extractor sees the working tree move. Pages 3 and 4
   record which revision they were drawn from.
3. The marker itself, when those two numbers differ. What it says matters more than where it sits:
   reading a diff of a file that has since changed is worse than useless, and a subtle marker is the
   same as no marker.
4. The marker is a tap target and redrawing is what tapping it does (UD9), so it is sized to be hit
   rather than only to be read, and it routes through the same place phase 2 gave the other taps.
   The case worth handling deliberately is a file that has left the changeset entirely: refreshing
   page 4 then has nothing to draw, and popping back to page 3 is more use than an empty page.
5. Confirm from the host's own log that page 1 updating does not turn every tick into a full screen
   refresh, which is the same check the bottom anchored conversation needed.

## Out of scope

- Any polling cadence decision, which is U4 and belongs to phase 1's measurement.
- Updating pages 3 and 4 in place, which UD7 rejects.

## Done when

- A session that starts waiting for input changes state on page 1 while the page is being looked at,
  without the reader touching anything.
- Editing a file while page 4 shows its diff produces a marker, and the diff on screen does not move
  until the marker is tapped, at which point it shows the edit.
- Reverting a file entirely while page 4 shows its diff, then tapping the marker, does something a
  reader can follow rather than showing an empty page.
- The refresh ledger shows the state column update as a partial refresh, not a full one.

## What the implementation found
