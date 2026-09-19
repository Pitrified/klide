---
status: draft
---

# Phase 4 - Off the home network

## Overview

Make the Kobo work on a network the host is not on. Blocked on phase 1 and on T2, which asks whether
this is wanted at all: a device that never leaves the house does not need this phase and the work is
not small.

Context: [`00_start.md`](00_start.md), case B. The options and what each costs are analysed there and
not repeated here.

## Goals

1. A route from a foreign network to the host, opened by the device.
2. Frames that the network in between cannot read, per TD5.
3. A removal procedure, because whatever is installed to do this comes off a borrowed device.

## Plan

- Take the option phase 1 left standing. If `tailscaled` runs, it is that, with an ephemeral auth
  key and revocation written into the removal steps; nothing about `KLD2` changes.
- If it does not, choose between a relay with a public address and a tunnel the device can run, on
  the evidence rather than on the analysis in [`00_start.md`](00_start.md), which was written without
  the device.
- Test on a network that is genuinely not the house one, including a phone hotspot and at least one
  network with a captive portal, because the portal is the failure that does not appear at home.
- Confirm the path survives a network that permits only 80 and 443 outbound.
- Record the frame timings again. A relay adds a hop and the numbers from phase 2 stop applying.

## Out of scope

- Forwarding a port on the home router. Rejected in [`00_start.md`](00_start.md) and not reopened by
  this phase.
- Anything that leaves a service reachable when the device is not using it.

## Done when

- A frame reaches the Kobo from a network the host is not on, and a press gets back.
- The path is encrypted end to end, or the ends are, and which one is written down.
- The removal steps are written and run once.

## What the implementation found
