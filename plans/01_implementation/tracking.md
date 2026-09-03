# implementation tracking

Klide turns a Kindle Paperwhite 11th gen into a streaming external display for Claude:
conversations, diffs and file views rendered on the host and drawn on e-ink, with touch used to navigate them.
Research, decisions and open questions live in [`../00_initial/00_start.md`](../00_initial/00_start.md).
This folder's own bootstrap note is [`00_start.md`](00_start.md).

## Key decisions

- The Kindle is a dumb frame sink and input source; all rendering happens on the host (D1). Keeps device code small and makes a second device mostly a matter of screen dimensions.
- The Kindle experimental browser is not a candidate: no WebSockets, no push, a ten-minute sleep (D2).
- Use the PW5 already in hand, on firmware 5.14.1.1, jailbroken with LanguageBreak (D3, D4). No Amazon account and no wifi needed for the exploit.
- Root access comes first because the OTA window is the only thing here that can close permanently (D5).
- The on-device client shape (FBInk binary versus KOReader plugin) is deliberately undecided until phase 2 reports (Q3: defer).
- Claude runs on the $20/month Pro subscription and no API-billed call is acceptable (D6). In practice: drive the Claude Code CLI under subscription auth, never `--bare` and never the Agent SDK with an API key.
- A companion app on the host observes Claude and exposes a socket. Root is available but not the target: it runs as the regular user with least permission (D7).
- klide reads the Claude Code session transcript, one JSONL file per session under `~/.claude/projects/` (D9). Message-level granularity accepted.
- klide is read-only toward Claude (D11). Touch navigates klide's own views and never writes to the session, so the README's "minimal feedback" idea is dropped and phase 5 is navigation only.
- The companion app is Python (D10).
- Tailscale is already in the stack, so host and Kindle do not need to share a LAN (D8).

## Phases

| #  | Phase                    | Plan                                            | Status  |
| -- | ------------------------ | ----------------------------------------------- | ------- |
| 1  | Root access              | [`01_root_access.md`](01_root_access.md)        | in progress |
| 2  | Display and input spike  | [`02_display_spike.md`](02_display_spike.md)    | planned |
| 3  | Frame transport          | [`03_frame_transport.md`](03_frame_transport.md)| planned |
| 4  | Host renderer and views  | [`04_host_renderer.md`](04_host_renderer.md)    | planned |
| 5  | Touch navigation         | [`05_touch_navigation.md`](05_touch_navigation.md)  | planned |

Status values: draft / planned / in progress / done / superseded / discarded.

## Log

Append-only. Newest at the bottom.

- 2026-09-03 : initial web research on Kindle jailbreaks, e-ink display paths, prior art and alternative vendors; written up in `00_start.md`
- 2026-09-03 : inspected the device over USB. `system/version.txt` reads `Kindle 5.14.1.1 (378310 001)`, no staged update files anywhere on the volume. Confirms LanguageBreak is the applicable exploit
- 2026-09-03 : converted the research note into a tracked plan folder; derived five phases, recorded decisions D1-D5 and open questions Q1-Q7. Q1 (how klide observes Claude) is unresearched and is the largest gap
- 2026-09-03 : reviewed the freshly written phases. Verified the PW5 panel is 1236x1648 (used in phase 4). Found one missing pitfall: the factory reset drops into the setup wizard, which asks for wifi, and that is the likeliest moment for an accidental connection; added to phase 1 as a risk and a pre-read step. No other corrections
- 2026-09-03 : constraints arrived from the user - Claude runs on the $20/month Pro subscription with no API cost permitted, a companion desktop app drives the Claude CLI and exposes a socket, the host has root privileges available, and Tailscale is already in the stack. Recorded as D6-D8; folded Q1 and Q4
- 2026-09-03 : researched how the companion app can observe Claude without API billing. Found that `claude -p --output-format stream-json` runs on subscription auth but `--bare` does not (it requires ANTHROPIC_API_KEY), and the Agent SDK requires API-key auth - so the earlier Q1 recommendation was wrong under the cost constraint. Verified on this machine that Claude Code writes a per-session JSONL transcript to `~/.claude/projects/<slug>/<session-id>.jsonl` with user/assistant/thinking/tool_use records. Four options written up as Q8
- 2026-09-03 : split the plan folder. `00_initial` keeps research, decisions and questions only; the five execution phases and this tracking file moved to `01_implementation`. Applied the accepted add/remove items: recovery section in phase 1, host-side simulator merged into phase 4, networking section trimmed, frame wire format recorded under deferred decisions
- 2026-09-04 : folded the Q2-Q9 answer batch. Jailbreak tries 5.14.1.1 directly first; on-device client shape deferred to the spike; KOReader stays; no hardware fallback is planned if rooting fails (the project stops instead); ingestion is transcript tailing at message-level granularity (D9); host app is Python (D10). D7 relaxed to least-permission regular user, which D9 makes trivial
- 2026-09-04 : folding Q8=a surfaced a consequence the option list had noted but the plan had not absorbed - transcript tailing is read-only, so phase 5 splits into navigation (works now) and answering Claude (needs a write path). Raised as Q10; phases 3 and 4 promoted from draft to planned now that nothing gates them
- 2026-09-04 : Q10 answered - klide stays read-only toward Claude (D11). Phase 5 loses its answering half and becomes touch navigation only; promoted to planned. All open questions are now answered and every phase is planned
- 2026-09-04 : reviewed the plan now that every question is answered. Renamed phase 5's file to `05_touch_navigation.md` to match its rescoped title. Found one contradiction: this file's summary paragraph still promised touch feedback after D11 removed it; corrected. No other findings
- 2026-09-04 : phase 1 started. Backed up the irreplaceable USB volume contents to an external location (books, `.sdr` sidecars, annotation logs, vocabulary, collections, fonts), verified by per-file SHA-256 in both directions. Skipped the regenerable bulk after measuring it: voice data, trash, indexes and caches are most of the volume
- 2026-09-04 : corrected the phase 1 backup step, which said to copy the entire volume because "the copy is free". Measurement showed the unique data is a few MB against a much larger volume. Two findings recorded in the phase file: rsync exited 0 having copied no sidecars because the filter did not include the intermediate author directories (caught only by checksum comparison), and `system/thumbnails` holds zero-byte `*.partial` placeholders that will false-positive a naive staged-update search
- 2026-09-04 : read the LanguageBreak walkthrough end to end. Confirmed the whole procedure runs with no network and no Amazon account: airplane mode ON is a stated prerequisite, the setup wizard's wifi step is dismissed by selecting a network and backing out, and demo mode setup takes fake information. The phase 1 risk about the setup wizard is resolved. Recorded the procedure's shape in the phase file, including the one timing-critical step (replug to the host the moment the "press power button" message appears during Resell Device) and the `;uzb` / `;dsts` hotfix sequence
- 2026-09-04 : re-checked the 5.14.3 lower bound. The upstream repo states no lower bound, only "5.16.2.1.1 or lower", and says the exploit works best around 5.16.2. The gitbook page title reads as a tested range rather than a floor, so the risk at 5.14.1.1 is reliability not incompatibility. Corrected the claim in the research file; it supports Q2's answer of trying directly first
