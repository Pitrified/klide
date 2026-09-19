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
- The diff totals are the only tappable part of the recap (UD10).
- The back control sits on the recap's own first line, so no strip is reserved for it (UD11).
- Read is per host, per session, and tapping into a conversation marks it read (UD12).

## Phases

| #  | Phase                 | Plan                                              | Status |
| -- | --------------------- | ------------------------------------------------- | ------ |
| 1  | Extractor and model   | [`01_extractor.md`](01_extractor.md)              | done |
| 2  | Navigation            | [`02_navigation.md`](02_navigation.md)            | done |
| 3  | The four pages        | [`03_four_pages.md`](03_four_pages.md)            | done |
| 4  | Live and stale        | [`04_live_and_dirty.md`](04_live_and_dirty.md)    | planned |

Status values: draft / planned / in progress / done / superseded / discarded.

All four are planned since the U batch was answered. Phase 1 still goes first: it needs nothing that
does not exist, and its measurement of what `claude agents --json` costs is what settles U4's
cadence. Phase 2 opens with the split U7 asked about, which is assessed but not decided.

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
- 2026-09-19 : answered U1 to U7. The recap's diff totals are its only tap target (UD10); the back
  control shares the recap's first line rather than getting a strip, which was not the recommendation
  and which makes the recap's first line shorter than the ones under it (UD11); read is per host per
  session and tapping in marks it read (UD12); the extractor's cadence waits on a measurement in
  phase 1; `one_file` stays unrouted and repo browsing is deferred with it; the `changeKind` cycle is
  deferred and only the uncommitted kind is shown. U7 was answered with "assess", so
  `src/klide/serve.py` was read and the assessment written into `00_start.md`: its loop does four
  things and three of them are page independent, so the recommendation is one loop with the source,
  `apply_event` and `render` turned into calls on the top of a stack, and `LiveState` demoted to the
  conversation page's state. Two objections checked rather than assumed: a page change needs no new
  refresh mechanism, since `pick_waveform` already returns the full waveform for a patch that size,
  and the coalescer and the socket handling both got their current shape from failures, so a loop per
  page would copy them or drift. All four phases move to planned
- 2026-09-19 : phase 1 done. `klide.ahp` holds the types, named after AHP's state model, and
  `klide.extract` fills them from the three local sources; `uv run klide-extract` prints the five
  live sessions on this box with their repo, branch, derived state and changeset. U4 answered by
  measuring: `claude agents --json` costs 0.22 s, so it is polled at 5 s while the transcripts keep
  0.25 s. The derivation rule was written in prose in the module docstring before it was
  implemented, and then measured: 758 real pause points across every transcript on this box, 43 of
  which end in a question mark, all five sampled being genuine questions. High precision, low
  recall, and the direction to be wrong in for a glanceable column. Rule 2 was checked by replaying
  a real transcript prefix by prefix at each of its three `AskUserQuestion` calls. The hole nobody
  can close from these sources is a permission prompt, which reaches neither the CLI nor the
  transcript
- 2026-09-19 : phase 3 done, taken before phase 2 because navigation has nothing to move between
  until the pages exist and the pages need no loop. The six views are now four pages plus the
  unrouted file view: `sessions`, `conversation_page`, `changes` and `one_diff`, each returning a
  `Page` of a column and its targets. `conversations`, `changed_files` and `file_tree` are deleted
  with their references (UD8). Page 4 keeps the path alone rather than the shared recap, which is
  the specification over the phase plan's step 2. Two new references cover states rather than
  pages: the empty changeset, which is what this repo shows most of the time, carrying the stale
  marker so the refresh control is in a reference too. Both shown failing before being counted
- 2026-09-19 : phase 2 done, and U7 with it. The serve loop grew a three-method `Source` protocol,
  which is exactly the three page specific points the assessment named, and `run_source` is now
  the loop for both the single-conversation host and the new `Reader`. The stack lives in the
  reader, above the loop and below the pages. The whole four-page walk was driven in a browser
  against live sessions on this box, including a tap that opened the patch of the file being
  edited at that moment, and three taps back up. One claim in the phase plan came out false when
  measured: a page change is not always a full refresh, because two pages sharing a recap produce
  a patch that starts below it, 74% of the panel and so just under the waveform threshold. Left as
  it is, recorded, and phase 4 owns refresh behaviour. The gesture map in `02_kobo/01_ui_ux.md`
  now carries what the reader actually does
