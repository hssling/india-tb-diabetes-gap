# Data inventory (structure only, no estimates)

Task 1, 21 Nov 2026. This file records what the sources print: annexure
numbers, pages, verbatim column headers, the units covered, the printed India
total rows, and whether counts or only percentages are printed. No rate, ratio,
sum, difference or prevalence combination has been computed. Every TB number
below is copied from a printed India total row. No NFHS-5 prevalence value is
written here; only the indicator labels are quoted.

## Conventions

- **Edition to data year:** ITR 2019 to 2018; ITR 2020 to 2019; ITR 2021 to 2020;
  TB Annual Report 2022 (`TBAnnaulReport2022.pdf`, cited as TBAR 2022) to 2021;
  ITR 2023 to 2022; ITR 2024 to 2023.
- **Pages:** "PDF p." is the 1-based page of the file in
  `data/source_manifest.csv`. "printed" is the page number printed on that page.
  TBAR 2022 is laid out as two-page spreads, so one PDF page carries two printed
  pages.
- **Headers:** verbatim. Cell line breaks are shown as spaces, column groups as
  `Group (sub, sub, sub)`, and `|` separates columns. Print errors are kept and
  marked [sic].
- **How the pages were read:** PyMuPDF 1.27.2.3 text blocks (one block per table
  row on these pages) for headers, unit names and total rows; pdfplumber 0.11.8,
  page by page with `page.flush_cache()`, rebuilding the rotated ITR 2019 pages
  from the characters (as in tb_priority_tool `src/extract/pdftext.py`) to
  cross-read them. ITR 2021 pages were rendered and read by eye.
- **"36 rows"** means one row per State/UT as printed, plus the India row.

## Summary: the TB-diabetes State tables

| Data year | Edition, table | PDF p. (printed) | Notified printed in the table? | Known DM status | Diabetic (TB-DM) | Linked to / initiated on DM treatment | Rows |
|---|---|---|---|---|---|---|---|
| 2018 | ITR 2019 A1.2 "TB Comorbidities" | 169–170 (147–148) | yes, total only | count (%) total only | count (%) total only | count (%) total only, "Linked to NCD Clinic" | 36 (DNH, D&D separate; no Ladakh) |
| 2019 | ITR 2020 A2.5 "TB-Diabetes" (not in the plan; see below) | 216–217 (192–193) | yes, public/private/total | counts; % on total only | counts; % on total only | counts; % on total only | 36 (DNH, D&D separate; no Ladakh) |
| 2020 | ITR 2021 A2.5 "TB-Diabetes" (scan; not used) | 236–238 (214–216) | no | count (%) | count (%) | count (%) | read by eye, not counted |
| 2021 | TBAR 2022 A2.5 "TB-Diabetes" | 96 (167–168) | no (A1.2, PDF p. 89) | count (%) | count (%) | count (%) | 36 (merged DNH and DD; Ladakh) |
| 2022 | ITR 2023 A2.10 "TB - DIABETES" | 239–240 (209–210) | no (A1.2, PDF pp. 213–214) | n (%) | n (%) | n (%) | 36 (merged DNH and DD; Ladakh) |
| 2023 | ITR 2024 A2.10 "TB - Diabetes" (not in the plan; see below) | 211–212 (180–181) | no (A1.2, PDF pp. 187–188) | n(%) | n(%) | n(%) | 36 (merged DNH and DD; Ladakh) |

**Usability for the registered data years (both the tested and the diabetic
counts must be printed):**
- **2018: usable.** Counts are printed for known blood-sugar status and for TB-DM
  patients, with the notified count in the same table. Only totals are printed
  (no public/private split).
- **2021: usable.** Counts are printed for known DM status and for TB-DM patients
  (public, private, total). Notified is not in the table; it is printed in
  TBAR 2022 A1.2.
- **2022: usable.** As 2021, with the percentage bases stated in the headers.
  Notified is in ITR 2023 A1.2.

In every year the count is printed. No cell needs to be derived from a
percentage in the Total columns; the `derived_from_percent` path (Review Focus 3)
is not needed for any Total cell found here.

