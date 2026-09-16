# meta

How this repo works, as opposed to what it builds.

Agents, skills and instructions live where the harness loads them, `.claude/` for Claude Code,
`.github/copilot-instructions.md` for the shared writing and working rules.
This folder holds what does not load anywhere: the reasoning behind those files, the record of what was tried,
and anything meant to be lifted out and used on another project.

| what | where |
| --- | --- |
| skills the harness loads | `.claude/skills/` |
| the repo's instructions | `.github/copilot-instructions.md`, imported by `CLAUDE.md` |
| why those skills and not others | [`adoption.md`](adoption.md) |
| experiment diary | `diary/`, once meta phase 4 defines the entry shape |

Plans for this track are in [`../plans/03_meta/`](../plans/03_meta/).
