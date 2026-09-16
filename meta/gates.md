# Gates

A gate is a check that fails instead of a person noticing. They exist so the technical decisions
this repo used to settle in conversation get settled by something that runs (MD3).

## The contract

Anything claiming to be a gate has to meet all five.

1. **One command locally.** `scripts/check.sh` runs every gate. No arguments to remember.
2. **The same command in CI.** [`.github/workflows/checks.yml`](../.github/workflows/checks.yml) calls that script
   and nothing else, so a green run locally means a green run there.
3. **Actionable failure.** The message names the file, the line, and what to do. "Failed" is not a message.
4. **Fast enough to actually be run.** If an agent would skip it to save time, it is not a gate, it is a wish.
5. **Demonstrated failing before it counts.** A gate nobody has seen fail is an assumption.

No dependency beyond bash, python3 and git. There is no node on this box, which rules out the usual
markdown and spelling tools; that constraint kept the gates small, which is not a loss.

## What runs now

| gate | what it catches | demonstrated by |
| --- | --- | --- |
| links | a relative markdown link whose target does not exist | found a real one on its first run, `00_start.md` pointing at a phase file that had moved folders |
| plan status | a phase whose frontmatter disagrees with its tracking table, a table row naming a file that does not exist, a phase file missing from the table | all three, by breaking each one deliberately |
| house style | what the writing rules ban outright, em dashes first | by adding one to `README.md` |
| format | Python formatting drift | by appending a badly spaced statement to a module |
| lint | unused imports, unsorted imports, the bugbear set | found a real unused `import sys` in `scripts/gates/plan_status.py` on its first run |
| types | anything mypy's strict mode rejects | by changing one annotation from `str` to `int`, which it traced to three call sites |
| test | a unit test failing | by changing an expected panel dimension |
| frames | a rendered frame differing from its reference, anywhere, by any amount | by moving the render margin one pixel, which it located at x=26 y=31 |

House style runs the [deslopify](../.claude/skills/deslopify/) scanner restricted to its `house_rules` category.
The other categories stay advisory and are run by hand, because they need triage: a list of three real things
trips the same pattern as a rhetorical triplet, and a gate that needs judgement is a gate people learn to ignore.

## The Python gates

Filled by app phase 1, which chose the stack. See [stack](../docs/stack.md) for why it is Python
and why these four tools.

They run through `uv run`, which syncs the locked environment before each one, so they need no
setup beyond uv and they run the same versions in a worktree as here. `uv.lock` is committed for
that reason. They take most of the script's runtime now, and it is still short enough to sit in a
pre-commit hook.

## The frame gate

Filled by app phase 2. It is the only gate specific to this project, and it is what MD10 means by
the frame being the evidence.

`uv run klide-skeleton` runs the whole loop: the host renders a page at panel size, serves it over
a socket, the simulator receives it and writes it out, and what arrived is compared against
`tests/references/skeleton.png`. It compares the received frame rather than the rendered one, so a
protocol bug fails the gate instead of slipping past it.

The tolerance is zero, at the panel's own 4-bit depth. That is defensible because this compares
the host's output before any panel is involved, and the host is deterministic: the font comes from
Pillow rather than the system, and Pillow is pinned in `uv.lock`. The ceiling is named rather than
hidden: a Pillow upgrade shifts antialiasing and the references need regenerating with `--update`,
which shows up as a reviewable diff of image files.

On failure it writes `build/frames/<name>.diff.png`, the rendered frame with every differing pixel
in red, and says which file to look at and how to accept the change if it was intended. The
reasoning behind the format, the storage and the tolerance is in
[`../src/klide/compare.py`](../src/klide/compare.py), which is where A5 is answered.

## Enforcement point

All three: the local script, a pre-commit hook, and CI.

The hook was rejected at first, on the grounds that a hook is not shared by git, has to be installed per
checkout, and is bypassed with one flag. That reasoning assumed CI would run. It does not: this box has no
GitHub credentials, nothing is pushed from here, and the workflow has never executed once. A hook that can be
bypassed beats a check that never fires, so the decision was reopened and reversed.

```bash
scripts/install-hooks.sh     # once per clone: git config core.hooksPath .githooks
```

`core.hooksPath` is what answers the "not shared by git" objection: [`.githooks/`](../.githooks/) is versioned
like anything else, and the install is one command rather than a copy into `.git/hooks`.
The hook runs `scripts/check.sh`, around a second on this repo, and blocks the commit when a gate fails.
`--no-verify` still bypasses it, deliberately, and CI is the backstop that catches the bypass once pushing works.

The workflow gained a `setup-uv` step when the Python gates landed, because the runner image does
not carry uv. That step is unverified: this box has no GitHub credentials, nothing has been pushed,
and the workflow has still never executed. It is written from the action's documentation.

Verified both directions: a commit carrying an em dash is refused and no commit object is written,
and a clean tree commits normally.
