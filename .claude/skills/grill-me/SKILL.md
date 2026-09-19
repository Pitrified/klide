---
name: grill-me
description: Interview the user in rounds about a plan, design or half-formed idea until nothing is left silently assumed, then write the result to a plan folder. Use when the user says grill me, grill this, stress test this, or arrives with an idea too vague to plan against.
---

# Grill me

Interview the user about an idea until you share an understanding of it, then write that
understanding down. Adapted from [grill-me](https://github.com/mattpocock/skills) by Matt Pocock, MIT.
What was changed and why is in [`README.md`](README.md); the reasoning behind taking it is in
[`plans/05_grill_me/00_start.md`](../../../plans/05_grill_me/00_start.md).

## The tree and the frontier

Treat the idea as a tree of decisions, where each one branches into the decisions that hang off it.
The frontier is every decision whose prerequisites are already settled: the questions that can be
asked now without guessing at an answer you have not heard yet.

Ask the whole frontier in one round, then stop and wait. A question whose answer depends on another
question in the same round belongs to a later round. The answers reshape the tree, settled decisions
push the frontier outward, and you recompute it and ask again.

The session is over when the frontier is empty, not when you have asked a certain number of things.
Do not start building until the user says you have got it.

## A round

Number the questions and give your recommended answer to each, so a user who agrees with all of them
can say so in one word. A round with no pushback in it is a round that was not worth asking.

Two formats, and the choice is about how the user is answering rather than about the content:

- **`AskUserQuestion`** when the answers enumerate. It renders as tappable options, which matters
  because the user is often on a phone, and it takes four questions of up to four options each.
  Put the recommendation first and label it, and write each option's description as the trade it
  makes rather than as a restatement of its label.
- **Prose** when an answer is a sentence rather than a choice, or when the round is wider than four
  questions. Number them, state the recommendation under each, and keep them far enough apart to be
  answered one at a time.

Either way the recommendation is a real position, taken because you looked at something. "Either
could work" is not a recommendation and wastes the round.

## Facts are your job, decisions are theirs

Never ask the user something you could find out. If a question on the frontier needs a fact about
the repository, the machine, or a library, go and get it: read the file, run the command, search the
web. Then ask the question the fact leaves open.

This is where most of the value is. Half the questions you were about to ask dissolve when you read
the code, and the ones that survive are sharper for it. A fact you had to go and find is also the
best source of pushback, because it is the part of the picture the user did not have.

Do not block a round on a slow lookup. Only the questions downstream of it wait; ask the rest now.

## Ending: write it down

The source treats the interview as stateless and leaves nothing behind. Here it ends by writing a
plan folder, because in this repo reasoning that only exists in a conversation is lost at the next
`/clear`, which is what
[`.claude/skills/principles/SKILL.md`](../principles/SKILL.md) means by encoding lessons in
structure.

So the last round is followed by a `00_start.md` in a new `plans/NN_<slug>/` folder, in the shape
[`tracked-development`](../../../plans/03_meta/00_start.md) describes:

- **Where this came from**, including that it came from an interview and on what date.
- **The analysis**, including the facts you went and found, with what you checked and when. A number
  you measured is worth more than the question it answered.
- **Decisions**, each with a two letter prefix unique to the folder and a number, stating what was
  rejected and why. A decision with no rejected alternative was not a decision.
- **Open questions**, one per thing the rounds did not settle, each with a `Recommended:` line and an
  empty `NEW_ANS:` slot for the user to fill in later.

That last part is the seam. Anything the interview could not close leaves in the format the
asynchronous fold-in loop already reads, so a question does not have to be resolved in the sitting to
be recorded.

Add the phase files and `tracking.md` only if the work is actually multi-phase. If it is one
afternoon's work, `00_start.md` alone is the whole output and saying so is better than manufacturing
four phases.
