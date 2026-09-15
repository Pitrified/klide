---
status: planned
---

# Phase 2 - Walking skeleton

## Overview

One frame, rendered on the host, carried over the wire, drawn by the simulator, and compared against a reference.
Thin but complete: it is the first thing that makes the evidence loop real, and everything after it is widening.
Context: [`00_start.md`](00_start.md). Depends on phase 1.

## Goals

1. A frame goes host to simulator and is displayed.
2. A frame comparison exists and can fail.
3. The wire protocol has a first shape, drawn from what the skeleton needed rather than from a design document.

## Plan

- Render one static frame of text at the panel size on the host.
- Send it. Whatever transport is cheapest for a local process; the protocol matters, the socket does not, yet.
- Have the simulator write it out as an image file (AD2).
- Build the comparison: a frame against a stored reference, producing a result a script can act on and an artifact
  a human can look at when it fails. This settles A5, which was deliberately left open until there was a real frame
  to compare.
- Decide reference storage: in the repo or generated, and what tolerance counts as a match at this bit depth.
- Write down the protocol that fell out of this, and check it against AD5: the device client has to be able to
  speak it later.

## Out of scope

- Streaming, dirty rectangles, refresh modes, input. Phase 3.
- Markdown, diffs, syntax highlighting, views. Phase 4.

## Done when

- One command renders, transports, displays and compares a frame.
- The comparison fails when the frame is deliberately wrong, and says something useful when it does.
- The gate from phase 1's frame comparison slot runs this in CI.

## What the implementation found
