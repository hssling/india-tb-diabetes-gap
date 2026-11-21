# Diabetes–TB Gap Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A pre-registered, reproducible State-level analysis of India's diabetes–TB screening and detection gaps (data years 2018, 2021 and 2022), plus a submission-ready manuscript.

**Architecture:**
- Extraction scripts (`src/extract/`) build a long panel: unit, year, measure, numerator, denominator, provenance. Sources are the India TB Report diabetes tables and the NFHS-5 State fact sheets.
- The analysis package `src/dmgap/` computes the reference prevalence, both gaps, the detection ratio, priorities, trends and H1–H3. For shrinkage, draws, P(top-k) and tiers it imports `tbprio` (pinned v1.0.1).
- The analysis plan `docs/analysis_plan.md` is pushed to a new public repo before any estimate.
- `verification/` recomputes the headlines independently.
- The manuscript is local, under `manuscript/`.

**Tech Stack:** Python 3.14 (`python -I`), numpy, scipy, pdfplumber, pytest, matplotlib; `tbprio @ git+https://github.com/hssling/india-tb-priority-tool@v1.0.1`.

**Spec:** `docs/superpowers/specs/2026-11-21-tb-diabetes-gap-design.md`

## Global Constraints
- `python -I`, LF line endings.
- Seed 20261122; numpy `default_rng`, reset per analysis; 10,000 draws.
- Reuse tbprio functions; never copy-modify them.
- No estimate (ratio, prevalence combination, gap, priority, trend, correlation) before the registration commit is pushed. Inventory of structure is allowed.
- No imputation. NA cells are listed. Every value carries source_file, pdf_page and table_id. Printed totals are checked.
- `data_raw/` and `manuscript/` are never committed. Source digests go in `data/source_manifest.csv`. No new downloads without asking the author.
- Wording:
  - "likely under-detection" only when the 95% interval of R lies wholly below 1;
  - no causal language; tiers, not ranks;
  - low detection may reflect true lower prevalence, the testing method or recording; say so.
- Label rule: "supported" only if the 95% interval excludes the null AND ≥80% of grid entries agree in sign.
- Commits end with "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>".
- Single author: Siddalingaiah H S, ORCID 0000-0002-4771-8285, Department of Community Medicine, Shridevi Institute of Medical Sciences and Research Hospital, Tumkur 572106, Karnataka, India; hssling@yahoo.com.

## Fixed analysis values (Task 2 copies these into the registered plan verbatim)
- **Data years:** 2018 (ITR 2019 Annexure 1.2 diabetes columns), 2021 (TB Annual Report 2022 Annexure 2.5), 2022 (ITR 2023 Annexure 2.10). If Task 1 finds that a year does not print both the tested and the diabetic counts, it is dropped and the reason recorded.
- **Units:** the tb_priority_tool coarsening (DNH&DD with Gujarat, Lakshadweep with Kerala, Ladakh with J&K), applied every year. NFHS units are merged into the same units by NFHS-5 population weights; if the fact sheets lack population, the ITR population is used.
- **Reference prevalence p_s:** NFHS-5 "blood sugar level high or very high (>140 mg/dl) or taking medicine", ages 15+, women w_s and men m_s. Then p_s = f_s·w_s + (1 − f_s)·m_s, where f_s is the female share of the State's notified TB patients in 2022 (ITR 2023 A1.6; transgender patients go with men for weighting, stated). Sensitivity: the simple average (w_s + m_s)/2.
- **Gap 1 (screening):**
  - u = notified − known status;
  - coverage c = known/notified;
  - expected undetected among the untested E1 = u·k·p_s.
- **Gap 2 (detection):**
  - y = diabetic/known-status-tested;
  - R = y/p_s;
  - undetected among the tested E2 = tested·max(0, k·p_s − y).
- **k:** main 1 (lower bound); sensitivities 1.5 and 2.
- **Likely under-detection:** the 95% interval of R, from Beta(½ + x, ½ + n − x) draws of y with p_s fixed, lies wholly below 1.
- **Priorities:** tbprio shrinkage, draws and P(top-5), applied to E1 and E2 per year; tiers act now ≥0.80 / probable ≥0.50 / uncertain ≥0.20 / lower; a per-100,000-notified view alongside. The main priority year is 2022.
- **Trend:** screening coverage c over 2018, 2021 and 2022, using tbprio's empirical-logit WLS slope with pooled φ, with no COVID indicator (stated). A "falling coverage" flag is set when the slope CI lies wholly below 0. Minimum: 3 years.

**Headline estimates**

| | Estimate | Null | Interval | Label |
|---|---|---|---|---|
| H1 | Spearman ρ between p_s and pooled y (2021 + 2022 counts summed per unit) | 0 | Fieller, √(1.06/(n−3)) | yes |
| H2 | National coverage 2018 vs 2022 | — | Wilson intervals | none (descriptive) |
| H3 | Number of units likely under-detecting at k = 1, 2022 | — | — | none (descriptive) |

