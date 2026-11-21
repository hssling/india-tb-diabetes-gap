"""Independent recompute of the registered results with the standard library only (analysis
plan section 10.4). Nothing of src/ is imported, nor numpy, scipy or tbprio: every formula
below is written out again from docs/analysis_plan.md.

Run as: python -I verification/check_outputs.py [--root DIR]

Inputs: data/extracted/dm_panel.csv, nfhs_dm.csv and tb_sex_2022.csv, and the committed
files of outputs/. Main specification throughout: the main denominator basis (plan 12.1),
the sex-weighted reference, k = k_b (p75, pool 2021 + 2022, empirical Bayes).

Tolerances.
- Deterministic values: relative 1e-9 (REL). The H1 slopes of the own IRLS: absolute 1e-6
  (TOL_B1); phi and the Wald SE: relative 1e-6.
- Exact Beta quantiles (Jeffreys intervals printed by scipy.stats.beta.ppf): relative 1e-7.
- Where the plan uses Monte Carlo (10,000 draws), the printed value is compared with its
  exact expectation, computed here from the regularised incomplete Beta function:
  - a mean of draws within MC_SE = 5 Monte Carlo standard errors (the standard deviation
    used is the exact posterior one, or an upper bound on it, divided by 100);
  - a share of draws P within 5 sqrt(P(1 - P)/10,000) + 0.001;
  - a 2.5th or 97.5th percentile of draws within Q_TOL = 0.15 posterior standard
    deviations of the exact quantile (about 5.5 standard errors of a sample percentile).
  A classification that rests on a Monte Carlo value (P >= 0.95; a 97.5th percentile below
  1) is "borderline" when the exact value lies within that tolerance of the threshold;
  either printed class is then accepted, and the borderline units are named.

(a) p_u (plan 4.3-4.4) for all 33 units, sex-weighted and simple, with w_u, m_u and f_u,
    against reference_prevalence.csv, and p_u in every unit row of cascade.csv.
(b) k_b (plan 5.2) for all 24 specifications of benchmark.csv (percentile x pool x
    reference x prior) with alpha, beta and the number of units; the main k_b in
    cascade.csv and in the main rows of gaps.csv.
(c) Data year 2023 (plan 5.1, 5.6, 8.7): every unit's N, K, D, C1 and y with their
    Jeffreys intervals; C2 and R at k = 1, 1.5, 2 with the draw intervals and
    P(R_k < 1); the "below the benchmark", "likely under-detection" and k = 1.5, 2 rule
    flags; H3 and the "likely under-detection" count at k = 1, with their unit lists.
(d) E1 and E2 (plan 5.3-5.5), 2023, main: the year's empirical-Bayes priors against
    benchmark.csv; every unit's point, mean and 95% interval in gaps.csv.
(e) H1 (plan 8.2, 8.4, 8.8): all 12 grid entries by this file's own IRLS (beta1, beta0,
    phi, Wald SE, n_obs, n_units, sign) against spec_curve.csv; the Kish effective
    number of clusters; the Spearman sensitivity with its Fieller interval (three rows).
(f) H2 (plan 8.6): Wilson coverage 2018 and 2022 and the Newcombe difference.
(g) The scenario (plan 6.4), 2023, main: c_b; each unit's expected A_u, the national
    expectation, the top five units and their share, against scenario.csv.
(h) The label (plan 8.9) from spec_curve.csv: signs, n_agree, n_grid and the label of H1
    (interval: the bootstrap interval printed in headline.csv); H2 and H3 carry none.
(i) Headline values equal their source rows: headline.csv H1 against the main row of
    spec_curve.csv and H1_wald_interval; H2 against H2_difference (2022 vs 2018); H3
    against H3_units and the k_b (main) 2023 count, and the cascade.csv flags; the k = 1
    count against count_fixed_rule_R97.5<1; the scenario c_b against benchmark.csv.

NOT re-derived here: the H1 bootstrap interval, the decomposition, P(top-5) and tiers, the
trend, the funnel, leave-one-out, the perturbation and the sensitivity specifications;
they are reproduced byte for byte by check_rerun.py.

Exit 1 on any failed comparison.
"""
import argparse
import csv
import math
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
YEARS = (2018, 2019, 2021, 2022, 2023)
YEAR = 2023
N_DRAWS = 10_000
REL = 1e-9
REL_Q = 1e-7
TOL_B1 = 1e-6
REL_FIT = 1e-6
MC_SE = 5.0
Q_TOL = 0.15
PROB = 0.95
Z = 1.96
FIELLER = 1.06
KS = (1.0, 1.5, 2.0)
PERCENTILES = {"p75": 75.0, "median": 50.0, "p90": 90.0}
POOLS = {"2021+2022": (2021, 2022), "2019+2021": (2019, 2021)}
MAIN_KB = ("p75", "2021+2022", "sex_weighted", "empirical_bayes")
JEFFREYS = (0.5, 0.5)
YEAR_SETS = {"2019+2021": ((2019, 2021), (2021,)),
             "2021-2023": ((2021, 2022, 2023), (2022, 2023)),
             "2023": ((2023,), ())}
MAIN_GRID = ("sex_weighted", "2019+2021", "tested")
MEASURES = {"notified": "N", "known_status": "K", "diabetic": "D", "initiated": "I"}
NATIONAL = "India"
SUPPORTED, NOT_ESTABLISHED = "supported", "not established"


# ------------------------------------------------------------------ input

