---
status: planned
---

# Phase 5 - Viewer and first human feedback

## Overview

A window that shows the simulator's screen and lets a person press the buttons.
Context: [`00_start.md`](00_start.md), and A8 there, which parked the viewer until something needed it.
Something does. Depends on phases 3 and 4.

## Why this exists

Not because a viewer is convenient. Because every check in this repo is currently self-referential.

The frame gate compares klide's output against a reference klide produced. So does the session gate,
and so does the views gate. They catch a change, which is what they are for, and they cannot catch a
design that was wrong when the reference was written. The agent sets the expectation and then meets it.

That is not hypothetical here. Body text rendered at 6.2 pt through phases 2, 3 and most of 4, on a
panel where that is half the smallest size anyone sets a paperback in. Every gate passed the whole
time. It was found when a person looked at the numbers and said the screen would be unreadable, and
the fix then took an hour. The same loop is presumably still running on things nobody has looked at
yet: line spacing, how a tool call reads, whether the six views are the right six, whether a page
three screens tall is a sensible unit.

A person looking at the screen is the only signal in the system that does not come from the system.
MD10 says the frame is the evidence, and this phase is about who gets to judge it.

## Goals

1. A person can see what the simulator is showing, without reading a PNG off disk.
2. A person can drive it: the page-turn buttons, a tap, a swipe.
3. Feedback from doing that is collected and acted on, and the ones that change the design are recorded.

## Plan

- A window showing the current frame, scaled to fit an ordinary monitor, redrawing when the frame changes.
  The scale factor is displayed, because a 300 ppi panel shown at 96 ppi is misleading by default and
  that misleading is exactly what caused the legibility fault.
- A way to see it at true physical size, or as close as the monitor allows, since that is the thing
  that cannot be judged from a scaled screenshot.
- Buttons for the two physical page-turn keys, wired to the `InputEvent.press` the scripted session
  already sends. No new protocol.
- Click to tap, drag to swipe, settling on release in short one-directional drags (A8, answered).
  The viewer must not offer smooth dragging the panel cannot deliver.
- Feed it from `klide-live` so the content is a real session rather than a fixture.
- Collect what the first sitting turns up, in one file, separating what is a bug from what is a
  preference from what is a design fault.

## Out of scope

- Anything the device does. This is a window onto the simulator, not a second client.
- Making the viewer pretty. It is an instrument.
- Becoming a gate. It cannot be one: a person is not deterministic, and that is the point of it.

## Open questions

- V1: What the viewer is written in. Python with tkinter is in the standard library and needs no
  new dependency, which matters because this box has no node and the stack doc's R8 applies here too.
  A browser page served locally is the alternative and pulls in more. Recommended: tkinter, and
  revisit if it fights.
- V2: Whether the viewer shows the panel's claimed refresh behaviour, or ignores it. Showing it
  means a redraw takes the hundreds of milliseconds the simulator claims, which is what makes a
  design that redraws too often feel as bad as it would on the device. MD10 argues for showing it.
  The counter-argument is that a person testing layout does not want to wait. Recommended: show it,
  with a switch to turn it off, and record which one gets used.

## Done when

- The viewer runs, shows a live session, and responds to the buttons and to a tap.
- A person has sat with it and the feedback is written down.
- Whatever that feedback changed is in the code, or recorded as deliberately not changed.

## What the implementation found
