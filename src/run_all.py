"""Task 4: the full analysis of the registered plan (docs/analysis_plan.md, §4-§8, §10).

Run from the repository root:  python -I src/run_all.py  [--out DIR]

Writes outputs/*.csv (plan §10.3). Reruns with the same inputs give byte-identical files.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if __package__ in (None, ""):
    sys.path.insert(0, str(ROOT))

import numpy as np  # noqa: E402

from src.dmgap import (N_DRAWS, SEED, benchmark, cascade, check_tbprio, draws,  # noqa: E402
                       gaps, panel, priority, reference, table, trend, validate)
from src.dmgap.draws import EB, JEFFREYS  # noqa: E402

OUT = ROOT / "outputs"
SEX, SIMPLE = reference.SEX_WEIGHTED, reference.SIMPLE
MAIN, REG, FROM = panel.BASIS_MAIN, panel.BASIS_REGISTERED, panel.BASIS_FROM_PCT
SPEC_REG = "denominator_a1_2_registered"
SPEC_FROM = "denominator_2022_from_percent"
BASIS_SPEC = {REG: SPEC_REG, FROM: SPEC_FROM}
SCENARIO_LABEL = ("an illustration, not a forecast; the interval reflects binomial uncertainty in "
                  "coverage and yield only, not uncertainty in p_u or k_b")
N_PERTURB = 1000
SD_PERTURB = 0.10
MAIN_YEAR = 2023
LOO_YEARS = (2023, 2022)


def kb_key(percentile="p75", pool=benchmark.POOL_MAIN, ref=SEX, prior=EB):
    return (percentile, pool, ref, prior)


def pool_name(pool) -> str:
    return "+".join(str(t) for t in pool)


class Analysis:
    def __init__(self):
        self.version = check_tbprio()
        self.rows = panel.load_rows()
        self.pan = panel.build(self.rows)
        self.basis_rows = {b: panel.basis_rows(b) for b in (REG, FROM)}
        self.bases = {b: panel.with_basis(self.pan, b, self.basis_rows[b])
                      for b in (REG, FROM)}
        self.panels = {MAIN: self.pan, **self.bases}
        nfhs, sex = reference.load_nfhs(), reference.load_sex()
        self.comp = reference.components(nfhs, sex)
        self.P = {SEX: reference.p_s(nfhs, sex, SEX), SIMPLE: reference.p_s(nfhs, sex, SIMPLE)}
        self.kbs = {}
        for perc in benchmark.PERCENTILES:
            for pool in (benchmark.POOL_MAIN, benchmark.POOL_ALT):
                for ref in (SEX, SIMPLE):
                    for prior in (EB, JEFFREYS):
                        self.kbs[(perc, pool, ref, prior)] = benchmark.k_b(
                            self.pan, self.P[ref], pool, perc, prior)
        self.KB = self.kbs[kb_key()].value
        self.DS = {}
        for t in panel.YEARS:
            for prior in (EB, JEFFREYS):
                self.DS[(t, prior, MAIN)] = draws.build(self.pan, t, prior, MAIN)
        for b, bp in self.bases.items():
            for t in panel.BASIS_YEARS[b]:
                for prior in (EB, JEFFREYS):
                    self.DS[(t, prior, b)] = draws.build(bp, t, prior, b)
        self.C3 = {t: cascade.c3_set(self.pan, t) for t in panel.C3_MAIN_YEARS}
        self.trend_rows, self.phis = trend.run(
            self.pan, {SPEC_REG: self.bases[REG], SPEC_FROM: self.bases[FROM]})
        self.falling = trend.falling(self.trend_rows)
        self.out: dict[str, list[dict]] = {}

    # ---- specifications of the gaps and priorities (§5.7, §6.1, §8.11) ----------------

    def gap_specs(self) -> list[dict]:
        ps, psimple = self.P[SEX], self.P[SIMPLE]
        all_y = panel.YEARS
        sp = [dict(spec="main", prior=EB, basis=MAIN, k=self.KB, p=ps, years=all_y)]
        for k in (1.0, 1.5, 2.0):
            sp.append(dict(spec=f"k={k:g}", prior=EB, basis=MAIN, k=k, p=ps, years=all_y))
        for perc in ("median", "p90"):
            sp.append(dict(spec=f"kb_{perc}", prior=EB, basis=MAIN,
                           k=self.kbs[kb_key(perc)].value, p=ps, years=all_y))
        sp.append(dict(spec="kb_pool_2019+2021", prior=EB, basis=MAIN,
                       k=self.kbs[kb_key(pool=benchmark.POOL_ALT)].value, p=ps,
                       years=all_y))
        sp.append(dict(spec="reference_simple", prior=EB, basis=MAIN,
                       k=self.kbs[kb_key(ref=SIMPLE)].value, p=psimple, years=all_y))
        sp.append(dict(spec="shrinkage_off", prior=JEFFREYS, basis=MAIN,
                       k=self.kbs[kb_key(prior=JEFFREYS)].value, p=ps, years=all_y))
        for b in (REG, FROM):
            sp.append(dict(spec=BASIS_SPEC[b], prior=EB, basis=b, k=self.KB, p=ps,
                           years=panel.BASIS_YEARS[b]))
        for factor in (0.8, 1.2):
            pf = reference.scaled(ps, factor)
            for k in (1.0, 1.5, 2.0):
                sp.append(dict(spec=f"p_x{factor:g}_k={k:g}", prior=EB, basis=MAIN, k=k,
                               p=pf, years=all_y))
        return sp

    # ---- outputs ------------------------------------------------------------------------

    def reference_rows(self):
        cols = ["unit", "members", "w", "m", "f", "male", "female", "transgender",
                "p_sex_weighted", "p_simple", "population_weights", "flags"]
        self.out["reference_prevalence"] = [{c: self.comp[u][c] for c in cols}
                                            for u in panel.UNITS]

    def benchmark_rows(self):
        rows = []
        for (perc, pool, ref, prior), kb in self.kbs.items():
            rows.append({"kind": "k_b", "percentile": perc, "pool": pool_name(pool),
                         "reference": ref, "prior": prior, "basis": "",
                         "year": "", "value": kb.value, "below_1": kb.value < 1.0,
                         "n_units": len(kb.units), "excluded_units": kb.excluded,
                         "alpha": kb.alpha, "beta": kb.beta,
                         "is_main": (perc, pool, ref, prior) == kb_key()})
        for b in (MAIN, REG):
            ds = self.DS[(MAIN_YEAR, EB, b)]
            for perc in benchmark.PERCENTILES:
                rows.append({"kind": "c_b", "percentile": perc, "prior": EB,
                             "basis": BASIS_SPEC.get(b, MAIN), "year": MAIN_YEAR,
                             "value": benchmark.c_b(ds, perc), "n_units": len(ds.units_c1),
                             "is_main": b == MAIN and perc == "p75"})
        for t, cs in self.C3.items():
            rows.append({"kind": "c3_b", "percentile": "p75", "year": t, "value": cs.c3_b,
                         "n_units": len(cs.units), "basis": MAIN})
        for (t, prior, b), ds in sorted(self.DS.items(), key=lambda kv: (kv[0][2] != MAIN,
                                                                         kv[0][2], kv[0][0],
                                                                         kv[0][1])):
            rows.append({"kind": "draw_set_prior", "prior": prior,
                         "basis": BASIS_SPEC.get(b, MAIN), "year": t,
                         "n_units": len(ds.cells), "n_units_c1": len(ds.units_c1),
                         "n_units_y": len(ds.units_y), "a1": ds.a1, "b1": ds.b1,
                         "a2": ds.a2, "b2": ds.b2, "no_screening_gap": ds.no_screening_gap,
                         "flags": ds.flags})
        self.out["benchmark"] = rows

    def cascade_rows(self):
        rows = []
        ps = self.P[SEX]
        flags: dict[tuple[str, str, str], list[str]] = {}
        for src_rows, spec in [(self.rows, MAIN)] + [(self.basis_rows[b], b) for b in (REG, FROM)]:
            for r in src_rows:
                if r["flag"]:
                    flags.setdefault((spec, r["unit"], r["year"]), []).append(
                        f"{r['measure']}:{r['flag']}")
        for b, pan in self.panels.items():
            years = panel.YEARS if b == MAIN else panel.BASIS_YEARS[b]
            for t in years:
                jeff = self.DS[(t, JEFFREYS, b)]
                for r in cascade.unit_rows(pan, t, ps, self.KB, jeff, self.C3.get(t)):
                    fl = list(flags.get((MAIN, r["unit"], str(t)), []))
                    if b != MAIN:
                        fl = [f for f in fl if not f.startswith("notified:")]
                        fl += flags.get((b, r["unit"], str(t)), [])
                    rows.append({"spec": BASIS_SPEC.get(b, "main"), **r, "flags": " | ".join(fl)})
            for t in years:
                nat = cascade.national(pan, t)
                r = {"spec": BASIS_SPEC.get(b, "main"), "unit": "National (sum of units)",
                     "year": t, "interval_method": "Wilson"}
                for q in ("C1", "y", "C3"):
                    key = q if (q != "C3" or t in panel.C3_MAIN_YEARS) else \
                        "C3_linked_ncd_clinic_2018"
                    v = nat[q]
                    r.update({key: v["value"], f"{key}_lo": v["lo"], f"{key}_hi": v["hi"],
                              f"{q}_x": v["x"], f"{q}_n": v["n"], f"{q}_units": v["units"]})
                rows.append(r)
        for r in rows:
            r.setdefault("interval_method", "Jeffreys; R from Jeffreys draws")
        self.out["cascade"] = rows

    def gaps_priority(self):
        gap_rows, prio_rows = [], []
        self.main_draws = {}
        for sp in self.gap_specs():
            for t in sp["years"]:
                ds = self.DS[(t, sp["prior"], sp["basis"])]
                g = gaps.draw_gaps(ds, sp["p"], sp["k"])
                if sp["spec"] == "main" and t in LOO_YEARS:
                    self.main_draws[t] = g
                for gap in ("E1", "E2", "total"):
                    res = priority.run(g[gap])
                    for u in sorted(g[gap]):
                        cell = ds.cells[u]
                        m, lo, hi = gaps.summarise(g[gap][u])
                        per = gaps.per_100k(m, cell.N)
                        base = {"unit": u, "year": t, "gap": gap, "spec": sp["spec"]}
                        if gap != "total":
                            gap_rows.append({**base, "k": sp["k"],
                                             "point": gaps.point(gap, cell, sp["p"][u],
                                                                 sp["k"]),
                                             "mean": m, "lo": lo, "hi": hi,
                                             "per_100k_notified": per})
                        prio_rows.append({**base, "mean": m, "lo": lo, "hi": hi,
                                          "per_100k_notified": per,
                                          "p_top5": res[u]["p_top5"], "tier": res[u]["tier"],
                                          "falling_coverage": self.falling[u]})
        for t, cs in self.C3.items():
            res = priority.run(cs.e3)
            for u in cs.units:
                cell = cs.cells[u]
                m, lo, hi = gaps.summarise(cs.e3[u])
                per = gaps.per_100k(m, cell.N)
                base = {"unit": u, "year": t, "gap": "E3", "spec": "main"}
                gap_rows.append({**base, "k": None, "point": float(cell.D - cell.I),
                                 "mean": m, "lo": lo, "hi": hi, "per_100k_notified": per})
                prio_rows.append({**base, "mean": m, "lo": lo, "hi": hi,
                                  "per_100k_notified": per, "p_top5": res[u]["p_top5"],
                                  "tier": res[u]["tier"],
                                  "falling_coverage": self.falling[u]})
        key = lambda r: (r["spec"] != "main", r["spec"], r["year"], r["gap"], r["unit"])  # noqa: E731
        self.out["gaps"] = sorted(gap_rows, key=key)
        self.out["priority"] = sorted(prio_rows, key=key)

    def decomposition_rows(self):
        rows = []
        specs = {s["spec"]: s for s in self.gap_specs()}
        for name in ("main", "k=1", "k=1.5", "k=2", SPEC_REG, SPEC_FROM):
            sp = specs[name]
            for t in sp["years"]:
                ds = self.DS[(t, sp["prior"], sp["basis"])]
                g = gaps.draw_gaps(ds, sp["p"], sp["k"])
                N = {u: ds.cells[u].N for u in ds.cells}
                for r in priority.decompose(g["E1"], g["E2"], N):
                    rows.append({"spec": name, "year": t, "k": sp["k"], **r})
        self.out["decomposition"] = rows

    def scenario_rows(self):
        rows = []
        ps = self.P[SEX]
        ds_main = self.DS[(MAIN_YEAR, EB, MAIN)]
        cb_main = benchmark.c_b(ds_main)
        specs = [("main", ds_main, self.KB, cb_main)]
        for k in (1.0, 1.5, 2.0):
            specs.append((f"k={k:g}", ds_main, k, cb_main))
        for perc in ("median", "p90"):
            specs.append((f"kb_{perc}", ds_main, self.kbs[kb_key(perc)].value,
                          benchmark.c_b(ds_main, perc)))
        ds_reg = self.DS[(MAIN_YEAR, EB, REG)]
        specs.append((SPEC_REG, ds_reg, self.KB, benchmark.c_b(ds_reg)))
        self.scen = {}
        for name, ds, k, cb in specs:
            s = priority.scenario(ds, ps, k, cb)
            self.scen[name] = s
            m, lo, hi = s["national"]
            common = {"spec": name, "year": MAIN_YEAR, "k": k, "c_b": cb,
                      "note": SCENARIO_LABEL}
            rows.append({**common, "row": "national", "unit": "", "mean": m, "lo": lo,
                         "hi": hi, "n_units": len(s["units"]), "excluded_units": s["excluded"],
                         "top5": s["top5"]})
            rows.append({**common, "row": "top5_share", "unit": "", "mean": s["share"],
                         "lo": s["share_lo"], "hi": s["share_hi"], "top5": s["top5"],
                         "n_undefined": s["share_n_undefined"]})
            for u in s["units"]:
                m, lo, hi = gaps.summarise(s["A"][u])
                rows.append({**common, "row": "unit", "unit": u, "mean": m, "lo": lo,
                             "hi": hi, "in_top5": u in s["top5"]})
        self.out["scenario"] = rows

    def headline_rows(self):
        ps, psimple = self.P[SEX], self.P[SIMPLE]
        hs = []  # headline_sensitivity
        # H1
        d = validate.h1_data(self.pan, ps)
        f = validate.fit_h1(d)
        boot = validate.bootstrap(d)
        entries = validate.grid(self.pan, {SEX: ps, SIMPLE: psimple})
        main_e = [e for e in entries if e["reference"] == SEX
                  and e["year_set"] == validate.MAIN_YEAR_SET and e["weights"] == validate.TESTED]
        assert len(main_e) == 1 and main_e[0]["beta1"] == f.b1
        lab, n_agree = validate.label((boot["lo"], boot["hi"]), entries, f.b1)
        ms = validate.tbv.sign(f.b1)
        for e in entries:
            e["is_main"] = e is main_e[0]
            e["agrees_with_main"] = e["sign"] is not None and e["sign"] == ms and ms in (1, -1)
        self.out["spec_curve"] = entries
        self.h1 = {"fit": f, "boot": boot, "data": d, "label": lab, "n_agree": n_agree}
        kish = validate.kish(d)
        se, wlo, whi = f.wald()
        head = [{"estimate": "H1", "value": f.b1, "lo": boot["lo"], "hi": boot["hi"],
                 "null": 0.0, "n": len(d.units), "n_grid": len(entries), "n_agree": n_agree,
                 "label": lab}]
        hs += [
            {"estimate": "H1_n_obs", "spec": "main", "value": len(d.y)},
            {"estimate": "H1_kish_effective_clusters", "spec": "main", "value": kish},
            {"estimate": "H1_one_inside_interval", "spec": "main",
             "value": boot["lo"] <= 1.0 <= boot["hi"]},
            {"estimate": "H1_bootstrap_discarded", "spec": "main",
             "value": boot["n_discarded"], "n": boot["n_boot"]},
            {"estimate": "H1_beta0", "spec": "main", "value": float(f.beta[0])},
            {"estimate": "H1_gamma_2021", "spec": "main", "value": float(f.beta[2])},
            {"estimate": "H1_pearson_phi", "spec": "main", "value": f.phi},
            {"estimate": "H1_wald_interval", "spec": "main", "value": f.b1, "lo": wlo,
             "hi": whi, "note": "model-based Wald, descriptive; not used for the label"},
            {"estimate": "H1_iterations", "spec": "main", "value": f.iterations},
        ]
        for factor in (0.8, 1.2):
            fs = validate.fit_h1(validate.h1_data(self.pan, reference.scaled(ps, factor)))
            hs.append({"estimate": "H1_point_nfhs_scaled", "spec": f"p_x{factor:g}",
                       "value": fs.b1})
        sp_specs = [("sex_weighted 2019+2021", ps, (2019, 2021)),
                    ("simple 2019+2021", psimple, (2019, 2021)),
                    ("sex_weighted 2021+2022 (fixed H1 years)", ps, (2021, 2022))]
        self.spearman = {}
        for name, p, yrs in sp_specs:
            s = validate.spearman_pooled(self.pan, p, yrs)
            self.spearman[name] = s
            hs.append({"estimate": "H1_spearman_fieller", "spec": name, "value": s["rho"],
                       "lo": s["lo"], "hi": s["hi"], "n": s["n"]})
        # H2
        nat = {b: {t: cascade.national(pan, t) for t in panel.YEARS}
               for b, pan in self.panels.items()}
        self.nat = nat

        def wil(b, t):
            v = nat[b][t]["C1"]
            return v["value"], v["lo"], v["hi"]

        dd, dlo, dhi = cascade.newcombe(wil(MAIN, 2018), wil(MAIN, 2022))
        head.append({"estimate": "H2", "value": dd, "lo": dlo, "hi": dhi, "null": None,
                     "n": f"2018:{nat[MAIN][2018]['C1']['units']};"
                          f"2022:{nat[MAIN][2022]['C1']['units']}",
                     "label": None})
        for b in (MAIN, REG, FROM):
            years = panel.YEARS if b == MAIN else panel.BASIS_YEARS[b]
            for t in years:
                c, lo, hi = wil(b, t)
                hs.append({"estimate": "H2_national_coverage", "spec": BASIS_SPEC.get(b, MAIN),
                           "year": t, "value": c, "lo": lo, "hi": hi,
                           "n": nat[b][t]["C1"]["units"],
                           "note": f"K={nat[b][t]['C1']['x']}; N={nat[b][t]['C1']['n']}"})
        for b, (t1, t2) in ((MAIN, (2018, 2022)), (MAIN, (2019, 2022)), (MAIN, (2018, 2023)),
                            (REG, (2018, 2022)), (FROM, (2018, 2022))):
            dd, dlo, dhi = cascade.newcombe(wil(b, t1), wil(b, t2))
            hs.append({"estimate": "H2_difference", "spec": BASIS_SPEC.get(b, MAIN),
                       "year": f"{t2} vs {t1}", "value": dd, "lo": dlo, "hi": dhi,
                       "note": "Newcombe hybrid score"})
        # H3
        jeff23 = self.DS[(MAIN_YEAR, JEFFREYS, MAIN)]
        h3_units = validate.below_units(jeff23, {u: self.KB * ps[u] for u in panel.UNITS})
        self.h3_units = h3_units
        head.append({"estimate": "H3", "value": len(h3_units), "lo": None, "hi": None,
                     "null": None, "n": len(jeff23.units_y), "label": None})
        kbm = self.kbs[kb_key()]
        constructed = [u for u in kbm.units if kbm.g[u] < kbm.value]
        hs.append({"estimate": "H3_by_construction_pool_g_below_kb", "spec": "main",
                   "year": "2021+2022", "value": len(constructed), "n": len(kbm.units),
                   "units": constructed})
        hs.append({"estimate": "H3_units", "spec": "main", "year": MAIN_YEAR,
                   "value": len(h3_units), "n": len(jeff23.units_y), "units": h3_units})
        count_specs = [("k_b (main)", self.KB, ps), ("k=1", 1.0, ps), ("k=1.5", 1.5, ps),
                       ("k=2", 2.0, ps), ("kb_median", self.kbs[kb_key("median")].value, ps),
                       ("kb_p90", self.kbs[kb_key("p90")].value, ps),
                       ("kb_pool_2019+2021",
                        self.kbs[kb_key(pool=benchmark.POOL_ALT)].value, ps),
                       ("shrinkage_off k_b", self.kbs[kb_key(prior=JEFFREYS)].value, ps),
                       ("reference_simple k_b", self.kbs[kb_key(ref=SIMPLE)].value, psimple),
                       ("reference_simple k=1", 1.0, psimple)]
        for factor in (0.8, 1.2):
            for k in (1.0, 1.5, 2.0):
                count_specs.append((f"p_x{factor:g} k={k:g}", k,
                                    reference.scaled(ps, factor)))
        for t in panel.YEARS:
            jeff = self.DS[(t, JEFFREYS, MAIN)]
            for name, k, p in count_specs:
                kp = {u: k * p[u] for u in panel.UNITS}
                below = validate.below_units(jeff, kp)
                fixed = validate.fixed_rule_units(jeff, kp)
                in_pool = " (in-sample: a k_b pool year)" if t in benchmark.POOL_MAIN else ""
                hs.append({"estimate": "count_P(R<1)>=0.95", "spec": name, "year": t,
                           "value": len(below), "n": len(jeff.units_y), "units": below,
                           "note": "below the benchmark at k_b" + in_pool
                           if "k_b" in name or name.startswith("kb_") else
                           "P(R_k < 1) >= 0.95 at a fixed k"})
                hs.append({"estimate": "count_fixed_rule_R97.5<1", "spec": name, "year": t,
                           "value": len(fixed), "n": len(jeff.units_y), "units": fixed,
                           "note": "likely under-detection" if name == "k=1" else
                           "the fixed rule as a sensitivity (no phrase)"})
        # trend summaries
        for model in sorted(self.phis):
            rows_m = [r for r in self.trend_rows if r["model"] == model]
            hs.append({"estimate": "trend_falling_count", "spec": model,
                       "value": sum(1 for r in rows_m if r.get("falling_coverage")),
                       "n": sum(1 for r in rows_m if r["status"] == "estimated"),
                       "units": [r["unit"] for r in rows_m if r.get("falling_coverage")]})
            hs.append({"estimate": "trend_flag_differs_from_main", "spec": model,
                       "value": sum(1 for r in rows_m if r["falling_differs_from_main"]),
                       "units": [r["unit"] for r in rows_m if r["falling_differs_from_main"]]})
            hs.append({"estimate": "trend_phi", "spec": model, "value": self.phis[model]})
        self.out["headline"] = head
        self.hs = hs

    def funnel_rows(self):
        ps = self.P[SEX]
        f23 = validate.fit_h1(validate.h1_data(self.pan, ps, "2023", validate.TESTED))
        rows = validate.funnel(self.pan, ps, f23, 2023, (), "2023 alone regression")
        for t in (2019, 2021):
            rows += validate.funnel(self.pan, ps, self.h1["fit"], t, (2021,),
                                    "main H1 fit (2019+2021)")
        self.out["funnel"] = rows

    def perturbation_rows(self):
        ps = self.P[SEX]
        units = list(panel.UNITS)
        ds = self.DS[(MAIN_YEAR, EB, MAIN)]
        jeff = self.DS[(MAIN_YEAR, JEFFREYS, MAIN)]
        yhat = self.kbs[kb_key()].yhat

        def state(p, kb):
            g = gaps.draw_gaps(ds, p, kb)
            tiers = {gap: {u: r["tier"] for u, r in priority.run(g[gap]).items()}
                     for gap in ("E1", "E2", "total")}
            h3 = set(validate.below_units(jeff, {u: kb * p[u] for u in units}))
            cls = {u: priority.classify(*priority.share_probs(g["E1"][u], g["E2"][u])[:3])
                   for u in g["total"]}
            return tiers, h3, cls

        base_t, base_h3, base_c = state(ps, self.KB)
        rng = np.random.default_rng(SEED)
        Z = rng.normal(0.0, SD_PERTURB, size=(N_PERTURB, len(units)))
        same_t = {gap: {u: 0 for u in units} for gap in base_t}
        same_h3 = {u: 0 for u in units}
        same_c = {u: 0 for u in units}
        kb_rep = np.empty(N_PERTURB)
        for i in range(N_PERTURB):
            p = {u: ps[u] * float(np.exp(Z[i, j])) for j, u in enumerate(units)}
            kb = benchmark.k_b_from_yhat(yhat, p)
            kb_rep[i] = kb
            t_, h3, c_ = state(p, kb)
            for gap in base_t:
                for u in base_t[gap]:
                    same_t[gap][u] += t_[gap].get(u) == base_t[gap][u]
            for u in units:
                same_h3[u] += (u in h3) == (u in base_h3)
                if u in base_c:
                    same_c[u] += c_.get(u) == base_c[u]
        rows = []
        for u in units:
            r = {"unit": u, "n_replicates": N_PERTURB}
            for gap in ("E1", "E2", "total"):
                if u in base_t[gap]:
                    r[f"tier_{gap}"] = base_t[gap][u]
                    r[f"share_tier_{gap}_unchanged"] = same_t[gap][u] / N_PERTURB
            r["h3_member"] = u in base_h3
            r["share_h3_unchanged"] = same_h3[u] / N_PERTURB
            if u in base_c:
                r["class"] = base_c[u]
                r["share_class_unchanged"] = same_c[u] / N_PERTURB
            rows.append(r)
        self.out["perturbation"] = rows
        lo, hi = np.percentile(kb_rep, [2.5, 97.5], method="linear")
        self.hs.append({"estimate": "perturbation_k_b_replicates", "spec": "sd=0.10",
                        "year": MAIN_YEAR, "value": float(kb_rep.mean()), "lo": float(lo),
                        "hi": float(hi), "n": N_PERTURB})

    def loo_rows(self):
        ps = self.P[SEX]
        rows = []
        d = self.h1["data"]
        vals = {}
        for u in d.units:
            try:
                vals[u] = validate.fit_h1(validate.h1_data(self.pan, ps, omit=u)).b1
            except validate.Undefined:
                vals[u] = None
            rows.append({"kind": "H1_beta1", "year": "2019+2021", "omitted": u,
                         "value": vals[u]})
        ok = {u: v for u, v in vals.items() if v is not None}
        umin = min(ok, key=lambda u: (ok[u], u))
        umax = max(ok, key=lambda u: (ok[u], u))
        rows.append({"kind": "H1_beta1_min", "omitted": umin, "value": ok[umin]})
        rows.append({"kind": "H1_beta1_max", "omitted": umax, "value": ok[umax]})
        main_sp = self.spearman["sex_weighted 2019+2021"]
        sv = {}
        for u in main_sp["units"]:
            s = validate.spearman_pooled(self.pan, ps, (2019, 2021), omit=u)
            sv[u] = s["rho"]
            rows.append({"kind": "spearman_rho", "year": "2019+2021", "omitted": u,
                         "value": s["rho"], "lo": s["lo"], "hi": s["hi"], "n": s["n"]})
        ok = {u: v for u, v in sv.items() if v is not None}
        umin = min(ok, key=lambda u: (ok[u], u))
        umax = max(ok, key=lambda u: (ok[u], u))
        rows.append({"kind": "spearman_rho_min", "omitted": umin, "value": ok[umin]})
        rows.append({"kind": "spearman_rho_max", "omitted": umax, "value": ok[umax]})
        for t in LOO_YEARS:
            base = {gap: priority.act_now(priority.run(self.main_draws[t][gap]))
                    for gap in ("E1", "E2")}
            changes = {gap: {} for gap in base}
            for o in panel.UNITS:
                kb_o = benchmark.k_b(self.pan, ps, omit=o).value
                ds_o = draws.build(self.pan, t, EB, MAIN, omit=o)
                g = gaps.draw_gaps(ds_o, ps, kb_o)
                for gap in base:
                    act = priority.act_now(priority.run(g[gap]))
                    remaining = set(g[gap])
                    changed = sorted((act ^ (base[gap] - {o})) & remaining)
                    changes[gap][o] = changed
                    rows.append({"kind": f"act_now_{gap}", "year": t, "omitted": o,
                                 "k_b": kb_o, "value": len(changed), "changed_units": changed,
                                 "act_now": sorted(act)})
            for gap in base:
                mx = max(len(v) for v in changes[gap].values())
                who = [o for o in panel.UNITS if len(changes[gap][o]) == mx]
                rows.append({"kind": f"act_now_{gap}_max_changes", "year": t,
                             "omitted": who, "value": mx,
                             "act_now": sorted(base[gap])})
        self.out["leave_one_out"] = rows

    def na_rows(self):
        rows = []
        for r in self.rows:
            if r["flag"]:
                rows.append({"spec": "main", "unit": r["unit"], "year": r["year"],
                             "measure": r["measure"], "value": r["value"], "kind": "flag",
                             "reason": r["flag"], "source_file": r["source_file"],
                             "pdf_page": r["pdf_page"], "table_id": r["table_id"]})
        for b, brows in self.basis_rows.items():
            for r in brows:
                rows.append({"spec": BASIS_SPEC[b], "unit": r["unit"], "year": r["year"],
                             "measure": r["measure"], "value": r["value"], "kind": "flag",
                             "reason": r["flag"], "source_file": r["source_file"],
                             "pdf_page": r["pdf_page"], "table_id": r["table_id"]})
        for b, pan in self.panels.items():
            years = panel.YEARS if b == MAIN else panel.BASIS_YEARS[b]
            for u in panel.UNITS:
                for t in years:
                    c = pan[(u, t)]
                    for q, reason in (("C1", c.c1_reason()), ("y", c.y_reason()),
                                      ("C3", c.c3_reason())):
                        if reason:
                            rows.append({"spec": BASIS_SPEC.get(b, "main"), "unit": u,
                                         "year": t, "measure": q, "kind": "NA",
                                         "reason": reason})
        for (t, prior, b), ds in sorted(self.DS.items(), key=lambda kv: (kv[0][2], kv[0][0],
                                                                         kv[0][1])):
            for fl in ds.flags:
                rows.append({"spec": BASIS_SPEC.get(b, "main"), "unit": "", "year": t,
                             "measure": prior, "kind": "flag", "reason": fl})
            if ds.no_screening_gap:
                rows.append({"spec": BASIS_SPEC.get(b, "main"), "unit": "", "year": t,
                             "measure": prior, "kind": "flag",
                             "reason": "no screening gap (sum U = 0)"})
        for key, kb in self.kbs.items():
            for u in kb.excluded:
                rows.append({"spec": f"k_b {key[0]} {pool_name(key[1])} {key[2]} {key[3]}",
                             "unit": u, "kind": "excluded_from_k_b_pool",
                             "reason": "y NA in a pool year"})
        self.out["na_cells"] = rows

    def write(self, out: Path):
        self.out["trend"] = self.trend_rows
        self.out["headline_sensitivity"] = self.hs
        cols = {
            "headline": ["estimate", "value", "lo", "hi", "null", "n", "n_grid", "n_agree",
                         "label"],
            "headline_sensitivity": ["estimate", "spec", "year", "value", "lo", "hi", "n",
                                     "units", "note"],
            "gaps": ["unit", "year", "gap", "spec", "k", "point", "mean", "lo", "hi",
                     "per_100k_notified"],
            "priority": ["unit", "year", "gap", "spec", "mean", "lo", "hi",
                         "per_100k_notified", "p_top5", "tier", "falling_coverage"],
            "trend": ["unit", "model", "years", "n_years", "indicator", "slope", "se", "lo",
                      "hi", "phi", "falling_coverage", "status", "falling_differs_from_main"],
        }
        paths = []
        for name in sorted(self.out):
            paths.append(table.write(out / f"{name}.csv", self.out[name], cols.get(name)))
        return paths

    def run(self, out: Path):
        self.reference_rows()
        self.benchmark_rows()
        self.cascade_rows()
        self.gaps_priority()
        self.decomposition_rows()
        self.scenario_rows()
        self.headline_rows()
        self.funnel_rows()
        self.perturbation_rows()
        self.loo_rows()
        self.na_rows()
        return self.write(out)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Run the registered analysis (Task 4).")
    ap.add_argument("--out", type=Path, default=OUT, help="output directory")
    args = ap.parse_args(argv)
    a = Analysis()
    for p in a.run(args.out):
        print(f"wrote {p.name}")
    print(f"tbprio {a.version}; seed {SEED}; {N_DRAWS} draws; k_b = {a.KB!r}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
