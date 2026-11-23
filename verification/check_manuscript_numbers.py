# Adapted from hssling/india-tb-priority-tool v1.0.1 (MIT), verification/check_manuscript_numbers.py
# (itself adapted from hssling/india-tb-acf-campaign and hssling/india-state-tb-score); modified:
# the catalogue of this paper (the cascade, the gaps and tiers, the decomposition, the headline
# estimates, the funnel, the scenario and the sensitivities from outputs/; registration and plan
# constants from docs/), a single-anonymized manuscript that carries its title page, a structured
# abstract of at most 200 words, a main text of at most 3,000 words, at most five display items,
# and this paper's wording rules (identified, never newly diagnosed alone; tiers, not ranks).
"""Check every number in the manuscript against the committed outputs.

Run as: python -I verification/check_manuscript_numbers.py [--manuscript-dir DIR] [--regenerate]

The manuscript folder (default manuscript/; git-ignored, kept private, not in this repository)
holds manuscript.md (the manuscript, title-page block included: the journal's review is single
anonymized), highlights.md, title_page_src.md, cover_letter.md, section_phrases.json,
number_skeleton.json and exhibits/. A relative DIR is taken from the repository root. When the
folder or its manuscript.md is absent this prints "SKIPPED: ..." and exits 0 (a fresh clone);
check_all then counts the step as skipped. If manuscript.md is present without
section_phrases.json (or the reverse) the check FAILS.

Checks (each section's text with its whitespace collapsed; the References are excluded from 1-3):

1. Section phrases. section_phrases.json lists, for each section ("Title", "Abstract", the "## "
   headings, "Highlights"), phrases with {label} placeholders. Each label is a catalogue value
   (catalogue(): from outputs/, docs/registration_event.json and the registered plan, formatted
   by exhibits/formats.py). Every filled phrase must occur whole in its own section.
2. Every number is accounted for: by a phrase placeholder or a FIXED pattern (exhibit names,
   step and hypothesis names, years, catalogue dates, reference numbers, plan sections, formula
   constants). A token with no label is UNACCOUNTED.
3. The golden skeleton (number_skeleton.json): each section's ordered tokens and labels of the
   reviewed text. Regenerate only after review: ... --regenerate
4. Claims stated in words (claims()), re-tested on the outputs.
5. Exhibits: Table 1 and Figures 1-4 cited in order, at most five display items, a caption for
   each figure; Tables S1-S13 exist and are first cited in order. exhibits/tables.md, each
   figureN_data.csv and graphical_abstract_data.csv equal what the exhibit scripts produce now.
6. References (Elsevier numbered style): [n], [n,m], [n–m]; every number in range; every
   reference cited; numbered in order of first citation; at most 50; each with a DOI, an access
   date, or a [dataset] / [software] tag.
7. Lengths: highlights 3 to 5 bullets of at most 85 characters; a structured abstract (Aims,
   Methods, Results, Conclusions) of at most 200 words, without citations; 1 to 7 keywords; the
   main text (Introduction to Discussion, headings excluded) at most 3,000 words.
8. Title page and wording: the manuscript names the author, the affiliation and the e-mail, and
   its title, author and corresponding-author lines equal those of title_page_src.md; the AI
   declaration is the same in both; no internal identifiers; British spelling; "identified",
   never "newly diagnosed" alone; "likely under-detection" only with k = 1; no causal, ranking
   or blaming language; "identification-led", never "detection-led"; H1's label as in
   outputs/headline.csv. Private caveats (section_phrases.json "caveats") occur whole. The
   cover letter names every related manuscript listed in section_phrases.json "cover_letter".

Exit 1 on any problem.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from exhibits.formats import (MINUS, MONTHS, NATIONAL, about_thousands, and_list, count, day,  # noqa: E402
                              ijtld_style, num, one, patients, pct, ratio, read_csv, rng, state_rows)
from verification import ijtld  # noqa: E402

DEFAULT_MS_DIR = "manuscript"
MS_NAME = "manuscript.md"
PHRASES = "section_phrases.json"
SKELETON = "number_skeleton.json"
HIGHLIGHTS = "highlights.md"
TITLE_PAGE = "title_page_src.md"
COVER = "cover_letter.md"
LIMITS = {"abstract": 200, "main": 3000, "highlight_chars": 85, "references": 50, "display_items": 5}
MAIN_SECTIONS = ("Introduction", "Methods", "Results", "Discussion")
ABSTRACT_PARTS = ("Aims", "Methods", "Results", "Conclusions")
AI_HEADING = ("Declaration of generative AI and AI-assisted technologies in the manuscript preparation "
              "process")
YEAR = "2023"


# --------------------------------------------------------------------------------------
# The plan and the registration
# --------------------------------------------------------------------------------------
def plan_text(root: Path) -> str:
    return (root / "docs" / "analysis_plan.md").read_text(encoding="utf-8")


def plan_has(root: Path, s: str, where: str) -> str:
    """s, after confirming the registered plan states it (so the constant is the plan's)."""
    if s not in re.sub(r"\s+", " ", plan_text(root)):
        raise ValueError(f"the plan ({where}) does not state {s!r}")
    return s


# --------------------------------------------------------------------------------------
# Catalogue: label -> (text as printed, source)
# --------------------------------------------------------------------------------------
def catalogue(root: Path) -> dict[str, tuple[str, str]]:
    c: dict[str, tuple[str, str]] = {}

    def put(label: str, text: str, source: str) -> None:
        if label in c:
            raise ValueError(f"duplicate catalogue label {label}")
        c[label] = (text, source)

    # ---- registration and plan constants -------------------------------------------------
    reg = json.loads((root / "docs" / "registration_event.json").read_text(encoding="utf-8"))
    put("date.registration", day(reg["pushed_at"]), "docs/registration_event.json: pushed_at")
    put("reg.time", reg["pushed_at"][11:19] + " UTC", "docs/registration_event.json: pushed_at")
    put("reg.commit", reg["registered_commit"][:7], "docs/registration_event.json: registered_commit")
    plan_has(root, "21 November 2026", "header")
    put("plan.draws", plan_has(root, "10,000", "§1 notation, §5.3"), "docs/analysis_plan.md §5.3")
    for lab, s in (("t80", "0.80"), ("t50", "0.50"), ("t20", "0.20")):
        plan_has(root, f"P ≥ {s}" if lab == "t80" else f"{s} ≤ P", "§6.1")
        put(f"plan.{lab}", s, "docs/analysis_plan.md §6.1 tiers")
    put("plan.p95", plan_has(root, "0.95", "§5.6, §6.3"), "docs/analysis_plan.md §5.6 and §6.3")
    put("plan.half", plan_has(root, "0.5", "§6.3"), "docs/analysis_plan.md §6.3 (share 0.5)")
    plan_has(root, "k = 1, 1.5 and 2", "§5.2")
    put("plan.k1", "k = 1", "docs/analysis_plan.md §5.2, §5.6 (the fixed rule at k = 1)")
    put("plan.k_sens", "k = 1, 1.5 and 2", "docs/analysis_plan.md §5.2")
    put("plan.k_hi", "k = 1.5 and 2", "docs/analysis_plan.md §5.2 (sensitivities 1.5 and 2)")
    put("plan.agree", plan_has(root, "≥80%", "§8.9").replace("≥", ""), "docs/analysis_plan.md §8.9")
    put("plan.grid", plan_has(root, "12 entries", "§8.8").split()[0], "docs/analysis_plan.md §8.8")
    put("plan.z998", plan_has(root, "99.8%", "§8.5"), "docs/analysis_plan.md §8.5")
    put("plan.mgdl", plan_has(root, ">140 mg/dl", "§4.2").lstrip(">"), "docs/analysis_plan.md §4.2")
    put("plan.age", "aged " + plan_has(root, "15 years", "§4.2") + " and over", "docs/analysis_plan.md §4.2")
    put("plan.p75", plan_has(root, "75th percentile", "§5.2"), "docs/analysis_plan.md §5.2")
    put("plan.p90", plan_has(root, "90th percentile", "§5.2").replace(" ", "-"), "docs/analysis_plan.md §5.2")
    put("plan.p975", plan_has(root, "97.5th percentile", "§5.6"), "docs/analysis_plan.md §5.6")
    put("plan.replicates", plan_has(root, "1,000 replicates", "§8.11"), "docs/analysis_plan.md §8.11")
    put("plan.yield8", plan_has(root, "near 8%", "§11"), "docs/analysis_plan.md §11 (printed national yield near 8%)")
    put("lit.dm_range", "13% to 32%", "literature: abstracts of refs 8 (1,084 of 8,109, 13%) and 9 (298 of 920, 32.4%), "
        "via Crossref; ref 7 (25.3%) lies within")
    put("lit.kiefe", "10%", "literature: Kiefe et al. 1998, the achievable benchmark (top performers covering 10% of patients)")
    put("plan.top5", "five", plan_has(root, "P(top-5)", "§6.1") and "docs/analysis_plan.md §6.1 (top five)")

    # ---- the national cascade (outputs/cascade.csv, national rows) ------------------------
    ca = read_csv(root, "outputs/cascade.csv")
    nat = {r["year"]: r for r in ca if r["unit"] == NATIONAL and r["spec"] == "main"}
    for y, r in nat.items():
        put(f"nat.C1.{y}", pct(r["C1"]), f"outputs/cascade.csv: national {y} C1")
    ys = [float(r["y"]) for r in nat.values()]
    put("nat.y.range", f"between {pct(min(ys))} and {pct(max(ys))}", "outputs/cascade.csv: national y, min and max over years")
    n23 = nat[YEAR]
    put("nat.y", pct(n23["y"]), "outputs/cascade.csv: national 2023 y")
    put("nat.C3", pct(n23["C3"]), "outputs/cascade.csv: national 2023 C3")
    put("nat.D", count(n23["y_x"]), "outputs/cascade.csv: national 2023 D (y_x)")
    put("nat.I", count(n23["C3_x"]), "outputs/cascade.csv: national 2023 I (C3_x)")
    put("nat.notinit", count(int(n23["y_x"]) - int(n23["C3_x"])), "outputs/cascade.csv: national 2023 D - I")
    hs = read_csv(root, "outputs/headline_sensitivity.csv")
    hl = {r["estimate"]: r for r in read_csv(root, "outputs/headline.csv")}
    h2 = hl["H2"]
    put("H2", f"{num(100 * float(h2['value']), 2)} percentage points ({rng(num(100 * float(h2['lo']), 2), num(100 * float(h2['hi']), 2))})",
        "outputs/headline.csv: H2 value, lo, hi (x100)")

    # ---- the State cascade, 2023 ---------------------------------------------------------
    st = [r for r in state_rows(ca) if r["spec"] == "main" and r["year"] == YEAR]
    put("units", count(len(st)), "outputs/cascade.csv: units, main 2023")
    lo1 = min(st, key=lambda r: float(r["C1"]))
    hi1 = max(st, key=lambda r: float(r["C1"]))
    put("c1.min", f"{pct(lo1['C1'])} ({lo1['unit']})", "outputs/cascade.csv: 2023 lowest C1")
    put("c1.max", f"{pct(hi1['C1'])} ({hi1['unit']})", "outputs/cascade.csv: 2023 highest C1")
    put("c1.ge90", f"{count(sum(float(r['C1']) >= 0.9 for r in st))} of {count(len(st))}", "outputs/cascade.csv: 2023 C1 >= 0.90")
    c2 = [float(r["C2"]) for r in st]
    put("c1.thr", "90%", "fixed: the coverage threshold of the c1.ge90 count")
    put("c2.range", rng(ratio(min(c2)), ratio(max(c2))), "outputs/cascade.csv: 2023 C2 min and max")
    put("c2.above", count(sum(v >= 1 for v in c2)), "outputs/cascade.csv: 2023 C2 >= 1 (point)")
    lo3 = min(st, key=lambda r: float(r["C3"]))
    hi3 = max(st, key=lambda r: float(r["C3"]))
    put("c3.min", f"{pct(lo3['C3'])} ({lo3['unit']})", "outputs/cascade.csv: 2023 lowest C3")
    put("c3.max", f"{pct(hi3['C3'])} ({hi3['unit']})", "outputs/cascade.csv: 2023 highest C3")
    put("c3.lt50", count(sum(float(r["C3"]) < 0.5 for r in st)), "outputs/cascade.csv: 2023 C3 < 0.50")
    put("c3.thr", "50%", "fixed: the threshold of the c3.lt50 count")
    put("link.below", count(sum(r["linkage_below_benchmark"] == "True" for r in st)),
        "outputs/cascade.csv: 2023 linkage_below_benchmark")
    b = read_csv(root, "outputs/benchmark.csv")
    put("kb", ratio(one(b, "main k_b", kind="k_b", is_main="True")["value"], 3), "outputs/benchmark.csv: main k_b")
    put("cb", pct(one(b, "main c_b", kind="c_b", is_main="True")["value"]), "outputs/benchmark.csv: main c_b")

    # ---- headline estimates ---------------------------------------------------------------
    h1 = hl["H1"]
    put("H1.value", ratio(h1["value"]), "outputs/headline.csv: H1 value")
    put("H1.ci", rng(ratio(h1["lo"]), ratio(h1["hi"])), "outputs/headline.csv: H1 lo, hi")
    put("H1.agree", f"{count(h1['n_agree'])} of {count(h1['n_grid'])}", "outputs/headline.csv: H1 n_agree, n_grid")
    put("H1.label", h1["label"], "outputs/headline.csv: H1 label")
    h3 = hl["H3"]
    put("H3", f"{count(h3['value'])} of {count(h3['n'])}", "outputs/headline.csv: H3 value, n")
    pool = one(hs, "pool", estimate="H3_by_construction_pool_g_below_kb", spec="main")
    put("H3.pool", f"{count(pool['value'])} of {count(pool['n'])}", "outputs/headline_sensitivity.csv: H3 by construction")
    fx = one(hs, "k=1 2023", estimate="count_fixed_rule_R97.5<1", spec="k=1", year=YEAR)
    put("fixed.k1", f"{count(fx['value'])} of {count(fx['n'])}", "outputs/headline_sensitivity.csv: fixed rule k=1, 2023")
    hk = {k: one(hs, f"k={k}", estimate="count_P(R<1)>=0.95", spec=f"k={k}", year=YEAR) for k in ("1.5", "2")}
    put("H3.k15k2", f"{count(hk['1.5']['value'])} and {count(hk['2']['value'])}",
        "outputs/headline_sensitivity.csv: count_P(R<1)>=0.95 at k=1.5 and k=2, 2023")
    loo = read_csv(root, "outputs/leave_one_out.csv")
    put("H1.kish", num(one(hs, "kish", estimate="H1_kish_effective_clusters", spec="main")["value"], 1),
        "outputs/headline_sensitivity.csv: H1_kish_effective_clusters")
    put("H1.loo", rng(ratio(one(loo, "min", kind="H1_beta1_min")["value"]), ratio(one(loo, "max", kind="H1_beta1_max")["value"])),
        "outputs/leave_one_out.csv: H1_beta1_min, H1_beta1_max")
    sp = one(hs, "spearman", estimate="H1_spearman_fieller", spec="sex_weighted 2019+2021")
    put("H1.spearman", f"{ratio(sp['value'])} ({rng(ratio(sp['lo']), ratio(sp['hi']))})",
        "outputs/headline_sensitivity.csv: H1_spearman_fieller sex_weighted 2019+2021")

    # ---- gaps and tiers, 2023 --------------------------------------------------------------
    pr = [r for r in read_csv(root, "outputs/priority.csv") if r["year"] == YEAR]
    main = [r for r in pr if r["spec"] == "main"]
    for g in ("E1", "E2", "E3"):
        put(f"{g}.act", and_list(sorted(r["unit"] for r in main if r["gap"] == g and r["tier"] == "act now")),
            f"outputs/priority.csv: main 2023 {g} act now")
    for g in ("E1", "E2"):
        put(f"{g}.sum", count(sum(float(r["mean"]) for r in main if r["gap"] == g)), f"outputs/priority.csv: main 2023 {g} sum of mean")
    e2 = [r for r in main if r["gap"] == "E2"]
    act = sum(float(r["mean"]) for r in e2 if r["tier"] == "act now")
    tot = sum(float(r["mean"]) for r in e2)
    put("E2.act_share", f"{count(act)} of the {count(tot)} ({pct(act / tot)})", "outputs/priority.csv: main 2023 E2 act-now sum / total")
    big = max((r for r in main if r["gap"] == "E3"), key=lambda r: float(r["mean"]))
    put("E3.top", f"{big['unit']} alone accounting for {patients(big['mean'], big['lo'], big['hi'])}",
        "outputs/priority.csv: main 2023 largest E3 mean, lo, hi")
    t = sorted((r for r in main if r["gap"] == "total"), key=lambda r: -float(r["per_100k_notified"]))
    put("total.per100k", f"{t[0]['unit']} ({count(t[0]['per_100k_notified'])} per 100,000 notified) and {t[1]['unit']} "
        f"({count(t[1]['per_100k_notified'])})", "outputs/priority.csv: main 2023 total, two largest per_100k_notified")
    gj = one(main, "Gujarat total", unit="Gujarat", gap="total")
    put("gj.per100k", count(gj["per_100k_notified"]), "outputs/priority.csv: main 2023 Gujarat total per_100k_notified")
    reg = [r for r in pr if r["spec"] == "denominator_a1_2_registered" and r["gap"] == "E1" and r["tier"] == "act now"]
    m1 = {r["unit"] for r in main if r["gap"] == "E1" and r["tier"] == "act now"}
    r1 = {r["unit"] for r in reg}
    put("reg.E1swap", f"{and_list(sorted(r1 - m1))} in place of {and_list(sorted(m1 - r1))}",
        "outputs/priority.csv: E1 act now, Annexure 1.2 basis against main")

    # ---- decomposition ----------------------------------------------------------------------
    dc = [r for r in read_csv(root, "outputs/decomposition.csv") if r["spec"] == "main" and r["year"] == YEAR]
    n = {k: sum(r["class"] == k for r in dc) for k in ("identification-led", "screening-led", "mixed")}
    put("class.id", count(n["identification-led"]), "outputs/decomposition.csv: main 2023 identification-led")
    put("class.scr", count(n["screening-led"]), "outputs/decomposition.csv: main 2023 screening-led")
    put("class.mixed", count(n["mixed"]), "outputs/decomposition.csv: main 2023 mixed")

    # ---- scenario ------------------------------------------------------------------------------
    sc = read_csv(root, "outputs/scenario.csv")
    s = {k: one(sc, k, spec=k, row="national") for k in ("main", "k=1", "k=1.5", "k=2", "kb_median")}
    put("scen", patients(s["main"]["mean"], s["main"]["lo"], s["main"]["hi"]), "outputs/scenario.csv: main national")
    put("scen.top5", pct(one(sc, "top5", spec="main", row="top5_share")["mean"]), "outputs/scenario.csv: main top5_share")
    put("scen.k1", count(s["k=1"]["mean"]), "outputs/scenario.csv: k=1 national mean")
    put("scen.median", count(s["kb_median"]["mean"]), "outputs/scenario.csv: kb_median national mean")
    allnat = [float(r["mean"]) for r in sc if r["row"] == "national"]
    put("scen.range", rng(count(min(allnat)), count(max(allnat))), "outputs/scenario.csv: national mean, min and max over specs")
    put("scen.k15k2", f"{count(s['k=1.5']['mean'])} and {count(s['k=2']['mean'])}", "outputs/scenario.csv: k=1.5 and k=2 national")

    # ---- perturbation ---------------------------------------------------------------------------
    pt = read_csv(root, "outputs/perturbation.csv")
    cols = ("share_tier_E1_unchanged", "share_tier_E2_unchanged", "share_tier_total_unchanged", "share_h3_unchanged",
            "share_class_unchanged")
    ks = [sum(float(r[col]) >= 0.9 for r in pt) for col in cols]
    put("pert.thr", "90%", "fixed: the share threshold of the pert.range count")
    put("pert.range", f"between {count(min(ks))} and {count(max(ks))} of {count(len(pt))}",
        "outputs/perturbation.csv: units with each share >= 0.90, min and max over the five results")

    # ---- values written only in the IJTLD manuscript (manuscript/v2) ---------------------------
    put("lit.dm", "13–32%", "literature: abstracts of refs 8 (1,084 of 8,109, 13%) and 9 (298 of 920, 32.4%), via "
        "Crossref; ref 7 (25.3%) lies within")
    put("plan.k_words", "1, 1.5 and 2", "docs/analysis_plan.md §5.2 (k = 1, 1.5 and 2)")
    put("plan.k_lit", "1.5–2", "docs/analysis_plan.md §5.2 (literature ratios k = 1.5 and 2)")
    put("scen.about", about_thousands(s["main"]["mean"]), "outputs/scenario.csv: main national mean, nearest thousand")
    put("scen.choices", f"{about_thousands(min(allnat))}–{about_thousands(max(allnat))}",
        "outputs/scenario.csv: national mean, min and max over specs, nearest thousand")
    main_n = float(s["main"]["mean"])
    put("scen.fold", f"{round(float(s['k=1.5']['mean']) / main_n)}–{round(float(s['k=2']['mean']) / main_n)}-fold",
        "outputs/scenario.csv: k=1.5 and k=2 national mean over main, rounded")
    for g in ("E1", "E2", "E3"):
        top = sorted((r for r in main if r["gap"] == g), key=lambda r: -float(r["mean"]))[:5]
        put(f"{g}.big", f"{and_list([r['unit'] for r in top])} ({and_list([count(r['per_100k_notified']) for r in top])} "
            f"per 100,000 notified)", f"outputs/priority.csv: main 2023 {g}, five largest means, per_100k_notified")
    put("E3.top_n", f"{big['unit']} alone had {count(big['mean'])}", "outputs/priority.csv: main 2023 largest E3 mean")
    return c


def catalogue_for(root: Path, journal: str = "pcd") -> dict[str, tuple[str, str]]:
    """The catalogue as printed in the journal's style (IJTLD: no-break-space thousands, en-dash ranges)."""
    cat = catalogue_cached(root)
    if journal != "ijtld":
        return cat
    return {k: (ijtld_style(v), src) for k, (v, src) in cat.items()}


@lru_cache(maxsize=4)
def catalogue_cached(root: Path) -> dict[str, tuple[str, str]]:
    return catalogue(root)


# --------------------------------------------------------------------------------------
# Claims stated in words, re-tested on the outputs
# --------------------------------------------------------------------------------------
def claims(root: Path) -> list[str]:
    out: list[str] = []

    def need(ok: bool, msg: str) -> None:
        if not ok:
            out.append(f"CLAIM fails: {msg}")

    hl = {x["estimate"]: x for x in read_csv(root, "outputs/headline.csv")}
    need(hl["H1"]["label"] == "supported" and float(hl["H1"]["lo"]) > 0, "H1 is supported, its interval above 0")
    hs = read_csv(root, "outputs/headline_sensitivity.csv")
    need(one(hs, "H3 pool", estimate="H3_by_construction_pool_g_below_kb", spec="main")["value"] == hl["H3"]["value"],
         "H3 equals the by-construction count")
    b = read_csv(root, "outputs/benchmark.csv")
    need(float(one(b, "k_b", kind="k_b", is_main="True")["value"]) < 1, "the benchmark multiplier is below 1")
    sp = read_csv(root, "outputs/spec_curve.csv")
    need(all(float(x["beta1"]) > 0 for x in sp), "every H1 grid entry is positive")
    ca = read_csv(root, "outputs/cascade.csv")
    st = [r for r in state_rows(ca) if r["spec"] == "main" and r["year"] == YEAR]
    above = {r["unit"] for r in st if float(r["C2"]) >= 1}
    need({"Kerala", "Puducherry", "Tamil Nadu"} <= above, "Kerala, Puducherry and Tamil Nadu identify at or above the benchmark")
    for u in ("Gujarat", "Rajasthan", "Telangana"):
        r = one(st, u, unit=u)
        need(float(r["C1"]) >= 0.85 and float(r["C2"]) < 0.5, f"{u} screens most patients but identifies few (C2 < 0.5)")
    need(all(r["C3_linked_ncd_clinic_2018"] for r in ca if r["year"] == "2018" and r["spec"] == "main"),
         "2018 C3 is the linked-to-NCD-clinic definition")
    pr = [r for r in read_csv(root, "outputs/priority.csv") if r["year"] == YEAR and r["spec"] == "main"]
    need(all(r["tier"] in ("act now", "lower priority") for r in pr if r["gap"] in ("E1", "E2", "E3")),
         "no unit is probable priority or uncertain for E1, E2 or E3 in 2023")
    reg = [r for r in read_csv(root, "outputs/priority.csv") if r["year"] == YEAR and r["spec"] == "denominator_a1_2_registered"]
    a = {r["unit"] for r in pr if r["gap"] == "E2" and r["tier"] == "act now"}
    r2 = {r["unit"] for r in reg if r["gap"] == "E2" and r["tier"] == "act now"}
    need(a == r2, "the E2 act-now set is unchanged on the Annexure 1.2 basis")
    dc = [r for r in read_csv(root, "outputs/decomposition.csv") if r["spec"] == "main" and r["year"] == YEAR]
    need(all(r["small_total_shortfall"] == "True" for r in dc if r["class"] == "screening-led"),
         "every screening-led unit has a small total shortfall")
    c1 = {r["unit"]: float(r["C1"]) for r in st}
    hi = [r for r in dc if c1[r["unit"]] >= 0.9]
    need(sum(r["class"] == "identification-led" for r in hi) > len(hi) / 2,
         "where coverage is at least 90%, most units are identification-led")
    c2 = {r["unit"]: float(r["C2"]) for r in st}
    need({r["unit"] for r in dc if r["class"] == "screening-led"} == {u for u, v in c2.items() if v >= 1},
         "screening-led units are exactly those identifying at or above the benchmark")
    need(one(pr, "Gujarat total", unit="Gujarat", gap="total")["tier"] == "act now",
         "Gujarat is in the act-now tier for the total shortfall")
    pt = read_csv(root, "outputs/perturbation.csv")
    cols = ("share_tier_E1_unchanged", "share_tier_E2_unchanged", "share_tier_total_unchanged", "share_h3_unchanged",
            "share_class_unchanged")
    need(sum(all(float(r[c]) >= 0.9 for c in cols) for r in pt) == 21, "21 units keep all results in at least 90% of replicates")
    tr = read_csv(root, "outputs/trend.csv")
    need(not any(r["falling_coverage"] == "True" for r in tr), "no unit has falling coverage in any trend model")
    fu = read_csv(root, "outputs/funnel.csv")
    for y in ("2019", "2021", "2023"):
        need(one(fu, f"Gujarat {y}", unit="Gujarat", funnel_year=y)["position"] == "below the 99.8% limit",
             f"Gujarat lies below the 99.8% limit in {y}")
    need(one(fu, "Tamil Nadu 2019", unit="Tamil Nadu", funnel_year="2019")["position"] == "above the 99.8% limit",
         "Tamil Nadu lies above the 99.8% limit in 2019")
    for y in ("2021", "2023"):
        for u in ("Karnataka", "Tamil Nadu"):
            need(one(fu, f"{u} {y}", unit=u, funnel_year=y)["position"] == "above the 99.8% limit",
                 f"{u} lies above the 99.8% limit in {y}")
    need(not any(r["position"] == "below the 99.8% limit" and r["unit"] != "Gujarat" for r in fu),
         "Gujarat is the only unit below the 99.8% limit")
    need(all(float(r["p_top5"]) in (0.0, 1.0) for r in pr), "every 2023 P(top-5) is 0 or 1 (tiers = the five largest)")
    for g in ("E1", "E2", "E3"):
        rs = [r for r in pr if r["gap"] == g]
        top = {r["unit"] for r in sorted(rs, key=lambda r: -float(r["mean"]))[:5]}
        need(top == {r["unit"] for r in rs if r["tier"] == "act now"}, f"the {g} act-now tier is the five largest means")
    sc = read_csv(root, "outputs/scenario.csv")
    need(float(one(sc, "k=1.5", spec="k=1.5", row="national")["mean"]) > float(one(sc, "main", spec="main", row="national")["mean"]),
         "the scenario grows at the literature ratio 1.5")
    need(float(one(b, "c_b", kind="c_b", is_main="True")["value"]) > 0.95, "the benchmark coverage is above 95%")
    return out


# --------------------------------------------------------------------------------------
# Section phrases (private; read at run time from <folder>/section_phrases.json)
# --------------------------------------------------------------------------------------
def load_phrase_file(ms_dir: Path) -> dict:
    d = json.loads((ms_dir / PHRASES).read_text(encoding="utf-8"))
    secs = d.get("sections") if isinstance(d, dict) else None
    if not isinstance(secs, dict) or not secs or not all(
            isinstance(k, str) and isinstance(v, list) and all(isinstance(x, str) for x in v) for k, v in secs.items()):
        raise ValueError(f"{PHRASES}: 'sections' must map section names to lists of phrases")
    return d


def section_phrases(ms_dir: Path) -> dict[str, list[str]]:
    return load_phrase_file(ms_dir)["sections"]


# --------------------------------------------------------------------------------------
# Fixed (non-result) number patterns
# --------------------------------------------------------------------------------------
SUPPLEMENT = [f"S{k}" for k in range(1, 15)]
TABLES = [1]
FIGURES = [1, 2, 3, 4]
FIXED: list[tuple[str, str]] = [
    ("reference", r"\[\d+(?:[,–]\d+)*\]"),
    ("exhibit", r"\bTables? S\d{1,2}(?:(?:,| and| to|–) ?S\d{1,2})*\b"),
    ("exhibit", r"\b(?:Table|Fig\.)s? [1-4](?:(?:,| and| to) [1-4])*\b"),
    ("name", r"\b[CEH][1-3]\b|\bNFHS-[45]\b|\bHbA1c\b|\bP\(top-5\)|\bper 100,000\b|\bICMR-INDIAB-17\b"),
    ("ci_level", r"\b95%"),
    ("plan_section", r"\bplan sections? 12\.\d(?:–12\.\d)?\b"),
    ("formula", r"\bN\(1 − C1\)|\bC2 = y/\(k_b p_u\)|\bP\(C2 < 1\)|\bE1/\(E1 \+ E2\)|\bbelow 1\b|\bmax\(0,|\bexcluded 0\b|\bnear 0 or 1\b|\bk = 1\.5 and 2\b"),
    ("date", r"\b\d{1,2} (?:" + "|".join(MONTHS) + r") 20\d\d\b"),
    ("years", r"\b20(?:1[7-9]|2[0-6])–(?:20)?(?:1[7-9]|2[0-6])\b"),
    ("year", r"(?<![\d.,])20(?:1[7-9]|2[0-6])(?![\d]|[.,]\d)"),
    ("doi", r"10\.5281/zenodo\.(?:\d+|X+)"),
]
NUMBER = re.compile(r"\d+(?:[,\u00a0]\d{3}(?!\d))*(?:\.\d+)?")


def sections(text: str) -> dict[str, str]:
    """Heading -> whitespace-collapsed text: the title ("Title") and every '## ' section (its
    '### ' subsections included) but the References. The title-page block between the title and
    the Abstract is not a section (it holds the author's details, checked separately)."""
    out: dict[str, list[str]] = {}
    cur = None
    for ln in text.splitlines():
        if ln.startswith("# ") and not out:
            out["Title"] = [ln[2:]]
            cur = None
        elif ln.startswith("## "):
            cur = ln[3:].strip()
            out[cur] = []
        elif cur is not None:
            out[cur].append(ln)
    return {k: re.sub(r"[^\S\u00a0]+", " ", "\n".join(v)).strip() for k, v in out.items() if k != "References"}


def fill(template: str, cat: dict) -> tuple[str, list[tuple[int, int, str]]]:
    out, spans, pos = "", [], 0
    for m in re.finditer(r"\{([^}]+)\}", template):
        out += template[pos:m.start()]
        val = cat[m.group(1)][0]
        spans.append((len(out), len(out) + len(val), m.group(1)))
        out += val
        pos = m.end()
    return out + template[pos:], spans


def _occurrences(body: str, phrase: str) -> list[int]:
    before = r"(?<![\d.,−-])" if re.match(r"[\d−-]", phrase) else ""
    after = r"(?![\d]|[.,]\d)" if re.search(r"\d$", phrase) else ""
    pat = re.compile(before + re.escape(phrase) + after)
    return [m.start() for m in pat.finditer(body)]


def assign(name: str, body: str, cat: dict, required: list[str],
           fixed: list[tuple[str, str]] | None = None) -> tuple[list[dict], list[str]]:
    """Label every number token of one section; return (skeleton entries, problems)."""
    probs: list[str] = []
    labels: dict[int, tuple[str, str]] = {}
    toks = [(m.start(), m.end(), m.group()) for m in NUMBER.finditer(body)]
    for tpl in required:
        try:
            phrase, spans = fill(tpl, cat)
        except KeyError as e:
            probs.append(f"PHRASES in {name}: unknown label {e}")
            continue
        occ = _occurrences(body, phrase)
        if not occ:
            probs.append(f"MISSING in {name}: {phrase!r}")
            continue
        for at in occ:
            for s, e, _ in toks:
                for ps, pe, lab in spans:
                    if at + ps <= s and e <= at + pe and s not in labels:
                        labels[s] = (lab, cat[lab][1])
    dates = {v[0]: k for k, v in cat.items() if k.startswith("date.")}
    for kind, pat in (FIXED if fixed is None else fixed):
        for m in re.finditer(pat, body):
            for s, e, _ in toks:
                if m.start() <= s and e <= m.end() and s not in labels:
                    if kind == "date":
                        lab = dates.get(m.group())
                        if lab is None:
                            probs.append(f"DATE in {name} is not a catalogue date: {m.group()!r}")
                            continue
                        labels[s] = (lab, cat[lab][1])
                    else:
                        labels[s] = (f"fixed:{kind}", f"fixed {kind}: {m.group()}")
    entries = []
    for s, e, t in toks:
        if s not in labels:
            probs.append(f"UNACCOUNTED number in {name}: {t!r} in ...{body[max(0, s - 40):e + 20]}...")
            entries.append({"token": t, "label": "UNACCOUNTED", "source": ""})
        else:
            entries.append({"token": t, "label": labels[s][0], "source": labels[s][1]})
    return entries, probs


def all_sections(text: str, highlights: str | None) -> dict[str, str]:
    secs = sections(text)
    if highlights is not None:
        secs["Highlights"] = re.sub(r"\s+", " ", "\n".join(ln for ln in highlights.splitlines()
                                                           if not ln.startswith("#"))).strip()
    return secs


def skeleton(text: str, highlights: str | None, root: Path,
             required: dict[str, list[str]]) -> tuple[dict[str, list[dict]], list[str]]:
    cat = catalogue_cached(root)
    secs = all_sections(text, highlights)
    out, probs = {}, []
    for name in required:
        if name not in secs:
            probs.append(f"MISSING section {name!r}")
    for name, body in secs.items():
        entries, p = assign(name, body, cat, required.get(name, []))
        out[name] = entries
        probs += p
    return out, probs


def skeleton_problems(now: dict, gold: dict | None, root: Path, cat: dict | None = None) -> list[str]:
    if gold is None:
        return [f"{SKELETON} missing: after review run python -I verification/check_manuscript_numbers.py --regenerate"]
    cat = catalogue_cached(root) if cat is None else cat
    out = []
    for name in sorted(set(now) | set(gold)):
        a = [(x["token"], x["label"]) for x in gold.get(name, [])]
        b = [(x["token"], x["label"]) for x in now.get(name, [])]
        if a != b:
            k = next((i for i, (x, y) in enumerate(zip(a, b)) if x != y), min(len(a), len(b)))
            out.append(f"SKELETON {name}: entry {k + 1} is {b[k] if k < len(b) else '(none)'}, golden has "
                       f"{a[k] if k < len(a) else '(none)'} ({len(b)} tokens now, {len(a)} golden)")
        for x in gold.get(name, []):
            lab = x["label"]
            if lab.startswith("fixed:"):
                continue
            if lab not in cat:
                out.append(f"SKELETON {name}: golden label {lab} is not in the catalogue")
            elif x["token"] not in NUMBER.findall(cat[lab][0]):
                out.append(f"SKELETON {name}: golden token {x['token']!r} is no longer in {lab} = {cat[lab][0]!r}")
    return out


# --------------------------------------------------------------------------------------
# Exhibits: citations, captions, display items, and the regenerated tables and figure data
# --------------------------------------------------------------------------------------
def exhibit_problems(text: str) -> list[str]:
    secs = sections(text)
    body = " ".join(v for k, v in secs.items() if k not in ("Title", "Abstract", "Figure captions"))
    out = []
    for kind, want, pat in (("Table", TABLES, r"\bTables? ((?:[1-9](?:, | and | to )?)+)"),
                            ("Figure", FIGURES, r"\bFigs?\. ((?:[1-9](?:, | and | to )?)+)")):
        seen = []
        for m in re.finditer(pat, body):
            seen += [int(n) for n in re.findall(r"[1-9]", m.group(1))]
        first = list(dict.fromkeys(seen))
        if sorted(first) != want:
            out.append(f"EXHIBITS: {kind}s cited {first}, expected each of {want}")
        elif first != want:
            out.append(f"EXHIBITS: first citations of {kind}s out of order: {first}")
    if len(TABLES) + len(FIGURES) > LIMITS["display_items"]:
        out.append(f"EXHIBITS: {len(TABLES) + len(FIGURES)} display items, more than {LIMITS['display_items']}")
    sup: list[str] = []
    for m in re.finditer(r"\bTables? (S\d{1,2}(?:(?:,| and| to|–) ?S\d{1,2})*)", body):
        parts = re.findall(r"S(\d{1,2})", m.group(1))
        if re.search(r"(?: to|–) ?S", m.group(1)) and len(parts) == 2:
            parts = [str(k) for k in range(int(parts[0]), int(parts[1]) + 1)]
        for p in parts:
            s = f"S{p}"
            if s not in SUPPLEMENT:
                out.append(f"EXHIBITS: supplementary {s} does not exist")
            else:
                sup.append(s)
    first = list(dict.fromkeys(sup))
    if first != [s for s in SUPPLEMENT if s in first]:
        out.append(f"EXHIBITS: supplementary tables first cited out of order: {first}")
    never = [s for s in SUPPLEMENT if s not in first]
    if never:
        out.append(f"EXHIBITS: supplementary tables never cited: {never}")
    caps = secs.get("Figure captions", "")
    for n in FIGURES:
        if f"Fig. {n}." not in caps:
            out.append(f"EXHIBITS: no caption for Fig. {n}")
    return out


def regenerated_problems(ms_dir: Path, root: Path) -> list[str]:
    """tables.md and the figure and graphical-abstract data equal what the exhibit scripts
    produce from outputs/ now."""
    from exhibits import make_figures, make_graphical_abstract, make_tables
    out = []
    ex = ms_dir / "exhibits"
    p = ex / "tables.md"
    if not p.exists():
        return ["EXHIBITS: exhibits/tables.md missing (python -I exhibits/make_tables.py)"]
    if p.read_text(encoding="utf-8") != make_tables.render_md(make_tables.build(root)):
        out.append("EXHIBITS: exhibits/tables.md differs from the tables regenerated from outputs/")
    for k, fn in make_figures.FIGURES.items():
        q = ex / f"figure{k}_data.csv"
        if not q.exists() or q.read_bytes() != make_figures.data_csv(fn(root)):
            out.append(f"EXHIBITS: exhibits/figure{k}_data.csv differs from the data regenerated from outputs/")
    q = ex / "graphical_abstract_data.csv"
    if not q.exists() or q.read_bytes() != make_figures.data_csv(make_graphical_abstract.ga_data(root)):
        out.append("EXHIBITS: exhibits/graphical_abstract_data.csv differs from the data regenerated from outputs/")
    return out


# --------------------------------------------------------------------------------------
# References: Elsevier numbered style
# --------------------------------------------------------------------------------------
def ref_list(text: str) -> list[tuple[int, str]]:
    part = text.split("\n## References", 1)
    if len(part) != 2:
        return []
    body = part[1].split("\n## ", 1)[0]
    return [(int(m.group(1)), m.group(2)) for m in re.finditer(r"(?m)^\[(\d+)\] (.+)$", body)]


def citations(text: str) -> list[int]:
    body = text.split("\n## References", 1)[0]
    order: list[int] = []
    for m in re.finditer(r"\[(\d+(?:[,–]\d+)*)\]", body):
        for part in m.group(1).split(","):
            a, _, b = part.partition("–")
            order += list(range(int(a), int(b or a) + 1))
    return order


def reference_problems(text: str) -> list[str]:
    refs = ref_list(text)
    if not refs:
        return ["REFERENCES: no '## References' section with entries '[n] ...'"]
    n = len(refs)
    out = []
    if n > LIMITS["references"]:
        out.append(f"REFERENCES: {n} references, more than {LIMITS['references']}")
    if [k for k, _ in refs] != list(range(1, n + 1)):
        out.append("REFERENCES: list not numbered 1..n")
    order = citations(text)
    for k in sorted(set(order)):
        if not 1 <= k <= n:
            out.append(f"REFERENCES: citation {k} outside 1..{n}")
    first = list(dict.fromkeys(order))
    if first != sorted(first):
        out.append(f"REFERENCES: not numbered in order of first citation: {first}")
    never = sorted(set(range(1, n + 1)) - set(order))
    if never:
        out.append(f"REFERENCES: never cited: {never}")
    for k, e in refs:
        if "doi.org" not in e and "(accessed " not in e and "as described in" not in e:
            out.append(f"REFERENCES: [{k}] has neither a DOI nor an access date")
        if e.startswith(("[dataset]", "[software]")) and "doi.org/10.5281/zenodo." not in e:
            out.append(f"REFERENCES: [{k}] is a data or software reference without its Zenodo DOI")
    return out


# --------------------------------------------------------------------------------------
# Lengths: highlights, abstract, keywords, main text
# --------------------------------------------------------------------------------------
def words(s: str) -> int:
    return len(re.findall(r"\S+", re.sub(r"[*_#|]", " ", s)))


def bullets(highlights: str) -> list[str]:
    return [ln[2:].strip() for ln in highlights.splitlines() if ln.startswith("- ")]


def main_text(text: str) -> str:
    """Introduction to Discussion, '### ' headings excluded (the journal's 3,000-word count)."""
    out, keep = [], False
    for ln in text.splitlines():
        if ln.startswith("## "):
            keep = ln[3:].strip() in MAIN_SECTIONS
            continue
        if keep and not ln.startswith("#"):
            out.append(ln)
    return "\n".join(out)


def length_problems(text: str, highlights: str | None) -> list[str]:
    out = []
    secs = sections(text)
    ab = secs.get("Abstract", "")
    kw = re.search(r"\*\*Keywords:\*\* (.+)$", ab)
    abstract = ab[:kw.start()].strip() if kw else ab
    if words(abstract) > LIMITS["abstract"]:
        out.append(f"LENGTH: abstract {words(abstract)} words, limit {LIMITS['abstract']}")
    heads = re.findall(r"\*\*(\w+):\*\*", abstract)
    if heads != list(ABSTRACT_PARTS):
        out.append(f"LENGTH: abstract headings {heads}, expected {list(ABSTRACT_PARTS)}")
    if re.search(r"\[\d", abstract):
        out.append("LENGTH: the abstract cites a reference")
    if not kw:
        out.append("LENGTH: no '**Keywords:**' line at the end of the Abstract")
    else:
        k = [x.strip() for x in kw.group(1).split(";") if x.strip()]
        if not 1 <= len(k) <= 7:
            out.append(f"LENGTH: {len(k)} keywords (1 to 7 allowed)")
    for name in MAIN_SECTIONS:
        if name not in secs:
            out.append(f"LENGTH: no '## {name}' section")
    m = words(main_text(text))
    if m > LIMITS["main"]:
        out.append(f"LENGTH: main text {m} words (Introduction to Discussion, headings excluded), limit {LIMITS['main']}")
    if highlights is not None:
        b = bullets(highlights)
        if not 3 <= len(b) <= 5:
            out.append(f"HIGHLIGHTS: {len(b)} bullets (3 to 5 required)")
        for x in b:
            if len(x) > LIMITS["highlight_chars"]:
                out.append(f"HIGHLIGHTS: {len(x)} characters (limit {LIMITS['highlight_chars']}): {x!r}")
    return out


# --------------------------------------------------------------------------------------
# Title page, wording and labels
# --------------------------------------------------------------------------------------
BANNED = [
    (r"\bTask \d|\bfix round\b|\bcontroller\b|\bimplementer\b|\bdispatch", "drafting-process language"),
    (r"\bITR ?20\d\d\b|\bTBAR\b|\bA1\.\d|\bA2\.\d", "a shorthand source identifier"),
    (r"§", "a section sign (write 'plan section 12.1')"),
    (r"\b(?:outputs|data|verification|exhibits|src|docs)/\S+|\.py\b|\.csv\b", "a file path"),
    (r"\bbelow_benchmark\b|\bp_top5\b|\bdenominator_a1|\bkb_median\b|\bper_100k|\blikely_under_detection\b",
     "an internal variable name"),
]
WORDING = [
    (r"\bnewly diagnosed\b(?! or known| where reported)", "write 'identified' (newly diagnosed or known), never 'newly diagnosed' alone"),
    (r"\bdetection-led\b", "write 'identification-led'"),
    (r"\bwidespread\b", "H3 is never 'widespread'"),
    (r"\bcaus(?:ed|es|ing)\b|\bled to\b|\bresulted in\b|\bimpact of the programme\b|\bbecause of the programme\b",
     "causal language"),
    (r"\branked (?:first|second|third|\d)|\b(?:first|second|third|top)-ranked\b|\brank(?:ed|s)? (?:first|highest|lowest)\b"
     r"|\bnumber one\b|\bworst\b|\bbest[- ]performing\b|\bfailing\b|\bto blame\b", "ranking or blaming language"),
]
AMERICAN = [r"\banalyz", r"\bstandardiz", r"(?<!World Health )\borganiz", r"\bprogram\b(?! Planning)", r"\bprograms\b",
            r"\bcolor", r"\bcenters?\b", r"\bbehavior", r"\bmodeling\b", r"\blabeled\b", r"\bminimiz", r"\bprioritiz",
            r"\brecogniz", r"\butiliz", r"\bcategoriz", r"\bhospitaliz", r"\bemphasiz", r"\bfavor", r"\bjudgment",
            r"\bgeneraliz"]


def wording_problems(name: str, text: str) -> list[str]:
    out = []
    body = text.split("\n## References", 1)[0]
    if name == "exhibits/tables.md":
        body = "\n".join(ln for ln in body.splitlines() if not ln.startswith("# Tables (generated"))
    for pat, what in BANNED + WORDING:
        for m in re.finditer(pat, body, re.I if (pat, what) in WORDING else 0):
            out.append(f"WORDING in {name}: {what}: {m.group()!r}")
    for sent in re.split(r"(?<=[.;])\s+", re.sub(r"\s+", " ", body)):
        if re.search(r"under-detection", sent, re.I):
            if not re.search(r"likely under-detection", sent, re.I) or "k = 1" not in sent:
                out.append(f"WORDING in {name}: 'under-detection' only as 'likely under-detection' with k = 1: "
                           f"{sent[:120]!r}")
    for pat in AMERICAN:
        for m in re.finditer(pat, body, re.I):
            out.append(f"SPELLING in {name}: American form {m.group()!r}")
    return out


def label_problems(text: str, root: Path) -> list[str]:
    """H1's label is written exactly as in outputs/headline.csv wherever H1 is labelled."""
    hl = {x["estimate"]: x["label"] for x in read_csv(root, "outputs/headline.csv")}
    out = []
    body = text.split("\n## References", 1)[0]
    for m in re.finditer(r"\b(H1)\b[^\n]{0,200}?\b(supported|not established|established|confirmed|validated|proven)\b",
                         body):
        e, lab = m.group(1), m.group(2)
        if lab in ("established", "confirmed", "validated", "proven") or lab != hl[e]:
            out.append(f"LABEL: {e} written as {lab!r} in ...{m.group()[-80:]}...; outputs/headline.csv has {hl[e]!r}")
    for m in re.finditer(r"\b(H[23])\b[^.\n]{0,120}?\b(supported|not established|confirmed|validated)\b", body):
        out.append(f"LABEL: {m.group(1)} carries no label, but is written {m.group(2)!r}")
    return out


def front_line(text: str, key: str) -> str | None:
    hits = [ln for ln in text.splitlines() if ln.startswith(key)]
    return hits[0] if len(hits) == 1 else None


def title_page_problems(text: str, title_page: str) -> list[str]:
    """Single anonymized: the manuscript carries the title-page block, equal to title_page_src.md."""
    out = []
    head = text.split("\n## Abstract", 1)[0]
    title = text.splitlines()[0][2:].strip() if text.startswith("# ") else ""
    tp_title = (front_line(title_page, "**Title:**") or "").split(":**", 1)[-1].strip()
    if not title or title != tp_title:
        out.append("TITLE PAGE: the manuscript's title differs from title_page_src.md")
    for key in ("**Author:**", "**Corresponding author:**"):
        a, b = front_line(head, key), front_line(title_page, key)
        if a is None or a != b:
            out.append(f"TITLE PAGE: the manuscript's {key.strip('*:')} line is missing or differs from title_page_src.md")
    if not re.search(r"[\w.+-]+@[\w-]+\.[\w.]+", head):
        out.append("TITLE PAGE: the manuscript's title-page block has no e-mail address")
    if not re.search(r"\d{4}-\d{4}-\d{4}-\d{3}[\dX]", head):
        out.append("TITLE PAGE: the manuscript's title-page block has no ORCID")
    if "**Abbreviations:**" not in head:
        out.append("TITLE PAGE: no abbreviations footnote on the first page")
    return out


def declaration_problems(text: str, title_page: str) -> list[str]:
    ms = sections(text).get(AI_HEADING, "")
    m = re.search(r"\*\*" + re.escape(AI_HEADING) + r"\.?\*\* *(.+)", title_page)
    page = re.sub(r"\s+", " ", m.group(1)).strip() if m else ""
    if not ms or not page:
        return ["DECLARATION: the AI declaration is missing from the manuscript or the title page"]
    if ms != page:
        return ["DECLARATION: the AI declaration differs between the manuscript and the title page"]
    names = list(sections(text))
    refs_at = text.find("\n## References")
    ai_at = text.find("\n## " + AI_HEADING)
    out = []
    if not (0 <= ai_at < refs_at):
        out.append("DECLARATION: the AI declaration is not a section before the References")
    if "Declarations of interest: none" not in sections(text).get("Declarations of interest", ""):
        out.append("DECLARATION: the manuscript lacks 'Declarations of interest: none'")
    if "Acknowledgements" not in names or names.index("Acknowledgements") > names.index(AI_HEADING):
        out.append("DECLARATION: no Acknowledgements section before the AI declaration")
    return out


def cover_problems(cover: str | None, required: list[str]) -> list[str]:
    if cover is None:
        return [f"MISSING: {COVER}"]
    return [f"COVER LETTER: does not name the related manuscript {r!r}" for r in required if r not in cover]


def caveat_problems(text: str, caveats: dict[str, list[str]]) -> list[str]:
    secs = sections(text)
    return [f"CAVEAT missing in {name}: {c!r}" for name, cs in caveats.items() for c in cs
            if c not in secs.get(name, "")]


# --------------------------------------------------------------------------------------
# The IJTLD profile (manuscript/v2; verification/ijtld.py holds the journal's rules)
# --------------------------------------------------------------------------------------
NB = chr(0xa0)
FIXED_IJTLD: list[tuple[str, str]] = [
    ("reference", r"\^\d+(?:[,–]\d+)*\^"),
    ("online", r"\b(?:Tables?|Figures?) S\d{1,2}(?:(?:,| and|–) ?S\d{1,2})*\b"),
    ("exhibit", r"\bTable 1\b|\bFigures? [12](?: and [12])?\b"),
    ("name", r"\bH[1-3]\b|\bNFHS-5\b|\bHbA1c\b|\bper 100" + NB + r"000\b"),
    ("ci_level", r"\b95%"),
    ("plan_section", r"\bplan section 12\.\d\b"),
    ("formula", r"\b(?:below|above|of) 1\b|\bexcluded 0\b|\b0 or 1\b|\bone half\b"),
    ("date", r"\b\d{1,2} (?:" + "|".join(MONTHS) + r") 20\d\d\b"),
    ("years", r"\b20(?:1[7-9]|2[0-6])–(?:20)?(?:1[7-9]|2[0-6])\b"),
    ("year", r"(?<![\d.,])20(?:1[7-9]|2[0-6])(?![\d]|[.,]\d)"),
]
REF_DOIS = "reference_dois.json"


def journal_of(ms_dir: Path) -> str:
    """The folder's journal profile: section_phrases.json "journal" ("pcd" when absent)."""
    try:
        return load_phrase_file(ms_dir).get("journal", "pcd")
    except (OSError, ValueError):
        return "pcd"


def assign_ijtld(name: str, body: str, cat: dict, required: list[str]) -> tuple[list[dict], list[str]]:
    return assign(name, body, cat, required, FIXED_IJTLD)


def skeleton_ijtld(text: str, root: Path, required: dict[str, list[str]]) -> tuple[dict[str, list[dict]], list[str]]:
    cat = catalogue_for(root, "ijtld")
    secs = sections(text)
    out, probs = {}, []
    for name in required:
        if name not in secs:
            probs.append(f"MISSING section {name!r}")
    for name, body in secs.items():
        entries, p = assign_ijtld(name, body, cat, required.get(name, []))
        out[name] = entries
        probs += p
    return out, probs


def skeleton_problems_ijtld(now: dict, gold: dict | None, root: Path) -> list[str]:
    return skeleton_problems(now, gold, root, catalogue_for(root, "ijtld"))


def online_text(text: str) -> str:
    """The text with the online-material link removed (it is a URL, not a file path)."""
    return text.replace(ijtld.ONLINE_URL, "<online material>")


def exhibit_problems_ijtld(text: str, root: Path) -> list[str]:
    secs = sections(text)
    body = " ".join(v for k, v in secs.items() if k not in ("Title", "Abstract", "Figure legends"))
    out = []
    for kind, want, pat in (("Table", ijtld.TABLES, r"\bTables? ([1-9](?:(?:, | and )[1-9])*)\b(?! ?S)"),
                            ("Figure", ijtld.FIGURES, r"\bFigures? ([1-9](?:(?:, | and )[1-9])*)\b")):
        seen = []
        for m in re.finditer(pat, body):
            seen += [int(n) for n in re.findall(r"[1-9]", m.group(1))]
        first = list(dict.fromkeys(seen))
        if sorted(first) != want:
            out.append(f"EXHIBITS: {kind}s cited {first}, expected each of {want}")
        elif first != want:
            out.append(f"EXHIBITS: first citations of {kind}s out of order: {first}")
    n_disp = len(ijtld.TABLES) + len(ijtld.FIGURES)
    if n_disp > ijtld.LIMITS["display_items"]:
        out.append(f"EXHIBITS: {n_disp} display items, more than {ijtld.LIMITS['display_items']}")
    leg = secs.get("Figure legends", "")
    for n in ijtld.FIGURES:
        if f"Figure {n}." not in leg:
            out.append(f"EXHIBITS: no legend for Figure {n}")
    if re.search(r"\bFigure [3-9]\b|\bTable [2-9]\b", body + " " + leg):
        out.append("EXHIBITS: a display item beyond Table 1 and Figures 1 and 2 is cited")
    online = (root / "docs" / "online_material" / "tables.md")
    have = set(re.findall(r"(?m)^## Table (S\d+)\.", online.read_text(encoding="utf-8"))) if online.exists() else set()
    have |= {f"S{k}" for k in range(1, 10) if (root / "docs" / "online_material" / f"figureS{k}.pdf").exists()}
    for m in re.finditer(r"\b(Tables?|Figures?) (S\d{1,2}(?:(?:,| and|–) ?S\d{1,2})*)", body):
        parts = re.findall(r"S(\d{1,2})", m.group(2))
        if "–" in m.group(2) and len(parts) == 2:
            parts = [str(k) for k in range(int(parts[0]), int(parts[1]) + 1)]
        kind = "Table" if m.group(1).startswith("Table") else "Figure"
        allowed = ijtld.ONLINE_TABLES if kind == "Table" else ijtld.ONLINE_FIGURES
        for p in parts:
            if f"S{p}" not in allowed or (kind == "Table" and f"S{p}" not in have):
                out.append(f"EXHIBITS: online {kind} S{p} does not exist in docs/online_material")
    if ijtld.ONLINE_URL not in text:
        out.append(f"EXHIBITS: the text does not link the online material ({ijtld.ONLINE_URL})")
    if not re.search(r"online material", body):
        out.append("EXHIBITS: the text never cites the online material")
    return out


def regenerated_problems_ijtld(ms_dir: Path, root: Path) -> list[str]:
    from exhibits import make_figures, make_ijtld
    out = []
    ex = ms_dir / "exhibits"
    p = ex / "tables.md"
    if not p.exists() or p.read_text(encoding="utf-8") != make_ijtld.render(root):
        out.append("EXHIBITS: exhibits/tables.md differs from Table 1 regenerated from outputs/ (python -I exhibits/make_ijtld.py)")
    for k, fn in make_ijtld.FIGURES.items():
        q = ex / f"figure{k}_data.csv"
        if not q.exists() or q.read_bytes() != make_figures.data_csv(fn(root)):
            out.append(f"EXHIBITS: exhibits/figure{k}_data.csv differs from the data regenerated from outputs/")
    return out


def ref_list_ijtld(text: str) -> list[tuple[int, str]]:
    part = text.split("\n## References", 1)
    if len(part) != 2:
        return []
    body = part[1].split("\n## ", 1)[0]
    return [(int(m.group(1)), m.group(2).strip()) for m in ijtld.REF_LINE.finditer(body)]


def citations_ijtld(text: str) -> list[int]:
    body = text.split("\n## References", 1)[0]
    order: list[int] = []
    for m in ijtld.CITE.finditer(body):
        for part in m.group(1).split(","):
            a, _, b = part.partition("–")
            order += list(range(int(a), int(b or a) + 1))
    return order


def reference_dois(ms_dir: Path) -> dict[str, str]:
    p = ms_dir / REF_DOIS
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


def reference_problems_ijtld(text: str, ms_dir: Path) -> list[str]:
    refs = ref_list_ijtld(text)
    if not refs:
        return ["REFERENCES: no '## References' section with entries 'n\\. ...'"]
    n = len(refs)
    out = []
    if n > ijtld.LIMITS["references"]:
        out.append(f"REFERENCES: {n} references, more than {ijtld.LIMITS['references']}")
    if [k for k, _ in refs] != list(range(1, n + 1)):
        out.append("REFERENCES: list not numbered 1..n")
    order = citations_ijtld(text)
    for k in sorted(set(order)):
        if not 1 <= k <= n:
            out.append(f"REFERENCES: citation {k} outside 1..{n}")
    first = list(dict.fromkeys(order))
    if first != sorted(first):
        out.append(f"REFERENCES: not numbered in order of first citation: {first}")
    never = sorted(set(range(1, n + 1)) - set(order))
    if never:
        out.append(f"REFERENCES: never cited: {never}")
    if re.search(r"\[\d+(?:[,–]\d+)*\]", text.split("\n## References", 1)[0]):
        out.append("REFERENCES: a bracketed citation [n] (IJTLD uses superscript numbers)")
    dois = reference_dois(ms_dir)
    for k, e in refs:
        kind = ijtld.entry_kind(e)
        if kind == "unknown":
            out.append(f"REFERENCES: [{k}] is not in the journal's style (article, web page with access date, or Zenodo DOI)")
        if kind == "article" and str(k) not in dois:
            out.append(f"REFERENCES: [{k}] has no verified DOI in {REF_DOIS}")
        if kind == "zenodo" and not re.search(r"Version \d+\.\d+\.\d+ \[(?:dataset|software)\]", e):
            out.append(f"REFERENCES: [{k}] a data or software reference must name its version and [dataset] or [software]")
        if "doi.org" in e and kind != "zenodo":
            out.append(f"REFERENCES: [{k}] prints a DOI (the journal's style has none; it is kept in {REF_DOIS})")
        out += ijtld.author_problems(k, e)
    extra = sorted(set(dois) - {str(k) for k, e in refs if ijtld.entry_kind(e) == "article"}, key=int)
    if extra:
        out.append(f"REFERENCES: {REF_DOIS} holds DOIs for entries that are not articles: {extra}")
    return out


def abstract_ijtld(text: str) -> str:
    return sections(text).get("Abstract", "")


def length_problems_ijtld(text: str, title_page: str | None) -> list[str]:
    out = []
    ab = abstract_ijtld(text)
    if words(ab) > ijtld.LIMITS["abstract"]:
        out.append(f"LENGTH: abstract {words(ab)} words, limit {ijtld.LIMITS['abstract']}")
    heads = re.findall(r"\*\*(\w+):\*\*", ab)
    if heads != list(ijtld.ABSTRACT_PARTS):
        out.append(f"LENGTH: abstract headings {heads}, expected {list(ijtld.ABSTRACT_PARTS)}")
    if re.search(r"\^\d|\[\d", ab):
        out.append("LENGTH: the abstract cites a reference")
    ab_abbr = ijtld.abbreviations(ab)
    if ab_abbr:
        out.append(f"ABSTRACT: abbreviations {sorted(set(ab_abbr))} (none allowed)")
    for name in MAIN_SECTIONS:
        if name not in sections(text):
            out.append(f"LENGTH: no '## {name}' section")
    m = words(main_text(text))
    if m > ijtld.LIMITS["main"]:
        out.append(f"LENGTH: main text {m} words (Introduction to Discussion, headings excluded), limit {ijtld.LIMITS['main']}")
    title = text.splitlines()[0][2:].strip() if text.startswith("# ") else ""
    out += ijtld.title_problems(title)
    if title_page is not None:
        out += ijtld.running_head_problems(ijtld.field(title_page, "Running head") or "")
        out += ijtld.keyword_problems(ijtld.keywords_of(title_page), title)
    return out


TP_FIELDS = ("Title", "Running head", "Author", "Affiliation", "Corresponding author", "Keywords", "Word counts",
             "Acknowledgements", "Funding", "Conflicts of interest", "Ethics", "Data availability",
             "Use of artificial intelligence")


def title_page_problems_ijtld(text: str, title_page: str, n_refs: int) -> list[str]:
    out = []
    for f in TP_FIELDS:
        if ijtld.field(title_page, f) is None:
            out.append(f"TITLE PAGE: no single '**{f}:**' line in {TITLE_PAGE}")
    title = text.splitlines()[0][2:].strip() if text.startswith("# ") else ""
    if not title or title != (ijtld.field(title_page, "Title") or ""):
        out.append("TITLE PAGE: the manuscript's title differs from title_page_src.md")
    corr = ijtld.field(title_page, "Corresponding author") or ""
    if not re.search(r"[\w.+-]+@[\w-]+\.[\w.]+", corr) or "India" not in corr or not re.search(r"\b\d{6}\b", corr):
        out.append("TITLE PAGE: the corresponding author needs a full address (with postcode) and an e-mail")
    if not re.search(r"\d{4}-\d{4}-\d{4}-\d{3}[\dX]", corr):
        out.append("TITLE PAGE: the corresponding author has no ORCID")
    wc = ijtld.field(title_page, "Word counts") or ""
    for want in (f"references {n_refs}", f"tables {len(ijtld.TABLES)}", f"figures {len(ijtld.FIGURES)}"):
        if want not in wc:
            out.append(f"TITLE PAGE: the word-count line does not state {want!r}")
    if "10.5281/zenodo." not in (ijtld.field(title_page, "Data availability") or ""):
        out.append("TITLE PAGE: the data availability statement has no Zenodo DOI (or its placeholder)")
    if "Claude" not in (ijtld.field(title_page, "Use of artificial intelligence") or "") or "Claude" not in sections(text).get("Methods", ""):
        out.append("DECLARATION: the use of an AI assistant must be stated on the title page and in the Methods")
    return out


def wording_problems_ijtld(name: str, text: str) -> list[str]:
    body = online_text(text.split("\n## References", 1)[0])
    if name == "exhibits/tables.md":
        body = "\n".join(ln for ln in body.splitlines() if not ln.startswith("# Tables (generated"))
    out = wording_problems(name, body)
    out += [f"WORDING in {name}: {h}" for h in ijtld.wording_hits(body)]
    return out


def problems_ijtld(root: Path, ms_dir: Path, text: str, gold: dict | None, required: dict,
                   exhibits: bool = True) -> list[str]:
    pf = load_phrase_file(ms_dir)
    now, out = skeleton_ijtld(text, root, required)
    out += skeleton_problems_ijtld(now, gold, root)
    out += claims(root)
    out += exhibit_problems_ijtld(text, root)
    if exhibits:
        out += regenerated_problems_ijtld(ms_dir, root)
    caveats = pf.get("caveats", {})
    if not caveats:
        out.append(f"CAVEAT: no caveats listed in {PHRASES}")
    out += caveat_problems(text, caveats)
    out += reference_problems_ijtld(text, ms_dir)
    tp = read_opt(ms_dir, TITLE_PAGE)
    out += length_problems_ijtld(text, tp)
    out += label_problems(text, root)
    out += wording_problems_ijtld(MS_NAME, text)
    tables = read_opt(ms_dir, "exhibits/tables.md")
    if tables is not None:
        out += wording_problems_ijtld("exhibits/tables.md", tables)
    if tp is None:
        out.append(f"MISSING: {TITLE_PAGE}")
    else:
        out += wording_problems_ijtld(TITLE_PAGE, tp)
        out += title_page_problems_ijtld(text, tp, len(ref_list_ijtld(text)))
    cover = read_opt(ms_dir, COVER)
    out += cover_problems(cover, pf.get("cover_letter", []))
    if cover is not None:
        out += wording_problems_ijtld(COVER, cover)
    if not pf.get("cover_letter"):
        out.append(f"COVER LETTER: no related manuscripts listed in {PHRASES} 'cover_letter'")
    return out


# --------------------------------------------------------------------------------------
# Driver
# --------------------------------------------------------------------------------------
def manuscript_dir(root: Path, argv: list[str]) -> tuple[Path, list[str]]:
    ap = argparse.ArgumentParser(add_help=False, allow_abbrev=False)
    ap.add_argument("--manuscript-dir", default=DEFAULT_MS_DIR)
    a, rest = ap.parse_known_args(argv)
    d = Path(a.manuscript_dir)
    return (d if d.is_absolute() else root / d), rest


def rel(p: Path, root: Path) -> str:
    try:
        return p.relative_to(root).as_posix()
    except ValueError:
        return p.as_posix()


def load_gold(ms_dir: Path) -> dict | None:
    p = ms_dir / SKELETON
    return json.loads(p.read_text(encoding="utf-8"))["sections"] if p.exists() else None


def read_opt(ms_dir: Path, name: str) -> str | None:
    p = ms_dir / name
    return p.read_text(encoding="utf-8") if p.exists() else None


def problems(root: Path, ms_dir: Path, text: str | None = None, gold: dict | None = None,
             required: dict | None = None, highlights: str | None = None, exhibits: bool = True) -> list[str]:
    """Every problem of the manuscript folder (the arguments override what is read from it;
    exhibits=False skips regenerating the tables and figure data, for the mutation sweep)."""
    text = text if text is not None else (ms_dir / MS_NAME).read_text(encoding="utf-8")
    gold = gold if gold is not None else load_gold(ms_dir)
    required = required if required is not None else section_phrases(ms_dir)
    highlights = highlights if highlights is not None else read_opt(ms_dir, HIGHLIGHTS)
    if not required:
        return [f"PHRASES: no section phrases ({PHRASES} missing or empty)"]
    if journal_of(ms_dir) == "ijtld":
        return problems_ijtld(root, ms_dir, text, gold, required, exhibits)
    pf = load_phrase_file(ms_dir)
    now, out = skeleton(text, highlights, root, required)
    out += skeleton_problems(now, gold, root)
    out += claims(root)
    out += exhibit_problems(text)
    if exhibits:
        out += regenerated_problems(ms_dir, root)
    caveats = pf.get("caveats", {})
    if not caveats:
        out.append(f"CAVEAT: no caveats listed in {PHRASES}")
    out += caveat_problems(text, caveats)
    out += reference_problems(text)
    out += length_problems(text, highlights)
    out += label_problems(text, root)
    out += wording_problems(MS_NAME, text)
    if highlights is None:
        out.append(f"MISSING: {HIGHLIGHTS}")
    else:
        out += wording_problems(HIGHLIGHTS, highlights)
    tables = read_opt(ms_dir, "exhibits/tables.md")
    if tables is not None:
        out += wording_problems("exhibits/tables.md", tables)
    tp = read_opt(ms_dir, TITLE_PAGE)
    if tp is None:
        out.append(f"MISSING: {TITLE_PAGE}")
    else:
        out += wording_problems(TITLE_PAGE, tp)
        out += title_page_problems(text, tp)
        out += declaration_problems(text, tp)
    cover = read_opt(ms_dir, COVER)
    out += cover_problems(cover, pf.get("cover_letter", []))
    if cover is not None:
        out += [p for p in wording_problems(COVER, cover) if "file path" not in p]
    if not pf.get("cover_letter"):
        out.append(f"COVER LETTER: no related manuscripts listed in {PHRASES} 'cover_letter'")
    return out


def golden(text: str, highlights: str | None, root: Path, required: dict, journal: str = "pcd") -> dict:
    if journal == "ijtld":
        now, probs = skeleton_ijtld(text, root, required)
    else:
        now, probs = skeleton(text, highlights, root, required)
    if probs:
        raise SystemExit("cannot regenerate the skeleton while phrases or numbers fail:\n" + "\n".join(probs))
    return {"about": "Golden numeric skeleton of manuscript.md and highlights.md: for each section, every number token "
                     "in reading order with the catalogue label that accounts for it and its source. Written by "
                     "verification/check_manuscript_numbers.py --regenerate after review.",
            "sections": now}


def main(root: Path = ROOT, argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ms_dir, rest = manuscript_dir(root, argv)
    unknown = [a for a in rest if a != "--regenerate"]
    if unknown:
        print(f"FAIL: unknown arguments {unknown}")
        return 1
    name = rel(ms_dir, root)
    if not ms_dir.is_dir():
        print(f"SKIPPED: {name}/ not present (kept private, not in this repository)")
        return 0
    ms, ph = ms_dir / MS_NAME, ms_dir / PHRASES
    if not ms.exists() and not ph.exists():
        print(f"SKIPPED: {name}/{MS_NAME} not present (kept private, not in this repository)")
        return 0
    if not ms.exists() or not ph.exists():
        have, lack = (MS_NAME, PHRASES) if ms.exists() else (PHRASES, MS_NAME)
        print(f"FAIL: {name}/{have} is present but {name}/{lack} is missing")
        return 1
    try:
        required = section_phrases(ms_dir)
    except ValueError as e:
        print(f"FAIL: {name}/{PHRASES} cannot be read: {e}")
        return 1
    text = ms.read_text(encoding="utf-8")
    if "--regenerate" in rest:
        g = golden(text, read_opt(ms_dir, HIGHLIGHTS), root, required, journal_of(ms_dir))
        (ms_dir / SKELETON).write_text(json.dumps(g, indent=1, ensure_ascii=False) + "\n", encoding="utf-8",
                                       newline="\n")
        print(f"wrote {name}/{SKELETON}: {sum(len(v) for v in g['sections'].values())} number tokens")
        return 0
    found = problems(root, ms_dir, text, required=required)
    for ln in found:
        print(ln)
    gold = load_gold(ms_dir) or {}
    n_tok = sum(len(v) for v in gold.values())
    n_traced = sum(1 for v in gold.values() for x in v if not x["label"].startswith("fixed:"))
    if journal_of(ms_dir) == "ijtld":
        print(f"IJTLD profile: {n_tok} number tokens ({n_traced} traced to a source file, {n_tok - n_traced} fixed "
              f"labels), {sum(len(v) for v in required.values())} section phrases, {len(catalogue_cached(root))} "
              f"catalogue values, {len(ref_list_ijtld(text))} references; Table 1 and figure data regenerated from "
              f"outputs/; hard limits (main {ijtld.LIMITS['main']}, abstract {ijtld.LIMITS['abstract']}, references "
              f"{ijtld.LIMITS['references']}, display items {ijtld.LIMITS['display_items']}, title "
              f"{ijtld.LIMITS['title_chars']}, running head {ijtld.LIMITS['running_head_chars']}, keywords 3-5) checked; "
              f"{len(found)} problem(s)")
        return 1 if found else 0
    print(f"{n_tok} number tokens ({n_traced} traced to a source file, {n_tok - n_traced} fixed labels), "
          f"{sum(len(v) for v in required.values())} section phrases, {len(catalogue_cached(root))} catalogue "
          f"values, {len(ref_list(text))} references; tables, figure and graphical-abstract data regenerated from "
          f"outputs/; {len(found)} problem(s)")
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main())
