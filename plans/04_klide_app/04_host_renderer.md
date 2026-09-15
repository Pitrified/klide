---
status: planned
---

# Phase 4 - Host renderer and views

## Overview

The part that makes klide useful: turning a Claude Code session transcript into frames worth looking at.
Context: [`00_start.md`](00_start.md). Depends on phases 2 and 3.
Design notes in [`../02_kobo/01_ui_ux.md`](../02_kobo/01_ui_ux.md), ingestion is D9 and D10.

## Goals

1. A live transcript becomes frames.
2. The view set exists and can be navigated.
3. Streaming behaves: updates coalesce, and the panel is not asked to redraw more often than it can.

## Plan

- Tail the session JSONL, at message-level granularity (D9), read-only (D11).
- Render the views: conversation, conversation list, changed files, one diff, file tree, one file.
  Everything except the diff is a scrolling column of text, so that case comes first.
- Markdown, then syntax highlighting, then diff colouring at a bit depth that has no colour.
- Coalesce updates on the host and send dirty rectangles rather than frames, which is the K4 leaning.
- Each view gets reference frames and a comparison, so a regression in layout fails a gate instead of being noticed.

## Out of scope

- Touch navigation on real hardware.
- GPU, until something here is measurably too slow (AD6).

## Done when

- A real session renders and updates live in the simulator.
- Every view has a reference frame and the comparison gate covers them.
- Navigation works from scripted input.

## What the implementation found
