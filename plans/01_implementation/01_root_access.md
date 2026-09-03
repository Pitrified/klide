---
status: planned
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
- Copy the entire USB volume to the host as a backup. Documents are expendable but the copy is free.
- Remove any device password lock; LanguageBreak requires none.
- Run the kindlemodding jailbreak wizard against the actual model and firmware, and follow whichever exploit it names rather than the table in `00_start.md`. The table is a map, not a spec.
- Read the LanguageBreak walkthrough end to end before touching the device, and confirm every step of the reset and setup flow can be completed with no network. The exploit works through the language selection screen, which is part of the post-reset setup wizard, and that wizard normally presents a wifi step.
- Attempt LanguageBreak at 5.14.1.1 (Q2: a). It needs a factory reset into demo mode, then a two-stage sideload during a "Resell Device" operation.
- If it fails: sideload the 5.16.2.1.1 `.bin` over USB via Settings > Update Your Kindle, offline, then retry. Never update past 5.16.2.1.1.
- Install the LanguageBreak hotfix (its own, not the standard one), then KUAL and MRPI.
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
- A backup of the pre-jailbreak USB volume exists on the host.

## Risks

- The factory reset drops the device into the out-of-box setup wizard, which asks for wifi. This is the single moment in the project where an accidental network connection is most likely, and it is unresolved whether the wizard can be dismissed without one. LanguageBreak's own procedure runs in airplane mode and exploits the language screen inside that wizard, so it should be possible, but confirm from the walkthrough before starting rather than while standing at the screen.
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

