---
status: planned
---

# Phase 5 - First unsupervised run

## Overview

What the other four phases are for. One bounded piece of real work, run without a person watching,
and judged on whether the evidence it produced is trustworthy.
Context: [`00_start.md`](00_start.md). Depends on phases 2, 3 and 4, MD9 sets what the agent is allowed to do: anything needing no GitHub credentials.

## Goals

1. Run one task to completion with no supervision and a hard blast radius.
2. Judge the result on evidence rather than on whether it looks finished.
3. Decide from that whether parallel agents are worth trying here at all.

## Plan

- Pick a task that is real, bounded and reversible, with a finish condition a script can check.
- Set the blast radius explicitly: which paths may be written, whether a commit is allowed, and what must never happen.
  No push is possible from this box, which helps here.
- Run it. Keep everything: transcript, gate output, artifacts.
- Review against the evidence contract from phase 3, not against the summary the agent wrote about itself.
- Only then consider width, and only one step of it: a second agent, in a worktree (MD8).
  The rigor comes first, which is the argument the source material makes, and concurrency is the last dial to turn.

## Out of scope

- Long overnight runs, until one short run has been trusted.
- More than two agents at once, and the cloud path (M9).
- Anything touching the borrowed Kobo.

## Done when

- One unsupervised run has finished and been judged, pass or fail.
- The failure modes it showed are in the diary and have changed a skill, a gate or an instruction.

## What the implementation found
