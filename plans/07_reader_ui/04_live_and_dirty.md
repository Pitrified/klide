---
status: done
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

Implemented 2026-09-20.

**Two checks, not one.** `Screen.poll` is the cheap one and runs every tick, which is twenty times
a second; `Screen.recheck` is the one that launches a process and runs on a cadence. The cadence
is `AGENTS_POLL`, the 5 s that came out of phase 1's measurement of the CLI, and `git diff` in one
repository is cheaper than that, so one number covers both. Splitting them is what keeps a page
that watches a repository from forking a process at the tick rate.

**Page 1 takes the new state; pages 3 and 4 keep what they have and raise a marker.** That is UD7
implemented as two different answers to the same `recheck`, which is the clearest place to see the
decision in the code.

**The partial-refresh check, done deterministically.** The plan asked for it from the host's log.
It is a test instead: render page 1 with a session idle, render it again with the same session
needing input, and take the dirty rectangle. 1264x45, which is 2% of the panel, and `pick_waveform`
gives it the text mode. A reference or a log reading would both have been weaker; this one fails if
the page ever stops being cheap to update.

It was then watched happening. With `scripts/drive.py --pages` on page 3 of this repo, a tracked
file was edited by a background shell 16 s into the run; the marker appeared on the next cadence,
the tree underneath did not move, and the frame that carried the marker was 1264x441, a quarter of
the panel, in the text mode.

**A file that has left the changeset pops back to the tree.** Refreshing page 4 when the patch is
empty gives the reader the page that can say what is there now, rather than an empty one. The note
says both halves: what was gone, and where they ended up.

**A CLI that stops answering leaves the list alone.** `claude agents --json` failing for one
cadence is not a reason to blank page 1; what is on screen stays until a check succeeds.