def read(path: Path) -> list[dict]:
    with open(path, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def flt(s):
    return None if s is None or s.strip() in ("", "NA") else float(s)


def integer(s):
    return None if s is None or s.strip() in ("", "NA") else int(s)


def boolean(s: str) -> bool:
    if s not in ("True", "False"):
        raise ValueError(f"not a boolean: {s!r}")
    return s == "True"


def load_panel(root: Path) -> dict:
    """(unit, year) -> {"N", "K", "D", "I"} from dm_panel.csv (main basis, plan 12.1)."""
    out: dict = {}
    for r in read(root / "data" / "extracted" / "dm_panel.csv"):
        out.setdefault((r["unit"], int(r["year"])), {})[MEASURES[r["measure"]]] = \
            integer(r["value"])
    return out


def c1_ok(c) -> bool:  # plan 3.5
    return c["N"] is not None and c["K"] is not None and c["N"] > 0 and c["K"] <= c["N"]


def y_ok(c) -> bool:
    return c["K"] is not None and c["D"] is not None and c["K"] > 0 and c["D"] <= c["K"]


# ------------------------------------------------------------------ arithmetic

def close(a, b, rel=REL) -> bool:
    if a is None or b is None:
        return a is None and b is None
    return math.isclose(a, b, rel_tol=rel, abs_tol=rel * 1e-3)


def percentile(values, q: float) -> float:
    """Linear interpolation between order statistics (numpy's "linear" method)."""
    s = sorted(values)
    h = (len(s) - 1) * q / 100.0
    lo = math.floor(h)
    hi = min(lo + 1, len(s) - 1)
    return s[lo] + (s[hi] - s[lo]) * (h - lo)


def mom_beta(x: list, n: list) -> tuple[float, float]:
    """The beta-binomial method-of-moments prior (plan 5.2, 5.3: tbprio's rule, written out
    again): m = sum x / sum n; s2 the unweighted variance of x/n (divisor U - 1);
    tau2 = s2 - m(1 - m) mean(1/n); S = m(1 - m)/tau2 - 1 bounded to [1, 1e6] (1e6 when
    tau2 <= 0). Raises when U < 2 or m is 0 or 1."""
    U = len(x)
    if U < 2:
        raise ValueError("fewer than 2 units")
    m = math.fsum(x) / math.fsum(n)
    if not 0.0 < m < 1.0:
        raise ValueError(f"pooled rate {m}")
    s2 = math.fsum((xi / ni - m) ** 2 for xi, ni in zip(x, n)) / (U - 1)
    tau2 = s2 - m * (1.0 - m) * math.fsum(1.0 / ni for ni in n) / U
    S = 1e6 if tau2 <= 0 else min(max(m * (1.0 - m) / tau2 - 1.0, 1.0), 1e6)
    return m * S, (1.0 - m) * S


def prior_or_jeffreys(x, n) -> tuple[float, float]:
    try:
        return mom_beta(x, n)
    except ValueError:
        return JEFFREYS  # plan 5.3, prior_fallback_jeffreys


def _betacf(a: float, b: float, x: float) -> float:
    """Continued fraction of the incomplete Beta function (modified Lentz)."""
    tiny, eps = 1e-300, 1e-15
    qab, qap, qam = a + b, a + 1.0, a - 1.0
    c, d = 1.0, 1.0 - qab * x / qap
    d = 1.0 / (d if abs(d) > tiny else tiny)
    h = d
    for m in range(1, 1_000_000):
        m2 = 2 * m
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1.0 + aa * d
        d = 1.0 / (d if abs(d) > tiny else tiny)
        c = 1.0 + aa / c
        c = c if abs(c) > tiny else tiny
        h *= d * c
        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1.0 + aa * d
        d = 1.0 / (d if abs(d) > tiny else tiny)
        c = 1.0 + aa / c
        c = c if abs(c) > tiny else tiny
        de = d * c
        h *= de
        if abs(de - 1.0) < eps:
            return h
    raise ArithmeticError("incomplete Beta: no convergence")


def _log_front(a: float, b: float, x: float) -> float:
    return (math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b) + a * math.log(x)
            + b * math.log1p(-x))


def betainc(a: float, b: float, x: float) -> float:
    """The regularised incomplete Beta function I_x(a, b) = P(Beta(a, b) <= x)."""
    if x <= 0.0:
        return 0.0
    if x >= 1.0:
        return 1.0
    front = math.exp(_log_front(a, b, x))
    if x < (a + 1.0) / (a + b + 2.0):
        return front * _betacf(a, b, x) / a
    return 1.0 - front * _betacf(b, a, 1.0 - x) / b


def beta_mean_sd(a: float, b: float) -> tuple[float, float]:
    s = a + b
    return a / s, math.sqrt(a * b / (s * s * (s + 1.0)))


def beta_ppf(q: float, a: float, b: float) -> float:
    """The q-quantile of Beta(a, b): safeguarded Newton on betainc, from the normal
    approximation."""
    mean, sd = beta_mean_sd(a, b)
    x = min(max(mean + statistics.NormalDist().inv_cdf(q) * sd, 1e-12), 1.0 - 1e-12)
    lo, hi = 0.0, 1.0
    lbeta = math.lgamma(a) + math.lgamma(b) - math.lgamma(a + b)
    for _ in range(400):
        F = betainc(a, b, x)
        if F < q:
            lo = x
        else:
            hi = x
        dens = math.exp((a - 1.0) * math.log(x) + (b - 1.0) * math.log1p(-x) - lbeta)
        xn = x - (F - q) / dens if dens > 0 else (lo + hi) / 2.0
        if not lo < xn < hi:
            xn = (lo + hi) / 2.0
        if abs(xn - x) <= 1e-15 * x or hi - lo <= 1e-16:
            return xn
        x = xn
    raise ArithmeticError("Beta quantile: no convergence")


def jeffreys_interval(x: int, n: int) -> tuple[float, float]:
    a, b = 0.5 + x, 0.5 + n - x
    return beta_ppf(0.025, a, b), beta_ppf(0.975, a, b)


def e_max(t: float, a: float, b: float) -> float:
    """E[max(Y, t)], Y ~ Beta(a, b): t P(Y <= t) + E[Y; Y > t]."""
    return t * betainc(a, b, t) + a / (a + b) * (1.0 - betainc(a + 1.0, b, t))


def e_shortfall(t: float, a: float, b: float) -> float:
    """E[max(0, t - Y)], Y ~ Beta(a, b)."""
    return t * betainc(a, b, t) - a / (a + b) * betainc(a + 1.0, b, t)


