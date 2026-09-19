---
status: draft
---

# Phase 2 - Same network

## Overview

Get a client on the device talking to the host over the house LAN, accepting for the length of the
spike that anything else on that LAN could do the same. The point is to answer whether a Lua client
can speak `KLD2` at all, which is a question about the protocol and not about access.

Context: [`00_start.md`](00_start.md), case A.

## Goals

1. A frame from the host drawn on the Kobo panel, over Wi-Fi.
2. A button press on the Kobo reaching the host.
3. Knowing what a full frame costs over Wi-Fi to this device, which is the number D1 in
   [`../04_klide_app/06_device_client.md`](../04_klide_app/06_device_client.md) is waiting for.

## Plan

- Start the host with `--bind` on the LAN address, deliberately, and note the time.
- Point the client at it and work until a frame arrives.
- Measure a full frame and a dirty rectangle, end to end, several times.
- Stop the host and return to the loopback default the same sitting. Per TD3 the wide bind lasts as
  long as the spike and not longer.

## Out of scope

- Authentication. This phase runs without it on purpose and is the reason phases 3 and 4 exist.
- Any network the host is not on. That is phase 4.

## Done when

- The device renders a frame from the host over the LAN and a press gets back.
- The frame timings are recorded here with the date.
- The host is back on loopback and the spike window is closed.

## What the implementation found
