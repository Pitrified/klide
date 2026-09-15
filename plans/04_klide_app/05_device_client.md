---
status: draft
---

# Phase 5 - Device client

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
- Any change that is not reversible on a device that goes back.

## Done when

- The device renders what the simulator renders, from the same host.
- The simulator's timing claims are corrected by measurement.

## What the implementation found
