---
status: planned
---

# Phase 3 - Simulator fidelity

## Overview

Make the simulator imitate the parts of the device that can make a frame wrong or a design bad, and take over the
client's own logic as well as the panel's. Context: [`00_start.md`](00_start.md). Depends on phase 2.

## Goals

1. The simulator behaves enough like a Libra 2 that a design fault shows up in it.
2. The client-side behaviour lives here first, so the device client is later a port (AD4).
3. Input exists, so navigation can be exercised without hardware.

## Plan

- Panel: 1264x1680, the right bit depth, and the refresh modes with their different costs.
- Timing: partial update latency, and the difference between a fast mode and a full refresh. Enough that something
  designed to redraw too often looks bad here rather than on the device.
- Input: touch, swipes, and the page-turn buttons, driven both by a person in the viewer and by a script,
  because an agent has to be able to press them.
- Sleep and resume, since the design leans on reconnecting cleanly rather than staying awake.
- Client logic: the bounded cache, the taller page buffer for panning, and the disconnect overlay.
- Ghosting accumulation stays out (A2), to be added when there is something to calibrate it against.

## Out of scope

- Optics, battery, wifi.
- Anything that only matters on real hardware, which phase 5 collects instead.

## Done when

- A scripted session can drive input and produce frames for each step.
- Disconnecting the host leaves the cached frame and the overlay, without a person watching.
- The latency and refresh behaviour is documented as what the simulator claims, so the device can later be compared
  against it.

## What the implementation found
