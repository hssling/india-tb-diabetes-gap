# Mutation record

<!-- Adapted from hssling/india-tb-priority-tool v1.0.1 (MIT), verification/MUTATIONS.md; modified: this repository's checks and mutations -->

Each check was shown to fail on a deliberate break (analysis plan section 10.4). All breaks
were made in a scratch clone (`git clone <repo> <scratch>/mut`), never in this repository
or its history; the clone was restored (`git checkout -- .` and `git reset --hard` to the
cloned commit) between runs. Run on 21 November 2026: mutations 1-8 against commit
31984a0, mutations 9-11 against commit 2ab2dad (the full README). The clone has no
`data_raw/`, so the extraction rerun of check_rerun prints SKIPPED there; no other check
reads `data_raw/`.

| # | Check | Break | Result |
|---|-------|-------|--------|
| 1 | check_outputs | headline value: `headline.csv` H1 value 1.70128... to 1.71128... | caught (FAIL, exit 1) |
| 2 | check_plan_order | `docs/analysis_plan.md` section 5.2 "Main k_b = the 75th percentile of g_u" to "80th", above section 12; first uncommitted, then committed | caught both times (FAIL, exit 1) |
| 3 | check_outputs | label flipped: `headline.csv` H1 "supported" to "not established" | caught (FAIL, exit 1) |
| 4 | check_outputs, check_extraction_totals | extracted cell: `dm_panel.csv` Bihar 2023 diabetic + 1 | caught by both (FAIL, exit 1) |
| 5 | check_extraction_totals | extracted table cell: `dm_cells.csv` ITR 2019 A1.2 notified, Bihar + 1 | caught (FAIL, exit 1) |
| 6 | check_outputs | one NFHS-5 prevalence: `nfhs_dm.csv` Kerala women 24.8 to 24.9 | caught (FAIL, exit 1) |
| 7 | check_outputs | k_b in an output: `benchmark.csv` main k_b x 1.001 | caught (FAIL, exit 1) |
| 8 | check_outputs | a Monte Carlo mean: `gaps.csv` Bihar E2 2023 main mean x 1.02 | caught (FAIL, exit 1) |
| 9 | check_deviations | a README line "A further deviation was made in data year 2021." | caught (FAIL, exit 1) |
| 10 | check_rerun | one byte of `outputs/trend.csv` ("estimated" to "Estimated") | caught (FAIL, exit 1) |
| 11 | check_all | mutation 1, whole suite | FAIL: pytest, check_outputs, check_rerun (exit 1) |

## 1. Headline value

```
# outputs/headline.csv, H1 value + 0.01
python -I verification/check_outputs.py
```

```
FAIL: (i) headline H1 value vs spec_curve main beta1: printed '1.7112817360612669' but expected '1.7012817360612669'
FAIL: (i) headline H1 value vs H1_wald_interval: printed '1.7112817360612669' but expected '1.7012817360612669'
FAIL: (i) headline H1 value vs the own IRLS: printed 1.7112817360612669 but the exact expectation is 1.7012817360612662 (tolerance 1e-06)
exit 1
```

## 2. Plan edited above section 12

```
# docs/analysis_plan.md: "Main k_b = the 75th percentile of g_u" -> "... 80th ..."
python -I verification/check_plan_order.py
git commit -am "mutation: edit above section 12"
python -I verification/check_plan_order.py
```

```
FAIL: the working-tree docs/analysis_plan.md above section 12 differs from its content at the registration commit 7c7ba61 (an uncommitted edit)
exit 1
FAIL: commit a8865d8: docs/analysis_plan.md above section 12 differs from its content at the registration commit 7c7ba61
exit 1
```

## 3. Label flipped

```
# outputs/headline.csv, H1 label "supported" -> "not established"
python -I verification/check_outputs.py
```

```
FAIL: (h) headline H1 label: printed 'not established' but expected 'supported'
exit 1
```

## 4. Extracted panel cell

```
# data/extracted/dm_panel.csv, Bihar 2023 diabetic 8696 -> 8697
python -I verification/check_outputs.py
python -I verification/check_extraction_totals.py
```

```
FAIL: (c) Bihar 2023 D: printed 8696 but expected 8697
FAIL: (c) Bihar 2023 y: printed 0.059201165505926245 but recomputed 0.05920797336764495
FAIL: (c) Bihar 2023 y_lo: printed 0.05800295423145554 but recomputed 0.05800969693675492
FAIL: (c) Bihar 2023 y_hi: printed 0.06041674754225409 but recomputed 0.06042362029212346
FAIL: (c) Bihar 2023 C2: printed 0.48587766624985246 but recomputed 0.4859335399465233
FAIL: (c) Bihar 2023 R_k1: printed 0.3994840686852647 but recomputed 0.39953000751561024
... (33 more FAIL lines, including the 2023 empirical-Bayes prior a2)
exit 1

FAIL: 2023 diabetic: panel sum 181027 != printed rows 181026
exit 1
```

