---
status: draft
---

# Meta layer - bootstrap

## The turn

The repo now carries two tracks.

1. **A meta layer.** Learn how to orchestrate unsupervised work by more than one agent.
   Collect best practices, install or write skills, and keep the agents, skills and instructions
   in the repo with the same care as code. Keep a diary of experiments.
   The intent is to generalise this beyond klide and into the whole workflow.
2. **The klide app.** Still the thing being built. The physical Kobo is not here, so it starts
   from a simulator that imitates the device and is friendly to agents.
   Tracked separately in [`../04_klide_app/00_start.md`](../04_klide_app/00_start.md).

The direction of travel is unsupervised. Interactions should shift toward functional specification,
with patterns, CI, and quality, performance and lint gates carrying the technical decisions instead of a person.
Tracked development is the scaffold for the bootstrap phase only, while the guardrails do not exist yet.
It is expected to change shape.

## Research, 2026-09-15

Source: Lauren Tan (poteto), Cursor, previously Meta React and Netflix. The 50 minute video is her
GrokBot workshop. A closely matching 60 minute Maven session, "How Cursor Turned AI Agents Into Better
Engineers", 2026-08-12, outlines: agents as talented but forgetful new hires, an agent trust curve from
micromanagement to automated PR merging, verification skills and feature maps, pstack itself, keeping
skills honest with evals, and guardrails for production use.
No transcript of the video was found. The recaps below are secondary, and the repo is primary.

**pstack** is her working method, open sourced at `github.com/cursor/plugins/tree/main/pstack`, MIT.
It is 47 skills, 23 of them one principle each, 23 playbooks, 2 subagents, and a dormant automation pack.
Claude Code ports exist, for example `irg1008/cstack`, which reports around 2,700 tokens of session overhead.

The parts that look load-bearing:

* **One entry point.** `/poteto-mode` matches the request to a playbook, copies that playbook's steps verbatim
  into a todo list so nothing is silently dropped, and calls the other skills as steps need them.
* **Verification as infrastructure.** An agent has to interact with the real product, inspect the result,
  recognise failure and retry until it can show success. "The build passed" is not evidence.
  Where a project has no scripted way to prove behaviour, `/create-verification-skill` generates one,
  with a feature map that a second skill keeps from drifting.
* **Depth before width.** Her line is that naive parallelisation makes agents write slop faster.
  The width skills, `/arena` for competing implementations and `/swarm` for distributed slices, come after
  a single agent has a verified environment.
* **Build the lever.** Turn recurring manual work into a tool or a skill that a reviewer can rerun,
  rather than doing it by hand.
* **Encode lessons in structure.** Make the rule a lint, a flag, a runtime check or a script instead of more prose.
* **Cost is real.** One reported comparison had a 30 minute task take 60 minutes under pstack, and catch three
  false claims the agent had made about its own work. Spend the rigor where being wrong is expensive.
* **Metrics.** Accepted fixes, review time, rework after review, escaped defects, cost per accepted change.
  Not PR count.

Two of her positions are worth flagging because they cut against this repo as it stands.
She does not believe in planning: "the best spec is code". And she has argued that worktrees are dead and cloud
agents are the future, on the grounds that each agent wants its own computer to run code and take screenshots on.
This repo is currently nine commits of planning and no code.

## What this repo looks like today

Four days of plan folders, no source, no tests, no CI, no lint, no stack.
Guardrails count: zero. Every technical decision so far was made by a person in conversation,
which is exactly the thing the new direction wants to stop doing.

That is an unusually good starting position for this experiment. There is no legacy to protect,
the stack is open, and the first real workload is a simulator whose output is an image,
which is the cheapest possible form of observable evidence.

## Decisions

Taken from the framing above, not re-derived.

* **MD1. Two tracks, separately tracked.** Meta layer here, app in `04_klide_app`.
* **MD2. Meta artifacts are kept with care and are a deliverable in themselves.** Agents, skills, instructions
  and an experiment diary, maintained to be lifted out of this repo and used elsewhere.
* **MD3. Specification over technical direction.** The user's side of the conversation should trend toward
  what the thing must do. Patterns, CI, and quality, performance and lint gates carry the rest.
* **MD4. Nothing is set in stone, and the interaction itself is under review.** A recurring session review
  looks for painful interactions between user and agent, and between agents.
* **MD5. Simulator first.** The physical Kobo is not here, and the simulator is wanted anyway because it is
  what makes the app testable by an agent.
* **MD6. The stack is open.** Rust, Go, Flutter or anything else, for the host, the renderer and the simulator,
  GPU where it helps.
* **MD7. Tracked development is bootstrap scaffolding.** It stays until the guardrails can carry the same load,
  and it is expected to change shape rather than be preserved.

## Open questions

Numbered `M` for this folder, continuing across batches.

- M1: How much of pstack do we take.
  a. Install a Claude Code port wholesale and work inside it.
  b. Read it, cherry-pick a handful of skills and principles, write our own thin router.
  c. Ignore it and build from our own experience.
  Recommended: b, because the verification and evidence ideas transfer while 47 skills, Cursor built-ins
  and a per-session token cost do not fit a repo with no code yet.
  NEW_ANS:
- M2: Where the meta artifacts live.
  a. Harness-native paths only, `.claude/skills/`, `.claude/agents/`, so they actually load.
  b. A `meta/` folder only, which loads nowhere and has to be copied.
  c. Harness-native paths for what must load, plus `meta/` for the diary, experiments and anything portable.
  Recommended: c.
  NEW_ANS:
- M3: Which harnesses this has to work on. Claude Code only for now, or Cursor and others too.
  Recommended: Claude Code only until something works, since portability is the second problem.
  NEW_ANS:
- M4: What "unsupervised" is allowed to mean here, concretely. Which actions an agent may take without asking:
  editing, committing, opening PRs, merging, pushing. Note this box has no GitHub credentials, so pushing is
  already impossible from here.
  NEW_ANS:
- M5: The review cadence, and its trigger. Every N sessions, weekly, or at each phase boundary.
  Recommended: at each phase boundary plus a standing weekly slot, because painful interactions are easiest
  to recall while they are recent.
  NEW_ANS:
- M6: The diary format. One file per experiment, or an append-only log, and what a good entry contains.
  Recommended: one file per experiment with a fixed frontmatter, so entries can be graded later.
  NEW_ANS:
- M7: What counts as proof for this app. pstack's answer is interacting with the running product.
  klide's equivalent is a rendered frame, which suggests the simulator should emit images an agent can diff
  against a reference, and that this is the first lever to build.
  Recommended: yes, make frame-level evidence the verification primitive and design the simulator around it.
  NEW_ANS:
- M8: The parallelism model. Claude Code has worktrees and background agents. Lauren Tan's position is that
  each agent wants its own machine. What do we actually run here, on one box.
  NEW_ANS:
