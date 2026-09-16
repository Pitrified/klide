---
name: deslopify
description: Scan prose for the statistical fingerprints of AI writing and rewrite by meaning, then re-scan until clean. A script does the detection. Use when the user says deslopify, deslop, remove the AI tells, or make this not sound like AI, and before publishing any agent-drafted prose in this repo.
---

# Deslopify

Strip the machine fingerprints out of a text so it reads as one person writing for one reader about
something they know. Adapted from [deslopify](https://github.com/JuliusBrussee/skills) by Julius Brussee.

The repo's own writing rules are in [`.github/copilot-instructions.md`](../../../.github/copilot-instructions.md)
and they win wherever the two disagree. This skill is the mechanical half: finding the tells, not defining the style.

## Why it loops

Two things make this different from proofreading.

**You cannot see your own slop.** The same priors that produce the pattern make it invisible on re-read.
So detection is mechanical, a script against a fixed catalog. "Does this look like AI to me" is not a detection method.

**Rewriting reintroduces it.** Asked to remove "it is not just X, it is Y", a model returns "this is less about X than Y",
the same move wearing a hat. So every rewrite is re-scanned, and the loop runs until a scan comes back clean.

Scan, diagnose, rewrite by meaning, re-scan, repeat, then check the register.

## 1. Scan

```bash
.claude/skills/deslopify/scripts/deslop-scan.sh FILE...
.claude/skills/deslopify/scripts/deslop-scan.sh --quiet FILE...   # counts only
```

Exits 1 when it finds something, so it can be wired to a gate later.
Fenced code blocks are stripped before scanning, and the skill's own pattern files are skipped,
because both are full of the words being hunted.

Categories, one pattern file each in `patterns/`:

| category | what it catches |
| --- | --- |
| negative_parallelism | the "not X but Y" family, the highest-value one |
| puffery | delve, tapestry, robust, leverage, and the rest of the inflated vocabulary |
| hedging | reflexive balance, throat-clearing, summary openers |
| intensifiers | words claiming force instead of showing it |
| rule_of_three | triplets that make thin analysis look thorough |
| false_range | "from X to Y" with no spectrum between them |
| house_rules | what this repo bans outright, em dashes first |
| formatting | the term-colon bullet, "serves as a", the X-is-the-Y-of-Z metaphor |

Plus one check the regexes cannot do: cadence, a run of four or more consecutive sentences within four words
of the same length. Tables, lists and headers are dropped first. Human prose mixes a four-word sentence with a
thirty-word one; a paragraph of identical lengths is the strongest current tell.

A match is a finding, not an edit. Everything goes through triage.

One known false positive: a file that catalogs the banned words matches its own catalog.
`.github/copilot-instructions.md` is the example in this repo. The skill's own `patterns/` files are skipped
automatically; that one is not, and its hits are read and dismissed by hand.

## 2. Rewrite by meaning

Never fix a pattern by paraphrasing the pattern. Work out what the sentence asserts, then assert that.

For every "not X but Y", pick one of three:

1. **Nobody believes X.** Delete the X half and assert Y with whatever evidence the text has.
2. **People really do hold X.** Earn it: name who, and say concretely why Y beats it. A real contrast survives being made specific.
3. **The contrast decorates a sentence that asserts nothing.** Delete the sentence. Most cases are this one.

The same move in disguise counts as a new finding: "less about X than Y", "the real X is Y",
"the question is not X, it is Y", and the rhetorical question answered in one word.

For the rest: replace puffery with the plain word or the fact it was hiding. Keep the strongest item of a triplet
and cut the others. Commit to a claim instead of hedging it. Replace "many projects" and "studies show" with
names and dates drawn only from the source or from research actually done, never invented; where the author has to
supply one, leave a marked placeholder. Cut throat-clearing openers and summary closers.

**Overcorrection is also slop.** No manufactured voice, no fake informality, no invented typos.
In technical prose, deslopping means cutting puffery and committing to claims; adding attitude makes it worse.
Preserve meaning, claims and facts exactly. Flag anything that looks factually wrong instead of quietly fixing it.

## 3. Re-scan

Run the scan again on the rewritten text. Expect fresh tells. Cap at four passes; if a sentence still trips a
pattern after four, rewrite it from its bare claim: what fact or opinion is this sentence for?

## 4. Report

Hand back the text and a short change log: categories fixed, counts, and how many passes it took.
