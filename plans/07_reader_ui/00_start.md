---
status: draft
---

# The reader UI - bootstrap

## Where this came from

An interview on 2026-09-19, run by hand because the `/grill-me` skill in
[`../05_grill_me/00_start.md`](../05_grill_me/00_start.md) is still a draft with no `SKILL.md`.
Two rounds of questions across the frontier, ending here, which is what GD2 in that folder says an
adapted version should do. Whether the skill is worth writing is G4, and this sitting is the first
evidence either way.

The input was a four page specification, given in full, plus a request to check whether the Agent
Host Protocol applies. The six views in [`../../src/klide/views.py`](../../src/klide/views.py) were
built from the rough list in [`../02_kobo/01_ui_ux.md`](../02_kobo/01_ui_ux.md) and have never been
arranged into anything a person can walk. This folder is that arrangement, and the data behind it.

## The four pages, as specified

1. **Conversation selector.** A list, no bullets. Each row carries the name Claude exposes, the repo,
   and the state: needs input, unread since Claude wrote, other. Tap a row for page 2.
2. **Conversation.** A recap at the top with the name, the repo, the current branch and the git diff
   totals. The body is the conversation, scrolling. Tap the diff totals for page 3.
3. **Diff explorer.** The same recap. The body is a tree of folders listing only the files the diff
   touches, scrolling. Tap a file for page 4.
4. **One file's diff.** The top is the file path alone, trimmed from the left when too long. The body
   is the diff rendered inline.

On every page, a control in the top right returns to the page you came from.

## What the Agent Host Protocol is, and whether it applies

