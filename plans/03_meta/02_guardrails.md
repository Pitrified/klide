---
status: done
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
  an actionable message, is fast enough that an agent will actually run it, and has been seen to fail.
  Written as [`../../meta/gates.md`](../../meta/gates.md).
- Stack-independent now: relative link resolution, agreement between each phase's frontmatter and its tracking
  table, the writing rules the repo bans outright, and a CI workflow that runs them.
  Spellcheck and commit message shape were dropped, see below.
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

- The links gate found a real broken link on its first run, in `00_initial/00_start.md`, pointing at a phase file
  that had moved to another folder months of edits ago. The gate paid for itself before it was finished.
- The links gate itself was broken in a way only a failing case could show. It crashed instead of reporting when
  given relative paths, because the crash lived in the code that formats a finding, and a passing run never
  reaches that code. This is the argument for rule 5 of the contract, and it was found by following it.
- No node on this box, so cspell and the markdown linters are unavailable. Spellcheck is dropped rather than
  faked; `.vscode/settings.json` still holds the word list for the editor.
- Commit message shape is dropped too. The rule is a preference with no failing case anyone has hit, and a gate
  without a real failure is decoration.
- The enforcement decision was reversed a day after it was made. CI was chosen over a pre-commit hook because a
  hook is bypassable, which assumed CI would run. It cannot: no GitHub credentials on this box, nothing pushed,
  the workflow has never executed. A bypassable check beats one that never fires, so the hook went in, shared
  through `core.hooksPath` rather than copied into `.git/hooks`.
- Only the `house_rules` category of the writing scan is gated. The rest need triage, and a gate that needs
  judgement teaches people to ignore gates.
