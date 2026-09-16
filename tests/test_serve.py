"""Serving a live session to a viewer, checked without a viewer.

The window needs a person, and none of what is under it does. What is checked here is the part that
would otherwise only be found by pressing a button and seeing nothing happen: where the history
window sits, what a press moves, and that a real client on a real socket receives real frames.
"""

import json
import socket
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from klide.host import serve
from klide.input import Button, Direction, InputEvent
from klide.panel import KOBO_LIBRA_2
from klide.protocol import encode_input, read_frame
from klide.render import Metrics
from klide.serve import LiveState, apply_event, render, title_for
from klide.serve import run as serve_live
from klide.transcript import Block, BlockKind, Role, Turn

METRICS = Metrics.for_panel(KOBO_LIBRA_2)


def turns(count: int) -> list[Turn]:
    return [
        Turn(role=Role.ASSISTANT, blocks=(Block(BlockKind.TEXT, f"turn {i}"),))
        for i in range(count)
    ]


# Where the reader is looking


def test_a_new_session_follows_the_live_tail() -> None:
    state = LiveState(window=4, turns=turns(10))
    assert state.following
    assert [t.text for t in state.visible()] == ["turn 6", "turn 7", "turn 8", "turn 9"]


def test_paging_back_walks_into_history() -> None:
    state = LiveState(window=4, turns=turns(10))
    assert state.page_back()
    assert not state.following
    assert [t.text for t in state.visible()] == ["turn 2", "turn 3", "turn 4", "turn 5"]


def test_paging_back_stops_at_the_beginning() -> None:
    state = LiveState(window=4, turns=turns(6))
    assert state.page_back()
    assert not state.page_back()  # nothing moved, so nothing is redrawn


def test_paging_forward_returns_to_the_tail() -> None:
    state = LiveState(window=4, turns=turns(10))
    state.page_back()
    assert state.page_forward()
    assert state.following


def test_paging_forward_at_the_tail_does_nothing() -> None:
    state = LiveState(window=4, turns=turns(10))
    assert not state.page_forward()


def test_a_tap_returns_to_the_tail_from_anywhere() -> None:
    state = LiveState(window=2, turns=turns(20))
    for _ in range(4):
        state.page_back()
    assert not state.following
    assert apply_event(InputEvent.tap(600, 800), state)
    assert state.following


def test_a_tap_at_the_tail_changes_nothing() -> None:
    state = LiveState(window=2, turns=turns(20))
    assert not apply_event(InputEvent.tap(600, 800), state)


def test_the_buttons_page_both_ways() -> None:
    state = LiveState(window=2, turns=turns(20))
    assert apply_event(InputEvent.press(Button.PAGE_BACK), state)
    assert apply_event(InputEvent.press(Button.PAGE_FORWARD), state)


def test_a_swipe_pages_like_a_button() -> None:
    state = LiveState(window=2, turns=turns(20))
    assert apply_event(InputEvent.swipe(Direction.LEFT), state)
    assert apply_event(InputEvent.swipe(Direction.RIGHT), state)


def test_an_empty_session_renders_rather_than_failing() -> None:
    # The viewer connects before anything has been said, every time.
    frame = render(LiveState(), KOBO_LIBRA_2, METRICS)
    assert frame.is_full_panel


def test_the_title_says_when_you_are_in_history() -> None:
    # Otherwise a reader who paged back cannot tell a quiet session from a stale screen.
    state = LiveState(window=2, turns=turns(10))
    assert title_for(state) == "live"
    state.page_back()
    assert title_for(state) == "history, 2 back"


# Over a real socket


def test_a_client_receives_a_frame_and_its_presses_are_acted_on(tmp_path: Path) -> None:
    """End to end on TCP: connect, get a frame, send a press, get another frame.

    Uses the protocol rather than the viewer module, because this is checking the host half. The
    viewer's own half is checked in test_viewer.py.
    """
    transcript = tmp_path / "t.jsonl"
    records = [
        {"type": "assistant", "message": {"role": "assistant", "content": f"line {i}"}}
        for i in range(12)
    ]
    transcript.write_text("\n".join(json.dumps(r) for r in records) + "\n")

    port = _free_port()
    received: list[int] = []
    done = threading.Event()

    def client() -> None:
        sock = socket.create_connection(("127.0.0.1", port), timeout=10)
        with sock, sock.makefile("rb") as stream:
            frame, _waveform, _page = read_frame(stream, KOBO_LIBRA_2)
            received.append(frame.height)
            sock.sendall(encode_input(InputEvent.press(Button.PAGE_BACK)))
            frame, _waveform, _page = read_frame(stream, KOBO_LIBRA_2)
            received.append(frame.height)
        done.set()

    def host() -> None:
        with serve(("127.0.0.1", port), timeout=10) as link:
            serve_live(link, transcript, KOBO_LIBRA_2, METRICS, window=3, seconds=5.0)

    with ThreadPoolExecutor(max_workers=2) as pool:
        serving = pool.submit(host)
        pool.submit(client)
        assert done.wait(20), "client never finished"
        serving.result()

    assert len(received) == 2
    # The first is the whole screen; the second is the rectangle that paging changed.
    assert received[0] == KOBO_LIBRA_2.height
    assert 0 < received[1] <= KOBO_LIBRA_2.height


def _free_port() -> int:
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return int(probe.getsockname()[1])


def test_a_press_is_answered_without_waiting_for_the_coalescer() -> None:
    # A person pressing a button should not wait behind a transcript poll. The loop answers a press
    # at once and only new content waits to settle, which is checked here by the state change being
    # immediate rather than by timing anything.
    state = LiveState(window=2, turns=turns(20))
    assert apply_event(InputEvent.press(Button.PAGE_BACK), state) is True
