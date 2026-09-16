#!/usr/bin/env bash
# Every gate, one command. CI runs this same script, so a green run here means
# a green run there. Add a gate by adding a line; keep each one fast enough
# that an agent will actually run it.
set -uo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."

failed=()
run() {
  local name="$1"; shift
  echo "--- $name"
  if "$@"; then echo "    ok"; else failed+=("$name"); echo "    FAILED"; fi
}

mapfile -t MD < <(git ls-files '*.md')

run "links"       python3 scripts/gates/links.py "${MD[@]}"
run "plan status" python3 scripts/gates/plan_status.py
run "house style" .claude/skills/deslopify/scripts/deslop-scan.sh --only house_rules --quiet "${MD[@]}"

# Python gates. `uv run` syncs the locked environment first, so these need no
# setup beyond uv itself and they run the same versions everywhere.
run "format"      uv run --quiet ruff format --check .
run "lint"        uv run --quiet ruff check .
run "types"       uv run --quiet mypy
run "test"        uv run --quiet pytest -q

echo
if [[ ${#failed[@]} -eq 0 ]]; then
  echo "all gates passed"
  exit 0
fi
echo "failed: ${failed[*]}"
exit 1
