# Pre-registered analysis plan: the diabetes–TB gap in India's States

**Date of this plan:** 21 November 2026
**Author:** Siddalingaiah H S, MD, Professor, Department of Community Medicine, Shridevi Institute of Medical Sciences and Research Hospital, Tumkur 572106, Karnataka, India. ORCID 0000-0002-4771-8285. hssling@yahoo.com. Single author.
**Repository:** https://github.com/hssling/india-tb-diabetes-gap
**Status:** registered before any estimate was computed. The registration point (the commit SHA and the UTC time of the public push, taken from the GitHub API) is recorded in `docs/registration_event.json`. `verification/check_plan_order.py` checks that the text above §12 is byte-identical at every later commit, and that no file under `src/dmgap/` (the analysis package), `data/extracted/` or `outputs/` was committed before the registration commit. The registration record must name the full 40-character commit SHA and may never be re-pointed.
**Design:** `docs/superpowers/specs/2026-11-21-tb-diabetes-gap-design.md` (approved by the author on 21 November 2026). **Implementation plan:** `docs/superpowers/plans/2026-11-21-tb-diabetes-gap.md`, sections "Global Constraints", "Fixed analysis values", "Strengthened analyses" and "Controller rulings after Task 1". **Data inventory (structure only):** `docs/data_inventory.md`. Where any of these and this plan differ, this plan governs.

**Conventions in this plan.**
- A paragraph marked **Constraint (verbatim)** copies the implementation plan's "Global Constraints" word for word.
- A paragraph marked **Fixed (verbatim)** copies its "Fixed analysis values" word for word.
- A paragraph marked **Strengthened (verbatim)** copies its "Strengthened analyses (21 Nov 2026 …)" word for word.
- A paragraph marked **Ruling (verbatim)** copies its "Controller rulings after Task 1 (21 Nov 2026 …)" word for word.
- **Precedence.** Ruling, then Strengthened, then Fixed, then Constraint: the later, more specific text overrides the earlier one where they differ. Every difference is settled in a paragraph marked **Resolution**, and all are listed in §1.4.
- A paragraph marked **Operational detail** fixes how a value is applied. These details were settled when this plan was written, before any estimate.
- "Edition" is the report; "data year" is the year its State tables describe (§3.2). "Unit" is a State or UT after coarsening (§4.1).
- **Notation.** k is always the reference multiplier (§5.2). The number of top places in a priority probability is always written out: P(top-5). For unit u and data year t: N_ut notified TB patients (the C1 denominator, §3.4); K_ut TB patients with known diabetes status ("tested"); D_ut TB–DM patients identified ("diabetic"); I_ut TB–DM patients initiated on anti-diabetic treatment (linked to an NCD clinic in 2018); U_ut = N_ut − K_ut untested; p_u the reference prevalence as a proportion (§4.4). The subscript t is dropped where the year is clear.
- Every percentile is `numpy.percentile(..., method="linear")`. "95% interval" means the 2.5th and 97.5th percentiles of 10,000 draws unless another method is named.

---

## 1. Background and scope

### 1.1 Purpose

Diabetes roughly triples the risk of TB and worsens TB treatment outcomes, and India carries the world's largest joint burden. India's 2018 National Framework for Joint TB–Diabetes Collaborative Activities makes diabetes screening of every notified TB patient the standard. The India TB Reports print, by State, how many TB patients have a known diabetes status, how many of those were found to have diabetes, and how many of those were started on anti-diabetic treatment. NFHS-5 (2019–21) prints each State's prevalence of high blood sugar, or treatment for it, in adults.

The question is: in each State, how many TB patients with diabetes are likely going unidentified, and is the shortfall at the screening step or at the identification step? The users are the Central TB Division (CTD), the State TB Cells and the National Programme for Prevention and Control of Non-Communicable Diseases (NP-NCD), for integrating TB and diabetes services. The framing is constructive and practice-guiding, not a critique.

### 1.2 Scope

- Published, aggregate, official data only (§3). No individual-level data.
- The unit is the State or UT after coarsening (§4.1). There is no district analysis, because no district TB–diabetes table is published.
- The main priority year is data year 2023 (§3.2).
- Harm is counted in natural units: TB patients with diabetes not identified (§5.4, §5.5). The screening and identification gaps are reported separately and also added, because they count the same kind of patient.
- Out of scope: causal effects of any intervention; estimating national diabetes prevalence; modelling diabetes prevalence among TB patients from age- and sex-specific data (the State fact sheets print no age-specific diabetes; the multiplier k covers this, §5.2).

### 1.3 Wording

**Constraint (verbatim).**
- Wording:
  - "likely under-detection" only when the 95% interval of R lies wholly below 1;
  - no causal language; tiers, not ranks;
  - low detection may reflect true lower prevalence, the testing method or recording; say so.

**Ruling (verbatim).** **C2 meaning.** The ITR TB–DM count includes "already existing" diabetes (ITR 2019 narrative, p. 65). C2 is therefore "diabetes identified among screened TB patients, newly diagnosed or known". It is comparable with NFHS-5, which also counts people taking medicine. The wording is "identified", never "newly diagnosed".

**Operational detail.**
- "Likely under-detection" is used only under the rule of §5.6 (R at k = 1). A unit whose yield is below the data-driven benchmark (§5.6, k = k_b) is described as "identification below the benchmark", a relative statement, never as "under-detection".
- Where the fixed and strengthened texts say "detection" or "diagnosed" for the C2 step, the reported wording is "identification" or "identified" (ruling above).
- Wherever a low ratio, a gap or a priority is reported, the text says that it may reflect a truly lower prevalence among the State's TB patients, the testing method or recording, and not only missed diabetes.
- Results describe programme data, not the performance or effort of any State's staff. No State is described as failing or to blame. Headline text uses tiers, never ranks.

### 1.4 Precedence and the conflicts settled in this plan

| # | Topic | Earlier text | Later text that governs | Settled in |
|---|---|---|---|---|
| 1 | Data years | Fixed: 2018, 2021, 2022. Design §3: ITR 2020 and ITR 2024 print no State table | Ruling: five years, 2018, 2019, 2021, 2022, 2023; 2020 dropped. The inventory found the ITR 2020 and ITR 2024 tables | §3.2 |
| 2 | Main priority year | Fixed: 2022 | Ruling: 2023 | §6.1 |
| 3 | Trend | Fixed: 2018, 2021, 2022; no COVID indicator | Ruling: 2018, 2019, 2021, 2022, 2023, with the 2021 indicator, as in the priority tool | §7 |
| 4 | Multiplier k | Fixed: main 1; sensitivities 1.5 and 2 | Strengthened: main k_b; sensitivities k = 1, 1.5, 2, the median and best-decile benchmarks | §5.2 |
| 5 | Detection ratio | Fixed: R = y/p_s | Strengthened: C2 = y/(k·p_s). Here R_k = y/(k·p_u); R_1 is the fixed R; C2 is R at k = k_b | §5.1, §5.6 |
| 6 | "Likely under-detection" and H3 | Fixed and Constraint: the 95% interval of R wholly below 1, at k = 1; H3 counts these units in 2022 | Strengthened: H3 counts units with C2 below the benchmark at 95% posterior probability. Settled here: H3 follows the ruled main priority year, 2023 (out-of-pool); 2022 reported alongside. The k = 1 rule keeps the phrase and is reported alongside H3 | §5.6, §8.7 |
| 7 | H1 estimate | Fixed: Spearman ρ, Fieller interval | Strengthened: quasi-binomial slope β₁ with a cluster bootstrap; Spearman kept as a registered sensitivity | §8.2–§8.4 |
| 8 | H1 years | Fixed: 2021 + 2022 pooled; Strengthened: year effect (2021, 2022) | Ruling: 2019 + 2021 | §8.2 |
| 9 | H1 grid | Fixed: weighting × year {2021, 2022, pooled} × shrinkage of y | Strengthened: reference × year set × weights. Ruling: year-set axis {2019 + 2021, 2021–2023, 2023 alone} | §8.8 |
| 10 | "Hierarchical" regression | Strengthened title: "Hierarchical regression" | Strengthened text: a quasi-binomial model with a cluster bootstrap over units. No random effect is fitted; the nesting of unit-years in units is handled by the cluster bootstrap | §8.2 |
| 11 | H2 | Fixed: national coverage 2018 vs 2022 | Strengthened: unchanged. Ruling: silent. Kept as 2018 vs 2022; the other three years reported alongside | §8.6 |
| 12 | k_b pool | Strengthened: pooled 2021 and 2022 | Ruling: silent (it moves only H1 to 2019 + 2021). Kept; a 2019 + 2021 pool added as a sensitivity | §5.2 |
| 13 | NFHS unit merging | Fixed: NFHS-5 population weights, else ITR population | Ruling: ITR 2023 A1.1 population (the fact sheets print none) | §4.3 |
| 14 | C1 denominators | Fixed: "notified" | Ruling: each year's own table where printed, else A1.2; 2018 flagged; a sensitivity drops 2018 | §3.4 |
| 15 | C3 | Strengthened: used where printed as counts | Ruling: main C3 uses the "initiated on treatment" years; 2018 shown separately and flagged | §5.1 |
| 16 | NCD-reach check | Strengthened item 7: computed only if the fact sheets print the components | The fact sheets do not print them: dropped before registration | §9.1 |
| 17 | Leave-one-out tiers | Fixed: the 2022 act-now sets | Ruling: main priority year 2023; 2022 reported alongside | §8.10 |
| 18 | Design robustness grid | Design §4: k × weighting × year × shrinkage | Superseded by the H1 grid (§8.8); k, weighting and shrinkage become named sensitivities (§5.7) | §5.7 |
| 19 | Seed | The tbprio package's own constant is 20261121 | Constraint: 20261122. tbprio's seed constant is not used | §10.1 |
| 20 | Task 5 verification text | "H1 and its Fieller interval" | H1 is now β₁; the recompute covers β₁ and the Spearman sensitivity with its Fieller interval | §10.4 |
| 21 | Shrinkage of y | Fixed H1 grid axis | Removed from the grid by the Strengthened grid; kept as a sensitivity of the priorities (shrinkage off) | §5.7 |
| 22 | k = 1 as "lower bound" | Fixed and Strengthened: k = 1 "(lower bound)" | Settled here: k = 1 is a reference point, not a guaranteed lower bound, because p_u's random-glucose threshold is below diagnostic thresholds (§10.5). The quoted words stay verbatim and are read this way | §5.2, §10.5 |

