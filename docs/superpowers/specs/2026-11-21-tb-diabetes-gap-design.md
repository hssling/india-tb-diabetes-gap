# The diabetes–TB gap in India's States: design

The author approved this design on 21 November 2026 ("yes go ahead"). It was chosen from a second round of research ideas, after novelty and data checks. The earlier idea, "missing TB patients", overlapped with the author's own paper, IJTB 2026, doi 10.1016/j.ijtb.2026.01.010.

## 1. Intent

Diabetes roughly triples the risk of TB. It worsens TB treatment outcomes. India carries the world's largest joint burden.

India's 2018 National Framework for Joint TB–Diabetes Collaborative Activities makes diabetes screening of every notified TB patient the standard. The India TB Reports print, by State:
- how many TB patients have a known diabetes status;
- how many of those were found diabetic.

NFHS-5 (2019–21) prints each State's diabetes prevalence in adults.

**Question.** In each State, how many TB patients with diabetes are likely going undetected, and is the shortfall at the screening step or the detection step?

**Users.** The Central TB Division, State TB Cells and the NCD programme (NP-NCD), for integrating TB and diabetes services.

**Framing.** Constructive and practice-guiding, not a critique. The paper cites the author's IJTB 2026 paper, which recommends community screening for comorbidities, and builds on it.

## 2. Goals, non-goals, anti-goals

**Goals.**
- Two gaps per State and year, each in absolute numbers of patients with uncertainty:
  - the screening gap;
  - the detection gap.
- Priority tiers for each gap.
- A trend in screening coverage over the years available.
- A State-level association test.
- Full reproducibility and pre-registration.
- Reuse of the author's released priority tool (tbprio v1.0.1, DOI 10.5281/zenodo.24411057) for shrinkage, P(top-k) and tiers. It is imported at that pinned version, which also shows the tool is reusable.

**Non-goals.**
- Causal effects.
- Individual-level data.
- District analysis (no district diabetes–TB data are published).
- Estimating national diabetes prevalence.

**Anti-goals.**
- Claiming that low detection proves under-detection. It may reflect true lower prevalence among TB patients, the testing method or recording.
- Blaming States.
- Rankings without uncertainty.
- Language implying causation.

## 3. Data (all public)

**TB–diabetes State tables.** These were found by a structure-only scan, with no values computed:

| Data year | Source |
|---|---|
| 2018 | ITR 2019 Annexure 1.2 (TB comorbidities, diabetes columns). The builder confirms the columns |
| 2021 | TB Annual Report 2022, Annexure 2.5 "TB-Diabetes": TB patients with known DM status (%), TB-DM patients diagnosed among tested (%), TB-DM patients initiated on treatment |
| 2022 | ITR 2023, Annexure 2.10 "TB-Diabetes" |

- ITR 2020 (data 2019) and ITR 2024 (data 2023) print no State diabetes table.
- ITR 2021 is a scanned image and is not used.
- The PDFs are local copies in tb_priority_tool/data_raw (SHA-256 recorded there). They are copied and re-verified.

**NFHS-5 State fact sheets** (2019–21):
- Source: the official compendiums, Phase I (22 fact sheets) and Phase II (15). They were downloaded with the author's permission on 21 November 2026 from dhsprogram.com/pubs/pdf/OF43/.
- SHA-256:
  - Phase I: 5bcc2a37b13ffc0203d736803f72aece88b4beb0bc168d1f069e110178ab2bd7
  - Phase II: 3e8ee12bb4a59e9ec2e7bebc736b2252d61e9ed98ce322717debe11dd73c52b7
- Indicators: "Blood sugar level – high or very high (>140 mg/dl) or taking medicine to control blood sugar level", for women and for men aged 15 years and over, by State/UT.

**Notified TB by sex** (ITR 2023 Annexure 1.6), for weighting the sex-specific NFHS prevalence.

**Units.** States/UTs coarsened the same way in every year, reusing the priority tool's crosswalk (merging DNH&DD, Lakshadweep with Kerala and Ladakh with J&K, as needed). NFHS reports DNH&DD, Ladakh and Lakshadweep separately; these are merged by population weights from the NFHS or ITR population columns.

