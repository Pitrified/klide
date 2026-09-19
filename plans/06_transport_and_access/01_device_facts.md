---
status: draft
---

# Phase 1 - Device facts

## Overview

Find out what the Kobo can actually do, because every later choice in this folder turns on facts
about that firmware rather than on reasoning available from here. Draft, because it needs the
borrowed device.

Context: [`00_start.md`](00_start.md). Overlaps the device work in
[`../02_kobo/00_start.md`](../02_kobo/00_start.md) and should be run in the same sitting as the
questions there, since both need the device awake and reachable.

## Goals

1. Answer T1: whether `tailscaled` runs usefully on this Kobo.
2. Answer T4: what, if anything, can encrypt a socket from KOReader's Lua.
3. Establish what the device has for outbound connections at all.

## Plan

- Get a shell, by whatever route [`../02_kobo/00_start.md`](../02_kobo/00_start.md) settles.
- Record the architecture, the kernel version and whether `/dev/net/tun` exists or can be created.
- Try a static `tailscale`/`tailscaled` build for that architecture. If it starts, bring it up with
  an ephemeral auth key, confirm the host is reachable from the device and record what it costs in
  memory and battery over an hour of idle. If it does not start, record the reason rather than the
  conclusion.
- Inventory the Lua side: whether a TLS binding is present and loadable, whether `zlib` is, and what
  socket library the plugin path actually has. This overlaps D1 in
  [`../04_klide_app/06_device_client.md`](../04_klide_app/06_device_client.md), which wants the same
  answer about decompression, so ask both questions once.
- Check for an ssh client on the device, which decides whether the tunnel option in
  [`00_start.md`](00_start.md) is alive or dead.
- Write every answer back into [`00_start.md`](00_start.md) as a resolved `T`, with the date.

## Out of scope

- Installing anything permanently. Everything here is run from a copied file and removed after.
- Any klide code. This phase produces facts.

## Done when

- T1 is answered with an observation from the device, not an expectation.
- T4 is answered or recorded as impossible to answer without more than the device allows.
- The findings are in [`00_start.md`](00_start.md) with the date they were taken.

## What the implementation found
