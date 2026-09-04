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
- Reversibility is native: KFMon ships an uninstaller and KOReader is a directory.
- Wifi from day one means the Tailscale answer (Q4) can be exercised immediately, and the USB-networking workaround for a freshly rooted device is not needed.

## Harder

- Model and firmware are unknown and decide a lot. KOReader's Kobo v5 support arrived in nightlies in July 2026, so on firmware 5.x the build is a nightly rather than a release.
- Screen size and DPI are unknown until the model is, so the renderer's layout numbers cannot be fixed yet.
- Firmware updates arrive when the device syncs and disable KFMon. On the Kindle the answer was to block updates permanently; here it is to reinstall, because blocking updates on a borrowed device is exactly the kind of change that is hard to hand back.
- Nickel keeps running. Whatever draws to the framebuffer has to coexist with it or stop it and put it back.
- The loan has an end date, and device-specific findings may not carry to the PW5.

## Launcher

Nickel, the stock UI, will not start anything that is not Kobo's, and there is no app list or shell to reach from it.
A launcher is the bridge: something running outside Nickel that notices an action the user can take inside it, and spawns a program.

KFMon is a daemon started at boot from a udev rule. It watches with inotify for one chosen file being opened in Nickel and runs the command bound to it.
The KOReader entry looks like a book in the library; tapping it starts KOReader.
NickelMenu instead hooks Nickel's own menus and adds real entries to them, running arbitrary commands, chaining them, toggling wifi, rebooting, showing command output.

KFMon is the choice: it supports firmware 5.x and NickelMenu does not, it does not hook into Nickel, and it ships an uninstaller.

What that costs:

- Arbitrary commands from the stock UI. Each KFMon action needs its own watched file, and each shows up in the owner's library. One entry for klide is fine, a menu of utilities is not.
- Launching from where you already are. A KFMon trigger means going to the library and opening the item.
- The on-device conveniences, wifi toggle, reboot, run a script and show its output. Those move to the host over SSH.

None of it is on the critical path, because klide needs exactly one launch action.

Skipping the launcher entirely is possible once a shell exists, since KOReader and klide can then start from the host.
Getting that first shell is the catch: dropbear ships inside KOReader, which is what the launcher starts.
The way out is Kobo's own debug services, `EnableDebugServices=true` under `[DeveloperSettings]` in `.kobo/Kobo/Kobo eReader.conf`,
reported to give root telnet on 4.x on current models and unverified on 5.x.
That is one config line and the most reversible root access available.
The alternative, a `KoboRoot.tgz` that drops a boot script, is a root filesystem change and is not worth it here.
Test debug services first (K1); if they work, the launcher is a convenience rather than a dependency.

See KD1 below, which settles how much the device is asked to do.

## Technology choices to revisit

- Q3, on-device client shape. The reversibility constraint pushes it to the KOReader plugin: a plugin is files under `.adds/koreader/plugins/`, removed by deleting them, and it inherits touch input. A cross-compiled FBInk binary is more to install and more to leave behind, and it needs a different koxtoolchain target than the Kindle work assumed.
- Q4, transport. Wifi is available immediately, so plain LAN or an SSH tunnel through KOReader may be enough for the spike and Tailscale becomes one more thing to install and remove.
- D1 stops being an assumption. Two devices make the host-renders-frames split testable instead of asserted.

## Back on the table

- Continued reading is free. Nickel and the owner's library stay in place, so Q5 turns from a requirement into a side effect.
- Touch navigation gets cheaper through the plugin path, but D11 does not reverse: klide is read-only toward Claude because it tails a transcript, which is a host-side fact and has nothing to do with the device.

## Decisions

* **KD1. One launch action on the device, everything else from the host by preference.**
  The Kobo starts a single thing. Driving, debugging, restarting and inspecting normally happen over a network shell,
  ssh, telnet, Tailscale or USB, from a machine with a real screen and keyboard rather than a small, laggy e-ink one.
  Picking the device up and doing something on it is allowed where that is simply easier; it just should not be the routine path.
  Consequences: KFMon's one-file-per-action limit stops mattering, and the on-device conveniences NickelMenu would have given are not missed.

## Open questions

- K1: Which Kobo, and on which firmware. Needed before anything else; ask the friend for the model and Settings > Device information.
- K2: How long the loan is, and whether the friend accepts a documented, reversible install at all, or only what the stock UI allows.
- K3: Does this replace the Kindle path or run beside it. The Kindle plan is mid-phase 1 with the firmware update not yet applied.