---

## 2. Questions and hypotheses

- **Q1. The care cascade.** For each unit and data year: what share of notified TB patients was screened for diabetes (C1); how does the share identified with diabetes among those screened compare with what the unit's diabetes burden implies (C2); and what share of those identified was started on anti-diabetic treatment (C3)? (§5.1)
- **Q2. The two gaps and where to act.** How many TB patients with diabetes are likely unidentified because they were not screened (E1), and how many among those screened (E2)? In which units would closing each gap identify the most, how certain is each unit's place among the top five, and is each unit's shortfall screening-led or identification-led? (§5.4–§6.3)
- **Q3. Trend.** Is screening coverage rising or falling in each unit over 2018–2023? (§7)
- **Q4. Does identification follow burden?** Across units, is the TB–DM yield higher where diabetes is more prevalent (H1)? Which units identify well below what their burden predicts (the funnel)? (§8.2–§8.5)
- **Q5. National picture.** How did national screening coverage change between 2018 and 2022 (H2)? How many units identify below the benchmark (H3)? How many more TB patients with diabetes would be identified each year if every unit reached the benchmark coverage and yield (the scenario)? (§6.4, §8.6, §8.7)

H1 is the only labelled estimate (§8.9). H2, H3, the scenario and all sensitivities are descriptive.

---

## 3. Data sources, data years and data rules

### 3.1 Files

All files are local copies, verified by SHA-256 against `data/source_manifest.csv`. They are kept in `data_raw/`, which is not committed and not redistributed.

| File (`data_raw/…`) | Edition or document | Data year | SHA-256 | Use |
|---|---|---|---|---|
| `india_tb_report/India-TB-Report-2019.pdf` | India TB Report (ITR) 2019 | 2018 | `87e546751372ba157cb9eba1620173d54aad0fb99abc1b99f4302e9a2005c03b` | N, K, D, I (linked) |
| `india_tb_report/ITR2020.pdf` | ITR 2020 | 2019 | `63b9408015dae510858e0eef2711e809d398bfe3149dd21c94390b258c007e7e` | N, K, D, I |
| `india_tb_report/TBAnnaulReport2022.pdf` | TB Annual Report 2022 (TBAR 2022) | 2021 | `dc9ff4a88a28eb87232770d0956fe92b2b266b15e5794f879a7335b7c083418b` | N, K, D, I |
| `india_tb_report/ITR2023.pdf` | ITR 2023 | 2022 | `0817ac3a1e7a03273438073d4e685f88aa93507ad115ec5c6588edfddc8f0b7b` | N, K, D, I; notified by sex (f_u); population for NFHS merging |
| `india_tb_report/ITR2024.pdf` | ITR 2024 | 2023 | `e37f9f406153b5e9a19726538c3f4d09dc4c470281c34fe511adaa56a0e22765` | N, K, D, I |
| `nfhs5/NFHS-5_India_and_State_Factsheet_Compendium_Phase-I.pdf` | NFHS-5 State and UT fact sheets, Phase I (22 sheets) | fieldwork 2019–20 | `5bcc2a37b13ffc0203d736803f72aece88b4beb0bc168d1f069e110178ab2bd7` | w_u, m_u |
| `nfhs5/NFHS-5_India_and_State_Factsheet_Compendium_Phase-II.pdf` | NFHS-5 India and State/UT fact sheets, Phase II (India + 14 sheets) | fieldwork 2020–21 | `3e8ee12bb4a59e9ec2e7bebc736b2252d61e9ed98ce322717debe11dd73c52b7` | w_u, m_u |

**Constraint (verbatim).** `data_raw/` and `manuscript/` are never committed. Source digests go in `data/source_manifest.csv`. No new downloads without asking the author.

ITR 2020 is copied from `../tb_priority_tool/data_raw/india_tb_report/ITR2020.pdf` and added to `data/source_manifest.csv` with the digest above by `tools/fetch_sources.py`, before extraction (ruling, §3.2). ITR 2021 (data year 2020) is a scan and is not used. No other source is used. A new source is added only with the author's approval, and its addition is logged in §12.

### 3.2 Data years

**Fixed (verbatim).** **Data years:** 2018 (ITR 2019 Annexure 1.2 diabetes columns), 2021 (TB Annual Report 2022 Annexure 2.5), 2022 (ITR 2023 Annexure 2.10). If Task 1 finds that a year does not print both the tested and the diabetic counts, it is dropped and the reason recorded.

**Ruling (verbatim).** **Data years: five.**

  | Data year | Source |
  |---|---|
  | 2018 | ITR 2019 A1.2 |
  | 2019 | ITR 2020 A2.5, pp. 216–217 |
  | 2021 | TBAR 2022 A2.5 |
  | 2022 | ITR 2023 A2.10 |
  | 2023 | ITR 2024 A2.10, pp. 211–212 |

  2020 is dropped (ITR 2021 is a scan). ITR 2020 is added to the manifest from the tb_priority_tool copy. ITR 2020 A2.6 is titled "TB - Tobacco" but carries diabetes headers with different values; A2.5 is used and the discrepancy is recorded.

**Ruling (verbatim).** **Main years.** The main priority year is 2023, the latest. The trend uses 2018, 2019, 2021, 2022 and 2023, with tbprio's empirical-logit WLS, φ, and the 2021 indicator, exactly as in the priority tool. H1 pools 2019 and 2021, the data years matching NFHS-5 fieldwork (2019–21). The H1 grid's year-set axis becomes {2019 + 2021 (main), 2021–2023, 2023 alone}.

**Resolution.** The ruling governs: the data years are 2018, 2019, 2021, 2022 and 2023. Each of the five tables prints both the tested and the diabetic counts (inventory), so none is dropped under the fixed rule. No value is taken from ITR 2021 or from ITR 2020 A2.6. Edition to data year: ITR 2019 → 2018; ITR 2020 → 2019; TBAR 2022 → 2021; ITR 2023 → 2022; ITR 2024 → 2023.

### 3.3 Source table and column for each data year

Column headers are quoted as printed (`docs/data_inventory.md`). "Total" means the Total sub-column of a Public/Private/Total group; "count part" means the count of a printed `count (%)` or `n (%)` cell. PDF pages are the 1-based pages of the files in §3.1. In every year the Total column is used, never Public or Private alone.

| Data year | Table (PDF pp.) | K: known status | D: diabetic (TB–DM) | I: treatment step | N: notified (C1 denominator) |
|---|---|---|---|---|---|
| 2018 | ITR 2019 A1.2 "TB Comorbidities" (169–170, rotated) | "Total TB patients with known blood sugar status (%)", count part | "Total TB- DM Co- morbid patients (%)", count part | "TB-DM Co-morbid patients Linked to NCD Clinic (%)", count part (flag `c3_linked_ncd_clinic`) | same table: "Total TB patients Notified (notified cases based on current PHI)" (flags `denominator_own_table`, `denominator_current_phi`) |
| 2019 | ITR 2020 A2.5 "TB-Diabetes" (216–217) | "TB patients with known DM status (%)", Total, count part | "TB Patients diagnosed with Diabetes among tested (%)", Total, count part | "TB- DM patients initiated on Anti-diabetic treatment (%)", Total, count part | same table: "TB Patients notified", Total (flag `denominator_own_table`; Task 3 records any stated basis) |
| 2021 | TBAR 2022 A2.5 "TB-Diabetes" (96) | "TB patients with known DM status (%)", Total, count part | "TB - DM Patients diagnosed among tested (%)", Total, count part | "TB- DM patients initiated on Anti-diabetic treatment (%)", Total, count part | TBAR 2022 A1.2 "TB Case Notification" (89): "TB patients notified (Achievement against target %)", Total, count part (flag `denominator_a1_2_diagnosing_phi`) |
| 2022 | ITR 2023 A2.10 "TB - DIABETES" (239–240) | "TB patients with known DM status, n (% of notified)", Total, count part | "TB - DM Patients diagnosed among tested, n (% of those with known DM status)", Total, count part | "TB- DM patients initiated on Anti- diabetic treatment, n (% of TB-DM)", Total, count part | ITR 2023 A1.2 "TB CASE NOTIFICATION" (213–214): "TB patients notified, n (% achievement against target)", Total, count part (flag `denominator_a1_2_diagnosing_phi`) |
| 2023 | ITR 2024 A2.10 "TB - Diabetes" (211–212) | "TB patients with known DM status, n(%)", Total, count part | "TB - DM patients diagnosed among tested, n(%)", Total, count part | "TB- DM patients initiated on anti-diabetic treatment, n(%)", Total, count part | ITR 2024 A1.2 "TB case notification" (187–188): "TB patients notified, n(% of achievement against target)", Total, count part (flag `denominator_a1_2_diagnosing_phi`) |

**Ruling (verbatim).** **Extraction method.** Task 3 reads rotated ITR 2019 cells by cell position (pdfplumber words with coordinates) or whole rows, not line text.

Other inputs:
- **Notified by sex (f_u, §4.4):** ITR 2023 A1.6 "GENDER DISAGGREGATED DATA ON TOTAL TB NOTIFICATION, PAEDIATRIC TB NOTIFICATION AND TREATMENT INITIATION", PDF pp. 221–222, "TB Cases Notified (Male, Female, Trans Gender)". Written to `data/extracted/tb_sex_2022.csv`.
- **Population (NFHS unit merging only, §4.3):** ITR 2023 A1.1 "PRESUMPTIVE TB CASES EXAMINATION", PDF p. 211, "Popula- tion - 2022 (in lakhs)". Written to the `population` column of `data/extracted/nfhs_dm.csv`.
- **NFHS-5 (§4.2):** fact-sheet lines 101 (women) and 104 (men), NFHS-5 Total column, at the pages listed in the inventory. Written to `data/extracted/nfhs_dm.csv`.
- The panel `data/extracted/dm_panel.csv` has the columns `unit, year, measure, value, source_file, pdf_page, table_id, flag`, with measure ∈ {notified, known_status, diabetic, initiated}. The 2019 records carry the flag `itr2020_a26_discrepancy`, recording that A2.6 prints diabetes-worded headers with different values and is not used.

### 3.4 Denominators and flags

