"""Task 4 analysis tests (plan §4-§8, §10).

The two pinned Review Focus tests (test_detection_gap_floor_zero,
test_tbprio_pinned_version), the brief's tests (test_ratio_interval_rule, test_label_rule,
test_outputs_byte_identical_on_rerun) and unit tests of k_b, the R intervals, the
decomposition rule, the scenario formula, the IRLS and the draw-set order.
"""
import hashlib
import importlib.metadata
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest
import tbprio
from scipy.stats import beta as beta_dist
from tbprio import shrink

from src.dmgap import (SEED, benchmark, cascade, check_tbprio, draws, gaps, panel, priority,
                       reference, validate)
from src.dmgap.draws import EB, JEFFREYS

ROOT = Path(__file__).resolve().parents[1]
OUTPUTS = ROOT / "outputs"

# SHA-256 of src/tbprio/* at tag v1.0.1 of hssling/india-tb-priority-tool, recorded with
# `git show v1.0.1:src/tbprio/<file> | sha256sum` in the local checkout (21 Nov 2026).
TBPRIO_V101 = {
    "__init__.py": "4067d1c97393be078a199753d5c9402a56337eb5b07cfe88273448d15f871d22",
    "__main__.py": "4fdbd07dc7384b8ada292817a8b9f1692a381c539579db5fb3fb544eb966493f",
    "district.py": "815e10f7ab9529b93a1a3a574269bf84a5db1623438bbd90a5dcbfaffd429f93",
    "harm.py": "3e60565c319f7b38553d39bb25055cefa57ddfdf9348197879ea33f8c637f0a1",
    "panel.py": "235d992b123e8ea50eedeba13346d6c44bca6104ee130a940154dad079b17d84",
    "priority.py": "f5557a434394729ad748bb0fa5b25a9fe01e052cb0df6d4cc5f4e8318162f116",
    "report.py": "f1ff4cdf80a0593e055494ecdd1b1363a5ba6b7923bc815d21d49738773396be",
    "schema.py": "39688c1cb76ec47cdac6a745074c756ebdedff74353f13bbbf860d28acd13df8",
    "shrink.py": "b95859662e7855020319cfad398b97f32d38c5c33d0b4243ceeff75f5e5c4f4b",
    "state.py": "1b7ec61f514ebb518841bf7c18d5ef3479516ae8d3785ee7ab1584c48fad5c57",
    "table.py": "0a99d43157a84186b76ece3e12272e723886a41bc20b6442ea533ef85570b97c",
    "trend.py": "5fc582f329ac11f066419f162da3e5eb432e3319b042e548cbc6bede962870a8",
    "validate.py": "3f35042dbad52cf2996495f68e54a838535def51be4150276a4a0af37026bef0",
}


def synth(fn) -> dict:
    """A synthetic panel: fn(i, unit, year) -> (N, K, D, I) for every unit-year."""
    out = {}
    for i, u in enumerate(panel.UNITS):
        for t in panel.YEARS:
            out[(u, t)] = panel.Cell(u, t, *fn(i, u, t))
    return out


# ---- Review Focus 5 -------------------------------------------------------------------

def test_tbprio_pinned_version():
    assert importlib.metadata.version("tbprio") == "1.0.1"
    assert getattr(tbprio, "__version__", "1.0.1") == "1.0.1"
    assert check_tbprio() == "1.0.1"
    src = Path(tbprio.__file__).resolve().parent
    files = sorted(p.name for p in src.glob("*.py"))
    assert files == sorted(TBPRIO_V101)
    for name, digest in TBPRIO_V101.items():
        assert hashlib.sha256((src / name).read_bytes()).hexdigest() == digest, name


# ---- Review Focus 4 -------------------------------------------------------------------

