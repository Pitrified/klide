# Klide

Read a Claude Code session on an e-ink device, on the other side of the room from the machine it
runs on.

## Where it is now

The host renders; the device is a frame sink that blits what arrives and sends back presses. That
split is D1, and it is why nothing of klide runs on the device.

- **The renderer** turns a live transcript into pages for a 1264x1680 panel with sixteen greys:
  markdown, tables, unified diffs and syntax-highlighted source. [How, and why](docs/rendering.md).
- **The simulator** is the device, headless, including the parts that are easy to forget: a bounded
  page cache, refresh modes that cost what the panel says they cost, sleeping and disconnecting.
  [What it claims and what is unverified](docs/simulator.md).
- **The wire protocol** is byte-aligned big-endian so a KOReader Lua plugin can read it with
  `string.byte`. [The format](docs/protocol.md).
- **The viewer** is the screen in a browser, and the first client of that protocol written from the
  specification rather than from the code. [Running it](viewer/README.md).
- **The device itself** is a Kobo Libra 2 rather than the Kindle below. Not yet in hand, which is
  why every timing number in the docs is marked as a claim rather than a measurement.

Everything is checked by one command, `scripts/check.sh`, and what each check catches and how it
was shown to fail is in [gates](meta/gates.md). The work is planned and recorded in
[`plans/`](plans/), which is the source of truth for what is decided and what is still open.

## The original note

Kept as written, because the plans refer back to it and because it is the thing all of the above is
answerable to. The device changed from a Kindle to a Kobo; the requirements did not.

### Idea

Use a kindle as an external display for claude.

Should support:
* streaming: high latency is ok, but the update should be continuous, no page reload or button press
* multiple conversations: jump between projects
* diff: see all the modified files, open to standard diff, from last commit is ok
* files: navigate and open

Nice to have:
* markdown rendering
* syntax highlighting
* minimal feedback: typing a full answer is out of scope, but a multiple choice or approval could be nice. opens a full can of worm about duplex connections or whatever, so maybe not.

Assumptions:
* Kindle can be fully hacked, preserving the existing OS is not a requirement. If so, being still able to read epubs is desirable, other formats not needed.
* Claude will always run on another machine.
* Kindle model is paperwhite 11th gen. Positive if more models are supported, but not a requirement.
* Updating firmware or whatever OS is in the kindle is not permitted, unless carefully vetted to prevent enshittification of the product. No amazon trash leaking into the kindle. No amazon account connected.
* If other Kindle models are more moddable, one could be purchased with limited budget.
