"""Serving a live session to a viewer, checked without a viewer.

A screen needs a person, and none of what is under it does. What is checked here is the part that
would otherwise only be found by pressing a button and seeing nothing happen: where the history
screen sits, what a press moves, and that a real client on a real socket receives real frames.
"""

import json
import socket
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from klide.frame import Frame
from klide.host import serve
from klide.input import Button, Direction, InputEvent
from klide.panel import KOBO_LIBRA_2, Panel
from klide.protocol import encode_input, read_frame
from klide.render import Metrics
from klide.serve import LiveState, apply_event, fill, render, title_for
from klide.serve import run as serve_live
from klide.transcript import Block, BlockKind, Role, Turn
from klide.views import conversation

METRICS = Metrics.for_panel(KOBO_LIBRA_2)


def turns(count: int) -> list[Turn]:
    return [
        Turn(role=Role.ASSISTANT, blocks=(Block(BlockKind.TEXT, f"turn {i}"),))
        for i in range(count)
    ]


# Where the reader is looking


def fills(state: LiveState) -> list[str]:
    """The screen as text, header and padding dropped, so a test can read what is on it."""
    lines = fill(state, METRICS)
    header = conversation([], METRICS, title=title_for(state), subtitle=f"{len(state.turns)} turns")
    return [line.text for line in lines[len(header.lines) :] if line.text]


def test_the_screen_is_filled_rather_than_a_fixed_number_of_turns() -> None:
    """The fault a person found: short shell turns left the bottom two thirds of the panel blank.

    Six turns was a constant, and a constant cannot know how tall a turn is.
    """
    state = LiveState(turns=turns(200))
    lines = fill(state, METRICS)
    assert len(lines) == METRICS.lines_per_screen, "the screen is filled to its last line"
    assert state.shown > 6, f"only {state.shown} turns on a screen that holds more"


def test_the_newest_turn_sits_on_the_bottom_margin() -> None:
    # The point of filling from the bottom: the newest thing is always in the same place.
    state = LiveState(turns=turns(200))
    assert fills(state)[-1] == "turn 199"


def test_a_short_session_still_sits_at_the_bottom() -> None:
    # Too little to fill the screen, so the gap goes above the text rather than below it.
    state = LiveState(turns=turns(2))
    lines = fill(state, METRICS)
    assert lines[-1].text == "turn 1"
    assert not lines[-3].text or lines[-3].text == "turn 0"


def test_a_new_turn_pushes_the_oldest_off_the_top() -> None:
    state = LiveState(turns=turns(200))
    before = fills(state)
    state.turns.append(
        Turn(role=Role.ASSISTANT, blocks=(Block(BlockKind.TEXT, "the newest thing"),))
    )
    after = fills(state)
    assert after[-1] == "the newest thing"
    assert after[0] != before[0], "the top line moved up"
    assert before[-1] in after, "what was newest is still on screen, higher up"


def test_the_oldest_turn_on_screen_is_clipped_rather_than_dropped() -> None:
    """A tall turn at the top shows its end, the way a terminal shows the end of a long line.

    Dropping it instead would leave a blank band at the top whenever the oldest turn that nearly
    fit did not quite, which is the same wasted screen in a new place.
    """
    tall = Turn(role=Role.ASSISTANT, blocks=(Block(BlockKind.TEXT, "long\n" * 60),))
    state = LiveState(turns=[tall, *turns(3)])
    lines = fill(state, METRICS)
    assert len(lines) == METRICS.lines_per_screen
    assert lines[-1].text == "turn 2"


def test_a_new_session_follows_the_live_tail() -> None:
    state = LiveState(turns=turns(10))
    assert state.following
    assert fills(state)[-1] == "turn 9"


def test_paging_back_walks_into_history_by_a_screenful() -> None:
    state = LiveState(turns=turns(200))
    fill(state, METRICS)
    screenful = state.shown
    assert state.page_back()
    assert not state.following
    assert state.offset == screenful, "a page is however many turns were on the screen"
    assert fills(state)[-1] == f"turn {199 - screenful}"


def test_paging_back_stops_at_the_beginning() -> None:
    state = LiveState(turns=turns(200))
    fill(state, METRICS)
    while state.page_back():
        fill(state, METRICS)
    assert not state.page_back()  # nothing moved, so nothing is redrawn


