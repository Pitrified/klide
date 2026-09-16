#!/usr/bin/env bash
# Point git at the versioned hooks directory. One command per clone.
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
git config core.hooksPath .githooks
echo "core.hooksPath = .githooks"
echo "hooks now active: $(ls .githooks | tr '\n' ' ')"
