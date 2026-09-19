# What we took from pstack, and what we did not

Source: [pstack](https://github.com/cursor/plugins/tree/main/pstack), Lauren Tan, MIT.
Read at the source on 2026-09-16, not through the recaps. 47 skills, 23 of them one principle each,
23 playbooks, 2 subagents, 1 dormant automation pack, around 172 KB of skill text.

The decision was M1: cherry-pick, do not adopt. The filter is this repo's situation.
It has no source code, no history to trace, one or two agents at a time (MD8), and a product whose
evidence is a rendered frame (MD10). Most of pstack is built for the opposite case, a large codebase
with a long history and many agents, and it is good work that does not apply here yet.

## Taken

Four principles, in [`.claude/skills/principles/SKILL.md`](../.claude/skills/principles/SKILL.md),
rewritten for this repo rather than copied.

| principle | why this one |
| --- | --- |
| prove it works | the whole reason the simulator exists. Without it MD10 is a slogan. |
| build the lever | the frame comparison, the gates and the simulator are all levers; this names the habit. |
| sequence verifiable units | the app track is five phases of multi-step work, which is exactly the failure case. |
| encode lessons in structure | the meta track's entire output is supposed to be mechanisms, not more prose. |

They are one skill rather than four, because Claude Code loads every skill's description into every session
and only loads a body when the skill is invoked. Four skills would cost four descriptions to save nothing.

## Deferred, with a trigger

| thing | trigger |
| --- | --- |
| `create-verification-skill` | app phase 2, when there is an app to verify. The idea is already MD10; the generator is worth revisiting once the frame comparison exists and can be described to a cold agent. |
| `reflect` | meta phase 4. Its shape is three parallel reviewers plus a synthesizer over the transcript, which is more machinery than one or two agents need. The routing idea, every finding becomes a concrete skill edit, is the part to keep. |
| `tdd`, `architect` | when there is code. Both assume a function boundary or a test path exists. |
| `arena`, `swarm` | MD8. Width comes after the interactions hold, and we are at one or two agents. |

## Rejected

| thing | why |
| --- | --- |
| `poteto-mode` and the 23 playbooks | 18.7 KB of router plus a playbook library, written for a mature codebase. MD7 says tracked development is our scaffolding for now. Revisit when there is code to route work over, not before. |
| `how`, `why`, `recall`, `teach`, `blast-radius` | all reconstruct history from git, tickets, chat and observability. This repo has twelve commits and no product. Nothing to trace. |
| `interrogate` | adversarial multi-model review of a diff. Claude Code ships `/code-review` and an ultra multi-agent variant already. Duplicating it buys nothing. |
| `typescript-best-practices`, `unslop`, `no-comments`, `technical-writing`, `bro` | writing and TypeScript specific. The house writing rules are already in `.github/copilot-instructions.md`, and the stack is not chosen. |
| `automate-me`, `setup-pstack`, `make-bot-ui` | Cursor primitives, model panels, and a Grok Bot webhook UI. Either not portable or not wanted. |
| `show-me-your-work` | a committed decision trail. The plan folders and the commit history already are one. |
| the `benny` automation pack | triages Slack issue reports. There is no Slack and there are no users. |

## What it cost

The four principles are one skill. What loads unconditionally is its frontmatter description,
around 60 words. The body, around 2.4 KB, loads only when the skill is invoked.
The alternative considered and rejected was putting the principles in `copilot-instructions.md`,
which would load all of it into every session whether or not the work needed it.

## A second source

[deslopify](https://github.com/JuliusBrussee/skills) by Julius Brussee, taken and adapted on 2026-09-16 as
[`.claude/skills/deslopify/`](../.claude/skills/deslopify/). Taken because it is the one thing that makes the
repo's existing writing rules checkable rather than aspirational: the rules were already written, nothing enforced them.

Two changes from the original. The pattern catalog became runnable: a script over pattern files per category,
so the scan is one command rather than a page of greps to paste. And the house rules became their own category,
since this repo bans em dashes outright where the original only counts their density.

The other repos on this box carry the same "How to write" section as this one, checked on 2026-09-16.
Nothing in them needed folding in, and the script is written to be copied out to them unchanged.

## A third source

[grill-me](https://github.com/mattpocock/skills) by Matt Pocock, taken and adapted on 2026-09-19 as
[`.claude/skills/grill-me/`](../.claude/skills/grill-me/). It fills a step that had a name and no
procedure: `tracked-development` says what a `00_start.md` contains and assumes the idea already has
enough shape to write one. The interview is how it gets that shape.

Taken after running it by hand first, on the reader UI, which is
[`plans/07_reader_ui/`](../plans/07_reader_ui/00_start.md). Two rounds, eight questions, three of
which changed the design. Doing it by hand before writing it down is the same order the deslopify
scanner was built in, and it is the reason the skill says what it says about facts.

The changes from the original are listed in
[`.claude/skills/grill-me/README.md`](../.claude/skills/grill-me/README.md). The one that matters is
that it is not stateless: upstream leaves no artifact by design, and here the interview ends by
writing the plan folder. The sibling `grill-with-docs` is rejected for the reason `how`, `why` and
`recall` were, which is that it needs a history to ground in.

This is a third skill description loaded into every session, on the order of the 60 words the
principles cost. Three sources, three skills, and the ceiling is worth watching rather than assuming:
the cost of a skill is paid every session and the benefit only when it is invoked.

## Reading the second source properly

`deslopify` was taken out of [JuliusBrussee/skills](https://github.com/JuliusBrussee/skills) on
2026-09-16 on the strength of one skill, and the other seven in that repository were never opened.
Cloned and read on 2026-09-19, prompted by finding that it carries its own `grill-me`. Eight skills,
around 73 KB of skill text, MIT.

The two `grill-me` skills are different designs, compared in
[`.claude/skills/grill-me/README.md`](../.claude/skills/grill-me/README.md). Pocock's was already
adapted and stays; what Brussee's has that it does not is assessed below with the rest.

### Proposed, not taken

Nothing in this section is in the repo yet. Each is a proposal with a reason, waiting on a decision.

| thing | what it is | why it fits here |
| --- | --- | --- |
| the question ladder, out of `grill-me` | seven rungs a grilling must eventually cover: goal fit, constraint reality, option pressure, execution path, failure modes, validation, reversibility | our skill says which questions are askable now and nothing says which must be asked eventually. Rungs five to seven are this repo's documented weak spot: the 2026-09-18 review found three phases of green gates over content that never exercised the feature, which is a validation question nobody asked. Cheap to add, since it is a checklist against the tree rather than a change to how rounds work |
| the cardinal rule, out of `last-20-percent` | never call something done until you have consumed its output the way the end user will, where reading your own code and passing tests are both not consuming it | this is the instruction edit the diary review proposed on 2026-09-18 and left unapplied, written better than we wrote it. It is also AD9 restated: the viewer exists because every gate compares klide's output against a reference klide produced |
| golden artifacts, out of `last-20-percent` | hand-craft the best possible instance of what a generator produces, before building the generator, and use it as spec, fixture and quality bar at once | the sharpest thing in the eight. Every reference frame in this repo was generated by the code it gates, which is exactly the weakness AD9 names and the reason a person reading a screen found the 6.2 pt text and the unrendered markdown. A hand-made reference page, laid out by a person and committed, would be the first check here that is not self-referential |
| the scene list, out of `last-20-percent` | decompose the moment of use, not the noun, and treat the residue as the real work: first-run and empty states, defaults, the failure experience, microcopy | `plans/07_reader_ui/` is a noun list. Page 3 shows nothing at all on this repo today, and that was noticed while writing the plan rather than designed for. The empty changeset, the first connection, and what page 4 does when its file leaves the diff are all scene-list items |

### Deferred, with a trigger

| thing | trigger |
| --- | --- |
| `loop-factory` | meta phase 5. A spec-driven loop of inbox, active and archive with a review gate before anything counts as done, which is the shape the first unsupervised run needs. MD7 says tracked development is the scaffolding for now, so this is what to compare against when that starts to chafe |
| the trip protocol, out of `context-canary` | whenever compaction loses something that costs a correction. The checkpoint, re-anchor and reset sequence is sound, and its best line is that the test is one-sided: a missing canary is strong evidence of degradation and a present one is weak evidence of health, which is the same shape as the weakest check that could pass |

### Rejected

| thing | why |
| --- | --- |
| the canary line itself, out of `context-canary` | a fixed prefix on every reply, which the house writing rules would not survive, and the repo already answers context loss the structural way by keeping decisions in plan folders rather than in the conversation |
| the calibration dials, out of `grill-me` | knowledge and pressure levels for an unknown user. There is one user here, the level does not move between sessions, and a round that opens by asking how hard to push spends the first question on the wrong thing |
| `interface-kit` | 21 KB on colour systems, animation and spatial design for a screen with sixteen grey levels, no motion and a refresh measured in hundreds of milliseconds. The typography it teaches is decided already, in AD8 and `docs/rendering.md` |
| `junior-to-senior` | adversarial senior review of an agent-written plan. Rejected for the reason `interrogate` was: Claude Code ships `/code-review` and an ultra variant, and pstack's `reflect` is already deferred to meta phase 4 for the same job |
| `caveman` | compressed output to save tokens. Already installed in the user's dotfiles, and it trades the thing this repo's writing rules exist to protect |

## What to re-read later

pstack is worth a second pass once the app has code and the gates exist. The parts most likely to become
relevant then, in order: the verification skill generator with its feature map, `architect`, `tdd`,
and the playbook idea, if by then tracked development is showing its limits rather than ours.
