---
status: planned
---

# Phase 2 - Display and input spike

## Overview

Answer the hardware questions that decide the architecture, on the smallest possible amount of code.
Most published Kindle display work targets i.MX devices; the PW5 is MediaTek MT8113,
so FBInk's behaviour on this panel is an assumption, not a fact.
The output of this phase is measurements and a decision on Q3, not a feature.

Context: [`../00_initial/00_start.md`](../00_initial/00_start.md). Depends on [`01_root_access.md`](01_root_access.md).

## Goals

1. Establish whether FBInk drives the PW5 panel correctly, and if not, what does.
2. Characterise refresh: partial update latency, and how many partials before ghosting forces a full refresh.
3. Establish how to read touch events.
4. Resolve Q3 with evidence.

## Plan

- Cross-compile or fetch FBInk for `arm-kindlepw2-linux-gnueabi` and run it on the device. Print text, draw a PNG, exercise the region and waveform flags.
- Compare against built-in `eips -g` as a baseline that is known to exist on the device. If FBInk misbehaves on MT8113, `eips` bounds what is still possible.
- Time a small-region partial update and a full refresh. Record the numbers here with the date, since they are measurements.
- Append text repeatedly to one region and note when ghosting becomes unacceptable, to size the periodic full-refresh interval.
- Identify the touch `/dev/input` node and dump events. Check whether reading it conflicts with the running Amazon framework, and what has to be stopped if it does.
- Establish how to suppress the screensaver and keep the device awake, via `powerd`/lipc or KOReader's KeepAlive approach.
- Write the Q3 recommendation into `00_start.md` as a new question batch if the answer is not clean.

## Out of scope

- Any networking or streaming. Frames in this phase come from files already on the device.
- Rendering markdown, diffs, or anything klide-shaped.
- Power optimisation. Battery measurement is noted as an unknown but does not gate the architecture.

## Done when

- A PNG generated on the host and copied to the device is drawn on screen on demand.
- Partial and full refresh latencies are recorded in this file.
- A touch on the screen produces an identifiable event on the device.
- The device can be held awake with the screen on for longer than the default sleep timeout.
- Q3 has a recommended answer backed by what was observed.

## What the implementation found

