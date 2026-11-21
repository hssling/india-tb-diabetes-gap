"""Benchmarks: k_b (plan §5.2), c_b (§6.4) and c3_b (§5.1).

k_b: units with non-NA y in both pool years; x_u = D sum, n_u = K sum over the pool;
(alpha, beta) = tbprio.shrink.beta_binomial(x, n) (EB) or (1/2, 1/2) (Jeffreys, shrinkage
off); posterior mean yhat_u = (alpha + x_u) / (alpha + beta + n_u); g_u = yhat_u / p_u;
k_b = numpy.percentile(g, 75 | 50 | 90, method="linear"). Computed once per specification
from posterior means; no floor.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from tbprio import shrink

from . import panel
from .draws import EB, JEFFREYS, DrawSet

PERCENTILES = {"p75": 75.0, "median": 50.0, "p90": 90.0}
POOL_MAIN = (2021, 2022)
POOL_ALT = (2019, 2021)


def pct(values, q: float) -> float:
    return float(np.percentile(np.asarray(values, dtype=float), q, method="linear"))


@dataclass
class KB:
    value: float
    percentile: str
    pool: tuple[int, ...]
    prior: str
    units: list[str]
    excluded: list[str]
    alpha: float
    beta: float
    yhat: dict[str, float]
    g: dict[str, float]


def pool_counts(pan: dict, pool=POOL_MAIN, omit: str | None = None):
    """(units, x, n, excluded) of the k_b pool (§5.2)."""
    units, excluded = [], []
    for u in panel.UNITS:
        if u == omit:
            continue
        if all(pan[(u, t)].y_ok for t in pool):
            units.append(u)
        else:
            excluded.append(u)
    x = {u: sum(pan[(u, t)].D for t in pool) for u in units}
    n = {u: sum(pan[(u, t)].K for t in pool) for u in units}
    return units, x, n, excluded


def k_b(pan: dict, p: dict[str, float], pool=POOL_MAIN, percentile: str = "p75",
        prior: str = EB, omit: str | None = None) -> KB:
    units, x, n, excluded = pool_counts(pan, pool, omit)
    if prior == EB:
        a, b = shrink.beta_binomial(np.array([x[u] for u in units], dtype=float),
                                    np.array([n[u] for u in units], dtype=float))
    elif prior == JEFFREYS:
        a, b = shrink.JEFFREYS_BINOMIAL
    else:
        raise ValueError(f"unknown prior {prior!r}")
    yhat = {u: (a + x[u]) / (a + b + n[u]) for u in units}
    g = {u: yhat[u] / p[u] for u in units}
    value = pct([g[u] for u in units], PERCENTILES[percentile])
    return KB(value, percentile, tuple(pool), prior, units, excluded, float(a), float(b),
              yhat, g)


def k_b_from_yhat(yhat: dict[str, float], p: dict[str, float],
                  percentile: str = "p75") -> float:
    """k_b from fixed posterior means and a (perturbed) p (§8.11)."""
    return pct([yhat[u] / p[u] for u in yhat], PERCENTILES[percentile])


def c_b(ds: DrawSet, percentile: str = "p75") -> float:
    """The benchmark coverage (§6.4): the percentile, over the units with non-NA C1, of the
    EB posterior-mean coverage 1 - (a1 + U)/(a1 + b1 + N), with the year's (a1, b1)."""
    if ds.prior != EB:
        raise ValueError("c_b uses the empirical-Bayes draw set")
    if ds.no_screening_gap:
        return 1.0
    cov = [1.0 - (ds.a1 + ds.cells[u].U) / (ds.a1 + ds.b1 + ds.cells[u].N)
           for u in ds.units_c1]
    return pct(cov, PERCENTILES[percentile])


def c3_b(cells: list[panel.Cell]) -> float:
    """The linkage benchmark (§5.1): the 75th percentile of (1/2 + I)/(1 + D) over the
    year's units with non-NA C3."""
    return pct([(0.5 + c.I) / (1.0 + c.D) for c in cells if c.c3_ok], 75.0)
