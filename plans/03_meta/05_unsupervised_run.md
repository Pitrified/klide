---
status: draft
---

# Phase 5 - First unsupervised run

## Overview

The point of the other four phases. One bounded piece of real work, run without a person watching,
and judged on whether the evidence it produced is trustworthy.
Context: [`00_start.md`](00_start.md). Depends on phases 2, 3 and 4, and on M4 for what the agent is allowed to do.

## Goals

1. Run one task to completion with no supervision and a hard blast radius.
2. Judge the result on evidence rather than on whether it looks finished.
3. Decide from that whether parallel agents are worth trying here at all.

## Plan

- Pick a task that is real, bounded and reversible, with a finish condition a script can check.
- Set the blast radius explicitly: which paths may be written, whether a commit is allowed, and what must never happen.
  No push is possible from this box, which is a useful accident.
- Run it. Keep everything: transcript, gate output, artifacts.
- Review against the evidence contract from phase 3, not against the summary the agent wrote about itself.
- Only then consider width: a second agent, an adversarial reviewer, or a swarm.
  The rigor comes first, which is the whole argument of the source material.

## Out of scope

- Long overnight runs, until one short run has been trusted.
- Anything touching the borrowed Kobo.

## Done when

- One unsupervised run has finished and been judged, pass or fail.
- The failure modes it showed are in the diary and have changed a skill, a gate or an instruction.

## What the implementation found
