---
status: in progress
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

    a browser, wherever you are sitting
      |  HTTP
      v
    the viewer, a page served over a socket    either machine; simpler next to the host
      |  TCP
      v
    wherever Claude runs              the klide host, headless

Two ways across, in order of preference:

- **Over Tailscale, directly.** The viewer connects to the host's tailnet address and no SSH is
  involved at all. Verified: an unprivileged process binds the tailnet IP on a high port, so any peer
  can reach it. This is the path that needs nothing from the host and nothing from its administrator,
  and it is the same transport the Kobo will use (D8).
- **Over plain SSH, forwarded.** `ssh -L 5000:localhost:5000 <host>` where Tailscale is not available.
  Client-side flag, but the server decides whether to allow it, so it has to be checked per host.

A correction worth keeping, because it was nearly acted on. An earlier note here said
`AllowTcpForwarding` defaults to yes and was confirmed not disabled on this box. That was wrong: the
check grepped `/etc/ssh/sshd_config`, which does not exist here. This box runs no OpenSSH server at
all, only `tailscaled`, and the session that produced the claim arrived over Tailscale SSH. The lesson
is the ordinary one, that an absent file and an absent setting read the same to a careless grep.

**How to check a host you have no root on.** Reading `sshd_config` needs root, and `sshd -T` needs
root, so the check has to be behavioural. The obvious probe does not work: `-o ExitOnForwardFailure`
only covers setting the forward up, and a local forward's setup is a listening socket on the client,
so it succeeds even when the server will refuse every channel. The server is only consulted when a
connection arrives. So make one arrive, and point it at something the host is certainly running,
its own SSH port:

    ssh -f -N -L 9999:localhost:22 <host>
    nc -v localhost 9999          # an SSH- banner means forwarding works
                                  # "administratively prohibited" means it does not
    pkill -f "ssh -f -N -L 9999"  # the -f forward stays in the background until killed

`nc` appearing to hang after the banner is the probe succeeding, not failing. It has reached a real
SSH server, which sends its banner and then waits for the client's; `nc` is not an SSH client and
never sends one, so the server waits out its login grace period. The banner is the whole result.

Run against the second host on 2026-09-16: forwarding is allowed there, and the banner read
`SSH-2.0-OpenSSH_8.9p1 Ubuntu-3ubuntu0.17`, which is Ubuntu 22.04. That matters for a reason beyond
forwarding: 22.04 ships Python 3.10 and klide asks for 3.12 or newer. It is not a request for the
administrator. `uv` installs its own interpreter under the user's home directory, which is already
how this box runs klide: the system Python here is 3.14.4 and the venv uses a 3.13.14 that uv
downloaded. So AD10 holds on that host too, with nothing to ask for.

None of this matters where Tailscale reaches the host, which is the case to prefer.

What this costs on the host: nothing. An unprivileged user can bind a high TCP port, verified. No
privileged command, no install, no sshd edit, no boot step, nothing to ask an admin for. The host does
not need a graphical toolkit, which is just as well since it has no display to use one on.

What it costs on the machine with the screen: a browser, and one forwarded port. REVISED 2026-09-17
with V4. This previously read "a copied file, and uv", which was true of the tkinter version and was
the part that kept failing. Nothing needs to be installed on that machine now, and nothing needs to
be copied to it: the viewer runs next to the host and serves a page. WSLg was confirmed working on
the WSL machine (WSL 2.5.10, WSLg 1.0.66, `DISPLAY=:0.0`) and is no longer needed for this.

The host needs TCP, which it does not have yet: `host.py` speaks unix sockets only. That is not extra
work, it is the device client's transport (D8, Q4) pulled forward a phase.

## Plan

- Add TCP to the host, alongside the unix socket the gates use. Bind the tailnet address, not
  only loopback, so a peer can reach it without a forward.
