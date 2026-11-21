"""Headline estimates, the regression, the funnel, the grid and the label (plan §8).

H1 (§8.2): D_ut ~ quasi-binomial(K_ut, pi_ut), logit(pi) = b0 + b1 logit(p_u) + year
indicators; prior weights a = K ("tested") or 1 ("unweighted"); response y = D/K. IRLS
(numpy only): start mu = (a y + 1/2)/(a + 1), eta = logit(mu); repeat W = a mu (1 - mu),
z = eta + (y - mu)/(mu (1 - mu)), beta = (X'WX)^-1 X'Wz, eta = X beta, mu = expit(eta);
stop when max |delta beta| < 1e-10, at most 100 iterations. Non-convergence or a singular
X'WX makes the estimate undefined. Pearson phi = sum a (y - mu)^2 / (mu (1 - mu)) /
(n_obs - n_par); the Wald interval b1 +/- 1.96 sqrt(phi [(X'WX)^-1]_11) is descriptive.

Cluster bootstrap (§8.3): fresh rng(20261122); the H1 units sorted; indices
rng.integers(0, U, size=(10000, U)); each drawn unit brings all its unit-years; undefined
fits are discarded and counted; the 2.5th and 97.5th percentiles of b1.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from tbprio import district as tbd
from tbprio import validate as tbv

from . import N_DRAWS, SEED, panel
from .cascade import PROB
from .draws import DrawSet

Z = 1.96
Z998 = 3.09
TOL = 1e-10
MAX_ITER = 100
NULL = 0.0

YEAR_SETS = {"2019+2021": (2019, 2021), "2021-2023": (2021, 2022, 2023), "2023": (2023,)}
YEAR_INDICATORS = {"2019+2021": (2021,), "2021-2023": (2022, 2023), "2023": ()}
MAIN_YEAR_SET = "2019+2021"
TESTED = "tested"
UNWEIGHTED = "unweighted"
WEIGHTS = (TESTED, UNWEIGHTED)

FLAG_LOW = "identification well below what the across-unit relationship with p_u predicts"
FLAG_HIGH = "identification well above what the across-unit relationship with p_u predicts"


class Undefined(Exception):
    """The IRLS fit is undefined (non-convergence or a singular X'WX)."""


@dataclass
class GLMFit:
    beta: np.ndarray
    cov_unscaled: np.ndarray
    phi: float
    n_obs: int
    n_par: int
    iterations: int

    @property
    def b1(self) -> float:
        return float(self.beta[1])

    def wald(self) -> tuple[float, float, float]:
        se = float(np.sqrt(self.phi * self.cov_unscaled[1, 1]))
        return se, self.b1 - Z * se, self.b1 + Z * se


def logit(x):
    x = np.asarray(x, dtype=float)
    return np.log(x / (1.0 - x))


def expit(x):
    return 1.0 / (1.0 + np.exp(-np.asarray(x, dtype=float)))


def irls(X: np.ndarray, y: np.ndarray, a: np.ndarray, tol: float = TOL,
         max_iter: int = MAX_ITER) -> GLMFit:
    X = np.asarray(X, dtype=float)
    y = np.asarray(y, dtype=float)
    a = np.asarray(a, dtype=float)
    n_par = X.shape[1]
    mu = (a * y + 0.5) / (a + 1.0)
    eta = np.log(mu / (1.0 - mu))
    beta_old = None
    for it in range(1, max_iter + 1):
        v = mu * (1.0 - mu)
        w = a * v
        z = eta + (y - mu) / v
        XtW = X.T * w
        M = XtW @ X
        if np.linalg.matrix_rank(M) < n_par:
            raise Undefined("singular X'WX")
        try:
            beta = np.linalg.solve(M, XtW @ z)
        except np.linalg.LinAlgError as e:
            raise Undefined("singular X'WX") from e
        eta = X @ beta
        mu = expit(eta)
        if not (np.all(np.isfinite(beta)) and np.all((mu > 0) & (mu < 1))):
            raise Undefined("non-finite fit")
        if beta_old is not None and float(np.max(np.abs(beta - beta_old))) < tol:
            v = mu * (1.0 - mu)
            M = (X.T * (a * v)) @ X
            if np.linalg.matrix_rank(M) < n_par:
                raise Undefined("singular X'WX")
            cov = np.linalg.inv(M)
            n_obs = len(y)
            phi = (float(np.sum(a * (y - mu) ** 2 / v)) / (n_obs - n_par)
                   if n_obs > n_par else float("nan"))
            return GLMFit(beta, cov, phi, n_obs, n_par, it)
        beta_old = beta
    raise Undefined("non-convergence")


# ---- H1 data -------------------------------------------------------------------------

@dataclass
class H1Data:
    year_set: str
    weights: str
    units: list[str]          # alphabetical: the H1 units (at least one observation)
    obs_unit: list[str]
    obs_year: list[int]
    X: np.ndarray
    y: np.ndarray
    a: np.ndarray
    rows_of: list[np.ndarray]  # per unit (in ``units`` order), its observation rows


def h1_data(pan: dict, p: dict[str, float], year_set: str = MAIN_YEAR_SET,
            weights: str = TESTED, omit: str | None = None) -> H1Data:
    years = YEAR_SETS[year_set]
    ind = YEAR_INDICATORS[year_set]
    ou, oy, X, y, a = [], [], [], [], []
    for u in panel.UNITS:
        if u == omit:
            continue
        for t in years:
            c = pan[(u, t)]
            if not c.y_ok:
                continue
            ou.append(u)
            oy.append(t)
            X.append([1.0, float(logit(p[u]))] + [1.0 if t == j else 0.0 for j in ind])
            y.append(c.D / c.K)
            a.append(float(c.K) if weights == TESTED else 1.0)
    units = sorted(set(ou))
    ou_arr = np.array(ou)
    rows_of = [np.flatnonzero(ou_arr == u) for u in units]
    return H1Data(year_set, weights, units, ou, oy, np.array(X), np.array(y),
                  np.array(a), rows_of)


def fit_h1(d: H1Data) -> GLMFit:
    return irls(d.X, d.y, d.a)


def h1(pan: dict, p: dict[str, float], year_set: str = MAIN_YEAR_SET,
       weights: str = TESTED, omit: str | None = None) -> GLMFit:
    """The H1 fit (§8.2) under one specification: h1_data then fit_h1. Raises Undefined."""
    return fit_h1(h1_data(pan, p, year_set, weights, omit))


def kish(d: H1Data) -> float:
    """(sum w_u)^2 / sum w_u^2, w_u = the unit's total prior weight (§8.3)."""
    w = np.array([d.a[r].sum() for r in d.rows_of])
    return float(w.sum() ** 2 / np.sum(w ** 2))


def bootstrap(d: H1Data, n_boot: int = N_DRAWS) -> dict:
    rng = np.random.default_rng(SEED)
    U = len(d.units)
    idx = rng.integers(0, U, size=(n_boot, U))
    b1 = np.full(n_boot, np.nan)
    for i in range(n_boot):
        rows = np.concatenate([d.rows_of[j] for j in idx[i]])
        try:
            b1[i] = irls(d.X[rows], d.y[rows], d.a[rows]).b1
        except Undefined:
            pass
    ok = b1[~np.isnan(b1)]
    lo, hi = np.percentile(ok, [2.5, 97.5], method="linear")
    return {"lo": float(lo), "hi": float(hi), "n_boot": n_boot,
            "n_discarded": int(n_boot - ok.size), "draws": b1}


def grid(pan: dict, refs: dict[str, dict[str, float]]) -> list[dict]:
    """The 12 H1 grid entries (§8.8): reference x year set x weights."""
    out = []
    for ref, p in refs.items():
        for ys in YEAR_SETS:
            for w in WEIGHTS:
                d = h1_data(pan, p, ys, w)
                e = {"reference": ref, "year_set": ys, "weights": w,
                     "n_obs": len(d.y), "n_units": len(d.units)}
                try:
                    f = fit_h1(d)
                    se, lo, hi = f.wald()
                    e.update(beta1=f.b1, beta0=float(f.beta[0]), phi=f.phi, wald_se=se,
                             wald_lo=lo, wald_hi=hi, iterations=f.iterations,
                             status="estimated")
                except Undefined as ex:
                    e.update(beta1=None, status=f"undefined ({ex})")
                e["sign"] = tbv.sign(e["beta1"])
                out.append(e)
    return out


def label(interval: tuple, entries: list[dict], main_b1: float) -> tuple[str, int]:
    """(label, n_agree) by tbprio.validate.label / n_agree (§8.9)."""
    signs = [tbv.sign(e["beta1"]) for e in entries]
    ms = tbv.sign(main_b1)
    return tbv.label(interval, NULL, signs, ms), tbv.n_agree(signs, ms)


# ---- Spearman sensitivity (§8.4) -----------------------------------------------------

def spearman_pooled(pan: dict, p: dict[str, float], years=(2019, 2021),
                    omit: str | None = None) -> dict:
    units = [u for u in panel.UNITS if u != omit and all(pan[(u, t)].y_ok for t in years)]
    yp = [sum(pan[(u, t)].D for t in years) / sum(pan[(u, t)].K for t in years)
          for u in units]
    rho = tbv.spearman([p[u] for u in units], yp)
    lo, hi = tbv.fisher_ci(rho, len(units))
    return {"rho": rho, "lo": lo, "hi": hi, "n": len(units), "units": units}


# ---- funnel (§8.5) -------------------------------------------------------------------

def funnel(pan: dict, p: dict[str, float], f: GLMFit, year: int,
           indicators: tuple[int, ...], source: str) -> list[dict]:
    units = [u for u in panel.UNITS if pan[(u, year)].y_ok]
    z, rows = [], []
    for u in units:
        c = pan[(u, year)]
        eta = f.beta[0] + f.beta[1] * float(logit(p[u]))
        for j, yr in enumerate(indicators):
            if yr == year:
                eta += f.beta[2 + j]
        mu = float(expit(eta))
        e = c.K * mu
        zu = (c.D - e) / np.sqrt(c.K * mu * (1.0 - mu))
        z.append(float(zu))
        rows.append({"unit": u, "funnel_year": year, "expected_from": source,
                     "observed": c.D, "tested": c.K, "mu_hat": mu, "expected": e,
                     "z": float(zu)})
    phi_f = tbd.winsorised_phi(z)
    wf = tbd.widen(phi_f)
    l95, l998 = Z * wf, Z998 * wf
    for r in rows:
        zu = r["z"]
        if zu < -l998:
            pos, flag = "below the 99.8% limit", FLAG_LOW
        elif zu < -l95:
            pos, flag = "between the 95% and 99.8% limits (below)", ""
        elif zu > l998:
            pos, flag = "above the 99.8% limit", FLAG_HIGH
        elif zu > l95:
            pos, flag = "between the 95% and 99.8% limits (above)", ""
        else:
            pos, flag = "within the 95% limits", ""
        r.update(phi_f=phi_f, widen=wf, lower_95=-l95, upper_95=l95, lower_998=-l998,
                 upper_998=l998, position=pos, flag=flag)
    return rows


# ---- H3 and the fixed-rule counts (§5.6, §8.7) ----------------------------------------

def below_units(jeff: DrawSet, kp: dict[str, float]) -> list[str]:
    """Units with P(y(d) < k p_u) >= 0.95 ("identification below the benchmark" at k_b)."""
    return [u for u in jeff.units_y if float(np.mean(jeff.y[u] < kp[u])) >= PROB]


def fixed_rule_units(jeff: DrawSet, kp: dict[str, float]) -> list[str]:
    """Units whose 97.5th percentile of R = y(d)/(k p_u) is below 1 (the fixed rule)."""
    return [u for u in jeff.units_y
            if float(np.percentile(jeff.y[u] / kp[u], 97.5, method="linear")) < 1.0]
