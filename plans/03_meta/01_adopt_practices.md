---
status: in progress
---

# Phase 1 - Adopt practices

## Overview

Decide what this repo takes from existing agent-orchestration practice, and land it.
First because everything after it is easier with the vocabulary settled, and cheap because it is reading and copying.
Context: [`00_start.md`](00_start.md). M1 is b, so this is a cherry-pick: read pstack, take a few skills and principles, write our own thin router later. M2 is c and M3 is Claude Code only.

## Goals

1. Read pstack at the source rather than through recaps, and record what applies to a repo with no code.
2. Land the chosen skills and principles where the harness loads them.
3. Write down what was rejected and why, so it is not rediscovered.

## Plan

- Clone or read `github.com/cursor/plugins/tree/main/pstack` directly. The recaps in `00_start.md` are secondary.
- Sort every skill into take, adapt, reject. Bias to reject: a repo with no source cannot use most of them yet.
- Translate what we take from Cursor's primitives to Claude Code's, and check each one actually loads.
- Record what the addition costs. Corrected during the phase: a skill's body is not charged on every session,
  only its description is, because Claude Code loads bodies on invocation. The cost to measure is the description,
  and the comparison is against putting the same text in the always-loaded instructions file.
- Capture the principles as short files, one rule each, rather than as a page of prose.

## Out of scope

- Writing our own router or `-mode` skill. That needs a few real tasks to mine first.
- Portability to other harnesses (M3).
- Anything requiring a running product to verify, which is phase 2 of the app track.

## Done when

- The take, adapt, reject list exists with a reason per entry.
- What we took loads in a fresh session and is exercised at least once.
- The session token overhead it adds is measured, not estimated.

## What the implementation found

- The plan's token claim was wrong and is corrected above. Skill bodies load on invocation, descriptions load always.
  That changed the design: four principles became one skill, because four skills would have cost four descriptions
  to save nothing.
- pstack is 172 KB of skill text and almost none of it fits a repo with no code. The rejections are not close calls:
  five skills reconstruct history this repo does not have, five are writing or TypeScript specific, three are Cursor
  primitives. The take/adapt/reject list with a reason each is in [`../../meta/adoption.md`](../../meta/adoption.md).
- The principles themselves are short, 1 to 2.5 KB each, and are the part that transfers. The router and its
  twenty-three playbooks are the part that does not, yet.
