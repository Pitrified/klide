#!/usr/bin/env python3
"""A phase's status must be the same in its own frontmatter and in tracking.md.

The two drift whenever a phase is opened or closed in one place and not the
other, and a plan folder that lies about where the work stands is worse than
no plan folder. Checks every plans/*/tracking.md against its sibling files.
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PLANS = ROOT / "plans"
VALID = {"draft", "planned", "in progress", "done", "superseded", "discarded"}
ROW = re.compile(r"^\|\s*\d+\s*\|[^|]*\|\s*\[`([^`]+)`\][^|]*\|\s*([^|]+?)\s*\|\s*$")
FRONT = re.compile(r"\Astatus:\s*(.+)$", re.MULTILINE)


def frontmatter_status(md: Path) -> str | None:
    text = md.read_text()
    if not text.startswith("---\n"):
        return None
    block = text.split("---\n", 2)[1]
    match = FRONT.search(block)
    return match.group(1).strip() if match else None


def main() -> int:
    findings = []
    for tracking in sorted(PLANS.glob("*/tracking.md")):
        listed = set()
        for line_no, line in enumerate(tracking.read_text().splitlines(), 1):
            row = ROW.match(line)
            if not row:
                continue
            name, table_status = row.group(1), row.group(2)
            listed.add(name)
            where = f"{tracking.relative_to(ROOT)}:{line_no}"
            phase = tracking.parent / name
            if not phase.exists():
                findings.append(f"{where}: table names {name}, which does not exist")
                continue
            if table_status not in VALID:
                findings.append(f"{where}: status {table_status!r} is not one of {sorted(VALID)}")
            own = frontmatter_status(phase)
            if own is None:
                findings.append(f"{phase.relative_to(ROOT)}: no status in frontmatter")
            elif own != table_status:
                findings.append(
                    f"{where}: table says {table_status!r}, "
                    f"{phase.relative_to(ROOT)} says {own!r}"
                )
        for phase in sorted(tracking.parent.glob("[0-9][0-9]_*.md")):
            if phase.name.startswith("00_") or phase.name in listed:
                continue
            findings.append(
                f"{phase.relative_to(ROOT)}: phase file missing from "
                f"{tracking.relative_to(ROOT)}"
            )
    for f in findings:
        print(f"plan status: {f}")
    if findings:
        print(f"\n{len(findings)} inconsistency. The files and the table have to agree.")
        return 1
    print("plan status: every phase agrees with its tracking table")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
