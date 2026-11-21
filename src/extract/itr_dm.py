"""Extract the TB-diabetes counts, the 2022 notified counts by sex and the 2022
population (analysis plan sections 3.3-3.5 and 4.1).

Run: python -I src/extract/itr_dm.py   (from the repository root)

Reads the tables fixed in plan section 3.3 from the India TB Reports in
data_raw/ (ITR 2019, ITR 2020, TBAR 2022, ITR 2023, ITR 2024) and writes:

- data/extracted/dm_cells.csv: every extracted printed cell, one row per
  printed row (36 State/UT rows and the India row) and column, before
  coarsening, with its page and the cell as printed;
- data/extracted/dm_panel.csv: ``unit, year, measure, value, source_file,
  pdf_page, table_id, flag``, one row per coarsened unit (33), data year (2018,
  2019, 2021, 2022, 2023) and measure (notified, known_status, diabetic,
  initiated). ``value`` is the count summed over the unit's printed rows;
  nothing else is computed (no ratio, rate or estimate);
- data/extracted/tb_sex_2022.csv: the ITR 2023 Annexure 1.6 "TB Cases
  Notified" counts (male, female, transgender), one row per printed row;
- plan section 12.1 (21 Nov 2026): the main notified N of 2021-2023 is TBAR
  2022 A1.4 net notified, ITR 2023 A1.6 male + female + transgender and ITR
  2024 A1.4 net notified (current PHI) Total, the bases of the diabetes tables'
  own percentages. Sensitivities: data/extracted/dm_panel_notified_registered.csv
  (the registered A1.2 basis, flag plan_12.1_registered_basis) and
  data/extracted/dm_panel_notified_2022_from_percent.csv (2022 N back-calculated
  from the printed known-status percentage, with value_lo/value_hi, flag
  derived_from_percent).

The ITR 2023 Annexure 1.1 population (lakhs, as printed) is kept in
dm_cells.csv; src/extract/nfhs.py reads it from there.

Rules (plan sections 3.3-3.5, 4.1):
- The Total column is used, never Public or Private alone; of a ``count (%)``
  cell the count is used, not the percentage.
- Where a needed cell prints only a percentage, the count is derived as
  round-half-up(base x % / 100) and flagged ``derived_from_percent`` with the
  range of counts that print the same percentage (``derive_from_percent``).
  The bases are those printed in the ITR 2023 headers: known status on
  notified, diabetic on known status, initiated on diabetic. No cell of the
  tables used needs this.
- Every table is compared with its printed India row, column by column (the
  sum of the 36 printed State/UT rows, blank cells left out). A difference is
  recorded with its size in RECORDED_GAPS and not corrected.
- Printed rows are mapped by src/extract/crosswalk.py and merged rows are
  summed into their unit. A member row whose cell is absent or blank adds
  nothing; the unit carries ``member_missing:<row>``. A unit whose members are
  all missing has an empty value and ``NA:all_members_missing``.
- Impossible or empty cells (plan section 3.5, Review Focus 1), per unit-year:
  C1 is NA when known_status > notified or notified = 0; C2 and y are NA when
  diabetic > known_status or known_status = 0; C3 is NA when initiated >
  diabetic or diabetic = 0. The NA is a flag on the numerator's row
  (``NA:C1:<reason>`` on known_status, ``NA:y:<reason>`` on diabetic,
  ``NA:C3:<reason>`` on initiated). The printed counts are kept, because an NA
  step removes the unit-year only from the quantities that use it (a unit
  with C1 NA still enters E2 if its y is valid).

Rotated ITR 2019 pages are read by character position (grid.py), as the plan
requires. Each page is checked for the table's title (first page, where the
title is in the text layer) and a header text.
"""
from __future__ import annotations

import math
import sys
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if __package__ in (None, ""):
    sys.path.insert(0, str(ROOT))

from src.extract import annex, cells, crosswalk  # noqa: E402

EXTRACTED = ROOT / "data" / "extracted"
CELLS_CSV = EXTRACTED / "dm_cells.csv"
PANEL_CSV = EXTRACTED / "dm_panel.csv"
SEX_CSV = EXTRACTED / "tb_sex_2022.csv"
REGISTERED_CSV = EXTRACTED / "dm_panel_notified_registered.csv"
FROM_PCT_CSV = EXTRACTED / "dm_panel_notified_2022_from_percent.csv"

