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

House style runs the [deslopify](../.claude/skills/deslopify/) scanner restricted to its `house_rules` category.
The other categories stay advisory and are run by hand, because they need triage: a list of three real things
trips the same pattern as a rhetorical triplet, and a gate that needs judgement is a gate people learn to ignore.

## Slots the app track fills

Empty until a stack exists (app phase 1). Each one is a line in `scripts/check.sh` when it lands.

| slot | what it will check |
| --- | --- |
| format | the formatter for the chosen language, in check mode |
| lint | the linter, at whatever strictness survives the first week |
| types | the type checker, if the language has one worth running |
| test | the unit suite |
| frames | a rendered frame against its reference, which is the gate MD10 is about and the only one specific to this project |

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

Verified both directions: a commit carrying an em dash is refused and no commit object is written,
and a clean tree commits normally.
