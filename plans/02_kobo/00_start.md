---
status: draft
---

# Kobo - bootstrap

A friend lends a Kobo. Research and decisions for the Kindle path stay in [`../00_initial/00_start.md`](../00_initial/00_start.md);
this folder covers only what differs. Web research 2026-09-04, nothing tested, and the device is not in hand yet.

## New constraint

The device goes back. Nothing risky, nothing hard to restore.

- No firmware update, no factory reset, no partition or bootloader work.
- Changes live on the USB-visible user partition where possible, under `.adds/`. Root filesystem changes only through packages that ship an uninstaller.
- Do not touch the owner's Kobo account, library, reading positions or settings. Back up `.kobo/Kobo/Kobo eReader.conf` and the user partition before the first change, and verify the restore before returning the device.
- Every install is recorded in this folder with its removal step, checked by putting the device back to stock once during the loan, not at the end.

## What changes

Phase 1 mostly disappears. Kobo needs no exploit: KOReader installs from a `KoboRoot.tgz` that Nickel unpacks on eject,
KFMon launches it, and a root shell comes from KOReader's dropbear plugin with keys in `.adds/koreader/settings/SSH`.
No demo mode, no timing-critical replug, no anti-rollback, no OTA fear. Wifi is allowed here, so the whole airplane-mode discipline drops.

## Easier

- Panel and toolchain are the well-trodden path. FBInk's main platform is Kobo, most i.MX rather than the PW5's MT8113, which removes the largest unknown in the display spike.
- KOReader on Kobo is a first-class target with published builds, not a post-jailbreak add-on.
- Reversibility is native: KFMon ships an uninstaller, NickelMenu removes itself from a file in `.adds/nm/`, and KOReader is a directory.
- Wifi from day one means the Tailscale answer (Q4) can be exercised immediately, and the USB-networking workaround for a freshly rooted device is not needed.

## Harder

- Model and firmware are unknown and decide a lot. Kobo firmware 5.x breaks NickelMenu; KFMon supports it, and KOReader's Kobo v5 support arrived in nightlies in July 2026. On 4.x both launchers are available.
- Screen size and DPI are unknown until the model is, so the renderer's layout numbers cannot be fixed yet.
- Firmware updates arrive when the device syncs and disable KFMon. On the Kindle the answer was to block updates permanently; here it is to reinstall, because blocking updates on a borrowed device is exactly the kind of change that is hard to hand back.
- Nickel keeps running. Whatever draws to the framebuffer has to coexist with it or stop it and put it back.
- The loan has an end date, and device-specific findings may not carry to the PW5.

## Technology choices to revisit

- Q3, on-device client shape. The reversibility constraint pushes it to the KOReader plugin: a plugin is files under `.adds/koreader/plugins/`, removed by deleting them, and it inherits touch input. A cross-compiled FBInk binary is more to install and more to leave behind, and it needs a different koxtoolchain target than the Kindle work assumed.
- Q4, transport. Wifi is available immediately, so plain LAN or an SSH tunnel through KOReader may be enough for the spike and Tailscale becomes one more thing to install and remove.
- D1 stops being an assumption. Two devices make the host-renders-frames split testable instead of asserted.

## Back on the table

- Continued reading is free. Nickel and the owner's library stay in place, so Q5 turns from a requirement into a side effect.
- Touch navigation gets cheaper through the plugin path, but D11 does not reverse: klide is read-only toward Claude because it tails a transcript, which is a host-side fact and has nothing to do with the device.

## Open questions

- K1: Which Kobo, and on which firmware. Needed before anything else; ask the friend for the model and Settings > Device information.
- K2: How long the loan is, and whether the friend accepts a documented, reversible install at all, or only what the stock UI allows.
- K3: Does this replace the Kindle path or run beside it. The Kindle plan is mid-phase 1 with the firmware update not yet applied.
