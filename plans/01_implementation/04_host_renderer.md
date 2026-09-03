---
status: planned
---

# Phase 4 - Host renderer and views

## Overview

The bulk of klide, and by D1 it is entirely ordinary host-side software: take Claude's state, lay it out for the PW5's 1236x1648 grayscale panel (verified against device specs), and emit frames into the phase 3 transport.

Ingestion is settled: klide tails the Claude Code session transcript, one JSONL file per session under
`~/.claude/projects/<project-slug>/` (D9), in Python (D10). Records are message-level, carrying `user`, `assistant`
(with `text`, `thinking` and `tool_use` blocks) and `system` types. The app runs as the regular user (D7);
reading those files needs nothing privileged.

Context: [`../00_initial/00_start.md`](../00_initial/00_start.md). Depends on [`03_frame_transport.md`](03_frame_transport.md).

## Goals

1. Tail a session transcript and turn its records into a conversation model klide can render.
2. Render the conversation view with markdown, streaming token by token.
3. Render the diff view: files changed since the last commit, openable to a standard diff.
4. Render the file view: navigate the tree, open a file, with syntax highlighting.
5. Show tool calls, since `tool_use` blocks are most of what a Claude session actually contains.
6. Switch between multiple concurrent conversations. One transcript file per session makes this mostly file discovery.

## Plan

- Parse the transcript first, against a real file this machine already has, before any rendering. The format is internal and undocumented, so a parser with a snapshot test is the thing that will catch a Claude Code version bump breaking klide.
- Treat unknown record types and unknown content-block types as skippable rather than fatal, for the same reason.
- **Build the simulator first.** Render frames to a window (or a PNG viewer) on the host at exactly 1236x1648, grayscale, with no device attached. Everything in this phase is developed against it, so the render loop can be iterated on in seconds rather than over a wire. This is also what makes phase 4 startable before phase 1 finishes.
- Keep one render path. The simulator and the device must consume the same frame output, differing only in where it is sent, or the two will drift and the simulator will stop predicting the device.
- Build a layout engine sized for the target panel: fixed dimensions, grayscale, no animation, legible at e-ink contrast.
- Conversation view first, since it is the requirement the whole project exists for.
- Diff and file views next; both are static pages and cheaper than the streaming view.
- Conversation switching last, as it is state management rather than rendering.
- Emit dirty regions rather than whole frames wherever the transport supports it.

## Out of scope

- Input. Views are selected from the host in this phase; touch arrives in phase 5.
- Any on-device logic beyond drawing what it is sent.

## Done when

- The simulator renders every view at panel dimensions, and the device shows the same pixels.
- A live Claude session streams into the conversation view on the Kindle, readable at reading distance.
- Diff and file views render correctly and are legible.
- Switching between two conversations works, driven from the host.

## What the implementation found