**Ruling (verbatim).** **Denominators.** Coverage C1 uses notified from each year's own table where printed. Otherwise it uses A1.2 (diagnosing PHI) for 2021–2023. 2018 uses current PHI (flagged). 2019 is per its table (Task 3 records it). The flag is carried; the sensitivity analysis drops 2018.

**Operational detail.**
- The C1 denominators are those of §3.3. The C2 denominator is K (known status) and the C3 denominator is D (diabetic), from the same diabetes table, every year.
- "The sensitivity analysis drops 2018" is applied to the trend (§7.3), the only main analysis that uses 2018 C1 across years. H2 compares 2018 with 2022 by the fixed definition; its 2018 value carries the flag, and H2 is also reported as 2019 vs 2022 (§8.6).
- **Denominator-basis sensitivity, 2022 (fixed here).** The companion priority tool found (its plan §12.2) that the percentages of ITR 2023 Annexure 2.1 imply denominators matching ITR 2023 A1.6 (male + female + transgender), not A1.2. The 2022 diabetes table prints "% of notified" on its known-status column, so the same may hold. The main 2022 denominator stays A1.2, as ruled. Every 2022 quantity that uses N (C1, E1, the 2022 priorities of E1 and of the total, H2, the trend) is also reported with N = the A1.6 sum for the same unit (flag `denominator_a1_6_sensitivity`).
- **Implied-denominator check (an extraction check, not an estimate).** At extraction (Task 3, after registration), for every Total known-status cell that prints a percentage, K ÷ (printed % ÷ 100) is compared with the registered N. The comparison is recorded in the extraction check and does not change the main analysis. Any change made because of it is a dated deviation in §12.

### 3.5 Data rules

**Constraint (verbatim).** No imputation. NA cells are listed. Every value carries source_file, pdf_page and table_id. Printed totals are checked.

**Operational detail.**
- **Printed totals.** For every table, the sum of the printed State/UT rows (before coarsening) is compared with the printed India row, column by column. A difference is recorded with its size in the extraction check. It is not corrected, and the State values are used as printed.
- **Impossible or empty cells** (Review Focus 1). For a unit-year: C1 is NA when K > N or N = 0; C2 (and y) is NA when D > K or K = 0; C3 is NA when I > D or D = 0. Each NA is listed in `outputs/na_cells.csv` with its reason. An NA measure removes the unit-year only from the quantities that use it: a unit with C1 NA still enters E2 if its y is valid, and the reverse.
- **Percent-only cells** (Review Focus 3). Counts are taken when printed. Where only a percentage is printed, the count is derived as round-half-up(base × % ÷ 100), with the rounding interval recorded and the flag `derived_from_percent`. The inventory found no Total cell that needs this.
- Where a cell prints both a count and a percentage, the count is used and the percentage is not.
- Definitional changes between editions are recorded as flags, not harmonised: `denominator_current_phi` (2018), `known_blood_sugar_status_wording` (2018, "known blood sugar status" rather than "known DM status"), `c3_linked_ncd_clinic` (2018), `denominator_a1_2_diagnosing_phi` (2021–2023).

---

## 4. Units, crosswalk and reference prevalence

### 4.1 Units

**Fixed (verbatim).** **Units:** the tb_priority_tool coarsening (DNH&DD with Gujarat, Lakshadweep with Kerala, Ladakh with J&K), applied every year. NFHS units are merged into the same units by NFHS-5 population weights; if the fact sheets lack population, the ITR population is used.

**Operational detail.**
- In every data year, the following printed rows are added to the named unit before any rate is formed:
  - "Dadra & Nagar Haveli" and "Daman & Diu" (two rows in ITR 2019 and ITR 2020), or "Dadra and Nagar Haveli and Daman and Diu" (one row from TBAR 2022 onwards) → **Gujarat**;
  - Lakshadweep → **Kerala**;
  - Ladakh (a separate row from TBAR 2022 onwards) → **Jammu and Kashmir**. ITR 2019 and ITR 2020 print no Ladakh row; their Jammu & Kashmir row is used as printed.
- This gives 33 units in every data year: the 36 printed rows less the three merged.
- Merging sums N, K, D, I, the notified-by-sex counts and the population over the member rows.
- Each edition's printed names, and the NFHS sheet names, are mapped by an explicit crosswalk (`src/extract/crosswalk.py`), for example "NCT Delhi" → Delhi, "Tamil nadu" → Tamil Nadu, "Dadra & Nagar Haveli and Daman & Diu" → Gujarat. A name not in the crosswalk stops extraction with an error that names it (Review Focus 2). An ITR unit with no NFHS match, or an NFHS sheet with no TB unit, is likewise an error.
- A member row that is absent, blank or NA adds nothing; the merged unit carries the flag `member_missing:<name>` and is listed in `outputs/na_cells.csv`. A unit whose members are all NA is NA for that measure and year.
- Small UTs are not separately analysed; they are reported only within the unit they join. This is a stated limitation.

### 4.2 NFHS-5 inputs

**Ruling (verbatim).** **NFHS-5 inputs.** NFHS-5 totals are used. There is no population in the fact sheets, so unit merging uses ITR 2023 A1.1 population. The DNH&DD sheet is already merged.

**Operational detail.**
- Women w and men m: the NFHS-5 **Total** column (not Urban, not Rural, not NFHS-4) of line 101 "Blood sugar level - high or very high (>140 mg/dl) or taking medicine to control blood sugar level23 (%)" (women) and of line 104, with the same wording (men), in the section "Blood Sugar Level among Adults (age 15 years and above)" of each State/UT sheet. Footnote 23: "Random blood sugar measurement." The printed percentage is divided by 100.
- A Total cell printed in parentheses (25–49 unweighted cases) is used and flagged `nfhs_small_sample`; a starred cell (percentage not shown) is NA. The inventory found neither on lines 101 and 104.
- The India sheet is not used for p_u.

### 4.3 Merging NFHS units

For a coarsened unit with member sheets j (Gujarat with "Dadra & Nagar Haveli and Daman & Diu"; Kerala with Lakshadweep; Jammu & Kashmir with Ladakh), with ITR 2023 A1.1 population P_j (in lakhs, as printed):
- w_u = Σ_j P_j·w_j ÷ Σ_j P_j, and m_u = Σ_j P_j·m_j ÷ Σ_j P_j.
- The same total-population weights are used for women and for men, because no sex-specific population is printed. This is stated.
- The population of the "Dadra & Nagar Haveli and Daman & Diu" sheet is the sum of whatever member rows ITR 2023 A1.1 prints for it. A member with no printed population stops the merge with an error that names it.
- Every other unit has one sheet and takes its values unchanged.

### 4.4 Reference prevalence p_u

**Fixed (verbatim).** **Reference prevalence p_s:** NFHS-5 "blood sugar level high or very high (>140 mg/dl) or taking medicine", ages 15+, women w_s and men m_s. Then p_s = f_s·w_s + (1 − f_s)·m_s, where f_s is the female share of the State's notified TB patients in 2022 (ITR 2023 A1.6; transgender patients go with men for weighting, stated). Sensitivity: the simple average (w_s + m_s)/2.

**Operational detail.**
- Here p_u is the implementation plan's p_s, for unit u.
- f_u = Female ÷ (Male + Female + Transgender), from the ITR 2023 A1.6 "TB Cases Notified" columns, summed over the unit's member rows (§4.1). Transgender patients enter the denominator and are weighted with men.
- The 2022 f_u is used for every data year; one NFHS round gives one p_u per unit for all years.
- Main: p_u = f_u·w_u + (1 − f_u)·m_u ("sex-weighted"). Sensitivity: p_u = (w_u + m_u)/2 ("simple"). Wherever the simple reference is used, every quantity built on p_u, including k_b (§5.2), is recomputed with it.
- p_u carries no sampling interval: the fact sheets print none. Its uncertainty is handled by the sensitivity of §8.11.

---

## 5. The cascade, the benchmark multiplier and the two gaps

### 5.1 The TB–diabetes care cascade

**Strengthened (verbatim).**
1. **The TB–diabetes care cascade (the headline novelty).** Three steps per State and year:
   - C1 screened = known status ÷ notified;
   - C2 diagnosed = the detection ratio R = y/(k·p_s);
   - C3 linked = TB–DM patients initiated on diabetes treatment ÷ TB–DM diagnosed.

   C3 is used only where Task 1 finds it printed as counts or as derivable counts. A novelty check on 21 Nov 2026 found no State-level TB–diabetes cascade for India.

**Ruling (verbatim).** **C3 definitions.** C3 linkage is "linked to NCD clinic" in 2018 and "initiated on anti-diabetic treatment" from 2021 (2019: Task 3 records the header). The main C3 uses the years with the "initiated on treatment" definition. 2018 is shown separately and flagged.

**Operational detail.** For each unit u and data year t with the needed non-NA cells:
- **C1** (screened) = K/N. 95% interval: the Jeffreys interval, the 2.5th and 97.5th percentiles of Beta(½ + K, ½ + N − K), by `scipy.stats.beta.ppf`.
- **y** (identified among screened) = D/K, with the same Jeffreys interval.
- **C2** = R at k = k_b: C2 = y/(k_b·p_u), with the draw-based interval of §5.6. Its label in text is "diabetes identified among screened TB patients, newly diagnosed or known, relative to the benchmark expectation". R at k = 1, 1.5 and 2 is reported alongside.
- **C3** (initiated) = I/D, with the Jeffreys interval. All five tables print C3 as counts. The ITR 2020 A2.5 header for 2019 reads "TB- DM patients initiated on Anti-diabetic treatment (%)" (inventory; Task 3 re-records it), so the main C3 uses 2019, 2021, 2022 and 2023. If Task 3 finds a different 2019 header, 2019 C3 is shown separately like 2018, and this is recorded in §12. 2018 ("Linked to NCD Clinic") is reported in a separate column with the flag `c3_linked_ncd_clinic` and is not compared with the other years.
- **Linkage gap E3** = D − I (identified, not initiated), with Jeffreys draws of C3. It is reported with P(top-5) and tier for 2023, and it is not added to E1 + E2. A unit whose C3 is below the 75th percentile of units' C3 with probability ≥ 0.95 is described as 'linkage below the benchmark'.
  - Operational detail: for each data year with the main C3 definition (2019, 2021, 2022, 2023), a C3 draw set: a fresh `numpy.random.default_rng(20261122)`; the units with non-NA C3, in the order of §5.3; c3^(d) = `rng.beta(½ + I, ½ + D − I, size=10000)`; E3^(d) = D·(1 − c3^(d)). P(top-5) = `tbprio.priority.p_topk` and tier = `tbprio.priority.tier(·, False)`, as in §6.1. The linkage benchmark c3_b = the 75th percentile, across the year's units with non-NA C3, of the Jeffreys posterior means (½ + I)/(1 + D); "linkage below the benchmark" when the share of draws with c3^(d) < c3_b is at least 0.95. 2018 (linked to an NCD clinic) has no E3 tier. Headline E3 tiers are for 2023; the other years are reported alongside.
