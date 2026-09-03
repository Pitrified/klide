---
status: planned
---

# Phase 5 - Touch navigation

## Overview

Touch events travel from the Kindle back to the host, so the display can be navigated instead of only watched.
Given D1 this is small: the device sends coordinates, the host owns all the meaning.

Scope is navigation only. By D11 klide never sends anything to the Claude session, so there is no approval gate,
no multiple choice, and no write path to build. The README's "minimal feedback" idea is deliberately dropped.

Context: [`../00_initial/00_start.md`](../00_initial/00_start.md). Depends on [`04_host_renderer.md`](04_host_renderer.md).

## Goals

1. Touch events sent from device to host over the existing connection.
2. Navigation: switch conversation, scroll, open a file, open a diff.
3. Nothing else. Navigation is the whole phase.

## Plan

- Device side: read the input node identified in phase 2 and forward events. No interpretation on the device.
- Host side: hit-test against the layout that produced the current frame, so the host always knows what was tapped.
- Render tap targets large enough for a finger and visible at e-ink contrast.
- Keep the event path one-directional in the same sense the rest of the design is: the device reports what was touched, the host decides what that means.

## Out of scope

- Anything that writes to the Claude session: approvals, choices, typed answers. Out of scope by D11.
- Gestures beyond tap, unless scrolling needs a swipe.

## Done when

- Tapping the Kindle changes what is displayed, with latency good enough to feel deliberate rather than broken.
- Every view reachable from the host is reachable from the device.

## What the implementation found

