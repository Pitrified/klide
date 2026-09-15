---
status: planned
---

# Phase 2 - Guardrails

## Overview

Replace the person in the loop for technical decisions with checks that fail loudly.
MD3 only works if the gates exist; until then "the agent decides" means "nobody decides".
Context: [`00_start.md`](00_start.md).

## Goals

1. State what a gate must provide before it counts as one.
2. Land the stack-independent gates now.
3. Leave a defined slot for the language-specific gates the app track will fill.

## Plan

- Write the gate contract: every gate runs locally with one command, runs in CI on the same command, fails with
  an actionable message, and is fast enough that an agent will actually run it.
- Stack-independent now: markdown and link checking on the plan folders, spellcheck against the existing
  `cSpell.words`, commit message shape, and a CI workflow that runs them.
- Define the slots the app track fills when the stack lands: format, lint, type check, unit test, and the
  performance or frame-comparison gate that M7 points at.
- Decide the enforcement point. A pre-commit hook, CI only, or both, and what an agent is allowed to bypass.
- No gate without a failing case demonstrated first, or it is decoration.

## Out of scope

- Language-specific tooling, which depends on the stack decision in the app track.
- Deployment. There is nothing to deploy.

## Done when

- The gate contract is written down.
- CI runs on every push and fails on a deliberately broken commit.
- The list of empty slots exists, with what each will check.

## What the implementation found
