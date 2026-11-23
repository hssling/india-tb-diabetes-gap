# Adapted from hssling/india-tb-priority-tool v1.0.1 (MIT), exhibits/formats.py (itself adapted from
# hssling/india-tb-acf-campaign); modified: the formats of this paper (shares, ratios, patients,
# percentage points), shared by exhibits/make_tables.py, exhibits/make_figures.py,
# exhibits/make_graphical_abstract.py and verification/check_manuscript_numbers.py.
"""Number formats of the manuscript and its exhibits: the only place they are fixed.

Every number printed in the tables, the figure labels and the text goes through one of these
functions, so the number check (verification/check_manuscript_numbers.py) and the exhibits
always agree on how a value from outputs/ is written.
"""
from __future__ import annotations

import csv
import re
from datetime import date
from pathlib import Path

MINUS = "−"  # a negative number is written with the minus sign U+2212
TO = " to "        # every interval: "1.01 to 2.18"
MONTHS = ("January February March April May June July August September October November "
          "December").split()
TIERS = ["act now", "probable priority", "uncertain", "lower priority"]
GAPS = {"E1": "screening gap", "E2": "identification gap", "E3": "linkage gap", "total": "total shortfall"}
CLASSES = ["identification-led", "screening-led", "mixed"]
YEARS = ["2018", "2019", "2021", "2022", "2023"]


def num(x: float | str, dp: int) -> str:
    """x with dp decimals; a negative value with the minus sign."""
    s = f"{float(x):.{dp}f}"
    if s.startswith("-") and float(s) == 0:
        s = s[1:]
    return MINUS + s[1:] if s.startswith("-") else s


def count(x: float | str) -> str:
    """A whole number with thousands separators ("108,647"); x is rounded half to even."""
    v = round(float(x))
    s = f"{v:,}"
    return MINUS + s[1:] if s.startswith("-") else s


def rng(lo: str, hi: str) -> str:
    return f"{lo}{TO}{hi}"


def pct(x: float | str, dp: int = 1) -> str:
    """A share as a percentage: 0.9254 -> "92.5%"."""
    return num(100 * float(x), dp) + "%"


def pp(x: float | str, dp: int = 1) -> str:
    """A difference of shares in percentage points: 0.6272 -> "62.7 percentage points"."""
    return num(100 * float(x), dp) + " percentage points"


def ratio(x: float | str, dp: int = 2) -> str:
    """A ratio or coefficient (R, k, beta): two decimals by default."""
    return num(x, dp)


def prob(x: float | str) -> str:
    """A probability: two decimals; 1 and 0 written in full only when exact."""
    v = float(x)
    if v == 1.0:
        return "1"
    if v == 0.0:
        return "0"
    s = num(v, 2)
    if s == "1.00":
        return num(v, 3) if num(v, 3) != "1.000" else ">0.999"
    if s == "0.00":
        return num(v, 3) if num(v, 3) != "0.000" else "<0.001"
    return s


def patients(mean: str, lo: str, hi: str) -> str:
    """A count of patients with its interval: "5,389 (5,344 to 5,435)"."""
    return f"{count(mean)} ({rng(count(lo), count(hi))})"


def share_ci(x: str, lo: str, hi: str, dp: int = 1) -> str:
    """A share with its interval: "92.5% (92.5% to 92.6%)"."""
    return f"{pct(x, dp)} ({rng(pct(lo, dp), pct(hi, dp))})"


def ratio_ci(x: str, lo: str, hi: str, dp: int = 2) -> str:
    return f"{ratio(x, dp)} ({rng(ratio(lo, dp), ratio(hi, dp))})"


def day(iso: str) -> str:
    """'2026-11-21' -> '21 November 2026'."""
    d = date.fromisoformat(iso[:10])
    return f"{d.day} {MONTHS[d.month - 1]} {d.year}"


def and_list(items: list[str]) -> str:
    """'A, B and C' (no item: 'none')."""
    items = list(items)
    if not items:
        return "none"
    return items[0] if len(items) == 1 else ", ".join(items[:-1]) + " and " + items[-1]


# --------------------------------------------------------------------------------------
# The IJTLD style (manuscript/v2): thousands separated by a no-break space ("108 647",
# "per 100 000") and intervals with an en dash ("1.01–2.18"). Applied to values already
# formatted above, so the numbers themselves never change.
# --------------------------------------------------------------------------------------
NBSP = "\u00a0"


def si_thousands(s: str) -> str:
    """'108,647' -> '108 647' (no-break space); other commas are kept."""
    return re.sub(r"(?<=\d),(?=\d{3}(?!\d))", NBSP, s)


def en_ranges(s: str) -> str:
    """'1.01 to 2.18' -> '1.01–2.18' (only between two numbers)."""
    return re.sub(r"(\d%?) to ((?:" + MINUS + r")?\d)", r"\1–\2", s)


def ijtld_style(s: str) -> str:
    return en_ranges(si_thousands(s))


def about_thousands(x: float | str) -> str:
    """A count rounded to the nearest thousand, IJTLD style: 108647 -> '109 000'."""
    return si_thousands(count(round(float(x) / 1000) * 1000))


def read_csv(root: Path, rel: str) -> list[dict]:
    with open(root / rel, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def one(rows: list[dict], what: str, **kv) -> dict:
    hits = [r for r in rows if all(r[k] == v for k, v in kv.items())]
    if len(hits) != 1:
        raise ValueError(f"{what}: {len(hits)} rows match {kv}")
    return hits[0]


NATIONAL = "National (sum of units)"


def state_rows(rows: list[dict]) -> list[dict]:
    """The rows of the 33 units (the national sum row left out)."""
    return [r for r in rows if r.get("unit") != NATIONAL]
