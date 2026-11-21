# Environment

Every script is run as `python -I <script>` from the repository root, with LF line
endings (`.gitattributes`). Task 1 (the source manifest and the data inventory)
was run with:

- Windows 11 Pro (64-bit)
- Python 3.14.0
- pytest 9.0.0: the tests
- pdfplumber 0.11.8: reading the India TB Report tables, page by page, with
  `page.flush_cache()` after each page to bound memory; the rotated annexure
  pages are rebuilt from the characters as in tb_priority_tool's
  `src/extract/pdftext.py`
- PyMuPDF 1.27.2.3: locating pages, reading table rows and headers as text
  blocks, and reading the NFHS-5 fact-sheet indicator lines; used for the
  inventory only

`tools/fetch_sources.py` and `tests/test_manifest.py` use the standard library
only (plus pytest).

From Task 4, the analysis uses numpy 2.3.5 and scipy 1.16.3, and imports `tbprio`
pinned to v1.0.1 (`pyproject.toml`). matplotlib is used only for the manuscript
figures.

Task 3 (extraction, 21 Nov 2026) used the same Python 3.14.0 and pdfplumber
0.11.8 (`src/extract/`, page by page with `page.flush_cache()`). Run, from the
repository root: `python -I src/extract/itr_dm.py`, then
`python -I src/extract/nfhs.py`, then
`python -I verification/check_extraction_totals.py` and
`python -I verification/check_implied_denominator.py`. PyMuPDF was used only to
cross-read the ITR 2019 Annexure 1.2 rows and the NFHS-5 indicator lines, and to
render the pages read by eye for `tests/test_known_cells.py`; no committed code
imports it.

Task 4 (analysis, 21 Nov 2026) used Python 3.14.0, numpy 2.3.5, scipy 1.16.3 and the
installed tbprio 1.0.1 (its src/tbprio byte-identical to tag v1.0.1; checked by
`tests/test_analysis.py::test_tbprio_pinned_version`). Run, from the repository root:
`python -I src/run_all.py` (about two minutes; writes `outputs/*.csv`, byte-identical on
rerun). `python -I src/run_all.py --out DIR` writes to another directory.