def avg_ranks(values: list) -> list[float]:
    order = sorted(range(len(values)), key=lambda i: values[i])
    ranks = [0.0] * len(values)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and values[order[j + 1]] == values[order[i]]:
            j += 1
        for k in range(i, j + 1):
            ranks[order[k]] = (i + j) / 2 + 1
        i = j + 1
    return ranks


def pearson(a: list, b: list):
    n = len(a)
    if n < 2:
        return None
    ma, mb = sum(a) / n, sum(b) / n
    sab = sum((x - ma) * (y - mb) for x, y in zip(a, b))
    saa = sum((x - ma) ** 2 for x in a)
    sbb = sum((y - mb) ** 2 for y in b)
    if saa <= 0 or sbb <= 0:
        return None
    return sab / math.sqrt(saa * sbb)


def fieller(rho, n):
    if rho is None or n <= 3:
        return None, None
    if abs(rho) >= 1:
        return rho, rho
    z, se = math.atanh(rho), math.sqrt(FIELLER / (n - 3))
    return math.tanh(z - Z * se), math.tanh(z + Z * se)


def sign(v):
    if v is None or v != v:
        return None
    return (v > 0) - (v < 0)


def label(lo, hi, signs, main_sign) -> tuple[str, int]:
    """Plan 8.9: "supported" only if the interval excludes 0 and >= 80% of the entries
    have the main estimate's strict sign."""
    agree = sum(1 for s in signs if main_sign in (1, -1) and s == main_sign)
    if lo is None or hi is None or not ((lo > 0 and hi > 0) or (lo < 0 and hi < 0)):
        return NOT_ESTABLISHED, agree
    if main_sign not in (1, -1):
        return NOT_ESTABLISHED, agree
    return (SUPPORTED if agree >= 0.8 * len(signs) else NOT_ESTABLISHED), agree


def wilson(x: int, n: int) -> tuple[float, float, float]:
    centre = (x + Z * Z / 2.0) / (n + Z * Z)
    half = Z * math.sqrt(x * (n - x) / n + Z * Z / 4.0) / (n + Z * Z)
    return x / n, centre - half, centre + half


def newcombe(w1, w2) -> tuple[float, float, float]:
    (p1, l1, u1), (p2, l2, u2) = w1, w2
    d = p2 - p1
    return (d, d - math.sqrt((p2 - l2) ** 2 + (u1 - p1) ** 2),
            d + math.sqrt((u2 - p2) ** 2 + (p1 - l1) ** 2))


# ------------------------------------------------------------------ the IRLS of plan 8.2

def solve(M: list[list[float]], r: list[float]) -> list[float]:
    """Gaussian elimination with partial pivoting; raises on a singular matrix."""
    n = len(r)
    A = [row[:] + [r[i]] for i, row in enumerate(M)]
    scale = max(abs(v) for row in M for v in row) or 1.0
    for c in range(n):
        p = max(range(c, n), key=lambda i: abs(A[i][c]))
        if abs(A[p][c]) <= 1e-13 * scale:
            raise ArithmeticError("singular X'WX")
        A[c], A[p] = A[p], A[c]
        for i in range(c + 1, n):
            f = A[i][c] / A[c][c]
            for j in range(c, n + 1):
                A[i][j] -= f * A[c][j]
    x = [0.0] * n
    for i in range(n - 1, -1, -1):
        x[i] = (A[i][n] - sum(A[i][j] * x[j] for j in range(i + 1, n))) / A[i][i]
    return x


def xtwx(X, w):
    p = len(X[0])
    return [[math.fsum(w[k] * X[k][i] * X[k][j] for k in range(len(X))) for j in range(p)]
            for i in range(p)]


def irls(X: list, y: list, a: list) -> dict:
    """Plan 8.2: start mu = (a y + 1/2)/(a + 1); W = a mu(1 - mu); z = eta + (y - mu)/
    (mu(1 - mu)); beta = (X'WX)^-1 X'Wz; stop when max |delta beta| < 1e-10 (at most 100
    iterations). Pearson phi; Wald SE of beta1 = sqrt(phi [(X'WX)^-1]_11)."""
    n, p = len(y), len(X[0])
    mu = [(ai * yi + 0.5) / (ai + 1.0) for ai, yi in zip(a, y)]
    eta = [math.log(m / (1.0 - m)) for m in mu]
    old = None
    for it in range(1, 101):
        v = [m * (1.0 - m) for m in mu]
        w = [ai * vi for ai, vi in zip(a, v)]
        z = [e + (yi - m) / vi for e, yi, m, vi in zip(eta, y, mu, v)]
        r = [math.fsum(w[k] * X[k][i] * z[k] for k in range(n)) for i in range(p)]
        beta = solve(xtwx(X, w), r)
        eta = [math.fsum(xi * bi for xi, bi in zip(X[k], beta)) for k in range(n)]
        mu = [1.0 / (1.0 + math.exp(-e)) for e in eta]
        if old is not None and max(abs(b - o) for b, o in zip(beta, old)) < 1e-10:
            v = [m * (1.0 - m) for m in mu]
            M = xtwx(X, [ai * vi for ai, vi in zip(a, v)])
            e1 = [1.0 if i == 1 else 0.0 for i in range(p)]
            cov11 = solve(M, e1)[1]
            phi = math.fsum(ai * (yi - m) ** 2 / vi
                            for ai, yi, m, vi in zip(a, y, mu, v)) / (n - p)
            return {"beta": beta, "phi": phi, "se": math.sqrt(phi * cov11), "iterations": it}
        old = beta
    raise ArithmeticError("non-convergence")


