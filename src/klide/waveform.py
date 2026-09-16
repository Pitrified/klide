"""Refresh modes, and what the simulator claims each one costs.

Every number here is a claim, not a measurement. That distinction is the whole point of this
module, so it is enforced by the type rather than left in a comment: a `Mode` carries its
`source`, and the simulator prints it when asked.

Where the numbers come from: FBInk's `fbink.h` documents an approximate duration per waveform mode
in the comments on `WFM_MODE_INDEX_E`. FBInk is the tool this project would drive on the device, so
its figures are the best published source available. They are not Libra 2 measurements. E Ink does
not publish per-mode timings at all; the figures vary with the panel, the controller and the
temperature, which is why no vendor number exists to check these against.

Two consequences, both deliberate:

- The ordering is trustworthy and the absolute values are not. A2 is faster than DU is faster than
  GC16, and a design that redraws too often will look bad here for the right reason. Whether a
  GC16 on a Libra 2 is 450ms or 300ms is unknown.
- Carta 1200 claims a response time improvement over Carta 1000, so these are more likely to be
  slow than fast for this panel. Which way, and by how much, is unknown.

Calibration belongs to the device client phase (6), when the Kobo is in hand: measure each mode
and replace `FBINK_CLAIMS`
with a profile carrying a real source. Nothing else has to change, because everything reads the
durations through `Mode`.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

FBINK_SOURCE = (
    "FBInk fbink.h, WFM_MODE_INDEX_E comments, read 2026-09-16; not measured on a Libra 2"
)


class UnknownModeError(LookupError):
    """No refresh mode is registered under that name."""


class Waveform(StrEnum):
    """The subset of FBInk's modes that a Kobo can be relied on to have.

    FBInk notes that on very old Kobos only AUTO, DU and GC16 may be relied on. The Libra 2 is
    Mk. 10 and has the rest, but klide only needs these four: one fast mode for streaming text, one
    full mode to clear ghosting, and one in between.
    """

    A2 = "a2"
    DU = "du"
    GL16 = "gl16"
    GC16 = "gc16"


@dataclass(frozen=True)
class Mode:
    """What one refresh mode claims about itself."""

    waveform: Waveform
    milliseconds: int
    grey_levels: int
    flashes: bool
    source: str

    @property
    def seconds(self) -> float:
        return self.milliseconds / 1000


FBINK_CLAIMS: dict[Waveform, Mode] = {
    # "From B&W to B&W, fast (~120ms), some ghosting." Never flashes.
    Waveform.A2: Mode(Waveform.A2, 120, 2, False, FBINK_SOURCE),
    # "From any to B&W, fast (~260ms), some light ghosting." Never flashes.
    Waveform.DU: Mode(Waveform.DU, 260, 2, False, FBINK_SOURCE),
    # "From white to any, ~450ms, some ghosting." Optimised for text on a white background.
    Waveform.GL16: Mode(Waveform.GL16, 450, 16, False, FBINK_SOURCE),
    # "From any to any, ~450ms, high fidelity (i.e., lowest risk of ghosting)." Flashes.
    Waveform.GC16: Mode(Waveform.GC16, 450, 16, True, FBINK_SOURCE),
}


def get_mode(waveform: Waveform | str) -> Mode:
    """Look up a mode, raising rather than returning None on a typo."""
    try:
        return FBINK_CLAIMS[Waveform(waveform)]
    except (ValueError, KeyError):
        known = ", ".join(w.value for w in Waveform)
        raise UnknownModeError(f"no refresh mode {waveform!r}; known modes: {known}") from None


def mode_for(levels_used: int, since_flash: int, flash_every: int) -> Mode:
    """Pick a mode the way a client would: the cheapest that can draw this content, unless a full
    refresh is due.

    `flash_every` is a policy, not a panel property. Partial modes accumulate ghosting and a GC16
    clears it; how many partials are tolerable before one is needed is exactly the measurement A2
    defers, so the count lives in the client's configuration rather than in this table.
    """
    if since_flash >= flash_every:
        return FBINK_CLAIMS[Waveform.GC16]
    if levels_used <= 2:
        return FBINK_CLAIMS[Waveform.A2]
    return FBINK_CLAIMS[Waveform.GL16]
