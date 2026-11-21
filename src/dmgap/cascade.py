"""The TB-diabetes care cascade, R, and the linkage gap E3 (plan §5.1, §5.6).

- C1 = K/N, y = D/K, C3 = I/D, each with the Jeffreys interval (Beta(1/2 + x,
  1/2 + n - x) quantiles 0.025 and 0.975, scipy.stats.beta.ppf).
- R_k = y / (k p_u); its interval from the year's Jeffreys draw set y(d). C2 = R at k_b.
- "Likely under-detection": the 97.5th percentile of R_1(d) < 1 (k = 1.5 and 2 as a
  sensitivity, never with the phrase). "Identification below the benchmark":
  P(R_kb < 1) = share of y(d) < k_b p_u >= 0.95.
- E3 = D - I; C3 draw set per main-C3 year: fresh rng(20261122), units with non-NA C3 in
  alphabetical order, c3(d) = rng.beta(1/2 + I, 1/2 + D - I, 10000), E3(d) = D (1 - c3(d)).
  c3_b = the 75th percentile of (1/2 + I)/(1 + D); "linkage below the benchmark" when the
  share of c3(d) < c3_b is >= 0.95.
- National values: sums over the units with non-NA cells, with Wilson intervals; no
  national R.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np
from scipy.stats import beta as beta_dist

from . import N_DRAWS, SEED, benchmark, panel
from .draws import DrawSet

Z = 1.96
PROB = 0.95


def jeffreys(x: int, n: int) -> tuple[float, float]:
    lo, hi = beta_dist.ppf([0.025, 0.975], 0.5 + x, 0.5 + n - x)
    return float(lo), float(hi)


def wilson(x: int, n: int, z: float = Z) -> tuple[float, float, float]:
    """(proportion, lo, hi): the Wilson interval (§8.6)."""
    c = x / n
    centre = (x + z * z / 2.0) / (n + z * z)
    half = z * math.sqrt(x * (n - x) / n + z * z / 4.0) / (n + z * z)
    return c, centre - half, centre + half


def newcombe(c1: tuple, c2: tuple) -> tuple[float, float, float]:
    """d = c2 - c1 with Newcombe's hybrid-score interval from the two Wilson intervals
    (c, l, u) (§8.6)."""
    p1, l1, u1 = c1
    p2, l2, u2 = c2
    d = p2 - p1
    lo = d - math.sqrt((p2 - l2) ** 2 + (u1 - p1) ** 2)
    hi = d + math.sqrt((u2 - p2) ** 2 + (p1 - l1) ** 2)
    return d, lo, hi


def r_draws(ds: DrawSet, u: str, p: float, k: float) -> np.ndarray:
    return ds.y[u] / (k * p)


def r_summary(ds: DrawSet, u: str, p: float, k: float) -> tuple[float, float, float, float]:
    """(point R, lo, hi, P(R < 1)) at multiplier k from the Jeffreys draws."""
    c = ds.cells[u]
    r = r_draws(ds, u, p, k)
    lo, hi = np.percentile(r, [2.5, 97.5], method="linear")
    return (c.D / c.K) / (k * p), float(lo), float(hi), float(np.mean(r < 1.0))


def likely_under_detection(ds: DrawSet, u: str, p: float, k: float = 1.0) -> bool:
    """The fixed rule (§5.6): the 97.5th percentile of R_k(d) lies below 1."""
    return bool(np.percentile(r_draws(ds, u, p, k), 97.5, method="linear") < 1.0)


def p_below(ds: DrawSet, u: str, p: float, k: float) -> float:
    """P(R_k < 1): the share of y(d) < k p_u."""
    return float(np.mean(ds.y[u] < k * p))


def below_benchmark(ds: DrawSet, u: str, p: float, k: float) -> bool:
    return p_below(ds, u, p, k) >= PROB


@dataclass
class C3Set:
    year: int
    units: list[str]
    cells: dict[str, panel.Cell]
    c3_b: float
    c3: dict[str, np.ndarray] = field(repr=False)
    e3: dict[str, np.ndarray] = field(repr=False)

    def p_below(self, u: str) -> float:
        return float(np.mean(self.c3[u] < self.c3_b))

    def linkage_below(self, u: str) -> bool:
        return self.p_below(u) >= PROB


def c3_set(pan: dict, year: int, omit: str | None = None,
           n_draws: int = N_DRAWS) -> C3Set:
    if year not in panel.C3_MAIN_YEARS:
        raise ValueError(f"{year} has no main C3 definition (2018: linked to NCD clinic)")
    cells = {c.unit: c for c in panel.year_cells(pan, year, omit)}
    units = [u for u in sorted(cells) if cells[u].c3_ok]
    cb = benchmark.c3_b(list(cells.values()))
    rng = np.random.default_rng(SEED)
    c3, e3 = {}, {}
    for u in units:
        c = cells[u]
        c3[u] = rng.beta(0.5 + c.I, 0.5 + c.D - c.I, size=n_draws)
        e3[u] = c.D * (1.0 - c3[u])
    return C3Set(year, units, cells, cb, c3, e3)


def national(pan: dict, year: int) -> dict:
    """National C1, y and C3 (sums over the units with non-NA cells), Wilson intervals."""
    cells = panel.year_cells(pan, year)
    out: dict = {"year": year}
    for name, ok, num, den in (("C1", "c1_ok", "K", "N"), ("y", "y_ok", "D", "K"),
                               ("C3", "c3_ok", "I", "D")):
        use = [c for c in cells if getattr(c, ok)]
        x = sum(getattr(c, num) for c in use)
        n = sum(getattr(c, den) for c in use)
        v, lo, hi = wilson(x, n)
        out[name] = {"x": x, "n": n, "units": len(use), "value": v, "lo": lo, "hi": hi}
    return out


def unit_rows(pan: dict, year: int, p: dict[str, float], kb: float, jeff: DrawSet,
              c3s: C3Set | None, ks=(1.0, 1.5, 2.0)) -> list[dict]:
    """One cascade row per unit for the year (§5.1, §5.6, §10.3)."""
    if jeff.year != year:
        raise ValueError("draw set of another year")
    rows = []
    for u in panel.UNITS:
        c = pan[(u, year)]
        r: dict = {"unit": u, "year": year, "N": c.N, "K": c.K, "D": c.D, "I": c.I,
                   "p_u": p[u], "k_b": kb}
        if c.c1_ok:
            lo, hi = jeffreys(c.K, c.N)
            r.update(C1=c.K / c.N, C1_lo=lo, C1_hi=hi)
        else:
            r["C1_na"] = c.c1_reason()
        if c.y_ok:
            lo, hi = jeffreys(c.D, c.K)
            r.update(y=c.D / c.K, y_lo=lo, y_hi=hi)
            pt, rlo, rhi, pb = r_summary(jeff, u, p[u], kb)
            r.update(C2=pt, C2_lo=rlo, C2_hi=rhi, P_R_kb_below_1=pb,
                     below_benchmark=pb >= PROB)
            for k in ks:
                pt, rlo, rhi, pb = r_summary(jeff, u, p[u], k)
                tag = f"{k:g}"
                r.update({f"R_k{tag}": pt, f"R_k{tag}_lo": rlo, f"R_k{tag}_hi": rhi,
                          f"P_R_k{tag}_below_1": pb})
            r["likely_under_detection"] = likely_under_detection(jeff, u, p[u], 1.0)
            for k in ks[1:]:
                r[f"under_detection_rule_k{k:g}"] = likely_under_detection(jeff, u, p[u], k)
        else:
            r["y_na"] = c.y_reason()
        if c.c3_ok:
            lo, hi = jeffreys(c.I, c.D)
            key = "C3" if year in panel.C3_MAIN_YEARS else "C3_linked_ncd_clinic_2018"
            r.update({key: c.I / c.D, f"{key}_lo": lo, f"{key}_hi": hi})
            if c3s is not None and u in c3s.c3:
                pb = c3s.p_below(u)
                r.update(c3_b=c3s.c3_b, P_C3_below_c3b=pb, linkage_below_benchmark=pb >= PROB)
        else:
            r["C3_na"] = c.c3_reason()
        if c.c1_ok and c.y_ok:
            r["cumulative_C1C2"] = c.D / (c.N * kb * p[u])
            if c.c3_ok and year in panel.C3_MAIN_YEARS:
                r["cumulative_C1C2C3"] = c.I / (c.N * kb * p[u])
        rows.append(r)
    return rows
