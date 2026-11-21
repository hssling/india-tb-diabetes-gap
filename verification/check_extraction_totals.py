"""Check the extracted tables against their printed India totals (analysis plan
sections 3.4, 3.5 and 10.4).

Run: python -I verification/check_extraction_totals.py   (from the repository root)

Reads only the committed extracts (no PDF is needed):

1. Printed totals. For every table and extracted column of
   data/extracted/dm_cells.csv, the sum of the 36 printed State/UT rows is
   compared with the printed India row. A difference must be one recorded,
   with its size, in src/extract/itr_dm.py RECORDED_GAPS; any other difference
   fails. The same is done for data/extracted/tb_sex_2022.csv.
2. Coarsening. For every data year and measure, the 33 unit values of
   data/extracted/dm_panel.csv sum to the 36 printed rows of dm_cells.csv
   (merging adds the member rows and loses nothing), and the panel has
   33 units x 5 years x 4 measures.
3. Implied denominators (section 3.4, an extraction check, not an estimate).
   For every printed Total known-status cell that prints a percentage p, the
   range of denominators consistent with it, K / ((p +- half a unit of p's
   last digit) / 100), is compared with the registered notified count N of the
   same printed row (and, for 2022, with the ITR 2023 A1.6 male + female +
   transgender sum). Each comparison is written to
   data/extracted/implied_denominator_check.csv; the counts inside and outside
   the range are printed. It changes nothing in the analysis.

The printed-total results are written to data/extracted/total_checks.csv.
Exit status 1 if a check fails.
"""
from __future__ import annotations

import csv
import sys
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.extract import itr_dm  # noqa: E402  (standard library only at import)

EXTRACTED = ROOT / "data" / "extracted"
NATIONAL = "India"
N_ROWS = 36

# Data year -> (table key of the known-status column, table key of N).
KNOWN = {2018: ("ITR2019_A1.2", "ITR2019_A1.2"), 2019: ("ITR2020_A2.5", "ITR2020_A2.5"),
         2021: ("TBAR2022_A2.5", "TBAR2022_A1.2"), 2022: ("ITR2023_A2.10", "ITR2023_A1.2"),
         2023: ("ITR2024_A2.10", "ITR2024_A1.2")}