def test_paging_back_does_nothing_when_it_all_fits() -> None:
    state = LiveState(turns=turns(2))
    fill(state, METRICS)
    assert not state.page_back(), "there is no history behind a screen that holds everything"


def test_paging_forward_returns_to_the_tail() -> None:
    state = LiveState(turns=turns(200))
    fill(state, METRICS)
    state.page_back()
    assert state.page_forward()
    assert state.following


def test_paging_forward_at_the_tail_does_nothing() -> None:
    state = LiveState(turns=turns(10))
    assert not state.page_forward()


def test_a_tap_returns_to_the_tail_from_anywhere() -> None:
    state = LiveState(turns=turns(200))
    fill(state, METRICS)
    for _ in range(4):
        state.page_back()
        fill(state, METRICS)
    assert not state.following
    assert apply_event(InputEvent.tap(600, 800), state)
    assert state.following


def test_a_tap_at_the_tail_changes_nothing() -> None:
    state = LiveState(turns=turns(20))
    assert not apply_event(InputEvent.tap(600, 800), state)


def test_the_buttons_page_both_ways() -> None:
    state = LiveState(turns=turns(200))
    fill(state, METRICS)
    assert apply_event(InputEvent.press(Button.PAGE_BACK), state)
    assert apply_event(InputEvent.press(Button.PAGE_FORWARD), state)


def test_a_swipe_pages_like_a_button() -> None:
    state = LiveState(turns=turns(200))
    fill(state, METRICS)
    assert apply_event(InputEvent.swipe(Direction.LEFT), state)
    assert apply_event(InputEvent.swipe(Direction.RIGHT), state)


def test_an_empty_session_renders_rather_than_failing() -> None:
    # The viewer connects before anything has been said, every time.
    frame = render(LiveState(), KOBO_LIBRA_2, METRICS)
    assert frame.is_full_panel


def test_the_cap_limits_how_far_back_the_fill_reaches() -> None:
    # The knob the browser harness uses to force a small screenful.
    state = LiveState(turns=turns(200), cap=3)
    assert fills(state) == ["claude", "turn 197", "turn 198", "turn 199"]


def test_the_title_says_when_you_are_in_history() -> None:
    # Otherwise a reader who paged back cannot tell a quiet session from a stale screen.
    state = LiveState(turns=turns(200))
    fill(state, METRICS)
    assert title_for(state) == "live"
    screenful = state.shown
    state.page_back()
    assert title_for(state) == f"history, {screenful} back"


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
            serve_live(link, transcript, KOBO_LIBRA_2, METRICS, cap=3, seconds=5.0)

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
    state = LiveState(turns=turns(20))
    assert apply_event(InputEvent.press(Button.PAGE_BACK), state) is True


#: A panel small enough that a frame is a couple of bytes, for tests about the link rather than
#: about what is drawn on it.
TINY = Panel(name="tiny", width=2, height=1, grey_levels=16, ppi=300)


def test_a_quiet_reader_is_not_mistaken_for_a_departed_one() -> None:
    """A session must not end because nobody pressed anything.

    `--wait` is how long to wait for a viewer to connect. It was also being used as the read
    timeout on the connection once there was one, so a host told to wait two hours also stopped two
    hours after the last press. Measured before it was understood: a host started at 09:55:28 died
    at 11:55:39, which is 7200 seconds to the second.

    A short `timeout` with no `read_timeout` is the shape that would have caught it: the accept
    budget is nearly spent and the connection still must not time out.
    """
    port = _free_port()
    with ThreadPoolExecutor(max_workers=1) as pool:
        connecting = pool.submit(_connect_after, port, 0.2)
        with serve(("127.0.0.1", port), timeout=1.0) as link:
            client = connecting.result(timeout=5)
            try:
                assert link._conn.gettimeout() is None, (
                    "the connection must not inherit the accept budget, or a reader who presses "
                    "nothing for that long ends the session"
                )
                time.sleep(1.5)  # longer than the accept timeout, saying nothing at all
                link.send_frame(Frame(TINY, 0, 0, 2, 1, bytes([0, 15])))
                assert client.recv(64), "the link is still usable after being idle"
            finally:
                client.close()


def _connect_after(port: int, delay: float) -> socket.socket:
    time.sleep(delay)
    return socket.create_connection(("127.0.0.1", port), timeout=5)