def test_detection_gap_floor_zero():
    # y = D/K = 0.30 well above k p = 0.10: E2 = 0 observed, and never negative per draw.
    pan = synth(lambda i, u, t: (1000, 900, 270 if i == 0 else 60, 30))
    p = {u: 0.10 for u in panel.UNITS}
    u0 = panel.UNITS[0]
    assert gaps.point_e2(pan[(u0, 2023)], 0.10, 1.0) == 0.0
    ds = draws.build(pan, 2023, EB)
    e2 = gaps.e2_draws(ds, p, 1.0)
    for u, d in e2.items():
        assert np.all(d >= 0.0), u
        assert np.array_equal(d == 0.0, ds.y[u] >= 0.10), u
    assert np.all(e2[u0] == 0.0)
    # the floor is per draw: a unit whose observed y is just above k p can have mean > 0
    pan2 = synth(lambda i, u, t: (1000, 50, 6, 3))   # y = 0.12
    ds2 = draws.build(pan2, 2023, JEFFREYS)
    e2b = gaps.e2_draws(ds2, {u: 0.10 for u in panel.UNITS}, 1.0)
    assert gaps.point_e2(pan2[(u0, 2023)], 0.10, 1.0) == 0.0
    assert e2b[u0].mean() > 0.0 and e2b[u0].min() == 0.0
    rows = gaps.compute(pan, p, 1.0)
    assert all(r["E2"] >= 0.0 for r in rows)


# ---- R and "likely under-detection" (§5.6) --------------------------------------------

