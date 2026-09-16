"""Panel geometry.

The numbers come from the device notes in `plans/02_kobo/00_start.md`, which record what the
Libra 2's own information screen reported. Both the renderer and the simulator need them, so they
live in one place rather than being repeated at each call site.
"""

from dataclasses import dataclass


class UnknownPanelError(LookupError):
    """No panel is registered under that name."""


@dataclass(frozen=True)
class Panel:
    """A target screen, as far as anything drawing to it needs to care."""

    name: str
    width: int
    height: int
    grey_levels: int

    @property
    def bits_per_pixel(self) -> int:
        """Bits needed per pixel, which is what the wire format has to carry."""
        return (self.grey_levels - 1).bit_length()

    @property
    def frame_bytes(self) -> int:
        """Size of one packed full frame, the ceiling any transport has to move."""
        return self.width * self.height * self.bits_per_pixel // 8


KOBO_LIBRA_2 = Panel(name="kobo-libra-2", width=1264, height=1680, grey_levels=16)

PANELS = {p.name: p for p in (KOBO_LIBRA_2,)}


def get_panel(name: str) -> Panel:
    """Look up a panel by name, raising rather than returning None on a typo."""
    try:
        return PANELS[name]
    except KeyError:
        known = ", ".join(sorted(PANELS))
        raise UnknownPanelError(f"no panel named {name!r}; known panels: {known}") from None
