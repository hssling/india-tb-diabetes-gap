"""Check the extracted tables against their printed India totals (analysis plan
sections 3.5, 10.4 and 12.1).

Run: python -I verification/check_extraction_totals.py   (from the repository root)

Reads only the committed extracts (no PDF is needed):

1. Printed totals. For every table and extracted column of
   data/extracted/dm_cells.csv, the sum of the 36 printed State/UT rows is
   compared with the printed India row. A difference must be one recorded,
   with its size, in src/extract/itr_dm.py RECORDED_GAPS; any other difference
   fails. The same is done for data/extracted/tb_sex_2022.csv.
2. Coarsening. For every data year and measure, the 33 unit values of
   data/extracted/dm_panel.csv (and of the plan section 12.1 sensitivity file
   dm_panel_notified_registered.csv) sum to the printed rows of dm_cells.csv
   they are built from (merging adds the member rows and loses nothing), and
   the panel has 33 units x 5 years x 4 measures.

The implied-denominator check (plan sections 3.4 and 12.1) is
verification/check_implied_denominator.py. The printed-total results are
written to data/extracted/total_checks.csv. Exit status 1 if a check fails.
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


def _printed_sum(cells: list[dict], src: itr_dm.Source) -> int:
    key, fields, _ = src
    return sum(int(r["value"]) for r in cells if r["table_key"] == key
               and r["field"] in fields and r["printed_unit"] != NATIONAL and r["value"] != "")


def _panel_sum(panel: list[dict], year: int, measure: str) -> int:
    return sum(int(r["value"]) for r in panel if int(r["year"]) == year
               and r["measure"] == measure and r["value"] != "")


def coarsening(cells: list[dict], panel: list[dict],
               registered: list[dict] | None = None) -> list[str]:
    bad = []
    if len(panel) != 33 * 5 * 4:
        bad.append(f"dm_panel.csv has {len(panel)} rows, expected 660")
    units = {r["unit"] for r in panel}
    if len(units) != 33:
        bad.append(f"dm_panel.csv has {len(units)} units, expected 33")
    for year, ms in itr_dm.SOURCES.items():
        for measure, src in ms.items():
            printed, merged = _printed_sum(cells, src), _panel_sum(panel, year, measure)
            if printed != merged:
                bad.append(f"{year} {measure}: panel sum {merged} != printed rows {printed}")
    if registered is not None:
        if len(registered) != 33 * 3:
            bad.append(f"dm_panel_notified_registered.csv has {len(registered)} rows")
        for year, src in itr_dm.REGISTERED_NOTIFIED.items():
            printed = _printed_sum(cells, src)
            merged = _panel_sum(registered, year, "notified")
            if printed != merged:
                bad.append(f"registered {year}: sum {merged} != printed rows {printed}")
    return bad


def _write(name: str, rows: list[dict]) -> None:
    with open(EXTRACTED / name, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]), lineterminator="\n")
        w.writeheader()
        w.writerows(rows)


def main() -> int:
    cells = _read("dm_cells.csv")
    sex = _read("tb_sex_2022.csv")
    checks = printed_totals(cells)
    bad = itr_dm.unrecorded_gaps(checks)
    for c in checks + sex_totals(sex):
        mark = "ok " if c["difference"] == 0 else "GAP"
        print(f"{mark} {c['table_key']:>14} {c['field']:<16} State sum {c['state_sum']}, "
              f"printed {c['printed']}, difference {c['difference']}, "
              f"blank {c['blank_cells']}")
    bad += [f"tb_sex_2022 {c['field']}: difference {c['difference']}"
            for c in sex_totals(sex) if c["difference"] != 0]
    bad += coarsening(cells, _read("dm_panel.csv"), _read("dm_panel_notified_registered.csv"))
    _write("total_checks.csv", checks + sex_totals(sex))
    for b in bad:
        print(f"FAIL: {b}")
    if bad:
        return 1
    print("OK: printed totals match or are recorded; coarsening preserves the totals")
    return 0


if __name__ == "__main__":
    sys.exit(main())