CELL_COLS = ["edition", "year", "table_key", "table_id", "pdf_page", "printed_name",
             "printed_unit", "unit", "field", "column_header", "cell_printed", "value", "flag"]
PANEL_COLS = ["unit", "year", "measure", "value", "source_file", "pdf_page", "table_id", "flag"]
SEX_COLS = ["printed_name", "printed_unit", "unit", "male", "female", "transgender",
            "source_file", "pdf_page", "table_id", "flag"]

FILES = {
    "ITR 2019": "data_raw/india_tb_report/India-TB-Report-2019.pdf",
    "ITR 2020": "data_raw/india_tb_report/ITR2020.pdf",
    "TBAR 2022": "data_raw/india_tb_report/TBAnnaulReport2022.pdf",
    "ITR 2023": "data_raw/india_tb_report/ITR2023.pdf",
    "ITR 2024": "data_raw/india_tb_report/ITR2024.pdf",
}
YEAR_OF = {"ITR 2019": 2018, "ITR 2020": 2019, "TBAR 2022": 2021, "ITR 2023": 2022,
           "ITR 2024": 2023}

MEASURES = ("notified", "known_status", "diabetic", "initiated")
# The percentage base of each measure, for a percent-only cell (ITR 2023 headers:
# "% of notified", "% of those with known DM status", "% of TB-DM").
PCT_BASE = {"known_status": "notified", "diabetic": "known_status", "initiated": "diabetic"}


@dataclass(frozen=True)
class Field:
    name: str
    index: int  # 0-based value cell after the name
    header: str  # verbatim column header (plan section 3.3)
    decimal: bool = False


@dataclass(frozen=True)
class TableSpec:
    key: str
    edition: str
    table_id: str
    pages: tuple[int, ...]
    ncells: int  # value cells per row
    fields: tuple[Field, ...]
    title: str | None  # text on the first page (None: the title is not in the text layer)
    header: str  # text on every page
    region: tuple[float, float] | None = None

    @property
    def year(self) -> int:
        return YEAR_OF[self.edition]

    @property
    def source_file(self) -> str:
        return FILES[self.edition]

    def field(self, name: str) -> Field:
        return next(f for f in self.fields if f.name == name)


