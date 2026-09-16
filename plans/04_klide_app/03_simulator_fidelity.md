---
status: done
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

`uv run klide-session` drives nine steps and writes the screen after each one. The panel and the
client logic are in [`../../src/klide/device.py`](../../src/klide/device.py); what the simulator
claims about a Libra 2, and which claims are documentation rather than measurement, is in
[`../../docs/simulator.md`](../../docs/simulator.md).

- **The latency numbers are sourced, not invented.** This was the phase's real risk: the device is
  not here, and a plausible invented millisecond figure is the worst possible output for a runbook.
  Research found that E Ink does not publish per-mode timings at all and that they vary with panel,
  controller and temperature, so no vendor number exists. FBInk's `fbink.h` does document an
  approximate duration per waveform mode, and FBInk is the tool this project would drive on the
  device, so those are the figures used. Every `Mode` carries its source string and a test asserts
  that it says "not measured on a Libra 2".
- **The ordering is trustworthy and the absolute values are not**, and the code says so rather than
  implying otherwise. Calibration is a phase 5 task that replaces one table.
- **A gate that passed a change it should have caught.** Breaking the client deliberately found
  that quadrupling the flash rate moved no pixels, because ghosting is not modelled (A2), so the
  image comparison passed it. The fix is a refresh ledger: a text file recording what each step
  cost the panel, compared exactly like a reference frame. Three deliberate breakages now fail:
  a pan error, a smaller cache, and the redraw policy change that started it.
- **The ledger had to be recorded during the run.** Reconstructing it afterwards from the device's
  refresh history attributed all eight refreshes to the first step, because the history carries no
  step boundaries. Caught by reading the output rather than by a test.
- **K9 is answered by building it.** The taller page buffer and the cache are the same thing: a
  bounded cache of pages keyed by an id the host assigns, where a page may be any height and the
  buffer is whichever entry is on screen. It cost a page id on the wire.
- **The protocol moved to version 2**, because a second message type going the other way does not
  fit one fixed header. It split into a common header and a type-specific body. The encoding rules
  did not change; they were already fixed by the Lua client that does not exist yet.
- **Dirty rectangles are a capability with no caller.** The device draws a partial rectangle and it
  is tested, but every message the host actually sends is a whole page. Phase 4 has the case that
  forces one, which is streaming text into a view a paragraph at a time. Listing this phase as
  covering dirty rectangles would overstate what runs.
- **The suite got slow and was fixed rather than tolerated.** Six session tests each running a
  full-panel session took the suite to sixteen seconds, which is the kind of number that gets a
  gate skipped. They share one run through a module fixture now.
- **The writing gate missed a word the writing rules ban.** "load-bearing" reached a document and
  passed. Adding it to the hard gate immediately produced a false positive on a log entry that
  legitimately names the words it removed, which is the case the gates contract warns about, so the
  words went into the advisory category the by-hand scan reads instead.
