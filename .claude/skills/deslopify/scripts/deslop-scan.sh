#!/usr/bin/env bash
# Mechanical scan for AI writing tells. Reports findings; it does not edit.
# Usage: deslop-scan.sh [--quiet] FILE...
#   --quiet         counts only, no matched lines
#   --only A,B      restrict to these categories (pattern file names without the number)
# Exit: 0 clean, 1 findings, 2 usage error.
set -uo pipefail

SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PATTERN_DIR="$SKILL_DIR/patterns"
QUIET=0
MAX_SHOWN=8
ONLY=""

while [[ ${1-} == --* ]]; do
  case "$1" in
    --quiet) QUIET=1; shift ;;
    --only) ONLY="${2-}"; shift 2 ;;   # comma-separated category names
    *) echo "unknown option: $1" >&2; exit 2 ;;
  esac
done

if [[ $# -eq 0 ]]; then
  echo "usage: $(basename "$0") [--quiet] FILE..." >&2
  exit 2
fi

# Fenced code blocks are stripped before scanning: shell and code legitimately
# contain banned words. Line numbers are preserved by blanking, not deleting.
strip_code() {
  awk '/^[[:space:]]*```/ {fence = !fence; print ""; next} {print (fence ? "" : $0)}' "$1"
}

total=0
for file in "$@"; do
  [[ -f $file ]] || { echo "no such file: $file" >&2; exit 2; }
  case "$(cd "$(dirname "$file")" && pwd)/$(basename "$file")" in
    "$SKILL_DIR"/*) echo "skipped (this skill's own files): $file"; continue ;;
  esac

  body="$(strip_code "$file")"
  file_total=0
  report=""

  for patterns in "$PATTERN_DIR"/*.txt; do
    category="$(basename "$patterns" .txt)"; category="${category#[0-9][0-9]_}"
    if [[ -n $ONLY && ",$ONLY," != *",$category,"* ]]; then continue; fi
    hits="$(printf '%s\n' "$body" | grep -Ein -f "$patterns" || true)"
    [[ -z $hits ]] && continue
    n=$(printf '%s\n' "$hits" | wc -l)
    file_total=$((file_total + n))
    report+="  $category: $n"$'\n'
    if [[ $QUIET -eq 0 ]]; then
      report+="$(printf '%s\n' "$hits" | head -n "$MAX_SHOWN" | sed 's/^/    /')"$'\n'
      [[ $n -gt $MAX_SHOWN ]] && report+="    ... $((n - MAX_SHOWN)) more"$'\n'
    fi
  done

  # Cadence: runs of four or more consecutive sentences within 4 words of each other.
  # Tables, lists and headers are dropped first; they are not prose and their
  # regularity is not a tell. Sentences under 8 words are skipped for the same reason.
  # A run has to sit inside one paragraph. Counting across blank lines measures the
  # document's structure rather than the writer's rhythm, and fires on every list.
  cadence="$(printf '%s\n' "$body" | grep -Ev '^[[:space:]]*([-*|#>]|[0-9]+\.)' \
    | awk 'NF == 0 {print "==PARA=="; next} {printf "%s ", $0} END {print ""}' \
    | sed 's/[.!?][])"]* /\n/g' \
    | awk 'BEGIN {run = 1; worst = 1}
           /==PARA==/ {run = 1; prev = -99; next}
           NF < 8 {run = 1; prev = -99; next}
           (NF - prev <= 4 && prev - NF <= 4) {run++; if (run > worst) worst = run; prev = NF; next}
           {run = 1; prev = NF}
           END {print worst+0}')"
  if [[ -z $ONLY || ",$ONLY," == *",cadence,"* ]] && [[ ${cadence:-0} -ge 4 ]]; then
    file_total=$((file_total + 1))
    report+="  cadence: $cadence consecutive sentences of near-identical length"$'\n'
  fi

  if [[ $file_total -eq 0 ]]; then
    echo "clean: $file"
  else
    echo "$file: $file_total finding(s)"
    printf '%s' "$report"
  fi
  total=$((total + file_total))
done

echo
if [[ $total -eq 0 ]]; then
  echo "no findings"
  exit 0
fi
echo "$total finding(s). Each one is a finding, not an automatic edit: triage per SKILL.md."
exit 1
