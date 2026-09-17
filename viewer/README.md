# The viewer

A window onto the klide simulator, for the machine that has a screen.

klide runs on a host that is usually headless and may be one nobody gives us root on, so the window
cannot open there (AD10). The viewer runs where you are and connects to the host over the network,
which makes it the first real client of the wire protocol rather than a special case. The Kobo will
be the second.

## Why it is one file that imports nothing

[`klide_viewer.py`](klide_viewer.py) is self-contained: standard library and tkinter, no klide, no
Pillow, no pip. Copy it, run it.

That is worth roughly forty duplicated lines of header parsing for three reasons. It installs on a
new PC by copying one file, which matters because the PC it runs on changes. It keeps a GUI
dependency out of a package that runs headless. And it is the first implementation of the protocol
written against [the specification](../docs/protocol.md) rather than sharing the code that defines
it: a protocol only one codebase can speak has not been shown to be a protocol.

Duplication is only acceptable if divergence fails a gate, so
[`tests/test_viewer.py`](../tests/test_viewer.py) decodes this file's output against klide's encoder
and pins its constants, its refresh table and its input codes to klide's. If the two drift, the
`test` gate fails.

## Setup

One package, on the machine with the screen:

    sudo apt install python3-tk        # Debian, Ubuntu, and WSL distros

Then run it with the system Python. tkinter is in the standard library, but it needs a Tcl/Tk the
interpreter can find, and that is the one part of this file that does not travel.

The file carries [PEP 723](https://peps.python.org/pep-0723/) metadata and `uv run
klide_viewer.py` does work where uv's interpreter has a working Tk. It is not dependable, and the
difference is worth knowing rather than rediscovering. uv fetches a standalone CPython whose
bundled Tcl differs by build: one machine here resolved 3.13 with Tcl 9.0 and ran; another resolved
a build linked against Tcl 8.6 with no 8.6 library files and failed with `Can't find a usable
init.tcl`. `requires-python` is set low on purpose so that a system Python which already has a
working Tk is eligible rather than passed over.

If it cannot open a window it now says which of the two problems it is, because the remedies are
opposites: a missing Tcl library means use the system Python, and a missing display means you are
on the wrong machine.

Under WSL2 with WSLg the window opens as an ordinary Windows window. `echo $DISPLAY` printing
something is the sign that part is working.

## Running it

On the host, start a session and wait for a viewer:

    uv run klide-live --serve --port 5000

Then, on the machine with the screen:

    uv run klide_viewer.py --host <the host> --port 5000

If the host is on your tailnet, use its tailnet address and nothing else is needed. If it is only
reachable by SSH, forward the port first:

    ssh -f -N -L 5000:localhost:5000 <the host>
    uv run klide_viewer.py --host localhost --port 5000

The shebang is `#!/usr/bin/env -S uv run --script`, so `./klide_viewer.py --host ...` works too once
the file is executable, without naming a Python at all.

To check whether a host allows forwarding at all, without root on it, see the probe in
[the phase plan](../plans/04_klide_app/05_viewer.md).

## What the controls do

| control | effect |
| --- | --- |
| `◀ page` / `page ▶`, or the arrow keys | the device's two physical page-turn buttons |
| click | a tap, which returns to the live tail of the session |
| drag and release | a swipe, which pages; settled on release, never smooth |
| `1:1` to `1:4` | how much the panel is scaled down to fit your monitor |
| `true size` | as close to the panel's physical size as integer scaling allows |
| `honest refresh`, or space | wait the refresh time the simulator claims |

**Honest refresh is on by default and that is deliberate.** A redraw takes the hundreds of
milliseconds a real panel claims, which is what makes a design that redraws too often feel as bad
here as it would on the device. Turn it off to click between views quickly when the question is
layout rather than feel. Both settings have a job; neither is the concession.

The status line reports the scale, the panel's real size in millimetres, the density it is being
shown at against your monitor's, and the refresh mode of the last frame. It says all of that
because the one design fault that survived three phases of gates was text rendered at 6.2 pt, which
looked fine on a monitor and would have been unreadable on the device.

## What it is for

Every other check in klide compares its output against a reference klide produced. Those catch a
change and cannot catch a decision that was wrong when the reference was written. A person looking
at the screen is the only judgement in the system that does not come from inside it (AD9).