F = Field
SPECS: dict[str, TableSpec] = {s.key: s for s in (
    # ---- 2018: ITR 2019 A1.2 "TB Comorbidities" (rotated pages; totals only)
    TableSpec("ITR2019_A1.2", "ITR 2019", "Annexure 1.2", (169, 170), 11, (
        F("notified", 0, "Total TB patients Notified (notified cases based on current PHI)"),
        F("known_status", 5, "Total TB patients with known blood sugar status (%): count part"),
        F("diabetic", 6, "Total TB- DM Co- morbid patients (%): count part"),
        F("initiated", 7, "TB-DM Co-morbid patients Linked to NCD Clinic (%): count part"),
    ), "1.2 TB Comorbidities", "blood sugar"),
    # ---- 2019: ITR 2020 A2.5 "TB-Diabetes"
    TableSpec("ITR2020_A2.5", "ITR 2020", "Annexure 2.5", (216, 217), 12, (
        F("notified", 2, "TB Patients notified: Total"),
        F("known_status", 5, "TB patients with known DM status (%): Total, count part"),
        F("diabetic", 8, "TB Patients diagnosed with Diabetes among tested (%): Total, "
                         "count part"),
        F("initiated", 11, "TB- DM patients initiated on Anti-diabetic treatment (%): Total, "
                           "count part"),
    ), "2.5 TB-Diabetes", "Anti-diabetic treatment (%)"),
    # ---- 2021: TBAR 2022 A2.5 "TB-Diabetes" (one table across the spread) and A1.2
    TableSpec("TBAR2022_A2.5", "TBAR 2022", "Annexure 2.5", (96,), 9, (
        F("known_status", 2, "TB patients with known DM status (%): Total, count part"),
        F("diabetic", 5, "TB - DM Patients diagnosed among tested (%): Total, count part"),
        F("initiated", 8, "TB- DM patients initiated on Anti-diabetic treatment (%): Total, "
                          "count part"),
    ), "2.5 TB-Diabetes", "TB patients with known DM status (%)"),
    TableSpec("TBAR2022_A1.2", "TBAR 2022", "Annexure 1.2", (89,), 9, (
        F("notified", 5, "TB patients notified (Achievement against target %): Total, "
                         "count part"),
    ), "1.2 TB Case Notification", "TB patients notified (Achievement against target %)"),
    # Plan section 12.1: the main 2021 N. Left half of the spread.
    TableSpec("TBAR2022_A1.4", "TBAR 2022", "Annexure 1.4", (91,), 5, (
        F("notified", 3, "Net TB Patients Notified"),
    ), "1.4 Patient Transfer Status & Treatment Initiation Status", "Net TB Patients Notified",
        region=(0.0, 0.5)),
    # ---- 2022: ITR 2023 A2.10 "TB - DIABETES", A1.2, A1.6 and A1.1
    TableSpec("ITR2023_A2.10", "ITR 2023", "Annexure 2.10", (239, 240), 9, (
        F("known_status", 2, "TB patients with known DM status, n (% of notified): Total, "
                             "count part"),
        F("diabetic", 5, "TB - DM Patients diagnosed among tested, n (% of those with known "
                         "DM status): Total, count part"),
        F("initiated", 8, "TB- DM patients initiated on Anti- diabetic treatment, n (% of "
                          "TB-DM): Total, count part"),
    ), None, "TB patients with known DM status, n"),
    TableSpec("ITR2023_A1.2", "ITR 2023", "Annexure 1.2", (213, 214), 9, (
        F("notified", 5, "TB patients notified, n (% achievement against target): Total, "
                         "count part"),
    ), None, "Target TB patients expected"),
    TableSpec("ITR2023_A1.6", "ITR 2023", "Annexure 1.6", (221, 222), 9, (
        F("male", 0, "TB Cases Notified: Male"),
        F("female", 1, "TB Cases Notified: Female"),
        F("transgender", 2, "TB Cases Notified: Trans Gender"),
    ), "1.6 GENDER DISAGGREGATED DATA ON TOTAL TB NOTIFICATION", "TB Cases Notified"),
    # The plan (section 3.3) names PDF p. 211, which prints the rows down to
    # Manipur and every row merged by section 4.3; the table continues on p. 212
    # (Meghalaya to West Bengal and the India row), read for the printed total.
    TableSpec("ITR2023_A1.1", "ITR 2023", "Annexure 1.1", (211, 212), 9, (
        F("population_lakhs", 0, "Popula- tion - 2022 (in lakhs)", decimal=True),
    ), "1.1 PRESUMPTIVE TB CASES EXAMINATION", "Popula"),
    # ---- 2023: ITR 2024 A2.10 "TB - Diabetes" and A1.2
    TableSpec("ITR2024_A2.10", "ITR 2024", "Annexure 2.10", (211, 212), 9, (
        F("known_status", 2, "TB patients with known DM status, n(%): Total, count part"),
        F("diabetic", 5, "TB - DM patients diagnosed among tested, n(%): Total, count part"),
        F("initiated", 8, "TB- DM patients initiated on anti-diabetic treatment, n(%): Total, "
                          "count part"),
    ), "2.10. TB - Diabetes", "TB patients with known DM status, n"),
    TableSpec("ITR2024_A1.2", "ITR 2024", "Annexure 1.2", (187, 188), 9, (
        F("notified", 5, "TB patients notified, n(% of achievement against target): Total, "
                         "count part"),
    ), "1.2. TB case notification", "Target of TB patients expected"),
    # Plan section 12.1: the main 2023 N.
    TableSpec("ITR2024_A1.4", "ITR 2024", "Annexure 1.4", (191, 192), 9, (
        F("notified", 5, "Net TB patients* notified (Based on current PHI); public-private "
                         "disaggregated: Total"),
    ), "1.4. Patient transfer status and treatment initiation status",
        "Net TB patients* notified"),
)}

