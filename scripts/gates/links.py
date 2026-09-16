#!/usr/bin/env python3
"""Relative markdown links must resolve to a file in the repo.

Absolute URLs and anchors are ignored: this checks the links that rot silently
when a file is renamed, which is the failure the plan folders actually hit.
"""
import re
import sys
from pathlib import Path

LINK = re.compile(r"\[[^\]]*\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
ROOT = Path(__file__).resolve().parents[2]


def broken(md: Path) -> list[str]:
    out = []
    for line_no, line in enumerate(md.read_text().splitlines(), 1):
        for target in LINK.findall(line):
            if target.startswith(("http://", "https://", "mailto:", "#")):
                continue
            path = (md.parent / target.split("#", 1)[0]).resolve()
            if not path.exists():
                out.append(f"{md.relative_to(ROOT)}:{line_no}: {target}")
    return out


def main(argv: list[str]) -> int:
    files = [Path(a).resolve() for a in argv] or sorted(ROOT.rglob("*.md"))
    files = [f for f in files if ".git" not in f.parts]
    findings = [f for md in files for f in broken(md)]
    for f in findings:
        print(f"broken link: {f}")
    if findings:
        print(f"\n{len(findings)} broken link(s). Fix the path or the file name.")
        return 1
    print(f"links: {len(files)} file(s) checked, all targets resolve")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