def h1_fit(panel: dict, units: list, p: dict, year_set: str, weights: str) -> dict:
    years, ind = YEAR_SETS[year_set]
    X, y, a, obs_units = [], [], [], []
    for u in units:
        for t in years:
            c = panel[(u, t)]
            if not y_ok(c):
                continue
            X.append([1.0, math.log(p[u] / (1.0 - p[u]))] + [float(t == j) for j in ind])
            y.append(c["D"] / c["K"])
            a.append(float(c["K"]) if weights == "tested" else 1.0)
            obs_units.append(u)
    fit = irls(X, y, a)
    w: dict = {}
    for u, ai in zip(obs_units, a):
        w[u] = w.get(u, 0.0) + ai
    fit.update(n_obs=len(y), n_units=len(w),
               kish=math.fsum(w.values()) ** 2 / math.fsum(v * v for v in w.values()))
    return fit


# ------------------------------------------------------------------ the recompute

def reference(root: Path, units: list) -> dict:
    """Plan 4.3-4.4: unit -> {w, m, f, sex_weighted, simple}."""
    sheets: dict = {}
    for r in read(root / "data" / "extracted" / "nfhs_dm.csv"):
        if r["unit"] == NATIONAL:
            continue
        target = next((f.split(":", 1)[1] for f in r["flag"].split(";")
                       if f.startswith("merge_into:")), r["unit"])
        s = sheets.setdefault(r["unit"], {"target": target, "pop": float(r["population"])})
        s[r["sex"]] = float(r["prevalence_pct"]) / 100.0
    sex: dict = {}
    for r in read(root / "data" / "extracted" / "tb_sex_2022.csv"):
        if r["unit"] == "":
            continue
        acc = sex.setdefault(r["unit"], [0, 0, 0])
        for i, col in enumerate(("male", "female", "transgender")):
            acc[i] += int(r[col])
    out = {}
    for u in units:
        names = sorted((n for n, s in sheets.items() if s["target"] == u),
                       key=lambda n: (n != u, n))
        if not names:
            raise ValueError(f"no NFHS-5 sheet for {u}")
        tot = sum(sheets[n]["pop"] for n in names)
        w = sum(sheets[n]["pop"] * sheets[n]["women"] for n in names) / tot
        m = sum(sheets[n]["pop"] * sheets[n]["men"] for n in names) / tot
        male, female, trans = sex[u]
        f = female / (male + female + trans)
        out[u] = {"w": w, "m": m, "f": f, "sex_weighted": f * w + (1.0 - f) * m,
                  "simple": (w + m) / 2.0}
    return out


def k_b(panel: dict, units: list, p: dict, pool: tuple, perc: str, prior: str) -> dict:
    """Plan 5.2."""
    pu = [u for u in units if all(y_ok(panel[(u, t)]) for t in pool)]
    x = [sum(panel[(u, t)]["D"] for t in pool) for u in pu]
    n = [sum(panel[(u, t)]["K"] for t in pool) for u in pu]
    a, b = mom_beta(x, n) if prior == "empirical_bayes" else JEFFREYS
    g = {u: (a + xi) / (a + b + ni) / p[u] for u, xi, ni in zip(pu, x, n)}
    return {"value": percentile(g.values(), PERCENTILES[perc]), "alpha": a, "beta": b,
            "n_units": len(pu), "g": g}


