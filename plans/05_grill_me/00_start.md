---
status: draft
---

# grill-me - bootstrap

## Where this came from

A detour during the meta track, parked here rather than worked now. The question asked was how an
outside skill, `/grill-me` from aihero.dev, would fit this repo's way of planning. It is a third
outside source after pstack and deslopify, so it belongs to the meta track's adoption question
([`../03_meta/00_start.md`](../03_meta/00_start.md), M1) and the record in
[`../../meta/adoption.md`](../../meta/adoption.md). It is a sibling folder rather than a meta phase
because it is executable on its own later and nothing in the meta track waits on it.

Source read on 2026-09-17: <https://www.aihero.dev/skills-grill-me>. The page describes the skill,
it does not publish the `SKILL.md`, so the body would be written here rather than copied.

## What the skill is

An interview loop. Invoked by name in a fresh conversation with a loose idea, it questions the user
in rounds, each round covering the whole frontier of unresolved questions so that nothing is asked
before its prerequisite is answered. Explicitly stateless: no files, no workspace artifacts. The
stated success criterion is friction, "a session with no pushback from you is a session you didn't
need", with passive agreement named as the failure that produces confident nonsense. It is not
code specific.

Two siblings on the same page: `grill-with-docs` grills against a codebase, `wayfinder` handles an
idea too large to grill directly.

## Where it fits here

It fills a gap that already has a name: `00_start.md`. The `tracked-development` skill says what a
bootstrap file contains, the idea, the analysis, the decisions with their rejected alternatives and
the open questions, but not how to get from a vague note to one. It assumes the idea already has
enough shape to write down. The interview is the step before that.

The `Q`/`NEW_ANS` convention is not a competitor. The two halves split by latency:

| | interview | `Q`/`NEW_ANS` |
| --- | --- | --- |
| where | chat, synchronous | file, asynchronous |
| when | before the plan exists | while the plan is being folded in |
| batch | one round, answered now | a batch left for the user to fill in later |
| record | none, as published | permanent, the decision record |

## The conflict

Statelessness is wrong for this repo. The premise of tracked development, and of the `encode lessons
in structure` principle in [`../../.claude/skills/principles/SKILL.md`](../../.claude/skills/principles/SKILL.md),
is that reasoning lives on disk because context does not survive a `/clear`. A grilling session that
produces firm decisions and then evaporates is the failure both were written against.

The adaptation is to keep the round mechanism and drop the statelessness. The terminating condition
of the interview is writing `00_start.md`: the decisions with the rejected alternatives that surfaced
during the rounds, and every question that did not resolve emitted as a numbered `Q` with a
recommendation above an empty `NEW_ANS:` slot. That last part is the seam. The interview hands its
leftovers to the existing fold-in loop in the format that loop already reads.

## Decisions

* **GD1. Take the interview, adapted, as its own skill.** Invocable by name, usable for work that is
  not multi-phase. The rejected alternative was a "phase 0: interview" section inside
  `tracked-development`, which loads no extra description but is only reachable once the work is
  already known to be multi-phase, which is the thing the interview is there to determine.
* **GD2. Not stateless.** The interview ends by writing `00_start.md`, per the conflict above. This is
  a deliberate departure from the source, not an oversight in porting it.
* **GD3. Unresolved questions leave as `Q` + `NEW_ANS`.** The interview does not press for an answer
  to everything in one sitting. What survives the rounds unanswered becomes the first question batch.
* **GD4. Reject both siblings, for the reasons already used in `adoption.md`.** `grill-with-docs`
  needs a codebase to ground in, which is the same reason `how`, `why` and `recall` were rejected.
  `wayfinder` overlaps the rule tracked development already carries, that a folder holding more than
  roughly five sub-plans is probably two features.

## Cost

One more skill description loaded into every session, on the order of the 60 words `principles`
costs. The body loads only on invocation. The accounting is the same as the one in `adoption.md`.

## Open questions

Numbered `G` for this folder, continuing across batches.

- G1: Does the interview write `00_start.md` itself, or hand back a draft in chat for the user to
  place. Writing it directly matches GD2 and leaves nothing to lose on a `/clear`; handing it back
  keeps a bad interview from creating a folder that then has to be deleted.
  a. write the folder and `00_start.md` at the end of the rounds
  b. write nothing until the user says where it goes
  Recommended: a, because the case the skill exists for is an idea vague enough that the user does
  not yet know it deserves a folder, and a draft folder is cheap to discard.
  NEW_ANS:
- G2: Where the skill lives. The repo's `.claude/skills/` like `principles` and `deslopify`, or
  `~/dotfiles` like the symlinked ones, given it is project independent by design.
  a. repo, and lift it out later if it earns it
  b. dotfiles from the start, shared across every repo on this box
  Recommended: b, because unlike `principles` nothing in it is specific to klide, and the meta
  track's MD2 says these artifacts are meant to be lifted out anyway.
  NEW_ANS:
- G3: Whether the rounds have a stopping rule, or run until the user stops them. The source does not
  say. A fixed count is easy to gate on and easy to make useless.
  NEW_ANS:
- G4: Whether this needs the `skillify` treatment rather than being written cold. `skillify` triages
  on a refinement arc, something that failed and was corrected, and this has none: it is an outside
  pattern being ported, closer to the pstack and deslopify path.
  Recommended: write it cold, following the `adoption.md` pattern, and add the third-source row there.
  NEW_ANS:
- G5: Does it reuse the interaction under review in MD4. The interview is a specific interaction
  shape, and the meta track's phase 3 is about the interaction contract. If they overlap, this folder
  might be an input to that phase rather than a standalone skill.
  NEW_ANS:
