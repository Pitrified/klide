---
status: planned
---

# Phase 3 - Interaction contract

## Overview

The shape of the exchange between the user and an agent, and between agents, once specification is the input
and evidence is the output. This is the phase that makes MD3 concrete.
Context: [`00_start.md`](00_start.md). Depends on phase 2 for what evidence a gate can produce.

## Goals

1. Define what a functional specification looks like here, at a size a person will actually write.
2. Define what an agent must hand back before work counts as done.
3. Define how work is handed between agents without a person relaying it.

## Plan

- Draft the spec template: what the thing must do, how it is observed, what is out of scope, and the finish
  condition. Keep it short enough to write in one sitting.
- Draft the evidence contract: which artifact proves the change, where it is stored, and who checks it.
  For klide this is a rendered frame, per M7.
- Decide the handoff record between agents: task brief, owner, acceptance criteria, evidence required.
  The recap of Lauren Tan's workflow describes a coordinator, an owner and an independent reviewer; worth trying
  at this scale before assuming it is overkill.
- Write one real spec for a slice of the app and run it end to end.

## Out of scope

- Multi-agent parallelism, which comes after a single agent works against this contract.
- Anything requiring the physical device.

## Done when

- A spec template and an evidence contract exist in the meta folder.
- One real task has gone from spec to evidence without the user making a technical decision mid-flight.

## What the implementation found
