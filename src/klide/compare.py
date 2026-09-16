"""Comparing a rendered frame against a stored reference.

This settles A5, which app phase 1 left open on the grounds that the first real comparison would
show what the answer had to be. It did, in three parts.

**The evidence format is an 8-bit greyscale PNG.** A frame holds 4-bit levels, and spreading a
level to 8 bits multiplies it by 17, which a right shift of four undoes exactly. So the stored PNG
is lossless with respect to the levels it came from and a person can still open it and look at it.
Nothing is given up by storing the readable form.

**References live in the repo.** They are small, they change rarely, and a reference that is
generated on demand cannot fail: it would agree with whatever the code currently does, which is the
one thing a gate must not do.

**The tolerance is zero.** Not because e-ink is exact, but because this comparison is of the host's
output, before any panel is involved, and the host is deterministic: same text, same pinned Pillow,
same bytes. A tolerance here would only hide a real change. The cost is named rather than hidden:
a Pillow or freetype upgrade will shift antialiasing and the references will need regenerating,
which `--update` does and which shows up as a reviewable diff of image files.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PIL import Image

from klide.frame import Frame
from klide.panel import Panel


class ReferenceMissingError(FileNotFoundError):
    """No reference frame is stored under that name."""


@dataclass(frozen=True)
class Comparison:
    """What a comparison found. `matched` is the gate's answer, the rest is for the person
    reading the failure."""

    name: str
    matched: bool
    differing_pixels: int
    total_pixels: int
    first_difference: tuple[int, int] | None

    def summary(self) -> str:
        if self.matched:
            return f"{self.name}: matches reference ({self.total_pixels} pixels)"
        assert self.first_difference is not None
        x, y = self.first_difference
        share = self.differing_pixels * 100 / self.total_pixels
        return (
            f"{self.name}: {self.differing_pixels} of {self.total_pixels} pixels differ "
            f"({share:.2f}%), first at x={x} y={y}"
        )


def load_reference(path: Path, panel: Panel) -> Frame:
    """Read a stored reference back into a frame."""
    if not path.exists():
        raise ReferenceMissingError(f"no reference at {path}; render one with --update")
    with Image.open(path) as img:
        return Frame.from_image(img.convert("L"), panel)


def save_frame(frame: Frame, path: Path) -> None:
    """Write a frame where a person can open it."""
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_image().save(path, format="PNG")


def compare(actual: Frame, reference: Frame, name: str) -> Comparison:
    """Compare at the panel's own bit depth, exactly."""
    total = actual.width * actual.height
    if (actual.width, actual.height) != (reference.width, reference.height):
        return Comparison(
            name=name,
            matched=False,
            differing_pixels=total,
            total_pixels=total,
            first_difference=(0, 0),
        )
    differing = 0
    first: tuple[int, int] | None = None
    for i, (a, b) in enumerate(zip(actual.levels, reference.levels, strict=True)):
        if a != b:
            differing += 1
            if first is None:
                first = (i % actual.width, i // actual.width)
    return Comparison(
        name=name,
        matched=differing == 0,
        differing_pixels=differing,
        total_pixels=total,
        first_difference=first,
    )


def write_difference(actual: Frame, reference: Frame, path: Path) -> None:
    """Write an artifact a person can look at: the rendered frame, with every pixel that differs
    from the reference painted red. A count tells you something went wrong, this tells you what."""
    base = actual.to_image().convert("RGB")
    if (actual.width, actual.height) != (reference.width, reference.height):
        path.parent.mkdir(parents=True, exist_ok=True)
        base.save(path, format="PNG")
        return
    mask = Image.frombytes(
        "L",
        (actual.width, actual.height),
        bytes(255 if a != b else 0 for a, b in zip(actual.levels, reference.levels, strict=True)),
    )
    red = Image.new("RGB", base.size, (220, 0, 0))
    base.paste(red, mask=mask)
    path.parent.mkdir(parents=True, exist_ok=True)
    base.save(path, format="PNG")
