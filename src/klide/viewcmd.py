"""Render every view from fixtures and compare each against its reference.

The third gate of the same shape: the frame gate checks one static page, the session gate checks a
driven client, and this checks what the pages look like. A layout regression fails here and names
the page it moved, instead of being noticed on a device weeks later.

Everything it renders comes from `tests/fixtures`, never from the machine it runs on. A view fed
from live git state or a real transcript would compare a different page on every run, which is the
one thing a reference cannot survive.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from klide.ahp import ChangesetFile, ChangesetState, FileEdit, SessionState, SessionStatus
from klide.compare import (
    ReferenceMissingError,
    compare,
    load_reference,
    save_frame,
    write_difference,
)
from klide.panel import KOBO_LIBRA_2, Panel
from klide.render import Metrics, render_column
from klide.transcript import read
from klide.views import (
    Page,
    View,
    changes,
    conversation_page,
    one_diff,
    one_file,
    sessions,
)

ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "tests" / "fixtures"
REFERENCES = ROOT / "tests" / "references" / "views"
ARTIFACTS = ROOT / "build" / "frames" / "views"


def edit(path: str, added: int, removed: int, binary: bool = False) -> ChangesetFile:
    return ChangesetFile(
        id=path, edit=FileEdit(path=path, added=added, removed=removed, binary=binary)
    )


CHANGESET = ChangesetState(
    files=(
        edit("src/klide/render.py", 61, 28),
        edit("src/klide/views.py", 181, 0),
        edit("src/klide/document.py", 169, 0),
        edit("tests/references/views/changes.png", 0, 0, binary=True),
        edit("tests/test_views.py", 94, 0),
        edit("meta/gates.md", 14, 2),
        edit("README.md", 3, 1),
    )
)

#: The one a reader would tap into, and the one page 3 is drawn from.
CURRENT = SessionState(
    session_id="61a5d506-5366-4db2-a53b-9d3f15e75761",
    title="klide-g4-1",
    project="klide",
    branch="main",
    working_directories=("/home/pmn/repos/klide",),
    status=SessionStatus.IDLE | SessionStatus.IS_READ,
    activity="idle, last spoke assistant in turn de9a771c",
    turns=61,
    changeset=CHANGESET,
)

LIVE = [
    CURRENT,
    SessionState(
        session_id="3730563b-4457-4dca-97c4-9a40b11898fb",
        title="klide-g4-2",
        project="klide",
        branch="main",
        status=SessionStatus.INPUT_NEEDED,
        activity="input needed: AskUserQuestion in turn a7da92d6",
        turns=2577,
    ),
    SessionState(
        session_id="baa8ccea-bb7c-4f18-8fff-405faf76b9f1",
        title="linux-box-cloudflare",
        project="linux-box-cloudflare",
        branch="feat/tunnel-rotation",
        status=SessionStatus.IDLE | SessionStatus.IS_READ,
        activity="idle, last spoke assistant in turn 284e274b",
        turns=12,
    ),
]

#: The state this repo is in most of the time, and the one page 3 has to be designed for.
CLEAN = SessionState(
    session_id="61a5d506-5366-4db2-a53b-9d3f15e75761",
    title="klide-g4-1",
    project="klide",
    branch="main",
    status=SessionStatus.IDLE,
    turns=61,
)

SAMPLE_FILE = '''"""Panel geometry."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Panel:
    """A target screen, as far as anything drawing to it needs to care."""

    name: str
    width: int
    height: int
    grey_levels: int
    ppi: int

    def points_to_pixels(self, points: float) -> int:
        # A point is 1/72 inch, so a point size only means something with a ppi.
        return round(points / 72 * self.ppi)
'''


def build(panel: Panel = KOBO_LIBRA_2) -> dict[View, Page]:
    """Every page, laid out from the fixtures. No panel and no pixels involved."""
    metrics = Metrics.for_panel(panel)
    turns = read(FIXTURES / "transcript.jsonl")
    diff_text = (FIXTURES / "sample.diff").read_text()
    return {
        View.SESSIONS: sessions(LIVE, metrics),
        View.CONVERSATION: conversation_page(CURRENT, turns, metrics)[0],
        View.CHANGES: changes(CURRENT, metrics),
        # Two things at once, deliberately: the empty changeset, and the stale marker that is also
        # the refresh control. Both are states a reference would otherwise never see.
        View.CHANGES_EMPTY: changes(CLEAN, metrics, stale=True),
        # A path longer than the header, so the left trim is in the reference rather than in a
        # test alone.
        View.DIFF: one_diff(
            "src/klide/rendering/backends/experimental/render.py", diff_text, metrics
        ),
        View.FILE: one_file("src/klide/panel.py", SAMPLE_FILE, metrics, language="python"),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Render every view and check it.")
    parser.add_argument(
        "--update", action="store_true", help="write references instead of comparing"
    )
    args = parser.parse_args(argv)

    panel = KOBO_LIBRA_2
    pages = build(panel)
    failures = 0

    for view, page in pages.items():
        column = page.column
        frame = render_column(column, panel)
        produced = ARTIFACTS / f"{view.value}.png"
        save_frame(frame, produced)
        reference_path = REFERENCES / f"{view.value}.png"
        screens = frame.height // panel.height

        if args.update:
            save_frame(frame, reference_path)
            print(f"views: {view.value}: reference written, {screens} screens")
            continue

        try:
            expected = load_reference(reference_path, panel)
        except ReferenceMissingError as missing:
            print(f"views: {missing}")
            failures += 1
            continue

        # A view that changed height is a different page, not a different picture of the same one.
        if (frame.width, frame.height) != (expected.width, expected.height):
            failures += 1
            print(
                f"views: {view.value}: page is now {frame.height}px "
                f"({screens} screens), reference is {expected.height}px"
            )
            continue

        result = compare(frame, expected, view.value)
        if result.matched:
            print(f"views: {view.value}: matches, {len(column.lines)} lines, {screens} screens")
            continue
        failures += 1
        difference = ARTIFACTS / f"{view.value}.diff.png"
        write_difference(frame, expected, difference)
        print(f"views: {result.summary()}")
        print(f"views:   difference {difference.relative_to(ROOT)}, differing pixels in red")

    if args.update:
        print(f"views: wrote {len(pages)} references to {REFERENCES.relative_to(ROOT)}")
        return 0
    if failures:
        print(f"views: {failures} of {len(pages)} views differ")
        print("views: if the change was intended, re-run with --update and review the diffs")
        return 1
    print(f"views: all {len(pages)} views match their references")
    return 0


if __name__ == "__main__":
    sys.exit(main())