def _read(name: str) -> list[dict]:
    with open(EXTRACTED / name, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def _num(s: str) -> int | Decimal | None:
    if s == "":
        return None
    return Decimal(s) if "." in s else int(s)


def printed_totals(cells: list[dict]) -> list[dict]:
    groups: dict[tuple[str, str], dict[str, int | Decimal | None]] = {}
    for r in cells:
        groups.setdefault((r["table_key"], r["field"]), {})[r["printed_unit"]] = _num(r["value"])
    out = []
    for (key, field), vals in groups.items():
        states = [v for u, v in vals.items() if u != NATIONAL]
        if len(vals) != N_ROWS + 1 or NATIONAL not in vals:
            raise SystemExit(f"FAIL: {key} {field}: {len(vals)} printed rows")
        s = sum((v for v in states if v is not None), start=type(vals[NATIONAL])(0))
        out.append({"table_key": key, "field": field, "state_sum": s,
                    "printed": vals[NATIONAL], "difference": s - vals[NATIONAL],
                    "blank_cells": sum(v is None for v in states)})
    return out


def sex_totals(rows: list[dict]) -> list[dict]:
    out = []
    for s in ("male", "female", "transgender"):
        states = [int(r[s]) for r in rows if r["printed_unit"] != NATIONAL and r[s] != ""]
        nat = int(next(r[s] for r in rows if r["printed_unit"] == NATIONAL))
        out.append({"table_key": "tb_sex_2022", "field": s, "state_sum": sum(states),
                    "printed": nat, "difference": sum(states) - nat,
                    "blank_cells": len(rows) - 1 - len(states)})
    return out


def coarsening(cells: list[dict], panel: list[dict]) -> list[str]:
    bad = []
    if len(panel) != 33 * 5 * 4:
        bad.append(f"dm_panel.csv has {len(panel)} rows, expected 660")
    units = {r["unit"] for r in panel}
    if len(units) != 33:
        bad.append(f"dm_panel.csv has {len(units)} units, expected 33")
    for year, ms in itr_dm.SOURCES.items():
        for measure, (key, _) in ms.items():
            printed = sum(int(r["value"]) for r in cells if r["table_key"] == key
                          and r["field"] == measure and r["printed_unit"] != NATIONAL
                          and r["value"] != "")
            merged = sum(int(r["value"]) for r in panel if int(r["year"]) == year
                         and r["measure"] == measure and r["value"] != "")
            if printed != merged:
                bad.append(f"{year} {measure}: panel sum {merged} != printed rows {printed}")
    return bad


def _pct(text: str) -> Decimal | None:
    t = text.strip()
    i = t.rfind("(")
    if i < 0 or not t.endswith(")"):
        return None
    inner = t[i + 1:-1].replace("%", "").strip()
    try:
        return Decimal(inner)
    except ArithmeticError:
        return None


def implied_denominators(cells: list[dict], sex: list[dict]) -> list[dict]:
    val = {(r["table_key"], r["printed_unit"], r["field"]): r for r in cells}
    a16 = {r["printed_unit"]: int(r["male"]) + int(r["female"]) + int(r["transgender"])
           for r in sex if r["male"] != "" and r["female"] != "" and r["transgender"] != ""}
    out = []
    for year, (kkey, nkey) in KNOWN.items():
        units = sorted({r["printed_unit"] for r in cells if r["table_key"] == kkey})
        for u in units:
            kr = val[(kkey, u, "known_status")]
            p = _pct(kr["cell_printed"])
            if p is None or kr["value"] in ("", "0"):
                continue
            k = int(kr["value"])
            half = Decimal(1).scaleb(p.as_tuple().exponent) / 2
            lo = Decimal(k) * 100 / (p + half)
            hi = Decimal(k) * 100 / (p - half) if p - half > 0 else None
            bases = [("registered_N", int(val[(nkey, u, "notified")]["value"]))]
            if year == 2022 and u in a16:
                bases.append(("a1_6_sex_sum", a16[u]))
            for basis, n in bases:
                inside = lo <= n and (hi is None or n <= hi)
                out.append({"year": year, "printed_unit": u, "known_status": k,
                            "pct_printed": str(p), "implied_lo": lo.quantize(Decimal("0.1")),
                            "implied_hi": "" if hi is None else hi.quantize(Decimal("0.1")),
                            "basis": basis, "n": n, "inside": "yes" if inside else "no"})
    return out


def _write(name: str, rows: list[dict]) -> None:
    with open(EXTRACTED / name, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]), lineterminator="\n")
        w.writeheader()
        w.writerows(rows)


def main() -> int:
    cells = _read("dm_cells.csv")
    sex = _read("tb_sex_2022.csv")
    panel = _read("dm_panel.csv")
    checks = printed_totals(cells)
    bad = itr_dm.unrecorded_gaps(checks)
    for c in checks + sex_totals(sex):
        mark = "ok " if c["difference"] == 0 else "GAP"
        print(f"{mark} {c['table_key']:>14} {c['field']:<16} State sum {c['state_sum']}, "
              f"printed {c['printed']}, difference {c['difference']}, "
              f"blank {c['blank_cells']}")
    bad += [f"tb_sex_2022 {c['field']}: difference {c['difference']}"
            for c in sex_totals(sex) if c["difference"] != 0]
    bad += coarsening(cells, panel)
    _write("total_checks.csv", checks + sex_totals(sex))
    imp = implied_denominators(cells, sex)
    _write("implied_denominator_check.csv", imp)
    print("implied-denominator check (section 3.4): N inside the range implied by the "
          "printed known-status percentage")
    for year in KNOWN:
        for basis in ("registered_N", "a1_6_sex_sum"):
            rs = [r for r in imp if r["year"] == year and r["basis"] == basis]
            if rs:
                n_in = sum(r["inside"] == "yes" for r in rs)
                print(f"  {year} {basis}: {n_in} of {len(rs)} printed rows inside")
    for b in bad:
        print(f"FAIL: {b}")
    if bad:
        return 1
    print("OK: printed totals match or are recorded; coarsening preserves the totals")
    return 0


if __name__ == "__main__":
    sys.exit(main())