# Data year -> measure -> (table key, fields summed for a printed row, flags
# carried by every row of the measure).
_A26 = "itr2020_a26_discrepancy"
_P121 = "plan_12.1"
_SEX = ("male", "female", "transgender")
Source = tuple[str, tuple[str, ...], tuple[str, ...]]
SOURCES: dict[int, dict[str, Source]] = {
    2018: {
        "notified": ("ITR2019_A1.2", ("notified",),
                     ("denominator_own_table", "denominator_current_phi")),
        "known_status": ("ITR2019_A1.2", ("known_status",),
                         ("known_blood_sugar_status_wording",)),
        "diabetic": ("ITR2019_A1.2", ("diabetic",), ()),
        "initiated": ("ITR2019_A1.2", ("initiated",), ("c3_linked_ncd_clinic",)),
    },
    2019: {
        # ITR 2020 A2.5 prints no basis for its notified column (no footnote, no
        # header note on PDF pp. 216-217): recorded as notified_basis_not_stated.
        "notified": ("ITR2020_A2.5", ("notified",),
                     ("denominator_own_table", "notified_basis_not_stated", _A26)),
        "known_status": ("ITR2020_A2.5", ("known_status",), (_A26,)),
        "diabetic": ("ITR2020_A2.5", ("diabetic",), (_A26,)),
        "initiated": ("ITR2020_A2.5", ("initiated",), (_A26,)),
    },
    # 2021-2023 notified: plan section 12.1 (21 Nov 2026) puts N on the basis of
    # the diabetes tables' own percentages. The registered A1.2 basis is kept as
    # a sensitivity (REGISTERED_NOTIFIED).
    2021: {
        "notified": ("TBAR2022_A1.4", ("notified",),
                     ("denominator_a1_4_net_current_phi", _P121)),
        "known_status": ("TBAR2022_A2.5", ("known_status",), ()),
        "diabetic": ("TBAR2022_A2.5", ("diabetic",), ()),
        "initiated": ("TBAR2022_A2.5", ("initiated",), ()),
    },
    2022: {
        "notified": ("ITR2023_A1.6", _SEX, ("denominator_a1_6_sex_sum", _P121)),
        "known_status": ("ITR2023_A2.10", ("known_status",), ()),
        "diabetic": ("ITR2023_A2.10", ("diabetic",), ()),
        "initiated": ("ITR2023_A2.10", ("initiated",), ()),
    },
    2023: {
        "notified": ("ITR2024_A1.4", ("notified",),
                     ("denominator_a1_4_net_current_phi", _P121)),
        "known_status": ("ITR2024_A2.10", ("known_status",), ()),
        "diabetic": ("ITR2024_A2.10", ("diabetic",), ()),
        "initiated": ("ITR2024_A2.10", ("initiated",), ()),
    },
}
# The registered N of 2021-2023 (plan section 3.3: A1.2, diagnosing PHI), kept as
# the plan section 12.1 sensitivity.
REGISTERED_NOTIFIED: dict[int, Source] = {
    y: (k, ("notified",), ("denominator_a1_2_diagnosing_phi", "plan_12.1_registered_basis"))
    for y, k in ((2021, "TBAR2022_A1.2"), (2022, "ITR2023_A1.2"), (2023, "ITR2024_A1.2"))
}
YEARS = tuple(SOURCES)

# Printed-total differences found at extraction (plan section 3.5): (table key,
# field) -> (sum of the 36 printed State/UT rows, printed India value). Recorded,
# not corrected; any other difference fails the check.
RECORDED_GAPS: dict[tuple[str, str], tuple[int | Decimal, int | Decimal]] = {
    # ITR 2019 A1.2: the 36 State/UT cells of the three diabetes columns sum to
    # more than the India row prints (known status +1057, TB-DM +81, linked to
    # NCD clinic +31). Every cell was read twice, by character position (grid.py)
    # and by PyMuPDF text blocks, and the two readings agree cell for cell
    # (21 Nov 2026); the differences are in the printed table. The notified
    # column sums exactly.
    ("ITR2019_A1.2", "known_status"): (620527, 619470),
    ("ITR2019_A1.2", "diabetic"): (47678, 47597),
    ("ITR2019_A1.2", "initiated"): (18913, 18882),
}


# ---- cell values ------------------------------------------------------------------

def _pct(text: str) -> Decimal:
    """'(67%)' / '(91.5)' -> Decimal('67') / Decimal('91.5')."""
    t = text.strip()
    if not (t.startswith("(") and t.endswith(")")):
        raise ValueError(f"not a percentage: {text!r}")
    t = t[1:-1].replace("%", "").strip()
    try:
        return Decimal(t)
    except ArithmeticError:
        raise ValueError(f"not a percentage: {text!r}") from None


