---
status: draft
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
   marker, per the specification.
2. The recap header, shared by pages 2, 3 and 4: name, repo, branch, and the added and removed
   totals. One implementation, not three.
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
