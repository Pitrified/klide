---
date: 2026-09-18
kind: review
covers: the two sessions that built the viewer and the reading view, 34 human turns over three days
outcome: five recurring patterns, each routed to a mechanism; two design faults that only a person could have found
---

## What was tried

Building a viewer so a person could look at what klide renders, then acting on what they said.
Across it: a tkinter window, four attempts to make it run, a browser page instead, a browser the
agent can drive, and a rewrite of the reading view.

This review reads the transcript rather than the commits, because the commits record what was
decided and the transcript records what it cost to get there.

## What was expected

That the expensive part would be the rendering, since that is where the product is.

## What happened

The expensive part was the gap between "correct here" and "correct where it runs". Fourteen
failures worth naming, and they fall into five groups rather than fourteen.

**The weakest check that could pass.** Claimed uv's CPython ships tkinter, having run
`import tkinter` and never `Tk()`. Claimed `AllowTcpForwarding` was not disabled, from a grep of
`/etc/ssh/sshd_config` on a box with no SSH server, where an absent file and an absent setting read
alike. Concluded the host's input reader had not raised, from `tail` on a log where stderr is
unbuffered and stdout is not, so the line that named the cause was sitting at the top of the file.
Concluded a press produced no frame, from a probe piped through `head -c 200`, which closed the
stream inside the first event.

**Correct on this machine, wrong on the one that matters.** The tkinter viewer took four rounds and
never ran once on the machine with the screen: a missing Tcl library, then a Python pin, then a
tighter pin, then a threading fix that was a correct change made for a wrong reason. The claim
underneath all four was that uv's 3.13 carries Tcl 9.0, which is true here and was false there,
because `uv run` had used an interpreter already installed on that machine. Later, frames went to
the browser as 2.8 MB of raw pixels and took four to five seconds a press through an SSH tunnel;
that design was made where the viewer and the browser were the same host, so the link was free and
the size of a frame never appeared as a cost.

**Green gates over content that never exercises the feature.** Body text rendered at 6.2 pt through
three phases with every gate passing. Markdown was rendered at block level only, so bold showed its
asterisks and a table was reflowed into prose, again with every gate passing. Both gates compare
against references, and the fixture contained neither small text nor a table, so there was nothing
for them to differ from. Both faults were found by a person reading a screen.

**One name answering two questions.** `--wait` meant both how long to hold the door open for a
viewer and how long a read on the connection may block, so a host told to wait two hours also
stopped two hours after the last press. It killed the session four times in one day. `scale` meant
both an integer divisor and a true physical size, so true size showed a 107 mm panel at 97 mm. A
space between styled runs had to be the prose style and a space inside one had to keep its own, and
one rule for both broke whichever case it was not written for.

**Diagnosis without instrumentation.** A press that the host correctly ignored and a press that
never arrived looked identical on the panel, so the page buttons read as dead when one of them was
working as designed. The host and the viewer each logged that the other had disconnected. In both
cases the log line that resolved it was one line, added after the fact.

## What it cost

Of 34 human turns, 12 were corrections: roughly one turn in three spent telling the agent that
something it had reported as working did not.

Four rounds on the tkinter toolkit before abandoning it. Four host restarts, with two confident
wrong diagnoses, before reading the whole log. Three design decisions shipped and then reversed:
one byte per pixel, integer-only scaling, a six-turn window.

The user said the general rule outright, and it is the cheapest sentence in the transcript: "add log
and experiments rather than guessing". Every time an instrument went in first, the answer came in
one run.

## What changed

Routed by scale, per the fourth principle. Nothing here is a note to be read later; each is a thing
that runs or a rule that loads.

**A test, for the fixture gap.** `tests/test_views.py` now asserts that the view fixture exercises
every markdown construct the renderer supports. A reference gate covers exactly what its fixture
contains, and both design faults above were invisible for that reason. This is the cheap half of
the problem; the other half is below.

**Proposed, for the instructions.** Two rules that no existing principle covers, offered rather than
applied because they change how every future session behaves:

- Where the artifact is consumed is where it has to be checked. "It works here" is not evidence
  about a machine you are not on, and a version number is not a build.
- When two components each report that the other failed, that is a missing message rather than a
  mystery. Add the line before forming the theory.

**Not proposed.** No new gate for the first pattern. A check cannot know which observation is too
weak, and the existing principle already says to suspect the observation before the system. It was
not followed; more prose saying the same thing would not have helped.

**Left as it was.** The four principles, unedited, and the gate contract, unedited. The gates did
what they were built to do. What failed was the assumption that they covered the design, which is
what AD9 already says and what the viewer exists to answer.