def derive_from_percent(base: int, pct_text: str) -> tuple[int, int, int]:
    """(count, lo, hi) for a cell that prints only a percentage of `base`.

    count = round-half-up(base x pct / 100); [lo, hi] are the whole counts whose
    percentage rounds to the printed value (half a unit of its last digit).
    """
    p = _pct(pct_text)
    half = Decimal(1).scaleb(p.as_tuple().exponent) / 2
    count = int((Decimal(base) * p / 100).quantize(Decimal(1), rounding=ROUND_HALF_UP))
    lo = max(0, math.ceil(Decimal(base) * (p - half) / 100))
    hi = min(base, math.floor(Decimal(base) * (p + half) / 100))
    if lo > hi:
        raise ValueError(f"no count of {base} prints as {pct_text!r}")
    return count, lo, hi


def cell_count(cell: annex.Cell | None, base: int | None, where: str
               ) -> tuple[int | None, list[str]]:
    """(count, flags) of one printed cell. A blank or absent cell gives None. A
    percent-only cell is derived from `base` and flagged."""
    if cell is None:
        return None, []
    if cell.n is not None:
        try:
            return cells.parse_int(cell.n), []
        except ValueError as e:
            raise ValueError(f"{where}: {e}") from None
    if cell.pct is None or "NA" in cell.pct or cell.pct.replace(" ", "") in ("(%)", "()"):
        return None, []
    if base is None:
        raise ValueError(f"{where}: percent-only cell {cell.raw!r} has no base")
    v, lo, hi = derive_from_percent(base, cell.pct)
    return v, [f"derived_from_percent:{cell.pct.strip()}_of_{base}_range_{lo}-{hi}"]


# ---- reading ----------------------------------------------------------------------

@dataclass
class Table:
    spec: TableSpec
    cells: dict[str, list[annex.Cell | None]]  # printed unit (and "India") -> cells
    pages: dict[str, int]
    raw_names: dict[str, str]


def _squash(s: str) -> str:
    return "".join(s.split()).casefold()


def read_table(spec: TableSpec, pdf_path: Path | None = None) -> Table:
    import pdfplumber  # only the extraction needs it

    from src.extract import grid, pdftext

    path = pdf_path or ROOT / spec.source_file
    rows: dict[str, list[annex.Cell | None]] = {}
    pages: dict[str, int] = {}
    raw: dict[str, str] = {}
    with pdfplumber.open(path) as pdf:
        for i, p in enumerate(spec.pages):
            chars, w, h = pdftext.page_chars(pdf, p)
            lines = grid.lines_of(chars, w, h, spec.region)
            text = "".join("".join(t.text for t in ln.tokens) for ln in lines).casefold()
            if i == 0 and spec.title is not None and _squash(spec.title) not in text:
                raise ValueError(f"{spec.key}: title {spec.title!r} not on PDF p. {p}")
            if _squash(spec.header) not in text:
                raise ValueError(f"{spec.key}: header {spec.header!r} not on PDF p. {p}")
            try:
                pr = grid.read_page(chars, w, h, spec.year, spec.ncells, spec.region)
            except ValueError as e:
                raise ValueError(f"{spec.key} PDF p. {p}: {e}") from None
            found = list(pr.rows.items())
            if pr.national is not None:
                found.append((crosswalk.NATIONAL, pr.national))
            for name, cs in found:
                if name in rows:
                    raise ValueError(f"{spec.key}: {name} printed on two pages")
                rows[name], pages[name], raw[name] = cs, p, pr.raw_names[name]
    if crosswalk.NATIONAL not in rows:
        raise ValueError(f"{spec.key}: no India row")
    missing = [u for u in crosswalk.PRINTED[spec.year] if u not in rows]
    if missing:
        raise ValueError(f"{spec.key}: printed rows not found: {missing}")
    return Table(spec, rows, pages, raw)


@lru_cache(maxsize=None)
def read_all() -> dict[str, Table]:
    return {k: read_table(s) for k, s in SPECS.items()}


# ---- printed cells (before coarsening) ------------------------------------------------

@dataclass
class CellValue:
    value: int | Decimal | None
    flags: list[str]


