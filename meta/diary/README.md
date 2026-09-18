# Diary

One file per experiment or review. The point is entries that can be graded later, not read later,
which is why the shape is fixed: an entry that does not say what was expected cannot be wrong, and
an entry that cannot be wrong teaches nothing.

    meta/diary/<YYYY-MM-DD>-<slug>.md

Frontmatter, all four fields required:

```yaml
---
date: 2026-09-18
kind: review          # review | experiment
covers: what was read or tried, in a few words
outcome: one line, including "nothing changed" when nothing did
---
```

Then the five headings from [the phase plan](../../plans/03_meta/04_diary_and_review.md), in order:
**What was tried**, **What was expected**, **What happened**, **What it cost**, **What changed**.

Two rules that are the whole reason this exists.

Failures are recorded at the same weight as successes. A failed approach that is not written down
gets retried, and this repo has already retried one four times.

A finding turns into a mechanism, not into more prose. Route it by scale: a one-off is a line in the
relevant `tracking.md`, a recurring correction is a gate or an edit to a skill or the instructions, a
systemic problem is a principle. An entry whose findings all stayed inside the entry has not
finished.
