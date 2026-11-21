# The diabetes-TB gap in India's States

Code, extracted data, outputs and a pre-registered analysis plan for a State-level
analysis of the TB-diabetes care cascade in India: how many TB patients with diabetes are
likely going unidentified in each State or UT, and whether the shortfall lies at the
screening step or at the identification step. It uses only published, aggregate,
official data: the India TB Report diabetes tables (data years 2018, 2019, 2021, 2022 and
2023) and the NFHS-5 (2019-21) State and UT fact sheets.

The framing is practice-guiding, for the Central TB Division, the State TB Cells and the
National Programme for Prevention and Control of Non-Communicable Diseases (NP-NCD). It is
not a league table: results are given as tiers, not ranks, and they describe programme
data, not the performance or effort of any State's staff. All associations reported here
are observational; none is a causal estimate. A low identification ratio, a gap or a
priority may reflect a truly lower diabetes prevalence among a State's TB patients, the
testing method or recording, and not only missed diabetes.

## The question

The analysis plan, [`docs/analysis_plan.md`](docs/analysis_plan.md), asks (its section 2):

- **Q1. The care cascade.** For each unit and year: what share of notified TB patients
  had a known diabetes status (C1, screened); how does the share identified with diabetes
  among those screened compare with what the unit's diabetes burden implies (C2); and
  what share of those identified was started on anti-diabetic treatment (C3)?
- **Q2. The two gaps and where to act.** How many TB patients with diabetes are expected
  among those not screened (E1, the screening gap) and among those screened but not
  identified (E2, the identification gap)? Where would closing each gap identify the
  most, how certain is that, and is each unit's shortfall screening-led or
  identification-led?
- **Q3. Trend.** Is screening coverage rising or falling in each unit over 2018-2023?
- **Q4. Does identification follow burden?** Across units, is the TB-diabetes yield
  higher where diabetes is more prevalent (H1)?
- **Q5. National picture.** National screening coverage 2018 vs 2022 (H2); the number of
  units with identification below the benchmark (H3); and an illustrative national
  scenario.

"Identified" means diabetes identified among screened TB patients, newly diagnosed or
already known: the India TB Report count includes existing diabetes, as does NFHS-5.

## Registration

The plan was committed and pushed to this public repository before any estimate was
computed: commit `7c7ba61` (7c7ba61787623cb988293d0d884d221b25fa0283), pushed on
21 November 2026 at 15:05:56 UTC
([`docs/registration_event.json`](docs/registration_event.json); time from the GitHub
API). The text above its section 12 is frozen: `verification/check_plan_order.py` checks
that it is byte-identical at every later commit and in the working tree, and that no
analysis module, extracted value or output was committed before the registration commit.

### Changes after registration (plan §12)

Each is a dated entry in §12 of the plan; all four were made on 21 November 2026.

- **§12.1, the only deviation, decided before any estimate was computed.** The registered
  screening-coverage denominator for 2021-2023 (Annexure 1.2, notified by diagnosing
  facility) did not match the percentages printed in the diabetes tables themselves
  (2 of 37 rows each year). The printed percentages matched Annexure 1.4 net notified in
  2021 and 2023 (37 of 37) and the Annexure 1.6 male + female + transgender sum in 2022
  (28 of 37). §12.1 therefore puts numerator and denominator on the same basis: these
  counts are the main N for 2021-2023, and the registered A1.2 basis (and, for 2022, N
  back-calculated from the printed percentage) are reported as sensitivities. 2018 and
  2019 were unchanged. Under the registered basis Himachal Pradesh and Tripura have more
  patients with a known status than notified in 2021-2023 (6 cells set to NA).
- **§12.2, a naming note.** The flag names used in the extracted data for these bases.
- **§12.3, consequential notes on carrying out §12.1**, with no new analysis: the
  registered "A1.6 sensitivity" slots are filled by the §12.1 sensitivities; the seed is
  reset per draw set; the decomposition share is summarised over draws with a shortfall
  (every draw had one); the cumulative C1·C2·C3 is not formed for 2018; and the outputs
  call the class whose share lies mainly at the identification step "identification-led",
  following the plan's own wording rule (its section 1.3).
- **§12.4, a scope note.** Exactly which results are on both denominator bases (the
  cascade, gaps, priorities, decomposition, scenario, trend, H2 and its companions, and
  the leave-one-out E1 sets) and which are on the main basis only (the k-grid, the NFHS
  scaling and the State-specific perturbation).