def cell_values(tables: dict[str, Table]) -> dict[tuple[str, str, str], CellValue]:
    """(table key, printed unit or "India", field) -> value. Percent-only cells are
    derived from their base (PCT_BASE), which is read first."""
    out: dict[tuple[str, str, str], CellValue] = {}
    order = {"notified": 0, "known_status": 1, "diabetic": 2, "initiated": 3}
    todo = [(t, f) for t in tables.values() for f in t.spec.fields]
    todo.sort(key=lambda tf: order.get(tf[1].name, -1))
    for t, f in todo:
        for u, cs in t.cells.items():
            where = f"{t.spec.key} {u} {f.name}"
            c = cs[f.index]
            if f.decimal:
                v = None if c is None or c.n is None else cells.parse_decimal(c.n)
                out[(t.spec.key, u, f.name)] = CellValue(v, [])
                continue
            base = None
            if f.name in PCT_BASE and t.spec.year in SOURCES:
                src = SOURCES[t.spec.year][PCT_BASE[f.name]]
                if all((src[0], u, b) in out for b in src[1]):
                    base = member_value(out, src, u).value  # type: ignore[assignment]
            v, flags = cell_count(c, base, where)
            out[(t.spec.key, u, f.name)] = CellValue(v, flags)
    for t in tables.values():
        blank = [f.name for f in t.spec.fields
                 if out[(t.spec.key, crosswalk.NATIONAL, f.name)].value is None]
        if blank:
            raise ValueError(f"{t.spec.key}: India row blank in {blank}")
    return out


def member_value(vals: dict[tuple[str, str, str], CellValue], src: Source,
                 printed: str) -> CellValue:
    """The value of one printed row for a source: the sum of its fields (one
    field, or the A1.6 male + female + transgender); None if any is blank."""
    key, fields, _ = src
    cvs = [vals[(key, printed, f)] for f in fields]
    if any(cv.value is None for cv in cvs):
        return CellValue(None, [])
    return CellValue(sum(cv.value for cv in cvs), [fl for cv in cvs for fl in cv.flags])


def total_checks(tables: dict[str, Table], vals: dict[tuple[str, str, str], CellValue]
                 ) -> list[dict]:
    """One row per table and extracted column: State sum, printed India value,
    the difference (sum - printed) and the number of blank State cells."""
    out = []
    for key, t in tables.items():
        for f in t.spec.fields:
            states = [vals[(key, u, f.name)].value for u in crosswalk.PRINTED[t.spec.year]]
            s, nat, blanks = annex.total_gaps(states, vals[(key, crosswalk.NATIONAL, f.name)].value)
            out.append({"table_key": key, "field": f.name, "state_sum": s, "printed": nat,
                        "difference": s - nat, "blank_cells": blanks})
    return out


def unrecorded_gaps(checks: list[dict],
                    recorded: dict[tuple[str, str], tuple] = RECORDED_GAPS) -> list[str]:
    """Differences not in `recorded`, and recorded gaps that are not found."""
    bad = []
    keys = {(c["table_key"], c["field"]) for c in checks}
    for c in checks:
        k = (c["table_key"], c["field"])
        if c["difference"] != 0:
            if recorded.get(k) != (c["state_sum"], c["printed"]):
                bad.append(f"{k[0]} {k[1]}: State sum {c['state_sum']} vs printed "
                           f"{c['printed']} (difference {c['difference']}) is not recorded")
        elif k in recorded:
            bad.append(f"{k[0]} {k[1]}: recorded gap {recorded[k]} no longer present")
    for k in recorded:
        if k not in keys:
            bad.append(f"recorded gap for unknown column {k}")
    return bad


def cell_rows(tables: dict[str, Table], vals: dict[tuple[str, str, str], CellValue]
              ) -> list[dict]:
    out = []
    for key, t in tables.items():
        for u in list(crosswalk.PRINTED[t.spec.year]) + [crosswalk.NATIONAL]:
            for f in t.spec.fields:
                c = t.cells[u][f.index]
                cv = vals[(key, u, f.name)]
                out.append({
                    "edition": t.spec.edition, "year": t.spec.year, "table_key": key,
                    "table_id": t.spec.table_id, "pdf_page": t.pages[u],
                    "printed_name": t.raw_names[u], "printed_unit": u,
                    "unit": "" if u == crosswalk.NATIONAL else crosswalk.coarsen(u),
                    "field": f.name, "column_header": f.header,
                    "cell_printed": "" if c is None else c.raw,
                    "value": cv.value, "flag": ";".join(cv.flags),
                })
    return out


