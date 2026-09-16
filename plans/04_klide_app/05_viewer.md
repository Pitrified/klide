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

## Where it runs

Not on the host. Checked 2026-09-16: this box is headless, with no `DISPLAY` and no `WAYLAND_DISPLAY`,
and the next host may be one we do not administer (AD10). A window cannot be opened where klide runs.

So the viewer is a klide client that happens to run on a PC. It connects to the host the way the UI
notes already say a device does, outward over a socket, which makes it the first real network client
rather than a special case. The Kobo will do the same later over Tailscale.

The measured topology, one hop:

    WSL2 and WSLg on Windows          the viewer, a window
      |  TCP
      v
    wherever Claude runs              the klide host, headless

Two ways across, neither needing anything privileged:

- `ssh -L 5000:localhost:5000 <host>` from WSL. Client-side only. `AllowTcpForwarding` defaults to yes
  in OpenSSH and is not disabled here, so this needs no server change.
- Tailscale on the WSL machine, which is tidier and is a setup step rather than a flag.

What this costs on the host: nothing. An unprivileged user can bind a high TCP port, verified. No
privileged command, no install, no sshd edit, no boot step, nothing to ask an admin for. The host does
not even need tkinter, which is just as well since its system Python has none.

What it costs on the WSL side: `python3-tk`, one apt install. WSLg was confirmed working there
(WSL 2.5.10, WSLg 1.0.66, `DISPLAY=:0.0`), and that machine is being replaced soon, which is an argument
for keeping its setup to one package and one file.

The host needs TCP, which it does not have yet: `host.py` speaks unix sockets only. That is not extra
work, it is the device client's transport (D8, Q4) pulled forward a phase.

## Plan

- Add TCP to the host, alongside the unix socket the gates use.
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

- The device's own logic. The viewer is a client of the host, but the cache, the page buffer and the
  disconnect overlay stay in the simulator where phase 3 put them (AD4). The viewer shows a screen and
  forwards presses; it does not become a second implementation of the client.
- Making the viewer pretty. It is an instrument.
- Becoming a gate. It cannot be one: a person is not deterministic, and that is the point of it.

## Open questions

- ~~V1: What the viewer is written in.~~ ANSWERED 2026-09-16: Python and tkinter, under WSLg.
  Confirmed working on the target machine. It needs `python3-tk` there, which is one apt install on a
  machine we administer and which is being replaced soon anyway. A browser page was the alternative and
  pulls in more for no gain, now that nothing has to be served to a remote display.
- V3: Whether the viewer imports `klide` or reimplements the protocol in one self-contained file.
  Importing means no duplication, and means the WSL machine needs the repo synced and kept in step.
  A single file means copying one thing to whatever PC is current, and it would be the first
  implementation of the wire protocol written against the specification rather than sharing its code,
  which is the AD5 check [`../../docs/protocol.md`](../../docs/protocol.md) currently records as
  unverified. The cost is roughly forty duplicated lines of header parsing.
  Recommended: self-contained, for the same reason the repo vendors fonts. The thing being checked has
  to be checkable from outside. Not yet decided.
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
