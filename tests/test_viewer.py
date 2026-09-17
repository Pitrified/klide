"""The viewer is a second implementation of the protocol. This holds it to the contract.

`viewer/klide_viewer.py` ships to another machine as one file and imports no klide. That is
deliberate: a protocol only one codebase can speak has not been shown to be a protocol, and the
viewer is the first implementation written against the specification instead of sharing its code.
It is the strongest available check on AD5 short of the real Lua client.

Duplicating an implementation is only acceptable if divergence fails a gate, which is what this
file is. Everything the viewer copied from klide is checked against klide here: the constants, the
decoder, the input encoder, and the table of claimed refresh durations.

The viewer is loaded by path rather than imported as a package, because it is not one, and because
loading it the way the target machine does is part of what is being checked. tkinter is not needed
to import it, only to run the window, so this works on a headless box.
"""

import importlib.util
import io
import sys
from pathlib import Path
from typing import Any

import pytest

from klide.frame import Frame
from klide.input import Button, Direction, EventKind, InputEvent
from klide.panel import KOBO_LIBRA_2, Panel
from klide.protocol import (
    FRAME,
    HEADER_SIZE,
    INPUT,
    MAGIC,
    WAVEFORM_CODES,
    encode_frame,
    read_input,
)
from klide.waveform import FBINK_CLAIMS, Waveform

VIEWER_PATH = Path(__file__).resolve().parents[1] / "viewer" / "klide_viewer.py"


