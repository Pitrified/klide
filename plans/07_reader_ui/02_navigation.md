---
status: draft
---

# Phase 2 - the stack, the tap and the back control

## Overview

How a reader moves. Four pages, one way down and one way up, on a wire that already carries the
events this needs.

## Goals

- A page stack: push on a tap that opens something, pop on the back control, per UD2.
- A tap routed to the row it landed on, per UD3.
- The physical buttons scrolling whatever is on screen, on all four pages, per UD4.
- The gesture map in [`../02_kobo/01_ui_ux.md`](../02_kobo/01_ui_ux.md) updated to say what it now is.

## Plan

1. Decide U7 before writing anything: whether navigation lives inside the loop in
   [`../../src/klide/serve.py`](../../src/klide/serve.py) or above it. The stack's state goes wherever
   that lands.
2. A layout that records where each row was drawn, so a y coordinate maps back to the thing it names.
   `lay_conversation` in [`../../src/klide/views.py`](../../src/klide/views.py) already returns where
   each turn began, which is the same trick and the pattern to follow.
3. The back control, in the top right of every page, and U2 answered by measuring what reserving the
   strip costs in lines rather than by guessing.
4. Route tap, button and swipe through one place that owns the stack, so an event that means nothing
   on the current page is refused visibly rather than dropped. The diary review's fifth pattern is
   that a press correctly ignored and a press that never arrived look identical.
5. Update the gesture map with what replaced it and why, keeping the old text visible per the repo's
   planning rule.

## Out of scope

- What the four pages contain. Phase 3.
- Swipe as a second way back. Rejected in the interview, not revisited here.
- Pinch, long hold and the rest of the provisional map, which are untouched by this.

## Done when

- The viewer can walk from page 1 to page 4 and back by tapping and pressing, with no view reachable
  by two different routes.
- A tap on a row opens that row and not the one above it, checked on the first row, the last row, and
  the gap between two rows.
- Every ignored event leaves a line saying it was ignored and why.
- `scripts/drive.py` can drive the whole walk, since a navigation path that only a person can exercise
  is the thing the harness exists for.

## What the implementation found
