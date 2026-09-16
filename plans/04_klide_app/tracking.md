# klide app tracking

The app itself, restarted from a simulator because the device is not here and a rendered frame is the evidence
an agent can check its own work against. Analysis and decisions in [`00_start.md`](00_start.md);
the requirements it inherits are in [`../00_initial/00_start.md`](../00_initial/00_start.md) and
[`../02_kobo/`](../02_kobo/). How the work is run is the meta track, [`../03_meta/tracking.md`](../03_meta/tracking.md).

## Key decisions

- The stack is chosen against a written requirement list, not by racing prototypes (AD1).
- The simulator is headless and emits frames; the viewer is a thin layer on top (AD2).
- It imitates what can make a frame wrong or a design bad, and stands in for the client as well as the panel (AD3, AD4).
- One wire protocol for the simulator and the real device (AD5).
- The frame is the evidence, which is where this track meets the meta one (MD10).
- Python for the host, the renderer and the simulator, confirming D10 against written requirements (AD7).
- The evidence is a PNG, references are committed, and the match tolerance is zero (A5, phase 2).
- The refresh timings are FBInk's documented figures, not measurements, and calibration waits for the device (phase 3).
- The taller page buffer and the cache are one structure, a bounded cache of pages of any height (K9, phase 3).
- Text is sized in points against the panel's real 300 ppi, never in pixels (AD8).
- Colour is not translated to grey: diffs lead with their own markers, highlighting groups by prominence (phase 4).
- Fonts are vendored so references stay reproducible without a system font (phase 4).
- Every gate is self-referential, so a person looking at the screen is the one outside signal; phase 5 builds the viewer that provides it.

## Phases

| #  | Phase                      | Plan                                                          | Status  |
| -- | -------------------------- | ------------------------------------------------------------- | ------- |
| 1  | Requirements and stack     | [`01_requirements_and_stack.md`](01_requirements_and_stack.md) | done    |
| 2  | Walking skeleton           | [`02_walking_skeleton.md`](02_walking_skeleton.md)             | done    |
| 3  | Simulator fidelity         | [`03_simulator_fidelity.md`](03_simulator_fidelity.md)         | done    |
| 4  | Host renderer and views    | [`04_host_renderer.md`](04_host_renderer.md)                   | done    |
| 5  | Viewer and human feedback  | [`05_viewer.md`](05_viewer.md)                                 | planned |
| 6  | Device client              | [`06_device_client.md`](06_device_client.md)                   | draft   |

Status values: draft / planned / in progress / done / superseded / discarded.

## Log

Append-only. Newest at the bottom.