**Findings that differ from the earlier controller scan** (for the controller to
decide; nothing is added to the plan here):
1. **ITR 2024 (data 2023) prints a State diabetes table**, Annexure 2.10, PDF
   pp. 211–212, with the same three column groups as ITR 2023.
2. **ITR 2020 (data 2019) prints a State diabetes table**, Annexure 2.5, PDF
   pp. 216–217, with counts. ITR 2020 is not in this repository's manifest; it
   was read from the sibling copy `../tb_priority_tool/data_raw/india_tb_report/ITR2020.pdf`
   (SHA-256 63b9408015dae510858e0eef2711e809d398bfe3149dd21c94390b258c007e7e
   in that repository's manifest). Its next table, A2.6 "TB - Tobacco"
   (PDF pp. 218–219), prints diabetes-worded headers [sic]; see below.
3. **ITR 2021 (data 2020, scan) also has A2.5 "TB-Diabetes"** (contents PDF
   p. 207; table PDF pp. 236–238), printing count (%) cells. It is a scan and the
   design does not use it.

---

## 2018: ITR 2019, `data_raw/india_tb_report/India-TB-Report-2019.pdf`

PDF page = printed page + 22. Annexure contents PDF p. 165 ("1.2 TB
Comorbidities 145"; the contents numbers run 2 lower than the printed pages).

**A1.2 "TB Comorbidities"**
- PDF pp. 169–170 (printed 147–148). Rotated (landscape on portrait) pages.
- Header: Total TB patients Notified (notified cases based on current PHI) |
  Total TB patients with known HIV status (%)# | HIV positive patients among
  tested* (%) | TB-HIV co- infected patients initiated on ART* | TB-HIV co-
  infected patients initiated on CPT* | Total TB patients with known blood sugar
  status (%) | Total TB- DM Co- morbid patients (%) | TB-DM Co-morbid patients
  Linked to NCD Clinic (%) | Total TB patients with known Tobacco usage status |
  Tobacco users among TB patients with known usage status | Tobacco users linked
  with Tobacco cessation centres
- The first column is the State name; it has no printed heading (the table
  title "1.2 TB Comorbidities" sits in its place).
- Diabetes columns, all printed as `count (%)`: known blood sugar status; TB-DM
  co-morbid patients; TB-DM co-morbid patients linked to NCD clinic. The
  percentage bases are not printed in the headers.
- No public/private split.
- Units: 36 rows. "Andaman & Nicobar Islands", "Dadra & Nagar Haveli" and
  "Daman & Diu" (separate), "Delhi", "Jammu & Kashmir" (no Ladakh row),
  "Lakshadweep", "Puducherry", "Telangana".
- Total row (PyMuPDF): `India | 2155894 | 1438912 (67%) | 49047 (3.4%) | 44080 | 45653 | 619470 (29%) | 47597 (8%) | 18882 (40%) | 467574 (22%) | 82258 | 17488`
- Footnotes: "* Source: NACO/ MPR report"; "# Data Complied [sic] from states".
- Reading note: pdfplumber's rotated-line rebuild splits multi-line cells (for
  example Assam's TB-DM cell and the India row are spread over three lines).
  The PyMuPDF block reading gives each row whole. Task 3 should read by block
  or by cell position, not by line.
- Definitional notes from the narrative, §6.2 "TB-Diabetes" (PDF pp. 64–65):
  - the TB-DM count is described as those "confirmed with newly
    diagnosed/already existing Diabetes", i.e. it includes previously known
    diabetes;
  - the "Linked to NCD Clinic" column's national figure is described in the
    narrative as initiated on anti-diabetic therapy.
- Notified by sex for 2018 is in A1.1 (PDF pp. 167–168): "TB patients
  notified$ – Gender (Male, Female, Trans- gender)" (from tb_priority_tool's
  inventory; not needed by the plan, which weights by 2022 only).

## 2021: TBAR 2022, `data_raw/india_tb_report/TBAnnaulReport2022.pdf`

Annexure contents PDF p. 86 ("2.5 TB - Diabetes 167", "2.6 TB - Tobacco 169").

**A2.5 "TB-Diabetes"**
- PDF p. 96 (printed spread 167–168).
- Header: State | TB patients with known DM status (%) (Public, Private, Total) |
  TB - DM Patients diagnosed among tested (%) (Public, Private, Total) | TB- DM
  patients initiated on Anti-diabetic treatment (%) (Public, Private, Total)
- Every cell is `count (%)`, or `NA`. NA appears only in Public/Private cells
  (Arunachal Pradesh, Lakshadweep, Puducherry private); no Total cell is NA.
- The percentage bases are not stated in the header.
- Notified is not in this table. It is printed in A1.2 "TB Case Notification",
  PDF p. 89: "TB patients notified (Achievement against target %) (Public,
  Private, Total)", India total 2135830, notification by diagnosing PHI (header
  and total as in tb_priority_tool's inventory, re-read here).
