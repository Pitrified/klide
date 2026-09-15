---
status: planned
---

# klide app - bootstrap

Spun out of [`../03_meta/00_start.md`](../03_meta/00_start.md), which holds the two-track split and MD1-MD7.
Phases in [`tracking.md`](tracking.md), derived once A1-A7 were answered.

## What this is

The app itself: a host that watches a Claude Code session, renders frames, and pushes them to a client on an
e-ink device. The requirements have not changed, and the earlier work still stands:
the research and decisions D1-D11 in [`../00_initial/00_start.md`](../00_initial/00_start.md),
and the device and UI notes in [`../02_kobo/`](../02_kobo/).

What changed is the starting point and the method.

* **Simulator first (MD5).** The Kobo is not here, and a simulator is wanted anyway. It is what makes the app
  testable without hardware, and it is the cheapest source of the observable evidence the meta track needs (M7).
* **Agent friendly.** The simulator is not primarily for a human to look at. It exists so an agent can run the app,
  capture what the screen would show, compare it against a reference and see its own mistakes.
* **Specification first (MD3).** Work starts from what the thing must do. Stack, patterns and structure are
  settled by gates and by the agent, not in conversation.
* **Stack open (MD6).** No language is committed. Rust, Go, Flutter, Python and anything else are candidates for
  the host, the renderer and the simulator, and they need not be the same one.

The device work in `02_kobo` is not cancelled, it is waiting for a device. K3 there, whether the Kobo replaces or
runs beside the Kindle path, is still open and is a separate question from this one.

## Decisions

* **AD1. The stack is chosen against written requirements, not a race.** A prototype small enough to be cheap is
  too small to be representative, and it rewards whatever is quick to start over whatever survives fifteen features.
  Phase 1 writes the requirement list, then assesses candidates against it with pros and cons (A1).
  This is a deliberate exception to the "settle forks with something that runs" line in
  [`../03_meta/00_start.md`](../03_meta/00_start.md): prototypes still settle narrow empirical questions,
  such as whether a candidate can render text fast enough, but not the choice itself.
* **AD2. The simulator is headless, and the viewer is a thin layer on top** (A3).
  An agent cannot look at a window, and the frame stream is the interface for both of them.
* **AD3. The simulator imitates what can make a frame wrong or a design bad.** Panel size and bit depth, refresh
  modes, partial update latency, touch, page-turn buttons, sleep and resume. Ghosting accumulation is deferred (A2).
* **AD4. It stands in for the client as well as the panel**, including the cache, the taller page buffer and the
  disconnect overlay, so the device client is later a port rather than a first attempt (A7).
* **AD5. One wire protocol for simulator and device** (A6). Whatever the simulator speaks, the Kobo speaks.
* **AD6. GPU only when something is measurably too slow**, and image rendering is the expected case (A4).

## Open questions

Numbered `A` for this folder.

- A1: The stack. Host, renderer and simulator, which may differ.
  Recommended: choose it by writing the same small frame-rendering slice twice, in two candidates, and keeping
  the one that survives the gates. That is a prototype, and it is cheaper than arguing about it.
  ANS: no. A slice that small is not representative, and it would reward the wrong property: a fast API might win
  on boot time today and lose badly fifteen features in. Write the requirements first, then assess candidates
  against them with pros and cons. Phase 1 does this.
- A2: What the simulator has to imitate, and what it may ignore.
  Candidates to imitate: panel size and bit depth, the refresh modes, partial update latency, ghosting accumulation,
  touch and the page-turn buttons, sleep and resume. Candidates to ignore: the panel's actual optics, battery, wifi.
  Recommended: imitate anything that can make a frame wrong or a design bad, ignore the rest.
  ANS: the candidate list as written, minus ghosting accumulation, which is overkill for a V1 and can be added
  when there is something to measure it against.
- A3: The simulator's shape.
  a. A window a person watches.
  b. A headless process that emits frames as files, plus a thin viewer.
  Recommended: b, because an agent cannot look at a window, and a viewer over a frame stream is a small extra.
  ANS: b.
- A4: Where a GPU actually helps. Rendering greyscale text at this panel size is not obviously heavy work.
  Worth naming the case before building for it: many conversations at once, syntax highlighting at speed,
  or image and diff rendering.
  ANS: image rendering is the case. Add it when something is measurably too slow, not before.
- A5: The evidence format. What a frame comparison produces, how references are stored, and what tolerance counts
  as a match on a 1 bit or 4 bit panel.
  ANS: unknown, and settled by doing rather than by deciding now. Phase 2 owns it, because the first real frame
  comparison will show what the answer has to be.
- A6: Whether the simulator speaks the same wire protocol as the real client will. If it does, the device client
  becomes a second implementation of a settled contract rather than a rewrite.
  Recommended: yes, and let that constrain the protocol early.
  ANS: yes.
- A7: Whether the simulator also stands in for the client's own logic, the cache, the taller page buffer and the
  disconnect overlay from [`../02_kobo/01_ui_ux.md`](../02_kobo/01_ui_ux.md), or only for the panel.
  ANS: yes, the client logic too. That makes the device client a port of something already working rather than
  a first implementation.