- A page showing the current frame, scaled to fit an ordinary monitor, redrawing when the frame changes.
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
- A way to drive the page from a script, added 2026-09-17 after the first sitting. Not in the
  original plan and worth saying why it was added. The viewer's JavaScript had never run anywhere
  its author could see it, because this host has no browser, so the first report from a person was
  "the page buttons do not do anything" and there was no way to tell where between the click and
  the socket the event stopped. `scripts/drive.py` opens the page in Chromium or Firefox, operates
  it, and folds the browser console, the viewer's log and the host's log into one stream in time
  order. The page reports itself into that stream, so the same sequence is readable when a person
  is driving instead.

## What the first sitting found

Recorded as they came, since this is the phase that exists to collect them.

- **The page-turn buttons looked dead, and one of them was telling the truth.** Pressing page
  forward at the live tail is correctly ignored by the host, and the page showed exactly what a
  broken button shows: nothing. A press the host refuses and a press that never arrived were
  indistinguishable on screen. The status line now says `button forward: no change` when a press
  draws nothing, and the host's log says why. Reproduced in both engines before and after.
- **The other page button works in Chromium and Firefox**, driven headless through the same path a
  person clicks, as do the arrow keys, tap and swipe. So the original report is explained by the
  case above rather than by a bug in the input path, which is what three rounds of server-side
  probing had failed to establish.
- **Changing the assumed monitor density did not re-fit the panel.** It moved the calibration bar
  and left the panel at a size the new number contradicted. Fixed: the number is what true size
  means, so changing it re-fits.
- **`klide-live --serve` exits when the viewer disconnects**, so restarting the viewer kills the
  host. Reloading the browser is fine, since that is only the event stream. Not yet fixed.
- **A browser cannot measure the monitor.** Noted under V4 rather than here, because it is a
  consequence of the toolkit rather than something the sitting turned up.
- **It was slow over a tunnel: four to five seconds a press.** Frames went to the browser as one
  byte per pixel, base64-encoded, which is 2.8 MB for a full screen. Rendering, diffing and
  encoding on the host total under 0.2s and a press-to-paint round trip here is about 0.35s, so all
  of that time was the link. A panel of rendered text is mostly one colour: the same screen is
  24 KB as a PNG, which the browser also decodes itself rather than the page looping over two
  million pixels. Measured 117x smaller on one real screen, and 4.5s becomes 0.04s at 5 Mbit/s.
  The viewer writes the PNG by hand out of `zlib` and `struct`, because it ships as one file with
  no dependencies.
  Worth keeping as a lesson rather than a fix: this was designed on a machine where the viewer and
  the browser were the same host, so the link was free and the size of a frame never showed up.

## Out of scope

- The device's own logic. The viewer is a client of the host, but the cache, the page buffer and the
  disconnect overlay stay in the simulator where phase 3 put them (AD4). The viewer shows a screen and
  forwards presses; it does not become a second implementation of the client.
- Making the viewer pretty. It is an instrument.
- Becoming a gate. It cannot be one: a person is not deterministic, and that is the point of it.

## Open questions

- V5: Whether driving the browser should become a gate.
  Opened 2026-09-17. `scripts/drive.py` is deliberately an instrument, not a gate: it is started by
  hand, `scripts/check.sh` does not run it and CI does not either. That was chosen rather than
  defaulted, because a gate needs a browser downloaded before anyone can commit, and because what
  the harness checks is whether a person can use the thing, which has no reference frame.
  The gate version, if it is ever wanted, is already designed and should not be re-derived: drive a
  fixed transcript through a scripted sequence, read the canvas back with `toDataURL`, and assert
  it equals the frame klide sent, exactly, at 4-bit depth. That needs no golden file, because
  klide's own output is the reference. It is the same convergence property the streaming tests
  already hold the simulator to, and it would catch the decoding path, patch placement, and any
  JavaScript error that stops a redraw.
  What it would not catch is a design that was wrong when it was written, which is the thing this
  phase exists for and the reason AD9 is not closed by any amount of automation.
  Deliberately not decided until the harness has been used enough to know whether it is stable
  enough to block a commit.
