# Stack

Why klide is written in what it is written in.
Decided in [app phase 1](../plans/04_klide_app/01_requirements_and_stack.md) against the requirement
list below, which AD1 asks for instead of a race between prototypes.

Scope: the host, the renderer and the simulator. The device client is a separate question,
still open as Q3, and it is Lua or C either way because that is what runs on the device.

## What has to be true

Properties the stack has to hold at fifteen features, not at the first one.
Each is written so that two people scoring a candidate against it would land in the same place.

**R1. It renders text to a greyscale bitmap at panel size.**
1264x1680 at 16 grey levels, carrying markdown, unified diffs and syntax-highlighted source.
The renderer needs control of font metrics, because the host computes the layout the device blits (D1).
This is the requirement most likely to decide the answer, because it is the one where ecosystems
differ by years of work rather than by taste.

**R2. It holds a long-lived process.**
Tail a growing JSONL transcript, keep a socket per connected client, run a timer that coalesces
updates into frames worth sending. All of it is I/O-bound at small N.

**R3. It speaks a protocol the other end can implement.**
The other end is a KOReader Lua plugin or a cross-compiled C binary (Q3), and one protocol serves
both the simulator and the device (AD5). This constrains the wire format to something writable in
Lua without dependencies. It says almost nothing about the host language, and is listed so that it
stops being offered as an argument for one.

**R4. It produces and compares frames as files.**
The simulator is headless and emits frames (AD2), and the frame comparison is the project's one
real verification gate (MD10). That needs image I/O and pixel-level diffing in the same language
the simulator is written in.

**R5. It does not need to cross-compile.**
D1 makes the device a frame sink with no klide rendering code on it. Nothing in the host, the
renderer or the simulator ever runs on ARM. This requirement is written down because it is void,
and because "we will need to cross-compile later" is the usual argument for a compiled language
here. It does not apply.

**R6. Its gates run on this box.**
A formatter, a linter, a type checker and a test runner, none of which may require node, which is
not installed and whose absence already shaped the existing gates (see [gates](../meta/gates.md)).

**R7. An agent can work in it unattended.**
The edit-run loop has to be short enough that an agent iterates rather than batches, failures have
to name a file and a line, and the language has to be common enough that an agent writes idiomatic
code without inventing an idiom. This is a real requirement here rather than a soft one: the meta
track's direction of travel is unsupervised runs (MD3), and a stack that costs an agent a compile
cycle per attempt costs it on every attempt.

**R8. It is already on this box, or cheap to put there.**
Checked 2026-09-16: python3 3.14.4 and uv are installed, with Pillow and pygments already
importable. Dart 3.12.2 is installed. rustc, cargo, go, node and npm are absent.

## The one thing measured rather than argued

R1 turns on whether a scripting language can rasterise a full page fast enough, which is a
measurement, not an opinion. Taken 2026-09-16 on this box with Pillow and pygments, rendering the
Libra 2's full 1264x1680 page of monospaced text:

- A full frame of plain text renders in tens of milliseconds, and syntax highlighting through
  pygments roughly triples that. Still tens of milliseconds.
- A dirty rectangle the size of a paragraph, which is what streaming actually sends, renders in
  single-digit milliseconds.
- Packing to 4 bits per pixel is free. Encoding to PNG is not, and `Image.quantize` costs more
  than the rendering did. The renderer picks its own grey levels, so it can draw into the palette
  directly and skip that step; this is a note for the wire format question in phase 2, not a
  finding about the language.

The comparison that matters is against the panel, which answers a partial refresh in hundreds of
milliseconds. Rendering is an order of magnitude below the thing it feeds. A faster language would
make a component faster that is not, and will not be, the bottleneck.

The probe is not kept. It measured one number and that number is recorded here.

## Candidates

| candidate | R1 render | R2 process | R4 frames | R6 gates | R7 agent loop | R8 present |
| --- | --- | --- | --- | --- | --- | --- |
| Python | Pillow and pygments, measured above | asyncio | Pillow | ruff, mypy, pytest | no compile step | yes, with both libraries |
| Rust | assembled from cosmic-text or fontdue, plus syntect and pulldown-cmark | tokio | image | cargo fmt, clippy, test | compile cycle per attempt | no |
| Go | x/image/font is a low-level primitive, no highlighting-to-bitmap path | best of the four | image | gofmt, vet, test | fast compile | no |
| Dart and Flutter | Flutter renders, but it wants an engine and a surface | fine | awkward headless | dart format, analyze, test | fine | yes |
| TypeScript | canvas needs native deps | fine | fine | needs node | fine | no, and node is absent |

Reading the table:

- **Rust** is the strongest candidate on R6 and the weakest on R1 and R7. Its usual advantages,
  a single static binary and cross-compilation, are the ones R5 voided. What is left is
  correctness enforced by the compiler, bought with an edit-compile-run loop on every unattended
  attempt and with hand-assembling a text rendering stack that Python has as two imports.
- **Go** has its strength and this project's difficulty in the wrong places. Concurrent servers are
  what it is good at, and R2 is the easy requirement. Rasterising highlighted text is the hard one,
  and it is Go's weakest ecosystem of the five.
- **Dart and Flutter** is on the box, and Flutter is a GUI toolkit. AD2 says the simulator is
  headless and the viewer is a thin layer on top, which is that arrangement inverted. Rendering
  offscreen through Flutter means driving an engine to get a file, which is more machinery than
  Pillow for the same output.
- **TypeScript** fails R8 and R6 together. Installing node on this box is a system-level change,
  and it would buy a rendering path that needs native modules anyway.
- **Python** loses on exactly one axis, the performance ceiling, which the measurement above puts
  an order of magnitude below the panel it feeds.

## Decision

Python, for the host, the renderer and the simulator. One language for all three: they share the
panel geometry, the frame representation and the comparison code, and splitting them would mean
writing the frame format twice to save nothing.

This confirms D10 rather than reopening it. D10 was taken in conversation before the requirements
existed, which is what MD3 wants to stop doing, so phase 1's job was to check whether it survives
being written down. It does, and R5 is why: the argument that would have overturned it, needing a
compiled language to reach the device, does not apply to a design where the device runs no klide
rendering code.

What the choice costs, stated plainly so it is not a surprise later:

- No compile-time guarantee. Bought back partially by mypy in strict mode as a gate, which is
  weaker than a compiler and is checked rather than assumed.
- A performance ceiling that AD6 already names: image rendering is the case where it might bind.
  The upgrade path is a native extension for the one function that is measurably too slow, not a
  rewrite, and nothing should be done about it until something is measured.

Rejected candidates keep their reasons in the table above rather than being re-derived when
someone asks again.

## Tooling

- **uv** for the environment and the lockfile. `uv.lock` is committed, so the gates run the same
  versions here, in a worktree and in CI.
- **ruff** for both formatting and linting, which is one tool and one config instead of two.
  The lint selection starts narrow, at pyflakes, pycodestyle, isort, bugbear, comprehensions and
  pyupgrade, and widens as the code earns it.
- **mypy** in strict mode. Astral's `ty` is faster and is pre-1.0; worth revisiting once it is not.
- **pytest** for tests.

All four run from `scripts/check.sh` like every other gate.
