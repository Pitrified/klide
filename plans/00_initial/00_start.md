# Klide initial research

## draft

given the general idea in klide/README.md

web search for:
* kindle experimental browser capabilities
* kindle custom os or root access
* existing kindle hacks or mods - for fun, even unrelated
* existing kindle hacks or mods - for connecting AI assistants to the kindle
* ??? anything else pertinent

## findings

Web research only, September 2026. Nothing below has been tested on hardware.
Firmware and exploit facts are the most perishable part of this page.

Target device: Kindle Paperwhite 11th gen (PW5) on firmware 5.14.1.1, which is the version the PW5 shipped with.
The device has never taken an update. Documents on it are expendable and will be backed up first.
Devices from other vendors are in scope.

### Do this before anything else

**Keep the device off wifi and in airplane mode.**
5.14.1.1 is old enough to be jailbreakable and new enough that Amazon will push it straight to 5.19.x on first contact with a network.
That update is one-way: anti-rollback blocks downgrading below 5.18.x, and 5.19.5 has no public jailbreak.
The single largest risk to this project is the device connecting to wifi once before anyone has locked it down.

Also check the root of the USB volume for `.bin` or `update.bin.tmp.partial` files, which mean an update is already staged, and delete them.

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

### Jailbreak: LanguageBreak

