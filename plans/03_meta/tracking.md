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

## Phases

| #  | Phase                   | Plan                                                      | Status |
| -- | ----------------------- | --------------------------------------------------------- | ------ |
| 1  | Adopt practices         | [`01_adopt_practices.md`](01_adopt_practices.md)           | planned |
| 2  | Guardrails              | [`02_guardrails.md`](02_guardrails.md)                     | planned |
| 3  | Interaction contract    | [`03_interaction_contract.md`](03_interaction_contract.md) | planned |
| 4  | Diary and session review| [`04_diary_and_review.md`](04_diary_and_review.md)         | planned |
| 5  | First unsupervised run  | [`05_unsupervised_run.md`](05_unsupervised_run.md)         | planned |

Status values: draft / planned / in progress / done / superseded / discarded.

## Log

Append-only. Newest at the bottom.

- 2026-09-15 : researched Lauren Tan's pstack and the recaps of her Cursor agent talk; bootstrapped this folder with the two-track split, decisions MD1-MD7 and open questions M1-M8. No phase started, and every phase is `draft` until the M batch is answered
- 2026-09-16 : answered how her method meshes with a greenfield project, that her own repo ships a multi-phase plan playbook and that the disagreement is about resolving technical forks in prose rather than about direction; checked what "each agent its own machine" costs here, and found Claude Code cloud sessions run an isolated VM per session on this plan with no separate compute charge. Folded in M9: worktrees for now, GitHub App kept in the background. Added MD8, start at one or two agents and increase slowly
- 2026-09-16 : folded in the M1-M10 batch. pstack is cherry-picked not adopted, Claude Code only, meta artifacts split between harness-native paths and `meta/`, the unsupervised boundary is what works without GitHub credentials (MD9), the frame is the evidence (MD10), and the review cadence is deliberately flexible. All five phases move from draft to planned
