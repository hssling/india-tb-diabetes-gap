"""The screening gap E1, the identification gap E2 and the total (plan §5.4-§5.5).

Observed ("point"): E1 = U k p_u; E2 = K max(0, k p_u - D/K).
Draw d: E1 = N s(d) k p_u; E2 = K max(0, k p_u - y(d)) (the floor per draw: E2 is never
negative, Review Focus 4); T = E1 + E2 for units with both non-NA.
"""
from __future__ import annotations

import numpy as np
from tbprio import harm

from . import panel
from .draws import DrawSet


def point_e1(cell: panel.Cell, p: float, k: float) -> float | None:
    return None if not cell.c1_ok else cell.U * k * p


def point_e2(cell: panel.Cell, p: float, k: float) -> float | None:
    return None if not cell.y_ok else cell.K * max(0.0, k * p - cell.D / cell.K)


def compute(pan: dict, p_s: dict[str, float], k: float) -> list[dict]:
    """The observed E1, E2 and total of every unit-year at multiplier k (None where NA)."""
    out = []
    for u in panel.UNITS:
        for t in panel.YEARS:
            c = pan[(u, t)]
            e1, e2 = point_e1(c, p_s[u], k), point_e2(c, p_s[u], k)
            out.append({"unit": u, "year": t, "E1": e1, "E2": e2,
                        "total": None if e1 is None or e2 is None else e1 + e2})
    return out


def e1_draws(ds: DrawSet, p: dict[str, float], k: float) -> dict[str, np.ndarray]:
    return {u: ds.cells[u].N * ds.s[u] * (k * p[u]) for u in ds.units_c1}


def e2_draws(ds: DrawSet, p: dict[str, float], k: float) -> dict[str, np.ndarray]:
    return {u: ds.cells[u].K * np.maximum(0.0, k * p[u] - ds.y[u]) for u in ds.units_y}


def total_draws(e1: dict, e2: dict) -> dict[str, np.ndarray]:
    return {u: e1[u] + e2[u] for u in e1 if u in e2}


def draw_gaps(ds: DrawSet, p: dict[str, float], k: float) -> dict[str, dict]:
    """{"E1": ..., "E2": ..., "total": ...}, each unit -> 10,000 draws."""
    e1, e2 = e1_draws(ds, p, k), e2_draws(ds, p, k)
    return {"E1": e1, "E2": e2, "total": total_draws(e1, e2)}


def point(gap: str, cell: panel.Cell, p: float, k: float) -> float | None:
    if gap == "E1":
        return point_e1(cell, p, k)
    if gap == "E2":
        return point_e2(cell, p, k)
    e1, e2 = point_e1(cell, p, k), point_e2(cell, p, k)
    return None if e1 is None or e2 is None else e1 + e2


def per_100k(mean: float, N: int | None) -> float | None:
    """The mean of the draws / N x 100,000 (§6.2); N is the unit-year's C1 denominator."""
    if N is None or N == 0:
        return None
    return mean / N * 100_000.0


def summarise(draws: np.ndarray) -> tuple[float, float, float]:
    return harm.summary(draws)
