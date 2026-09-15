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

## Planning against "the best spec is code"

Her position is narrower than the slogan, and her own repo shows it.
pstack ships a multi-phase plan playbook and a prototype playbook, and the README says cursor's plan mode
"works great with pstack". The claim is about defaults, not about capability: planning is not the first move,
and a plan is not the artifact.

It also comes from a specific situation. She works in a large existing codebase where the product direction
is already set, the domain is known, and the expensive failure is an agent writing plausible code that is wrong.
In that setting a prose plan is a second source of truth that drifts from the first one.

A new project does not have that. Two things her system consumes rather than produces:
the product direction, and the finish condition. `/poteto-mode` is invoked with a goal and a definition of done;
it never invents them. So the part of our planning that says what klide is for, what it must do, and what is
out of bounds is not in competition with her method. It is the input it assumes.

The part that is in competition is the rest of our plan folders: prose that resolves technical forks.
Which transport, which client shape, which launcher, which stack. Her answer to those is not a paragraph,
it is a prototype or a type signature, and two of her principles say so directly, exhaust-the-design-space
(build 2-3 competing prototypes and compare) and foundational-thinking (settle the data structures first).

Where that leaves this repo: keep prose for direction, constraints and the record of why, since code holds
none of those. Move fork-resolution out of prose and into things that run. A1 in the app track is the first test
of that, and it is already written as "build the slice twice and keep what survives the gates" rather than
"decide the stack".

## Each agent its own machine

What she proposes is Cursor cloud agents: each agent gets an isolated VM with a real computer, so it can install
dependencies, run the app, drive a browser, take screenshots and video, and interact with the product as a user would.
Her argument against worktrees is resources, that a strong machine runs maybe ten agents before it strains,
and that a worktree gives an agent a directory rather than a computer.
Cursor charges those agents at API pricing, which D6 rules out for us.

What we have, checked 2026-09-16:

* **Claude Code cloud sessions.** Research preview, and it includes Pro. Each session runs in its own
  Anthropic-managed VM, network access is restricted by an allowlist, and git credentials stay outside the sandbox.
  Start one per task with `claude --cloud "<task>"`, several in parallel, and pull one back with `--teleport`.
  The relevant line for D6: sessions share the account's normal rate limits and there is no separate compute charge
  for the VM. So the shape she describes is available here without API billing.
* **The wrinkle.** Cloud sessions clone from GitHub, and this box holds no GitHub credentials by design.
  Either the Claude GitHub App gets installed on the repo from the user's own browser, or `CCR_FORCE_BUNDLE=1`
  uploads the local repository instead, in which case the session cannot push back.
* **Locally.** Subagents can run in a git worktree, the Bash tool has an OS-enforced filesystem and network sandbox
  via `/sandbox`, and dev containers or VMs sit above that. This is the cheap end, and it is a directory plus a
  boundary rather than a computer.

The honest read for klide: her argument for a real computer is about verifying behaviour by driving the product.
Our product is a simulator that emits frames, which is the one case where a directory is nearly enough, because the
evidence is a file rather than a screen someone has to look at. That makes worktrees adequate for longer here than
they would be for a browser app, and it makes the cloud path worth trying for the runs that need isolation rather
than as the default.

Answered in M9: worktrees for now, and the cloud path stays available rather than planned.
At the concurrency MD8 sets, the machine is not the limit anyway.

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
* **MD9. The unsupervised boundary is what this box can reach.** An agent may eventually do anything that needs
  no GitHub credentials: edit, commit, branch, use worktrees, run whatever it likes locally. Push, PR and merge sit
  outside it because the box has no credentials for them, so the limit is enforced by the machine rather than by an
  instruction an agent could talk itself out of (M4).
* **MD10. The frame is the evidence.** Verification for klide is a rendered frame compared against a reference,
  and the simulator exists to produce it (M7). This is the one lever worth building before anything else.
* **MD8. Start at one or two agents and earn more.** The workshop outline calls this the agent trust curve,
  micromanagement at one end and automated merging at the other, moved along slowly. Concurrency is the last dial
  to turn, not the first: one agent, occasionally two, while the meta interactions and the constraints are still
  being shaped. Worktrees carry that comfortably, which is why M9 defers the cloud path rather than taking it.
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
  ANS: b.
- M2: Where the meta artifacts live.
  a. Harness-native paths only, `.claude/skills/`, `.claude/agents/`, so they actually load.
  b. A `meta/` folder only, which loads nowhere and has to be copied.
  c. Harness-native paths for what must load, plus `meta/` for the diary, experiments and anything portable.
  Recommended: c.
  ANS: c. Harness-native paths for anything that must load, `meta/` for the diary and anything meant to travel.
- M3: Which harnesses this has to work on. Claude Code only for now, or Cursor and others too.
  Recommended: Claude Code only until something works, since portability is the second problem.
  ANS: Claude Code.
- M4: What "unsupervised" is allowed to mean here, concretely. Which actions an agent may take without asking:
  editing, committing, opening PRs, merging, pushing. Note this box has no GitHub credentials, so pushing is
  already impossible from here.
  ANS: eventually everything that can be done without GitHub credentials. Editing, committing, branching,
  worktrees, running anything locally. Pushing, PRs and merges are outside the boundary because the box cannot
  reach them, which makes the limit enforced rather than promised. "Eventually" is the operative word: the
  permission grows as the runs earn it (MD8).
- M5: The review cadence, and its trigger. Every N sessions, weekly, or at each phase boundary.
  Recommended: at each phase boundary plus a standing weekly slot, because painful interactions are easiest
  to recall while they are recent.
  ANS: flexible. At a phase boundary, straight after a painful interaction, daily, whenever it is worth doing.
  No fixed schedule, and a review that finds nothing still gets logged.
- M6: The diary format. One file per experiment, or an append-only log, and what a good entry contains.
  Recommended: one file per experiment with a fixed frontmatter, so entries can be graded later.
  ANS: as recommended.
- M7: What counts as proof for this app. pstack's answer is interacting with the running product.
  klide's equivalent is a rendered frame, which suggests the simulator should emit images an agent can diff
  against a reference, and that this is the first lever to build.
  Recommended: yes, make frame-level evidence the verification primitive and design the simulator around it.
  ANS: yes. The frame is the evidence, and the simulator is built around producing it.
- M8: The parallelism model. Claude Code has worktrees and background agents. Lauren Tan's position is that
  each agent wants its own machine. What do we actually run here, on one box.
  ANS: settled by MD8 and M9. One agent, sometimes two, in worktrees on this box.
- M9: Whether to enable the cloud path at all, and how. Installing the Claude GitHub App on the repo gives cloud
  sessions that can push, at the cost of a GitHub App with write access to the repo. `CCR_FORCE_BUNDLE=1` needs
  nothing but cannot push back.
  Recommended: bundle mode first, since the results can be teleported back and nothing new gets write access.
  ANS: neither for now. Worktrees until this machine strains. The GitHub App stays in the background as the option
  to reach for if isolation or push access turns out to be the thing blocking a run, and it is installed from the
  user's own browser when that happens. See MD8 for the concurrency this assumes.
- M10: What isolation each class of work gets. Same session, subagent, worktree, sandboxed bash, cloud VM.
  Recommended: decide it by blast radius rather than by size of task, and write it into the interaction contract
  in phase 3.
  ANS: flexible. Blast radius is the guide, not a table to look up.
