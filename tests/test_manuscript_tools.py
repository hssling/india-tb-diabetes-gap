"""Tests of the manuscript tooling: the exhibit builders, the submission build's guards and
the manuscript checks. None needs the private manuscript folder, pandoc or Microsoft Word."""
from __future__ import annotations

import re
from pathlib import Path

import pytest

from exhibits import formats, make_figures, make_graphical_abstract, make_tables
from tools import build_submission
from verification import check_docx_tie, check_manuscript_numbers as cmn, mutate_manuscript

ROOT = Path(__file__).resolve().parents[1]


# --------------------------------------------------------------------------------------
# Number formats
# --------------------------------------------------------------------------------------
def test_formats():
    assert formats.count("108647.3365") == "108,647"
    assert formats.count(-1234.4) == "−1,234"
    assert formats.pct("0.92543") == "92.5%"
    assert formats.ratio("1.7012817") == "1.70"
    assert formats.prob(1.0) == "1" and formats.prob(0.0) == "0"
    assert formats.prob(0.99999) == ">0.999" and formats.prob(0.997) == "0.997"
    assert formats.prob(0.0004) == "<0.001"
    assert formats.patients("5389.4", "5344.2", "5435.0") == "5,389 (5,344 to 5,435)"
    assert formats.and_list(["A", "B", "C"]) == "A, B and C" and formats.and_list([]) == "none"
    assert formats.day("2026-11-21T15:05:56Z") == "21 November 2026"


# --------------------------------------------------------------------------------------
# Exhibits: every cell built from outputs/
# --------------------------------------------------------------------------------------
def test_tables_build_from_outputs():
    tables = make_tables.build(ROOT)
    labels = [t.label for t in tables]
    assert labels == ["Table 1"] + [f"Table S{k}" for k in range(1, 15)]
    for t in tables:
        assert t.rows and t.notes
        for r in t.rows:
            assert len(r) == len(t.header), t.label
            assert not any("|" in c for c in r)
    md = make_tables.render_md(tables)
    assert md == make_tables.render_md(make_tables.build(ROOT))  # deterministic
    t1 = tables[0]
    h1 = next(r for r in t1.rows if r[0] == "H1")
    assert h1[-1].startswith("supported")


def test_table_s7_tiers_match_priority_output():
    pr = [r for r in formats.read_csv(ROOT, "outputs/priority.csv")
          if r["spec"] == "main" and r["year"] == "2023" and r["gap"] == "E2" and r["tier"] == "act now"]
    s7 = next(t for t in make_tables.build(ROOT) if t.label == "Table S7")
    act = sorted(r[0] for r in s7.rows if r[4].endswith("(act now)"))
    assert act == sorted(r["unit"] for r in pr)


def test_figure_and_graphical_abstract_data():
    for k, fn in make_figures.FIGURES.items():
        rows = fn(ROOT)
        assert rows, k
        assert make_figures.data_csv(rows) == make_figures.data_csv(fn(ROOT))
    assert len(make_figures.fig2_data(ROOT)) == 33
    assert {r["gap"] for r in make_figures.fig3_data(ROOT)} == {"E1", "E2", "E3"}
    assert {r["year"] for r in make_figures.fig4_data(ROOT)} == {"2019", "2021", "2023"}
    ga = {r["item"]: r["value"] for r in make_graphical_abstract.ga_data(ROOT)}
    assert ga["units"] == "33" and ga["act now E2"].count(";") == 4
    assert set(make_figures.CODE) == {r["unit"] for r in make_figures.fig2_data(ROOT)}
    assert len(set(make_figures.CODE.values())) == 33


# --------------------------------------------------------------------------------------
# The number check: catalogue, claims and rules
# --------------------------------------------------------------------------------------
def test_catalogue_and_claims_hold_on_outputs():
    cat = cmn.catalogue(ROOT)
    assert cat["kb"][0] == "0.822" and cat["H1.label"][0] == "supported"
    assert cat["date.registration"][0] == "21 November 2026"
    assert cmn.claims(ROOT) == []