[AHP](https://github.com/microsoft/agent-host-protocol) is Microsoft's, published in August 2026.
A standalone host process owns agent sessions and synchronises their state to any number of clients
over JSON-RPC: an initial snapshot, then ordered action envelopes against immutable per-channel
state. VS Code is the reference server. The published client list covers Rust, TypeScript, Kotlin,
Swift and Go.

Claude Code is not among them. Checked on this box against 2.1.273: nothing in `claude --help`
mentions AHP, an agent host or a sessions server, and the protocol's own implementations page lists
no Anthropic anything. So there is no host to connect to and an extractor has to exist either way,
which was the premise the question was asked under.

What is worth taking is the state model, because it already names every field these four pages need
and it was designed by people who had the same problem:

| what the pages need | AHP calls it |
| --- | --- |
| conversation name | session `title` |
| repo | session `project`, `workingDirectories` |
| the state column | `SessionStatus`, a bitset of `Idle` 1, `Error` 2, `InProgress` 8, `InputNeeded` 24, `IsRead` 32, `IsArchived` 64 |
| the conversation body | chat `turns`, with `activeTurn` and `queuedMessages` |
| pages 3 and 4 | `changesets`, each a `changeKind` and a list of files |

Two of those settle arguments this repo was about to have. `IsRead` is "unread since Claude wrote",
which the specification named and no local source reports. `changeKind` is the distinction between
an uncommitted diff, a session diff and a branch diff, which is the question page 3 cannot avoid.

## What the extractor has to work with

Three sources, all local, all verified on 2026-09-19.

- `claude agents --json` runs without a TTY and returns an array of live sessions. Observed fields:
  `pid`, `cwd`, `kind`, `startedAt`, `sessionId`, `name`, `status`. Five sessions at the time,
  across four repos. This is page 1's list, the repo and the identity, at no cost to us.
  The only `status` values seen were `idle` and `busy`; nothing in it reports needing input or being
  unread, so those come from elsewhere.
- The transcripts under `~/.claude/projects/<slug>/*.jsonl`, already read by
  [`../../src/klide/transcript.py`](../../src/klide/transcript.py) and watched live by
  [`../../src/klide/live.py`](../../src/klide/live.py). This is page 2's body and the evidence for
  the derived states.
- `git` in the session's `cwd`, for the branch, the totals and the per file diffs.

## What page 3 would show today

Nothing. This repo's tree is clean and `origin/main...HEAD` is 0 and 0, so every reading of "the git
diff" is empty on the repo being actively worked in. That is not an argument against the page; it is
the reason UD5 had to be decided rather than assumed, and the reason the empty state is part of the
page rather than an afterthought.

## The model this replaces

[`../02_kobo/01_ui_ux.md`](../02_kobo/01_ui_ux.md) carries a provisional gesture map in which a swipe
up or down switches view and a tap on the centre opens whatever a cursor sits on. That is a carousel
of peers. The specification above is a hierarchy with a return path, and the two cannot both be true
about where a reader is. The gesture map loses, and says so; it was marked provisional twice in its
own text and this is what it was waiting for.

## Decisions

* **UD1. Take AHP's data model, not its transport.** The extractor's output uses AHP's names and
  shapes, so a session has a `title`, a `project` and a status bitset, and a changeset has a
  `changeKind`. Nothing speaks JSON-RPC, there are no action envelopes and there is no reducer.
  Rejected: hosting a real AHP server, which buys multi client synchronisation that one Kobo and one
  browser viewer do not need, and would land on the Lua client as a JSON-RPC implementation or a
  replacement for `KLD2`. Also rejected: naming the fields ourselves, which costs the same to write
  and drifts from the one published vocabulary for exactly this data. If Claude Code ever ships an
  AHP server the source swaps behind the same types, which is the whole reason to pay the naming tax.
* **UD2. Navigation is a stack of four pages.** Down by tapping, up by the back control. Where the
  reader is, is the path they took. This supersedes the swipe carousel in `02_kobo/01_ui_ux.md` for
  the reader UI. What it costs is the quick hop, since returning from a diff to the conversation is
  two steps rather than one.
* **UD3. A tap opens the row under it.** The wire already carries a tap with panel coordinates
  ([`../../src/klide/input.py`](../../src/klide/input.py)), and the host laid the page out, so the
  host knows which row a y coordinate landed in. No cursor state on either side.
  Rejected: a highlight moved by the physical buttons, which costs a panel refresh for every row
  crossed.
* **UD4. The physical buttons always scroll the current page.** One meaning on all four pages: rows
  on 1 and 3, the conversation on 2, the diff on 4. It stays answerable from the device cache, which
  is what makes paging feel immediate, and it does not change with scroll position.
* **UD5. The diff is what is uncommitted.** Working tree plus index against `HEAD`, which is what
  `git diff` means to a person. The cycle through `changeKind` values is wanted and deferred, not
  rejected; it is recorded as U6 rather than built now.
* **UD6. Page 1's states are derived from the transcript, and what is derived is logged.** The CLI
  reports two states and the specification asks for two more. The derivation is a rule about the last
  turn, so it will be wrong sometimes, and a rule that is sometimes wrong and silent is the pattern
  the diary review named as the recurring cost. It says what it concluded and from which turn.
* **UD7. Page 1 updates in place; pages 3 and 4 hold still and say when they are stale.** The session
  list is the reason to glance at the device, so its state column is live. A diff that repaints while
  it is being read is the worst case for e-ink, and a file can leave the changeset entirely while
  page 4 is showing it. Holding still silently is no better, so both pages carry a marker when the
  underlying changeset has moved since they were drawn. Page 2 keeps the behaviour it has, live at
  the tail and frozen once the reader pages back.
* **UD8. Page 3 is a tree, and it absorbs two existing views.** `changed_files` is a flat list with
  counts and `file_tree` is a tree of every path; page 3 is a tree of only the touched paths with the
  counts on the row. Both are replaced rather than kept alongside, so there is one thing to gate.
* **UD9. The stale marker on pages 3 and 4 is the refresh control.** Tapping it redraws the page from
  the current changeset. This costs no room in the top strip, which is spoken for by the back
  control, and it puts the control where the reader is already looking when they want it. The marker
  is then never a dead end: the page that says it is out of date is also the way to fix it. What it
  constrains is the marker's size, since something to be tapped has a minimum that something to be
  read does not.

* **UD10. The diff totals are the only tappable thing in the recap.** The name, the repo and the
  branch are text on every page. The alternative, a recap that always opens page 3, makes the recap
  on page 3 a link to itself, and a region that is live on one page and inert on the next is learned
  the hard way.
* **UD11. The back control shares the recap's line.** Top right, on every page, on the same line the
  recap starts on, so it costs no vertical space of its own. No strip is reserved for it, which was
  the recommendation and is not what was chosen. What it constrains is the recap's first line: it
  ends where the control begins, so the name and the repo have a shorter line than the ones under
  them, and page 4's trimmed-from-the-left path is trimmed against that shorter width.
* **UD12. Read is per host, per session, and tapping in marks it read.** The device holds no durable
  state (K5), so the marker lives with the extractor. Marking on arrival rather than on reaching the
  bottom: a session opened and glanced at is a session read, and the rule that needs no scroll
  tracking is the one to start with.

## Open questions

Numbered `U` for this folder, continuing across batches.
Answered on 2026-09-19, in the second sitting.

- U1: What the recap at the top of pages 2, 3 and 4 is tappable for, beyond the diff totals on page 2.
  Tapping the recap on page 3 has no obvious destination, and a region that is tappable on one page
  and inert on the next is the kind of inconsistency a reader learns the hard way.
  a. only the diff totals on page 2 are a target, everything else in the recap is inert everywhere
  b. the recap is a target on every page and always goes to page 3
  Recommended: a, because b makes the recap on page 3 a link to itself.
  NEW_ANS: a. The diff totals on page 2 are the only target in the recap. Everything else in it is
  text on every page. Recorded as UD10.
- U2: Whether the back control occupies a reserved strip on every page, and what that costs.
  A fixed row at the top is the easiest thing to aim at and the easiest to keep consistent, and it
  spends vertical space on all four pages on a screen where the body is the point.
  Recommended: reserve it, measure what it costs in lines, and revisit if it is more than two.
  NEW_ANS: On every page, and on the same line as the top of the recap so it costs no vertical
  space of its own. Not the recommendation: no strip is reserved. Recorded as UD11, with what it
  constrains.
- U3: Where the read marker lives and when a session counts as read. Per session, on the host, since
  the device holds no durable state (K5). Whether arriving at page 2 marks it read immediately, or
  only once the reader reaches the bottom, is the part with a real answer either way.
  NEW_ANS: Per host, per session, and tapping into a conversation marks it read. The simple rule
  on purpose. Recorded as UD12.
- U4: How often the extractor runs, and whether a subprocess per poll is acceptable.
  `claude agents --json` is a process launch; the transcripts are files that can be watched. A
  plausible shape is watching the files continuously and running the CLI on a slower cadence.
  Recommended: measure what the call costs before designing around it.
  NEW_ANS: Measure it. The cadence is chosen from the measurement in phase 1, not before it.
- U5: What happens to `one_file`, the sixth view. The four pages leave it with no route, and "open
  the whole file, not just its diff" is a natural page 5 rather than a view to delete.
  Recommended: leave it in place, unrouted, until someone wants it.
  NEW_ANS: Left in place, unrouted. Browsing the whole repo, which is what would give it a route,
  is deferred with it.
- U6: When the `changeKind` cycle arrives, and what control moves it. Wanted per UD5, and it needs a
  target on a screen whose top strip is already spoken for by the back control. The stale marker
  solved the same problem by being its own control (UD9), which may or may not generalise: a marker
  appears when there is something to say, and a scope cycle has to be there before the reader knows
  they want it.
  NEW_ANS: Deferred, and not implemented now. One change kind is shown, the one since the last
  commit, which is UD5. No control is designed for a cycle that does not exist yet.
- U7: Whether all four pages are served by the loop in
  [`../../src/klide/serve.py`](../../src/klide/serve.py), which today knows only the conversation,
  or whether navigation sits above it. This decides where the stack's state lives.
  NEW_ANS: Assess rather than pick, which is below. The assessment recommends one loop with three
  hooks, and it is a recommendation, not yet a decision.

## U7 assessed: what the serve loop actually knows

Read at 2026-09-19 against `src/klide/serve.py` as committed at `85a1821`.

`run()` does four things in its loop. Three of them have nothing to do with which page is on screen:

- drain the input queue and stop when the reader thread posts `None`
- ask a `Coalescer` whether a burst of changes has settled
- render, take a `dirty_rectangle` against the previous frame, pick a waveform, send, and treat a
  dead socket as the end of the session rather than a fault

The fourth is page specific and there are exactly three places it shows:

| place | today | what a stack needs |
| --- | --- | --- |
| the source being polled | one `Follower` over one transcript | whichever source the current page reads |
| `apply_event` | `LiveState.page_back` / `page_forward` / tap returns to the tail | the current page's handler, plus push and pop |
| `render` | `fill()`, hardwired to `conversation` | the current page's own |

So the recommendation is one loop with those three turned into calls on whatever is on top of the
stack, and `LiveState` demoted from "what the viewer is looking at" to the conversation page's own
state. The stack itself lives in a new object between `run` and the pages, which is the answer to
where the navigation state goes: not in `LiveState`, not in `run`.

Two things checked rather than assumed, because the objection to one loop would be that a page
change is not the same kind of update as a new turn:

- A page change does not need a new refresh mechanism. `pick_waveform` already returns `GC16` once a
  patch covers three quarters of the panel, and a whole new page always will, so the full refresh a
  page change wants is what it already gets.
- The three shared jobs are not trivial to duplicate. The coalescer has two limits because either
  alone behaved badly, and the socket handling says which of three endings happened because it once
  said none of them. A loop per page would copy both, or drift from them.

What is not settled by this: whether the back control is an event the stack handles or a page's own,
and whether a page that has been popped keeps its scroll position when it is pushed again. Both are
phase 2's to answer with code in front of them.