## 5. Extracted table cell

```
# data/extracted/dm_cells.csv, ITR2019_A1.2 notified, Bihar 106313 -> 106314
python -I verification/check_extraction_totals.py
```

```
FAIL: ITR2019_A1.2 notified: State sum 2155895 vs printed 2155894 (difference 1) is not recorded
FAIL: 2018 notified: panel sum 2155894 != printed rows 2155895
exit 1
```

## 6. One NFHS-5 prevalence

```
# data/extracted/nfhs_dm.csv, Kerala women 24.8 -> 24.9
python -I verification/check_outputs.py
```

```
FAIL: (a) Kerala w: printed 0.24789779824435168 but recomputed 0.24889586990933948
FAIL: (a) Kerala p_sex_weighted: printed 0.26213379124085223 but recomputed 0.2624854535344308
FAIL: (a) Kerala p_simple: printed 0.25888815656929054 but recomputed 0.2593871924017844
FAIL: (a) cascade main Kerala 2018 p_u: printed 0.26213379124085223 but recomputed 0.2624854535344308
... (67 more FAIL lines: every Kerala p_u, R and E1/E2 point)
exit 1
```

k_b itself is unchanged by this edit (Kerala is not at the 75th percentile of g_u); a
change that moves k_b is mutation 7.

## 7. k_b in an output

```
# outputs/benchmark.csv, main k_b (p75, 2021+2022, sex_weighted, empirical_bayes) x 1.001
python -I verification/check_outputs.py
```

```
FAIL: (b) k_b p75 2021+2022 sex_weighted empirical_bayes: printed 0.8230128292176289 but recomputed 0.82219063857905
exit 1
```

## 8. A Monte Carlo mean

```
# outputs/gaps.csv, Bihar 2023 E2 main, mean x 1.02
python -I verification/check_outputs.py
```

```
FAIL: (d) Bihar E2 mean: printed 9386.136273714848 but the exact expectation is 9201.351035535788 (tolerance 4.52)
exit 1
```

## 9. Unlogged deviation in the README

```
printf 'A further deviation was made in data year 2021.\n' >> README.md
python -I verification/check_deviations.py
```

```
FAIL: README.md line 278: labelled 'deviation' but names no dated plan 12 entry that carries that label
exit 1
```

## 10. Output byte edited

```
# outputs/trend.csv, the first "estimated" -> "Estimated"
python -I verification/check_rerun.py
```

```
FAIL: outputs/trend.csv differs from the analysis rerun
exit 1
```

## 11. Whole suite with mutation 1

```
python -I verification/check_all.py
```

```
[FAIL] pytest -q
    FAILED tests/test_analysis.py::test_outputs_byte_identical_on_rerun - Asserti...
    FAILED tests/test_verification.py::test_check_outputs_passes_on_the_committed_outputs
    FAILED tests/test_verification.py::test_own_irls_matches_the_main_slope_to_1e_6
    3 failed, 190 passed, 3 skipped in 183.40s (0:03:03)
[PASS] check_plan_order: OK: ...
[PASS] check_deviations: OK: ...
[PASS] check_extraction_totals: OK: printed totals match or are recorded; coarsening preserves the totals
[PASS] check_implied_denominator: OK: the match counts are those recorded in plan section 12.1
[FAIL] check_outputs
    FAIL: (i) headline H1 value vs spec_curve main beta1: ...
    FAIL: (i) headline H1 value vs H1_wald_interval: ...
    FAIL: (i) headline H1 value vs the own IRLS: ...
[FAIL] check_rerun
    SKIPPED: extraction rerun (data_raw/ is not distributed; ...)
    FAIL: outputs/headline.csv differs from the analysis rerun
[SKIP] check_manuscript_numbers: SKIPPED: manuscript/manuscript.md does not exist
[SKIP] check_docx_tie: SKIPPED: manuscript/manuscript.md does not exist

4/7 checks passed (2 skipped)
exit 1
```

## Fixed in the tests

The same breaks, on temporary copies of `outputs/`, `data/extracted/`, the plan and the
README (or a temporary clone for the plan), are fixed in `tests/test_verification.py`,
which runs in the pytest step of check_all:

- check_outputs: `test_mutated_headline_value_fails`,
  `test_mutated_descriptive_headline_fails` (H3 value; H2 lo), `test_flipped_label_fails`,
  `test_label_on_a_descriptive_estimate_fails`, `test_spec_curve_sign_flip_fails`,
  `test_changed_extracted_cell_fails_check_outputs`, `test_changed_nfhs_prevalence_fails`,
  `test_changed_kb_in_benchmark_fails`, `test_changed_kb_in_cascade_fails`,
  `test_monte_carlo_summaries_are_checked` (an E2 mean, the national scenario mean, an R
  interval end), `test_flipped_h3_flag_fails`, `test_check_outputs_main_exits_1_on_a_mutation`;
  and `test_check_outputs_is_standard_library_only` (no numpy, scipy, tbprio or src is
  imported or loaded), `test_own_irls_matches_the_main_slope_to_1e_6`,
  `test_exact_beta_functions`;
