---
status: planned
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