- Units: 36 rows, "Andaman & Nicobar Islands", "Dadra and Nagar Haveli and Daman
  and Diu" (merged), "Delhi", "Jammu & Kashmir", "Ladakh", "Lakshadweep",
  "Puducherry".
- Total row: `India | 1410182 (89%) | 489861 (88%) | 1900043 (89%) | 123021 (9%) | 34466 (7%) | 157487 (8%) | 79970 (65%) | 17176 (50%) | 97146 (62%)`
- No footnote is printed on the page.

## 2022: ITR 2023, `data_raw/india_tb_report/ITR2023.pdf`

PDF page = printed page + 30. Annexure contents PDF p. 207 ("2.10 TB - Diabetes
209", "2.11 TB - Tobacco 211").

**A2.10 "TB - DIABETES"**
- PDF pp. 239–240 (printed 209–210).
- Header: State | TB patients with known DM status, n (% of notified) (Public,
  Private, Total) | TB - DM Patients diagnosed among tested, n (% of those with
  known DM status) (Public, Private, Total) | TB- DM patients initiated on Anti-
  diabetic treatment, n (% of TB-DM) (Public, Private, Total)
- Every cell is `n (%)`, or `NA`. NA appears only in Public/Private cells
  (Arunachal Pradesh, Lakshadweep, Puducherry private); no Total cell is NA.
- Notified is not in this table. It is printed in A1.2 "TB CASE NOTIFICATION",
  PDF pp. 213–214: "TB patients notified, n (% achievement against target)
  (Public, Private, Total)", India total 2422121. The edition has no
  net-notified (current PHI) annexure.
- Units: 36 rows, "Andaman & Nicobar Islands", "Dadra and Nagar Haveli and Daman
  and Diu" (the name is a separate text block from its values on p. 239),
  "Delhi", "Jammu & Kashmir", "Ladakh", "Lakshadweep", "Puducherry".
- Total row: `India | 1707030 (92.1) | 508900 (89.6) | 2215930 (91.5) | 143167 (8.4) | 30564 (6) | 173731 (7.8) | 93897 (65.6) | 16161 (52.9) | 110058 (63.3)`
- **Notified by sex** (for the p_s weighting): A1.6 "GENDER DISAGGREGATED DATA ON
  TOTAL TB NOTIFICATION, PAEDIATRIC TB NOTIFICATION AND TREATMENT INITIATION",
  PDF pp. 221–222 (printed 191–192). Header: State | TB Cases Notified (Male,
  Female, Trans Gender) | Paediatric TB Cases Notified, n (% of total notified)
  (Male, Female, Trans Gender) | Total TB Cases initiated on treatment, n (% of
  total notified) (Male, Female, Trans Gender). Total row: `India | 1472190 | 948455 | 1021 | …`. Counts are printed.
- **Population:** A1.1 "PRESUMPTIVE TB CASES EXAMINATION", PDF p. 211 (printed
  181), column "Popula- tion - 2022 (in lakhs)".

## 2023: ITR 2024, `data_raw/india_tb_report/ITR2024.pdf` (not a registered data year)

PDF page = printed page + 31. Annexure contents PDF p. 182 ("2.10. TB –
Diabetes 181"; the page footers read 180–181).

**A2.10 "TB - Diabetes"**
- PDF pp. 211–212 (printed 180–181).
- Header: States/UTs | TB patients with known DM status, n(%) (Public, Private,
  Total) | TB - DM patients diagnosed among tested, n(%) (Public, Private,
  Total) | TB- DM patients initiated on anti-diabetic treatment, n(%) (Public,
  Private, Total)
- Every cell is `n (%)`, or `NA`; NA only in Public/Private cells. The
  percentage bases are not stated.
- Units: 36 rows, "Andaman and Nicobar Islands", "Dadra and Nagar Haveli and
  Daman and Diu", "Delhi", "Jammu and Kashmir", "Ladakh", "Lakshadweep",
  "Puducherry"; total row "INDIA".
- Total row: `INDIA | 1753665 (92.8) | 608279 (91.8) | 2361944 (92.5) | 145739 (8.3) | 35287 (5.8) | 181026 (7.7) | 95971 (65.9) | 16887 (47.9) | 112858 (62.3)`
- Notified: A1.2 "TB case notification", PDF pp. 187–188, India total 2552257
  (tb_priority_tool's inventory).

## 2019: ITR 2020 (sibling copy; not in this manifest; not a registered data year)

PDF page = printed page + 24. Contents PDF p. 201: "2.5 TB-Diabetes 192",
"2.6 TB - Tobacco 194".

**A2.5 "TB-Diabetes"**
- PDF pp. 216–217 (printed 192–193).
- Header: State | TB Patients notified (Public, Private, Total) | TB patients
  with known DM status (%) (Public, Private, Total) | TB Patients diagnosed with
  Diabetes among tested (%) (Public, Private, Total) | TB- DM patients initiated
  on Anti-diabetic treatment (%) (Public, Pri- vate, Total)
- Counts in every column; the percentage is printed on the Total cells only.
  Some Public/Private cells are blank (for example Lakshadweep private).
- Units: 36 rows; "Dadra & Nagar Haveli" and "Daman & Diu" separate; no Ladakh.
- Total row: `India | 1777168 | 627647 | 2404815 | 1279801 | 255649 | 1535450 (64%) | 99773 | 14518 | 114291 (7%) | 53354 | 6135 | 59489 (52%)`

**A2.6 "TB - Tobacco" [sic headers]**
- PDF pp. 218–219 (printed 194–195). Titled Tobacco, but the header reads:
  State | TB Patients Notified | TB patients with know [sic] Blood Glucose
  Status % | TB- Diabetes Co-morbid patients | TB-DM patients linked to diabetic
  treatment (each Public, Private, Total).
- Total row: `India | 1777168 | 627647 | 2404815 | 1160608 | 207622 | 1368230 (57%) | 177654 | 14453 | 192107 (14%) | 44399 | 2116 | 46515 (24%)`
- The values differ from A2.5. Which of the two tables carries diabetes data
  must be settled from the edition (or the controller) before 2019 is used.

## 2020: ITR 2021 (scan; not used)

`../tb_priority_tool/data_raw/india_tb_report/ITR2021.pdf` has no text layer.
Its contents (PDF p. 207) list "2.5 TB-Diabetes 214", "2.6 TB-Tobacco 217".
PDF p. 236 (printed 214), read by eye at 90 dpi, shows the header: State | TB
patients with known DM status (%) (Public, Private, Total) | TB - DM Patients
diagnosed among tested (%) (Public, Private, Total) | TB- DM patients initiated
on Anti-diabetic treatment (%) (Public, Private, Total), with `count (%)` cells
and a merged "Dadra and Nagar Haveli and Daman and Diu" row. No value was read.

## The third cascade step: linkage to diabetes treatment

| Data year | Verbatim header | Printed as |
|---|---|---|
| 2018 | TB-DM Co-morbid patients Linked to NCD Clinic (%) | count (%), total only |
| 2021 | TB- DM patients initiated on Anti-diabetic treatment (%) | count (%), public/private/total |
| 2022 | TB- DM patients initiated on Anti- diabetic treatment, n (% of TB-DM) | n (%), public/private/total |
| 2023 (ITR 2024) | TB- DM patients initiated on anti-diabetic treatment, n(%) | n(%), public/private/total |
| 2019 (ITR 2020 A2.5) | TB- DM patients initiated on Anti-diabetic treatment (%) | count; % on total only |

The 2018 step differs in wording: linked to an NCD clinic, not initiated on
anti-diabetic treatment (the ITR 2019 narrative treats the two as the same).

## Other State-level diabetes-related columns

- **Testing method (HbA1c, random or fasting glucose):** no TB report table
  prints it. A text search of the four manifest editions for "HbA1c",
  "glucose", "RBS", "FBS" and "glycated" found no annexure column; the only
  annexure hits are ITR 2019 A1.2 ("blood sugar status").
- **Tobacco** (same structure as the diabetes tables, not part of this study):
  - 2018: ITR 2019 A1.2, the last three columns (above). Counts; the known
    status column also prints (%).
  - 2021: TBAR 2022 A2.6 "TB-Tobacco", PDF p. 97 (printed 169–170). Header:
    State | TB patients with known Tobacco usage status (%) | Tobacco users
    identified amongst screened (%) | Tobacco users linked with Tobacco cessation
    centres (%) (each Public, Private, Total). Total row: `India | 1224478 (78%) | 348971 (62%) | 1573449 (74%) | 166626 (14%) | 23089 (7%) | 189715 (12%) | 51252 (31%) | 5384 (23%) | 56636 (30%)`
  - 2022: ITR 2023 A2.11 "TB - TOBACCO", PDF pp. 241–242 (printed 211–212).
    Header: State | TB patients with known Tobacco usage status, n (% of
    notified) | Tobacco users identified amongst screened, n (% of those with
    known tobacco usage status) | Tobacco users linked with Tobacco cessation
    centres, n (% of tobacco users) (each Public, Private, Total). Total row:
    `India | 1473433 (79.5) | 354179 (62.4) | 1827612 (75.5) | 194531 (13.2) | 16012 (4.5) | 210543 (11.5) | 62753 (32.3) | 4404 (27.5) | 67157 (31.9)`
  - 2023: ITR 2024 A2.11 "TB – Tobacco", PDF pp. 213–214, same structure, n(%).
- TBAR 2022, ITR 2023 and ITR 2024 also print TB-Alcohol annexures (A2.7, A2.12,
  A2.12); not inventoried.

---

## NFHS-5 State and UT fact sheets

Files: `data_raw/nfhs5/NFHS-5_India_and_State_Factsheet_Compendium_Phase-I.pdf`
(142 pages; 22 State/UT fact sheets, no India sheet) and
`…_Phase-II.pdf` (96 pages; India plus 14 State/UT fact sheets). Together they
cover the 36 States/UTs. Each fact sheet is six PDF pages: a cover ("State Fact
Sheet" or "Union Territory Fact Sheet" and the name), an introduction, and four
"<Name> - Key Indicators" pages. The front matter of Phase I (PDF pp. 1–8) is a
scan.

**Indicator lines** (identical on every sheet; verbatim, on the third Key
Indicators page, section "Blood Sugar Level among Adults (age 15 years and
above)"):
- Women: "101. Blood sugar level - high or very high (>140 mg/dl) or taking
  medicine to control blood sugar level23 (%)"
- Men: "104. Blood sugar level - high or very high (>140 mg/dl) or taking
  medicine to control blood sugar level23 (%)"
- Also printed: 99/102 "Blood sugar level - high (141-160 mg/dl)23 (%)" and
  100/103 "Blood sugar level - very high (>160 mg/dl)23 (%)".
- Footnote 23: "Random blood sugar measurement."
- Columns: NFHS-5 (Urban | Rural | Total) | NFHS-4 (Total). The NFHS-4 cell is
  "na" on lines 101 and 104 on every sheet. The analysis uses the
  NFHS-5 Total column.
- Column-heading period: "NFHS-5 (2019-20)" on all Phase I sheets; "NFHS-5
  (2020-21)" on the Phase II State/UT sheets; "NFHS-5 (2019-21)" on the India
  sheet.
- Cell flags: "( ) Based on 25-49 unweighted cases" and "* Percentage not shown;
  based on fewer than 25 unweighted cases". On lines 101 and 104, only
  Chandigarh's Rural cells are in parentheses; no Total cell is in parentheses
  or starred on any sheet.
- No confidence interval or standard error is printed.

**Population:** no population count is printed. Each introduction prints the
sample ("Information was gathered from N households, N women, and N men"), and
Key Indicators line 3 prints "Sex ratio of the total population (females per
1,000 males)". So the plan's fallback applies: NFHS units are merged by the ITR
population (ITR 2023 A1.1, "Population - 2022 (in lakhs)", PDF p. 211).

**Pages, per State/UT** (PDF page of the indicator lines; cover page in
brackets):

| Phase I unit (sheet type) | p. | Phase II unit (sheet type) | p. |
|---|---|---|---|
| Andaman & Nicobar Islands (UT) | 13 [9] | India (India Fact Sheet) | 9 [5] |
| Andhra Pradesh | 19 [15] | Arunachal Pradesh | 15 [11] |
| Assam | 25 [21] | Chhattisgarh | 21 [17] |
| Bihar | 31 [27] | Haryana | 27 [23] |
| Dadra & Nagar Haveli and Daman & Diu (UT) | 37 [33] | Jharkhand | 33 [29] |
| Goa | 43 [39] | Madhya Pradesh | 39 [35] |
| Gujarat | 49 [45] | Odisha | 45 [41] |
| Himachal Pradesh | 55 [51] | Punjab | 51 [47] |
| Jammu & Kashmir (UT) | 61 [57] | Rajasthan | 57 [53] |
| Karnataka | 67 [63] | Tamil Nadu (cover: "Tamil nadu") | 63 [59] |
| Kerala | 73 [69] | Uttar Pradesh | 69 [65] |
| Lakshadweep (UT) | 79 [75] | Uttarakhand | 75 [71] |
| Ladakh (UT) | 85 [81] | Chandigarh (UT) | 81 [77] |
| Maharashtra | 91 [87] | NCT Delhi (UT) | 87 [83] |
| Meghalaya | 97 [93] | Puducherry (UT) | 93 [89] |
| Manipur | 103 [99] | | |
| Mizoram | 109 [105] | | |
| Nagaland | 115 [111] | | |
| Sikkim | 121 [117] | | |
| Telangana | 127 [123] | | |
| Tripura | 133 [129] | | |
| West Bengal | 139 [135] | | |

**UT fact sheets and the TB units:**
- "Dadra & Nagar Haveli and Daman & Diu": one merged UT sheet, matching the
  merged TB row of 2021 and 2022; in 2018 the TB report prints DNH and D&D
  separately. Under the tb_priority_tool coarsening this unit goes with
  Gujarat.
- "Ladakh": its own UT sheet; goes with "Jammu & Kashmir" (own UT sheet). The
  2018 TB table has no Ladakh row.
- "Lakshadweep": own UT sheet; goes with Kerala.
- "Andaman & Nicobar Islands", "Chandigarh", "NCT Delhi" and "Puducherry": own
  UT sheets, each matching one TB row ("NCT Delhi" vs "Delhi" in the TB
  reports).

## Notes for Task 2 and Task 3

- The percentage base for "known DM status" is printed only in ITR 2023 ("% of
  notified"). Notified comes from a different annexure in 2021 and 2022
  (diagnosing PHI, A1.2), but from the same table in 2018 ("based on current
  PHI").
- Known DM status and TB-DM are public plus private in 2021 and 2022; 2018 has
  totals only. The analysis should use the Total columns in every year.
- The TB-DM count includes previously known diabetes (ITR 2019 narrative).
- The 2018 linkage column (linked to NCD clinic) is not worded like the 2021 and
  2022 columns (initiated on anti-diabetic treatment).
