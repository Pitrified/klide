---
status: planned
---

# Phase 1 - the extractor and the data model

## Overview

The types the four pages read, and the code that fills them from this machine. Nothing renders in
this phase. It is first because every page after it is a function of these types, and because it is
the only part that can be checked without deciding anything about the screen.

## Goals

- One module of types, named after AHP's state model per UD1, covering a session, a chat turn and a
  changeset.
- An extractor filling them from the three local sources: `claude agents --json`, the transcripts,
  and `git` in each session's working directory.
- The derived states of UD6, with the derivation visible in the log.

## Plan

1. Write the types first, from the AHP state model rather than from what the sources happen to
   return. A session carries `title`, `project`, `working_directories`, `status` and `session_id`.
   A changeset carries a `change_kind` and its files. Where a field has no local source, it is
   absent rather than invented.
2. Read `claude agents --json` into a list of sessions. Pin the observed field names in a test
   against a captured sample, since the CLI is someone else's and can change under us.
3. Derive `InputNeeded` and the unread bit from the last turns of each transcript. Write the rule
   down in prose first, then implement the prose. Every derivation logs the session, the conclusion
   and the turn it came from.
4. The changeset from `git diff` against `HEAD`, working tree plus index (UD5), per file, with the
   added and removed counts and the patch text.
5. A command that prints what the extractor sees, so the output can be read without a panel.

## Out of scope

- Any rendering, any navigation, any input. Phases 2 and 3.
- The `change_kind` cycle. Recorded as U6; the field exists in the type and only one value is filled.
- Anything about a session on another machine. Every source here is local.

## Done when

- The types exist and a person can hold them against the AHP state model page and see the
  correspondence.
- The command prints the five or so live sessions on this box with their repos and states, and the
  states are right when checked by hand against what those sessions are actually doing.
- A session waiting on input is reported as waiting on input, demonstrated by putting one in that
  state rather than by reasoning about the rule.
- The git side reports a changeset that matches `git diff --numstat` run by hand, including the empty
  case.

## What the implementation found
