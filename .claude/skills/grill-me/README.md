# Where this came from

Source: [grill-me](https://github.com/mattpocock/skills/tree/HEAD/skills/productivity/grill-me),
Matt Pocock, MIT. Read at the source on 2026-09-19, along with
[grilling](https://github.com/mattpocock/skills/tree/HEAD/skills/productivity/grilling), which holds
the body it delegates to. The write-up that led here is
[aihero.dev/use-the-grill-me-skill](https://www.aihero.dev/use-the-grill-me-skill-k029d).

The third outside source taken into this repo, after
[pstack](https://github.com/cursor/plugins/tree/main/pstack) and
[deslopify](https://github.com/JuliusBrussee/skills). The accounting for all three is in
[`meta/adoption.md`](../../../meta/adoption.md).

## Taken unchanged

The mechanism, which is the whole point of it: a design tree, a frontier of decisions whose
prerequisites are settled, one round covering the whole frontier, numbered questions each carrying a
recommendation, and a stopping rule that is an empty frontier rather than a question count. Also the
rule that facts are the agent's job and decisions are the user's, and the warning that a session with
no pushback in it was not worth having.

## Changed

- **It is not stateless.** The source leaves no artifact by design. Here the interview ends by
  writing `plans/NN_<slug>/00_start.md`, and anything unresolved leaves as a numbered question with
  an empty `NEW_ANS:` slot. Reasoning that lives only in a conversation does not survive a `/clear`,
  which is the premise of the plan folders and of the `encode lessons in structure` principle.
- **One skill, not two.** Upstream splits `grill-me`, a stub carrying
  `disable-model-invocation: true`, from `grilling`, which holds the body. That buys explicit
  invocation only. Here it is one skill, because every skill's description is loaded into every
  session and two descriptions would buy nothing this repo needs.
- **No emoji in a round.** The upstream format uses question and arrow emoji with rules between
  questions. The house writing rules ban emoji, so rounds are numbered plainly.
- **`AskUserQuestion` is named as the format for enumerable answers.** Not in the source. It is here
  because the interview this skill was written from was answered from a phone, where tappable options
  are the difference between an answer and a shrug.
- **No sub-agent dispatch.** The source says to send a sub-agent after environment facts. This repo's
  instructions say not to spawn agents unless asked, so the facts get found inline. Nothing is lost
  except parallelism, and a round is only as slow as its slowest lookup.

## The other grill-me

[JuliusBrussee/skills](https://github.com/JuliusBrussee/skills) carries a skill of the same name, and
it is a different design rather than a copy. Read on 2026-09-19 by cloning the repo, after the
version above was already adapted. Recorded here because someone looking for the source of this skill
will find two, and because the two disagree about something real.

| | Pocock | Brussee |
| --- | --- | --- |
| batching | the whole frontier in one round | one question at a time |
| structure | a design tree, recomputed each round | a decision map with fixed slots and a seven rung ladder |
| stopping | the frontier is empty | the plan has a goal, constraints, an approach, validation and a next step |
| calibration | none | knowledge level and pressure level, both adjustable mid-session |
| per question | a recommended answer | a recommended answer and one line of why it matters |
| ending | nothing, stateless by design | a spoken summary of plan, open questions, next action and risks |

The batching difference is the one that matters and this skill keeps Pocock's, because a round of
four tappable questions is one thing to answer from a phone and four separate turns is four. The
ladder is the part of Brussee's worth stealing and it is assessed in
[`meta/adoption.md`](../../../meta/adoption.md) rather than taken quietly.

## Not taken

`grill-with-docs`, which grills against a codebase, for the same reason `how`, `why` and `recall`
were rejected from pstack: it needs a history to ground in. Revisit when there is more of one.

## Whether it earns its place

It was run by hand before it was written, on the reader UI, on 2026-09-19. Two rounds, eight
questions, and the record is `plans/07_reader_ui/`. Three of the eight changed the design rather than
confirming it, and one round found a fact that removed a question entirely, which is the behaviour
the skill exists to repeat.
