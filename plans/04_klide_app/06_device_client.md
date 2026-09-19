---
status: draft
---

# Phase 6 - Device client

## Overview

Port what the simulator already does onto the Kobo. Draft, because it needs the borrowed device, and because
what it costs depends on how much phase 3 got right.
Context: [`00_start.md`](00_start.md), device notes in [`../02_kobo/`](../02_kobo/).

## Goals

1. The same wire protocol, spoken by a client on real hardware (AD5).
2. Frames on a real panel, with the real refresh behaviour measured against what the simulator claimed.
3. Input from the real touchscreen and the page-turn buttons.

## Plan

- Settle the client shape, which is Q3 from the original plan and leans toward a KOReader plugin.
- Port the client logic from the simulator rather than writing it again.
- Measure the real panel against the simulator's claims and correct the simulator where it lied.
- Everything the borrowed device requires still applies: reversible, recorded, removable.

## Out of scope

- Rooting or installing anything, which is the `02_kobo` track.
- How the device reaches the host and proves it may, which is
  [`../06_transport_and_access/00_start.md`](../06_transport_and_access/00_start.md). This phase
  assumes a connection exists.
- Any change that is not reversible on a device that goes back.

## Done when

- The device renders what the simulator renders, from the same host.
- The simulator's timing claims are corrected by measurement.

## Open questions

- D1: Whether the wire protocol should carry compressed frames, and what the device can decompress.
  Opened 2026-09-17 by the viewer, which is the other client of the same protocol. Frames reached
  the browser as raw pixels and a person on the far end of an SSH tunnel got four to five seconds a
  press; as PNG the same screen went from 2765 KB to 24 KB. That was a viewer-internal transport
  and changed nothing about `KLD2`, but the arithmetic is worse on the Kobo, not better: a full
  frame is about a megabyte of packed 4bpp, over Wi-Fi, to a device with 512 MB of RAM and a slow
  processor.
  What is known: a panel of rendered text deflates by roughly two orders of magnitude, measured on
  real frames. Dirty rectangles already keep most updates small, so this is about the full redraws,
  which are the ones a reader waits on.
  What is not known, and has to be checked on the device rather than assumed: what decompression
  KOReader's Lua actually has available, and what it costs there. `zlib` through a binding is the
  obvious candidate and its presence is a fact about that firmware, not something to reason out
  from here. A protocol change that the client cannot decode is worse than a slow protocol.
  Not to be decided before the client exists. The reason to write it down now is that the frame
  format is the one part of `KLD2` that a second implementation would have to follow, and the cost
  of finding this out after the Lua client is written is a protocol version.
  Related: AD5, and V4 in [`05_viewer.md`](05_viewer.md) for how the viewer got here.

## What the implementation found