- **Cumulative cascade (descriptive, fixed here).** C1·C2 = D ÷ (N·k_b·p_u), the TB patients identified with diabetes as a share of those expected among all notified; and C1·C2·C3 = I ÷ (N·k_b·p_u), those started on treatment as a share of those expected. Both can exceed 1. No interval, no tier, no label.
- National values for each year (sums of N, K, D and I over the units with non-NA cells) are reported for C1, y and C3 with Wilson intervals (§8.6). No national R is formed.
- The cascade is descriptive; it has no tier and no label.

### 5.2 The benchmark multiplier k_b

**Fixed (verbatim).** **k:** main 1 (lower bound); sensitivities 1.5 and 2.

**Strengthened (verbatim).**
2. **Data-driven reference multiplier (main analysis).** Assuming k is replaced by an estimated benchmark:
   - k_b = the 75th percentile, across units, of the shrunken ratio y/p_s (pooled 2021 and 2022), the same benchmark logic as tbprio;
   - expected yield = k_b·p_s;
   - sensitivities: k = 1 (lower bound), 1.5 and 2 (published TB:population diabetes ratios, Crossref-verified at the manuscript stage), and the median and best-decile benchmarks.

**Resolution.** The strengthened text governs: the main multiplier is k_b; k = 1, 1.5 and 2 and the median and best-decile benchmarks are sensitivities. The rulings do not change the k_b pool (they move only H1 to 2019 + 2021, §8.2), so the pool stays 2021 + 2022. Because H1's reason (matching NFHS-5 fieldwork) applies to k_b too, a pool of 2019 + 2021 is added as a sensitivity, defined over the units with non-NA y in both 2019 and 2021.

**Operational detail.**
- **Units.** Those with non-NA y in both 2021 and 2022. Excluded units are listed; k_b still applies to them.
- **Pooled counts.** x_u = D_u,2021 + D_u,2022 and n_u = K_u,2021 + K_u,2022.
- **Shrinkage.** (α, β) = `tbprio.shrink.beta_binomial(x, n)` over these units. Posterior mean ŷ_u = (α + x_u)/(α + β + n_u).
- **Ratio and benchmark.** g_u = ŷ_u / p_u. Main k_b = the 75th percentile of g_u across the units ("p75"). Sensitivities: the 50th percentile ("median") and the 90th percentile ("p90", best decile). A higher g is better identification, so these are the 75th, 50th and 90th percentiles of performance, as in tbprio.
- k_b is computed once per specification from the posterior means. It is not redrawn per draw. The same k_b is applied to every data year.
- k_b is used as computed, without a floor. If k_b < 1, that is reported, and the k = 1 analysis then gives the larger expected yield.
- **Shrinkage off** (a sensitivity): α = β = ½ (`tbprio.shrink.JEFFREYS_BINOMIAL`) in place of the empirical-Bayes prior, so that ŷ_u = (½ + x_u)/(1 + n_u).
- Every value of k_b, with its specification and number of units, is written to `outputs/benchmark.csv`.
- By construction, about a quarter of units lie above k_b. "Below the benchmark" is therefore a relative statement: below the identification achieved by the better quarter of units, relative to their diabetes burden.

### 5.3 Draw sets

A **draw set** is defined by a data year t, a prior mode (empirical Bayes, the main; or Jeffreys) and, for 2022 only, a denominator basis (A1.2, the main; or A1.6, §3.4). Draws do not depend on p_u or k, which enter only afterwards.

**Operational detail.**
- **Priors.** Empirical Bayes: the untested share has (a₁, b₁) = `tbprio.shrink.beta_binomial(U, N)` over the units with non-NA C1 in the year; the yield has (a₂, b₂) = `tbprio.shrink.beta_binomial(D, K)` over the units with non-NA y in the year. Jeffreys: (a₁, b₁) = (a₂, b₂) = `tbprio.shrink.JEFFREYS_BINOMIAL` = (½, ½).
- **Special cases.** If ΣU = 0 over the year's units (nobody untested), no untested-share draws are taken, every E1 draw is 0, and the year is reported as having no screening gap. If `tbprio.shrink.beta_binomial` raises for any other reason (fewer than 2 units, or a pooled rate of 0 or 1), the Jeffreys prior is used for that year and quantity, with the flag `prior_fallback_jeffreys`.
- **Order.** A fresh `numpy.random.default_rng(20261122)` is created for each draw set. Units are processed in alphabetical order of unit name. For each unit, first (if its C1 is non-NA) s^(d) = `rng.beta(a₁ + U, b₁ + K, size=10000)`, the untested share; then (if its y is non-NA) y^(d) = `rng.beta(a₂ + D, b₂ + K − D, size=10000)`. Coverage draws are c^(d) = 1 − s^(d).
- Alphabetical order is Python `sorted()` over the canonical names in `src/extract/crosswalk.py`, which are: Andaman and Nicobar Islands, Andhra Pradesh, Arunachal Pradesh, Assam, Bihar, Chandigarh, Chhattisgarh, Delhi, Goa, Gujarat, Haryana, Himachal Pradesh, Jammu and Kashmir, Jharkhand, Karnataka, Kerala, Madhya Pradesh, Maharashtra, Manipur, Meghalaya, Mizoram, Nagaland, Odisha, Puducherry, Punjab, Rajasthan, Sikkim, Tamil Nadu, Telangana, Tripura, Uttar Pradesh, Uttarakhand, West Bengal. These 33 names are the canonical unit names of tb_priority_tool's crosswalk (`UNITS` in its `src/extract/crosswalk.py`), and the list above is already in `sorted()` order.
- `tbprio.harm.estimate` and `tbprio.harm.draws` are not used: their harm is the gap from a percentile benchmark of the same rate, which is neither E1 nor E2. Their conventions (one call per unit, alphabetical order, 10,000 draws, a fresh generator per set) are followed.
- Each quantity is summarised by `tbprio.harm.summary`, which gives the mean of the 10,000 draws and their 2.5th and 97.5th percentiles (`mean`, `lo`, `hi`).

### 5.4 Gap 1: the screening gap (E1)

**Fixed (verbatim).** **Gap 1 (screening):**
- u = notified − known status;
- coverage c = known/notified;
- expected undetected among the untested E1 = u·k·p_s.

**Operational detail.**
- Here u is U_ut. The observed value E1 = U·k·p_u is reported as `point`.
- In draw d: E1^(d) = N·s^(d)·k·p_u, from the draw set of §5.3. E1 is the number of TB patients with diabetes expected among those not screened, assuming that the untested have the expected yield k·p_u.
- Main k = k_b; sensitivities k = 1, 1.5, 2, and k at the median and p90 benchmarks.

### 5.5 Gap 2: the identification gap (E2)

**Fixed (verbatim).** **Gap 2 (detection):**
- y = diabetic/known-status-tested;
- R = y/p_s;
- undetected among the tested E2 = tested·max(0, k·p_s − y).

**Operational detail.**
- The observed value E2 = K·max(0, k·p_u − D/K) is reported as `point`.
- In draw d: E2^(d) = K·max(0, k·p_u − y^(d)). The floor is applied per draw, so E2 is never negative (Review Focus 4), and its mean can exceed 0 for a unit whose observed y is above k·p_u.
- Main k = k_b; the same sensitivities as E1.
- **Total shortfall** T^(d) = E1^(d) + E2^(d), for units with both non-NA. E1 and E2 count the same kind of patient, so their sum has a meaning (unlike the steps of the priority tool).

### 5.6 The detection ratio R, "likely under-detection" and "below the benchmark"

**Fixed (verbatim).** **Likely under-detection:** the 95% interval of R, from Beta(½ + x, ½ + n − x) draws of y with p_s fixed, lies wholly below 1.