- check_extraction_totals: `test_changed_extracted_cell_fails_check_extraction_totals`,
  `test_changed_panel_cell_fails_the_coarsening_check`;
- check_plan_order: `test_edit_above_section12_fails_in_a_clone` (uncommitted and
  committed);
- check_deviations: `test_unlogged_labels_fail` (post hoc; exploratory naming an entry
  that is not exploratory; two missing entries; deviation with no entry; deviation naming
  plan 12.2, a naming note; and two lines that pass),
  `test_unlogged_label_in_readme_and_data_flags_fail`, `test_undated_section12_entry_fails`,
  `test_post_hoc_line_covered_by_a_dated_post_hoc_entry_passes`;
- check_rerun: `test_rerun_compares_every_file_byte_for_byte` (a changed, a missing and an
  extra output, a changed extracted file, and the SKIP without `data_raw/`, with the reruns
  replaced by stubs);
- check_all: `test_check_all_steps_and_manuscript_skips`.

## Not exercised

- check_outputs does not re-derive the H1 bootstrap interval, P(top-5) and tiers, the
  decomposition, the trend, the funnel, leave-one-out, the perturbation or the
  sensitivity specifications; an edit there alone is caught by check_rerun (and the
  byte-identity test of `tests/test_analysis.py`), as mutation 10 shows.
- A Monte Carlo value is compared within a stated tolerance (check_outputs docstring), so
  an edit smaller than about five Monte Carlo standard errors passes check_outputs and is
  caught only by check_rerun. Classifications whose exact value lies within that
  tolerance of the threshold are reported as borderline (in 2023, Goa on the k = 1 rule).
- The manuscript checks (below) run only where the private `manuscript/` folder exists; in a
  clone without it, check_all reports them as SKIP.

## Manuscript checks

`verification/mutate_manuscript.py` copies the private, git-ignored `manuscript/` folder into
`manuscript/_mutations/` for every break (the real files are never written), applies one
named mutation, and runs check_manuscript_numbers and check_docx_tie on the copy. The
anchors that quote the manuscript are kept in the private `section_phrases.json`. Run on
21 November 2026 against the built Primary Care Diabetes set: **52 of 52 named mutations
caught**, and with `--sweep` every number token was caught: 353 of 353 in `manuscript.md`
(outside the References and the title-page block) and 789 of 789 in `02_manuscript.docx`
(tables and references included). The sweep first found one escape, a digit of the cited
tbprio Zenodo DOI in the .docx, because the tie normalised every Zenodo DOI; the tie now
normalises only the release DOI (the placeholder, or the DOI that `--doi` fills), and the
rerun caught it.

The named mutations cover: numbers changed in the .docx only (H1, Word's abstract count, a
Table S7 cell) and in the Markdown only (H2, a count in the abstract and in the highlights,
the registration time, the benchmark multiplier); the title page that a single-anonymized
manuscript must carry (the e-mail, the ORCID, the abbreviations footnote, a corresponding-
author line differing from the title page); reference numbers and order; table cells, the
figure data and the graphical-abstract data; the H1 label; a sign; internal identifiers;
wording ("newly diagnosed", "detection-led", "widespread", causal and ranking language,
"under-detection" without the k = 1 rule, American spelling); the highlight, abstract and
main-text limits and Word's counts; the AI declaration, the declaration of interest and the
caveats; a figure PDF, a low-resolution TIFF, an undersized graphical abstract and a sixth
display item; the cover letter's related manuscripts; and the file set.

## The IJTLD manuscript (manuscript/v2)

`verification/mutate_manuscript.py --manuscript-dir manuscript/v2` (also a `check_all` step)
applies 44 named breaks to copies of the private IJTLD manuscript folder and requires
`check_manuscript_numbers` or `check_docx_tie` to report each: numbers and table cells in the
Markdown and in the .docx, citation order and reference numbering, every IJTLD hard limit (title
over 110 characters or with an abbreviation, running head over 45 characters, a keyword repeating
the title, six keywords, an abbreviation in the abstract, an abstract over 200 words, a main text
over 2500 words, 36 references, a fourth display item), "pre-registered", stigmatising, causal,
American and drafting-process words, the online material (a missing table, a changed link, a
file in the upload folder), the layout (line numbers, justification, single spacing), the
figures (a 300 dpi TIFF, a swapped TIFF or embedded image) and the file set. The result table is
in `manuscript/v2/STRENGTHEN_report.md`.