- **H1 grid** (12 entries): p_s weighting {sex-weighted, simple} × year {2021, 2022, pooled} × shrinkage of y {on, off}.
- **Leave-one-out:** each unit, for H1 and for the 2022 act-now sets.
- **NFHS uncertainty:** sensitivity with p_s × {0.8, 1.2}. The NFHS fact sheets give no CI, so this is stated as a limitation.

**Strengthened analyses (21 Nov 2026, the author's request: novelty, innovation, policy/practice framing, advanced analyses; fixed BEFORE registration; Task 2 copies them into the registered plan, and they supersede earlier values where they differ)**

1. **The TB–diabetes care cascade (the headline novelty).** Three steps per State and year:
   - C1 screened = known status ÷ notified;
   - C2 diagnosed = the detection ratio R = y/(k·p_s);
   - C3 linked = TB–DM patients initiated on diabetes treatment ÷ TB–DM diagnosed.

   C3 is used only where Task 1 finds it printed as counts or as derivable counts. A novelty check on 21 Nov 2026 found no State-level TB–diabetes cascade for India.
2. **Data-driven reference multiplier (main analysis).** Assuming k is replaced by an estimated benchmark:
   - k_b = the 75th percentile, across units, of the shrunken ratio y/p_s (pooled 2021 and 2022), the same benchmark logic as tbprio;
   - expected yield = k_b·p_s;
   - sensitivities: k = 1 (lower bound), 1.5 and 2 (published TB:population diabetes ratios, Crossref-verified at the manuscript stage), and the median and best-decile benchmarks.
3. **Hierarchical regression of detection on prevalence (H1 replaced).** A quasi-binomial (overdispersed) logistic regression of TB–DM diagnosed / tested on logit(p_s), with a year effect (2021, 2022), weighted by tested, using numpy/scipy IRLS with a Pearson φ.
   - H1 is the slope β on logit(p_s). If detection follows true burden, β > 0. Null 0. Interval: a cluster bootstrap over units, 10,000 draws.
   - The Spearman ρ with Fieller interval is kept as a registered sensitivity.
4. **Overdispersed funnel.** Each unit's observed TB–DM diagnoses against those expected from the regression; multiplicative φ from 10%-winsorised z; 95% and 99.8% limits. Units below the 99.8% limit are flagged "detection well below what its diabetes burden predicts".
5. **Decomposition of the shortfall.** For each unit, the total undetected diabetic TB patients relative to the benchmark (E1 + E2) is split into a screening part (E1) and a detection part (E2), each with intervals. A unit is classed "screening-led" or "detection-led" when its share exceeds 0.5 with 95% posterior probability, otherwise "mixed". This tells each State which step to fix.
6. **Policy scenario.** The national number of additional diabetic TB patients identified per year if every unit reached the benchmark coverage and k_b, with a 95% interval, and the share contributed by the top 5 units. Labelled an illustration, not a forecast.
7. **Equity and health-system context (exploratory, labelled).** Spearman ρ between C1 coverage and the NFHS-5 State share of adults with high blood sugar who are on medicine, a proxy for NCD treatment reach. This is computed only if the fact sheets print the needed components; otherwise it is dropped before registration.
8. **H2 and H3** are unchanged: national coverage 2018 vs 2022; the count of units with C2 below benchmark at 95% posterior probability.

**H1 grid** (12 entries): reference {sex-weighted, simple} × year set {2021, 2022, pooled} × weights {tested, unweighted}.

## Review Focus
1. **A unit with known > notified, or diabetic > tested** (a reporting artefact). Expected: NA for that measure, listed. Pinned in Task 3: `test_impossible_counts_become_na`.
2. **An NFHS unit with no TB unit match, or an ITR unit with no NFHS match.** Expected: an explicit crosswalk; an unmatched name raises an error naming it. Pinned in Task 3: `test_unmatched_nfhs_unit_raises`.
3. **Percent-only cells** (some editions print "n (x%)" or % only). Expected: counts are taken when printed. When only % is printed, the count is derived with a rounding interval, flagged `derived_from_percent`. Pinned in Task 3: `test_percent_only_cell_derivation_flagged`.
4. **y above k·p_s** (detection above the reference). Expected: E2 = 0, never negative. Pinned in Task 4: `test_detection_gap_floor_zero`.
5. **A tbprio version drift.** Expected: `import tbprio`; assert `tbprio.__version__ == "1.0.1"`, or the installed metadata version is 1.0.1, at analysis start. Pinned in Task 4: `test_tbprio_pinned_version`.

---

### Task 1: Scaffold, manifest and inventory (no estimates)

**Files:** README stub, LICENSE (MIT), LICENSE-DATA (CC BY 4.0), ENVIRONMENT.md, pyproject.toml (dependency tbprio pinned), data/source_manifest.csv, tools/fetch_sources.py, docs/data_inventory.md, tests/test_manifest.py.

**Sources.**
- `tools/fetch_sources.py` copies these from ../tb_priority_tool/data_raw/india_tb_report/, verifying them against that repo's manifest:
  - India-TB-Report-2019.pdf;
  - TBAnnaulReport2022.pdf;
  - ITR2023.pdf;
  - ITR2024.pdf, for the sex table if needed.
- It verifies the two NFHS compendiums already in data_raw/nfhs5/ against the digests in the spec.

**Inventory.** For each data year: the table, pages, verbatim headers, units, printed India totals, and whether counts or only % are printed. For NFHS: the page and indicator lines per State/UT; whether population is printed; how the UT fact sheets are named.

- [ ] `test_manifest_digests_match`.
- [ ] Implement, run and commit.

### Task 2: Analysis plan and registration (HARD GATE)

**Files:** docs/analysis_plan.md (§1–§11 frozen; §12 "Deviations (dated)"), docs/registration_event.json, verification/check_plan_order.py and tests. Adapt the plan-order check from tb_priority_tool: the anchor is pinned, the guard covers src/dmgap/ and outputs/, the history check uses `--diff-merges=separate`, and `--ancestry-path` is used.

- [ ] Write the plan with every fixed value verbatim, plus "What had been seen" (spec §5) and "Known limitations stated in advance".
- [ ] Write the tests and implement the check. Commit.
- [ ] The controller reviews the plan, creates the public repo hssling/india-tb-diabetes-gap, pushes, and records pushed_at.

### Task 3: Extraction

**Files:** src/extract/{pdftext,cells}.py (copied with attribution from tb_priority_tool), src/extract/itr_dm.py, src/extract/nfhs.py, src/extract/crosswalk.py, data/extracted/{dm_panel.csv, nfhs_dm.csv, tb_sex_2022.csv}, verification/check_extraction_totals.py, tests/test_extract.py, tests/test_known_cells.py.

**Interfaces.**
- dm_panel.csv: `unit, year, measure ∈ {notified, known_status, diabetic, initiated}, value, source_file, pdf_page, table_id, flag`.
- nfhs_dm.csv: `unit, sex, prevalence_pct, population, source_file, pdf_page, flag`.

- [ ] Tests: the three pinned Review Focus tests; printed-total checks; `test_known_cells` with ≥10 values the implementer reads by eye.
- [ ] Implement, run and commit.

### Task 4: Analysis

**Files:** src/dmgap/{__init__,reference,gaps,priority,trend,validate}.py, src/run_all.py, outputs/{reference_prevalence.csv, gaps.csv, priority.csv, trend.csv, headline.csv, spec_curve.csv, leave_one_out.csv, na_cells.csv}, tests/test_analysis.py.

**Interfaces.**
- `reference.p_s(nfhs_rows, sex_rows, weighting: str) -> dict[str, float]`
- `gaps.compute(panel, p_s, k: float) -> list[dict]`
- `priority.run(gap_rows, gap: str, year: int, k: float, rng) -> list[dict]` (calls tbprio)
- `validate.h1(...)`
- `validate.label(...)`

- [ ] Tests: the two pinned Review Focus tests; `test_ratio_interval_rule`; `test_label_rule`; `test_outputs_byte_identical_on_rerun`.
- [ ] Implement, run and commit.

### Task 5: Verification and documentation

**Files:**
- verification/check_outputs.py: a standard-library recompute of p_s, E1/E2 for 3 units, R intervals and the H3 count, H1 and its Fieller interval, and the labels;
- check_deviations.py;
- check_rerun.py;
- check_all.py, which skips the manuscript checks until they exist;
- MUTATIONS.md and tests;
- README, outputs/README.md and CITATION.cff (version 1.0.0; date at release).

- [ ] Mutation tests catch: an altered headline; a plan edit above §12; a flipped label; an altered extracted cell; an altered p_s.
- [ ] Run `check_all`: all PASS. Commit.

### Task 6: Manuscript, exhibits and build (local)

**Files:**
- committed: exhibits builders, tools/build_submission.py (refuses SUBMITTED_ folders and unknown options), render_check.ps1, word_count_word.ps1, verification/check_manuscript_numbers.py, check_docx_tie.py, mutate_manuscript.py;
- local only: manuscript/.

**Journal.** The controller writes manuscript/journal_rules.md from the chosen journal's guide before dispatch.

**Content.**
- Figure 1: coverage and yield by State, with the reference line.
- Figure 2: the detection ratio R with intervals.
- Figure 3: undetected diabetic TB patients (E1, E2) as tiers.
- Figure 4: coverage trend.
- A table of headline estimates.
- The practice guidance for the Central TB Division, State TB Cells and NP-NCD.
- The limitations: k, NFHS without CI, ecological design, recording.
- The standard Elsevier AI declaration.
- The author's IJTB 2026 paper cited.

- [ ] Build; run render QA; get Word counts; run all checks and the mutations. Commit the tooling only.

### Task 7: Final review, release and hand-over (controller)
- [ ] Whole-branch review and a referee review, then one fix wave and a scoped re-review.
- [ ] Release v1.0.0. The author switches the repo on in Zenodo; then v1.0.1 for the DOI if needed. Rebuild with `--doi`.
- [ ] Update the tracker and memory; give the author the rulings list.
