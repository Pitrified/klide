---
status: planned
---

# Phase 3 - Frame transport

## Overview

The first end-to-end klide: the host generates frames continuously and the Kindle draws them as they arrive,
with no page reload and no button press. This is the README's primary requirement, isolated from any content.

Left as draft until phase 2 reports, because the client shape (Q3) and the refresh strategy both come out of it.

Context: [`../00_initial/00_start.md`](../00_initial/00_start.md). Depends on [`02_display_spike.md`](02_display_spike.md).

## Goals

1. A long-lived connection from host to device that pushes frames, rather than the device polling.
2. A device-side loop that draws each frame with a partial update and forces a periodic full refresh.
3. Only changed regions redrawn, so appending a line of text does not repaint the screen.

## Plan

- Define the wire format. Start with whole frames; add dirty-rectangle updates once the naive version's latency is known.
- Host side: a small server that renders a test pattern (a clock, a growing block of text) and pushes frames on change.
- Device side: connect, receive, draw, reconnect on drop.
- Handle sleep and wake: reconnect and force a full redraw on wake. The trmnl-kindle roadmap admits this is where such projects break.
- Decide the transport per Q4. USB networking for development; nothing in the design should depend on which one is used.

## Out of scope

- Real content. The test pattern is the point.
- Touch input, which is phase 5.

## Done when

- Text appended on the host appears on the Kindle without any interaction, continuously.
- The connection survives a device sleep/wake cycle and redraws correctly.
- Killing the host and restarting it recovers without touching the device.

## What the implementation found