def test_wording_rules():
    ok = "## Results\n\nDiabetes identified (newly diagnosed or known). Under the fixed rule at k = 1, units showed \"likely under-detection\".\n"
    assert cmn.wording_problems("x.md", ok) == []
    bad = ("## Results\n\nPatients newly diagnosed with diabetes. The States are detection-led. Bihar shows "
           "under-detection. The program caused it.\n")
    found = " ".join(cmn.wording_problems("x.md", bad))
    for what in ("newly diagnosed", "identification-led", "likely under-detection", "causal", "American"):
        assert what in found


def test_reference_order_and_limits():
    text = ("# T\n\n## Introduction\n\nA [1,2] and B [3].\n\n## References\n\n"
            "[1] A, T, J 1 (2000) 1–2. https://doi.org/10.1/a.\n[2] B, T, J 1 (2000) 1–2. https://doi.org/10.1/b.\n"
            "[3] C, T, J 1 (2000) 1–2. https://doi.org/10.1/c.\n")
    assert cmn.reference_problems(text) == []
    swapped = text.replace("A [1,2] and B [3]", "A [1,3] and B [2]")
    assert any("first citation" in p for p in cmn.reference_problems(swapped))


def test_length_rules():
    text = ("# T\n\n## Abstract\n\n**Aims:** a.\n\n**Methods:** b.\n\n**Results:** c.\n\n**Conclusions:** d.\n\n"
            "**Keywords:** A; B\n\n## Introduction\n\nx\n\n## Methods\n\nx\n\n## Results\n\nx\n\n## Discussion\n\nx\n")
    assert cmn.length_problems(text, "# Highlights\n\n- a\n- b\n- c\n") == []
    long = text.replace("**Aims:** a.", "**Aims:** " + "w " * 200)
    assert any("abstract" in p for p in cmn.length_problems(long, None))
    unstructured = text.replace("**Methods:** b.", "b.")
    assert any("headings" in p for p in cmn.length_problems(unstructured, None))


# --------------------------------------------------------------------------------------
# Guards: no manuscript folder, unknown options, a submitted folder
# --------------------------------------------------------------------------------------
def test_checks_skip_without_the_private_folder(tmp_path, capsys):
    argv = ["--manuscript-dir", str(tmp_path / "absent")]
    assert cmn.main(ROOT, argv) == 0 and "SKIPPED" in capsys.readouterr().out
    assert check_docx_tie.main(ROOT, argv) == 0 and "SKIPPED" in capsys.readouterr().out
    assert mutate_manuscript.main(argv, ROOT) == 0 and "SKIPPED" in capsys.readouterr().out
    assert cmn.main(ROOT, argv + ["--bogus"]) == 1


def test_number_check_fails_when_phrases_are_missing(tmp_path, capsys):
    (tmp_path / cmn.MS_NAME).write_text("# T\n", encoding="utf-8")
    assert cmn.main(ROOT, ["--manuscript-dir", str(tmp_path)]) == 1
    assert "is missing" in capsys.readouterr().out


def test_build_rejects_unknown_options_and_bad_doi(tmp_path):
    with pytest.raises(SystemExit) as e:
        build_submission.main(["--manuscript-dir", str(tmp_path), "--bogus"])
    assert e.value.code == 2
    with pytest.raises(SystemExit) as e:
        build_submission.main(["--manuscript-dir", str(tmp_path), "--do", "10.5281/zenodo.1"])  # no abbreviations
    assert e.value.code == 2
    with pytest.raises(SystemExit) as e:
        build_submission.main(["--manuscript-dir", str(tmp_path), "--doi", "10.1000/xyz"])
    assert "--doi must look like" in str(e.value.code)


def test_build_refuses_a_submitted_folder(tmp_path):
    (tmp_path / "submission").mkdir()
    (tmp_path / "submission" / "SUBMITTED_2026-11-21.txt").write_text("sent", encoding="utf-8")
    with pytest.raises(SystemExit) as e:
        build_submission.main(["--manuscript-dir", str(tmp_path), "--no-word"])
    assert "refusing to write" in str(e.value.code)
    assert not (tmp_path / "submission" / "02_manuscript.docx").exists()
    (tmp_path / "submission" / "SUBMITTED_2026-11-21.txt").unlink()
    (tmp_path / "SUBMITTED_note.md").write_text("sent", encoding="utf-8")
    with pytest.raises(SystemExit) as e:
        build_submission.main(["--manuscript-dir", str(tmp_path), "--no-word"])
    assert "refusing to write" in str(e.value.code)


