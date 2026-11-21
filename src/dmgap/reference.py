"""The reference prevalence p_u (plan §4.2-§4.4).

w_u, m_u: NFHS-5 lines 101 (women) and 104 (men), Total column, % / 100. Member sheets
(flag merge_into:<unit>) are merged with the ITR 2023 A1.1 population weights:
w_u = sum_j P_j w_j / sum_j P_j (the same weights for men). The India sheet is not used.
f_u = Female / (Male + Female + Transgender), ITR 2023 A1.6, summed over member rows.
Sex-weighted (main): p_u = f_u w_u + (1 - f_u) m_u. Simple: p_u = (w_u + m_u) / 2.
"""
from __future__ import annotations

import csv
from pathlib import Path

from . import panel

NFHS_CSV = panel.EXTRACTED / "nfhs_dm.csv"
SEX_CSV = panel.EXTRACTED / "tb_sex_2022.csv"
SEX_WEIGHTED = "sex_weighted"
SIMPLE = "simple"
WEIGHTINGS = (SEX_WEIGHTED, SIMPLE)
NATIONAL = "India"


def _read(path: Path) -> list[dict]:
    with open(path, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def load_nfhs() -> list[dict]:
    return _read(NFHS_CSV)


def load_sex() -> list[dict]:
    return _read(SEX_CSV)


def _merge_target(row: dict) -> str:
    for part in row["flag"].split(";"):
        if part.startswith("merge_into:"):
            return part[len("merge_into:"):]
    return row["unit"]


def components(nfhs_rows: list[dict], sex_rows: list[dict]) -> dict[str, dict]:
    """unit -> {members, w, m, f, population weights, flags} (§4.3-§4.4)."""
    sheets: dict[str, dict] = {}
    for r in nfhs_rows:
        if r["unit"] == NATIONAL:
            continue
        s = sheets.setdefault(r["unit"], {"target": _merge_target(r), "pop": None,
                                          "flags": set()})
        if r["population"].strip() == "":
            raise ValueError(f"NFHS sheet {r['unit']!r} has no population (§4.3)")
        pop = float(r["population"])
        if s["pop"] is not None and s["pop"] != pop:
            raise ValueError(f"NFHS sheet {r['unit']!r}: two populations")
        s["pop"] = pop
        if r["prevalence_pct"].strip() in ("", "NA", "*"):
            raise ValueError(f"NFHS sheet {r['unit']!r} {r['sex']}: no value")
        s[r["sex"]] = float(r["prevalence_pct"]) / 100.0
        if "nfhs_small_sample" in r["flag"].split(";"):
            s["flags"].add(f"nfhs_small_sample:{r['unit']}:{r['sex']}")
    by_unit: dict[str, list[str]] = {}
    for name, s in sheets.items():
        if s["target"] not in panel.UNITS:
            raise ValueError(f"NFHS sheet {name!r} maps to no TB unit")
        if "women" not in s or "men" not in s:
            raise ValueError(f"NFHS sheet {name!r} lacks women or men")
        by_unit.setdefault(s["target"], []).append(name)
    missing = [u for u in panel.UNITS if u not in by_unit]
    if missing:
        raise ValueError(f"TB units with no NFHS sheet: {missing}")

    sex: dict[str, list[int]] = {}
    for r in sex_rows:
        if r["unit"] == "":
            continue  # the printed India row
        if r["unit"] not in panel.UNITS:
            raise ValueError(f"A1.6 row maps to no TB unit: {r['unit']!r}")
        acc = sex.setdefault(r["unit"], [0, 0, 0])
        acc[0] += int(r["male"])
        acc[1] += int(r["female"])
        acc[2] += int(r["transgender"])
    missing = [u for u in panel.UNITS if u not in sex]
    if missing:
        raise ValueError(f"TB units with no A1.6 sex counts: {missing}")

    out = {}
    for u in panel.UNITS:
        names = sorted(by_unit[u], key=lambda n: (n != u, n))  # the unit's own sheet first
        pops = [sheets[n]["pop"] for n in names]
        tot = sum(pops)
        w = sum(p * sheets[n]["women"] for p, n in zip(pops, names)) / tot
        m = sum(p * sheets[n]["men"] for p, n in zip(pops, names)) / tot
        male, female, trans = sex[u]
        f = female / (male + female + trans)
        flags = sorted(set().union(*(sheets[n]["flags"] for n in names)))
        if len(names) > 1:
            flags.append("merged:" + "+".join(names))
        out[u] = {"unit": u, "members": ";".join(names),
                  "population_weights": ";".join(f"{n}={p!r}" for n, p in zip(names, pops)),
                  "w": w, "m": m, "f": f, "male": male, "female": female,
                  "transgender": trans,
                  "p_sex_weighted": f * w + (1.0 - f) * m, "p_simple": (w + m) / 2.0,
                  "flags": ";".join(flags)}
    return out


def p_s(nfhs_rows: list[dict], sex_rows: list[dict], weighting: str) -> dict[str, float]:
    """unit -> p_u under the weighting ("sex_weighted", main; or "simple")."""
    if weighting not in WEIGHTINGS:
        raise ValueError(f"unknown weighting {weighting!r}")
    comp = components(nfhs_rows, sex_rows)
    key = "p_sex_weighted" if weighting == SEX_WEIGHTED else "p_simple"
    return {u: comp[u][key] for u in panel.UNITS}


def scaled(p: dict[str, float], factor: float) -> dict[str, float]:
    """p_u x factor for every unit (§8.11)."""
    return {u: v * factor for u, v in p.items()}