- 2026-09-16 : folded in A1-A7 and derived the five phases. The stack is decided against written requirements rather than by a race, the simulator is headless and covers the client as well as the panel, ghosting is deferred, GPU waits for a measurement, and the evidence format is left to the first real frame comparison in phase 2
- 2026-09-16 : phase 1 done. Wrote the requirement list R1-R8 first, then scored five candidates against it in [`../../docs/stack.md`](../../docs/stack.md). Python, one language for host, renderer and simulator (AD7). The phase's real job was checking whether D10 survives being written down rather than asserted, and it does. R5 is the reason it is not Rust: D1 leaves no klide code on the device, so nothing here cross-compiles, which voids the usual argument for a compiled language. Measured the one empirical requirement, R1: a full 1264x1680 page of highlighted text renders in tens of milliseconds against a panel that answers a partial refresh in hundreds. Filled four of the five gate slots, ruff for format and lint, mypy strict, pytest, each demonstrated failing and each in `scripts/check.sh`. The lint gate found a real unused import in `scripts/gates/plan_status.py` on its first run. The frames gate stays open because A5 gives the evidence format to phase 2
- 2026-09-16 : phase 2 done. `uv run klide-skeleton` renders a page at panel size, serves it over a unix socket, receives it in the simulator, writes it out and compares it against a committed reference; the protocol is in [`../../docs/protocol.md`](../../docs/protocol.md). A5 answered: an 8-bit greyscale PNG that is lossless with respect to the 4-bit levels, references in the repo because a generated one agrees with whatever the code does, and a tolerance of zero, defensible because the host is deterministic once the font comes from pinned Pillow rather than the system. The comparison is of the received frame rather than the rendered one, so a protocol bug fails the gate instead of slipping past it. The protocol's shape was decided by the Lua client that does not exist yet: byte-aligned big-endian fields and rows padded to a byte, because KOReader's Lua has no `string.unpack`. The frames gate is filled and catches a one-pixel margin shift, which closes the last slot the meta track left open
- 2026-09-16 : phase 3 done. `uv run klide-session` drives nine steps and writes the screen after each; the client logic (bounded page cache, local panning, sleep and resume, disconnect banner) is in `src/klide/device.py`, and what the simulator claims is in [`../../docs/simulator.md`](../../docs/simulator.md). The phase's real risk was inventing latency numbers for a device that is not here. Research established that E Ink publishes no per-mode timings and that they vary with panel, controller and temperature, so FBInk's documented approximations are used and every mode carries a source string saying it was not measured on a Libra 2. Breaking the client deliberately found a gate that passed a change it should have caught: quadrupling the flash rate moves no pixels because ghosting is not modelled, so a refresh ledger is now compared alongside the images. K9 answered by building it, the taller page buffer and the cache are the same structure. The protocol moved to version 2 to carry a second message type going the other way. Dirty rectangles are supported and tested but nothing sends one yet, which is phase 4's case
- 2026-09-16 : fixed a legibility fault found by reading the frames as a physical object rather than as an image. The renderer used a 26 pixel font, which on a 300 ppi panel is 6.2 pt, about half the smallest size anyone sets a paperback in, and the point of the device is not straining to read it. Sizes are now typographic points converted through the new `Panel.ppi` (AD8): 11 pt body, 23 lines and about 51 characters a screen, 2.03 mm x-height. Two tests hold the floor, one on point size and one on lines per screen, because the mistake came from judging a 300 ppi frame on a desktop monitor and nothing structural stopped it. Raising the size then pushed every hand-wrapped line past the right edge, which the renderer clips silently, so a third test checks the canned pages fit. Both frame gates caught the change and the references were regenerated. Parked A8, how a person drives the simulator, since the viewer does not exist and the drag question is the part worth deciding deliberately
- 2026-09-16 : answered the drag half of A8, provisionally: settle on release, short one-directional drags, which is Kindle-like behaviour a reader already expects. Nothing to build, because the wire carries a discrete direction rather than a continuous delta and panning happens once per gesture; the decision records that this stays deliberate. The rest of A8, whether a viewer gets built at all and which phase owns it, is still open
- 2026-09-16 : phase 4 done. `uv run klide-views` gates all six views from fixtures; `uv run klide-live` watches a real session and streams it to the simulator, which is the first thing here that reads something nobody wrote for it. Rendering decisions in [`../../docs/rendering.md`](../../docs/rendering.md). The transcript format was read from a real file before anything was built on it, which is how the thinking finding surfaced: all 219 thinking blocks on this box carry an empty field and an opaque signature, so klide shows an activity marker because that is all the format supports. Fonts are vendored, since Pillow ships neither a monospace nor a bold. Colour is not translated to grey; diffs lead with the markers the format already has. Streaming rests on one property and that property is a test: dirty rectangles must converge on the same screen as sending the page. Running it against a real session found two defects the synthetic fixture could not, an empty heading for every tool-result turn and a heredoc rendering as a dozen lines, which is the argument for that command existing
- 2026-09-16 : added phase 5, the viewer, and pushed the device client to 6. The reason is not convenience: every gate in this repo compares klide's output against a reference klide produced, so they catch a change and cannot catch a design that was wrong when the reference was written. The agent sets the expectation and then meets it. The 6.2 pt text is the proof, since it survived three phases with every gate passing and was caught by a person asking whether the screen would be readable. A8 is now fully answered: the viewer gets built, it owns its own phase, and it comes before the device client because it needs no hardware and the feedback is worth having before anything is ported
