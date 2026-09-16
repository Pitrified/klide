---
name: principles
description: The four engineering rules this repo works by - prove it works, build the lever, sequence verifiable units, encode lessons in structure. Read before declaring work done, before doing non-trivial work by hand, when planning a multi-step change, or when writing the same correction a second time.
---

# Principles

Four rules, adapted from [pstack](https://github.com/cursor/plugins/tree/main/pstack) by Lauren Tan, MIT.
pstack ships twenty-three; these are the ones that apply to a repo whose product is a rendered frame.
Why only four, and what was left out, is in [`meta/adoption.md`](../../../meta/adoption.md).

## Prove it works

Verify against the real artifact, never a proxy, a self-report, or "it compiles".

Run the thing and exercise the actual path. Read the real value, not a cached or derived one.
When a check fails, suspect the observation before suspecting the system.
For delegated work, inspect the artifact, the diff, the file, the output, not the delegate's summary of it.

The strongest proof is a deterministic script that re-runs the same comparison, not a one-time look.
In this repo the artifact is usually a frame: render it, compare it against the reference, keep the result.

## Build the lever

When the work is not trivial, build the thing that does it or proves it, rather than doing it by hand.

Do the first unit by hand to learn the recipe, then write the script and prove it by re-running it on that unit.
A hand-done change can only be re-checked by redoing it; a script turns "trust me" into "run this".
The bar is triviality, not repetition: a one-off earns a lever when the lever is what makes it checkable.
Build the smallest script that does the job, never a framework.

If the lever was claimed and there is no script, codemod or generator in the diff, it was not applied.

## Sequence verifiable units

Break multi-step work into units that each end in a state you can check, and do not advance until the current one is green.

A break caught at the unit that caused it is cheap to find. A break caught after a batch is buried under
everything built on top of it. Order the commits so the sequence proves itself to a reader:
the failing test before the fix, the subtraction before the reshape, the baseline before the treatment.

## Encode lessons in structure

When you find yourself writing the same instruction twice, make it a mechanism instead of more text.

Pick the strongest mechanism the situation allows: a state that cannot be represented, then a check that fails CI,
then a canonical helper, then a runtime check, then prose. Prose is the weakest and the easiest to miss.
If the fix is structural, only make the structural fix; the instruction was the symptom.

Route by scale: a one-off is a note, a recurring correction is a gate or a skill edit, a systemic problem is a principle.
Recording without routing changes nothing.