- ~~V1: What the viewer is written in.~~ ANSWERED 2026-09-16: Python and tkinter, under WSLg,
  confirmed working on the target machine. A browser page was the alternative and pulls in more for
  no gain, now that nothing has to be served to a remote display.
  OVERTURNED 2026-09-17 by V4 below, which is where the reasoning is. "Confirmed working on the
  target machine" was the claim that did not survive; it had been confirmed on one machine, which
  then turned out not to be the one with the screen.
  It needs nothing installed. The file carries PEP 723 metadata asking for Python 3.13, so `uv run
  klide_viewer.py` fetches that interpreter and runs.
  CORRECTED 2026-09-17, twice, which is worth leaving visible. The first version said nothing needed
  installing because uv's CPython ships tkinter, "checked on this box": the check was real and the
  conclusion was not, since it held for one interpreter on one machine. On a second machine uv
  resolved a CPython linked against Tcl 8.6 with no 8.6 library files and the viewer died with
  `Can't find a usable init.tcl`. The second version then over-corrected, falling back to a system
  Python and an apt package, which gives up the property that made one file worth having. The fix is
  neither: name the version. uv's 3.13 builds carry Tcl/Tk 9.0, so asking for 3.13 makes uv fetch a
  working interpreter rather than accepting whatever the machine had.
- ~~V4: Whether the viewer should stop being a tkinter window and become a page in a browser.~~
  Opened 2026-09-17 because a working Tcl/Tk was the only part of the viewer that did not travel.
  ANSWERED the same day, by the tkinter version never once running on the machine it was for.
  The deciding evidence was a probe with no klide in it: a bare `Tk()` succeeded on that host and
  the next call, `root.update()`, aborted inside Xlib with `[xcb] Unknown sequence number`. No
  image, no socket, nothing of ours. The same probe reported Tcl 8.6.14 with `tcl_platform(threaded)`
  set, which also disposes of the previous day's diagnosis: the thread making X calls was Tcl's own
  notifier, so removing the viewer's reader thread could not have helped, and the Python pin had
  never been selecting the Tcl I claimed it did.
  Four attempts, each asserting a fix from one machine's behaviour and each failing differently on
  the machine that has the screen. Pinning a fourth Python would have been the same move again. A
  browser removes the whole class: no toolkit, no `$DISPLAY`, no Tcl, no version to guess at.
  What it costs, now that it is written: an HTTP server and an event stream in the standard library,
  the panel drawn into a canvas, and one thing genuinely lost. A browser cannot
  measure the monitor, where tkinter could ask X. True physical size is therefore a number the
  person calibrates against a ruler, with a 100 mm bar on the page to do it with, and the status
  line says "assumed" until they do. That matters more here than elsewhere, because physical
  legibility is the question this phase exists to answer.
  What is still unverified: the page's JavaScript has never been run. There is no browser and no JS
  runtime on the host, so the server, the protocol and the event stream are covered end to end by a
  test over real HTTP, and the drawing code is covered by reading it.
- ~~V3: Whether the viewer imports `klide` or reimplements the protocol in one self-contained file.~~
  ANSWERED 2026-09-16: one self-contained file, standard library and tkinter only, no `klide` import
  and no third-party dependency. It lives in `viewer/` rather than `src/klide/` because it ships to a
  different machine on a different schedule, and it is installed by copying one file.
  Three reasons, and one condition that makes them safe.
  It is the first implementation of the protocol written against the specification instead of sharing
  its code, which is the AD5 check [`../../docs/protocol.md`](../../docs/protocol.md) records as
  unverified; a protocol only one codebase can speak has not been shown to be a protocol.
  It keeps the replaceable machine's setup to one package and one file, which matters because that PC
  is being replaced.
  And it keeps `klide` free of a GUI dependency it would otherwise carry on a headless host.
  The condition: duplicating an implementation is only acceptable if divergence fails a gate. So the
  repo tests the standalone decoder against `klide`'s encoder, which makes the copy a conformance
  check rather than code waiting to drift. Two implementations held to one contract is the point, not
  the cost.
