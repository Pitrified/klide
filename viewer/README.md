# The viewer

The klide simulator's screen, in a browser.

klide runs on a host that is usually headless and may be one nobody gives us root on (AD10). The
viewer is a klide client that connects over the network and serves what it receives as a page,
which makes it the first real client of the wire protocol rather than a special case. The Kobo will
be the second.

It draws in a browser because a browser is the only graphical thing that is already on every
machine with a screen. It was a tkinter window first, and the history is worth a line: tkinter is
in the standard library, but a Tcl/Tk the interpreter can find is not, and that is a property of
the interpreter build and the machine rather than of this code. Three Python pins each failed
somewhere different, the last aborting inside Xlib on the first draw. V4 in
[the phase plan](../plans/04_klide_app/05_viewer.md) has the detail.

## Why it is one file that imports nothing

[`klide_viewer.py`](klide_viewer.py) is self-contained: standard library only, no klide, no Pillow,
no pip, no toolkit. Copy it, run it.

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

[uv](https://docs.astral.sh/uv/) on the machine that runs the viewer, and a browser on the machine
you are sitting at. The file carries [PEP 723](https://peps.python.org/pep-0723/) inline script
metadata, so `uv run` reads the block at the top and builds the environment.

`requires-python` is an ordinary floor. It used to be a narrow pinned range, which is what the
tkinter version needed and never reliably got.

## Running it

The viewer can run on either machine, because it talks TCP on one side and HTTP on the other. Next
to the host is the simpler of the two: nothing then has to be copied anywhere.

On the host:

    uv run klide-live --serve --port 5000          # one terminal
    uv run viewer/klide_viewer.py --port 5000      # another; prints the URL

From the machine with the screen, forward the viewer's HTTP port and open it:

    ssh -f -N -L 8000:localhost:8000 <the host>
    # then browse to http://localhost:8000/

If the host is on your tailnet, `--bind` its tailnet address and browse to it directly with no SSH
at all. Binding anything other than `127.0.0.1` puts the page on the network, and there is no
authentication on it, so the tailnet is the only place that is reasonable.

To run the viewer on the machine with the screen instead, copy the one file there and point it at
the host, forwarding klide's port rather than the viewer's:

    uv run klide_viewer.py --host <the host> --port 5000

The shebang is `#!/usr/bin/env -S uv run --script`, so `./klide_viewer.py` works too once the file
is executable, without naming a Python at all.

To check whether a host allows forwarding at all, without root on it, see the probe in
[the phase plan](../plans/04_klide_app/05_viewer.md).

## Driving it from a script

[`../scripts/drive.py`](../scripts/drive.py) opens the page in a real browser and operates it, so
the page can be used rather than described. It is how the JavaScript gets exercised at all on a
headless host.

One-time setup, no elevation needed:

    uv run playwright install chromium firefox

Then:

    uv run python scripts/drive.py --do "shot before" --do "click #back" --do "wait 2" --do "shot after"

Actions are `click <selector>`, `key <name>`, `tap <x> <y>` and `drag <x0> <y0> <x1> <y1>` in panel
coordinates, `wait <seconds>`, `shot <name>`, `text <selector>` and `eval <expression>`. It starts
its own host and viewer on ports of its own, or drives one already running with `--url`. `--browser
firefox` drives the other engine, and `--headed` shows the window.

Everything lands in one stream in time order, which is the point: the browser console, the viewer's
log and the host's log are otherwise three places.

    browser  klide: sending button back
    viewer:  http "POST /input HTTP/1.1" 200 -
    host:    serve: button page_back -> redraw, now 6 turns back of 1401
    viewer:  frame 1264x773 at (0,58) gl16 to 1 watching
    browser  klide: painted 1264x773 at (0,58) gl16, 0 waiting

Screenshots go to `build/browser/`, both the whole page and the panel alone. Nothing is compared
against a reference. This is not a gate and `scripts/check.sh` does not run it: what it checks is
whether a person can use the thing, and that judgement is a person's.

## What goes over the wire

Each patch reaches the browser as a PNG: where to put it, how it refreshes, and the image. A panel
of rendered text is mostly one colour, so a full screen is about 24 KB rather than the 2.8 MB it
was when the pixels went over raw, and the browser decodes it rather than the page looping over two
million of them.

That matters because the browser may be on the other end of an SSH tunnel, which is the ordinary
case here. It was four to five seconds a press before, and the host was never the reason: rendering,
diffing and encoding total under 0.2 seconds.

The viewer writes the PNG itself from `zlib` and `struct`, since it carries no dependencies. A test
reads the result with Pillow, which is klide's and not the viewer's, so the bytes are checked
against something that did not write them.

## What the page reports

The page says what it is doing, to the browser console prefixed `klide:` and to the viewer's own
log as `browser: ...`. So the whole sequence is readable without opening devtools, including while
someone else is driving the page.

Uncaught errors and rejected promises are reported the same way. That matters more than it sounds:
a JavaScript error early in the page leaves every handler after it unattached, and the result looks
like a page whose buttons merely do nothing.

The status line also reports the last input and what became of it, which distinguishes the three
cases that otherwise look identical on screen: `sent button back`, `input failed` when the request
never left the browser, and `button forward: no change` when the host received it and correctly did
nothing.

## What the controls do

| control | effect |
| --- | --- |
| `◀ page` / `page ▶`, or the arrow keys | the device's two physical page-turn buttons |
| click | a tap, which returns to the live tail of the session |
| drag and release | a swipe, which pages; settled on release, never smooth |
| `1:1` to `1:4` | how much the panel is scaled down to fit your monitor |
| `true size` | as close to the panel's physical size as integer scaling allows |
| `monitor ppi` | what `true size` assumes about your screen; see below |
| `honest refresh`, or space | wait the refresh time the simulator claims |

**Honest refresh is on by default and that is deliberate.** A redraw takes the hundreds of
milliseconds a real panel claims, which is what makes a design that redraws too often feel as bad
here as it would on the device. Turn it off to click between views quickly when the question is
layout rather than feel. Both settings have a job; neither is the concession.

The status line reports the scale, the panel's real size in millimetres, the density it is being
shown at against the monitor density it is assuming, and the refresh mode of the last frame. It
says all of that because the one design fault that survived three phases of gates was text rendered
at 6.2 pt, which looked fine on a monitor and would have been unreadable on the device.

**A browser cannot measure your monitor**, which is the one thing the tkinter version could do and
this cannot. CSS pixels are defined against a nominal 96 dpi, not against the glass. So `true size`
works from the number in the `monitor ppi` box, and the page draws a bar that should be 100 mm
wide at that number: hold a ruler to it and correct the number until it is. The setting is kept in
the browser. Until it is calibrated the physical size is a guess, and the status line says
"assumed" rather than pretending otherwise.

## What it is for

Every other check in klide compares its output against a reference klide produced. Those catch a
change and cannot catch a decision that was wrong when the reference was written. A person looking
at the screen is the only judgement in the system that does not come from inside it (AD9).
