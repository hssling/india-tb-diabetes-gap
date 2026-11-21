"""The implied-denominator check (analysis plan sections 3.4 and 12.1).

Run: python -I verification/check_implied_denominator.py   (from the repository root)

For every printed Total known-status cell that prints a percentage p (the 36
State/UT rows and the India row of each year's TB-diabetes table), the
denominators consistent with it are the whole N with

    K x 100 / (p + h) <= N <= K x 100 / (p - h),

h being half a unit of p's last printed digit. Each candidate printed count of
the same row is tested against that interval. This compares printed counts with
printed percentages; it is structural, not an estimate.

Candidates (all in data/extracted/dm_cells.csv; no PDF is needed):
- 2018: ITR 2019 A1.2 notified (the table's own; registered and main);
- 2019: ITR 2020 A2.5 notified (the table's own; registered and main);
- 2021: TBAR 2022 A1.2 notified (registered) and A1.4 net notified (main, §12.1);
- 2022: ITR 2023 A1.2 notified (registered) and A1.6 male + female +
  transgender (main, §12.1);
- 2023: ITR 2024 A1.2 notified (registered) and A1.4 net notified (main, §12.1).

The match counts must equal those in plan section 12.1 (EXPECTED); otherwise
the check fails. Each comparison is written to
data/extracted/implied_denominator_check.csv.
"""
from __future__ import annotations

import csv
import math
import sys
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXTRACTED = ROOT / "data" / "extracted"
OUT = EXTRACTED / "implied_denominator_check.csv"
SEX = ("male", "female", "transgender")

# year -> (table key of the known-status column, {basis: (table key, fields)})
CANDIDATES: dict[int, tuple[str, dict[str, tuple[str, tuple[str, ...]]]]] = {
    2018: ("ITR2019_A1.2", {"own_table": ("ITR2019_A1.2", ("notified",))}),
    2019: ("ITR2020_A2.5", {"own_table": ("ITR2020_A2.5", ("notified",))}),
    2021: ("TBAR2022_A2.5", {"a1_2_registered": ("TBAR2022_A1.2", ("notified",)),
                             "a1_4_net_main": ("TBAR2022_A1.4", ("notified",))}),
    2022: ("ITR2023_A2.10", {"a1_2_registered": ("ITR2023_A1.2", ("notified",)),
                             "a1_6_sex_sum_main": ("ITR2023_A1.6", SEX)}),
    2023: ("ITR2024_A2.10", {"a1_2_registered": ("ITR2024_A1.2", ("notified",)),
                             "a1_4_net_main": ("ITR2024_A1.4", ("notified",))}),
}
# Matches of the 37 printed rows, as recorded in plan section 12.1 (and 35/37,
# 37/37 for 2018 and 2019).
EXPECTED = {
    (2018, "own_table"): 35, (2019, "own_table"): 37,
    (2021, "a1_2_registered"): 2, (2021, "a1_4_net_main"): 37,
    (2022, "a1_2_registered"): 2, (2022, "a1_6_sex_sum_main"): 28,
    (2023, "a1_2_registered"): 2, (2023, "a1_4_net_main"): 37,
}


def read_cells(path: Path = EXTRACTED / "dm_cells.csv") -> list[dict]:
    with open(path, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def printed_pct(cell_printed: str) -> Decimal | None:
    t = cell_printed.strip()
    i = t.rfind("(")
    if i < 0 or not t.endswith(")"):
        return None
    try:
        return Decimal(t[i + 1:-1].replace("%", "").strip())
    except ArithmeticError:
        return None


def interval(k: int, p: Decimal) -> tuple[int, int | None]:
    """Whole N consistent with K printed as p% of N (hi None: unbounded)."""
    h = Decimal(1).scaleb(p.as_tuple().exponent) / 2
    lo = math.ceil(Decimal(k) * 100 / (p + h))
    hi = math.floor(Decimal(k) * 100 / (p - h)) if p - h > 0 else None
    return lo, hi


def comparisons(cells: list[dict]) -> list[dict]:
    val = {(r["table_key"], r["printed_unit"], r["field"]): r for r in cells}
    out = []
    for year, (kkey, bases) in CANDIDATES.items():
        units = [r["printed_unit"] for r in cells
                 if r["table_key"] == kkey and r["field"] == "known_status"]
        for u in units:
            kr = val[(kkey, u, "known_status")]
            p = printed_pct(kr["cell_printed"])
            if p is None or kr["value"] in ("", "0"):
                continue
            k = int(kr["value"])
            lo, hi = interval(k, p)
            for basis, (nkey, fields) in bases.items():
                vs = [val[(nkey, u, f)]["value"] for f in fields]
                if any(v == "" for v in vs):
                    continue
                n = sum(int(v) for v in vs)
                inside = lo <= n and (hi is None or n <= hi)
                out.append({"year": year, "printed_unit": u, "known_status": k,
                            "pct_printed": str(p), "n_lo": lo, "n_hi": "" if hi is None else hi,
                            "basis": basis, "n": n, "inside": "yes" if inside else "no"})
    return out


def counts(rows: list[dict]) -> dict[tuple[int, str], tuple[int, int]]:
    out: dict[tuple[int, str], tuple[int, int]] = {}
    for r in rows:
        k = (r["year"], r["basis"])
        a, b = out.get(k, (0, 0))
        out[k] = (a + (r["inside"] == "yes"), b + 1)
    return out


def main() -> int:
    rows = comparisons(read_cells())
    with open(OUT, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]), lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
    bad = []
    for k, (n_in, n) in sorted(counts(rows).items()):
        print(f"{k[0]} {k[1]:<18} {n_in} of {n} printed rows inside the interval")
        if n != 37 or EXPECTED.get(k) != n_in:
            bad.append(f"{k}: {n_in} of {n}, plan section 12.1 records {EXPECTED.get(k)} of 37")
    for b in bad:
        print(f"FAIL: {b}")
    if bad:
        return 1
    print("OK: the match counts are those recorded in plan section 12.1")
    return 0


if __name__ == "__main__":
    sys.exit(main())
