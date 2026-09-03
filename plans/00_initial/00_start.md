# Klide - bootstrap

## The idea

Use a Kindle as an external display for Claude. Original framing in [`../../README.md`](../../README.md):
streaming with no page reload, multiple conversations, diffs, file navigation,
markdown and syntax highlighting as nice-to-haves,
and minimal feedback (approve, multiple choice) as a maybe.
Claude always runs on another machine. No Amazon account, no firmware enshittification.

## Research

Web research only, September 2026, except the device state below. Nothing here has been tested on hardware.
Firmware and exploit facts are the most perishable part of this page.

### Device state, verified

Kindle Paperwhite 11th gen (PW5), connected over USB and inspected on 2026-09-03:

* `system/version.txt` reads `Kindle 5.14.1.1 (378310 001)`, the firmware the PW5 shipped with. The device has never taken an update.
* No `.bin`, `.partial` or `update*` files anywhere on the USB volume, so no update is staged.
* Documents are expendable and will be backed up before anything destructive.

**Keep the device off wifi and in airplane mode.**
5.14.1.1 is old enough to be jailbreakable and new enough that Amazon will push it straight to 5.19.x on first contact with a network.
That update is one-way: anti-rollback blocks downgrading below 5.18.x, and 5.19.5 has no public jailbreak.
The single largest risk to this project is the device reaching wifi once before it is locked down.

### Root access, custom OS

There is no custom OS for a modern Kindle.
Jailbreaking gets root on Amazon's Linux; it does not replace it.
postmarketOS has ports for some Kobo models, none for any recent Kindle, and the blocker is usually the proprietary e-ink panel drivers.

The PW5 is hostile to going lower: secure boot is enforced on production units, U-Boot is locked,
the debug UART pads were removed from the PCB (reachable only via USB-C debug accessory mode with external resistors, at 1.8V),
and an eMMC interposer has been built but never booted successfully.

This contradicts the README assumption that "kindle can be fully hacked, preserving the existing OS is not a requirement".
The realistic shape is the inverse: Amazon's OS stays, root sits on top of it, and KOReader takes over the reading UI.
Epub support comes for free rather than being something to protect.

### Jailbreak

