# reader UI tracking

The four pages a reader walks on the device, and the extractor behind them. Opened from an interview
on 2026-09-19 that started from a written specification of the pages and a question about the Agent
Host Protocol. Analysis and decisions in [`00_start.md`](00_start.md).

The views this arranges were built in [`../04_klide_app/04_host_renderer.md`](../04_klide_app/04_host_renderer.md);
the viewer that makes them checkable is [`../04_klide_app/05_viewer.md`](../04_klide_app/05_viewer.md).
The gesture map this supersedes is in [`../02_kobo/01_ui_ux.md`](../02_kobo/01_ui_ux.md).

## Key decisions

- AHP's data model, not its transport; Claude Code does not serve AHP, so the extractor exists either
  way and this only decides what it fills in (UD1).
- Navigation is a stack of four pages, down by tapping and up by a back control, which supersedes the
  swipe carousel (UD2).
- A tap opens the row under it, with no cursor on either side (UD3).
- The physical buttons scroll the current page, everywhere, always (UD4).
- The diff is what is uncommitted; the `change_kind` cycle is wanted and deferred (UD5).
- Page 1's extra states are derived from the transcript, and the derivation is logged (UD6).
- Page 1 updates in place; pages 3 and 4 hold still and say when they are stale (UD7).
- Page 3 is a tree of touched files, absorbing the flat changed files view and the full file tree (UD8).
- The stale marker is itself the refresh control, so it costs no room in the top strip (UD9).

## Phases

| #  | Phase                 | Plan                                              | Status |
| -- | --------------------- | ------------------------------------------------- | ------ |
| 1  | Extractor and model   | [`01_extractor.md`](01_extractor.md)              | planned |
| 2  | Navigation            | [`02_navigation.md`](02_navigation.md)            | draft |
| 3  | The four pages        | [`03_four_pages.md`](03_four_pages.md)            | draft |
| 4  | Live and stale        | [`04_live_and_dirty.md`](04_live_and_dirty.md)    | draft |

Status values: draft / planned / in progress / done / superseded / discarded.

Phase 1 is planned because it needs nothing that does not exist: three local sources, no device, no
screen decisions. The rest stay draft because U7 decides where phase 2's state lives and phase 1's
measurements decide U4.

## Log

Append-only. Newest at the bottom.

- 2026-09-19 : opened from a two round interview, run by hand because the `/grill-me` skill it was
  asked for is still a draft in [`../05_grill_me/00_start.md`](../05_grill_me/00_start.md) with no
  `SKILL.md`. Researched the Agent Host Protocol: it is Microsoft's, published August 2026, JSON-RPC
  with snapshots and action envelopes over immutable state, VS Code the reference server, and Claude
  Code is not an implementation, confirmed against 2.1.273 on this box. Took the state model and left
  the transport, because the vocabulary settles two arguments this repo was about to have, `IsRead`
  for unread and `changeKind` for what a diff is. Verified the three local sources the extractor has,
  including that `claude agents --json` runs without a TTY and returns the name, repo and a status of
  idle or busy for every live session, which is most of page 1 and none of its interesting states.
  Established that the specified navigation is a stack and the gesture map is a carousel, and that the
  gesture map loses. Eight decisions UD1-UD8, seven questions U1-U7, four phases
- 2026-09-19 : answered what refreshes a page once it says it is stale, which the interview left open.
  The marker is the control: tapping it redraws the page (UD9). It spends no room in the top strip,
  which the back control already has, and it means a page that reports being out of date is also the
  way to fix it. Noted against U6 that this does not obviously generalise to the `changeKind` cycle,
  because a marker appears when there is something to say and a scope control has to be present
  before the reader knows they want it
