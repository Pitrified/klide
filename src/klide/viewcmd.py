"""Render every view from fixtures and compare each against its reference.

The third gate of the same shape: the frame gate checks one static page, the session gate checks a
driven client, and this checks what the six views look like. A layout regression fails here and
names the view it moved, instead of being noticed on a device weeks later.

Everything it renders comes from `tests/fixtures`, never from the machine it runs on. A view fed
from live git state or a real transcript would compare a different page on every run, which is the
one thing a reference cannot survive.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from klide.compare import (
    ReferenceMissingError,
    compare,
    load_reference,
    save_frame,
    write_difference,
)
from klide.panel import KOBO_LIBRA_2, Panel
from klide.render import Metrics, render_column
from klide.text import Column
from klide.transcript import read
from klide.views import (
    ChangedFile,
    Session,
    View,
    changed_files,
    conversation,
    conversations,
    file_tree,
    one_diff,
    one_file,
)

ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "tests" / "fixtures"
REFERENCES = ROOT / "tests" / "references" / "views"
ARTIFACTS = ROOT / "build" / "frames" / "views"

SESSIONS = [
    Session(name="klide, phase 4", turns=5, updated="today", current=True),
    Session(name="klide, phase 3", turns=61, updated="today"),
    Session(name="linux-box-cloudflare", turns=12, updated="yesterday"),
]

CHANGED = [
    ChangedFile(path="src/klide/render.py", added=61, removed=28),
    ChangedFile(path="src/klide/views.py", added=181, removed=0),
    ChangedFile(path="src/klide/document.py", added=169, removed=0),
    ChangedFile(path="tests/test_views.py", added=94, removed=0),
    ChangedFile(path="meta/gates.md", added=14, removed=2),
]

TREE = [
    "src/klide/frame.py",
    "src/klide/panel.py",
    "src/klide/render.py",
    "src/klide/views.py",
    "tests/test_views.py",
    "docs/protocol.md",
    "docs/simulator.md",
    "README.md",
]

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


def build(panel: Panel = KOBO_LIBRA_2) -> dict[View, Column]:
    """Every view, laid out from the fixtures. No panel and no pixels involved."""
    metrics = Metrics.for_panel(panel)
    turns = read(FIXTURES / "transcript.jsonl")
    diff_text = (FIXTURES / "sample.diff").read_text()
    return {
        View.CONVERSATION: conversation(turns, metrics),
        View.CONVERSATIONS: conversations(SESSIONS, metrics),
        View.CHANGED_FILES: changed_files(CHANGED, metrics),
        View.DIFF: one_diff("src/klide/render.py", diff_text, metrics),
        View.FILE_TREE: file_tree(TREE, metrics),
        View.FILE: one_file("src/klide/panel.py", SAMPLE_FILE, metrics, language="python"),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Render every view and check it.")
    parser.add_argument(
        "--update", action="store_true", help="write references instead of comparing"
    )
    args = parser.parse_args(argv)

    panel = KOBO_LIBRA_2
    columns = build(panel)
    failures = 0

    for view, column in columns.items():
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
        print(f"views: wrote {len(columns)} references to {REFERENCES.relative_to(ROOT)}")
        return 0
    if failures:
        print(f"views: {failures} of {len(columns)} views differ")
        print("views: if the change was intended, re-run with --update and review the diffs")
        return 1
    print(f"views: all {len(columns)} views match their references")
    return 0


if __name__ == "__main__":
    sys.exit(main())
