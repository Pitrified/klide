"""Input events, which travel from the device to the host.

Touch is always handled on the device because that is where the touchscreen is. What travels is
only the gesture a client chose to forward: panning inside a page it already holds is answered
locally and never reaches the host, and everything that changes what is displayed is sent.

The gesture set is the provisional map from `plans/02_kobo/01_ui_ux.md`. It is provisional there
and provisional here; what this module fixes is the wire shape, not the meaning of a swipe.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum


class EventKind(IntEnum):
    """Byte codes, so the wire never carries a string."""

    TAP = 1
    SWIPE = 2
    BUTTON = 3


class Direction(IntEnum):
    NONE = 0
    LEFT = 1
    RIGHT = 2
    UP = 3
    DOWN = 4


class Button(IntEnum):
    """The Libra 2's physical page-turn buttons, which the Kindle path did not have."""

    NONE = 0
    PAGE_BACK = 1
    PAGE_FORWARD = 2


@dataclass(frozen=True)
class InputEvent:
    """One gesture or press.

    `x` and `y` are panel coordinates and are meaningful for a tap. A swipe carries its direction
    and the point it started from; a button press carries neither and sets them to zero.
    """

    kind: EventKind
    direction: Direction = Direction.NONE
    button: Button = Button.NONE
    x: int = 0
    y: int = 0

    @classmethod
    def tap(cls, x: int, y: int) -> InputEvent:
        return cls(kind=EventKind.TAP, x=x, y=y)

    @classmethod
    def swipe(cls, direction: Direction, x: int = 0, y: int = 0) -> InputEvent:
        return cls(kind=EventKind.SWIPE, direction=direction, x=x, y=y)

    @classmethod
    def press(cls, button: Button) -> InputEvent:
        return cls(kind=EventKind.BUTTON, button=button)

    def describe(self) -> str:
        """A name a scripted session can put in a filename and a person can read."""
        if self.kind is EventKind.TAP:
            return f"tap-{self.x}-{self.y}"
        if self.kind is EventKind.SWIPE:
            return f"swipe-{self.direction.name.lower()}"
        return f"press-{self.button.name.lower()}"
