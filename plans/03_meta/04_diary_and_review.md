---
status: in progress
---

# Phase 4 - Diary and session review

## Overview

The learning half. Without a record, the experiments leave nothing behind and the same painful interaction
happens twice. Context: [`00_start.md`](00_start.md). M6 sets the diary shape, one file per experiment with fixed frontmatter. M5 leaves the cadence flexible on purpose.

## Goals

1. A diary of experiments that can be graded later, not just read.
2. A session review that reliably finds painful interactions rather than summarising what went well.

## Plan

- Fix the diary entry format: what was tried, what was expected, what happened, what it cost, and what changed
  as a result. An entry with no change as a result is still an entry.
- Record failures at the same weight as successes. A failed approach that is not written down gets retried.
- Write the review procedure: what to read, what to look for, and what a finding turns into.
  Candidate signals: the user correcting the same thing twice, an agent asking for a decision the gates should
  have made, a task that needed more turns than its size warranted, and any point where the user took over.
- Feed findings back as edits to the instructions and skills, not as more prose in a plan file.
  This is the "encode lessons in structure" rule from pstack, applied to the interaction itself.

## Out of scope

- Metrics dashboards. Counting comes later, if the diary shows something worth counting.

## Done when

- The diary has entries from real work, including at least one failure.
- One review has run, produced findings, and changed something.

## What the implementation found

Started 2026-09-18, by a review rather than by writing the format first. The user asked what the
last three days should teach, which is goal 2 of this phase arriving before goal 1, and the entry
shape fell out of having something to write rather than being designed in advance.

The shape is in [`../../meta/diary/README.md`](../../meta/diary/README.md): the five headings this
plan already listed, plus four frontmatter fields, plus the rule that an entry whose findings all
stayed inside the entry has not finished.

The first entry is
[`2026-09-18-two-sessions-on-the-viewer.md`](../../meta/diary/2026-09-18-two-sessions-on-the-viewer.md).
It reads the transcript rather than the commits, because the commits record what was decided and the
transcript records what it cost, and the second is the thing a review is for.

What it found, in one line each: the weakest check that could pass, correct here and wrong where it
runs, green gates over content that never exercises the feature, one name answering two questions,
and diagnosis without instrumentation. Of 34 human turns, 12 were corrections.

One finding is already a mechanism: a test that the view fixture exercises every markdown construct
the renderer supports, shown failing by stripping the bold from the fixture. Two are proposed edits
to the instructions and are the user's call, since they change how every future session behaves.

Still open for this phase: the review *procedure*, as opposed to this one review. What to read, on
what cadence, and what a finding turns into. This entry did it by hand.
