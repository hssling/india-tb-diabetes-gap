"""Extract the NFHS-5 raised-blood-sugar indicators (analysis plan sections 3.3,
4.2 and 4.3).

Run: python -I src/extract/nfhs.py   (after src/extract/itr_dm.py)

Reads, from each of the 37 NFHS-5 fact sheets (22 State/UT sheets in Phase I;
the India sheet and 14 State/UT sheets in Phase II), the NFHS-5 Total column
of line 101 (women) and line 104 (men): "Blood sugar level - high or very high
(>140 mg/dl) or taking medicine to control blood sugar level23 (%)", at the
pages listed in docs/data_inventory.md. Writes data/extracted/nfhs_dm.csv:

    unit, sex, prevalence_pct, population, source_file, pdf_page, flag

- ``unit`` is the TB printed row the sheet matches (crosswalk.match_nfhs; the
  2022 structure: one "Dadra and Nagar Haveli and Daman and Diu" sheet, a
  Ladakh sheet), or "India" for the India sheet. One row per sheet and sex:
  the sheets are NOT merged here. The merge of section 4.3 (Gujarat with
  DNH&DD, Kerala with Lakshadweep, Jammu and Kashmir with Ladakh) is a
  population-weighted combination and is left to the analysis (Task 4); a
  member sheet carries ``merge_into:<unit>``.
- ``prevalence_pct`` is the Total cell as printed (a percentage, not divided
  by 100). A cell in parentheses (25-49 unweighted cases) is used and flagged
  ``nfhs_small_sample``; a starred cell is NA (empty) and flagged
  ``nfhs_suppressed``.
- ``population`` is the ITR 2023 Annexure 1.1 "Popula- tion - 2022 (in
  lakhs)" of the sheet's printed row, in lakhs as printed, read from
  data/extracted/dm_cells.csv (the fact sheets print no population; plan
  section 4.2). For the India sheet it is the printed India row. Every row
  carries ``population_lakhs:ITR2023_A1.1``.
- The India sheet is flagged ``national_sheet_not_used_for_p_u`` (section 4.2).

Each page is checked for its "<name> - Key Indicators" heading, the section
"Blood Sugar Level among Adults (age 15 years and above)", the "Women" and
"Men" sub-headings, the indicator wording and footnote 23. Values are placed by
word position: the band between line 101 (or 104) and the next line number,
within the column of the "Total" heading under "NFHS-5".
"""
from __future__ import annotations

import csv
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if __package__ in (None, ""):
    sys.path.insert(0, str(ROOT))

from src.extract import annex, crosswalk  # noqa: E402

EXTRACTED = ROOT / "data" / "extracted"
NFHS_CSV = EXTRACTED / "nfhs_dm.csv"
CELLS_CSV = EXTRACTED / "dm_cells.csv"
COLS = ["unit", "sex", "prevalence_pct", "population", "source_file", "pdf_page", "flag"]

PHASE1 = "data_raw/nfhs5/NFHS-5_India_and_State_Factsheet_Compendium_Phase-I.pdf"
PHASE2 = "data_raw/nfhs5/NFHS-5_India_and_State_Factsheet_Compendium_Phase-II.pdf"

# (file, PDF page of lines 99-104, sheet name as printed in the page heading);
# docs/data_inventory.md, "Pages, per State/UT".
SHEETS: tuple[tuple[str, int, str], ...] = (
    (PHASE1, 13, "Andaman & Nicobar Islands"),
    (PHASE1, 19, "Andhra Pradesh"),
    (PHASE1, 25, "Assam"),
    (PHASE1, 31, "Bihar"),
    (PHASE1, 37, "Dadra & Nagar Haveli and Daman & Diu"),
    (PHASE1, 43, "Goa"),
    (PHASE1, 49, "Gujarat"),
    (PHASE1, 55, "Himachal Pradesh"),
    (PHASE1, 61, "Jammu & Kashmir"),
    (PHASE1, 67, "Karnataka"),
    (PHASE1, 73, "Kerala"),
    (PHASE1, 79, "Lakshadweep"),
    (PHASE1, 85, "Ladakh"),
    (PHASE1, 91, "Maharashtra"),
    (PHASE1, 97, "Meghalaya"),
    (PHASE1, 103, "Manipur"),
    (PHASE1, 109, "Mizoram"),
    (PHASE1, 115, "Nagaland"),
    (PHASE1, 121, "Sikkim"),
    (PHASE1, 127, "Telangana"),
    (PHASE1, 133, "Tripura"),
    (PHASE1, 139, "West Bengal"),
    (PHASE2, 9, "India"),
    (PHASE2, 15, "Arunachal Pradesh"),
    (PHASE2, 21, "Chhattisgarh"),
    (PHASE2, 27, "Haryana"),
    (PHASE2, 33, "Jharkhand"),
    (PHASE2, 39, "Madhya Pradesh"),
    (PHASE2, 45, "Odisha"),
    (PHASE2, 51, "Punjab"),
    (PHASE2, 57, "Rajasthan"),
    (PHASE2, 63, "Tamil Nadu"),
    (PHASE2, 69, "Uttar Pradesh"),
    (PHASE2, 75, "Uttarakhand"),
    (PHASE2, 81, "Chandigarh"),
    (PHASE2, 87, "NCT Delhi"),
    (PHASE2, 93, "Puducherry"),
)
LINES = {"women": "101.", "men": "104."}
LABEL = ("Blood sugar level - high or very high (>140 mg/dl) or taking medicine to "
         "control blood sugar level23 (%)")