`verification/check_deviations.py` checks that every deviation label (plan §12) and
every reference to a §12 entry in the outputs, this README and the extracted data names a
dated entry.

## Headline results

Main specification: data year 2023 for H3 and the priorities; the main denominator basis;
the sex-weighted reference prevalence p_u; the benchmark multiplier k_b = 0.822 (the 75th
percentile across units of the shrunken yield relative to p_u, pooled 2021 + 2022; it is
below 1).

| | Estimate | Value | 95% interval | Label |
|---|---|---|---|---|
| H1 | Slope β₁ of the quasi-binomial regression of the TB-diabetes yield on logit(p_u), data years 2019 + 2021, 33 units (66 unit-years) | 1.70 | 1.01 to 2.18 (cluster bootstrap over units, 10,000 draws, none discarded) | **supported** (interval excludes 0; 12 of 12 grid entries positive) |
| H2 | National screening coverage, 2022 minus 2018 | 91.5% - 28.8% = 62.7 percentage points | 62.65 to 62.79 (Newcombe) | none (descriptive) |
| H3 | Units with identification below the benchmark in 2023, P(C2 < 1) ≥ 0.95 | 24 of 33 | - | none (descriptive) |

- **H1.** Identification rises with the diabetes burden: across units, the odds of a
  screened TB patient being identified with diabetes rise with the odds of raised blood
  sugar in adults (descriptive; the slope is not compared with 1). This is partly
  expected whatever the programme does, because both sources count treated diabetes. The
  model is ecological; with 33 units (Kish effective number of clusters 12.9) the
  bootstrap interval may be too narrow. The model-based Wald interval is 1.42 to 1.98
  (descriptive). The registered Spearman sensitivity gives ρ = 0.80 (Fisher-z interval with the Fieller-Hartley-Pearson variance,
  0.62 to 0.90; n = 33). Leaving out one unit at a time, β₁ ranges from 1.41 (without
  Tamil Nadu) to 1.83 (without Andhra Pradesh).
- **H2** restates published national percentages (seen before registration) with
  intervals. Coverage was 92.5% in 2023. The change of denominator basis between years
  matters more than the sampling intervals.
- **H3** is close to mechanical: by construction, 24 of the 33 pool units lie below
  k_b in 2021 + 2022, because k_b is the 75th percentile. "Below the benchmark" means below
  the identification achieved by the better quarter of units, relative to their diabetes
  burden; it is never a statement of widespread under-identification. On the plan's fixed
  rule (the 97.5th percentile of R = y/p_u below 1, at k = 1), 27 of 33 units show
  "likely under-detection" in 2023 (28 in 2022). Because p_u counts a random blood sugar
  above 140 mg/dl, k = 1 is a reference point, not a lower bound, and this count may
  partly reflect that threshold.

## The TB-diabetes cascade, national figures

Sums over the 33 units (main basis), with Wilson 95% intervals (all narrower than
±0.5 percentage points). C1: known diabetes status among notified TB patients. y:
diabetes identified among those screened. C3: started on anti-diabetic treatment among
those identified (2018: linked to an NCD clinic, a different definition, not compared
with later years).

| Data year | C1 screened | y identified | C3 initiated |
|---|---|---|---|
| 2018 | 28.8% (620,527 of 2,155,894) | 7.7% (47,678) | 39.7% linked to NCD clinic (18,913) |
| 2019 | 63.8% (1,535,450 of 2,404,815) | 7.4% (114,291) | 52.1% (59,489) |
| 2021 | 89.0% (1,900,043 of 2,135,830) | 8.3% (157,487) | 61.7% (97,146) |
| 2022 | 91.5% (2,215,930 of 2,421,666) | 7.8% (173,731) | 63.3% (110,058) |
| 2023 | 92.5% (2,361,944 of 2,552,257) | 7.7% (181,026) | 62.3% (112,858) |

No national identification ratio is formed (plan section 5.1).

## What the outputs show

All of the following are descriptive and carry no label. Units are listed
alphabetically within a tier.

