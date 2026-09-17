# meta layer tracking

Learning to orchestrate unsupervised agent work, and keeping the agents, skills, instructions and
experiment records in the repo as a deliverable. Analysis and decisions in [`00_start.md`](00_start.md).
The app being built alongside is tracked in [`../04_klide_app/00_start.md`](../04_klide_app/00_start.md).

## Key decisions

- Two tracks, separately tracked: the meta layer here, the app in `04_klide_app` (MD1).
- The user's side of the conversation trends toward what the thing must do; gates carry the technical calls (MD3).
- The interaction itself is under review, on a cadence, looking for painful exchanges (MD4).
- Tracked development is scaffolding for the bootstrap phase and is expected to change shape (MD7).
- pstack is read and cherry-picked, not adopted. Claude Code is the only harness (M1: b, M3).
- Concurrency is the last dial to turn: one agent, sometimes two, in worktrees, until the interactions hold (MD8, M9).
  Cloud sessions are available on this plan with no compute charge, and stay in the background until something needs them.

- The unsupervised boundary is whatever needs no GitHub credentials, which this box enforces by not having any (MD9).
- The frame is the evidence, and the simulator exists to produce it (MD10).
- A third outside source, the `/grill-me` interview, is spun off to [`../05_grill_me/00_start.md`](../05_grill_me/00_start.md) (MD11).

## Phases

| #  | Phase                   | Plan                                                      | Status |
| -- | ----------------------- | --------------------------------------------------------- | ------ |
| 1  | Adopt practices         | [`01_adopt_practices.md`](01_adopt_practices.md)           | done |
| 2  | Guardrails              | [`02_guardrails.md`](02_guardrails.md)                     | done |
| 3  | Interaction contract    | [`03_interaction_contract.md`](03_interaction_contract.md) | planned |
| 4  | Diary and session review| [`04_diary_and_review.md`](04_diary_and_review.md)         | planned |
| 5  | First unsupervised run  | [`05_unsupervised_run.md`](05_unsupervised_run.md)         | planned |

Status values: draft / planned / in progress / done / superseded / discarded.

## Log

Append-only. Newest at the bottom.

- 2026-09-15 : researched Lauren Tan's pstack and the recaps of her Cursor agent talk; bootstrapped this folder with the two-track split, decisions MD1-MD7 and open questions M1-M8. No phase started, and every phase is `draft` until the M batch is answered
- 2026-09-16 : answered how her method meshes with a greenfield project, that her own repo ships a multi-phase plan playbook and that the disagreement is about resolving technical forks in prose rather than about direction; checked what "each agent its own machine" costs here, and found Claude Code cloud sessions run an isolated VM per session on this plan with no separate compute charge. Folded in M9: worktrees for now, GitHub App kept in the background. Added MD8, start at one or two agents and increase slowly
- 2026-09-16 : folded in the M1-M10 batch. pstack is cherry-picked not adopted, Claude Code only, meta artifacts split between harness-native paths and `meta/`, the unsupervised boundary is what works without GitHub credentials (MD9), the frame is the evidence (MD10), and the review cadence is deliberately flexible. All five phases move from draft to planned
- 2026-09-16 : phase 1 started. Cloned pstack and read it at the source. Took four principles (prove it works, build the lever, sequence verifiable units, encode lessons in structure) as one skill at `.claude/skills/principles/`, deferred four things with a trigger each, rejected the rest with reasons in `meta/adoption.md`. Review before executing found one wrong claim in the phase plan: skill bodies are not charged every session, only descriptions are, which is why the four principles are one skill rather than four. Outstanding: confirming the skill registers, which needs a fresh session
- 2026-09-16 : took a second outside skill, deslopify, and adapted it into `.claude/skills/deslopify/` with a runnable scanner over per-category pattern files. Folded the mannered-writing idea into the repo's writing rules: prose is a window onto the subject rather than a performance, with Pinker's classic style, Oppenheimer 2006 and the guru effect as the why. Checked the other repos on this box for anti-slop sections worth harvesting and found they carry the same section as this one. The scanner found its own class of false positive, a file that catalogs the banned words matching its own catalog, documented rather than coded around
- 2026-09-16 : ran the deslopify scan over every plan file and rewrote the findings that survived triage. Removed two words the repo's own rules ban, "load-bearing" and "bites", four punchline fragments, and five reveal constructions of the "not X, but Y" shape. The remaining 26 findings are all triaged and kept: genuine lists of three distinct things, and real ranges the "from X to Y" pattern cannot tell from rhetorical ones. The cadence check was fixed during the pass, because it counted runs across paragraph and list boundaries and so fired on every structured document; it now requires a run inside one paragraph, checked against a file written to trip it
- 2026-09-16 : phase 2 done. Three stack-independent gates behind `scripts/check.sh`, called unchanged by the CI workflow: link resolution, agreement between phase frontmatter and tracking tables, and the banned writing rules. Each was demonstrated failing before being counted. The link gate found a real broken link on its first run and then crashed on it, because the bug was in the code that formats a finding and no passing run reaches it. Spellcheck dropped (no node on this box) and commit message shape dropped (no failing case anyone has hit). The contract and the empty slots for the app track are in `meta/gates.md`
- 2026-09-16 : confirmed that a skill written during a session does not register until the next one. Invoking `principles` mid-session returns "Unknown skill". Phase 1 stays in progress for that reason alone
- 2026-09-16 : reversed the enforcement decision from phase 2. The argument against a pre-commit hook was that it is bypassable, which only holds when CI runs, and CI has never run because this box has no GitHub credentials. Added `.githooks/pre-commit` calling the same `scripts/check.sh`, shared through `core.hooksPath` and installed by `scripts/install-hooks.sh`. Verified that a commit carrying a banned em dash is refused with no commit object written, and that a clean tree commits normally

- 2026-09-16 : phase 1 done. A fresh session ran the four checks the phase was waiting on: `principles` and `deslopify` both appear in the skill list, `principles` invokes and returns its four rules; the repo instructions carry the Planning section and the mannered-writing paragraphs; `scripts/check.sh` passes cold on 32 files with no findings. Nothing was wrong, so the phase closed unchanged
- 2026-09-17 : detour, no phase touched. Asked how aihero.dev's `/grill-me` would fit this repo's planning; found it fills the undocumented step before `00_start.md` and that its statelessness contradicts the reason the plan folders exist. Spun the reasoning and five open questions off to `05_grill_me/` as a draft, parked
