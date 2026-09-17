"""The viewer is a second implementation of the protocol. This holds it to the contract.

`viewer/klide_viewer.py` ships to another machine as one file and imports no klide. That is
deliberate: a protocol only one codebase can speak has not been shown to be a protocol, and the
viewer is the first implementation written against the specification instead of sharing its code.
It is the strongest available check on AD5 short of the real Lua client.

Duplicating an implementation is only acceptable if divergence fails a gate, which is what this
file is. Everything the viewer copied from klide is checked against klide here: the constants, the
decoder, the input encoder, and the table of claimed refresh durations.

The viewer is loaded by path rather than imported as a package, because it is not one, and because
loading it the way the target machine does is part of what is being checked. It draws in a browser
and imports nothing but the standard library, so all of it loads on a headless box.
"""

import base64
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
    encode_input,
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
    # set up: uv reads the block and builds the environment.
    assert "requires-python" in _script_metadata()


def test_the_viewer_does_not_depend_on_a_graphical_toolkit() -> None:
    """The reason the viewer draws in a browser.

    This was a tkinter window through three pinned Python versions. tkinter is stdlib, but a Tcl/Tk
    the interpreter can find is not: one machine failed with `Can't find a usable init.tcl`, and
    another aborted inside Xlib on the first draw, with Tcl reporting its own threaded notifier.
    Each pin was a guess about a machine nobody here can run. A browser needs no pin, so the version
    is an ordinary floor again, and importing a toolkit would quietly bring the problem back.
    """
    source = VIEWER_PATH.read_text()
    for toolkit in ("import tkinter", "from tkinter", "import gi", "import PyQt", "import wx"):
        assert toolkit not in source
    assert _script_metadata()["requires-python"].startswith(">=3.")


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


# What it hands the browser


def test_a_patch_goes_over_as_a_png_and_where_to_put_it() -> None:
    # The page hands this to the browser's own decoder, so a change in shape here is a change in
    # what gets drawn, with nothing in between to catch it.
    import json

    event = viewer.as_event(viewer.Patch(3, 5, 2, 1, "gl16", 7, bytes([0, 15])))
    assert event.startswith(b"data: ") and event.endswith(b"\n\n")
    payload = json.loads(event[len(b"data: ") :])
    assert (payload["x"], payload["y"], payload["w"], payload["h"]) == (3, 5, 2, 1)
    assert payload["mode"] == "gl16"
    assert base64.b64decode(payload["png"]).startswith(b"\x89PNG\r\n\x1a\n")


def test_the_png_the_viewer_writes_is_the_image_it_was_given() -> None:
    """A PNG written by hand, read back by something that did not write it.

    The viewer ships as one file and cannot import an imaging library, so it writes the four chunks
    itself. Checking it with Pillow, which is klide's and not the viewer's, is the only way to know
    the bytes are a PNG rather than something this file agrees with itself about.
    """
    import io

    from PIL import Image

    levels = bytes([0, 5, 10, 15, 15, 10, 5, 0])
    data = viewer.to_png(levels, 4, 2)
    read = Image.open(io.BytesIO(data))
    assert read.mode == "L", "greyscale, or the browser is decoding something else"
    assert read.size == (4, 2)
    # 0-15 widened to 0-255 by multiplying by 17, which is exact at both ends.
    assert list(read.getdata()) == [value * 17 for value in levels]