- **Priorities, 2023 (`priority.csv`).** For the screening gap E1, the "act now" tier
  (P(top-5) ≥ 0.80) holds Bihar, Delhi, Madhya Pradesh, Uttar Pradesh and West Bengal; for
  the identification gap E2, Bihar, Gujarat, Maharashtra, Rajasthan and Uttar Pradesh.
  Every other unit is "lower priority" for each gap. With tens of thousands of screened
  patients per large unit, P(top-5) is close to 0 or 1, so the tiers reflect sampling
  uncertainty only; the larger uncertainty from p_u, k and recording is shown by the
  sensitivities. For the linkage gap E3 (identified, not started on treatment), the act
  now tier holds Andhra Pradesh, Bihar, Madhya Pradesh, Maharashtra and Uttar Pradesh.
  Leaving out one unit at a time changes the act-now sets by at most one or two units.
- **Decomposition, 2023 (`decomposition.csv`).** 22 units are identification-led (5 of
  them with a small total shortfall), 9 are screening-led (all with a small total
  shortfall) and 2 are mixed (both small). Where screening coverage is already high,
  most of the expected shortfall lies at the identification step.
- **Scenario, 2023 (`scenario.csv`), an illustration, not a forecast.** If every unit
  reached the benchmark coverage (96.3%) and yield (k_b·p_u), about 108,600 more TB
  patients with diabetes would be identified per year (107,970 to 109,330; the interval
  reflects binomial uncertainty only, not uncertainty in p_u or k_b). Five units
  (Bihar, Gujarat, Maharashtra, Rajasthan, Uttar Pradesh) account for 64% of it. At
  k = 1 the figure is about 162,000; at the median benchmark about 35,500.
- **Funnel (`funnel.csv`).** Relative to the across-unit relationship with p_u, Gujarat's
  identification lies below the 99.8% limit in 2019, 2021 and 2023; Karnataka and Tamil
  Nadu lie above it in some years. This may reflect testing, recording or the reference
  prevalence as much as missed diabetes.
- **Trend (`trend.csv`).** No unit has a "falling coverage" flag in the main model or
  any sensitivity model. Coverage rose steeply from 2018 to 2021, which may partly
  reflect the change of denominator basis.
- **Robustness.** Under a State-specific perturbation of p_u (1,000 replicates), for each of
  tier, H3 membership and class, 26-30 of 33 units keep it in ≥90% of replicates (21 keep
  all three; `perturbation.csv`); k_b ranges from 0.735 to 0.894. The k-grid, the simple reference,
  shrinkage off and the A1.2 denominator basis are in the `spec` columns.

The files are described in [`outputs/README.md`](outputs/README.md) and in plan section
10.3.

## Reproduction

Python 3.14 on any platform; versions in [`ENVIRONMENT.md`](ENVIRONMENT.md). Every script
is run as `python -I <script>` from the repository root, with LF line endings.

```sh
python -I -m pip install numpy==2.3.5 scipy==1.16.3 pdfplumber==0.11.8 pytest==9.0.0
python -I -m pip install "tbprio @ git+https://github.com/hssling/india-tb-priority-tool@v1.0.1"

# The source PDFs (not distributed): place them in data_raw/ and verify their digests
python -I tools/fetch_sources.py

# Extraction (data/extracted/) and its checks
python -I src/extract/itr_dm.py
python -I src/extract/nfhs.py
python -I verification/check_extraction_totals.py
python -I verification/check_implied_denominator.py

# Analysis (outputs/*.csv, about two minutes; byte-identical on rerun)
python -I src/run_all.py

# The whole verification: PASS / FAIL / SKIP per step
python -I verification/check_all.py
```

`check_all` runs pytest, `check_plan_order`, `check_deviations` (plan §12),
`check_extraction_totals`, `check_implied_denominator`, `check_outputs` (an independent
recompute with the Python standard library only: p_u, k_b, the 2023 cascade with R, H3
and the k = 1 count, E1 and E2, H1 by its own IRLS, the Spearman sensitivity, H2, the
scenario and the label) and `check_rerun` (the extraction and the analysis rerun and
compared byte for byte). The manuscript checks are skipped until the private manuscript
exists. Each check was shown to fail on a deliberate break:
[`verification/MUTATIONS.md`](verification/MUTATIONS.md). Without `data_raw/`, the
extraction parts are skipped and everything else runs on the committed extracts.

## Data sources

The source documents are Government of India publications. They are not redistributed
here; `data/source_manifest.csv` records each file's origin, size and SHA-256 digest.