def test_doi_placeholder_is_filled_everywhere():
    md = "x 10.5281/zenodo.XXXXXXX y https://doi.org/10.5281/zenodo.XXXXXXX"
    assert build_submission.with_doi(md, "10.5281/zenodo.123") == "x 10.5281/zenodo.123 y https://doi.org/10.5281/zenodo.123"
    assert build_submission.with_doi(md, None) == md


def test_docx_tie_normalisation_and_md_units():
    units = check_docx_tie.md_units("## Results\n\n**H1** was 1.70\n(95% interval).\n\n| a | b |\n|---|---|\n| 1 | 2 |\n")
    assert units == ["Results", "H1 was 1.70 (95% interval).", "a | b", "1 | 2"]
    assert check_docx_tie.norm("doi 10.5281/zenodo.123") == check_docx_tie.norm("doi 10.5281/zenodo.XXXXXXX")


def test_mutation_sweep_skips_front_matter_and_references():
    text = "# Title 2023\n\n**Author:** X 572106\n\n## Abstract\n\nA 92.5%.\n\n## References\n\n[1] Y 12 (2000) 1.\n"
    toks = [text[a:b] for a, b in mutate_manuscript.md_token_spans(text)]
    assert toks == ["2023", "92.5"]
    assert len({m[0] for m in mutate_manuscript.MUTATIONS}) == len(mutate_manuscript.MUTATIONS)
    assert all(re.fullmatch(r"\d+[a-z]", m[0]) for m in mutate_manuscript.MUTATIONS)


def test_guidance_rule_uses_existing_outputs_only():
    assert make_tables.guidance_step("identification-led", True)[0].startswith("linkage")
    assert make_tables.guidance_step("screening-led", False) == (make_tables.STEP_TEXT["screening-led"], make_tables.DASH)
    s14 = next(t for t in make_tables.build(ROOT) if t.label == "Table S14")
    dc = {r["unit"]: r["class"] for r in formats.read_csv(ROOT, "outputs/decomposition.csv")
          if r["spec"] == "main" and r["year"] == "2023"}
    assert {r[0]: r[1] for r in s14.rows} == dc


# --------------------------------------------------------------------------------------
# The IJTLD profile (manuscript/v2): hard limits, display items and online material
# --------------------------------------------------------------------------------------
def test_ijtld_title_running_head_and_keywords():
    from verification import ijtld
    title = "Beyond screening: the tuberculosis–diabetes care cascade across India's States, 2018–2023"
    assert ijtld.title_problems(title) == []
    assert any("characters" in p for p in ijtld.title_problems(title + " and" * 10))
    assert any("abbreviations" in p for p in ijtld.title_problems(title.replace("tuberculosis", "TB")))
    assert ijtld.running_head_problems("Tuberculosis–diabetes care cascade in India") == []
    assert ijtld.running_head_problems("x" * 46) and ijtld.running_head_problems("")
    kw = ["comorbidity", "benchmarking", "programme monitoring", "hyperglycaemia", "ecological study"]
    assert ijtld.keyword_problems(kw, title) == []
    assert any("repeats" in p for p in ijtld.keyword_problems(kw[:4] + ["screening"], title))
    assert any("keywords" in p for p in ijtld.keyword_problems(kw[:2], title))
    assert any("keywords" in p for p in ijtld.keyword_problems(kw + ["surveillance"], title))


def test_ijtld_abstract_abbreviations_and_wording():
    from verification import ijtld
    assert ijtld.abbreviations("**Background:** People with tuberculosis in India's States.") == []
    assert ijtld.abbreviations("People with TB (95% CI) and HbA1c in NFHS-5") == ["TB", "CI", "HbA1c", "NFHS-5"]
    hits = " ".join(ijtld.wording_hits("TB patients, a defaulter, a TB suspect, a pre-registered plan, the referee"))
    for what in ("person-first", "defaulter", "suspect", "pre-registered", "drafting-process"):
        assert what in hits
    assert ijtld.wording_hits("People with TB; the steps to strengthen.") == []


