"""Draw sets (plan §5.3).

A draw set is a data year, a prior mode (empirical Bayes, main; or Jeffreys) and a
denominator basis. Priors: EB (a1, b1) = tbprio.shrink.beta_binomial(U, N) over the units
with non-NA C1; (a2, b2) = tbprio.shrink.beta_binomial(D, K) over the units with non-NA y;
Jeffreys (1/2, 1/2). If sum U = 0, no untested-share draws are taken and every E1 draw is
0. If beta_binomial raises otherwise, the Jeffreys prior is used with the flag
prior_fallback_jeffreys.

Order: a fresh numpy.random.default_rng(20261122) per draw set; units alphabetical; per
unit, first s = rng.beta(a1 + U, b1 + K, 10000) (if C1 is non-NA), then
y = rng.beta(a2 + D, b2 + K - D, 10000) (if y is non-NA). Coverage c = 1 - s.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
from tbprio import shrink

from . import N_DRAWS, SEED, panel

EB = "empirical_bayes"
JEFFREYS = "jeffreys"
PRIORS = (EB, JEFFREYS)
FALLBACK = "prior_fallback_jeffreys"


@dataclass
class DrawSet:
    year: int
    prior: str
    basis: str
    omit: str | None
    cells: dict[str, panel.Cell]
    units_c1: list[str]
    units_y: list[str]
    a1: float | None
    b1: float | None
    a2: float | None
    b2: float | None
    flags: list[str]
    no_screening_gap: bool
    s: dict[str, np.ndarray] = field(repr=False)
    y: dict[str, np.ndarray] = field(repr=False)

    def c(self, u: str) -> np.ndarray:
        return 1.0 - self.s[u]


def _prior(x: list[int], n: list[int], prior: str, what: str,
           flags: list[str]) -> tuple[float, float]:
    if prior == JEFFREYS:
        return shrink.JEFFREYS_BINOMIAL
    try:
        return shrink.beta_binomial(np.array(x, dtype=float), np.array(n, dtype=float))
    except ValueError:
        flags.append(f"{FALLBACK}:{what}")
        return shrink.JEFFREYS_BINOMIAL


def build(pan: dict, year: int, prior: str, basis: str = panel.BASIS_MAIN,
          omit: str | None = None, n_draws: int = N_DRAWS) -> DrawSet:
    """The draw set of one year, prior and basis over the panel ``pan`` (without ``omit``)."""
    if prior not in PRIORS:
        raise ValueError(f"unknown prior {prior!r}")
    cells = {c.unit: c for c in panel.year_cells(pan, year, omit)}
    units = sorted(cells)
    units_c1 = [u for u in units if cells[u].c1_ok]
    units_y = [u for u in units if cells[u].y_ok]
    flags: list[str] = []
    no_gap = sum(cells[u].U for u in units_c1) == 0
    if no_gap:
        a1 = b1 = None
    else:
        a1, b1 = _prior([cells[u].U for u in units_c1], [cells[u].N for u in units_c1],
                        prior, "untested_share", flags)
    a2, b2 = _prior([cells[u].D for u in units_y], [cells[u].K for u in units_y],
                    prior, "yield", flags)
    rng = np.random.default_rng(SEED)
    s: dict[str, np.ndarray] = {}
    y: dict[str, np.ndarray] = {}
    c1_set, y_set = set(units_c1), set(units_y)
    for u in units:
        c = cells[u]
        if u in c1_set and not no_gap:
            s[u] = rng.beta(a1 + c.U, b1 + c.K, size=n_draws)
        if u in y_set:
            y[u] = rng.beta(a2 + c.D, b2 + c.K - c.D, size=n_draws)
    if no_gap:
        s = {u: np.zeros(n_draws) for u in units_c1}
    return DrawSet(year, prior, basis, omit, cells, units_c1, units_y, a1, b1, a2, b2,
                   flags, no_gap, s, y)
