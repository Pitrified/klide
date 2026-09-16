---
status: done
---

# Phase 1 - Requirements and stack

## Overview

Pick the stack the way AD1 says: write down what the thing has to do and what it has to hold up under,
then assess candidates against that list. First because nothing else can start, and because this is the last
technical decision meant to be made in conversation rather than by a gate.
Context: [`00_start.md`](00_start.md).

## Goals

1. A requirement list that a stack can actually be judged against.
2. A candidate assessment with pros, cons and a decision.
3. The language-specific gate slots from the meta track's phase 2 filled in.

## Plan

- Write the requirements. Not features: properties. What has to be true at fifteen features, not at the first one.
  Candidates to cover: frame rendering of text, markdown and diffs at the panel size; holding a long-running
  process that tails a transcript; a wire protocol with a device client at the other end; a headless simulator;
  cross-compiling or otherwise reaching an ARM device later; how well the ecosystem renders text and images;
  what the testing and gate story looks like; how legible it is to an agent that has to work in it unattended.
- Name the candidates and assess each against the list. Rust, Go, Python, Flutter and anything else worth the row.
  One table, pros and cons, and a decision with its reason.
- Note that the host and the simulator need not be the same language, and say explicitly whether they are.
- Where a requirement turns on something measurable rather than arguable, measure that one thing.
  A prototype settles a narrow question here; it does not settle the choice (AD1).
- Once chosen, fill the gate slots left open in [`../03_meta/02_guardrails.md`](../03_meta/02_guardrails.md):
  format, lint, type check, test, and the frame comparison gate.

## Out of scope

- Writing the app. This phase ends at a decision and the gates that enforce it.
- The GPU question, which waits for a measurement (AD6).

## Done when

- The requirement list exists and is specific enough that two people would score a candidate the same way.
- A stack is chosen, with the reasoning and the rejected candidates recorded.
- The gates run on an empty project and fail on a deliberately broken commit.

## What the implementation found

The requirement list, the candidate table and the decision are in [`../../docs/stack.md`](../../docs/stack.md).
Python, for the host, the renderer and the simulator, all three in one language.

- **The phase's real question was whether D10 survives.** D10 already said Python, taken in
  conversation before any requirement was written, which is the habit MD3 exists to stop. Writing
  the requirements first and then scoring against them is the check, and D10 passes it.
- **R5 is why the answer is not Rust.** D1 leaves no klide rendering code on the device, so nothing
  in this track ever cross-compiles. That voids the usual argument for a compiled language, and
  what remains is a compiler's correctness guarantee against an edit-compile-run loop paid on every
  unattended agent attempt (R7).
- **One thing was measured rather than argued.** Rendering a full 1264x1680 page of highlighted
  text costs tens of milliseconds and a paragraph-sized dirty rectangle costs single digits,
  against a panel that answers a partial refresh in hundreds. `Image.quantize` turned out to cost
  more than the rendering, which is avoidable because the renderer picks its own grey levels; that
  is a note for phase 2's wire format, not a finding about the language.
- **Four of the five gate slots are filled**, with ruff for format and lint, mypy in strict mode,
  and pytest. Each was demonstrated failing, and the lint gate found a real unused import in
  `scripts/gates/plan_status.py` the first time it ran, which is the second time a new gate has
  caught something in the gates themselves.
- **The frames gate stays open.** A5 gives the evidence format to phase 2, so writing the
  comparison now would mean guessing the reference storage and the match tolerance as well.
- **The scaffold is deliberately small.** One module holding the panel geometry the device notes
  recorded, because both the renderer and the simulator need it and it is the smallest thing that
  is real rather than a placeholder. Phase 2 is the walking skeleton.