## 4. Method (the registered plan fixes every value)

**Reference prevalence p_s.** Each State's NFHS-5 diabetes prevalence for ages 15+, combining women and men weighted by the State's share of notified TB patients by sex (2022). NFHS fact sheets give point estimates only, so p_s carries no sampling interval. Its uncertainty is handled by sensitivity analyses (±20%), stated as a limitation.

**Gap 1: screening gap (per State-year).**
- Count: notified − TB patients with known diabetes status.
- Coverage: known ÷ notified.
- Harm-like count: untested × k·p_s, the expected diabetics among the untested.

**Gap 2: detection gap.**
- y = diabetic ÷ tested (with a binomial posterior).
- Detection ratio R = y / p_s.
- The diabetes prevalence among TB patients is expected to exceed the general-population prevalence. Main k = 1 is a conservative, assumption-free lower bound; sensitivity analyses use k = 1.5 and 2.
- A State is "likely under-detecting" if its 95% interval for R lies wholly below 1.
- Count: tested × max(0, k·p_s − y), the undetected diabetics among the tested.

**Priorities.** For each gap, harm (undetected diabetic TB patients) uses the tbprio machinery: empirical-Bayes shrinkage of the rates, 10,000 draws, P(top-5) tiers (act now ≥ 0.80; probable 0.50–0.80; uncertain 0.20–0.50; lower < 0.20) and a per-100,000-notified view. Absolute numbers come first.

**Trend.** Screening coverage over 2018, 2021 and 2022 per State: the empirical-logit WLS with φ, as in tbprio. There is no COVID indicator, because 2018 is the only pre-COVID point. This is stated.

**Headline estimates (labels "supported" / "not established", using the same rule as the companion studies):**
- **H1.** Spearman ρ between States' p_s and the yield y among tested TB patients, with 2021 and 2022 pooled. If detection works, they should be positively associated. Null 0. Fieller interval.
- **H2.** National screening coverage, 2018 vs 2022 (descriptive, with intervals; no label).
- **H3.** The number of States likely under-detecting, with k = 1 (descriptive).

**Robustness.** A specification grid over:
- k ∈ {1, 1.5, 2};
- p_s weighting (sex-weighted vs simple average);
- year (2021, 2022, pooled);
- shrinkage on/off.

Leave-one-out analyses are also run.

## 5. Registration and honesty

- **Registration.** A new public repo, hssling/india-tb-diabetes-gap. The analysis plan is pushed before any estimate, with a registration event file and dated deviations.
- **What had been seen.** The ITR tables, by structure. NFHS-5 State diabetes prevalences are widely published and had probably been seen. The author's own IJTB 2026 paper used NFHS-5 risk indicators. These are disclosed.
- **Disclosure.** The paper cites the author's IJTB 2026 paper and discloses the three TB papers now under review in its cover letter.

## 6. Paper

- **Content.** An original research paper framed as programme guidance on integrating TB and diabetes services.
- **Journal.** Hybrid or APC-free, verified from the journal's own guidelines at the manuscript stage. Leading candidates: Primary Care Diabetes (Elsevier) and Diabetes Research and Clinical Practice (Elsevier).

## 7. Constraints

- Python 3.14 with `python -I`; numpy and scipy; tbprio pinned to v1.0.1.
- LF line endings; fixed seed.
- No further downloads without asking.
- Manuscript local only, never committed.
- AI use declared in the standard Elsevier wording.

## 8. Approaches considered

- **A. A simple descriptive table of coverage and yield by State.** Rejected: not novel enough.
- **B. The chosen design.** A two-gap decomposition with uncertainty, tiers and reuse of the priority tool.
- **C. Modelling the diabetes prevalence among TB patients from age-sex-specific NFHS data.** Rejected: State fact sheets do not give age-specific diabetes. The k-multiplier sensitivity covers this more transparently.

## 9. Left to the builder

- Exact column mappings per edition.
- The NFHS page parsing.
- Module layout and test design, within the rules above.