# ---- the panel (coarsened units) ------------------------------------------------------

def na_reasons(n: int | None, k: int | None, d: int | None, i: int | None) -> dict[str, str]:
    """Plan section 3.5: the cascade steps that are NA for one unit-year, with the
    reason. C1 = K/N, y (and C2) = D/K, C3 = I/D. A missing input makes its step NA."""
    out: dict[str, str] = {}
    for step, num, den, num_name, den_name in (("C1", k, n, "known_status", "notified"),
                                               ("y", d, k, "diabetic", "known_status"),
                                               ("C3", i, d, "initiated", "diabetic")):
        if num is None or den is None:
            out[step] = "input_missing"
        elif den == 0:
            out[step] = f"{den_name}_zero"
        elif num > den:
            out[step] = f"{num_name}_exceeds_{den_name}"
    return out


NA_STEP_OF = {"known_status": "C1", "diabetic": "y", "initiated": "C3"}


def panel_rows(tables: dict[str, Table], vals: dict[tuple[str, str, str], CellValue],
               sources: dict[int, dict[str, Source]] = SOURCES) -> list[dict]:
    out = []
    for year in sources:
        for unit in crosswalk.UNITS:
            mem = crosswalk.members(unit, year)
            rows: dict[str, dict] = {}
            for m_name in MEASURES:
                src = sources[year][m_name]
                key, _, extra = src
                t = tables[key]
                used, missing, flags = [], [], list(extra)
                total = 0
                for m in mem:
                    cv = member_value(vals, src, m)
                    if cv.value is None:
                        missing.append(m)
                        continue
                    used.append(m)
                    total += cv.value  # type: ignore[operator]
                    flags += [f"{fl}@{m}" if len(mem) > 1 else fl for fl in cv.flags]
                if len(mem) > 1:
                    flags.append("merged:" + "+".join(mem))
                flags += [f"member_missing:{m}" for m in missing]
                value: int | None = total
                if not used:
                    value = None
                    flags.append("NA:all_members_missing")
                rows[m_name] = {
                    "unit": unit, "year": year, "measure": m_name, "value": value,
                    "source_file": t.spec.source_file,
                    "pdf_page": ";".join(str(p) for p in sorted({t.pages[m] for m in mem})),
                    "table_id": t.spec.table_id, "flag": flags,
                }
            na = na_reasons(*(rows[m]["value"] for m in MEASURES))
            for m_name, step in NA_STEP_OF.items():
                if step in na:
                    rows[m_name]["flag"].append(f"NA:{step}:{na[step]}")
            for m_name in MEASURES:
                r = rows[m_name]
                r["flag"] = ";".join(r["flag"])
                out.append(r)
    return out


def registered_notified_rows(tables: dict[str, Table],
                            vals: dict[tuple[str, str, str], CellValue]) -> list[dict]:
    """Plan section 12.1 sensitivity: the notified rows of 2021-2023 on the
    registered A1.2 basis (dm_panel.csv columns). Where known status exceeds this
    N, the C1 NA flag of plan section 3.5 is carried on the notified row itself."""
    srcs = {y: dict(SOURCES[y], notified=REGISTERED_NOTIFIED[y]) for y in REGISTERED_NOTIFIED}
    rows = panel_rows(tables, vals, srcs)
    known = {(r["unit"], r["year"]): r for r in rows if r["measure"] == "known_status"}
    out = []
    for r in rows:
        if r["measure"] != "notified":
            continue
        na = [f for f in known[(r["unit"], r["year"])]["flag"].split(";")
              if f.startswith("NA:C1:")]
        out.append(dict(r, flag=";".join([f for f in r["flag"].split(";") if f] + na)))
    return out


def implied_n(k: int, pct_text: str) -> tuple[int, int, int]:
    """(N, lo, hi) for a count K printed with percentage p of N: N =
    round-half-up(K x 100 / p), and [lo, hi] the whole N for which K/N prints as
    p (half a unit of p's last digit either side)."""
    p = _pct(pct_text)
    if p <= 0 or k <= 0:
        raise ValueError(f"no denominator is implied by {k} at {pct_text!r}")
    half = Decimal(1).scaleb(p.as_tuple().exponent) / 2
    n = int((Decimal(k) * 100 / p).quantize(Decimal(1), rounding=ROUND_HALF_UP))
    lo = math.ceil(Decimal(k) * 100 / (p + half))
    hi = math.floor(Decimal(k) * 100 / (p - half)) if p - half > 0 else n
    return n, lo, hi


