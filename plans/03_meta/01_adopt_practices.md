---
status: draft
---

# Phase 1 - Adopt practices

## Overview

Decide what this repo takes from existing agent-orchestration practice, and land it.
First because everything after it is easier with the vocabulary settled, and cheap because it is reading and copying.
Context: [`00_start.md`](00_start.md). Blocked on M1, M2 and M3.

## Goals

1. Read pstack at the source rather than through recaps, and record what applies to a repo with no code.
2. Land the chosen skills and principles where the harness loads them.
3. Write down what was rejected and why, so it is not rediscovered.

## Plan

- Clone or read `github.com/cursor/plugins/tree/main/pstack` directly. The recaps in `00_start.md` are secondary.
- Sort every skill into take, adapt, reject. Bias to reject: a repo with no source cannot use most of them yet.
- Translate what we take from Cursor's primitives to Claude Code's, and check each one actually loads.
- Record the token cost of what we added, since it is charged on every session.
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
