"""Task 3 extraction: the three pinned Review Focus tests, the printed-total and
coarsening checks, and the structure of the extracted files.

No PDF is needed: the rules are tested on synthetic cells, and the committed
extracts in data/extracted/ are checked directly.
"""
import csv
from decimal import Decimal
from pathlib import Path

import pytest

from src.extract import annex, crosswalk, itr_dm, nfhs
from verification import check_extraction_totals as cet

ROOT = Path(__file__).resolve().parents[1]
EXTRACTED = ROOT / "data" / "extracted"
SIBLING_CELLS = ROOT.parent / "tb_priority_tool" / "data" / "extracted" / "state_cells.csv"


def _read(name: str) -> list[dict]:
    with open(EXTRACTED / name, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


# ---- synthetic tables -------------------------------------------------------------

DEFAULT = {"notified": 1000, "known_status": 900, "diabetic": 80, "initiated": 50,
           "male": 600, "female": 399, "transgender": 1, "population_lakhs": Decimal("1.00")}


def _fake() -> tuple[dict, dict]:
    tables, vals = {}, {}
    for key, spec in itr_dm.SPECS.items():
        units = list(crosswalk.PRINTED[spec.year]) + [crosswalk.NATIONAL]
        tables[key] = itr_dm.Table(spec, {}, {u: spec.pages[0] for u in units}, {})
        for u in units:
            for f in spec.fields:
                vals[(key, u, f.name)] = itr_dm.CellValue(DEFAULT[f.name], [])
    return tables, vals


def _panel(tables, vals) -> dict[tuple[str, int, str], dict]:
    return {(r["unit"], r["year"], r["measure"]): r for r in itr_dm.panel_rows(tables, vals)}


# ---- Review Focus 1 ---------------------------------------------------------------

def test_impossible_counts_become_na():
    # The rule itself (plan section 3.5), one step at a time.
    assert itr_dm.na_reasons(100, 120, 10, 5) == {"C1": "known_status_exceeds_notified"}
    assert itr_dm.na_reasons(100, 50, 60, 5) == {"y": "diabetic_exceeds_known_status"}
    assert itr_dm.na_reasons(100, 50, 10, 11) == {"C3": "initiated_exceeds_diabetic"}
    assert itr_dm.na_reasons(0, 0, 0, 0) == {"C1": "notified_zero", "y": "known_status_zero",
                                             "C3": "diabetic_zero"}
    assert itr_dm.na_reasons(100, 100, 100, 100) == {}
    assert itr_dm.na_reasons(None, 10, 5, 1) == {"C1": "input_missing"}

    # In the panel: known > notified for Bihar 2022 makes C1 NA (flag on the
    # known_status row) but keeps the printed counts, so y and C3 are unaffected.
    tables, vals = _fake()
    vals[("ITR2023_A2.10", "Bihar", "known_status")] = itr_dm.CellValue(1500, [])
    vals[("TBAR2022_A2.5", "Assam", "diabetic")] = itr_dm.CellValue(950, [])
    vals[("ITR2024_A2.10", "Goa", "initiated")] = itr_dm.CellValue(81, [])
    p = _panel(tables, vals)
    k = p[("Bihar", 2022, "known_status")]
    assert k["value"] == 1500
    assert "NA:C1:known_status_exceeds_notified" in k["flag"].split(";")
    assert "NA:" not in p[("Bihar", 2022, "diabetic")]["flag"]
    assert "NA:" not in p[("Bihar", 2022, "initiated")]["flag"]
    assert "NA:y:diabetic_exceeds_known_status" in p[("Assam", 2021, "diabetic")]["flag"]
    # Assam 2021 also has I (50) <= D (950): C3 stays valid.
    assert "NA:" not in p[("Assam", 2021, "initiated")]["flag"]
    assert "NA:C3:initiated_exceeds_diabetic" in p[("Goa", 2023, "initiated")]["flag"]
    flagged = [key for key, r in p.items() if "NA:" in r["flag"]]
    assert sorted(flagged) == sorted([("Bihar", 2022, "known_status"),
                                      ("Assam", 2021, "diabetic"),
                                      ("Goa", 2023, "initiated")])


def test_real_panel_na_flags_match_the_rule():
    rows = _read("dm_panel.csv")
    by = {}
    for r in rows:
        by.setdefault((r["unit"], int(r["year"])), {})[r["measure"]] = r
    for (unit, year), ms in by.items():
        v = [None if ms[m]["value"] == "" else int(ms[m]["value"]) for m in itr_dm.MEASURES]
        na = itr_dm.na_reasons(*v)
        for m, step in itr_dm.NA_STEP_OF.items():
            flags = [f for f in ms[m]["flag"].split(";") if f.startswith("NA:")]
            want = [f"NA:{step}:{na[step]}"] if step in na else []
            assert flags == want, (unit, year, m)


def test_member_missing_adds_nothing_and_is_flagged():
    tables, vals = _fake()
    vals[("ITR2023_A2.10", "Ladakh", "diabetic")] = itr_dm.CellValue(None, [])
    vals[("ITR2023_A2.10", "Jammu and Kashmir", "diabetic")] = itr_dm.CellValue(70, [])
    p = _panel(tables, vals)
    r = p[("Jammu and Kashmir", 2022, "diabetic")]
    assert r["value"] == 70
    assert "member_missing:Ladakh" in r["flag"].split(";")
    assert "merged:Jammu and Kashmir+Ladakh" in r["flag"].split(";")
    for u in ("Jammu and Kashmir", "Ladakh"):
        vals[("ITR2023_A2.10", u, "diabetic")] = itr_dm.CellValue(None, [])
    r = _panel(tables, vals)[("Jammu and Kashmir", 2022, "diabetic")]
    assert r["value"] is None and "NA:all_members_missing" in r["flag"]


# ---- Review Focus 2 ---------------------------------------------------------------

def test_unmatched_nfhs_unit_raises():
    with pytest.raises(KeyError, match="Atlantis"):
        crosswalk.nfhs_printed_unit("Atlantis")
    sheets = [name for _, _, name in nfhs.SHEETS]
    assert len(sheets) == 37
    # A sheet with no TB unit is named in the error.
    with pytest.raises(KeyError, match="Daman & Diu only"):
        crosswalk.match_nfhs(sheets + ["Daman & Diu only"])
    # A TB unit with no NFHS sheet is named in the error.
    with pytest.raises(ValueError, match="Ladakh"):
        crosswalk.match_nfhs([s for s in sheets if s != "Ladakh"])
    # Two sheets for one unit.
    with pytest.raises(ValueError, match="two NFHS-5 sheets"):
        crosswalk.match_nfhs(sheets + ["Delhi"])
    # An ITR printed name that is not in the crosswalk also stops extraction.
    with pytest.raises(KeyError, match="Atlantis"):
        crosswalk.printed_unit("Atlantis", 2022)
    # The real sheets match the 36 printed rows of 2022 and the India sheet.
    m = crosswalk.match_nfhs(sheets)
    assert m["NCT Delhi"] == "Delhi"
    assert m["Dadra & Nagar Haveli and Daman & Diu"] == crosswalk.DNHDD
    assert m["India"] == crosswalk.NATIONAL
    assert set(m.values()) == set(crosswalk.PRINTED[2022]) | {crosswalk.NATIONAL}


def test_nfhs_build_rejects_unmatched_sheet_and_missing_population():
    cells = {(f, p, name): {"women": "10.0", "men": "11.0"} for f, p, name in nfhs.SHEETS}
    pop = {u: "1.00" for u in crosswalk.PRINTED[2022]} | {crosswalk.NATIONAL: "36.00"}
    assert len(nfhs.build(cells, pop)) == 74
    bad = dict(cells)
    bad[(nfhs.PHASE1, 999, "Atlantis")] = {"women": "1.0", "men": "1.0"}
    del bad[(nfhs.PHASE1, 85, "Ladakh")]
    with pytest.raises(KeyError, match="Atlantis"):
        nfhs.build(bad, pop)
    del pop["Ladakh"]
    with pytest.raises(ValueError, match="Ladakh"):
        nfhs.build(cells, pop)


def test_nfhs_cell_flags():
    assert nfhs.parse_total("17.5") == ("17.5", [])
    assert nfhs.parse_total("(17.2)") == ("17.2", ["nfhs_small_sample"])
    assert nfhs.parse_total("*") == (None, ["nfhs_suppressed"])
    with pytest.raises(ValueError):
        nfhs.parse_total("na")


# ---- Review Focus 3 ---------------------------------------------------------------

def test_percent_only_cell_derivation_flagged():
    # A printed count is used, not its percentage.
    assert itr_dm.cell_count(annex.Cell("190", "(33%)", "190 (33%)"), 606, "x") == (190, [])
    # A percent-only cell: round-half-up(base x % / 100), flagged with its range.
    v, flags = itr_dm.cell_count(annex.Cell(None, "(52%)", "(52%)"), 606, "x")
    assert v == 315  # 606 x 0.52 = 315.12
    assert flags == ["derived_from_percent:(52%)_of_606_range_313-318"]
    assert itr_dm.derive_from_percent(202, "(25%)") == (51, 50, 51)  # 50.5 rounds half up
    with pytest.raises(ValueError, match="no count"):
        itr_dm.derive_from_percent(10, "(25%)")  # no whole count of 10 prints as 25%
    assert itr_dm.derive_from_percent(1000, "(91.5)") == (915, 915, 915)
    # No base: an error, not a guess.
    with pytest.raises(ValueError, match="no base"):
        itr_dm.cell_count(annex.Cell(None, "(52%)", "(52%)"), None, "x")
    # Blank markers are not percentages.
    assert itr_dm.cell_count(annex.Cell(None, "(NA)", "(NA)"), 606, "x") == (None, [])
    assert itr_dm.cell_count(None, 606, "x") == (None, [])

    # Through the panel: the base of known status is the same row's notified;
    # the flag reaches the unit's row.
    tables, _ = _fake()
    t = tables["ITR2023_A2.10"]
    for u in list(crosswalk.PRINTED[2022]) + [crosswalk.NATIONAL]:
        t.cells[u] = [annex.Cell("1", None, "1")] * 9
    t.cells["Goa"] = [None, None, annex.Cell(None, "(91.5)", "(91.5)"),
                      None, None, annex.Cell("80", "(8.7)", "80 (8.7)"),
                      None, None, annex.Cell("50", "(62.5)", "50 (62.5)")]
    # The 2022 base N is the A1.6 male + female + transgender sum (plan section 12.1).
    s = tables["ITR2023_A1.6"]
    for u in list(crosswalk.PRINTED[2022]) + [crosswalk.NATIONAL]:
        s.cells[u] = [annex.Cell("600", None, "600"), annex.Cell("399", None, "399"),
                      annex.Cell("1", None, "1")] + [None] * 6
    only = {k: tables[k] for k in ("ITR2023_A2.10", "ITR2023_A1.6")}
    vals = itr_dm.cell_values(only)
    assert vals[("ITR2023_A2.10", "Goa", "known_status")].value == 915
    assert vals[("ITR2023_A2.10", "Goa", "known_status")].flags[0].startswith(
        "derived_from_percent:(91.5)_of_1000")
    assert vals[("ITR2023_A2.10", "Goa", "diabetic")].flags == []


def test_no_real_cell_needed_derivation():
    # The inventory found no Total cell that prints only a percentage.
    assert not any("derived_from_percent" in r["flag"] for r in _read("dm_panel.csv"))
    assert not any("derived_from_percent" in r["flag"] for r in _read("dm_cells.csv"))


# ---- printed totals and coarsening -------------------------------------------------

def test_printed_totals_match_or_are_recorded():
    checks = cet.printed_totals(_read("dm_cells.csv"))
    assert len(checks) == sum(len(s.fields) for s in itr_dm.SPECS.values())
    assert itr_dm.unrecorded_gaps(checks) == []
    gaps = {(c["table_key"], c["field"]) for c in checks if c["difference"] != 0}
    assert gaps == set(itr_dm.RECORDED_GAPS)
    assert all(c["difference"] == 0 for c in cet.sex_totals(_read("tb_sex_2022.csv")))


def test_unrecorded_gap_fails():
    checks = cet.printed_totals(_read("dm_cells.csv"))
    c = next(c for c in checks if c["table_key"] == "ITR2024_A2.10" and c["field"] == "diabetic")
    c["state_sum"] += 1
    c["difference"] += 1
    assert any("ITR2024_A2.10 diabetic" in b for b in itr_dm.unrecorded_gaps(checks))


def test_coarsening_preserves_totals():
    assert cet.coarsening(_read("dm_cells.csv"), _read("dm_panel.csv"),
                          _read("dm_panel_notified_registered.csv")) == []


# ---- plan section 12.1 ----------------------------------------------------------

def test_main_n_sources_are_plan_12_1():
    assert itr_dm.SOURCES[2021]["notified"][:2] == ("TBAR2022_A1.4", ("notified",))
    assert itr_dm.SOURCES[2022]["notified"][:2] == ("ITR2023_A1.6",
                                                    ("male", "female", "transgender"))
    assert itr_dm.SOURCES[2023]["notified"][:2] == ("ITR2024_A1.4", ("notified",))
    assert itr_dm.SOURCES[2018]["notified"][0] == "ITR2019_A1.2"
    assert itr_dm.SOURCES[2019]["notified"][0] == "ITR2020_A2.5"


def test_registered_basis_sensitivity_file():
    rows = _read("dm_panel_notified_registered.csv")
    assert list(rows[0]) == itr_dm.PANEL_COLS
    assert len(rows) == 33 * 3
    assert {(r["unit"], int(r["year"])) for r in rows} == \
        {(u, y) for u in crosswalk.UNITS for y in (2021, 2022, 2023)}
    assert all(r["measure"] == "notified" and r["table_id"] == "Annexure 1.2" and
               "plan_12.1_registered_basis" in r["flag"].split(";") for r in rows)
    # On the registered basis known status exceeds N in 6 unit-years (section 3.5);
    # on the plan section 12.1 basis in none.
    na = sorted((r["unit"], int(r["year"])) for r in rows if "NA:C1:" in r["flag"])
    assert na == sorted((u, y) for u in ("Himachal Pradesh", "Tripura")
                        for y in (2021, 2022, 2023))
    assert not any("NA:" in r["flag"] for r in _read("dm_panel.csv"))


def test_2022_from_percent_sensitivity_file():
    rows = _read("dm_panel_notified_2022_from_percent.csv")
    assert list(rows[0]) == itr_dm.FROM_PCT_COLS
    assert len(rows) == 33 and {r["unit"] for r in rows} == set(crosswalk.UNITS)
    for r in rows:
        assert int(r["value_lo"]) <= int(r["value"]) <= int(r["value_hi"]), r["unit"]
        assert {"derived_from_percent", "plan_12.1_sensitivity"} <= set(r["flag"].split(";"))
        assert r["year"] == "2022" and r["table_id"] == "Annexure 2.10"
    # The A1.6 main N lies within, or within 15 patients of, the interval.
    main = {r["unit"]: int(r["value"]) for r in _read("dm_panel.csv")
            if r["year"] == "2022" and r["measure"] == "notified"}
    for r in rows:
        assert int(r["value_lo"]) - 15 <= main[r["unit"]] <= int(r["value_hi"]) + 15, r["unit"]


def test_implied_n():
    assert itr_dm.implied_n(921, "(92.1)") == (1000, 1000, 1000)
    assert itr_dm.implied_n(20, "(100%)") == (20, 20, 20)
    with pytest.raises(ValueError):
        itr_dm.implied_n(0, "(0)")


# ---- structure ---------------------------------------------------------------------

def test_panel_structure():
    rows = _read("dm_panel.csv")
    assert list(rows[0]) == ["unit", "year", "measure", "value", "source_file", "pdf_page",
                             "table_id", "flag"]
    keys = {(r["unit"], int(r["year"]), r["measure"]) for r in rows}
    assert len(rows) == len(keys) == 33 * 5 * 4
    assert {r["unit"] for r in rows} == set(crosswalk.UNITS)
    assert {int(r["year"]) for r in rows} == {2018, 2019, 2021, 2022, 2023}
    assert all(r["value"] != "" and r["source_file"] and r["pdf_page"] and r["table_id"]
               for r in rows)


def test_panel_definition_flags():
    rows = _read("dm_panel.csv")

    def flags(year, measure):
        return [set(r["flag"].split(";")) for r in rows
                if int(r["year"]) == year and r["measure"] == measure]

    assert all({"denominator_own_table", "denominator_current_phi"} <= f
               for f in flags(2018, "notified"))
    assert all("known_blood_sugar_status_wording" in f for f in flags(2018, "known_status"))
    assert all("c3_linked_ncd_clinic" in f for f in flags(2018, "initiated"))
    assert all("itr2020_a26_discrepancy" in f for m in itr_dm.MEASURES for f in flags(2019, m))
    assert all("denominator_own_table" in f for f in flags(2019, "notified"))
    # Plan section 12.1: the main N of 2021-2023.
    assert all({"denominator_a1_4_net_current_phi", "plan_12.1"} <= f
               for y in (2021, 2023) for f in flags(y, "notified"))
    assert all({"denominator_a1_6_sex_sum", "plan_12.1"} <= f for f in flags(2022, "notified"))
    assert not any("denominator_a1_2_diagnosing_phi" in f for y in (2021, 2022, 2023)
                   for f in flags(y, "notified"))
    assert not any("c3_linked_ncd_clinic" in f for y in (2019, 2021, 2022, 2023)
                   for f in flags(y, "initiated"))
    # The 2019 C3 header is "initiated on Anti-diabetic treatment" (plan section 5.1).
    assert "initiated on Anti-diabetic treatment" in \
        itr_dm.SPECS["ITR2020_A2.5"].field("initiated").header


def test_cells_have_provenance():
    rows = _read("dm_cells.csv")
    assert len(rows) == 37 * sum(len(s.fields) for s in itr_dm.SPECS.values())
    assert all(r["pdf_page"] and r["table_id"] and r["cell_printed"] for r in rows)
    # Plan section 3.5: every value carries source_file, pdf_page and table_id.
    assert all(r["source_file"] == itr_dm.SPECS[r["table_key"]].source_file for r in rows)


def test_extraction_rerun_is_byte_identical(tmp_path):
    """Rerunning the extraction from the PDFs reproduces the committed files."""
    if not all((ROOT / s.source_file).is_file() for s in itr_dm.SPECS.values()):
        pytest.skip("data_raw/ is not distributed; run python -I tools/fetch_sources.py")
    paths = itr_dm.write_all(itr_dm.read_all(), tmp_path)
    for p in paths.values():
        assert p.read_bytes() == (EXTRACTED / p.name).read_bytes(), p.name


def test_nfhs_structure():
    rows = _read("nfhs_dm.csv")
    assert list(rows[0]) == ["unit", "sex", "prevalence_pct", "population", "source_file",
                             "pdf_page", "flag"]
    assert len(rows) == 74
    assert {(r["source_file"], r["pdf_page"]) for r in rows} == \
        {(f, str(p)) for f, p, _ in nfhs.SHEETS}
    assert {r["unit"] for r in rows} == set(crosswalk.PRINTED[2022]) | {crosswalk.NATIONAL}
    assert all(r["prevalence_pct"] != "" and r["population"] != "" for r in rows)
    merge = {r["unit"]: r["flag"] for r in rows if "merge_into:" in r["flag"]}
    assert set(merge) == {crosswalk.DNHDD, "Lakshadweep", "Ladakh"}
    assert all("national_sheet_not_used_for_p_u" in r["flag"]
               for r in rows if r["unit"] == crosswalk.NATIONAL)


def test_sex_structure():
    rows = _read("tb_sex_2022.csv")
    assert len(rows) == 37
    assert {r["printed_unit"] for r in rows} == set(crosswalk.PRINTED[2022]) | {"India"}


# ---- cross-check with the priority tool -------------------------------------------

def test_notified_counts_match_the_priority_tool():
    """The priority tool (v1.0.1 checkout) extracted the same notified counts from
    the same PDFs; this repository re-extracted them independently."""
    if not SIBLING_CELLS.is_file():
        pytest.skip("../tb_priority_tool/data/extracted/state_cells.csv not present")
    mine = {(r["table_key"], r["printed_unit"], r["field"]): r["value"]
            for r in _read("dm_cells.csv")}
    rename = {"notified_male": "male", "notified_female": "female",
              "notified_transgender": "transgender", "net_notified": "notified"}
    n = 0
    with open(SIBLING_CELLS, encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f):
            field = rename.get(r["field"], r["field"])
            k = (r["table_key"], r["printed_unit"], field)
            if field in ("notified", "male", "female", "transgender") and k in mine:
                assert mine[k] == r["value"], k
                n += 1
    assert n == 6 * 37 + 3 * 37  # A1.2 x 4, A1.4 (2021, 2023), A1.6 x 3 columns
