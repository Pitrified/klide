# What the simulator claims

The simulator stands in for a Kobo Libra 2 that is not here. This page is the list of things it
asserts about that device, so that when the device arrives each one can be checked instead of
rediscovered. Phase 3 built it; phase 5 is where these get compared against hardware.

Read it as a set of claims. Some are copied from documentation, some are policy the client chose,
and one class is deliberately absent. They are separated below because the three fail differently.

## Copied from documentation, unverified on this device

The refresh durations. FBInk's `fbink.h` documents an approximate duration per waveform mode in
the comments on `WFM_MODE_INDEX_E`, and those are the numbers in `src/klide/waveform.py`.

| mode | claimed | grey levels | flashes |
| --- | --- | --- | --- |
| a2 | 120 ms | 2 | no |
| du | 260 ms | 2 | no |
| gl16 | 450 ms | 16 | no |
| gc16 | 450 ms | 16 | yes |

FBInk is the tool this project would drive on the device, which makes it the best published source
available. It is not a measurement of this panel, and no vendor number exists to check it against:
E Ink does not publish per-mode timings, and the figures vary with the panel, the controller and
the temperature.

Two things follow, and both matter for how the numbers should be read.

The ordering is the trustworthy part. A2 is faster than DU, which is faster than GC16, and a design
that redraws too often costs visibly more in the simulator's accounting for the right reason.

The absolute values are not trustworthy. Carta 1200 claims a response time improvement over Carta
1000, so these are more likely to be slow than fast for this panel. By how much is unknown. When
the device is in hand, measuring each mode and replacing `FBINK_CLAIMS` is the whole of the change,
because everything reads durations through `Mode`.

## Physical size, which is not negotiable

7 inch diagonal, 1264x1680, 300 ppi, which is 107 x 142 mm of glass. Recorded because it is the
fact most easily lost: every frame in this repo gets looked at on a desktop monitor at a fraction
of its real density, and text that reads comfortably there is unreadable on the device.

Body text is 11 pt, giving 23 lines and about 51 characters a screen, with an x-height of 2.03 mm.
The renderer works in points and converts through `Panel.ppi` (AD8). A test holds the floor at 9 pt
and another holds the line count in a comfortable range, because this was got wrong once: the first
renderer used a 26 pixel font, which is 6.2 pt.

## Policy the client chose

These are not properties of the panel. They are decisions klide made, and they are in the
simulator so that they can be argued with.

**A full refresh every eight partial ones.** Partial modes accumulate ghosting and a GC16 clears
it. How many partials a Libra 2 tolerates before one is needed is exactly the measurement that A2
defers, so the number is configuration (`Device.flash_every`) rather than a constant.

**A cache of four pages, thrown away on exit.** The UI notes settle the size as a handful, on the
grounds that 512 MB of RAM against a frame of about a megabyte makes the limit a design choice
rather than a hardware one.

**Panning is answered on the device and view changes are not.** A page arrives taller than the
screen and the device moves inside it locally; anything that changes which view is displayed costs
a round trip. In the scripted session that is six local answers against two from the host.

**Panning clamps at both ends.** Running off the end of a page is a view change, and the host owns
those.

**A resume flashes.** The panel has been off, and the first draw after that is the one place a full
refresh is clearly worth its cost.

**On losing the host, keep the page and draw a banner.** K6's answer: a stale frame with a visible
warning beats a blank screen. The client draws the banner itself, because the host is by definition
gone.

## Deliberately absent

**Ghosting accumulation** (A2). The device counts partial refreshes since the last flash, which is
what a client needs in order to decide when to flash, but the image is not degraded. Modelling
degradation without something to calibrate it against would produce a number that looks like
evidence and is not.

**Optics, battery and wifi**, which are out of scope for the simulator and collected by phase 5
instead.

**Real time.** Nothing sleeps. `elapsed_ms` accumulates what the modes claim, so the cost of a
design shows up as a number rather than as a slow test.

**A viewer.** AD2 puts a thin viewer on top of the frame stream and it has not been built. The
simulator is driven by a script, which is what an agent needs and what the gates use. A viewer is
for a person, and the open question about what it would do with drag is A8 in the app track: a
mouse drag is continuous and the panel is not, so the interesting decision is whether the viewer
should imitate that badness faithfully rather than smooth it over.

## How the claims are checked

`uv run klide-session` drives a nine-step scripted session and writes the screen after every step.
Each screen is compared against a committed reference, and the refresh ledger is compared as a
separate reference file.

The ledger exists because the images cannot carry the cost. Changing the refresh policy changes
which waveform each update uses and how often the panel flashes, and in a simulator that does not
model ghosting none of that moves a pixel. Without the ledger the gate would pass a client that had
doubled its refresh budget, which was found by trying it.

## What a device would falsify

Worth writing down now, while the expectations are fresh, because this is the list phase 5 works
through:

- the four durations, all of them
- whether eight partials before a flash is too many, or needlessly few
- whether a local pan actually feels immediate once a real panel refresh is in the loop
- whether a resume is fast enough to be worth not holding the socket across a suspend
- whether a page three screens tall is the right amount to send at once
