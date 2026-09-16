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

## What to re-read later

pstack is worth a second pass once the app has code and the gates exist. The parts most likely to become
relevant then, in order: the verification skill generator with its feature map, `architect`, `tdd`,
and the playbook idea, if by then tracked development is showing its limits rather than ours.
