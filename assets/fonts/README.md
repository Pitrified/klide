# Vendored fonts

DejaVu Sans, DejaVu Sans Bold and DejaVu Sans Mono, copied from this machine's
`fonts-dejavu-core` package. Licence in [`LICENSE-DejaVu.txt`](LICENSE-DejaVu.txt):
Bitstream Vera terms, which permit redistribution with the notice.

They are in the repo rather than loaded from the system for the same reason the walking skeleton
used Pillow's bundled face: a reference frame is only a gate if the same text renders to the same
bytes here, in a worktree and on a CI runner, and no runner is guaranteed to have a given font.

Pillow's bundled face was enough while everything was body text. Phase 4 renders code, diffs and
headings, which need a monospace and a bold, and Pillow ships neither.