- ~~V2: Whether the viewer shows the panel's claimed refresh behaviour, or ignores it.~~
  ANSWERED 2026-09-16: both, as a toggle that works while the viewer is running rather than a flag
  chosen at startup. The two settings have different jobs and both are permanent. Honest mode makes a
  redraw take the hundreds of milliseconds the simulator claims, which is what makes a design that
  redraws too often feel as bad as it would on the device, and is why anyone would trust what they
  saw. Fast mode ignores the claim, for clicking between views when the question is layout rather
  than feel.
  Honest is the default. The viewer exists because every other check here is self-referential (AD9),
  and a viewer that showed an impossibly quick device, without saying it was doing so, would be one
  more agreeable mirror.
  Fast is the deliberate opt-out, not the starting point.
  This replaces an earlier recommendation to record which setting got used. That was premised on one
  of them turning out to be the right answer and the other being a concession; if both have standing
  jobs there is nothing to find out.
  How the delay is known: the frame message already carries the refresh mode, so the viewer maps that
  byte to a duration with a four-entry table of its own. That table is a second copy of the numbers in
  `waveform.FBINK_CLAIMS`, so the conformance test that pins the viewer's decoder to `klide`'s encoder
  covers it as well. Putting a duration on the wire was the alternative and was rejected: a real panel
  takes the time it takes, so the field would be baggage that only the simulator ever reads.

## Done when

- The viewer runs, shows a live session, and responds to the buttons and to a tap.
- A person has sat with it and the feedback is written down.
- Whatever that feedback changed is in the code, or recorded as deliberately not changed.

## What the implementation found

Built, and waiting on the part only a person can do.

- **The viewer is a klide client, not a window klide opens.** The host is headless, which was
  checked rather than assumed, so there was never a window to open there. Making the viewer connect
  over TCP turned the problem into the design the UI notes already described.
- **AD5 is checked by something now.** `viewer/klide_viewer.py` decodes real frames from a real host
  without importing klide, which is the first time the protocol has been read by code that was
  written from the specification rather than sharing it. It found nothing wrong. Lua remains
  unverified, because a second Python implementation still shares the language's habits.
- **The duplication is gated.** `tests/test_viewer.py` pins the viewer's constants, refresh table,
  input codes and decoder to klide's, so the two cannot drift without failing the `test` gate.
- **Two defects came out of running it rather than testing it.** The host tracebacked with a broken
  pipe when the viewer went away, which is what happens every time someone closes the window; and
  the failure was then swallowed silently, which turned "the viewer closed" and "the send timed out"
  into the same blank ending. Both fixed. A third was in the harness rather than the code: a
  readiness probe that connected and closed was itself consuming the single connection `serve`
  accepts.
- **The viewer has no threads, and that is a fix rather than a simplification.** The first version
  read the socket on a second thread and posted frames to the UI through a queue, which is the
  obvious shape and crashed X with `[xcb] Unknown sequence number` and an assertion failure. Nothing
  in that thread touched Tk. What touched Tk was the garbage collector: each redraw discards a
  `PhotoImage`, whose finaliser calls into Tk, and a finaliser runs on whichever thread happened to
  trigger the collection. tkinter is not thread-safe, so the socket is polled from inside tkinter's
  own loop instead. That made partial reads explicit, which they always were: a full frame is about
  a megabyte and TCP delivers it in pieces.
- **TCP is alongside the unix socket, not instead of it.** The gates keep using the unix socket,
  which needs no port and cannot collide, so nothing already green was disturbed by adding a
  transport.

## Still to do

The part this phase exists for. A person has to sit with it, and what they say has to be written
down and acted on. Until that happens the phase is not done, however much of it runs.
