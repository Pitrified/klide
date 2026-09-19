---
status: done
---

# Phase 3 - the four pages

## Overview

The pages themselves, rendered from phase 1's types rather than from fixtures. Three of the four
exist in some form already; the work is as much removal as addition.

## Goals

- Page 1, the session list, with the state column.
- Page 2, the conversation, with the recap header.
- Page 3, a tree of touched files with counts, replacing two existing views per UD8.
- Page 4, one file's diff, with the path trimmed from the left.

## Plan

1. Page 1 from `conversations` in [`../../src/klide/views.py`](../../src/klide/views.py), which today
   shows a name, a turn count and a timestamp. It gains the repo and the state and loses the bullet
   marker, per the specification. Read is per host per session and a tap marks it read (UD12), so the
   row a reader just came back from is the one whose state has changed.
2. The recap header, shared by pages 2, 3 and 4: name, repo, branch, and the added and removed
   totals. One implementation, not three. Its first line is short by whatever the back control takes
   (UD11), and the totals are the only part of it a tap means anything on (UD10).
3. Page 3 as a tree, folding `changed_files` and `file_tree` into one view. Collapse single child
   folders onto one row, because the column is 47 characters and indentation spends it fastest.
4. Page 4 from `one_diff`, which already renders a patch; what it gains is the left trim on a long
   path, which needs a measurement rather than a character count since the header font is
   proportional.
5. Extend the fixtures so the views gate covers the new shapes, including the empty changeset. A
   reference gate covers exactly what its fixture contains, which is the finding from the 2026-09-18
   review and the reason the 6.2 pt text survived three phases.

## Out of scope

- Live updating and the stale marker. Phase 4.
- `one_file`, which stays unrouted per U5.

## Done when

- All four pages render from real data taken off this machine, not from a fixture.
- Someone looks at them on the viewer at true size and says whether they are readable, which is the
  only check in this repo that is not self-referential.
- The views gate covers the tree, the recap and the empty changeset, each demonstrated failing.
- A path longer than the header is trimmed from the left with the end still readable.

## What the implementation found

Implemented 2026-09-19, before phase 2 rather than after it. The order in the tracking table put
navigation first, and navigation has nothing to move between until the pages exist; the pages are
also pure functions of phase 1's types, so they could be built and gated with no loop involved.
Phase 2 follows with something to route to.

**Page 4 is the path alone, not the shared recap.** The plan's step 2 said the recap is shared by
pages 2, 3 and 4; the specification said page 4's top is the file path. The specification wins.
The reader arrived at page 4 from a tree that already showed them the repo and the branch, and the
diff is the view whose alignment carries meaning, so it gets the room. The recap is pages 2 and 3.

**Views now return a `Page`, which is a column and its targets.** UD3 says the host knows which row
a y coordinate landed in because the host laid the page out, and the place that knows is the layout
itself. A `Target` names lines rather than pixels, since a column is laid out before anyone knows
where the page will be scrolled to; turning lines into a y range is the renderer's job, which is
phase 2's.

**The gap between two session rows belongs to neither.** A tap that lands between them opens
nothing, which beats opening whichever one the rounding favours.

**Two references were added for states, not pages.** `changes-empty` is the empty changeset, which
is what this repo shows most of the time, and it carries the stale marker as well, so the refresh
control is in a reference rather than only in a test. Both were shown failing: widening the tree
indent moved 1.23% of the changes page, and rewording the empty line moved 0.27% of the other and
failed its test.

**`conversations`, `changed_files` and `file_tree` are gone**, with their references, per UD8.
`one_file` stays with no route and no targets (U5).
