from pathlib import Path

import pytest

from klide.compare import (
    ReferenceMissingError,
    compare,
    load_reference,
    save_frame,
    write_difference,
)
from klide.frame import Frame
from klide.panel import Panel

TINY = Panel(name="tiny", width=4, height=2, grey_levels=16, ppi=300)


def a_frame(levels: bytes) -> Frame:
    return Frame(panel=TINY, x=0, y=0, width=4, height=2, levels=levels)


def test_identical_frames_match() -> None:
    frame = a_frame(bytes(range(8)))
    result = compare(frame, a_frame(bytes(range(8))), "same")
    assert result.matched
    assert result.differing_pixels == 0


def test_one_level_of_difference_fails() -> None:
    # The tolerance is zero, at the panel's own depth. A single level is a real change.
    changed = bytearray(range(8))
    changed[5] += 1
    result = compare(a_frame(bytes(changed)), a_frame(bytes(range(8))), "off-by-one")
    assert not result.matched
    assert result.differing_pixels == 1


def test_the_failure_locates_the_first_difference() -> None:
    changed = bytearray(range(8))
    changed[5] = 15
    result = compare(a_frame(bytes(changed)), a_frame(bytes(range(8))), "located")
    assert result.first_difference == (1, 1)
    assert "x=1 y=1" in result.summary()
    assert "1 of 8 pixels differ" in result.summary()


def test_a_size_mismatch_fails_instead_of_raising() -> None:
    other = Panel(name="other", width=2, height=2, grey_levels=16, ppi=300)
    wrong_size = Frame(panel=other, x=0, y=0, width=2, height=2, levels=bytes(4))
    result = compare(wrong_size, a_frame(bytes(8)), "resized")
    assert not result.matched


def test_references_roundtrip_through_png_without_loss(tmp_path: Path) -> None:
    frame = a_frame(bytes(range(8)))
    path = tmp_path / "ref.png"
    save_frame(frame, path)
    assert load_reference(path, TINY).levels == frame.levels


def test_a_missing_reference_says_how_to_make_one(tmp_path: Path) -> None:
    with pytest.raises(ReferenceMissingError, match="--update"):
        load_reference(tmp_path / "absent.png", TINY)


def test_the_difference_artifact_marks_changed_pixels_in_red(tmp_path: Path) -> None:
    changed = bytearray(range(8))
    changed[5] = 15
    path = tmp_path / "diff.png"
    write_difference(a_frame(bytes(changed)), a_frame(bytes(range(8))), path)
    from PIL import Image

    with Image.open(path) as img:
        assert img.convert("RGB").getpixel((1, 1)) == (220, 0, 0)
        assert img.convert("RGB").getpixel((0, 0)) != (220, 0, 0)