SECTION = "Blood Sugar Level among Adults (age 15 years and above)"
FOOTNOTE = "23Random blood sugar measurement."

_VALUE = re.compile(r"^(?:\d+(?:\.\d+)?|\(\d+(?:\.\d+)?\)|\*|na)$")


def _squash(s: str) -> str:
    return "".join(s.split()).casefold()


def parse_total(text: str) -> tuple[str | None, list[str]]:
    """(percentage as printed or None, flags) of one NFHS-5 Total cell."""
    t = text.strip()
    if re.fullmatch(r"\d+(?:\.\d+)?", t):
        return t, []
    m = re.fullmatch(r"\((\d+(?:\.\d+)?)\)", t)
    if m:
        return m.group(1), ["nfhs_small_sample"]
    if t == "*":
        return None, ["nfhs_suppressed"]
    raise ValueError(f"not an NFHS-5 percentage cell: {text!r}")


def _reading_order(words: list[dict], tol: float = 2.0) -> list[dict]:
    """Words grouped into lines (tops within `tol` points), each line left to right."""
    groups: list[list[dict]] = []
    for w in sorted(words, key=lambda w: w["top"]):
        if groups and w["top"] - groups[-1][0]["top"] <= tol:
            groups[-1].append(w)
        else:
            groups.append([w])
    return [w for g in groups for w in sorted(g, key=lambda w: w["x0"])]


def read_sheet(words: list[dict], heading: str) -> dict[str, str]:
    """{'women': Total cell, 'men': Total cell} (as printed) from one page's words
    (pdfplumber extract_words). Raises ValueError if the page is not the
    expected one or a cell cannot be placed."""
    lines: dict[float, list[dict]] = {}
    for w in sorted(words, key=lambda w: (round(w["top"]), w["x0"])):
        lines.setdefault(round(w["top"]), []).append(w)
    texts = [" ".join(w["text"] for w in ws) for _, ws in sorted(lines.items())]
    first = texts[0] if texts else ""
    if _squash(first) != _squash(f"{heading} - Key Indicators"):
        raise ValueError(f"page heading {first!r} is not {heading!r} - Key Indicators")
    page = _squash(" ".join(texts))
    for need in (SECTION, FOOTNOTE):
        if _squash(need) not in page:
            raise ValueError(f"{heading}: {need!r} not on the page")
    head = [w for w in words if w["top"] < 100 and w["text"] in ("Urban", "Rural", "Total")]
    head.sort(key=lambda w: w["x0"])
    if [w["text"] for w in head] != ["Urban", "Rural", "Total", "Total"]:
        raise ValueError(f"{heading}: column headings {[w['text'] for w in head]}")
    cols = {"urban": head[0], "rural": head[1], "total": head[2], "nfhs4": head[3]}

    def col_of(w: dict) -> str | None:
        xc = (w["x0"] + w["x1"]) / 2
        best = min(cols, key=lambda k: abs(xc - (cols[k]["x0"] + cols[k]["x1"]) / 2))
        c = cols[best]
        return best if c["x0"] - 12 <= xc <= c["x1"] + 12 else None

    def top_of(label: str) -> float:
        hits = [w["top"] for w in words if w["text"] == label and w["x0"] < 45]
        if len(hits) != 1:
            raise ValueError(f"{heading}: line {label} found {len(hits)} times")
        return hits[0]

    out: dict[str, str] = {}
    for sex, num in LINES.items():
        t0 = top_of(num)
        # The band ends at the next word in the line-number margin (the "Men"
        # sub-heading after line 101; the "Hypertension ..." section after 104).
        t1 = min(w["top"] for w in words if w["x0"] < 45 and w["top"] > t0 + 1)
        band = [w for w in words if t0 - 2 <= w["top"] < t1 - 2]
        label = " ".join(w["text"] for w in _reading_order([w for w in band if w["x1"] < 400]))
        if _squash(label) != _squash(f"{num} {LABEL}"):
            raise ValueError(f"{heading}: line {num} reads {label!r}")
        vals = [w for w in band if w["x0"] >= 400]
        placed: dict[str, str] = {}
        for w in vals:
            if not _VALUE.match(w["text"]):
                raise ValueError(f"{heading}: line {num}: unexpected token {w['text']!r}")
            k = col_of(w)
            if k is None or k in placed:
                raise ValueError(f"{heading}: line {num}: cannot place {w['text']!r}")
            placed[k] = w["text"]
        if set(placed) != set(cols):
            raise ValueError(f"{heading}: line {num}: cells {placed}")
        out[sex] = placed["total"]
    # "Women" precedes line 99 and "Men" precedes line 102.
    w_top = [w["top"] for w in words if w["text"] == "Women" and w["x0"] < 45]
    m_top = [w["top"] for w in words if w["text"] == "Men" and w["x0"] < 45]
    if not (w_top and m_top and min(w_top) < top_of("99.") and
            top_of("101.") < min(m_top) < top_of("102.")):
        raise ValueError(f"{heading}: the Women/Men sub-headings are not where expected")
    return out


