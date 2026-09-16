---
status: done
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

`uv run klide-skeleton` renders a page at panel size, serves it over a unix socket, receives it in
the simulator, writes it out and compares it against `tests/references/skeleton.png`.
The protocol is written up in [`../../docs/protocol.md`](../../docs/protocol.md).

- **A5 is answered, in three parts, and the reasoning is in the code that implements it.**
  An 8-bit greyscale PNG for the evidence, references committed to the repo, and a tolerance of
  zero. The part worth keeping is why zero is defensible: this compares the host's output before
  any panel is involved, and the host is deterministic once the font stops coming from the system.
  Pillow ships a scalable font and `uv.lock` pins Pillow, so the same text renders to the same
  bytes here, in a worktree and on a runner with no fonts installed.
- **The comparison is of the received frame, not the rendered one.** Comparing what the renderer
  produced would check the renderer and skip the wire entirely, which is most of what this phase
  exists to prove.
- **The protocol's shape was decided by the client that does not exist yet.** KOReader's Lua has no
  `string.unpack`, so every header field is a whole number of bytes, big-endian, and each row of
  pixels is padded to a byte boundary. A test reads the header with byte arithmetic the way Lua
  would, which is weaker than a working Lua client and is the strongest check available before Q3
  is answered.
- **Coordinates are in the header already.** A full frame is the rectangle covering the panel, so
  phase 3's dirty rectangles are the same message with a smaller one rather than a second type.
  This is the one place the skeleton looks ahead, on the grounds that the UI notes already put
  the hybrid as the likely landing point.
- **Levels, not greys.** A frame holds 4-bit levels rather than 8-bit greys, so the comparison is
  exact at the depth the panel actually shows instead of at a depth the host invented and the
  device would have discarded. Reduction is a right shift, following phase 1's finding that
  `Image.quantize` cost more than the rendering that fed it.
- **The frame gate catches a one-pixel margin shift**, reports where the first difference is, and
  writes the rendered frame with the differing pixels in red. Its first version dumped a traceback
  when a reference was missing, which fails the gate contract's rule that a failure says what to
  do; that is fixed.
- **Not done here, on purpose.** No handshake, no acknowledgement, no input, no compression, and
  the host closes after one frame. Phase 3 has the case that forces each of them.