def load_viewer() -> Any:
    """Load the standalone file the way the machine with the screen would."""
    spec = importlib.util.spec_from_file_location("klide_viewer", VIEWER_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["klide_viewer"] = module
    spec.loader.exec_module(module)
    return module


viewer: Any = load_viewer()
TINY = Panel(name="tiny", width=4, height=2, grey_levels=16, ppi=300)
LEVELS = bytes([0xA, 0xB, 0xC, 0xD, 1, 2, 3, 4])


def a_frame(panel: Panel = TINY, x: int = 0, y: int = 0) -> Frame:
    return Frame(panel=panel, x=x, y=y, width=4, height=2, levels=LEVELS)


# It ships on its own


def test_the_viewer_imports_nothing_from_klide() -> None:
    # The moment it imports klide it stops being an independent implementation and stops being
    # copyable to a machine that has no repo on it.
    source = VIEWER_PATH.read_text()
    assert "import klide" not in source
    assert "from klide" not in source


def test_the_viewer_needs_no_third_party_package() -> None:
    # Copying the file to whatever machine currently has a screen has to be the whole install.
    source = VIEWER_PATH.read_text()
    for forbidden in ("import PIL", "from PIL", "import numpy", "import pygments"):
        assert forbidden not in source


def _script_metadata() -> dict[str, Any]:
    """The PEP 723 block, parsed the way the specification says to read it."""
    import re
    import tomllib

    pattern = r"(?m)^# /// (?P<type>[a-zA-Z0-9-]+)$\s(?P<content>(^#(| .*)$\s)+)^# ///$"
    for match in re.finditer(pattern, VIEWER_PATH.read_text()):
        if match.group("type") != "script":
            continue
        content = "".join(
            line[2:] if line.startswith("# ") else line[1:]
            for line in match.group("content").splitlines(keepends=True)
        )
        return tomllib.loads(content)
    raise AssertionError("no PEP 723 script block in the viewer")


def test_the_viewer_declares_its_own_environment() -> None:
    # PEP 723 inline metadata is what lets `uv run klide_viewer.py` work on a machine with nothing
    # set up: uv reads the block, builds the environment, and its own CPython ships tkinter, which
    # Debian and Ubuntu split out of the system Python into a separate package.
    assert "requires-python" in _script_metadata()


def test_the_viewer_asks_for_a_python_whose_tk_works() -> None:
    """The version is load-carrying, not a formality.

    tkinter is stdlib but needs a Tcl/Tk the interpreter can find, and uv's standalone CPythons are
    not alike. A build resolved on another machine was linked against Tcl 8.6 with no 8.6 library
    files and died with `Can't find a usable init.tcl`; the 3.13 builds carry Tcl/Tk 9.0 and run.
    Lowering this floor would let uv pick the broken kind again, on a machine nobody is testing on.
    """
    requires = _script_metadata()["requires-python"]
    assert requires == ">=3.13", f"lowering this reintroduces the broken-Tk builds, got {requires}"


def test_the_viewer_declares_no_dependencies_and_should_not_gain_any() -> None:
    # The moment this list is non-empty the file stops being copyable to a machine with no network
    # or no patience, and starts being an install. The standard library and tkinter are the budget.
    assert _script_metadata()["dependencies"] == []


def test_the_shebang_runs_it_without_a_python_being_chosen_first() -> None:
    first_line = VIEWER_PATH.read_text().splitlines()[0]
    assert first_line == "#!/usr/bin/env -S uv run --script"


# The constants it copied


def test_the_wire_constants_agree() -> None:
    assert viewer.MAGIC == MAGIC
    assert viewer.HEADER_SIZE == HEADER_SIZE
    assert viewer.FRAME == FRAME
    assert viewer.INPUT == INPUT


def test_the_waveform_codes_agree_including_their_order() -> None:
    # Positional on the wire: reordering silently changes what every client draws.
    assert tuple(viewer.WAVEFORMS) == tuple(w.value for w in WAVEFORM_CODES)


def test_the_claimed_durations_agree() -> None:
    # The viewer waits this long in honest mode, so a drift here would make the panel feel wrong
    # while every klide test still passed.
    assert viewer.CLAIMED_MS == {w.value: m.milliseconds for w, m in FBINK_CLAIMS.items()}


def test_the_input_codes_agree() -> None:
    assert (viewer.TAP, viewer.SWIPE, viewer.BUTTON) == (
        EventKind.TAP,
        EventKind.SWIPE,
        EventKind.BUTTON,
    )
    assert (viewer.DIR_LEFT, viewer.DIR_RIGHT, viewer.DIR_UP, viewer.DIR_DOWN) == (
        Direction.LEFT,
        Direction.RIGHT,
        Direction.UP,
        Direction.DOWN,
    )
    assert (viewer.BTN_PAGE_BACK, viewer.BTN_PAGE_FORWARD) == (
        Button.PAGE_BACK,
        Button.PAGE_FORWARD,
    )


# It decodes what klide encodes


def test_the_viewer_decodes_a_klide_frame() -> None:
    message = encode_frame(a_frame(x=3, y=5), Waveform.GC16, page_id=7)
    stream = io.BytesIO(message)
    msg_type, body = viewer.read_message(stream)
    patch = viewer.decode_frame(body)
    assert msg_type == FRAME
    assert (patch.x, patch.y, patch.width, patch.height) == (3, 5, 4, 2)
    assert patch.waveform == Waveform.GC16.value
    assert patch.page_id == 7
    assert patch.levels == LEVELS


def test_the_viewer_decodes_a_full_panel_frame() -> None:
    panel = KOBO_LIBRA_2
    levels = bytes((i * 7) % panel.grey_levels for i in range(panel.width * panel.height))
    frame = Frame(panel, 0, 0, panel.width, panel.height, levels)
    _type, body = viewer.read_message(io.BytesIO(encode_frame(frame)))
    assert viewer.decode_frame(body).levels == levels


def test_the_viewer_decodes_an_odd_width_rectangle_without_the_padding_leaking() -> None:
    # Rows are padded to a whole byte, which is the part a second implementation gets wrong.
    panel = Panel(name="odd", width=3, height=2, grey_levels=16, ppi=300)
    frame = Frame(panel, 1, 1, 3, 2, bytes([1, 2, 3, 4, 5, 6]))
    _type, body = viewer.read_message(io.BytesIO(encode_frame(frame)))
    assert viewer.decode_frame(body).levels == bytes([1, 2, 3, 4, 5, 6])


def test_the_viewer_refuses_bad_magic() -> None:
    with pytest.raises(viewer.ProtocolError, match="bad magic"):
        viewer.read_message(io.BytesIO(b"XXXX" + bytes(HEADER_SIZE - 4)))


def test_the_viewer_refuses_a_truncated_message() -> None:
    with pytest.raises(viewer.ProtocolError):
        viewer.read_message(io.BytesIO(encode_frame(a_frame())[:-1]))


# klide decodes what the viewer encodes


def test_klide_reads_a_viewer_tap() -> None:
    raw = viewer.encode_input(viewer.TAP, x=640, y=900)
    assert read_input(io.BytesIO(raw)) == InputEvent.tap(640, 900)


def test_klide_reads_a_viewer_swipe() -> None:
    raw = viewer.encode_input(viewer.SWIPE, direction=viewer.DIR_UP)
    assert read_input(io.BytesIO(raw)) == InputEvent.swipe(Direction.UP)


def test_klide_reads_a_viewer_button_press() -> None:
    raw = viewer.encode_input(viewer.BUTTON, button=viewer.BTN_PAGE_FORWARD)
    assert read_input(io.BytesIO(raw)).button is Button.PAGE_FORWARD


# What it does with a decoded patch


def test_a_patch_is_painted_where_it_belongs() -> None:
    screen = viewer.Screen(4, 3)
    screen.apply(viewer.Patch(1, 1, 2, 1, "gl16", 0, bytes([0, 3])))
    assert list(screen.levels) == [15, 15, 15, 15, 15, 0, 3, 15, 15, 15, 15, 15]


def test_a_patch_is_clipped_rather_than_overflowing() -> None:
    screen = viewer.Screen(4, 2)
    screen.apply(viewer.Patch(3, 1, 4, 4, "gl16", 0, bytes(16)))
    assert len(screen.levels) == 8


def test_streamed_patches_converge_on_the_same_screen_klide_would_show() -> None:
    """The same property the streaming tests hold klide to, checked across the wire.

    The viewer paints rectangles into its own framebuffer, so if it ever placed one wrong the
    person looking at it would see a screen the device would never show, which is worse than
    showing nothing.
    """
    from klide.device import Device

    panel = Panel(name="small", width=8, height=6, grey_levels=16, ppi=300)
    device = Device(panel=panel)
    screen = viewer.Screen(panel.width, panel.height)

    patches = [
        Frame(panel, 0, 0, 8, 6, bytes([7] * 48)),
        Frame(panel, 2, 1, 4, 2, bytes([0, 1, 2, 3, 4, 5, 6, 7])),
        Frame(panel, 0, 5, 8, 1, bytes([9] * 8)),
    ]
    for patch in patches:
        device.receive(patch, Waveform.GL16)
        _type, body = viewer.read_message(io.BytesIO(encode_frame(patch)))
        screen.apply(viewer.decode_frame(body))

    assert bytes(screen.levels) == device.snapshot().levels


# The image it builds for Tk


def test_the_pgm_header_and_size_are_right() -> None:
    # Tk reads PGM natively, which is how the viewer avoids an imaging library entirely.
    data = viewer.to_pgm(bytes([0, 15, 8, 4]), 2, 2)
    assert data.startswith(b"P5\n2 2\n255\n")
    assert len(data) == len(b"P5\n2 2\n255\n") + 4


def test_levels_are_spread_across_the_full_range() -> None:
    data = viewer.to_pgm(bytes([0, 15]), 2, 1)
    assert data[-2:] == bytes([0, 255])
