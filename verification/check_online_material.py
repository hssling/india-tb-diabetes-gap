"""Check the online material (docs/online_material/) against the committed code and outputs.

Run as: python -I verification/check_online_material.py

1. Every text file that exhibits/make_online_material.py writes (README.md, tables.md, one CSV per
   table and the data of each figure) is regenerated from outputs/ and must be byte-identical.
2. Each figure exists as PDF and PNG; no file is present that the builder does not write.
3. The wording is person-first and plain: no "TB patients", "suspect", "defaulter" or
   "pre-registered" (verification/ijtld.py), and no American spelling.
4. Only aggregates: no column of any CSV is an individual-level identifier (the study holds none;
   every row is a State or Union Territory, a year, a specification or a national total).

Exit 1 on any problem.
"""
from __future__ import annotations

import csv
import io
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from exhibits import make_online_material as mo  # noqa: E402
from verification import ijtld  # noqa: E402
from verification.check_manuscript_numbers import AMERICAN  # noqa: E402

PERSONAL = re.compile(r"\b(?:name|patient_id|person|nikshay_id|phone|address|age_years|dob)\b", re.I)


def problems(root: Path = ROOT) -> list[str]:
    out = []
    d = root / mo.OUT_REL
    if not d.is_dir():
        return [f"MISSING: {mo.OUT_REL}/ (python -I exhibits/make_online_material.py)"]
    want = mo.text_files(root)
    for name, data in want.items():
        p = d / name
        if not p.exists():
            out.append(f"MISSING: {mo.OUT_REL}/{name}")
        elif p.read_bytes() != data:
            out.append(f"DIFFERS: {mo.OUT_REL}/{name} is not what the committed code writes from outputs/ (rebuild)")
    figs = {f"figure{k}.{ext}" for k in mo.FIGURES for ext in ("pdf", "png")}
    for f in sorted(figs):
        if not (d / f).exists():
            out.append(f"MISSING: {mo.OUT_REL}/{f}")
    for p in sorted(d.iterdir()):
        if p.is_file() and p.name not in set(want) | figs:
            out.append(f"EXTRA: {mo.OUT_REL}/{p.name} is not written by exhibits/make_online_material.py")
    for name, data in want.items():
        text = data.decode("utf-8")
        for h in ijtld.wording_hits(text):
            out.append(f"WORDING in {mo.OUT_REL}/{name}: {h}")
        for pat in AMERICAN:
            for m in re.finditer(pat, text, re.I):
                out.append(f"SPELLING in {mo.OUT_REL}/{name}: American form {m.group()!r}")
        if name.endswith(".csv"):
            header = next(csv.reader(io.StringIO(text)))
            bad = [c for c in header if PERSONAL.search(c)]
            if bad:
                out.append(f"PRIVACY: {mo.OUT_REL}/{name} has columns {bad}")
    return out


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if len(sys.argv) > 1:
        print(f"FAIL: unknown arguments {sys.argv[1:]}")
        return 1
    found = problems(ROOT)
    for ln in found:
        print(ln)
    n = len(mo.text_files(ROOT))
    print(f"online material: {n} text files regenerated from outputs/ and compared byte for byte, "
          f"{len(mo.FIGURES)} figures (PDF and PNG); person-first wording, British spelling, aggregates only; "
          f"{len(found)} problem(s)")
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main())
