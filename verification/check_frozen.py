"""Check that the submitted (frozen) manuscript sets are unchanged.

Run as: python -I verification/check_frozen.py

A submitted set is a <folder>/submission/ holding a SUBMITTED_*.txt record, written when the author
submitted it, that lists the SHA-256 of every file sent ("<sha256> [*]<name>" lines). Such a set
is frozen: the build refuses to write into it, and later work goes into a new folder. Its files
can no longer be tied to their Markdown by verification/check_docx_tie.py, because the author may
have edited a file in Word before uploading (as with both cover letters); this check proves
instead that each submitted file is still byte for byte what was sent, and that nothing has been
added to the set. Word's lock files (~$*) and the _render folder are ignored.

The folders: manuscript/ (Primary Care Diabetes), manuscript/v2/ (IJTLD) and manuscript/v3/
(Diabetes & Metabolic Syndrome: Clinical Research & Reviews). The manuscript
folders are private and git-ignored: "SKIPPED" when none is present. Exit 1 on any problem.
"""
from __future__ import annotations

import hashlib
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FOLDERS = ("manuscript", "manuscript/v2", "manuscript/v3")
LINE = re.compile(r"(?m)^([0-9a-f]{64}) +\*?(\S.*?)\s*$")


def problems(sub: Path) -> tuple[list[str], int]:
    """(problems, number of files verified) for one submitted set."""
    recs = sorted(sub.glob("SUBMITTED_*.txt"))
    if len(recs) != 1:
        return [f"FROZEN {sub}: expected one SUBMITTED_*.txt record, found {len(recs)}"], 0
    want = {name: h for h, name in LINE.findall(recs[0].read_text(encoding="utf-8"))}
    if not want:
        return [f"FROZEN {sub}: {recs[0].name} lists no SHA-256"], 0
    out = []
    for name, h in sorted(want.items()):
        p = sub / name
        if not p.exists():
            out.append(f"FROZEN {sub.parent.name}/{sub.name}: {name} is missing")
        elif hashlib.sha256(p.read_bytes()).hexdigest() != h:
            out.append(f"FROZEN {sub.parent.name}/{sub.name}: {name} differs from the submitted file")
    for p in sorted(sub.iterdir()):
        if p.is_file() and p.name not in want and p != recs[0] and not p.name.startswith("~$"):
            out.append(f"FROZEN {sub.parent.name}/{sub.name}: {p.name} was added after submission")
    return out, len(want)


def main(root: Path = ROOT) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if len(sys.argv) > 1 and root == ROOT:
        print(f"FAIL: unknown arguments {sys.argv[1:]}")
        return 1
    found, n_sets, n_files = [], 0, 0
    for rel in FOLDERS:
        sub = root / rel / "submission"
        if not sub.is_dir() or not list(sub.glob("SUBMITTED_*")):
            continue
        p, n = problems(sub)
        found += p
        n_sets += 1
        n_files += n
    if not n_sets:
        print("SKIPPED: no submitted manuscript set present (private, not in this repository)")
        return 0
    for ln in found:
        print(ln)
    print(f"frozen sets: {n_sets} submitted set(s), {n_files} files compared with their SHA-256 records; "
          f"{len(found)} problem(s)")
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main())
