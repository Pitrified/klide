---
status: in progress
---

# Phase 1 - Root access

## Overview

Get a root shell on the PW5 and put it in a state where Amazon can no longer take it away.
Sequenced first because the OTA window is the only thing in this project that can close permanently:
one wifi contact takes 5.14.1.1 to 5.19.x, and anti-rollback makes that irreversible.
No klide code is written in this phase.

Context: [`../00_initial/00_start.md`](../00_initial/00_start.md).

## Goals

1. Back up the device contents before anything destructive.
2. Root the device with LanguageBreak, without registering it to an Amazon account.
3. Install the post-jailbreak stack and block OTA updates.
4. Reach a shell from the host.

## Plan

- Confirm airplane mode is on and stays on for the whole phase. Re-verify no `.bin` or `*.partial` files are on the USB volume.
- Back up the irreplaceable contents of the USB volume. Not the whole volume: most of what is on it regenerates.
  Copy the books (`.mobi`, `.azw3`), the `.sdr` sidecar directories whole (reading positions, bookmarks, highlights),
  `system/userannotlogsDir`, `system/vocabulary`, `system/collections.json`, and `fonts/`.
  Skip `voice/` (reinstalls with the firmware), `.Trash-1000/`, search indexes, thumbnails, caches, and the calibre metadata files,
  which calibre rebuilds from the host library.
  Verify the copy by comparing SHA-256 per file in both directions, not by size and not by rsync's exit code.
- Remove any device password lock; LanguageBreak requires none.
- Run the kindlemodding jailbreak wizard against the actual model and firmware, and follow whichever exploit it names rather than the table in `00_start.md`. The table is a map, not a spec.
- ~~Read the LanguageBreak walkthrough end to end and confirm the flow needs no network.~~ Done 2026-09-04; see Risks. The shape of the procedure, recorded here so the sequencing is known in advance, with the published guide remaining the source of truth for the exact steps:
  factory reset, dismiss the setup wizard's wifi step, `;enter_demo` in the search bar and reboot, skip demo wifi and enter fake information, choose the `standard` demo type,
  clear the misconfiguration error with a two-finger tap then left swipe, sideload the LanguageBreak files to root over USB,
  "Resell Device" from the demo menu, **replug to the PC the moment the "press power button" message appears** and sideload a second time,
  then select Chinese, second from last in the right-hand list. The device reboots into log output.
- Note the timing step above is the only one that is not self-paced. Have the files staged on the host and the cable connected before starting the Resell operation.
- Attempt LanguageBreak at 5.14.1.1 (Q2: a). It needs a factory reset into demo mode, then a two-stage sideload during a "Resell Device" operation.
- If it fails: sideload the 5.16.2.1.1 `.bin` over USB via Settings > Update Your Kindle, offline, then retry. Never update past 5.16.2.1.1.
- Install the LanguageBreak hotfix (its own, not the standard one): `;uzb` in the search bar, copy `update_hotfix_languagebreak.bin` to root, then `;dsts` and select update. Then KUAL and MRPI.
- Note this contradicts the no-`.bin` rule above only in appearance: that rule is a precondition for starting, because a `.bin` at root means a staged OTA. Placing the hotfix `.bin` deliberately, later, is the intended flow.
- Block OTA with `renametobin`. Record in this file how to revert it, because a factory reset while it is active locks the device.
- Install a shell path: USBNetwork for dropbear over USB, and kterm on-device as a fallback that needs no host.
- Install KOReader (Q5: yes), so the device is still a usable reader independent of klide.

## Out of scope

- Any wifi configuration. Phase 1 stays on USB. Network topology is Q4 and belongs to phase 3.
- FBInk, drawing, and input. That is phase 2.
- Deciding between a standalone binary and a KOReader plugin. That is Q3, answered by phase 2.

## Done when

- A root shell on the device is reachable from the host over USB networking.
- `renametobin` is active and the revert procedure is written down in this file.
- KUAL launches and MRPI can install a package.
- KOReader opens an epub.
- A verified backup of the irreplaceable USB volume contents exists on the host, checked by per-file SHA-256 in both directions.

## Risks

- ~~The setup wizard may require wifi.~~ **Resolved 2026-09-04 by reading the walkthrough.** Airplane mode ON is a stated prerequisite of the exploit, the setup wizard's wifi step is dismissed by selecting any network and backing out, and demo mode's own setup is skipped with fake information. No step needs a network or an Amazon account. Watch for one small tension at the screen: with airplane mode on there may be no networks listed to select and back out of.
- The 5.14.3 lower bound on the kindlemodding page may be real, in which case the direct attempt fails. Handled by the sideload fallback above; costs time, not the device.
- A factory reset with `renametobin` already active locks the device. Order matters: reset first, jailbreak, then block updates.
- If both firmware levels fail, the project stops and gets reconsidered (Q6). There is no automatic migration to other hardware; the vendor comparison in the research file is background, not a queued fallback.

## Recovery

Write each of these down as it is confirmed, rather than looking them up mid-incident.

- **`renametobin` is active and a reset is needed.** Revert `renametobin` first. A factory reset with it active locks the device; kindlemodding publishes a recovery guide for that state.
- **Jailbreak lost after a firmware change.** The jailbreak itself survives; reinstall the hotfix, then KUAL, then extensions.
- **Device boots but KUAL is gone.** Reinstall the hotfix and KUAL from scratch before assuming anything worse.
- **Device will not boot.** Recovery mode and the kindlemodding recovery guide. The PW5 has no accessible UART on a stock unit, so there is no serial console fallback without hardware work.
- **Wifi reached the device and it updated.** Check `system/version.txt`. Above 5.16.2.1.1 LanguageBreak is gone; above 5.18.3 Sanctuary is gone too. Above both, Q6 applies and the project stops rather than routing around it.

## What the implementation found

- The volume holds far less unique data than its size suggests. Nearly all of it is text-to-speech voice data, deleted books, and rebuildable indexes; the irreplaceable part beyond the books is a few MB. The original step said "copy the entire volume, the copy is free", which was reflex rather than measurement.
- **rsync can report success having copied nothing.** An include filter that matches a nested directory pattern still needs the intermediate directories included, or rsync prunes them before descending. The first sidecar copy exited 0 and transferred none of them. Only a per-file checksum comparison caught it. Verify content, not exit codes, for anything on this device.
- Zero-byte `*.partial` files live in `system/thumbnails` as placeholders. They are unrelated to firmware updates, but they will match a naive `*.partial` search for a staged OTA. Check the filename, not just the extension.

