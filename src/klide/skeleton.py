"""The walking skeleton, end to end, in one command.

Render a frame on the host, carry it over the wire, have the simulator display it, compare what
was displayed against the stored reference. Thin but complete: every piece the later phases widen
is present here in its smallest honest form.

    uv run klide-skeleton              # run it, and fail if the frame changed
    uv run klide-skeleton --update     # accept the current output as the reference
"""

from __future__ import annotations

import argparse
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from klide.compare import (
    ReferenceMissingError,
    compare,
    load_reference,
    save_frame,
    write_difference,
)
from klide.frame import Frame
from klide.host import serve_once
from klide.panel import KOBO_LIBRA_2, Panel
from klide.render import render_text
from klide.simulator import display, receive_once

ROOT = Path(__file__).resolve().parents[2]
REFERENCES = ROOT / "tests" / "references"
ARTIFACTS = ROOT / "build" / "frames"

# Fixed on purpose. The reference is only meaningful if the input never drifts, so the skeleton's
# page is a constant rather than anything read from the machine it runs on.
PAGE = """klide walking skeleton

The host renders this page at the panel's own size and sends it over the wire
as one frame. The simulator receives it, writes it out as an image, and the
comparison checks it against the reference stored in the repo.

Nothing here is streamed, nothing is a dirty rectangle, and nothing is
markdown. Those are phases 3 and 4. What this proves is that a frame can go
from the host to the panel and be checked, which is the loop every later
phase is verified by.

    panel   kobo-libra-2, 1264x1680
    depth   4 bits per pixel, 16 grey levels
    wire    KLD1, an 18 byte header and packed rows
"""


def run_once(panel: Panel, socket_path: Path) -> Frame:
    """Render, serve and receive, returning what actually arrived at the simulator.

    The frame that gets compared is the received one rather than the rendered one. Comparing the
    rendered frame would check the renderer and skip the wire entirely, which is most of what this
    phase exists to prove.
    """
    frame = render_text(PAGE, panel)
    with ThreadPoolExecutor(max_workers=1) as pool:
        serving = pool.submit(serve_once, frame, socket_path)
        received = receive_once(socket_path, panel)
        serving.result()
    return received


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--update",
        action="store_true",
        help="write the current output as the reference instead of comparing against it",
    )
    parser.add_argument("--name", default="skeleton", help="reference name (default: skeleton)")
    args = parser.parse_args(argv)

    panel = KOBO_LIBRA_2
    reference_path = REFERENCES / f"{args.name}.png"

    with tempfile.TemporaryDirectory(prefix="klide-") as tmp:
        received = run_once(panel, Path(tmp) / "klide.sock")

    displayed = display(received, ARTIFACTS / f"{args.name}.png")

    if args.update:
        save_frame(received, reference_path)
        print(f"frames: wrote reference {reference_path.relative_to(ROOT)}")
        return 0

    try:
        reference = load_reference(reference_path, panel)
    except ReferenceMissingError as missing:
        # A gate's failure has to say what to do (see meta/gates.md), and a traceback does not.
        print(f"frames: {missing}", file=sys.stderr)
        print(f"frames: rendered {displayed.relative_to(ROOT)}", file=sys.stderr)
        return 1
    result = compare(received, reference, args.name)
    print(f"frames: {result.summary()}")
    if result.matched:
        return 0

    difference = ARTIFACTS / f"{args.name}.diff.png"
    write_difference(received, reference, difference)
    print(f"frames: rendered  {displayed.relative_to(ROOT)}")
    print(f"frames: reference {reference_path.relative_to(ROOT)}")
    print(f"frames: difference {difference.relative_to(ROOT)}, differing pixels in red")
    print("frames: if the change was intended, re-run with --update and review the image diff")
    return 1


if __name__ == "__main__":
    sys.exit(main())