class Checker:
    def __init__(self, root: Path):
        self.root = root
        self.bad: list[str] = []
        self.ok: list[str] = []
        out = root / "outputs"
        self.files = {name: read(out / f"{name}.csv") for name in (
            "reference_prevalence", "benchmark", "cascade", "gaps", "spec_curve",
            "headline", "headline_sensitivity", "scenario")}
        self.panel = load_panel(root)
        self.units = sorted({u for u, _ in self.panel})
        self.ref = reference(root, self.units)
        self.p = {u: self.ref[u]["sex_weighted"] for u in self.units}

    # -- helpers ---------------------------------------------------------------------

    def eq(self, what: str, printed, expected, rel=REL) -> bool:
        if isinstance(printed, str):
            printed = flt(printed)
        if close(printed, expected, rel):
            return True
        self.bad.append(f"{what}: printed {printed!r} but recomputed {expected!r}")
        return False

    def near(self, what: str, printed, expected: float, tol: float) -> bool:
        if isinstance(printed, str):
            printed = flt(printed)
        if printed is not None and abs(printed - expected) <= tol:
            return True
        self.bad.append(f"{what}: printed {printed!r} but the exact expectation is "
                        f"{expected!r} (tolerance {tol:.3g})")
        return False

    def same(self, what: str, printed, expected) -> bool:
        if printed == expected:
            return True
        self.bad.append(f"{what}: printed {printed!r} but expected {expected!r}")
        return False

    def rows(self, name: str, **match) -> list[dict]:
        return [r for r in self.files[name] if all(r.get(k) == v for k, v in match.items())]

    def one(self, name: str, **match) -> dict:
        hits = self.rows(name, **match)
        if len(hits) != 1:
            raise ValueError(f"{name}.csv: {len(hits)} rows match {match}")
        return hits[0]

    # -- (a) p_u ---------------------------------------------------------------------

    def check_reference(self):
        n0 = len(self.bad)
        printed = {r["unit"]: r for r in self.files["reference_prevalence"]}
        self.same("(a) reference_prevalence units", sorted(printed), self.units)
        for u in self.units:
            r = printed.get(u)
            if r is None:
                continue
            for col, key in (("w", "w"), ("m", "m"), ("f", "f"),
                             ("p_sex_weighted", "sex_weighted"), ("p_simple", "simple")):
                self.eq(f"(a) {u} {col}", r[col], self.ref[u][key])
        n_cas = 0
        for r in self.files["cascade"]:
            if r["unit"] in self.p:
                n_cas += 1
                self.eq(f"(a) cascade {r['spec']} {r['unit']} {r['year']} p_u", r["p_u"],
                        self.p[r["unit"]])
        if len(self.bad) == n0:
            self.ok.append(f"(a) p_u: {len(self.units)} units (sex-weighted and simple, with "
                           f"w, m, f) match reference_prevalence.csv and {n_cas} cascade rows")

    # -- (b) k_b ---------------------------------------------------------------------

    def check_kb(self):
        n0 = len(self.bad)
        refs = {"sex_weighted": self.p,
                "simple": {u: self.ref[u]["simple"] for u in self.units}}
        rows = self.rows("benchmark", kind="k_b")
        keys = {(r["percentile"], r["pool"], r["reference"], r["prior"]) for r in rows}
        expected = {(pc, pl, rf, pr) for pc in PERCENTILES for pl in POOLS for rf in refs
                    for pr in ("empirical_bayes", "jeffreys")}
        self.same("(b) benchmark.csv k_b specifications", sorted(keys), sorted(expected))
        self.kb = None
        for r in rows:
            key = (r["percentile"], r["pool"], r["reference"], r["prior"])
            kb = k_b(self.panel, self.units, refs[r["reference"]], POOLS[r["pool"]],
                     r["percentile"], r["prior"])
            what = f"(b) k_b {' '.join(key)}"
            self.eq(what, r["value"], kb["value"])
            self.eq(f"{what} alpha", r["alpha"], kb["alpha"])
            self.eq(f"{what} beta", r["beta"], kb["beta"])
            self.same(f"{what} n_units", integer(r["n_units"]), kb["n_units"])
            self.same(f"{what} below_1", r["below_1"], str(kb["value"] < 1.0))
            self.same(f"{what} is_main", r["is_main"], str(key == MAIN_KB))
            if key == MAIN_KB:
                self.kb, self.kb_g = kb["value"], kb["g"]
        if self.kb is None:
            raise ValueError("benchmark.csv has no main k_b row")
        for r in self.files["cascade"]:
            if r["unit"] in self.p:
                self.eq(f"(b) cascade {r['spec']} {r['unit']} {r['year']} k_b", r["k_b"],
                        self.kb)
        for r in self.rows("gaps", spec="main"):
            if r["gap"] in ("E1", "E2"):
                self.eq(f"(b) gaps main {r['unit']} {r['year']} {r['gap']} k", r["k"],
                        self.kb)
        if len(self.bad) == n0:
            self.ok.append(f"(b) k_b: {len(rows)} specifications match benchmark.csv; main "
                           f"k_b = {self.kb!r} in cascade.csv and gaps.csv")

    # -- (c) the 2023 cascade, R, H3 and the k = 1 count -------------------------------

    def check_cascade(self):
        n0 = len(self.bad)
        self.h3, self.h3_border, self.lud, self.lud_border = [], [], [], []
        units_y = []
        for u in self.units:
            c = self.panel[(u, YEAR)]
            r = self.one("cascade", spec="main", unit=u, year=str(YEAR))
            w = f"(c) {u} {YEAR}"
            for m in ("N", "K", "D"):
                self.same(f"{w} {m}", integer(r[m]), c[m])
            if c1_ok(c):
                self.eq(f"{w} C1", r["C1"], c["K"] / c["N"])
                lo, hi = jeffreys_interval(c["K"], c["N"])
                self.eq(f"{w} C1_lo", r["C1_lo"], lo, REL_Q)
                self.eq(f"{w} C1_hi", r["C1_hi"], hi, REL_Q)
            else:
                self.same(f"{w} C1 NA", r["C1"], "")
            if not y_ok(c):
                self.same(f"{w} y NA", r["y"], "")
                continue
            units_y.append(u)
            y = c["D"] / c["K"]
            a, b = 0.5 + c["D"], 0.5 + c["K"] - c["D"]
            q_lo, q_hi = jeffreys_interval(c["D"], c["K"])
            _, sd = beta_mean_sd(a, b)
            self.eq(f"{w} y", r["y"], y)
            self.eq(f"{w} y_lo", r["y_lo"], q_lo, REL_Q)
            self.eq(f"{w} y_hi", r["y_hi"], q_hi, REL_Q)
            for k, col in [(self.kb, "C2")] + [(k, f"R_k{k:g}") for k in KS]:
                kp = k * self.p[u]
                self.eq(f"{w} {col}", r[col], y / kp)
                self.near(f"{w} {col}_lo", r[f"{col}_lo"], q_lo / kp, Q_TOL * sd / kp)
                self.near(f"{w} {col}_hi", r[f"{col}_hi"], q_hi / kp, Q_TOL * sd / kp)
                P = betainc(a, b, kp)
                tol = MC_SE * math.sqrt(P * (1.0 - P) / N_DRAWS) + 0.001
                pcol = "P_R_kb_below_1" if col == "C2" else f"P_R_k{k:g}_below_1"
                self.near(f"{w} {pcol}", r[pcol], P, tol)
                if col == "C2":  # "identification below the benchmark" (plan 5.6)
                    firm = abs(P - PROB) > tol
                    if firm:
                        self.same(f"{w} below_benchmark", r["below_benchmark"], str(P >= PROB))
                    else:
                        self.h3_border.append(u)
                    if P >= PROB and firm:
                        self.h3.append(u)
                # the fixed rule: the 97.5th percentile of R_k below 1
                firm = abs(q_hi - kp) > Q_TOL * sd
                flag = "likely_under_detection" if k == 1.0 else (
                    f"under_detection_rule_k{k:g}" if col != "C2" else None)
                if flag is None:
                    continue
                if firm:
                    self.same(f"{w} {flag}", r[flag], str(q_hi < kp))
                if k == 1.0:
                    if not firm:
                        self.lud_border.append(u)
                    elif q_hi < kp:
                        self.lud.append(u)
        self.units_y = units_y
        self._count_tie("H3 (identification below the benchmark)", self.h3, self.h3_border,
                        "below_benchmark", "count_P(R<1)>=0.95", "k_b (main)")
        self._count_tie("likely under-detection at k = 1", self.lud, self.lud_border,
                        "likely_under_detection", "count_fixed_rule_R97.5<1", "k=1")
        if len(self.bad) == n0:
            note = ""
            if self.h3_border or self.lud_border:
                note = (f"; borderline (either class accepted): H3 {self.h3_border or 'none'}, "
                        f"k = 1 {self.lud_border or 'none'}")
            self.ok.append(f"(c) {YEAR}: C1, y, C2 and R at k = 1, 1.5, 2 with intervals and "
                           f"P(R < 1) for {len(units_y)} units; H3 = {len(self.h3)}, likely "
                           f"under-detection at k = 1 = {len(self.lud)}{note}")

    def _count_tie(self, name, firm, border, col, estimate, spec):
        printed = [r["unit"] for r in self.rows("cascade", spec="main", year=str(YEAR))
                   if r.get(col) == "True"]
        s = self.one("headline_sensitivity", estimate=estimate, spec=spec, year=str(YEAR))
        listed = s["units"].split(";") if s["units"] else []
        self.same(f"(c) {name}: {estimate} {spec} units vs cascade.csv flags", listed,
                  printed)
        self.same(f"(c) {name}: {estimate} {spec} value vs its units", integer(s["value"]),
                  len(listed))
        self.same(f"(c) {name}: n assessed", integer(s["n"]), len(self.units_y))
        if not (set(firm) <= set(listed) <= set(firm) | set(border)):
            self.bad.append(f"(c) {name}: printed {len(listed)} units {listed} but recomputed "
                            f"{len(firm)} {firm} (borderline {border})")

    # -- (d) E1 and E2, 2023 ---------------------------------------------------------

    def check_gaps(self):
        n0 = len(self.bad)
        cs = [self.panel[(u, YEAR)] for u in self.units]
        c1u = [u for u, c in zip(self.units, cs) if c1_ok(c)]
        yu = [u for u, c in zip(self.units, cs) if y_ok(c)]
        P = {u: self.panel[(u, YEAR)] for u in self.units}
        a1, b1 = prior_or_jeffreys([P[u]["N"] - P[u]["K"] for u in c1u],
                                   [P[u]["N"] for u in c1u])
        a2, b2 = prior_or_jeffreys([P[u]["D"] for u in yu], [P[u]["K"] for u in yu])
        self.priors = (a1, b1, a2, b2, c1u, yu)
        r = self.one("benchmark", kind="draw_set_prior", prior="empirical_bayes", basis="main",
                     year=str(YEAR))
        for col, v in (("a1", a1), ("b1", b1), ("a2", a2), ("b2", b2)):
            self.eq(f"(d) {YEAR} empirical-Bayes prior {col}", r[col], v)
        n = 0
        for u in c1u:
            c = P[u]
            kp = self.kb * self.p[u]
            g = self.one("gaps", unit=u, year=str(YEAR), gap="E1", spec="main")
            sa, sb = a1 + c["N"] - c["K"], b1 + c["K"]
            mean, sd = beta_mean_sd(sa, sb)
            self.eq(f"(d) {u} E1 point", g["point"], (c["N"] - c["K"]) * kp)
            self.near(f"(d) {u} E1 mean", g["mean"], c["N"] * kp * mean,
                      MC_SE * c["N"] * kp * sd / math.sqrt(N_DRAWS) + 1e-9)
            for col, q in (("lo", 0.025), ("hi", 0.975)):
                self.near(f"(d) {u} E1 {col}", g[col], c["N"] * kp * beta_ppf(q, sa, sb),
                          Q_TOL * c["N"] * kp * sd)
            n += 1
        for u in yu:
            c = P[u]
            kp = self.kb * self.p[u]
            g = self.one("gaps", unit=u, year=str(YEAR), gap="E2", spec="main")
            ya, yb = a2 + c["D"], b2 + c["K"] - c["D"]
            _, sd = beta_mean_sd(ya, yb)
            self.eq(f"(d) {u} E2 point", g["point"], c["K"] * max(0.0, kp - c["D"] / c["K"]))
            self.near(f"(d) {u} E2 mean", g["mean"], c["K"] * e_shortfall(kp, ya, yb),
                      MC_SE * c["K"] * sd / math.sqrt(N_DRAWS) + 1e-9)
            for col, q in (("lo", 0.975), ("hi", 0.025)):  # E2 falls as y rises
                self.near(f"(d) {u} E2 {col}", g[col],
                          c["K"] * max(0.0, kp - beta_ppf(q, ya, yb)), Q_TOL * c["K"] * sd)
            n += 1
        if len(self.bad) == n0:
            self.ok.append(f"(d) E1 and E2 {YEAR}, main: the priors and {n} unit gaps (point, "
                           f"mean, interval) match gaps.csv")

    # -- (e) H1 ------------------------------------------------------------------------

    def check_h1(self):
        n0 = len(self.bad)
        refs = {"sex_weighted": self.p,
                "simple": {u: self.ref[u]["simple"] for u in self.units}}
        rows = self.files["spec_curve"]
        self.fits = {}
        keys = []
        for r in rows:
            key = (r["reference"], r["year_set"], r["weights"])
            keys.append(key)
            w = f"(e) spec_curve {' '.join(key)}"
            try:
                f = h1_fit(self.panel, self.units, refs[key[0]], key[1], key[2])
            except ArithmeticError:
                self.same(f"{w} status", r["status"][:9], "undefined")
                self.fits[key] = None
                continue
            self.fits[key] = f
            self.near(f"{w} beta1", r["beta1"], f["beta"][1], TOL_B1)
            self.near(f"{w} beta0", r["beta0"], f["beta"][0], TOL_B1)
            self.eq(f"{w} phi", r["phi"], f["phi"], REL_FIT)
            self.eq(f"{w} wald_se", r["wald_se"], f["se"], REL_FIT)
            self.same(f"{w} n_obs", integer(r["n_obs"]), f["n_obs"])
            self.same(f"{w} n_units", integer(r["n_units"]), f["n_units"])
            self.same(f"{w} sign", integer(r["sign"]), sign(f["beta"][1]))
            self.same(f"{w} is_main", r["is_main"], str(key == MAIN_GRID))
        expected = [(rf, ys, wt) for rf in refs for ys in YEAR_SETS
                    for wt in ("tested", "unweighted")]
        self.same("(e) spec_curve.csv entries", sorted(keys), sorted(expected))
        main = self.fits.get(MAIN_GRID)
        if main is None:
            raise ValueError("the main H1 fit is undefined")
        self.b1 = main["beta"][1]
        kish = self.one("headline_sensitivity", estimate="H1_kish_effective_clusters")
        self.eq("(e) H1 Kish effective clusters", kish["value"], main["kish"])
        self.eq("(e) H1 Pearson phi", self.one("headline_sensitivity",
                                                estimate="H1_pearson_phi")["value"],
                main["phi"], REL_FIT)
        self.same("(e) H1_n_obs", integer(self.one("headline_sensitivity",
                                                   estimate="H1_n_obs")["value"]),
                  main["n_obs"])
        for name, ref, years in (("sex_weighted 2019+2021", "sex_weighted", (2019, 2021)),
                                 ("simple 2019+2021", "simple", (2019, 2021)),
                                 ("sex_weighted 2021+2022 (fixed H1 years)", "sex_weighted",
                                  (2021, 2022))):
            us = [u for u in self.units if all(y_ok(self.panel[(u, t)]) for t in years)]
            yp = [sum(self.panel[(u, t)]["D"] for t in years)
                  / sum(self.panel[(u, t)]["K"] for t in years) for u in us]
            rho = pearson(avg_ranks([refs[ref][u] for u in us]), avg_ranks(yp))
            lo, hi = fieller(rho, len(us))
            s = self.one("headline_sensitivity", estimate="H1_spearman_fieller", spec=name)
            for col, v in (("value", rho), ("lo", lo), ("hi", hi)):
                self.eq(f"(e) Spearman {name} {col}", s[col], v)
            self.same(f"(e) Spearman {name} n", integer(s["n"]), len(us))
        if len(self.bad) == n0:
            self.ok.append(f"(e) H1: the own IRLS reproduces all {len(rows)} grid entries "
                           f"(main beta1 = {self.b1!r}), phi, the Wald SE and Kish; the "
                           f"Spearman rho and Fieller intervals (3 rows) match")

    # -- (f) H2 ------------------------------------------------------------------------

    def check_h2(self):
        n0 = len(self.bad)
        w = {}
        for t in (2018, 2022):
            cs = [self.panel[(u, t)] for u in self.units if c1_ok(self.panel[(u, t)])]
            w[t] = wilson(sum(c["K"] for c in cs), sum(c["N"] for c in cs))
            w[t] = (*w[t], len(cs))
            s = self.one("headline_sensitivity", estimate="H2_national_coverage", spec="main",
                         year=str(t))
            for col, v in zip(("value", "lo", "hi"), w[t]):
                self.eq(f"(f) national coverage {t} {col}", s[col], v)
        d = newcombe(w[2018][:3], w[2022][:3])
        h = self.one("headline", estimate="H2")
        for col, v in zip(("value", "lo", "hi"), d):
            self.eq(f"(f) headline H2 {col}", h[col], v)
        self.same("(f) headline H2 n", h["n"], f"2018:{w[2018][3]};2022:{w[2022][3]}")
        self.h2 = d
        if len(self.bad) == n0:
            self.ok.append(f"(f) H2: coverage 2018 {w[2018][0]:.4f}, 2022 {w[2022][0]:.4f}; "
                           f"difference {d[0]!r} with its Newcombe interval")

    # -- (g) the scenario --------------------------------------------------------------

    def check_scenario(self):
        n0 = len(self.bad)
        a1, b1, a2, b2, c1u, yu = self.priors
        P = {u: self.panel[(u, YEAR)] for u in self.units}
        cov = [1.0 - (a1 + P[u]["N"] - P[u]["K"]) / (a1 + b1 + P[u]["N"]) for u in c1u]
        cb = percentile(cov, PERCENTILES["p75"])
        self.eq("(g) c_b (benchmark.csv, p75, main, 2023)",
                self.one("benchmark", kind="c_b", percentile="p75", basis="main",
                         year=str(YEAR))["value"], cb)
        units = [u for u in c1u if u in yu]
        EA, var = {}, {}
        for u in units:
            c = P[u]
            ca, cbeta = b1 + c["K"], a1 + c["N"] - c["K"]       # coverage c = 1 - s
            ya, yb = a2 + c["D"], b2 + c["K"] - c["D"]
            mc, sc = beta_mean_sd(ca, cbeta)
            my, sy = beta_mean_sd(ya, yb)
            t = self.kb * self.p[u]
            EA[u] = c["N"] * (e_max(cb, ca, cbeta) * e_max(t, ya, yb) - mc * my)
            var[u] = (c["N"] ** 2) * (sc * sc + sy * sy)  # an upper bound (Efron-Stein)
        rows = self.rows("scenario", spec="main")
        nat = next(r for r in rows if r["row"] == "national")
        self.eq("(g) scenario c_b", nat["c_b"], cb)
        self.eq("(g) scenario k", nat["k"], self.kb)
        total = math.fsum(EA.values())
        tol_nat = MC_SE * math.sqrt(math.fsum(var.values()) / N_DRAWS) + 1e-6
        self.near("(g) national A mean", nat["mean"], total, tol_nat)
        self.same("(g) national n_units", integer(nat["n_units"]), len(units))
        for r in rows:
            if r["row"] == "unit":
                u = r["unit"]
                if u not in EA:
                    self.bad.append(f"(g) scenario unit {u} is not a scenario unit")
                    continue
                self.near(f"(g) {u} A mean", r["mean"], EA[u],
                          MC_SE * math.sqrt(var[u] / N_DRAWS) + 1e-6)
        order = sorted(EA, key=lambda u: (-EA[u], u))
        top = order[:5]
        printed_top = nat["top5"].split(";")
        gap = EA[order[4]] - EA[order[5]] if len(order) > 5 else math.inf
        tie_tol = 2 * MC_SE * math.sqrt((var[order[4]] + var[order[5]]) / N_DRAWS) \
            if len(order) > 5 else 0.0
        if gap > tie_tol:
            self.same("(g) top-5 units", printed_top, top)
        tops = math.fsum(EA[u] for u in printed_top if u in EA)
        share = tops / total
        tol_top = MC_SE * math.sqrt(math.fsum(var[u] for u in printed_top if u in var)
                                    / N_DRAWS)
        sh = next(r for r in rows if r["row"] == "top5_share")
        self.near("(g) top-5 share", sh["mean"], share, (tol_top + share * tol_nat) / total)
        if len(self.bad) == n0:
            self.ok.append(f"(g) scenario {YEAR}: c_b {cb:.4f}; national expectation "
                           f"{total:.1f} (printed {float(nat['mean']):.1f}); top five "
                           f"{';'.join(top)}, share {share:.4f}")

    # -- (h) the label and (i) the source rows -----------------------------------------

    def check_label_and_ties(self):
        n0 = len(self.bad)
        sc = self.files["spec_curve"]
        signs = [integer(r["sign"]) if r["status"] == "estimated" else None for r in sc]
        main = next(r for r in sc if r["is_main"] == "True")
        ms = integer(main["sign"])
        for r, s in zip(sc, signs):
            self.same(f"(h) spec_curve {r['reference']} {r['year_set']} {r['weights']} "
                      f"agrees_with_main", r["agrees_with_main"],
                      str(s is not None and s == ms and ms in (1, -1)))
        h1 = self.one("headline", estimate="H1")
        lab, agree = label(flt(h1["lo"]), flt(h1["hi"]), signs, ms)
        self.same("(h) headline H1 label", h1["label"], lab)
        self.same("(h) headline H1 n_agree", integer(h1["n_agree"]), agree)
        self.same("(h) headline H1 n_grid", integer(h1["n_grid"]), len(sc))
        self.same("(h) headline H1 null", flt(h1["null"]), 0.0)
        own = [sign(f["beta"][1]) if f else None for f in self.fits.values()]
        self.same("(h) label from the own IRLS signs", label(flt(h1["lo"]), flt(h1["hi"]),
                                                             own, sign(self.b1))[0], lab)
        for est in ("H2", "H3"):
            r = self.one("headline", estimate=est)
            self.same(f"(h) headline {est} label (descriptive: none)", r["label"], "")
        # (i) source rows
        self.same("(i) headline H1 value vs spec_curve main beta1", h1["value"],
                  main["beta1"])
        self.same("(i) headline H1 value vs H1_wald_interval",
                  h1["value"], self.one("headline_sensitivity",
                                        estimate="H1_wald_interval")["value"])
        self.near("(i) headline H1 value vs the own IRLS", h1["value"], self.b1, TOL_B1)
        self.same("(i) headline H1 n vs spec_curve main n_units", h1["n"], main["n_units"])
        self.same("(i) H1_one_inside_interval",
                  self.one("headline_sensitivity", estimate="H1_one_inside_interval")["value"],
                  str(flt(h1["lo"]) <= 1.0 <= flt(h1["hi"])))
        h2 = self.one("headline", estimate="H2")
        d = self.one("headline_sensitivity", estimate="H2_difference", spec="main",
                     year="2022 vs 2018")
        for col in ("value", "lo", "hi"):
            self.same(f"(i) headline H2 {col} vs H2_difference main 2022 vs 2018", h2[col],
                      d[col])
        h3 = self.one("headline", estimate="H3")
        u3 = self.one("headline_sensitivity", estimate="H3_units")
        c3 = self.one("headline_sensitivity", estimate="count_P(R<1)>=0.95", spec="k_b (main)",
                      year=str(YEAR))
        for src, r in (("H3_units", u3), ("count_P(R<1)>=0.95 k_b (main)", c3)):
            self.same(f"(i) headline H3 value vs {src}", h3["value"], r["value"])
            self.same(f"(i) headline H3 n vs {src}", h3["n"], r["n"])
        self.same("(i) H3_units units vs the k_b (main) count", u3["units"], c3["units"])
        if not len(self.h3) <= integer(h3["value"]) <= len(self.h3) + len(self.h3_border):
            self.bad.append(f"(i) headline H3: printed {h3['value']} but recomputed "
                            f"{len(self.h3)} (borderline {self.h3_border})")
        if len(self.bad) == n0:
            self.ok.append(f"(h) label: H1 {h1['label']!r} ({agree}/{len(sc)} entries agree; "
                           f"interval {h1['lo']}-{h1['hi']}), H2 and H3 none; (i) headline "
                           f"H1, H2 and H3 equal their source rows")

    def run(self):
        steps = (self.check_reference, self.check_kb, self.check_cascade, self.check_gaps,
                 self.check_h1, self.check_h2, self.check_scenario, self.check_label_and_ties)
        for step in steps:
            try:
                step()
            except (KeyError, ValueError, ArithmeticError, StopIteration, TypeError) as e:
                self.bad.append(f"{step.__name__}: {type(e).__name__}: {e}")
                if step in (self.check_kb, self.check_cascade, self.check_gaps,
                            self.check_h1):
                    break  # later steps need its results
        return self.bad, self.ok


def problems(root: Path = ROOT) -> tuple[list[str], list[str]]:
    """(failures, one summary line per passed part)."""
    try:
        return Checker(root).run()
    except (OSError, KeyError, ValueError) as e:
        return [f"{type(e).__name__}: {e}"], []


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--root", default=str(ROOT), help="repository root (default: this one)")
    bad, ok = problems(Path(ap.parse_args(argv).root))
    for line in ok:
        print(line)
    if bad:
        for b in bad:
            print(f"FAIL: {b}")
        return 1
    print(f"OK: the standard-library recompute matches outputs/ ({len(ok)} parts)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