- India TB Report 2019, India TB Report 2020, TB Annual Report 2022, India TB Report 2023
  and India TB Report 2024 (Central TB Division, Ministry of Health and Family Welfare;
  tbcindia.mohfw.gov.in): the TB-diabetes annexure tables (data years 2018, 2019, 2021,
  2022, 2023), the notification annexures, and the 2022 notified counts by sex and
  population.
- National Family Health Survey (NFHS-5), 2019-21, India and State/UT fact sheet
  compendiums, Phases I and II (Ministry of Health and Family Welfare and the
  International Institute for Population Sciences), obtained from dhsprogram.com
  (pubs/pdf/OF43): lines 101 (women) and 104 (men), "blood sugar level high or very high
  (>140 mg/dl) or taking medicine", ages 15 and over, Total column.

The extracted values (`data/extracted/`) carry their source file, PDF page and table on
every row.

## Limitations

- **NFHS-5 gives no confidence interval.** p_u is a point estimate. A common scaling of
  p_u cancels under k_b; the State-specific perturbation is the only check of
  State-level error. Small States and UTs have the smallest NFHS samples.
- **NFHS-5 measures random blood sugar.** A single random reading above 140 mg/dl, or
  taking medicine, is not a diagnosis of diabetes. p_u is a reference level of raised or
  treated blood sugar in adults aged 15 and over, not diabetes prevalence. The TB
  programme's test is not printed in any table and may differ by State and year.
- **"Identified" includes known diabetes.** The TB-diabetes count includes existing
  diabetes, so the analysis cannot say how much diabetes the TB programme newly found.
- **k_b is below 1 (0.822).** The benchmark is relative to the better quarter of units,
  and a quarter of units lie above it by construction. k = 1 is a reference point, not a
  guaranteed lower bound; k = 1.5 and 2 rest on published ratios and give much larger
  gaps. TB patients differ from the adult population in age and sex; NFHS covers ages 15
  and over while notifications include children; and the 2022 sex shares are used for
  every year.
- **The denominator bases differ by year.** 2018 uses current-facility notified from its
  own table, 2019 its own table, 2021 and 2023 Annexure 1.4 net notified and 2022 the
  Annexure 1.6 sex sum (§12.1). Coverage and its trend partly reflect these bases; the
  registered A1.2 basis is reported alongside.
- **State level only.** The analysis is ecological: H1 says nothing about individual
  patients. Small UTs are merged into larger units (Dadra and Nagar Haveli and Daman and
  Diu with Gujarat, Lakshadweep with Kerala, Ladakh with Jammu and Kashmir). No district
  TB-diabetes table is published.
- **Timing.** NFHS-5 fieldwork was 2019-21; the 2023 gaps apply that reference.
- **C3 definitions change**: "linked to NCD clinic" in 2018, "initiated on anti-diabetic
  treatment" from 2019.
- **Recording.** Reporting artefacts (known status above notified, diabetic above tested)
  are set to NA and listed in `outputs/na_cells.csv`.

## Repository layout

- `docs/analysis_plan.md`: the registered plan (deviations dated in plan §12);
  `docs/registration_event.json`; `docs/data_inventory.md` (structure only, before
  registration); the design and implementation plan under `docs/superpowers/`.
- `data/source_manifest.csv`; `data/extracted/`: the extracted panel, NFHS-5 values, sex
  counts, the plan §12.1 sensitivity files and the extraction checks.
- `src/extract/`: the extraction; `src/dmgap/` and `src/run_all.py`: the analysis, which
  imports the author's TB priority tool package `tbprio` pinned to v1.0.1.
- `outputs/`: the results; `verification/`: the checks; `tests/`.

## Citation and licences

Cite as in [`CITATION.cff`](CITATION.cff). Version 1.0.0 is archived on Zenodo:
[10.5281/zenodo.24425259](https://doi.org/10.5281/zenodo.24425259) (all versions:
[10.5281/zenodo.24425258](https://doi.org/10.5281/zenodo.24425258)). Author: Siddalingaiah H S
(ORCID [0000-0002-4771-8285](https://orcid.org/0000-0002-4771-8285)), Department of
Community Medicine, Shridevi Institute of Medical Sciences and Research Hospital, Tumkur,
Karnataka, India.

Code (`src/`, `tools/`, `tests/`, `verification/`): MIT ([`LICENSE`](LICENSE)). Derived
data (`data/`, `outputs/`): CC BY 4.0 ([`LICENSE-DATA`](LICENSE-DATA)). The source
publications remain the property of their publishers and should also be cited.
