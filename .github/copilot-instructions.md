# Klide

## How to write

Technical prose: dry, concrete, and short without leaving anything out. That target is easier to
recognise by its two failure modes. On one side, padding that makes a page longer without making
it say more. On the other, cutting the detail that was the reason to write the sentence at all.
Aim between them.

The specific habits to avoid:

- **No hype.** Adjectives and adverbs that carry tone but no information: seamless, robust,
  powerful, elegantly, simply, blazing. Cut them, or replace them with the concrete fact, subject
  to the next rule.
- **No volatile numbers.** A number that changes with the next run is a measurement with a date
  on it. Leave it out. "The build takes 3 minutes" has to be rechecked every time
  the page is touched, and a runbook accumulates enough of those to become a list of chores. An
  order of magnitude is fine where the size is the point. Numbers that hold still - counts, ports,
  versions, retention windows - are facts and stay.
- **No padding.** One idea stated once. Do not restate a point in three framings to make a section
  feel thorough, and do not open a paragraph by announcing what it is about to say.
- **No fake drama.** The "it is not X, it is Y" reveal. The countdown that rules out two things
  before naming the third. The one-sentence paragraph deployed as a punchline. The "X is the Y of
  Z" metaphor. These are the most-cited tells of machine writing, and enough of this repo is
  written by a machine for it to matter.
- **No thesaurus reach.** delve, leverage, unleash, realm, landscape, ever-evolving, meticulous,
  underscore, boast, harness, tapestry, testament, quietly, bites, load-bearing. A sample, not an
  exhaustive blacklist. Ordinary words instead.
- **Plain copulas.** "is" and "are", not "serves as a", "stands as", "represents".
- **No closing summary** repeating what the page just said, and no motivational sign-off.
- **No emoji**, and no decorative headers. Headers are plain labels.
- **No confident filler where a fact is missing.** If a value is unknown, say it is unknown and
  say who would know. A plausible invented number is the worst possible output here: this is a
  runbook, and someone will act on it.
- **Mechanical.** No em dashes (`--`, `---`, or Unicode). Use a hyphen or rewrite the sentence. Do
  not wrap markdown to a fixed column; break lines on logical boundaries instead, such as after a
  period or between clauses.

The list is the recurring failures, not the definition. The rule is technical, dry, complete
prose; the bullets are what tends to go wrong on the way there.

> A foolish consistency is the hobgoblin of little minds.
>
> Emerson, *Self-Reliance*

## Spellcheck

When the spellchecker flags a technical term or a British/American spelling, add it to
`.vscode/settings.json` under `cSpell.words` rather than rewording around it.
