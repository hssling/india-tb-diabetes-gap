"""The trend in screening coverage (plan §7), through tbprio.trend.

Main: per unit, over the years with non-NA C1, tbprio.trend.fit(years, K, N) with its
defaults (empirical logit, WLS, the 2021 indicator where the unit has 2021 and an earlier
year); phi = tbprio.trend.pooled_phi over the main fits; (SE, lo, hi) =
tbprio.trend.interval(fit, phi); "falling coverage" when hi < 0.

Sensitivities (§7.3): without the 2021 indicator (main phi); dropping 2018 (phi pooled over
these fits); each §12.1 denominator basis (phi pooled over these fits).
"""
from __future__ import annotations

from tbprio import trend as tbt

from . import panel

MAIN = "main"
NO_INDICATOR = "without_2021_indicator"
DROP_2018 = "drop_2018"


def _series(pan: dict, u: str, years) -> tuple[list[int], list[int], list[int]]:
    ys, ks, ns = [], [], []
    for t in years:
        c = pan[(u, t)]
        if c.c1_ok:
            ys.append(t)
            ks.append(c.K)
            ns.append(c.N)
    return ys, ks, ns


def fits(pan: dict, years=panel.YEARS, indicator: bool | None = None) -> dict:
    """unit -> (years, Fit or the NotEstimable reason)."""
    out = {}
    for u in panel.UNITS:
        ys, ks, ns = _series(pan, u, years)
        try:
            if indicator is None:
                f = tbt.fit(ys, ks, ns)
            else:
                f = tbt.fit(ys, ks, ns, indicator=indicator)
            out[u] = (ys, f)
        except tbt.NotEstimable as e:
            out[u] = (ys, str(e))
    return out


def model_rows(model: str, fitted: dict, phi: float) -> list[dict]:
    rows = []
    for u in panel.UNITS:
        ys, f = fitted[u]
        r = {"unit": u, "model": model, "years": ";".join(str(t) for t in ys),
             "n_years": len(ys), "phi": phi}
        if isinstance(f, str):
            r["status"] = f
        else:
            se, lo, hi = tbt.interval(f, phi)
            r.update(indicator=f.indicator, slope=f.slope, se=se, lo=lo, hi=hi,
                     falling_coverage=hi < 0, status=tbt.ESTIMATED)
        rows.append(r)
    return rows


def _phi(fitted: dict) -> float:
    return tbt.pooled_phi([f for _, f in fitted.values() if not isinstance(f, str)])


def run(pan: dict, bases: dict[str, dict] | None = None) -> tuple[list[dict], dict]:
    """All trend rows and {model: phi}. ``bases``: name -> panel for the §12.1 bases."""
    main = fits(pan)
    phi_main = _phi(main)
    rows = model_rows(MAIN, main, phi_main)
    phis = {MAIN: phi_main}
    no_ind = fits(pan, indicator=False)
    rows += model_rows(NO_INDICATOR, no_ind, phi_main)
    phis[NO_INDICATOR] = phi_main
    drop = fits(pan, years=tuple(t for t in panel.YEARS if t != 2018))
    phis[DROP_2018] = _phi(drop)
    rows += model_rows(DROP_2018, drop, phis[DROP_2018])
    for name, bp in (bases or {}).items():
        f = fits(bp)
        phis[name] = _phi(f)
        rows += model_rows(name, f, phis[name])
    main_flag = {r["unit"]: r.get("falling_coverage") for r in rows if r["model"] == MAIN}
    for r in rows:
        r["falling_differs_from_main"] = r.get("falling_coverage") != main_flag[r["unit"]]
    return rows, phis


def falling(rows: list[dict]) -> dict[str, bool | None]:
    """unit -> the main falling-coverage flag (None when not estimable)."""
    return {r["unit"]: r.get("falling_coverage") for r in rows if r["model"] == MAIN}
