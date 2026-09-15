---
status: draft
---

# klide app - bootstrap

Draft. Spun out of [`../03_meta/00_start.md`](../03_meta/00_start.md), which holds the two-track split and MD1-MD7.
No phases yet; this is the note that has to be answered before phases are worth writing.

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

## Open questions

Numbered `A` for this folder.

- A1: The stack. Host, renderer and simulator, which may differ.
  Recommended: choose it by writing the same small frame-rendering slice twice, in two candidates, and keeping
  the one that survives the gates. That is a prototype, and it is cheaper than arguing about it.
  NEW_ANS:
- A2: What the simulator has to imitate, and what it may ignore.
  Candidates to imitate: panel size and bit depth, the refresh modes, partial update latency, ghosting accumulation,
  touch and the page-turn buttons, sleep and resume. Candidates to ignore: the panel's actual optics, battery, wifi.
  Recommended: imitate anything that can make a frame wrong or a design bad, ignore the rest.
  NEW_ANS:
- A3: The simulator's shape.
  a. A window a person watches.
  b. A headless process that emits frames as files, plus a thin viewer.
  Recommended: b, because an agent cannot look at a window, and a viewer over a frame stream is a small extra.
  NEW_ANS:
- A4: Where a GPU actually helps. Rendering greyscale text at this panel size is not obviously heavy work.
  Worth naming the case before building for it: many conversations at once, syntax highlighting at speed,
  or image and diff rendering.
  NEW_ANS:
- A5: The evidence format. What a frame comparison produces, how references are stored, and what tolerance counts
  as a match on a 1 bit or 4 bit panel.
  NEW_ANS:
- A6: Whether the simulator speaks the same wire protocol as the real client will. If it does, the device client
  becomes a second implementation of a settled contract rather than a rewrite.
  Recommended: yes, and let that constrain the protocol early.
  NEW_ANS:
- A7: Whether the simulator also stands in for the client's own logic, the cache, the taller page buffer and the
  disconnect overlay from [`../02_kobo/01_ui_ux.md`](../02_kobo/01_ui_ux.md), or only for the panel.
  NEW_ANS:
