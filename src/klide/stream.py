"""Streaming a growing conversation to the panel without redrawing all of it.

Two problems, and they pull in opposite directions.

**The panel is slow.** A full refresh costs hundreds of milliseconds and a transcript grows in
bursts, so redrawing the whole page per message asks the panel for work it cannot do and makes the
screen flicker through states nobody reads. The answer is to coalesce: wait until the content has
settled, or until a deadline, and send once.

**The reader is slower still.** Streaming every token to e-ink is pointless (the UI notes say so
outright), which is why D9's message-level granularity was accepted rather than regretted.

What gets sent is the rectangle that changed, not the page. Appending to a conversation usually
changes a band at the bottom, so the dirty rectangle is a fraction of the frame and the panel can
draw it with a fast waveform. The rectangle is found by comparing the new page against the old one
rather than by reasoning about layout, because layout reasoning would have to be right about
wrapping, and being wrong would leave stale pixels on a real device with no way to notice.

The property that makes this safe to do at all is checked in the tests: a sequence of dirty
rectangles has to leave the panel showing exactly what sending the whole page would have.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field

from klide.frame import Frame
from klide.waveform import Waveform


@dataclass(frozen=True)
class Update:
    """What to send: a rectangle, and the mode to draw it with."""

    frame: Frame
    waveform: Waveform


def changed_rows(old: Frame, new: Frame) -> tuple[int, int] | None:
    """The first and last row that differ, or None if nothing did.

    Rows rather than a full bounding box. A conversation is a column of text, so a change nearly
    always spans the full width anyway, and a row range costs one comparison per row instead of
    one per pixel.
    """
    if (old.width, old.height) != (new.width, new.height):
        return (0, new.height - 1)
    width = new.width
    first = None
    last = None
    for row in range(new.height):
        start = row * width
        end = start + width
        if old.levels[start:end] != new.levels[start:end]:
            if first is None:
                first = row
            last = row
    if first is None or last is None:
        return None
    return (first, last)


def dirty_rectangle(old: Frame, new: Frame) -> Frame | None:
    """The part of `new` that differs from `old`, as a frame placed where it belongs.

    Returns None when nothing changed, which is the case worth catching: a redraw that changes no
    pixels still costs a refresh and a flash on a real panel.
    """
    rows = changed_rows(old, new)
    if rows is None:
        return None
    first, last = rows
    height = last - first + 1
    return Frame(
        panel=new.panel,
        x=0,
        y=first,
        width=new.width,
        height=height,
        levels=new.levels[first * new.width : (last + 1) * new.width],
    )


def pick_waveform(patch: Frame, full_height: int) -> Waveform:
    """Which mode to draw a patch with.

    A2 is ruled out despite being the fastest: it goes from black and white to black and white
    only, and antialiased text is neither. That leaves the text mode for a patch and the full mode
    when the patch is most of the screen anyway, where the better result costs nothing extra.
    """
    if patch.height >= full_height * 3 // 4:
        return Waveform.GC16
    return Waveform.GL16


@dataclass
class Coalescer:
    """Decides when a burst of changes has settled enough to be worth a refresh.

    Two limits, because either alone behaves badly. A quiet period alone never fires while the
    assistant is still writing, so the screen stays stale through the most interesting part. A
    deadline alone fires mid-burst and spends refreshes on states nobody reads.
    """

    #: Send once nothing has changed for this long.
    quiet: float = 0.4
    #: Send anyway after this long, however busy it stays.
    deadline: float = 2.0

    pending: bool = field(default=False, init=False)
    first_change: float = field(default=0.0, init=False)
    last_change: float = field(default=0.0, init=False)

    def changed(self, now: float | None = None) -> None:
        moment = time.monotonic() if now is None else now
        if not self.pending:
            self.pending = True
            self.first_change = moment
        self.last_change = moment

    def due(self, now: float | None = None) -> bool:
        if not self.pending:
            return False
        moment = time.monotonic() if now is None else now
        settled = moment - self.last_change >= self.quiet
        overdue = moment - self.first_change >= self.deadline
        return settled or overdue

    def sent(self) -> None:
        self.pending = False
