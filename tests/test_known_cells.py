"""Pinned values, read by eye from the source pages, so that a wrong column, a
wrong row or a wrong page fails.

The extraction reviewer (21 Nov 2026) read every value below from the
rendered PDF pages (PyMuPDF images at 110-130 dpi), not from the extraction:
ITR 2019 PDF p. 169 (rotated); ITR 2020 p. 217; TBAR 2022 pp. 89 and 96;
ITR 2023 pp. 211, 213, 221 and 240; ITR 2024 pp. 188 and 212; NFHS-5 Phase I
pp. 13 and 85 and Phase II pp. 81 and 87. After plan section 12.1, the
plan's main 2021-2023 N were added, read the same way: TBAR 2022 A1.4 (PDF
p. 91, left half), ITR 2023 A1.6 (p. 221) and ITR 2024 A1.4 (p. 191).
Merged-unit values are the sums of the printed member rows, each read by eye.
"""
import csv
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
EXTRACTED = ROOT / "data" / "extracted"


def _read(name: str) -> list[dict]:
    with open(EXTRACTED / name, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


CELLS = {(r["table_key"], r["printed_unit"], r["field"]): r["value"]
         for r in _read("dm_cells.csv")}
PANEL = {(r["unit"], int(r["year"]), r["measure"]): r["value"] for r in _read("dm_panel.csv")}
SEX = {r["printed_unit"]: r for r in _read("tb_sex_2022.csv")}
NFHS = {(r["unit"], r["sex"]): r["prevalence_pct"] for r in _read("nfhs_dm.csv")}

# (table key, printed row, field): value as printed (count part of the Total cell).
KNOWN_CELLS = {
    # 2018, ITR 2019 A1.2, PDF p. 169 (rotated)
    ("ITR2019_A1.2", "Kerala", "notified"): "24720",
    ("ITR2019_A1.2", "Kerala", "known_status"): "8020",  # 8020 (32%)
    ("ITR2019_A1.2", "Kerala", "diabetic"): "2225",  # 2225 (28%)
    ("ITR2019_A1.2", "Kerala", "initiated"): "1106",  # 1106 (50%), linked to NCD clinic
    ("ITR2019_A1.2", "Assam", "diabetic"): "440",  # 440 (11%), printed over two lines
    ("ITR2019_A1.2", "Lakshadweep", "known_status"): "12",  # 12 (52%)
    # 2019, ITR 2020 A2.5, PDF p. 217
    ("ITR2020_A2.5", "Tamil Nadu", "notified"): "113513",
    ("ITR2020_A2.5", "Tamil Nadu", "known_status"): "79696",
    ("ITR2020_A2.5", "Tamil Nadu", "diabetic"): "16605",
    ("ITR2020_A2.5", "Tamil Nadu", "initiated"): "9490",
    ("ITR2020_A2.5", "Lakshadweep", "known_status"): "16",  # private cell blank
    # 2021, TBAR 2022 A2.5 (PDF p. 96) and A1.2 (PDF p. 89)
    ("TBAR2022_A2.5", "Ladakh", "known_status"): "256",
    ("TBAR2022_A2.5", "Ladakh", "diabetic"): "13",
    ("TBAR2022_A2.5", "Ladakh", "initiated"): "13",
    ("TBAR2022_A2.5", "Kerala", "diabetic"): "6650",
    ("TBAR2022_A1.2", "Puducherry", "notified"): "3444",
    ("TBAR2022_A1.2", "Ladakh", "notified"): "291",
    ("TBAR2022_A1.2", "Jammu and Kashmir", "notified"): "10826",
    # 2021, TBAR 2022 A1.4 "Net TB Patients Notified" (PDF p. 91; plan section 12.1)
    ("TBAR2022_A1.4", "Himachal Pradesh", "notified"): "14797",
    ("TBAR2022_A1.4", "Tripura", "notified"): "2777",
    ("TBAR2022_A1.4", "Jammu and Kashmir", "notified"): "11005",
    ("TBAR2022_A1.4", "Ladakh", "notified"): "319",
    ("TBAR2022_A1.4", "Delhi", "notified"): "84302",
    # 2023, ITR 2024 A1.4 net notified (current PHI), Total (PDF p. 191; section 12.1)
    ("ITR2024_A1.4", "Himachal Pradesh", "notified"): "16046",
    ("ITR2024_A1.4", "Jammu and Kashmir", "notified"): "11747",
    ("ITR2024_A1.4", "Ladakh", "notified"): "346",
    ("ITR2024_A1.4", "Kerala", "notified"): "21812",
    ("ITR2024_A1.4", "Lakshadweep", "notified"): "14",
    # 2022, ITR 2023 A2.10 (PDF p. 240), A1.2 (p. 213), A1.1 (p. 211)
    ("ITR2023_A2.10", "Uttar Pradesh", "known_status"): "490981",
    ("ITR2023_A2.10", "Uttar Pradesh", "diabetic"): "23448",
    ("ITR2023_A2.10", "Uttar Pradesh", "initiated"): "8831",
    ("ITR2023_A2.10", "Lakshadweep", "known_status"): "21",
    ("ITR2023_A1.2", "Gujarat", "notified"): "151912",
    ("ITR2023_A1.2", "Ladakh", "notified"): "320",
    ("ITR2023_A1.1", "Dadra and Nagar Haveli and Daman and Diu", "population_lakhs"): "8.54",
    ("ITR2023_A1.1", "Ladakh", "population_lakhs"): "2.57",
    ("ITR2023_A1.1", "Lakshadweep", "population_lakhs"): "0.67",
    # 2023, ITR 2024 A2.10 (PDF p. 212) and A1.2 (p. 188)
    ("ITR2024_A2.10", "West Bengal", "diabetic"): "12871",
    ("ITR2024_A2.10", "Mizoram", "initiated"): "107",
    ("ITR2024_A2.10", "Tamil Nadu", "known_status"): "97022",
    ("ITR2024_A1.2", "Odisha", "notified"): "62387",
    ("ITR2024_A1.2", "Tripura", "notified"): "3386",
}

# Coarsened units: (unit, year, measure) -> sum of the printed member rows.
KNOWN_PANEL = {
    ("Kerala", 2018, "known_status"): str(8020 + 12),  # Kerala + Lakshadweep
    ("Tamil Nadu", 2019, "initiated"): "9490",
    # Main N after plan section 12.1:
    ("Jammu and Kashmir", 2021, "notified"): str(11005 + 319),  # A1.4, J&K + Ladakh
    ("Himachal Pradesh", 2021, "notified"): "14797",  # A1.4
    ("Kerala", 2022, "notified"): str(15235 + 8289 + 5 + 13 + 9 + 0),  # A1.6 + Lakshadweep
    ("Himachal Pradesh", 2022, "notified"): str(10258 + 6243 + 4),  # A1.6
    ("Jammu and Kashmir", 2023, "notified"): str(11747 + 346),  # A1.4, J&K + Ladakh
    ("Kerala", 2023, "notified"): str(21812 + 14),  # A1.4, Kerala + Lakshadweep
    ("Uttar Pradesh", 2022, "diabetic"): "23448",
    ("West Bengal", 2023, "diabetic"): "12871",
}

# ITR 2023 A1.6, PDF p. 221: (male, female, transgender).
KNOWN_SEX = {
    "Kerala": ("15235", "8289", "5"),
    "Lakshadweep": ("13", "9", "0"),
    "Himachal Pradesh": ("10258", "6243", "4"),
    "Gujarat": ("93866", "54204", "55"),
}

# NFHS-5 Total column, lines 101 (women) and 104 (men).
KNOWN_NFHS = {
    ("Andaman and Nicobar Islands", "women"): "17.5",  # Phase I p. 13
    ("Andaman and Nicobar Islands", "men"): "17.9",
    ("Ladakh", "women"): "6.7",  # Phase I p. 85
    ("Ladakh", "men"): "8.3",
    ("Chandigarh", "women"): "19.0",  # Phase II p. 81; Rural (17.2) is not used
    ("Chandigarh", "men"): "16.6",
    ("Delhi", "women"): "12.2",  # Phase II p. 87, "NCT Delhi"
    ("Delhi", "men"): "14.1",
}


def test_at_least_twelve_values_across_every_year_and_nfhs():
    years = {k[0].split("_")[0] for k in KNOWN_CELLS}
    assert years >= {"ITR2019", "ITR2020", "TBAR2022", "ITR2023", "ITR2024"}
    assert {"TBAR2022_A1.4", "ITR2024_A1.4"} <= {k[0] for k in KNOWN_CELLS}
    assert len(KNOWN_CELLS) + len(KNOWN_PANEL) + len(KNOWN_NFHS) >= 12
    assert {u for u, _ in KNOWN_NFHS} >= {"Ladakh", "Chandigarh"}


@pytest.mark.parametrize("key", sorted(KNOWN_CELLS))
def test_known_cells(key):
    assert CELLS[key] == KNOWN_CELLS[key]


@pytest.mark.parametrize("key", sorted(KNOWN_PANEL))
def test_known_panel(key):
    assert PANEL[key] == KNOWN_PANEL[key]


@pytest.mark.parametrize("unit", sorted(KNOWN_SEX))
def test_known_sex(unit):
    r = SEX[unit]
    assert (r["male"], r["female"], r["transgender"]) == KNOWN_SEX[unit]


@pytest.mark.parametrize("key", sorted(KNOWN_NFHS))
def test_known_nfhs(key):
    assert NFHS[key] == KNOWN_NFHS[key]