def read_all() -> dict[tuple[str, int, str], dict[str, str]]:
    import pdfplumber

    out: dict[tuple[str, int, str], dict[str, str]] = {}
    for f in (PHASE1, PHASE2):
        with pdfplumber.open(ROOT / f) as pdf:
            for sf, p, name in SHEETS:
                if sf != f:
                    continue
                pg = pdf.pages[p - 1]
                words = [{k: w[k] for k in ("text", "x0", "x1", "top")}
                         for w in pg.extract_words()]
                pg.flush_cache()
                pg.close()
                try:
                    out[(sf, p, name)] = read_sheet(words, name)
                except ValueError as e:
                    raise ValueError(f"{f} PDF p. {p}: {e}") from None
    return out


def populations(path: Path = CELLS_CSV) -> dict[str, str]:
    """Printed TB row (2022) -> ITR 2023 A1.1 population in lakhs, as printed."""
    with open(path, encoding="utf-8", newline="") as f:
        return {r["printed_unit"]: r["value"] for r in csv.DictReader(f)
                if r["table_key"] == "ITR2023_A1.1" and r["field"] == "population_lakhs"}


def build(cells_by_sheet: dict[tuple[str, int, str], dict[str, str]],
          pop: dict[str, str]) -> list[dict]:
    if len(cells_by_sheet) != 37:
        raise ValueError(f"{len(cells_by_sheet)} NFHS-5 sheets read, expected 37")
    match = crosswalk.match_nfhs([name for _, _, name in cells_by_sheet])
    rows = []
    for (f, p, name), vals in cells_by_sheet.items():
        unit = match[name]
        if unit not in pop or pop[unit] == "":
            raise ValueError(f"no ITR 2023 A1.1 population for NFHS-5 sheet {name!r} ({unit})")
        for sex in ("women", "men"):
            pct, flags = parse_total(vals[sex])
            if unit == crosswalk.NATIONAL:
                flags.append("national_sheet_not_used_for_p_u")
            elif crosswalk.coarsen(unit) != unit:
                flags.append(f"merge_into:{crosswalk.coarsen(unit)}")
            if _squash(name) != _squash(unit):
                flags.append(f"sheet_name:{name}")
            flags.append("population_lakhs:ITR2023_A1.1")
            rows.append({"unit": unit, "sex": sex, "prevalence_pct": pct,
                         "population": pop[unit], "source_file": f, "pdf_page": p,
                         "flag": ";".join(flags)})
    rows.sort(key=lambda r: (r["unit"] != crosswalk.NATIONAL, r["unit"], r["sex"] != "women"))
    return rows


def main() -> int:
    rows = build(read_all(), populations())
    annex.write_csv(NFHS_CSV, COLS, rows)
    print(f"wrote {NFHS_CSV.relative_to(ROOT).as_posix()}: {len(rows)} rows")
    return 0


if __name__ == "__main__":
    sys.exit(main())