def test_a_full_panel_png_is_small_enough_to_send_over_a_tunnel() -> None:
    """The reason for the PNG at all, kept as a number that would notice a regression.

    Frames were sent as one byte per pixel, base64-encoded: 2.8 MB for a full screen, which took
    several seconds per press for someone reaching the viewer through an SSH tunnel. A panel of
    rendered text is mostly one colour, so it deflates enormously. The bound here is loose on
    purpose: it is not measuring compression, it is catching a return to sending raw pixels.
    """
    panel = KOBO_LIBRA_2
    levels = bytes(15 if (i // panel.width) % 40 else 0 for i in range(panel.width * panel.height))
    data = viewer.to_png(levels, panel.width, panel.height)
    assert len(data) < len(levels) // 10, (
        f"a full panel is {len(data)} bytes, which is not far enough below the "
        f"{len(levels)} raw pixels to be worth the encoding"
    )


def test_a_browser_arriving_late_is_given_the_whole_screen() -> None:
    # Reloading the page, or opening it after the host has already drawn, has to show what is on
    # the panel rather than a blank one. The viewer keeps the framebuffer for exactly this.
    screen = viewer.Screen(4, 3)
    screen.apply(viewer.Patch(1, 1, 2, 1, "du", 0, bytes([0, 3])))
    whole = screen.whole()
    assert (whole.x, whole.y, whole.width, whole.height) == (0, 0, 4, 3)
    assert whole.levels == bytes([15, 15, 15, 15, 15, 0, 3, 15, 15, 15, 15, 15])


def test_the_page_is_told_the_panel_it_is_drawing() -> None:
    # The page has no klide in it and no way to guess these; they arrive by substitution.
    import json

    page = viewer.page_for(1264, 1680, 300).decode("utf-8")
    assert "__CONFIG__" not in page, "the placeholder was left in the served page"
    line = next(x for x in page.splitlines() if x.startswith("const CONFIG = "))
    config = json.loads(line[len("const CONFIG = ") : -1])
    assert (config["width"], config["height"], config["ppi"]) == (1264, 1680, 300)
    assert config["claimed"] == viewer.CLAIMED_MS
    assert config["dragThreshold"] == viewer.DRAG_THRESHOLD_PX


# What the browser sends back


def test_a_tap_from_the_page_reaches_klide() -> None:
    raw = viewer.input_from_json({"kind": "tap", "x": 640, "y": 900})
    assert read_input(io.BytesIO(raw)) == InputEvent.tap(640, 900)


def test_a_swipe_from_the_page_reaches_klide() -> None:
    raw = viewer.input_from_json({"kind": "swipe", "direction": "up"})
    assert read_input(io.BytesIO(raw)) == InputEvent.swipe(Direction.UP)


def test_a_button_from_the_page_reaches_klide() -> None:
    raw = viewer.input_from_json({"kind": "button", "button": "forward"})
    assert read_input(io.BytesIO(raw)).button is Button.PAGE_FORWARD


def test_an_event_the_page_should_never_send_is_refused_rather_than_guessed() -> None:
    # The POST body comes from a browser, which is the one part of this that is not ours.
    for nonsense in (
        {"kind": "nudge"},
        {"kind": "swipe", "direction": "widdershins"},
        {"kind": "button", "button": "home"},
    ):
        with pytest.raises(viewer.ProtocolError):
            viewer.input_from_json(nonsense)


# Taking messages out of a stream that arrives in pieces


def test_an_incomplete_buffer_yields_nothing_and_is_left_alone() -> None:
    # TCP delivers a megabyte frame in whatever pieces it likes, so a partial buffer is the normal
    # case rather than an error.
    message = encode_frame(a_frame())
    buffer = bytearray(message[:20])
    assert viewer.take_message(buffer) is None
    assert len(buffer) == 20


def test_a_complete_message_is_taken_and_consumed() -> None:
    buffer = bytearray(encode_frame(a_frame()))
    taken = viewer.take_message(buffer)
    assert taken is not None
    assert taken[0] == FRAME
    assert buffer == bytearray()


def test_a_frame_arriving_in_many_small_pieces_is_reassembled() -> None:
    """The case that matters: a full-panel frame is about a megabyte and never arrives at once."""
    panel = KOBO_LIBRA_2
    levels = bytes((i * 5) % panel.grey_levels for i in range(panel.width * panel.height))
    message = encode_frame(Frame(panel, 0, 0, panel.width, panel.height, levels))

    buffer = bytearray()
    taken = None
    for start in range(0, len(message), 4096):
        buffer += message[start : start + 4096]
        taken = viewer.take_message(buffer)
        if taken is not None:
            break
    assert taken is not None, "never reassembled"
    assert viewer.decode_frame(taken[1]).levels == levels
    assert buffer == bytearray()


def test_two_messages_in_one_read_are_taken_one_at_a_time() -> None:
    buffer = bytearray(encode_frame(a_frame()) + encode_input(InputEvent.tap(1, 2)))
    first = viewer.take_message(buffer)
    second = viewer.take_message(buffer)
    assert first is not None and second is not None
    assert (first[0], second[0]) == (FRAME, INPUT)
    assert viewer.take_message(buffer) is None


def test_bad_magic_in_the_buffer_is_refused_rather_than_resynced() -> None:
    with pytest.raises(viewer.ProtocolError, match="bad magic"):
        viewer.take_message(bytearray(b"XXXX" + bytes(20)))


def test_frames_arriving_in_pieces_reach_a_watching_browser() -> None:
    """The reader thread, the framebuffer and the event stream, over a real socket pair.

    Each half has a test above; this is the one that would notice them being wired together wrong.
    It uses a socketpair rather than a mock because the thing being checked is that bytes divided
    the way a socket divides them still come out as one patch.
    """
    import json
    import socket as socketlib

    panel = Panel(name="pair", width=8, height=6, grey_levels=16, ppi=300)
    host_end, viewer_end = socketlib.socketpair()
    bridge = viewer.Bridge(viewer_end, panel.width, panel.height)
    outbox = bridge.subscribe()
    assert outbox.get(timeout=5), "a new watcher gets the screen as it stands"

    message = encode_frame(Frame(panel, 2, 1, 4, 2, bytes([0, 1, 2, 3, 4, 5, 6, 7])))
    for start in range(0, len(message), 3):
        host_end.sendall(message[start : start + 3])

    payload = json.loads(outbox.get(timeout=5)[len(b"data: ") :])
    assert (payload["x"], payload["y"], payload["w"], payload["h"]) == (2, 1, 4, 2)
    import io

    from PIL import Image

    drawn = Image.open(io.BytesIO(base64.b64decode(payload["png"])))
    assert list(drawn.getdata()) == [value * 17 for value in (0, 1, 2, 3, 4, 5, 6, 7)]

    host_end.close()
    assert outbox.get(timeout=5) is None, "the watcher is told when the host goes"