At 5.14.1.1 the applicable exploit is [LanguageBreak](https://github.com/notmarek/LanguageBreak), which covers everything at or below 5.16.2.1.1.
It fits the project's constraints better than any of the newer ones:

* **No Amazon account required.** It works on unregistered devices. The store-based exploits (WinterBreak, SpringBreak) need a registered Kindle with the Kindle Store reachable, which the README rules out.
* **No wifi required.** The documented procedure has airplane mode on throughout.
* It wants a factory reset and demo mode, and the device must have no password lock. The reset wipes documents, which is already acceptable here.
* It has its own hotfix, installed instead of the standard one.

One unresolved conflict in the sources: the kindlemodding gitbook page is titled "LanguageBreak (5.14.3-5.16.2.1.1)",
while the upstream repo says "any kindle running FW 5.16.2.1.1 or lower" and adds that the exploit "works best around version 5.16.2".
5.14.1.1 is below 5.14.3. Whether that lower bound is real or just the range the page author tested is not settled by anything found.

That gives two orderings, and the choice should be made before touching the device:

1. Attempt LanguageBreak directly at 5.14.1.1. Costs nothing but time if it fails, and leaves option 2 open.
2. Sideload a controlled update to 5.16.2.1.1 first, then jailbreak. Copy the `.bin` to the USB root and use Settings > Update Your Kindle; this works offline, so airplane mode stays on. Firmware archive: `files.cocaine.trade/firmware/kindle/`. **Do not go past 5.16.2.1.1** - 5.16.3 introduced breaking changes and later versions patch LanguageBreak.

Trying 1 first and falling back to 2 is the low-risk order.

Once jailbroken, block OTA updates with `renametobin` before wifi is ever enabled.
That must be reverted before any deliberate update or factory reset, or the device locks.
The jailbreak itself survives reboots; the hotfix and sometimes KUAL need reinstalling after a firmware update.

For reference, the wider exploit map, since the versions shift and sources disagree on the edges:

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
per-region refresh with explicit waveform choice, and it already supports Kindle, Kobo, reMarkable and PocketBook.
KOReader itself uses FBInk for input handling on Kindle.
This is what every dashboard project does, and it matches klide's requirements most directly:
the host renders a bitmap, the Kindle draws it, so markdown rendering, diffs, syntax highlighting and layout are all host-side problems.

**b. KOReader plugin (Lua).** KOReader is already a full framebuffer application with input, networking (luasocket),
a plugin API, and existing plugins for SSH, a terminal emulator, and keep-alive.
The `assistant.koplugin` family already streams LLM responses from Anthropic/OpenAI/Gemini/OpenRouter/Ollama on e-ink,
so streaming text into a KOReader UI is demonstrated, not speculative.
Touch input comes for free, which makes the "minimal feedback" nice-to-have (approve, multiple choice) cheap.
Cost: writing Lua against KOReader internals, and coupling to KOReader's release cycle.

**c. The experimental browser.** The weakest option, and it fails the primary requirement.
It is WebKit 531-534 (Safari 4/5 era). No WebSockets. HTML5 support is described as almost absent,
so long-polling is the only push mechanism anyone has got working.
One project reports `http://localhost` being unreachable from the browser and had to patch the `browserd` daemon to allow `file://`.
The device sleeps after roughly ten minutes unless the screensaver is disabled from a root shell, there is no kiosk mode,
and JS execution is slow enough that jQuery parse time is comparable to an iPhone 4.
Continuous streaming updates without a page reload are not realistically achievable here.

Recommended shape: **the Kindle is a dumb frame sink and input source; everything else runs on the host.**
That keeps the on-device code small, avoids cross-compiling a markdown/diff/highlighting stack for ARM,
and makes supporting a second device mostly a matter of screen dimensions.

### Requirements from the README, mapped

| requirement | path |
| --- | --- |
| streaming, continuous, no reload | host pushes frames over long-lived HTTP or a socket; on-device loop draws with FBInk partial updates |
| multiple conversations | host-side state, Kindle sends a "switch" event |
| diff, file navigation | host-side rendering, same frame channel |
| markdown, syntax highlighting | host-side, never on the device |
| minimal feedback (approve, choose) | touch events. KOReader plugin gives this directly; the FBInk path needs a small reader on `/dev/input/event*` posting back to the host |

Refresh behaviour will decide whether this feels usable:
partial updates are fast and leave ghosting, full updates are clean and flash.
A text pane that appends tokens wants partial updates on a small region plus a periodic full refresh.
FBInk exposes exactly that control; the browser does not.

### Networking

USB networking is the simplest and most secure, but tethers the Kindle to the host.
Over wifi, dropbear via USBNetwork or the KOReader SSH plugin works;
the USBNetwork wifi configuration has historically been reported as passwordless, so key-only auth needs checking explicitly.
Tailscale runs on jailbroken Kindles in proxy and tun modes, which removes the same-LAN constraint if Claude runs elsewhere.
Keeping the device awake and on wifi means fighting `powerd` via lipc; KOReader's KeepAlive plugin does this already.
Battery cost of an always-on wifi link plus frequent partial refreshes is unmeasured here.

### Other vendors

Now that buying a different device is allowed, the tradeoff is roughly: how much work to get code running, against how good the screen and the price are.

* **Kobo.** No exploit needed. Linux with a Qt frontend, NickelMenu adds launcher entries by dropping a file in `.kobo`, KOReader runs natively, telnet/SSH are reachable, FBInk supports it, and postmarketOS ports exist for some models. Everything in the FBInk and KOReader plans above applies unchanged, minus the jailbreak chapter and minus the permanent fear of an OTA update. The obvious fallback if the PW5 does not cooperate.
* **Boox.** Android, with ADB and normal sideloading on models that do not block developer mode. This turns klide into an Android app: a socket, a text view, touch input, and vendor APIs for refresh mode. By far the least device-level work, and the least interesting. Larger, more expensive, and the vendor's privacy record is worth checking before it becomes the always-on display for a coding session.
* **reMarkable.** Root shell over SSH is available without any exploit, and there is an existing project turning a Paper Pro Move into a dockable e-ink terminal running persistent Claude Code sessions over tmux and Tailscale, which is close to klide's goal. Worth reading regardless of what hardware gets used. Expensive, and the writing-focused hardware is not needed here.

The PW5 already in hand, on jailbreakable firmware, is the cheapest experiment.
Nothing found suggests the project needs a different device; the argument for one is only about how much time goes into the jailbreak and the low-level display code rather than into klide itself.

### Prior art

Displays and dashboards:

* [adtac gist, Kindle as an e-ink monitor](https://gist.github.com/adtac/eb639d3c707b55a28f0ee9a420aa7e0c) - screencapture, grayscale JPEG, netcat over USB net, `eips -g -w gc16`, reported around 3.5 fps on a PW3. Closest existing thing to klide.
* [kindletron](https://github.com/forestpurnell/kindletron) - VNC screenshot served over HTTP, Kindle polls. Default 60s refresh; the polling model is the part to avoid.
* [trmnl-kindle](https://github.com/usetrmnl/trmnl-kindle) - maintained dashboard client, 6th gen and later, tested on 10th and 12th gen. Useful for install packaging and sleep/redraw handling, which its roadmap admits is unfinished.
* [kiiin](https://github.com/thekakkun/kiiin), [kindledashboard](https://github.com/nfunky/kindledashboard), [kindle-voyage-weather](https://github.com/cdmckay/kindle-voyage-weather) - the weather-dashboard genre; all host-renders-image, Kindle-draws-image.

Tooling:

* [FBInk](https://github.com/NiLuJe/FBInk) - the display primitive.
* [koxtoolchain](https://github.com/koreader/koxtoolchain) - cross-compiler for native binaries.
* [KOReader](https://github.com/koreader/koreader), [terminal emulator](https://github.com/koreader/koreader/wiki/Terminal-emulator), [keep alive](https://github.com/koreader/koreader/wiki/Keep-alive) wiki pages.
* [KindleTool](https://github.com/NiLuJe/KindleTool) - firmware package extraction.
* [kindlemodding.org](https://kindlemodding.org/jailbreaking/) - the jailbreak wizard and FAQ; run the wizard against the real device before acting on the table above.
* [Kindle Mod Shelf](https://kindlemodshelf.me/) - curated index of jailbreaks, plugins, games.

AI on e-ink:

* [assistant.koplugin](https://github.com/omer-faruq/assistant.koplugin) - KOReader plugin, multiple providers including Anthropic, has a streaming mode. The most relevant precedent for rendering streamed model output on e-ink.
* [AskGPT](https://github.com/drewbaumann/AskGPT) - the ancestor of the above.
* [JailbreakedKindleGPT](https://github.com/ronibandini/JailbreakedKindleGPT) - shell script driven from kterm. Minimal, but proves the plumbing.
* The reMarkable Paper Pro Move terminal project noted above, for persistent Claude Code sessions on e-ink. Not located precisely yet; worth finding.

Unrelated but instructive about what the hardware tolerates:
DOOM, Game Boy emulation, VNC clients, Bluetooth audio players, interactive fiction interpreters,
and a (deprecated) [Debian chroot](https://github.com/simonachmueller/DebianKindle).

* [TAKT PW5 hardware notes](https://kb.taktpraha.cz/projects/kindlepw5) - UART over USB-C, secure boot, eMMC interposer.

### Open questions

* Does LanguageBreak actually work at 5.14.1.1, or does the 5.14.3 lower bound on the gitbook page hold. Decides whether a controlled update to 5.16.2.1.1 comes first.
* Is a PW5 5.16.2.1.1 `.bin` present in the community firmware archive, and does the offline sideload path work from 5.14.1.1.
* Does FBInk fully support the PW5 panel. The PW5 is MediaTek MT8113, not the i.MX used by older Kindles, and waveform and refresh-mode handling differ. Most published prior art is on i.MX devices.
* Touch input path on PW5: which `/dev/input` node, what protocol, and whether reading it conflicts with the running framework.
* Latency of a small partial refresh on PW5, and how bad ghosting gets before a full refresh is required.
* Battery life with wifi held open and frequent redraws.
* Whether to build on KOReader or ship a standalone binary. The main architectural fork, and it does not need deciding until root is on the device.