At 5.14.1.1 the applicable exploit is [LanguageBreak](https://github.com/notmarek/LanguageBreak), covering everything at or below 5.16.2.1.1.
It fits the project's constraints better than any newer one:

* **No Amazon account required.** It works on unregistered devices. The store-based exploits (WinterBreak, SpringBreak) need a registered Kindle with the Kindle Store reachable, which the README rules out.
* **No wifi required.** The documented procedure runs with airplane mode on throughout.
* It needs a factory reset into demo mode, and the device must have no password lock. The reset wipes documents, already acceptable here.
* It installs its own hotfix rather than the standard one.

One conflict the sources do not settle: the kindlemodding gitbook page is titled "LanguageBreak (5.14.3-5.16.2.1.1)",
while the upstream repo says "any kindle running FW 5.16.2.1.1 or lower" and notes the exploit "works best around version 5.16.2".
5.14.1.1 is below 5.14.3. Whether that lower bound is real or just the range someone tested is unknown.
Handling is in [`01_root_access.md`](01_root_access.md).

Sideloading a controlled update is the fallback: copy the `.bin` to the USB root and use Settings > Update Your Kindle.
That works offline, so airplane mode stays on. Firmware archive: `files.cocaine.trade/firmware/kindle/`.
**Never past 5.16.2.1.1** - 5.16.3 introduced breaking changes and later versions patch LanguageBreak.

Once jailbroken, block OTA updates with `renametobin` before wifi is ever enabled.
That must be reverted before any deliberate update or factory reset, or the device locks.
The jailbreak survives reboots; the hotfix and sometimes KUAL need reinstalling after a firmware update.

Wider exploit map, since versions shift and sources disagree on the edges:

| exploit | firmware | registration needed |
| --- | --- | --- |
| LanguageBreak | <= 5.16.2.1.1 | no |
| Sanctuary (rel. 2026-06-30) | 5.16.4 - 5.18.3 | no, works on blacklisted devices |
| WinterBreak / Mesquito | below 5.18.1 | yes |
| AdBreak | 5.18.1 - 5.18.6 (sources vary) | yes |
| SpringBreak (rel. 2026-06-22) | KT5 / PW5(SE) 5.19.2, 5.19.2.0.1 | yes |

Standard post-jailbreak stack: hotfix, KUAL (launcher), MRPI (package installer),
USBNetwork or the KOReader SSH plugin (dropbear, over USB or wifi), kterm (terminal), KOReader.
Custom native binaries are built with koxtoolchain, target `arm-kindlepw2-linux-gnueabi` (PW2 and later, hard-float on 5.16+).

### Three ways to get pixels on the screen

**a. Framebuffer push.** `eips` is built in: `eips -g file.png` draws an image with a partial update, `-f` forces a full one.
FBInk (NiLuJe) is the better tool for anything beyond that: CLI and C library, TTF rendering, image drawing,
per-region refresh with explicit waveform choice, already supporting Kindle, Kobo, reMarkable and PocketBook.
KOReader itself uses FBInk for input handling on Kindle.
This is what every dashboard project does, and it matches klide's requirements most directly:
the host renders a bitmap, the Kindle draws it, so markdown, diffs, highlighting and layout are all host-side problems.

**b. KOReader plugin (Lua).** KOReader is already a full framebuffer application with input, networking (luasocket),
a plugin API, and existing plugins for SSH, a terminal emulator, and keep-alive.
The `assistant.koplugin` family already streams LLM responses from Anthropic and others on e-ink,
so streaming text into a KOReader UI is demonstrated rather than speculative.
Touch input comes for free, which makes the feedback nice-to-have cheap.
Cost: writing Lua against KOReader internals, and coupling to KOReader's release cycle.

**c. The experimental browser.** Rejected. It fails the primary requirement.
WebKit 531-534 (Safari 4/5 era). No WebSockets. HTML5 support described as almost absent,
so long-polling is the only push mechanism anyone has got working.
One project reports `http://localhost` unreachable from the browser and had to patch the `browserd` daemon to allow `file://`.
The device sleeps after roughly ten minutes unless the screensaver is disabled from a root shell, there is no kiosk mode,
and JS execution is slow enough that jQuery parse time is comparable to an iPhone 4.

### Networking

Tailscale is already in the stack (D8), so the host and the Kindle do not need to share a LAN,
and Tailscale is known to run on jailbroken Kindles in proxy and tun modes.
USB networking stays the development path because it needs no configuration on a freshly rooted device.
Two device-side details matter regardless of transport: the USBNetwork wifi configuration has historically been reported
as passwordless, so key-only auth needs checking explicitly; and keeping the device awake means fighting `powerd` via lipc,
which KOReader's KeepAlive plugin already does.

### Other vendors

Buying a different device is in scope. The tradeoff is how much work to get code running against screen, price and vendor.

* **Kobo.** No exploit needed. Linux with a Qt frontend, NickelMenu adds launcher entries by dropping a file in `.kobo`, KOReader runs natively, SSH is reachable, FBInk supports it, and postmarketOS ports exist for some models. Everything in the display plan carries over unchanged, minus the jailbreak and minus the standing fear of an OTA update.
* **Boox.** Android, with ADB and normal sideloading on models that do not block developer mode. klide becomes an Android app: a socket, a text view, touch input, vendor APIs for refresh mode. Least device-level work. Larger, more expensive, and the vendor's privacy record is worth checking before it becomes the always-on display for a coding session.
* **reMarkable.** Root shell over SSH without any exploit, and an existing project turns a Paper Pro Move into a dockable e-ink terminal running persistent Claude Code sessions over tmux and Tailscale. Worth reading regardless of hardware choice. Expensive, and the writing hardware is not needed here.

### Prior art

Displays and dashboards:

* [adtac gist, Kindle as an e-ink monitor](https://gist.github.com/adtac/eb639d3c707b55a28f0ee9a420aa7e0c) - screencapture, grayscale JPEG, netcat over USB net, `eips -g -w gc16`, reported around 3.5 fps on a PW3. Closest existing thing to klide.
* [kindletron](https://github.com/forestpurnell/kindletron) - VNC screenshot served over HTTP, Kindle polls. Default 60s refresh; the polling model is the part to avoid.
* [trmnl-kindle](https://github.com/usetrmnl/trmnl-kindle) - maintained dashboard client, 6th gen and later. Useful for install packaging and sleep/redraw handling, which its roadmap admits is unfinished.
* [kiiin](https://github.com/thekakkun/kiiin), [kindledashboard](https://github.com/nfunky/kindledashboard), [kindle-voyage-weather](https://github.com/cdmckay/kindle-voyage-weather) - the weather-dashboard genre; all host-renders-image, Kindle-draws-image.

Tooling:

* [FBInk](https://github.com/NiLuJe/FBInk) - the display primitive.
* [koxtoolchain](https://github.com/koreader/koxtoolchain) - cross-compiler for native binaries.
* [KOReader](https://github.com/koreader/koreader), [terminal emulator](https://github.com/koreader/koreader/wiki/Terminal-emulator), [keep alive](https://github.com/koreader/koreader/wiki/Keep-alive) wiki pages.
* [KindleTool](https://github.com/NiLuJe/KindleTool) - firmware package extraction.
* [kindlemodding.org](https://kindlemodding.org/jailbreaking/) - the jailbreak wizard and FAQ; run the wizard against the real device before acting on the table above.
* [Kindle Mod Shelf](https://kindlemodshelf.me/) - curated index of jailbreaks, plugins, games.

AI on e-ink:

* [assistant.koplugin](https://github.com/omer-faruq/assistant.koplugin) - KOReader plugin, multiple providers including Anthropic, streaming mode. The most relevant precedent for rendering streamed model output on e-ink.
* [AskGPT](https://github.com/drewbaumann/AskGPT) - the ancestor of the above.
* [JailbreakedKindleGPT](https://github.com/ronibandini/JailbreakedKindleGPT) - shell script driven from kterm. Minimal, but proves the plumbing.
* The reMarkable Paper Pro Move terminal project noted above. Not located precisely yet; worth finding.

Unrelated but instructive about what the hardware tolerates:
DOOM, Game Boy emulation, VNC clients, Bluetooth audio players, interactive fiction interpreters,
and a (deprecated) [Debian chroot](https://github.com/simonachmueller/DebianKindle).

* [TAKT PW5 hardware notes](https://kb.taktpraha.cz/projects/kindlepw5) - UART over USB-C, secure boot, eMMC interposer.

## Decisions

* **D1. The Kindle is a dumb frame sink and input source. All rendering happens on the host.**
  Markdown, diff formatting, syntax highlighting and layout are ordinary host-side problems and awful on-device ones.
  Keeps device code small, avoids cross-compiling a rendering stack for ARM,
  and reduces supporting a second device to screen dimensions and a draw call.
  Rejected: rendering on the device, which multiplies the cross-compile burden and pins the project to one device.

* **D2. The experimental browser is not a candidate.**
  No WebSockets, effectively no push, a ten-minute sleep, no kiosk mode.
  It cannot satisfy "streaming, continuous, no page reload", which is the primary requirement.

* **D3. Use the PW5 already in hand.**
  It is on 5.14.1.1, which is jailbreakable without an Amazon account, so it is the cheapest experiment available.
  Rejected for now: Kobo (needs no exploit and is the fallback if the jailbreak fails, see Q6),
  Boox (least work but an Android app is a different project, and the vendor is unvetted),
  reMarkable (expensive, and stylus hardware is irrelevant here).

* **D4. LanguageBreak is the exploit.**
  The only one covering the 5.14.x band that also needs neither registration nor wifi.
  Rejected: Sanctuary (band starts at 5.16.4, would require updating first for no gain),
  WinterBreak and SpringBreak (both need a registered device and store access).

* **D5. Root access comes first, before any klide code.**
  Not because it is the interesting part, but because the OTA window is the one thing here that can close permanently.
  Everything else can be built at leisure.

* **D6. Claude runs on the $20/month Pro subscription. No API-billed call is acceptable.**
  This is a hard cost constraint, and it has a specific trap: Claude Code's `--bare` flag "doesn't use your subscription login"
  and requires `ANTHROPIC_API_KEY`, and the Claude Agent SDK requires API-key auth rather than subscription OAuth.
  Both bill per token. klide must drive the Claude Code CLI under normal subscription auth, never `--bare`, never the Agent SDK.
  Rejected: the Agent SDK, which was the earlier recommendation on Q1 and is the better-engineered option on every axis except the one that matters here.

* **D7. A companion app on the host observes Claude and exposes a socket.**
  It ingests the session's output, renders frames, and serves them.
  Root is available on the host but is not the target: the app should run as the regular user with the least permission that works.
  D9 makes that easy, since tailing a file under the user's own `~/.claude` needs nothing privileged.

* **D8. Tailscale is already in the stack.**
  Host and Kindle do not need to share a LAN, and the transport question (Q4) is settled by it.

* **D9. klide reads the Claude Code session transcript.**
  One JSONL file per session at `~/.claude/projects/<project-slug>/<session-id>.jsonl`, tailed as it grows.
  Message-level granularity is accepted for now; at e-ink refresh rates, per-token updates were never going to be drawn anyway.
  Rejected for now: driving `claude -p` (klide would own the session instead of watching the one you are already running),
  hooks alone (events, not content), and tmux capture (throws away the structure D1 depends on).
  The cost: this is an internal format that can change between Claude Code versions, and it is read-only. See Q10.

* **D11. klide is read-only toward Claude.**
  Touch navigates klide's own views. It never sends anything to the Claude session.
  This drops the README's "minimal feedback" nice-to-have, which the README itself hedged on
  ("opens a full can of worms about duplex connections or whatever, so maybe not").
  It also keeps D9 whole: nothing in the design depends on an integration that can break a running session,
  and the companion app needs no permission beyond reading files the user already owns.
  Rejected: hooks for an approval gate, which stay available later if the read-only version turns out to be frustrating in use.

* **D10. The companion app is Python.**
  Tailing, rendering and serving a socket are all library work rather than performance work at e-ink refresh rates.

## Deferred decisions

Recorded so they are not lost. Each has a phase that will force it.

* **The frame wire format.** Whole frames versus dirty rectangles, and the encoding. Deliberately not decided now: it should follow the refresh latency measured in the display spike, not precede it. Forced by phase 3.

## Unknowns to resolve by experiment

Not open questions for the user; these are measurements, and [`02_display_spike.md`](02_display_spike.md) exists to take them.

* Does FBInk fully support the PW5 panel. The PW5 is MediaTek MT8113, not the i.MX in older Kindles, and waveform and refresh-mode handling differ. Most published prior art is on i.MX devices.
* Latency of a small partial refresh, and how many partial updates before ghosting forces a full one.
* Touch input path: which `/dev/input` node, what protocol, and whether reading it fights the running framework.
* Whether a PW5 5.16.2.1.1 `.bin` is in the community firmware archive, and whether the offline sideload path works from 5.14.1.1.
* Battery life with wifi held open and frequent redraws.

## Open questions

- Q1: How does klide obtain the conversation stream from Claude? The README says Claude runs on another machine but never says how klide observes it.
  a. Scrape a tmux pane running Claude Code, capturing on change.
  b. Drive Claude through the Claude Agent SDK, with klide as the host program that owns the session.
  c. Claude Code hooks feeding events to a klide daemon.
  Recommended: b, because it gives structured events rather than a rectangle of terminal text.
  ANS: a companion app on the desktop drives the Claude CLI and exposes a socket (D7), on the $20/month Pro subscription with no API cost (D6). That rules out the recommendation as written: the Agent SDK requires an API key. The mechanism is re-opened as Q8 with the constraint applied.
- Q2: Attempt order for the jailbreak, given the unresolved 5.14.3 lower bound.
  a. Try LanguageBreak directly at 5.14.1.1; if it fails, sideload 5.16.2.1.1 and retry.
  b. Sideload 5.16.2.1.1 first, then jailbreak once on the version the exploit is known good on.
  Recommended: a, because it costs only time if it fails and leaves b fully available, whereas b is irreversible.
  ANS: a, "if it really cost anything". Phase 1 already sequences it this way. The remark is the point: attempting the exploit at 5.14.1.1 is close to free, so there is nothing to weigh against the irreversibility of b.
- Q3: On-device client shape. This is the main architectural fork.
  a. Standalone binary using FBInk, cross-compiled with koxtoolchain.
  b. KOReader plugin in Lua.
  c. Defer until after the display spike.
  Recommended: c, because the spike answers whether FBInk drives the PW5 panel correctly, and that answer decides a versus b. If it must be called now, a, since it keeps klide independent of KOReader's release cycle.
  ANS: c. The display spike decides it. Phase 2's "Done when" already requires a recommendation backed by what was observed.
- Q4: Network topology between host and Kindle.
  a. USB networking only. Simplest and most private, but the Kindle is tethered to the host.
  b. Wifi on the LAN, key-only dropbear.
  c. Tailscale, so the host does not need to be on the same network.
  Recommended: a for development and the spike, b or c later. Nothing about the design changes with the transport, so this can be deferred without cost.
  ANS: c. Tailscale is already in the stack (D8). USB networking still stands for phase 1 and the spike, since a freshly rooted device has no Tailscale on it yet.
- Q5: Does KOReader stay installed as the epub reader regardless of Q3? The README calls continued epub reading desirable.
  Recommended: yes. It is the standard post-jailbreak reader and costs nothing even if klide ships as a standalone binary.
  ANS: yes. Installed in phase 1 and part of its exit criteria.
- Q6: If LanguageBreak fails on this device at every firmware in range, what happens?
  a. Buy a Kobo and carry the plan over; only phase 1 is wasted.
  b. Stop and reconsider the project.
  Recommended: a, because phases 2 onward are device-agnostic by D1 and Kobo needs no exploit at all.
  ANS: b, and the question is "wildly speculative". No contingency is planned for it: if the device cannot be rooted, the project stops and gets reconsidered rather than automatically migrating to other hardware. The vendor comparison above stays as research, not as a standing fallback plan.
- Q7: Host-side language and stack. Nothing is committed yet; the repo is empty.
  Recommended: Python, unless there is an existing preference. The host does rendering and process orchestration, neither of which is performance-critical at e-ink refresh rates, and the Claude Agent SDK is available for it.
  ANS: superseded by Q9, which asks the same thing with the companion-app shape known and without the Agent SDK, ruled out by D6.
- Q8: Given D6 and D7, which mechanism does the companion app use to observe Claude? Researched on 2026-09-03; all four avoid API billing.
  a. **Tail the session transcript.** Claude Code writes one JSONL file per session to `~/.claude/projects/<project-slug>/<session-id>.jsonl`. Verified on this machine: this session's file holds `user`, `assistant` (with `text`, `thinking` and `tool_use` blocks) and `system` records.
     Pro: zero cost, zero interference, read-only so it cannot break a session; works while you drive Claude normally in your own terminal; one file per session means "multiple conversations" is nearly free; klide can restart and re-read from the top.
     Con: message-level granularity, not token-level; the format is internal and can change between Claude Code versions; read-only, so it gives no way to send anything back.
  b. **Companion app drives `claude -p --output-format stream-json --verbose --include-partial-messages`.** Documented event stream, `--resume <session-id>` for multiple conversations, `system/init` for metadata.
     Pro: token-level streaming; a documented and supported schema; the only option that can also send input, which phase 5 needs; runs on the subscription as long as `--bare` is avoided.
     Con: klide owns the session, so your interactive terminal is no longer the thing driving Claude. This is a different product from "a second screen for the session I am already running".
  c. **Claude Code hooks feeding a klide daemon.** Documented, event-driven, coexists with an interactive session, and a `PreToolUse` hook is a natural place to hang an approval gate.
     Pro: supported extension point; the cleanest write path for phase 5's approve/reject without taking over the session.
     Con: hooks fire on events, not content, so this is not a conversation stream on its own and must be paired with a or b.
  d. **Capture a tmux pane.** Works with anything, no integration at all.
     Pro: cannot break, and is a fifteen-minute spike.
     Con: a rectangle of ANSI text. It discards exactly the structure D1 depends on for diff and file views, and reconstructing it is worse than reading the structured source.
  Recommended: a + c. Tailing gives the content while you keep driving Claude in your own terminal, hooks give the write path, and neither takes the session away from you. b is the fallback if the transcript format proves too unstable, and is the right answer instead if klide should own the session rather than watch it. d only as a throwaway spike to see something on the screen early.
  ANS: a for now, accepting message-level granularity to begin with. Recorded as D9.
  Note the consequence: a alone is read-only, so klide can show a Claude session but cannot answer one. Navigation still works, since that is klide's own UI. Answering Claude needs a write path, re-opened as Q10.
- Q9: Host-side language, re-asking Q7 now that the shape is known: a long-lived companion process that tails or spawns a subprocess, renders bitmaps, and serves a socket.
  Recommended: Python. All three jobs are library work rather than performance work at e-ink refresh rates, and Pillow covers the rendering.
  ANS: Python. Recorded as D10.
- Q10: klide can now show a Claude session but not answer one, because D9 is read-only. What provides the write path for phase 5's approve and multiple-choice?
  a. Add Claude Code hooks alongside the transcript tail. A `PreToolUse` hook can block on klide's answer, which is exactly the approval gate the README describes.
  b. Switch ingestion to `claude -p --output-format stream-json` (Q8 b), which can both read and write, at the cost of klide owning the session.
  c. Leave klide read-only. Touch drives klide's own navigation only, and answering Claude stays out of scope.
  Recommended: c until phases 3 and 4 exist, then a. Navigation is most of phase 5's value and needs no write path at all; the approval gate is the one part that does, and hooks add it without giving up the read-only design that made D9 attractive.
  ANS: c. klide stays read-only toward Claude. Touch drives klide's own navigation; answering Claude is out of scope. Recorded as D11.