FROM_PCT_COLS = PANEL_COLS[:4] + ["value_lo", "value_hi"] + PANEL_COLS[4:]


def notified_2022_from_percent(tables: dict[str, Table]) -> list[dict]:
    """Plan section 12.1 sensitivity for 2022: N back-calculated from the printed
    ITR 2023 A2.10 Total known-status percentage ("% of notified"), summed over
    the unit's printed rows, with the summed rounding-interval bounds."""
    t = tables["ITR2023_A2.10"]
    f = t.spec.field("known_status")
    out = []
    for unit in crosswalk.UNITS:
        mem = crosswalk.members(unit, 2022)
        n = lo = hi = 0
        flags = ["derived_from_percent", "plan_12.1_sensitivity"]
        used = []
        for m in mem:
            c = t.cells[m][f.index]
            if c is None or c.n is None or c.pct is None:
                flags.append(f"member_missing:{m}")
                continue
            a, b, d = implied_n(cells.parse_int(c.n), c.pct)
            n, lo, hi = n + a, lo + b, hi + d
            used.append(m)
        if len(mem) > 1:
            flags.append("merged:" + "+".join(mem))
        vals: tuple = (n, lo, hi) if used else (None, None, None)
        if not used:
            flags.append("NA:all_members_missing")
        out.append({"unit": unit, "year": 2022, "measure": "notified", "value": vals[0],
                    "value_lo": vals[1], "value_hi": vals[2],
                    "source_file": t.spec.source_file,
                    "pdf_page": ";".join(str(p) for p in sorted({t.pages[m] for m in mem})),
                    "table_id": t.spec.table_id, "flag": ";".join(flags)})
    return out


def sex_rows(tables: dict[str, Table], vals: dict[tuple[str, str, str], CellValue]
             ) -> list[dict]:
    t = tables["ITR2023_A1.6"]
    out = []
    for u in list(crosswalk.PRINTED[t.spec.year]) + [crosswalk.NATIONAL]:
        r = {s: vals[(t.spec.key, u, s)].value for s in ("male", "female", "transgender")}
        flags = []
        if u == crosswalk.NATIONAL:
            flags.append("national_row")
        flags += [f"blank:{s}" for s, v in r.items() if v is None]
        out.append({"printed_name": t.raw_names[u], "printed_unit": u,
                    "unit": "" if u == crosswalk.NATIONAL else crosswalk.coarsen(u), **r,
                    "source_file": t.spec.source_file, "pdf_page": t.pages[u],
                    "table_id": t.spec.table_id, "flag": ";".join(flags)})
    return out


def write_all(tables: dict[str, Table], out_dir: Path = EXTRACTED) -> dict[str, Path]:
    vals = cell_values(tables)
    paths = {"cells": out_dir / CELLS_CSV.name, "panel": out_dir / PANEL_CSV.name,
             "registered": out_dir / REGISTERED_CSV.name,
             "from_percent": out_dir / FROM_PCT_CSV.name, "sex": out_dir / SEX_CSV.name}
    annex.write_csv(paths["cells"], CELL_COLS, cell_rows(tables, vals))
    annex.write_csv(paths["panel"], PANEL_COLS, panel_rows(tables, vals))
    annex.write_csv(paths["registered"], PANEL_COLS, registered_notified_rows(tables, vals))
    annex.write_csv(paths["from_percent"], FROM_PCT_COLS, notified_2022_from_percent(tables))
    annex.write_csv(paths["sex"], SEX_COLS, sex_rows(tables, vals))
    return paths


def main() -> int:
    tables = read_all()
    vals = cell_values(tables)
    checks = total_checks(tables, vals)
    for c in checks:
        mark = "ok" if c["difference"] == 0 else "GAP"
        print(f"{mark}: {c['table_key']} {c['field']}: State sum {c['state_sum']}, "
              f"printed {c['printed']}, blanks {c['blank_cells']}")
    bad = unrecorded_gaps(checks)
    for b in bad:
        print(f"FAIL: {b}")
    if bad:
        return 1
    for p in write_all(tables).values():
        print(f"wrote {p.relative_to(ROOT).as_posix()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