def test_ratio_interval_rule():
    # unit 0: y = 0.05 against p = 0.10 (clearly below); unit 1: y = 0.099 (interval
    # straddles 1); others y = 0.08.
    def fn(i, u, t):
        D = {0: 500, 1: 990}.get(i, 800)
        return (12000, 10000, D, D // 2)
    pan = synth(fn)
    p = {u: 0.10 for u in panel.UNITS}
    jeff = draws.build(pan, 2023, JEFFREYS)
    u0, u1 = panel.UNITS[0], panel.UNITS[1]
    for u, D in ((u0, 500), (u1, 990)):
        pt, lo, hi, pb = cascade.r_summary(jeff, u, p[u], 1.0)
        r = jeff.y[u] / 0.10
        assert pt == pytest.approx(D / 10000 / 0.10)
        assert (lo, hi) == tuple(np.percentile(r, [2.5, 97.5], method="linear"))
        assert pb == np.mean(r < 1.0)
        # the draw interval approximates the Jeffreys quantiles of y / p
        q = beta_dist.ppf([0.025, 0.975], 0.5 + D, 0.5 + 10000 - D) / 0.10
        assert lo == pytest.approx(q[0], rel=5e-3) and hi == pytest.approx(q[1], rel=5e-3)
    assert cascade.likely_under_detection(jeff, u0, 0.10, 1.0)
    assert not cascade.likely_under_detection(jeff, u1, 0.10, 1.0)
    # at k = 0.5 the expected yield is 0.05: unit 0 is no longer below
    assert not cascade.likely_under_detection(jeff, u0, 0.10, 0.5)
    # below the benchmark: P(R_k < 1) >= 0.95
    assert cascade.below_benchmark(jeff, u0, 0.10, 1.0)
    assert not cascade.below_benchmark(jeff, u1, 0.10, 1.0)
    kp = {u: 0.10 for u in panel.UNITS}
    assert u0 in validate.fixed_rule_units(jeff, kp)
    assert u1 not in validate.fixed_rule_units(jeff, kp)
    assert set(validate.below_units(jeff, kp)) >= {u0} and u1 not in validate.below_units(jeff, kp)
    # the cascade rows carry the same flags
    rows = {r["unit"]: r for r in cascade.unit_rows(pan, 2023, p, 1.0, jeff, None)}
    assert rows[u0]["likely_under_detection"] and not rows[u1]["likely_under_detection"]
    assert rows[u0]["below_benchmark"] and not rows[u1]["below_benchmark"]


def test_jeffreys_wilson_newcombe():
    lo, hi = cascade.jeffreys(10, 100)
    assert (lo, hi) == pytest.approx(tuple(beta_dist.ppf([0.025, 0.975], 10.5, 90.5)))
    c, lo, hi = cascade.wilson(10, 100)
    # Wilson (1927) for 10/100: 0.0552 to 0.1744
    assert c == 0.1 and lo == pytest.approx(0.05523, abs=1e-4) and hi == pytest.approx(
        0.17437, abs=1e-4)
    d, dlo, dhi = cascade.newcombe(cascade.wilson(10, 100), cascade.wilson(20, 100))
    assert d == pytest.approx(0.1)
    # Newcombe (1998) method 10 for 20/100 vs 10/100: about -0.0004 to 0.1997
    assert dlo == pytest.approx(-0.0004, abs=2e-3) and dhi == pytest.approx(0.1997, abs=2e-3)


# ---- the label rule (§8.9) ------------------------------------------------------------

def test_label_rule():
    entries = lambda signs: [{"beta1": s} for s in signs]  # noqa: E731
    ten = [1.0] * 10 + [-1.0, None]
    nine = [1.0] * 9 + [-1.0, 0.0, None]
    assert validate.label((0.1, 0.9), entries(ten), 0.5) == ("supported", 10)
    assert validate.label((0.1, 0.9), entries(nine), 0.5) == ("not established", 9)
    # interval touching or crossing the null
    assert validate.label((0.0, 0.9), entries(ten), 0.5)[0] == "not established"
    assert validate.label((-0.1, 0.9), entries([1.0] * 12), 0.5)[0] == "not established"
    # a supported negative estimate
    assert validate.label((-0.9, -0.1), entries([-1.0] * 12), -0.5) == ("supported", 12)
    # undefined or zero entries never agree
    assert validate.label((0.1, 0.9), entries([1.0] * 9 + [None, None, None]),
                          0.5) == ("not established", 9)
    assert validate.label((0.1, 0.9), entries([1.0] * 9 + [0.0] * 3),
                          0.5) == ("not established", 9)


# ---- k_b (§5.2) -----------------------------------------------------------------------

def test_k_b_known_values_jeffreys():
    # pool 2021 + 2022: n_u = 500 + 499 = 999; x_u = 10 i; p = 0.1; Jeffreys:
    # yhat = (10 i + 0.5) / 1000, g = (10 i + 0.5) / 100.
    def fn(i, u, t):
        if t == 2021:
            return (600, 500, 5 * i, 0)
        if t == 2022:
            return (600, 499, 5 * i, 0)
        return (600, 500, 10, 5)
    pan = synth(fn)
    p = {u: 0.1 for u in panel.UNITS}
    kb = benchmark.k_b(pan, p, prior=JEFFREYS)
    assert kb.value == pytest.approx((240 + 0.5) / 100)          # i = 24 of 0..32
    assert benchmark.k_b(pan, p, percentile="median", prior=JEFFREYS).value == pytest.approx(
        (160 + 0.5) / 100)
    assert benchmark.k_b(pan, p, percentile="p90", prior=JEFFREYS).value == pytest.approx(
        (280.5 + 0.8 * 10) / 100)                                 # 28.8: interpolated
    assert len(kb.units) == 33 and kb.excluded == []
    # by construction, about a quarter lie above k_b
    assert sum(g > kb.value for g in kb.g.values()) == 8


def test_k_b_empirical_bayes_and_exclusion():
    rng = np.random.default_rng(1)
    K = rng.integers(2000, 9000, size=(33, 5))
    Y = rng.uniform(0.04, 0.12, size=33)

    def fn(i, u, t):
        k = int(K[i, panel.YEARS.index(t)])
        if i == 3 and t == 2022:
            return (k + 10, 0, 0, 0)          # K = 0: y NA, excluded from the pool
        return (k + 100, k, int(round(Y[i] * k)), 1)
    pan = synth(fn)
    p = {u: 0.05 + 0.002 * i for i, u in enumerate(panel.UNITS)}
    kb = benchmark.k_b(pan, p)
    u3 = panel.UNITS[3]
    assert kb.excluded == [u3] and u3 not in kb.units and len(kb.units) == 32
    x = np.array([pan[(u, 2021)].D + pan[(u, 2022)].D for u in kb.units], dtype=float)
    n = np.array([pan[(u, 2021)].K + pan[(u, 2022)].K for u in kb.units], dtype=float)
    a, b = shrink.beta_binomial(x, n)
    g = (a + x) / (a + b + n) / np.array([p[u] for u in kb.units])
    assert kb.value == np.percentile(g, 75, method="linear")
    # the 2019 + 2021 pool
    kb2 = benchmark.k_b(pan, p, pool=benchmark.POOL_ALT)
    assert kb2.pool == (2019, 2021) and len(kb2.units) == 33
    # a common scaling of p scales k_b by the reciprocal (§8.11)
    kb8 = benchmark.k_b(pan, reference.scaled(p, 0.8))
    assert kb8.value == pytest.approx(kb.value / 0.8)
    # leave-one-out drops the unit from the pool
    assert panel.UNITS[0] not in benchmark.k_b(pan, p, omit=panel.UNITS[0]).units


# ---- draw sets (§5.3) -----------------------------------------------------------------

def test_draw_set_order_and_seed():
    def fn(i, u, t):
        if i == 2:
            return (1000, 1200, 50, 10)       # K > N: C1 NA, y valid
        if i == 5:
            return (1000, 900, 950, 10)       # D > K: y NA, C1 valid
        return (1000 + 10 * i, 800 + 5 * i, 40 + i, 20)
    pan = synth(fn)
    ds = draws.build(pan, 2022, EB)
    cells = [pan[(u, 2022)] for u in panel.UNITS]
    c1 = [c for c in cells if c.c1_ok]
    yy = [c for c in cells if c.y_ok]
    a1, b1 = shrink.beta_binomial([c.U for c in c1], [c.N for c in c1])
    a2, b2 = shrink.beta_binomial([c.D for c in yy], [c.K for c in yy])
    assert (ds.a1, ds.b1, ds.a2, ds.b2) == (a1, b1, a2, b2)
    rng = np.random.default_rng(SEED)
    for c in cells:
        if c.c1_ok:
            assert np.array_equal(ds.s[c.unit], rng.beta(a1 + c.U, b1 + c.K, size=10000))
        if c.y_ok:
            assert np.array_equal(ds.y[c.unit], rng.beta(a2 + c.D, b2 + c.K - c.D,
                                                         size=10000))
    assert panel.UNITS[2] not in ds.s and panel.UNITS[5] not in ds.y
    # a fresh generator per draw set: rebuilding gives identical draws
    ds2 = draws.build(pan, 2022, EB)
    assert all(np.array_equal(ds.y[u], ds2.y[u]) for u in ds.y)


def test_draw_set_no_screening_gap_and_fallback():
    pan = synth(lambda i, u, t: (1000, 1000, 50 + i, 10))   # U = 0 everywhere
    ds = draws.build(pan, 2023, EB)
    assert ds.no_screening_gap and ds.a1 is None
    assert all(np.all(v == 0) for v in ds.s.values())
    rng = np.random.default_rng(SEED)
    for u in panel.UNITS:   # no s draws were taken: the y stream starts at the first unit
        c = pan[(u, 2023)]
        assert np.array_equal(ds.y[u], rng.beta(ds.a2 + c.D, ds.b2 + c.K - c.D, size=10000))
    e1 = gaps.e1_draws(ds, {u: 0.1 for u in panel.UNITS}, 1.0)
    assert all(np.all(v == 0) for v in e1.values())
    pan0 = synth(lambda i, u, t: (1000, 900, 0, 0))          # D = 0: pooled yield 0
    ds0 = draws.build(pan0, 2023, EB)
    assert ds0.flags == ["prior_fallback_jeffreys:yield"] and (ds0.a2, ds0.b2) == (0.5, 0.5)


def test_na_rules():
    c = panel.Cell("X", 2023, 100, 120, 10, 5)
    assert c.c1_reason() == "K > N" and c.y_ok and c.c3_ok
    assert panel.Cell("X", 2023, 0, 0, 0, 0).c1_reason() == "N = 0"
    assert panel.Cell("X", 2023, 100, 0, 0, 0).y_reason() == "K = 0"
    assert panel.Cell("X", 2023, 100, 50, 60, 0).y_reason() == "D > K"
    assert panel.Cell("X", 2023, 100, 50, 10, 11).c3_reason() == "I > D"
    assert panel.Cell("X", 2023, 100, 50, 0, 0).c3_reason() == "D = 0"
    assert panel.Cell("X", 2023, None, 50, 10, 1).c1_reason() == "notified missing"


def test_reference_merge():
    nfhs = [
        {"unit": "India", "sex": "women", "prevalence_pct": "13", "population": "1",
         "flag": ""},
        {"unit": "India", "sex": "men", "prevalence_pct": "15", "population": "1",
         "flag": ""},
    ]
    sex = []
    for u in panel.UNITS:
        for s, v in (("women", "20.0"), ("men", "10.0")):
            nfhs.append({"unit": u, "sex": s, "prevalence_pct": v, "population": "300",
                         "flag": ""})
        sex.append({"unit": u, "male": "590", "female": "400", "transgender": "10"})
    for s, v in (("women", "40.0"), ("men", "30.0")):
        nfhs.append({"unit": "Ladakh", "sex": s, "prevalence_pct": v, "population": "100",
                     "flag": "merge_into:Jammu and Kashmir"})
    sex.append({"unit": "Jammu and Kashmir", "male": "0", "female": "0", "transgender": "0"})
    comp = reference.components(nfhs, sex)
    jk = comp["Jammu and Kashmir"]
    assert jk["w"] == pytest.approx((300 * 0.2 + 100 * 0.4) / 400)
    assert jk["m"] == pytest.approx((300 * 0.1 + 100 * 0.3) / 400)
    assert jk["members"] == "Jammu and Kashmir;Ladakh"
    assert jk["f"] == pytest.approx(400 / 1000)    # transgender in the denominator
    assert jk["p_sex_weighted"] == pytest.approx(0.4 * jk["w"] + 0.6 * jk["m"])
    assert jk["p_simple"] == pytest.approx((jk["w"] + jk["m"]) / 2)
    ps = reference.p_s(nfhs, sex, "sex_weighted")
    assert ps["Bihar"] == pytest.approx(0.4 * 0.2 + 0.6 * 0.1)
    bad = [r for r in nfhs if r["unit"] != "Goa"]
    with pytest.raises(ValueError, match="Goa"):
        reference.components(bad, sex)


# ---- decomposition (§6.3) -------------------------------------------------------------

def test_decomposition_rule_exclusions():
    e1 = np.array([1.0, 1.0, 0.0, 2.0, 0.0])
    e2 = np.array([1.0, 0.0, 0.0, 1.0, 3.0])
    p_gt, p_lt, anyp, s = priority.share_probs(e1, e2)
    # S = 0.5 (draw 0) and E1 + E2 = 0 (draw 2) count in neither; the base is all draws
    assert p_gt == pytest.approx(2 / 5) and p_lt == pytest.approx(1 / 5) and anyp
    assert np.isnan(s[2]) and s[0] == 0.5
    assert priority.classify(0.95, 0.0, True) == "screening-led"
    assert priority.classify(0.0, 0.95, True) == "identification-led"
    assert priority.classify(0.94, 0.05, True) == "mixed"
    assert priority.classify(0.0, 0.0, False) == "no shortfall"
    z = np.zeros(10)
    assert priority.classify(*priority.share_probs(z, z)[:3]) == "no shortfall"
    # 95% of draws at S = 0.5 and 5% with S > 0.5: mixed, not screening-led
    a = np.r_[np.ones(95), np.full(5, 2.0)]
    b = np.ones(100)
    p_gt, p_lt, _, _ = priority.share_probs(a, b)
    assert (p_gt, p_lt) == (0.05, 0.0)
    assert priority.classify(p_gt, p_lt, True) == "mixed"


def test_decomposition_small_total_shortfall():
    e1 = {"A": np.full(10, 90.0), "B": np.full(10, 1.0), "C": np.full(10, 5.0)}
    e2 = {"A": np.full(10, 10.0), "B": np.full(10, 9.0), "C": np.full(10, 5.0), "D": np.ones(10)}
    N = {"A": 1000, "B": 1000, "C": 100, "D": 10}
    rows = {r["unit"]: r for r in priority.decompose(e1, e2, N)}
    assert set(rows) == {"A", "B", "C"}                     # D has no E1
    assert rows["A"]["class"] == "screening-led"
    assert rows["B"]["class"] == "identification-led"
    assert rows["C"]["class"] == "mixed"                    # S = 0.5 in every draw
    # T per 100k: A 10000, B 1000, C 10000; median 10000; B below it
    assert rows["B"]["small_total_shortfall"] and not rows["A"]["small_total_shortfall"]
    assert rows["B"]["description"] == "small total shortfall; identification-led"


# ---- scenario (§6.4) ------------------------------------------------------------------

def test_scenario_formula():
    units = [f"U{j}" for j in range(6)]
    cells = {u: panel.Cell(u, 2023, 100 * (j + 1), 0, 0, 0) for j, u in enumerate(units)}
    c = {u: np.array([0.5, 0.9, 1.0]) for u in units}
    y = {u: np.array([0.1, 0.3, 0.05]) * (1 + 0.1 * j) for j, u in enumerate(units)}
    ds = draws.DrawSet(2023, EB, "main", None, cells, units, units, 1.0, 1.0, 1.0, 1.0, [],
                       False, {u: 1.0 - c[u] for u in units}, y)
    p = {u: 0.2 for u in units}
    s = priority.scenario(ds, p, 1.0, 0.8)
    for j, u in enumerate(units):
        N = cells[u].N
        exp = N * (np.maximum(c[u], 0.8) * np.maximum(y[u], 0.2) - c[u] * y[u])
        assert np.allclose(s["A"][u], exp)
        assert np.all(s["A"][u] >= 0)
    # draw 2: coverage 1.0 >= c_b and yield 0.05 < 0.2 -> N (0.2 - 0.05)
    assert s["A"]["U0"][2] == pytest.approx(100 * (0.2 - 0.05))
    total = sum(s["A"][u] for u in units)
    assert s["national"][0] == pytest.approx(total.mean())
    means = {u: s["A"][u].mean() for u in units}
    top = sorted(units, key=lambda u: (-means[u], u))[:5]
    assert s["top5"] == top and "U0" not in top
    assert s["share"] == pytest.approx(sum(means[u] for u in top) / sum(means.values()))


# ---- IRLS (§8.2) ----------------------------------------------------------------------

def test_irls_known_fit():
    rng = np.random.default_rng(7)
    m = 60
    x = rng.uniform(-3.0, -1.0, size=m)
    d = (np.arange(m) % 2).astype(float)
    X = np.column_stack([np.ones(m), x, d])
    beta = np.array([0.4, 1.7, 0.2])
    mu = validate.expit(X @ beta)
    a = rng.integers(100, 50000, size=m).astype(float)
    f = validate.irls(X, mu, a)                     # exact data: recovers beta
    assert np.allclose(f.beta, beta, atol=1e-8)
    assert f.phi == pytest.approx(0.0, abs=1e-12)
    # noisy data: the score equations X'a(y - mu) = 0 hold at the solution
    K = a.astype(int)
    D = rng.binomial(K, mu)
    yv = D / K
    f2 = validate.irls(X, yv, a)
    muh = validate.expit(X @ f2.beta)
    assert np.allclose(X.T @ (a * (yv - muh)), 0.0, atol=1e-6)
    phi = np.sum(a * (yv - muh) ** 2 / (muh * (1 - muh))) / (m - 3)
    assert f2.phi == pytest.approx(phi)
    se, lo, hi = f2.wald()
    assert se == pytest.approx(np.sqrt(phi * f2.cov_unscaled[1, 1]))
    # unweighted (a = 1) also converges
    assert np.allclose(validate.irls(X, mu, np.ones(m)).beta, beta, atol=1e-8)


def test_irls_undefined():
    X = np.column_stack([np.ones(5), np.full(5, -2.0)])   # one p_u: singular
    with pytest.raises(validate.Undefined):
        validate.irls(X, np.full(5, 0.1), np.ones(5))
    X = np.column_stack([np.ones(4), np.arange(4.0), np.zeros(4)])  # empty year column
    with pytest.raises(validate.Undefined):
        validate.irls(X, np.array([0.1, 0.2, 0.15, 0.3]), np.ones(4))


def test_h1_data_and_kish():
    pan = synth(lambda i, u, t: (1000, 500 + i, 40 + i, 10))
    p = {u: 0.1 + 0.002 * i for i, u in enumerate(panel.UNITS)}
    d = validate.h1_data(pan, p)
    assert len(d.y) == 66 and d.units == list(panel.UNITS)
    assert d.X.shape == (66, 3) and set(d.X[:, 2]) == {0.0, 1.0}
    w = np.array([2 * (500 + i) for i in range(33)], dtype=float)
    assert validate.kish(d) == pytest.approx(w.sum() ** 2 / np.sum(w ** 2))
    assert validate.h1_data(pan, p, "2023").X.shape == (33, 2)
    assert validate.h1_data(pan, p, "2021-2023").X.shape == (99, 4)


# ---- committed outputs ----------------------------------------------------------------

def test_outputs_structure():
    import csv
    read = lambda n: list(csv.DictReader(open(OUTPUTS / n, encoding="utf-8")))  # noqa: E731
    head = read("headline.csv")
    assert [r["estimate"] for r in head] == ["H1", "H2", "H3"]
    assert list(head[0]) == ["estimate", "value", "lo", "hi", "null", "n", "n_grid",
                             "n_agree", "label"]
    assert head[0]["label"] in ("supported", "not established")
    assert head[1]["label"] == "" and head[2]["label"] == ""
    assert len(read("spec_curve.csv")) == 12
    assert sum(r["is_main"] == "True" for r in read("spec_curve.csv")) == 1
    gp = read("gaps.csv")
    assert all(float(r["mean"]) >= 0 for r in gp)
    assert {r["gap"] for r in gp} == {"E1", "E2", "E3"}
    pr = read("priority.csv")
    assert {r["tier"] for r in pr} <= {"act now", "probable priority", "uncertain",
                                       "lower priority"}
    for name in ("reference_prevalence", "benchmark", "cascade", "gaps", "priority",
                 "decomposition", "scenario", "trend", "funnel", "headline",
                 "headline_sensitivity", "spec_curve", "perturbation", "leave_one_out",
                 "na_cells"):
        assert (OUTPUTS / f"{name}.csv").exists(), name
    raw = (OUTPUTS / "headline.csv").read_bytes()
    assert b"\r\n" not in raw


def _read_out(name):
    import csv
    with open(OUTPUTS / name, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def test_registered_basis_covers_c1_e1_outputs():
    reg = "denominator_a1_2_registered"
    for name, key, need in (("cascade.csv", "spec", None), ("gaps.csv", "spec", "E1"),
                            ("priority.csv", "spec", "E1"), ("decomposition.csv", "spec", None),
                            ("scenario.csv", "spec", None), ("trend.csv", "model", None)):
        rows = [r for r in _read_out(name) if r[key] == reg]
        assert rows, name
        if need:
            assert any(r["gap"] == need for r in rows), name
            assert {r["year"] for r in rows if r["gap"] == need} == {"2021", "2022", "2023"}
    pr = [r for r in _read_out("priority.csv") if r["spec"] == reg]
    assert any(r["gap"] == "total" for r in pr)
    # the basis's own falling-coverage flag: HP and Tripura are not estimable on A1.2
    for r in pr:
        if r["unit"] in ("Himachal Pradesh", "Tripura"):
            assert r["falling_coverage"] == ""
    loo = [r for r in _read_out("leave_one_out.csv")
           if r["spec"] == reg and r["kind"] == "act_now_E1"]
    assert {r["year"] for r in loo} == {"2022", "2023"} and len(loo) == 66
    assert any(r["spec"] == reg and r["kind"] == "act_now_E1_max_changes"
               for r in _read_out("leave_one_out.csv"))
    hs = _read_out("headline_sensitivity.csv")
    assert {r["year"] for r in hs if r["estimate"] == "H2_difference" and r["spec"] == reg} == {
        "2022 vs 2018", "2022 vs 2019", "2023 vs 2018"}
    assert {r["year"] for r in hs if r["estimate"] == "H2_national_coverage"
            and r["spec"] == reg} == {"2021", "2022", "2023"}
    scal = [r for r in hs if r["spec"].startswith("p_x0.8") and r["estimate"].startswith("count")]
    assert scal and all("R scales exactly by 1/0.8" in r["note"] for r in scal)


def test_funnel_and_perturbation_wiring():
    fu = _read_out("funnel.csv")
    assert len(fu) == 99
    assert {(r["funnel_year"], sum(1 for x in fu if x["funnel_year"] == r["funnel_year"]))
            for r in fu} == {("2023", 33), ("2019", 33), ("2021", 33)}
    guj = [r for r in fu if r["unit"] == "Gujarat" and r["funnel_year"] == "2023"][0]
    assert guj["position"] == "below the 99.8% limit"
    assert guj["flag"] == validate.FLAG_LOW
    assert float(guj["z"]) < float(guj["lower_998"])
    assert len({r["phi_f"] for r in fu if r["funnel_year"] == "2023"}) == 1
    pt = _read_out("perturbation.csv")
    assert [r["unit"] for r in pt] == list(panel.UNITS)
    for r in pt:
        assert r["n_replicates"] == "1000"
        for k in ("share_tier_E1_unchanged", "share_tier_E2_unchanged",
                  "share_tier_total_unchanged", "share_h3_unchanged", "share_class_unchanged"):
            assert 0.0 <= float(r[k]) <= 1.0
            assert float(r[k]) * 1000 == round(float(r[k]) * 1000)
    # the baseline matches the main 2023 outputs
    pr = {(r["unit"], r["gap"]): r["tier"] for r in _read_out("priority.csv")
          if r["spec"] == "main" and r["year"] == "2023"}
    de = {r["unit"]: r["class"] for r in _read_out("decomposition.csv")
          if r["spec"] == "main" and r["year"] == "2023"}
    h3 = [r for r in _read_out("headline_sensitivity.csv") if r["estimate"] == "H3_units"][0]
    for r in pt:
        assert r["tier_E1"] == pr[(r["unit"], "E1")] and r["class"] == de[r["unit"]]
        assert (r["h3_member"] == "True") == (r["unit"] in h3["units"].split(";"))


def test_outputs_byte_identical_on_rerun(tmp_path):
    r = subprocess.run([sys.executable, "-I", str(ROOT / "src" / "run_all.py"), "--out",
                        str(tmp_path)], cwd=ROOT, capture_output=True, text=True,
                       timeout=1800)
    assert r.returncode == 0, r.stderr
    committed = sorted(p.name for p in OUTPUTS.glob("*.csv"))
    rerun = sorted(p.name for p in tmp_path.glob("*.csv"))
    assert committed == rerun
    for name in committed:
        assert (OUTPUTS / name).read_bytes() == (tmp_path / name).read_bytes(), name