**Resolution.** The fixed definition R = y/p_s is R at k = 1 (§1.4, rows 5 and 6). In general R_k = y/(k·p_u), and C2 is R at k = k_b. The fixed rule, at k = 1, defines the phrase "likely under-detection" (the Constraint's wording rule). The strengthened H3 uses k_b and a one-sided 95% posterior probability (§8.7); its units are described as "identification below the benchmark".

**Operational detail.**
- **Draws.** The Jeffreys draw set of the year (§5.3): y^(d) ~ Beta(½ + D, ½ + K − D); R_k^(d) = y^(d)/(k·p_u), with p_u and k fixed. The 95% interval of R_k is the 2.5th and 97.5th percentiles of its draws.
- **Likely under-detection** (unit u, year t): the 97.5th percentile of R_1^(d) is below 1. The same rule at k = 1.5 and 2 is reported as a sensitivity, never with the phrase.
- **Identification below the benchmark** (unit u, year t): P(R_{k_b} < 1), the share of draws with y^(d) < k_b·p_u, is at least 0.95. The Jeffreys draws are used, as in the fixed rule, so that the classification rests on the unit's own counts; k_b is the main benchmark (empirical Bayes, §5.2).
- These are computed for every unit and data year and written to `outputs/cascade.csv`.

### 5.7 Sensitivities of the cascade, gaps and priorities

Each is reported alongside the main analysis, without a label:
- k = 1, 1.5, 2; k at the median and p90 benchmarks; k_b from the 2019 + 2021 pool (§5.2);
- the simple reference prevalence (§4.4);
- shrinkage off (the Jeffreys draw set and the Jeffreys k_b, §5.2, §5.3), which replaces the fixed grid's "shrinkage of y" axis that the strengthened grid removed;
- the 2022 A1.6 denominator (§3.4);
- p_u × 0.8 and × 1.2 (§8.11).

---

## 6. Priorities, decomposition and the national scenario

### 6.1 Priorities and tiers

**Fixed (verbatim).** **Priorities:** tbprio shrinkage, draws and P(top-5), applied to E1 and E2 per year; tiers act now ≥0.80 / probable ≥0.50 / uncertain ≥0.20 / lower; a per-100,000-notified view alongside. The main priority year is 2022.

**Resolution.** The ruling's main priority year, 2023, governs (§3.2). Priorities are computed for every data year; headline tiers are for 2023.

**Operational detail.**
- For each data year and each gap g ∈ {E1, E2}, over the units with a non-NA value of g: P(top-5) = `tbprio.priority.p_topk({unit: g^(d)}, 5)`, with the units in alphabetical order. In each draw the five largest values score 1; a unit whose value is 0 in a draw scores 0; units above 0 tied at the fifth place share the places left equally (the tbprio rule).
- Tier = `tbprio.priority.tier(P(top-5), False)`: "act now" P ≥ 0.80; "probable priority" 0.50 ≤ P < 0.80; "uncertain" 0.20 ≤ P < 0.50; "lower priority" P < 0.20. The rising argument is always False: this study has no "watch: rising" tier. The falling-coverage flag (§7) is reported alongside and never changes a tier.
- Main specification: 2023, k = k_b (p75, pooled 2021 + 2022, sex-weighted reference), the empirical-Bayes draw set. Headline tiers are per gap.
- The total shortfall T (§5.5) is given a P(top-5) and a tier in the same way, as a secondary view reported alongside the per-gap tiers.
- The sensitivities of §5.7 are reported in `outputs/priority.csv` with a `spec` column.

### 6.2 Per-100,000-notified view

`per_100k_notified` = the mean of the draws of g ÷ N × 100,000, with N the unit-year's C1 denominator (§3.3). It is shown alongside and is never used for tiers.

### 6.3 Decomposition: screening-led or identification-led

**Strengthened (verbatim).**
5. **Decomposition of the shortfall.** For each unit, the total undetected diabetic TB patients relative to the benchmark (E1 + E2) is split into a screening part (E1) and a detection part (E2), each with intervals. A unit is classed "screening-led" or "detection-led" when its share exceeds 0.5 with 95% posterior probability, otherwise "mixed". This tells each State which step to fix.

**Operational detail.**
- Main: 2023, k = k_b, the empirical-Bayes draw set (the same draws as the priorities). Units with both C1 and y non-NA.
- Share S^(d) = E1^(d) ÷ (E1^(d) + E2^(d)). A draw with E1^(d) + E2^(d) = 0 counts towards neither class.
- "Screening-led": P(S > 0.5) ≥ 0.95. "Detection-led" (written "identification-led" in text, §1.3): P(S < 0.5) ≥ 0.95. Otherwise "mixed". If every draw has E1 + E2 = 0, the unit is "no shortfall".
- P(S > 0.5) and P(S < 0.5) are computed over all 10,000 draws. Draws with S = 0.5 or E1 + E2 = 0 count in neither.
- The class is reported with T per 100,000 notified. Units below the median of T per 100,000 are described as 'small total shortfall' before their class.
  - Operational detail: T per 100,000 notified = the mean of T^(d) ÷ N × 100,000 (§6.2); the median is taken over the units classified in that year and specification.
- E1, E2 and S are reported as the mean and 95% interval. Sensitivities: k = 1, 1.5, 2, and the other data years. Output: `outputs/decomposition.csv`.

### 6.4 National scenario

**Strengthened (verbatim).**
6. **Policy scenario.** The national number of additional diabetic TB patients identified per year if every unit reached the benchmark coverage and k_b, with a 95% interval, and the share contributed by the top 5 units. Labelled an illustration, not a forecast.

**Operational detail.**
- **Benchmark coverage** c_b (2023) = the 75th percentile, across the units with non-NA C1 in 2023, using 2023's (a₁, b₁), of the empirical-Bayes posterior-mean coverage 1 − (a₁ + U)/(a₁ + b₁ + N) (the same benchmark logic as k_b). Under the median and p90 sensitivities, c_b and k_b both move to that percentile.
- For each unit with both C1 and y non-NA in 2023, in draw d: A_u^(d) = N·[max(c^(d), c_b)·max(y^(d), k_b·p_u) − c^(d)·y^(d)], which is never negative. Units already at or above both benchmarks add nothing; newly screened patients are assumed to have the yield max(y^(d), k_b·p_u).
- National A^(d) = Σ_u A_u^(d), reported as the mean and 95% interval (`tbprio.harm.summary`). The interval reflects binomial uncertainty in coverage and yield only; it excludes uncertainty in p_u and k_b, and this is stated with the scenario.
- **Top-5 share.** The five units with the largest mean A_u (`tbprio.validate.top5`, ties broken alphabetically). Share = Σ over those five of mean A_u ÷ Σ over all units of mean A_u; its 95% interval is that of the per-draw ratio with the five units fixed.
- Units excluded for NA are listed. The scenario is labelled "an illustration, not a forecast" wherever it appears. Sensitivities: k = 1, 1.5, 2 (with c_b unchanged) and the median and p90 benchmarks. Output: `outputs/scenario.csv`.

---

## 7. Trend in screening coverage

### 7.1 Fixed values and rulings

**Fixed (verbatim).** **Trend:** screening coverage c over 2018, 2021 and 2022, using tbprio's empirical-logit WLS slope with pooled φ, with no COVID indicator (stated). A "falling coverage" flag is set when the slope CI lies wholly below 0. Minimum: 3 years.

**Ruling (verbatim).** **Main years.** … The trend uses 2018, 2019, 2021, 2022 and 2023, with tbprio's empirical-logit WLS, φ, and the 2021 indicator, exactly as in the priority tool. (The full ruling is in §3.2.)

**Resolution.** The ruling governs: five years and the 2021 indicator. The fixed "no COVID indicator", and the design's reason for it (2018 the only pre-COVID point), no longer apply, because 2018 and 2019 both precede 2021. The falling-coverage flag and the 3-year minimum are kept.

### 7.2 Main model

**Operational detail.**
- For each unit, over the data years with non-NA C1, on observed (not shrunken) counts: `tbprio.trend.fit(years, K, N)` with its default arguments. This fits the empirical logit L_t = log((K_t + ½)/(N_t − K_t + ½)), with variance V_t = 1/(K_t + ½) + 1/(N_t − K_t + ½) and weights 1/V_t, in the model L_t = β₀ + β₁(t − 2023) + γ·[t = 2021]. The 2021 indicator is fitted where the unit has 2021 and an earlier year (`tbprio.trend.default_indicator`).
- A unit needs at least 3 non-NA years, and at least 3 non-NA years other than 2021 where the indicator is fitted; otherwise "trend not estimable (fewer than 3 years)" (`tbprio.trend.NotEstimable`).
- φ = `tbprio.trend.pooled_phi` over the main fits of all units: max(1, Σ Pearson χ² ÷ Σ residual df), with units of 0 residual df contributing nothing.
- (SE, lo, hi) of the slope = `tbprio.trend.interval(fit, φ)`: β₁ ± 1.96·√(φ·[(XᵀWX)⁻¹]₁₁).
- **Falling coverage**: hi < 0. A positive slope is rising coverage. The flag is reported with the tiers and never changes them.
- The 2018 denominator is on the current-PHI basis (the flag is carried, §3.4).

### 7.3 Sensitivities

- **Without the 2021 indicator**: `tbprio.trend.fit(years, K, N, indicator=False)` over the same years, with the main φ (as in the priority tool's §7.3).
- **Dropping 2018** (the ruling's sensitivity): the main model over 2019, 2021, 2022 and 2023, with φ pooled over these fits. This model is presented as the practice-relevant view of recent change: screening was being scaled up between 2018 and 2019 (§11), so with 2018 included a "falling coverage" flag is nearly impossible, and the denominator bases also change between years (§3.4), so every slope partly reflects them.
- **The 2022 A1.6 denominator** (§3.4): the main model with that 2022 N, with φ pooled over these fits.
- For each, the number of units whose falling-coverage flag differs from the main model is reported. Output: `outputs/trend.csv`.

---

## 8. Headline estimates, regression, funnel, grid and labels

### 8.1 Fixed values, strengthened analyses and the registered headline set

**Fixed (verbatim).** **Headline estimates**

| | Estimate | Null | Interval | Label |
|---|---|---|---|---|
| H1 | Spearman ρ between p_s and pooled y (2021 + 2022 counts summed per unit) | 0 | Fieller, √(1.06/(n−3)) | yes |
| H2 | National coverage 2018 vs 2022 | — | Wilson intervals | none (descriptive) |
| H3 | Number of units likely under-detecting at k = 1, 2022 | — | — | none (descriptive) |

**Strengthened (verbatim).**
3. **Hierarchical regression of detection on prevalence (H1 replaced).** A quasi-binomial (overdispersed) logistic regression of TB–DM diagnosed / tested on logit(p_s), with a year effect (2021, 2022), weighted by tested, using numpy/scipy IRLS with a Pearson φ.
   - H1 is the slope β on logit(p_s). If detection follows true burden, β > 0. Null 0. Interval: a cluster bootstrap over units, 10,000 draws.
   - The Spearman ρ with Fieller interval is kept as a registered sensitivity.

**Strengthened (verbatim).**
8. **H2 and H3** are unchanged: national coverage 2018 vs 2022; the count of units with C2 below benchmark at 95% posterior probability.

**Resolution: the registered headline set.**

| | Estimate | Null | Interval | Label |
|---|---|---|---|---|
| H1 | Slope β₁ on logit(p_u) of the quasi-binomial regression of D/K, data years 2019 + 2021 (§8.2) | 0 | Cluster bootstrap over units, 10,000 draws (§8.3) | yes (§8.9) |
| H2 | National screening coverage, 2018 vs 2022 (§8.6) | — | Wilson intervals for each year; Newcombe interval for the difference | none (descriptive) |
| H3 | Number of units with identification below the benchmark (C2 < 1 with posterior probability ≥ 0.95), data year 2023 (§8.7) | — | — | none (descriptive) |

The fixed H1 (Spearman ρ with the Fieller interval) is the registered sensitivity of §8.4, on the ruling's years. The fixed H3 (units likely under-detecting at k = 1) is reported alongside H3 (§8.7).

### 8.2 H1: the regression of identification on diabetes burden

**Operational detail.**
- **Observations.** Unit-years (u, t) for t in the year set (main: 2019 and 2021, per the ruling) with non-NA y. A unit may contribute one or both years.
- **Model.** D_ut ~ quasi-binomial(K_ut, π_ut), logit(π_ut) = β₀ + β₁·logit(p_u) + Σ_j γ_j·[t = j]. Year indicators: for {2019, 2021}, [t = 2021] (reference 2019); for {2021, 2022, 2023}, [t = 2022] and [t = 2023] (reference 2021); for {2023}, none.
- **Prior weights.** a_ut = K_ut ("tested", main) or a_ut = 1 ("unweighted", a grid axis). The response is the proportion y_ut = D_ut/K_ut.
- **IRLS** (numpy only). Start with μ = (a·y + ½)/(a + 1) and η = logit(μ). Repeat: working weights W = a·μ(1 − μ); working response z = η + (y − μ)/(μ(1 − μ)); β = (XᵀWX)⁻¹XᵀWz; η = Xβ; μ = expit(η). Stop when max |Δβ| < 10⁻¹⁰, after at most 100 iterations. Non-convergence, or a singular XᵀWX, is reported and the estimate is then undefined.
- **Pearson φ** = Σ a(y − μ)²/(μ(1 − μ)) ÷ (n_obs − n_par). It is reported with the fit, together with the model-based Wald interval β₁ ± 1.96·√(φ·[(XᵀWX)⁻¹]₁₁) as a descriptive comparison. The Wald interval is not used for the label.
- **H1** = β₁ under the main specification: reference sex-weighted, year set {2019, 2021}, weights tested. "If detection follows true burden, β > 0." Null 0.
- The model is ecological: β₁ describes units, not patients.
- β₁ > 0 is partly expected whatever the programme does, because both sources count treated diabetes: the TB–DM count includes known diabetes (§1.3), and NFHS-5 lines 101 and 104 include adults taking medicine. This is stated with H1.

### 8.3 H1 interval: the cluster bootstrap

- A fresh `numpy.random.default_rng(20261122)`. The H1 units (those with at least one observation) are sorted alphabetically; with U_H1 of them, the indices are drawn in one call: `rng.integers(0, U_H1, size=(10000, U_H1))`.
- In each draw, each drawn unit brings all its unit-years (a unit drawn twice enters twice), and the model is refitted by the IRLS of §8.2.
- A draw whose fit is undefined (non-convergence or a singular XᵀWX, for example when every drawn unit has the same p_u) is discarded, and the number discarded is reported.
- The 95% interval is the 2.5th and 97.5th percentiles of β₁ over the retained draws. It is computed for the main specification only.
- Reported with the interval: the Kish effective number of clusters, (Σ_u w_u)² ÷ Σ_u w_u², where w_u = Σ_t a_ut is the unit's total prior weight; and whether 1 lies inside the interval (β₁ = 1: the odds of identification change in proportion to the odds of p_u).
- With about 33 units, the percentile cluster bootstrap may give too-narrow intervals. This is stated with H1 (§10.5).

### 8.4 H1 sensitivity: Spearman ρ with the Fieller interval

- Units with non-NA y in both 2019 and 2021. Pooled y_u = (D_u,2019 + D_u,2021) ÷ (K_u,2019 + K_u,2021).
- ρ = `tbprio.validate.spearman(p, y_pooled)` (the Pearson correlation of average ranks); interval = `tbprio.validate.fisher_ci(ρ, n)`: tanh(atanh ρ ± 1.96·√(1.06/(n − 3))), none if n ≤ 3.
- Also reported with the simple reference, and for the pooled 2021 + 2022 counts of the fixed H1. No label.

### 8.5 The overdispersed funnel

**Strengthened (verbatim).**
4. **Overdispersed funnel.** Each unit's observed TB–DM diagnoses against those expected from the regression; multiplicative φ from 10%-winsorised z; 95% and 99.8% limits. Units below the 99.8% limit are flagged "detection well below what its diabetes burden predicts".

**Operational detail.**
- **Main funnel: data year 2023**, the main priority year, with expected values from the "2023 alone" regression (reference sex-weighted, weights tested; one of the grid entries, §8.8). Secondary funnels: 2019 and 2021, each from the main H1 fit.
- For each unit: expected E_u = K_u·μ̂_u, with μ̂_u = expit(β̂₀ + β̂₁·logit(p_u) + the year term); z_u = (D_u − K_u·μ̂_u) ÷ √(K_u·μ̂_u·(1 − μ̂_u)).
- φ_f = `tbprio.district.winsorised_phi(z)` over the units of the funnel year: each z is set to the 10th or 90th percentile where it lies outside them, and φ_f is the mean of the squared values. The limits are multiplied by `tbprio.district.widen(φ_f)`, which is √φ_f when φ_f > 1 and 1 otherwise.
- Limits: ±1.96 (95%) and ±3.09 (99.8%), times the widening factor.
- Flag: z_u below the lower 99.8% limit → "detection well below what its diabetes burden predicts" (written in text as "identification well below what the across-unit relationship with p_u predicts", §1.3). Above the upper 99.8% limit → "identification well above what the across-unit relationship with p_u predicts" (descriptive). Positions between the 95% and 99.8% limits are reported.
- Output: `outputs/funnel.csv`. The funnel has no label.

### 8.6 H2: national screening coverage

**Resolution.** H2 stays 2018 vs 2022: the strengthened text says it is unchanged, and the rulings are silent on it.

**Operational detail.**
- National coverage in year t: c_t = ΣK ÷ ΣN over the units with non-NA C1 in that year (the number of units is reported). The State rows are used; the printed India row is used only for the total check (§3.5).
- Wilson 95% interval for each year: centre (K + z²/2)/(N + z²), half-width z·√(K(N − K)/N + z²/4)/(N + z²), with z = 1.96.
- H2 = d = c_2022 − c_2018, with Newcombe's hybrid-score interval from the two Wilson intervals (l, u): lower = d − √((c₂ − l₂)² + (u₁ − c₁)²), upper = d + √((u₂ − c₂)² + (c₁ − l₁)²), where 1 is 2018 and 2 is 2022.
- Reported alongside: c_t for 2019, 2021 and 2023; 2019 vs 2022 (without the 2018 denominator flag); 2018 vs 2023; and 2022 on the A1.6 denominator. At these counts the sampling intervals are very narrow; the change of denominator basis between years (§3.4) matters more and is stated with H2.
- No null and no label.

### 8.7 H3: units with identification below the benchmark

**Operational detail.**
- **H3** = the number of units, in data year 2023, with P(R_{k_b} < 1) ≥ 0.95 (§5.6), over the units with non-NA y. The number of units assessed is reported. Descriptive; no null, interval or label.
- **Reported alongside H3** (descriptive): the number of units "likely under-detecting" (§5.6, R at k = 1, the fixed H3 definition) in 2023 and in 2022 (the fixed year); both counts for every data year; and the counts under k = 1.5, 2, the median and p90 benchmarks, the simple reference, and p_u × 0.8 and × 1.2.
- By construction, about 75% of the pool units have g_u < k_b. H3 is reported next to this count (the pool units with g_u < k_b, in 2021 + 2022) and is never described as widespread under-identification. 2023 is outside the pool years; 2022 is inside them and is labelled in-sample.

### 8.8 Specification grid

**Fixed (verbatim).** **H1 grid** (12 entries): p_s weighting {sex-weighted, simple} × year {2021, 2022, pooled} × shrinkage of y {on, off}.

**Strengthened (verbatim).** **H1 grid** (12 entries): reference {sex-weighted, simple} × year set {2021, 2022, pooled} × weights {tested, unweighted}.

**Ruling (verbatim).** The H1 grid's year-set axis becomes {2019 + 2021 (main), 2021–2023, 2023 alone}.

**Resolution and operational detail.**
- The H1 grid is reference {sex-weighted, simple} × year set {2019 + 2021 (main), 2021–2023, 2023 alone} × weights {tested, unweighted} = 12 entries, including the main entry.
- Each entry is the β₁ point estimate of §8.2 under that specification. The bootstrap interval is computed for the main entry only.
- An entry whose fit is undefined has no sign (§8.9).
- Every entry is written to `outputs/spec_curve.csv`.

### 8.9 Label rule

**Constraint (verbatim).** Label rule: "supported" only if the 95% interval excludes the null AND ≥80% of grid entries agree in sign.

**Operational detail.**
- The label applies to H1 only. H2, H3, the funnel, the scenario, the decomposition, leave-one-out and all sensitivities carry no label.
- Label = `tbprio.validate.label((lo, hi), 0, signs, main_sign)`, with signs = [`tbprio.validate.sign(β₁_e)` for each of the 12 entries e] and main_sign = `tbprio.validate.sign(β₁_main)`.
- "Excludes the null": both ends of the bootstrap interval are strictly above 0, or both strictly below 0.
- "Agree in sign": an entry's β₁ has the same strict sign as the main estimate. An entry with β₁ = 0, or undefined, does not agree. The main entry counts as one of the 12. "Supported" needs at least 10 of 12 (10/12 ≥ 0.80; 9/12 = 0.75 is not enough). Otherwise the label is "not established".
- The count of agreeing entries (`tbprio.validate.n_agree`) is reported. A "supported" negative β₁ is reported as such; the rule assumes no direction.

### 8.10 Leave-one-out (descriptive, no label)

**Fixed (verbatim).** **Leave-one-out:** each unit, for H1 and for the 2022 act-now sets.

**Resolution.** The act-now sets are those of the main priority year, 2023 (ruling); the 2022 sets are reported alongside.

**Operational detail.**
- **H1.** The main β₁ point estimate is refitted with each unit (all its unit-years) left out in turn. The minimum and maximum, with the unit whose omission gives each, are reported. The Spearman sensitivity (§8.4) is treated the same way.
- **Act-now sets.** For each gap (E1, E2) in 2023 (and 2022), each unit is removed in turn and the whole chain is recomputed over the remaining units: the year's priors, k_b (from the 2021 + 2022 pool without that unit), a fresh draw set (seed 20261122), P(top-5) and tiers. The number of remaining units whose act-now membership changes is reported, with the omitted unit that causes the most changes.
- Output: `outputs/leave_one_out.csv`.

### 8.11 NFHS uncertainty

**Fixed (verbatim).** **NFHS uncertainty:** sensitivity with p_s × {0.8, 1.2}. The NFHS fact sheets give no CI, so this is stated as a limitation.

**Operational detail.**
- Every p_u is multiplied by 0.8, and separately by 1.2.
- Under k_b, a common scaling of p_u cancels: k_b scales by the reciprocal factor, so k_b·p_u, and with it E1, E2, C2, H3, the decomposition and the scenario, are unchanged. This is stated, and these quantities are not rerun.
- The scaling is applied to every quantity at a fixed k (1, 1.5, 2): R and the "likely under-detection" counts, E1 and E2, and their 2023 tiers. It is also applied to the H1 main point estimate. The Spearman sensitivity is unchanged by a common scaling and is not rerun.
- A common scaling cannot represent State-specific error in NFHS-5; this is a limitation (§10.5).
- **State-specific perturbation.** 1,000 replicates (a new rng(20261122), units in the §5.3 order). Each unit's p_u is multiplied by an independent exp(N(0, 0.10²)). k_b, E1, E2, H3, the 2023 tiers and the decomposition classes are recomputed on the existing draw sets, which do not depend on p_u. For each unit, report the share of replicates in which its tier, H3 membership and class are unchanged.
  - Operational detail: the normal values are drawn in one call, `rng.normal(0.0, 0.10, size=(1000, U))`, with U the number of units and column j the j-th unit in the §5.3 order; a unit's multiplier is the exponential of its value. The results go to `outputs/perturbation.csv`.

---

## 9. Analyses dropped before registration, and exploratory status

### 9.1 The NCD-reach check: dropped

**Strengthened (verbatim).**
7. **Equity and health-system context (exploratory, labelled).** Spearman ρ between C1 coverage and the NFHS-5 State share of adults with high blood sugar who are on medicine, a proxy for NCD treatment reach. This is computed only if the fact sheets print the needed components; otherwise it is dropped before registration.

**Resolution: dropped.** The State fact sheets print, for women and men separately, lines 99/102 "Blood sugar level - high (141-160 mg/dl)", lines 100/103 "Blood sugar level - very high (>160 mg/dl)" and lines 101/104 "… high or very high (>140 mg/dl) or taking medicine to control blood sugar level" (inventory). "Taking medicine" is not printed on its own line. Line 101 minus lines 99 and 100 counts only those on medicine whose random blood sugar was 140 mg/dl or less; people on medicine whose blood sugar was still high are counted in lines 99 and 100 and cannot be separated from those not on medicine. The share of adults with high blood sugar who are on medicine therefore cannot be derived, and the check is dropped. Nothing replaces it.

### 9.2 Other analyses not done

- No testing-method analysis: no TB report table prints the diabetes test used (HbA1c, random or fasting glucose; inventory).
- No district, individual-level or causal analysis (§1.2).
- No age-specific modelling of the expected prevalence (design §8, approach C).

### 9.3 Exploratory analyses

Any analysis not in this plan is labelled exploratory wherever it appears, and is listed in §12 with its date and reason.

---

## 10. Computation, outputs, verification and limitations

### 10.1 Computation

**Constraint (verbatim).**
- `python -I`, LF line endings.
- Seed 20261122; numpy `default_rng`, reset per analysis; 10,000 draws.
- Reuse tbprio functions; never copy-modify them.

**Operational detail.**
- Python 3.14 with numpy 2.3.5 and scipy 1.16.3; tbprio 1.0.1 (below).
- "Reset per analysis" means a new `numpy.random.default_rng(20261122)` at the start of each of:
  - each draw set (§5.3), that is, each data year × prior mode (× denominator basis, for 2022);
  - the H1 cluster bootstrap (§8.3);
  - each leave-one-out refit of the act-now sets (§8.10);
  - each C3 draw set (§5.1);
  - the State-specific perturbation (§8.11).
- The seed constant of tbprio (`tbprio.harm.SEED`, 20261121) is not used.
- 10,000 draws in every draw set, and 10,000 bootstrap draws.
- Reruns with the same inputs must give byte-identical outputs. This is checked.

**Ruling (verbatim).** **tbprio.** The installed tbprio was refreshed to 1.0.1 from the local tb_priority_tool checkout; its src/tbprio is byte-identical to tag v1.0.1, and no download was involved. Task 4's pin test asserts the version is 1.0.1, and that src/tbprio file hashes match those recorded from tag v1.0.1.

At the start of every analysis run, the installed tbprio must report version 1.0.1 (`importlib.metadata.version("tbprio")`, or `tbprio.__version__` where it is defined), or the run stops (Review Focus 5).

### 10.2 tbprio functions used

| Function (tbprio 1.0.1) | Used for | Section |
|---|---|---|
| `tbprio.shrink.beta_binomial` | empirical-Bayes priors of the untested share, the yield and the pooled yield for k_b | §5.2, §5.3 |
| `tbprio.shrink.JEFFREYS_BINOMIAL` | the shrinkage-off (Jeffreys) prior | §5.2, §5.3 |
| `tbprio.harm.summary` | mean and 95% interval of draws | §5.3, §6.4 |
| `tbprio.priority.p_topk` | P(top-5) | §6.1 |
| `tbprio.priority.tier` | tiers (rising always False) | §6.1 |
| `tbprio.trend.fit`, `default_indicator`, `pooled_phi`, `interval`, `NotEstimable` | the coverage trend | §7 |
| `tbprio.validate.spearman`, `fisher_ci` | the H1 Spearman sensitivity | §8.4 |
| `tbprio.validate.top5` | the scenario's top-5 units | §6.4 |
| `tbprio.validate.label`, `sign`, `n_agree` | the H1 label | §8.9 |
| `tbprio.district.winsorised_phi`, `widen` | the funnel's multiplicative φ | §8.5 |

Functions are imported and called, never copied or modified. The IRLS fit, the draw sets, E1, E2, k_b, c_b, the decomposition and the scenario are new code in `src/dmgap/`.

### 10.3 Outputs

Extracted data (Task 3):
- `data/extracted/dm_panel.csv`: `unit, year, measure, value, source_file, pdf_page, table_id, flag`.
- `data/extracted/nfhs_dm.csv`: `unit, sex, prevalence_pct, population, source_file, pdf_page, flag`.
- `data/extracted/tb_sex_2022.csv`: the ITR 2023 A1.6 notified counts by sex, per printed row, with provenance.

Analysis outputs (Task 4), each with a `spec` column where it carries sensitivities:
- `outputs/reference_prevalence.csv`: unit, members, w, m, f, p (sex-weighted), p (simple), population weights, flags.
- `outputs/benchmark.csv`: k_b for every specification (percentile, pool, reference, prior) with its number of units; c_b for 2023; the linkage benchmark c3_b for each year with the main C3 definition.
- `outputs/cascade.csv`: per unit and year: N, K, D, I; C1, y and C3 with Jeffreys intervals; R at k_b, 1, 1.5 and 2 with draw intervals; P(R_{k_b} < 1); the "likely under-detection" and "below the benchmark" flags; P(C3 < c3_b) and the "linkage below the benchmark" flag; the cumulative cascade; flags.
- `outputs/gaps.csv`: per unit, year, gap (E1, E2, E3) and specification: `point, mean, lo, hi, per_100k_notified`.
- `outputs/priority.csv`: per unit, year, gap (E1, E2, total, E3) and specification: `mean, lo, hi, per_100k_notified, p_top5, tier, falling_coverage`.
- `outputs/decomposition.csv`: E1, E2 and the share S, with intervals, P(S > 0.5), P(S < 0.5) and the class.
- `outputs/scenario.csv`: the national A and its interval; per-unit A; the top-5 units and their share, with its interval.
- `outputs/trend.csv`: per unit and model: years, n_years, indicator, slope, SE, lo, hi, φ, falling_coverage, status.
- `outputs/funnel.csv`: per unit and funnel year: observed, expected, z, φ_f, the limits, position and flag.
- `outputs/headline.csv`: `estimate, value, lo, hi, null, n, n_grid, n_agree, label`, for H1, H2 and H3 (H2 and H3 without a label).
- `outputs/headline_sensitivity.csv`: the Spearman sensitivity, the fixed-definition H3 counts, the H2 companions and the NFHS-scaling results.
- `outputs/spec_curve.csv`: the 12 H1 grid entries.
- `outputs/perturbation.csv`: per unit, the shares of the 1,000 State-specific perturbation replicates in which its tier, H3 membership and decomposition class are unchanged (§8.11).
- `outputs/leave_one_out.csv`.
- `outputs/na_cells.csv`: every NA or flagged cell, with the reason.

### 10.4 Verification

- `verification/check_plan_order.py` checks the registration order: no file under `src/dmgap/`, `data/extracted/` or `outputs/` before the registration commit, over the full history with merges included; the registration record naming a full 40-character SHA and never re-pointed; and the text above §12 unchanged at every later commit on the ancestry path and in the working tree. Before `docs/registration_event.json` exists it fails with "NOT REGISTERED YET".
- An independent standard-library recompute covers: p_u for three units; E1 and E2 for three units; the R intervals and the H3 count; β₁ by its own IRLS; the Spearman sensitivity and its Fieller interval; and the label, from `outputs/spec_curve.csv`.
- Further checks: the extracted tables against their printed totals; the implied-denominator check (§3.4); a byte-for-byte rerun of `outputs/`; and mutation tests showing that each check fails when its target is altered.
- Every deviation from this plan is dated and explained in §12.

### 10.5 Known limitations stated in advance

- **NFHS-5 gives no confidence interval.** p_u is a point estimate with no sampling interval. The × 0.8 and × 1.2 sensitivity is a common scaling: it cancels under k_b, and it cannot represent State-specific error, which is the error that could move units between tiers or across the funnel limits. Small States and UTs have the smallest NFHS samples.
- **NFHS measures random blood sugar.** Footnote 23 of the fact sheets reads "Random blood sugar measurement." A single random reading above 140 mg/dl, or taking medicine, is not a diagnosis of diabetes. p_u is a reference level of raised or treated blood sugar in adults aged 15 and over, not diabetes prevalence. The TB programme's test is not printed in any table and may differ by State and year.
- **The TB–DM count includes known diabetes.** The ITR count includes "already existing" diabetes (ITR 2019 narrative), so C2 is diabetes identified, newly diagnosed or known. The analysis cannot say how much diabetes the TB programme newly found.
- **The expected yield is an assumption.** TB patients differ from the adult population in age and sex, and diabetes raises TB risk, so diabetes among TB patients is expected to exceed p_u. p_u's random-glucose threshold (>140 mg/dl) is below diagnostic thresholds, so p_u may overstate diabetes. k = 1 is a reference point, not a guaranteed lower bound, and 'likely under-detection' at k = 1 may reflect this threshold difference. k_b is relative to the better quarter of units (a quarter lie above it by construction); k = 1.5 and 2 rest on published ratios. NFHS covers ages 15 and over, while TB notifications include children. f_u is from 2022 for every year.
- **Denominator bases differ by year.** 2018 uses current-PHI notified from its own table; 2019 its own table's notified; 2021–2023 the A1.2 diagnosing-PHI notified from another annexure; and the 2022 percentages may be on the A1.6 basis. Coverage and its trend may partly reflect these bases.
- **C3 definitions change.** "Linked to NCD Clinic" in 2018; "initiated on anti-diabetic treatment" from 2019. 2018 C3 is not compared with later years.
- **H1.** β₁ > 0 is partly expected because both sources count treated diabetes. With about 33 units, the percentile cluster bootstrap may give too-narrow intervals.
- **State level only.** The analysis is ecological. A unit-level association (H1) says nothing about individual patients. Small UTs are merged into larger units. No district figures are published.
- **Timing.** NFHS-5 fieldwork was 2019–21, and the main priority year is 2023. H1 uses 2019 and 2021 for this reason, but the 2023 gaps apply a 2019–21 reference.
- **P(top-5) near 0 or 1.** With thousands to tens of thousands of tested patients per unit, binomial noise is small, so P(top-5) will mostly be close to 0 or 1. The tiers then express little uncertainty beyond sampling; the larger uncertainty from p_u, k and recording is shown only through the sensitivities.
- **Recording.** Low identification may reflect a truly lower prevalence among a State's TB patients, the testing method or recording, not only missed diabetes. Reporting artefacts (known above notified, diabetic above tested) are set to NA.
- **H2 is largely known.** The national coverage percentages are printed in the India rows of the source tables and were seen (§11); H2 is a descriptive restatement with intervals.

---

## 11. What had been seen before registration

**Constraint (verbatim).** No estimate (ratio, prevalence combination, gap, priority, trend, correlation) before the registration commit is pushed. Inventory of structure is allowed.

This section lists everything seen before this plan was registered. **No estimate of any kind had been computed** in this repository or for this study: no p_u, f_u, coverage, yield, ratio R, k_b, c_b, E1, E2, share, P(top-5), tier, trend, regression coefficient, correlation, funnel position, scenario or national rate, for any unit or year. No State value had been extracted in this repository.

1. **The source tables, by structure (Task 1 inventory, 21 November 2026).** Every table listed in `docs/data_inventory.md` was opened, in ITR 2019, ITR 2020 (the sibling copy), ITR 2021 (as page images), TBAR 2022, ITR 2023 and ITR 2024. Annexure numbers, pages, verbatim headers, the units covered and the printed India total rows were recorded.
   - The printed India rows were transcribed, including the national percentages printed in them. These show national screening coverage, national TB–DM yield and national treatment initiation for each year, as printed (for example, known blood-sugar status 29% in 2018 and known DM status 91.5% in 2022). H2 is therefore known in outline before registration, which is one reason it is descriptive. Nothing was calculated from these rows.
   - State rows were located by a text match on unit names and counted. Their values were on the pages read and may have been visible. None was recorded or used.
   - The ITR 2020 A2.5 and A2.6 discrepancy was found by comparing their printed headers and India rows, not State values.
   - The strengthened analysis set (commit 57e9a0b) was fixed before the Task 1 inventory (commit cde8e60). The controller's rulings after Task 1 (commit 6c0d004) followed the inventory.
   - The controller's rulings after Task 1 (five data years, main years, the meaning of C2, denominators, C3 definitions, NFHS inputs, the tbprio pin and the extraction method) were made from this structural record, not from State values.
2. **The TB–DM percentages printed in the ITR tables.** Every diabetes table prints, per State, the coverage and yield percentages (and the treatment-initiation percentage) next to the counts. C1, y and C3 are therefore published State figures, which readers of the reports, including the author, may have seen. This study adds the reference to diabetes burden (R, k_b), the counts of unidentified patients (E1, E2), their uncertainty, the tiers, the trends, H1 and the funnel.
3. **NFHS-5 State diabetes prevalences.** These are widely published and had probably been seen by the author. The author's own IJTB 2026 paper (doi 10.1016/j.ijtb.2026.01.010) used NFHS-5 risk indicators. In Task 1, the indicator lines of every State/UT fact sheet were located and their labels quoted; the values were on the pages read and may have been visible, but none was recorded. The national NFHS-5 figures for high blood sugar are also widely published. Together with the printed national TB–DM yield, the direction of a national comparison could be anticipated in outline. No ratio was computed. A printed national yield near 8%, against widely published NFHS-5 raised-glucose levels, made k_b < 1 and widespread R_1 < 1 foreseeable.
4. **The companion repositories.** The author's priority tool (hssling/india-tb-priority-tool), State TB Score study and ACF campaign study extracted no diabetes values (a text search of their extracted data and code found none). The priority tool's finding about the percentage base of ITR 2023 Annexure 2.1 (its plan §12.2) was seen and is the reason for the 2022 A1.6 sensitivity (§3.4). The priority tool extracted, and the author has seen, the State notified counts of ITR 2019 A1.2, TBAR 2022 A1.2, ITR 2023 A1.2 and ITR 2024 A1.2, and the ITR 2023 A1.6 notified counts by sex. These are the N inputs of C1 and E1 and the inputs of f_u. They were not combined with any diabetes value. Its methods (shrinkage, benchmark, P(top-k), tiers, trend, label rule, funnel φ) are reused through the pinned package.
5. **Literature.** A novelty check on 21 November 2026 searched for State-level TB–diabetes cascades for India and found none. The k = 1.5 and 2 sensitivities come from published ratios of diabetes prevalence among TB patients to that in the general population, to be verified on Crossref at the manuscript stage.
6. **Nothing else.** No output of this repository existed before the registration commit, and no file under `src/dmgap/` or `data/extracted/` had been written.

---

## 12. Deviations (dated)

**12.1 (21 November 2026): a deviation decided before any estimate was computed. The C1 (screening coverage) denominator for data years 2021–2023 now uses the basis of the diabetes tables' own percentages.**

**What was registered.** §3–§5 registered Annexure 1.2 (notified, diagnosing-PHI basis) as the N of C1 and E1 for 2021–2023.

**What the extraction review found.** The implied-denominator check (§3.4) showed that each year's TB–diabetes table prints known-status percentages whose denominators match a different printed count. The number of the 37 printed rows matching within the rounding interval:

| Year | A1.2 total (registered) | Best printed count |
|---|---|---|
| 2021 (TBAR 2022) | 2 | A1.4 "Net TB Patients Notified", current PHI: **37** |
| 2022 (ITR 2023; this edition has no A1.4) | 2 | A1.6 male + female + transgender sum: **28** (all 9 misses within 10 patients, 8 within 4) |
| 2023 (ITR 2024) | 2 | A1.4 net notified, current PHI, Total: **37** |

Mixing the two bases makes known status exceed N for Himachal Pradesh and Tripura in 2021–2023 (6 NA cells), and it distorts C1 elsewhere.

**Deviation.**
- **Main N:**
  - 2021: TBAR 2022 A1.4 net notified;
  - 2022: ITR 2023 A1.6 male + female + transgender;
  - 2023: ITR 2024 A1.4 net notified Total.
- **2018 and 2019 are unchanged.** Their registered bases already match the printed percentages: 35 of 37 in 2018 and 37 of 37 in 2019.
- **Sensitivities:** the registered A1.2 basis, with every C1- and E1-dependent result reported on both bases; and, for 2022, N back-calculated from the printed % (flagged `derived_from_percent`).

**Reason.** The numerator and denominator must share a basis, as in tb_priority_tool's §12.2.

**Timing.** Decided on 21 November 2026 from the Task 3 extraction review. At that point src/dmgap/ and outputs/ did not exist, and no ratio, gap, priority, trend or correlation had been computed. The matching itself compares printed counts with printed percentages; it is structural.

**12.2 (21 November 2026), a naming note with no change to any rule.** §3.4 names the 2022 A1.6 flag `denominator_a1_6_sensitivity`. After §12.1, the extracted data use these flags:
- `denominator_a1_6_sex_sum`: the main 2022 N;
- `plan_12.1_registered_basis`: the A1.2 sensitivity file;
- `plan_12.1_sensitivity`: the 2022 N derived from the printed percentage.

Analyses read these names.

**12.3 (21 November 2026), consequential notes on implementing §12.1, with no new analysis.**
1. §3.4, §5.3, §7.3 and §8.6 name a "2022 A1.6 sensitivity". After §12.1, A1.6 is the main 2022 N. These sensitivity slots are therefore filled by §12.1's own sensitivities: the A1.2 basis for 2021–2023 (with its own draw sets) and the 2022 N derived from the printed percentage. They run through every C1- and E1-dependent result, as §12.1 requires.
2. The seed is reset per §5.3 draw set. Priorities consume the shared draw sets.
3. The decomposition share S is summarised over draws with E1 + E2 > 0. In the data, every draw met this.
4. The cumulative C1·C2·C3 is not formed for 2018, whose C3 definition differs.
5. Outputs label the detection-led class "identification-led", following the §1.3 wording.

**12.4 (21 November 2026), the scope of §12.3 note 1 stated exactly, with no change to any estimate.**
- **On both bases.** The §12.1 sensitivities (the A1.2 basis for 2021–2023, and the 2022 N derived from the printed %) run through:
  - the cascade, the gaps and the priorities;
  - the decomposition and the scenario;
  - the trend and each basis's own falling-coverage flag;
  - H2, including the 2019 vs 2022 and 2018 vs 2023 companions;
  - the leave-one-out E1 act-now sets for 2022 and 2023.
- **Main basis only.** The k-grid, the NFHS ×0.8/×1.2 scaling and the State-specific p_u perturbation. This is stated in outputs/README.md.