def test_ijtld_reference_style():
    from verification import ijtld
    assert ijtld.entry_kind("Jeon CY, Murray MB. A title. PLoS Med 2008; 5: e152.") == "article"
    assert ijtld.entry_kind("Nair S, et al. A title. Public Health Action 2013; 3 (Suppl 1): S38–S42.") == "article"
    assert ijtld.entry_kind("X. A page. https://example.org/a Accessed 23 November 2026.") == "web"
    assert ijtld.entry_kind("X. Data. Version 1.1.0 [dataset]. Zenodo, 2026. https://doi.org/10.5281/zenodo.XXXXXXX") == "zenodo"
    assert ijtld.author_problems(1, "Brown LD, Cai TT, DasGupta A. Title. Stat Sci 2001; 16: 101–133.") == []
    assert ijtld.author_problems(1, "Kiefe CI, Weissman NW, Allison JJ, Farmer R. Title. J 1998; 10: 1.")
    assert ijtld.author_problems(1, "Kiefe CI, Weissman NW, et al. Title. J 1998; 10: 1.")


def test_ijtld_number_style():
    assert formats.ijtld_style("108,647 (107,967 to 109,333)") == "108 647 (107 967–109 333)"
    assert formats.about_thousands(35506) == "36 000"
    cat = cmn.catalogue_for(ROOT, "ijtld")
    assert cat["scen.about"][0] == "109 000" and cat["scen.fold"][0] == "3–5-fold"
    assert cat["H1.ci"][0] == "1.01–2.18"


def test_ijtld_table_and_figures_from_outputs():
    from exhibits import make_ijtld
    (t1,) = make_ijtld.build(ROOT)
    assert t1.label == "Table 1" and len(t1.rows) == 33 and len(t1.header) == 7
    dc = {r["unit"]: r["class"] for r in formats.read_csv(ROOT, "outputs/decomposition.csv")
          if r["spec"] == "main" and r["year"] == "2023"}
    words = {"Identification": "identification-led", "Screening": "screening-led", "Mixed": "mixed"}
    assert {r[0]: words[r[4]] for r in t1.rows} == dc
    assert make_ijtld.render(ROOT) == make_ijtld.render(ROOT)
    assert set(make_ijtld.FIGURES) == {1, 2}


def test_online_material_is_person_first_and_complete():
    from exhibits import make_online_material as mo
    files = mo.text_files(ROOT)
    assert {f"tableS{k}.csv" for k in range(1, 16)} <= set(files)
    for name, data in files.items():
        assert not mo.STIGMA.search(data.decode("utf-8")), name
    assert mo.person_first("TB patients screened (log scale)") == "People with TB screened (log scale)"
    assert files == mo.text_files(ROOT)


def test_ijtld_introduction_heading_and_build_profile(tmp_path):
    assert check_docx_tie.drop_introduction_heading("## Introduction\n\nText.\n") == "Text.\n"
    with pytest.raises(ValueError):
        check_docx_tie.drop_introduction_heading("## Methods\n\nText.\n")
    (tmp_path / "section_phrases.json").write_text('{"journal": "ijtld", "sections": {"Abstract": ["x"]}}',
                                                   encoding="utf-8")
    with pytest.raises(SystemExit) as e:
        build_submission.main(["--manuscript-dir", str(tmp_path), "--profile", "pcd", "--no-word"])
    assert "does not match" in str(e.value.code)
    with pytest.raises(SystemExit) as e:
        build_submission.main(["--manuscript-dir", str(tmp_path), "--profile", "nejm"])
    assert e.value.code == 2


def test_ijtld_mutations_are_named_uniquely():
    ids = [m[0] for m in mutate_manuscript.MUTATIONS_IJTLD]
    assert len(set(ids)) == len(ids) and all(re.fullmatch(r"i\d+[a-z]", i) for i in ids)
