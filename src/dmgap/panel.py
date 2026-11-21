"""The extracted panel, its NA rules and its denominator bases (plan §3.3-§3.5, §12.1).

A panel is a dict (unit, year) -> Cell with the counts N (the C1 denominator), K (known
status), D (diabetic) and I (initiated; linked to an NCD clinic in 2018).

Bases (§12.1, §12.2):
- "main": data/extracted/dm_panel.csv (2021 and 2023 N = A1.4 net notified, 2022 N =
  A1.6 male + female + transgender, flag denominator_a1_6_sex_sum);
- "a1_2_registered": the registered A1.2 N for 2021-2023
  (dm_panel_notified_registered.csv, flag plan_12.1_registered_basis);
- "2022_from_percent": the 2022 N back-calculated from the printed percentage
  (dm_panel_notified_2022_from_percent.csv, flag plan_12.1_sensitivity).
"""
from __future__ import annotations

import csv
from dataclasses import dataclass, replace
from pathlib import Path

from src.extract import crosswalk

ROOT = Path(__file__).resolve().parents[2]
EXTRACTED = ROOT / "data" / "extracted"
PANEL_CSV = EXTRACTED / "dm_panel.csv"
REGISTERED_CSV = EXTRACTED / "dm_panel_notified_registered.csv"
FROM_PCT_CSV = EXTRACTED / "dm_panel_notified_2022_from_percent.csv"

YEARS = (2018, 2019, 2021, 2022, 2023)
C3_MAIN_YEARS = (2019, 2021, 2022, 2023)
UNITS: tuple[str, ...] = tuple(sorted(crosswalk.UNITS))
MEASURES = {"notified": "N", "known_status": "K", "diabetic": "D", "initiated": "I"}

BASIS_MAIN = "main"
BASIS_REGISTERED = "a1_2_registered"
BASIS_FROM_PCT = "2022_from_percent"
BASIS_YEARS = {BASIS_REGISTERED: (2021, 2022, 2023), BASIS_FROM_PCT: (2022,)}
BASIS_FLAG = {BASIS_REGISTERED: "plan_12.1_registered_basis",
              BASIS_FROM_PCT: "plan_12.1_sensitivity"}
MAIN_2022_FLAG = "denominator_a1_6_sex_sum"


@dataclass(frozen=True)
class Cell:
    unit: str
    year: int
    N: int | None
    K: int | None
    D: int | None
    I: int | None

    @property
    def U(self) -> int:
        return self.N - self.K

    def c1_reason(self) -> str | None:
        """None when C1 = K/N is valid, else the NA reason (§3.5)."""
        if self.N is None:
            return "notified missing"
        if self.K is None:
            return "known status missing"
        if self.N == 0:
            return "N = 0"
        if self.K > self.N:
            return "K > N"
        return None

    def y_reason(self) -> str | None:
        if self.K is None:
            return "known status missing"
        if self.D is None:
            return "diabetic missing"
        if self.K == 0:
            return "K = 0"
        if self.D > self.K:
            return "D > K"
        return None

    def c3_reason(self) -> str | None:
        if self.D is None:
            return "diabetic missing"
        if self.I is None:
            return "initiated missing"
        if self.D == 0:
            return "D = 0"
        if self.I > self.D:
            return "I > D"
        return None

    @property
    def c1_ok(self) -> bool:
        return self.c1_reason() is None

    @property
    def y_ok(self) -> bool:
        return self.y_reason() is None

    @property
    def c3_ok(self) -> bool:
        return self.c3_reason() is None


def _read(path: Path) -> list[dict]:
    with open(path, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def _int(v: str) -> int | None:
    v = v.strip()
    if v in ("", "NA"):
        return None
    return int(v)


def load_rows(path: Path = PANEL_CSV) -> list[dict]:
    return _read(path)


def build(rows: list[dict]) -> dict[tuple[str, int], Cell]:
    """The panel from dm_panel.csv rows. Every unit-year of the 33 units and five years
    must be present; a unit not in the crosswalk stops the run (Review Focus 2)."""
    vals: dict[tuple[str, int], dict[str, int | None]] = {}
    for r in rows:
        u, t = r["unit"], int(r["year"])
        if u not in UNITS:
            raise ValueError(f"unit not in the crosswalk: {u!r}")
        if r["measure"] not in MEASURES:
            raise ValueError(f"unknown measure {r['measure']!r}")
        vals.setdefault((u, t), {})[MEASURES[r["measure"]]] = _int(r["value"])
    panel = {}
    for u in UNITS:
        for t in YEARS:
            v = vals.get((u, t))
            if v is None:
                raise ValueError(f"no panel rows for {u} {t}")
            panel[(u, t)] = Cell(u, t, v.get("N"), v.get("K"), v.get("D"), v.get("I"))
    for u in UNITS:
        flag = next(r["flag"] for r in rows
                    if r["unit"] == u and r["year"] == "2022" and r["measure"] == "notified")
        if MAIN_2022_FLAG not in flag.split(";"):
            raise ValueError(f"main 2022 N of {u} lacks the flag {MAIN_2022_FLAG}")
    return panel


def load(path: Path = PANEL_CSV) -> dict[tuple[str, int], Cell]:
    return build(load_rows(path))


def basis_rows(basis: str) -> list[dict]:
    path = {BASIS_REGISTERED: REGISTERED_CSV, BASIS_FROM_PCT: FROM_PCT_CSV}[basis]
    rows = _read(path)
    for r in rows:
        if BASIS_FLAG[basis] not in r["flag"].split(";"):
            raise ValueError(f"{path.name}: row {r['unit']} {r['year']} lacks the flag "
                             f"{BASIS_FLAG[basis]}")
        if r["measure"] != "notified" or int(r["year"]) not in BASIS_YEARS[basis]:
            raise ValueError(f"{path.name}: unexpected row {r['unit']} {r['year']} "
                             f"{r['measure']}")
    return rows


def with_basis(panel: dict, basis: str, rows: list[dict] | None = None) -> dict:
    """The panel with N replaced for the basis's years (§12.1)."""
    if basis == BASIS_MAIN:
        return dict(panel)
    rows = basis_rows(basis) if rows is None else rows
    out = dict(panel)
    seen = set()
    for r in rows:
        key = (r["unit"], int(r["year"]))
        if key not in out:
            raise ValueError(f"unit-year not in the panel: {key}")
        out[key] = replace(out[key], N=_int(r["value"]))
        seen.add(key)
    expected = {(u, t) for u in UNITS for t in BASIS_YEARS[basis]}
    if seen != expected:
        raise ValueError(f"basis {basis}: rows do not cover the 33 units x "
                         f"{BASIS_YEARS[basis]}")
    return out


def year_cells(panel: dict, year: int, omit: str | None = None) -> list[Cell]:
    """The year's cells, alphabetical by unit (the §5.3 order), optionally without one."""
    return [panel[(u, year)] for u in UNITS if u != omit]
