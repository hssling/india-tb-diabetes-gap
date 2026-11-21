"""Priorities, the decomposition and the national scenario (plan §6).

- P(top-5) = tbprio.priority.p_topk({unit: draws}, 5), units alphabetical; tier =
  tbprio.priority.tier(P, False) (no "watch: rising" tier in this study).
- Decomposition (§6.3): S(d) = E1(d) / (E1(d) + E2(d)); P(S > 0.5) and P(S < 0.5) over all
  10,000 draws, draws with S = 0.5 or E1 + E2 = 0 counting in neither. "screening-led"
  P(S > 0.5) >= 0.95; "identification-led" (the plan's "detection-led", worded per §1.3)
  P(S < 0.5) >= 0.95; otherwise "mixed"; "no shortfall" when every draw has E1 + E2 = 0.
  Units below the median of T per 100,000 notified (over the units classified) are
  described as "small total shortfall" before their class.
- Scenario (§6.4): A_u(d) = N [max(c(d), c_b) max(y(d), k_b p_u) - c(d) y(d)]; national
  A(d) = sum_u A_u(d); top-5 by mean A_u (tbprio.validate.top5); share with the five
  units fixed.
"""
from __future__ import annotations

import numpy as np
from tbprio import harm
from tbprio import priority as tbp
from tbprio import validate as tbv

from .draws import DrawSet

TOP = 5
PROB = 0.95
SCREENING = "screening-led"
IDENTIFICATION = "identification-led"
MIXED = "mixed"
NO_SHORTFALL = "no shortfall"
SMALL = "small total shortfall"


def run(gap_draws: dict[str, np.ndarray]) -> dict[str, dict]:
    """unit -> {"p_top5", "tier"} over the units with a non-NA value of the gap (§6.1)."""
    ordered = {u: gap_draws[u] for u in sorted(gap_draws)}
    p = tbp.p_topk(ordered, TOP)
    return {u: {"p_top5": p[u], "tier": tbp.tier(p[u], False)} for u in ordered}


def act_now(result: dict[str, dict]) -> set[str]:
    return {u for u, r in result.items() if r["tier"] == "act now"}


def share_probs(e1: np.ndarray, e2: np.ndarray) -> tuple[float, float, bool, np.ndarray]:
    """(P(S > 0.5), P(S < 0.5), any shortfall, S with NaN where E1 + E2 = 0)."""
    t = e1 + e2
    pos = t > 0
    s = np.full(t.shape, np.nan)
    np.divide(e1, t, out=s, where=pos)
    n = t.size
    p_gt = float(np.count_nonzero(pos & (s > 0.5)) / n)
    p_lt = float(np.count_nonzero(pos & (s < 0.5)) / n)
    return p_gt, p_lt, bool(pos.any()), s


def classify(p_gt: float, p_lt: float, any_shortfall: bool) -> str:
    if not any_shortfall:
        return NO_SHORTFALL
    if p_gt >= PROB:
        return SCREENING
    if p_lt >= PROB:
        return IDENTIFICATION
    return MIXED


def decompose(e1: dict, e2: dict, N: dict[str, int]) -> list[dict]:
    """One row per unit with both E1 and E2 (§6.3)."""
    units = [u for u in sorted(e1) if u in e2]
    rows = []
    for u in units:
        p_gt, p_lt, anyp, s = share_probs(e1[u], e2[u])
        t = e1[u] + e2[u]
        r = {"unit": u}
        for name, d in (("E1", e1[u]), ("E2", e2[u]), ("total", t)):
            m, lo, hi = harm.summary(d)
            r.update({f"{name}_mean": m, f"{name}_lo": lo, f"{name}_hi": hi})
        defined = s[~np.isnan(s)]
        if defined.size:
            m, lo, hi = harm.summary(defined)
            r.update(S_mean=m, S_lo=lo, S_hi=hi)
        r.update(S_n_defined=int(defined.size), P_S_gt_half=p_gt, P_S_lt_half=p_lt,
                 **{"class": classify(p_gt, p_lt, anyp)},
                 total_per_100k=float(np.mean(t / N[u] * 100_000.0)))
        rows.append(r)
    if rows:
        med = float(np.percentile([r["total_per_100k"] for r in rows], 50,
                                  method="linear"))
        for r in rows:
            r["median_total_per_100k"] = med
            r["small_total_shortfall"] = r["total_per_100k"] < med
            r["description"] = (f"{SMALL}; {r['class']}" if r["small_total_shortfall"]
                                else r["class"])
    return rows


def scenario(ds: DrawSet, p: dict[str, float], k: float, cb: float) -> dict:
    """The national scenario (§6.4); an illustration, not a forecast."""
    units = [u for u in ds.units_c1 if u in ds.y]
    excluded = [u for u in sorted(ds.cells) if u not in units]
    A = {}
    for u in units:
        c, y, N = ds.c(u), ds.y[u], ds.cells[u].N
        A[u] = N * (np.maximum(c, cb) * np.maximum(y, k * p[u]) - c * y)
    total = np.sum(np.vstack([A[u] for u in units]), axis=0)
    means = {u: float(A[u].mean()) for u in units}
    top = tbv.top5(means, TOP)
    top_draws = np.sum(np.vstack([A[u] for u in top]), axis=0)
    ratio = np.divide(top_draws, total, out=np.full(total.shape, np.nan), where=total > 0)
    ok = ratio[~np.isnan(ratio)]
    share = sum(means[u] for u in top) / sum(means.values())
    lo, hi = np.percentile(ok, [2.5, 97.5], method="linear")
    return {"units": units, "excluded": excluded, "A": A, "means": means,
            "national": harm.summary(total), "top5": top, "share": share,
            "share_lo": float(lo), "share_hi": float(hi),
            "share_n_undefined": int(ratio.size - ok.size), "c_b": cb, "k": k}
