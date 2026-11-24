"""Tests of the DMSCRR profile (manuscript/v3): the journal's rules in verification/dmscrr.py, the
exhibit builder exhibits/make_dmscrr.py, the build's profile guard and verification/check_frozen.py.
None needs the private manuscript folder, pandoc or Microsoft Word."""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

import pytest

from exhibits import formats, make_dmscrr, make_online_material, make_tables
from tools import build_submission
from verification import check_frozen, check_manuscript_numbers as cmn, dmscrr, mutate_manuscript

ROOT = Path(__file__).resolve().parents[1]
TITLE = ("Tuberculosis services as an entry point to diabetes care: where people with both conditions are lost in "
         "India's States")


def test_title_and_keywords():
    assert dmscrr.title_problems(TITLE) == []
    assert any("characters" in p for p in dmscrr.title_problems(TITLE + ", 2018 to 2023"))
    assert any("abbreviations" in p for p in dmscrr.title_problems(TITLE.replace("Tuberculosis", "TB")))
    kw = dmscrr.split_keywords("Diabetes mellitus; Tuberculosis; Comorbidity; Care cascade; Screening; India")
    assert dmscrr.keyword_problems(kw) == []
    assert any("keywords" in p for p in dmscrr.keyword_problems(kw[:2]))
    assert any("keywords" in p for p in dmscrr.keyword_problems(kw + [f"k{i}" for i in range(7)]))
    assert any("multi-word" in p for p in dmscrr.keyword_problems(kw[:3] + ["Screening and linkage"]))


def test_abstract_heads_and_abbreviations():
    ab = ("**Background and Aims:** Text. **Methods:** Text. **Results:** Text. **Conclusions:** Text. "
          "**Keywords:** A; B")
    assert dmscrr.abstract_heads(ab) == list(dmscrr.ABSTRACT_PARTS)
    assert dmscrr.abstract_heads(ab.replace("Background and Aims", "Background")) != list(dmscrr.ABSTRACT_PARTS)
    assert dmscrr.undefined_abbreviations("**Methods:** People with tuberculosis (TB) and TB clinics.") == []
    assert dmscrr.undefined_abbreviations("**Methods:** TB and NCD services.") == ["NCD", "TB"]


def test_highlight_structure():
    good = ["Highlights", dmscrr.HIGHLIGHT_KNOWN, "a", "b", dmscrr.HIGHLIGHT_ADDS, dmscrr.HIGHLIGHT_NEW, "c", "d",
            dmscrr.HIGHLIGHT_IMPACT, "e"]
    parts, probs = dmscrr.highlight_structure(good)
    assert probs == [] and parts == {"known": ["a", "b"], "new": ["c", "d"], "impact": ["e"]}
    assert dmscrr.highlight_structure(good[:4] + ["x"] + good[4:])[1]
    assert dmscrr.highlight_structure(good[:-2] + ["e"])[1]
    assert any("characters" in p for p in dmscrr.highlight_structure(good[:-1] + ["x" * 86])[1])
    md = "# Highlights\n\n## " + dmscrr.HIGHLIGHT_KNOWN + "\n\n- a\n- b\n"
    assert dmscrr.highlight_lines_md(md)[:4] == ["Highlights", "", dmscrr.HIGHLIGHT_KNOWN, ""]


def test_reference_style():
    art = ("Huangfu P, Ugarte-Gil C, Golub J, Pearson F, Critchley J. The effects of diabetes. Int J Tuberc Lung Dis "
           "2019; 23: 783–96. https://doi.org/10.5588/ijtld.18.0433")
    assert dmscrr.entry_kind(art) == "article"
    assert dmscrr.ARTICLE.search(art.replace("diabetes.", "diabetes?")).group("journal") == "Int J Tuberc Lung Dis"
    assert dmscrr.entry_kind("X. A page. https://example.org/a Accessed 23 November 2026.") == "web"
    assert dmscrr.entry_kind("[dataset] A B. Data, Zenodo, v1.2.0; 2026. https://doi.org/10.5281/zenodo.XXXXXXX") == "zenodo"
    assert dmscrr.author_problems(1, art) == []
    seven = "Baker MA, Harries AD, Jeon CY, Hart JE, Kapur A, Lönnroth K, Ottmani SE. Title."
    assert dmscrr.author_problems(1, seven)
    assert dmscrr.author_problems(1, "Baker MA, Harries AD, et al. Title.")
    assert dmscrr.author_problems(1, seven.replace("Ottmani SE.", "et al.")) == []
    assert dmscrr.author_problems(1, "India Diabetes Mellitus–Tuberculosis Study Group. Title.") == []
    for ok in ("783–96", "e448–60", "S38–42", "385–443", "671–81", "1501–8", "e152", "102801"):
        assert dmscrr.page_problems(1, ok) == [], ok
    for bad in ("783–796", "1501–1508", "443–447", "S929–S930"):
        assert dmscrr.page_problems(1, bad), bad


def test_fill_counts(tmp_path):
    (tmp_path / "manuscript.md").write_text("# T\n\n## References\n\n1\\. A.\n\n2\\. B.\n\n## Figure legends\n",
                                            encoding="utf-8")
    text = "abstract [[abstract]]; total [[total]]; refs [[references]]"
    assert dmscrr.fill_counts(text, tmp_path) == text  # no counts yet: left as they are
    (tmp_path / "word_counts_word.json").write_text(json.dumps(
        {"abstract": 197, "main_with_headings": 3229, "display_words": 1042, "dmscrr_total": 4271}), encoding="utf-8")
    assert dmscrr.fill_counts(text, tmp_path) == "abstract 197; total 4,271; refs 2"


def test_table1_and_supplement_from_outputs():
    (t1,) = make_dmscrr.build(ROOT)
    assert len(t1.rows) == 33 and t1.header[-1] == "First step"
    pr = formats.read_csv(ROOT, "outputs/cascade.csv")
    st = {r["unit"]: float(r["C3"]) for r in pr if r["spec"] == "main" and r["year"] == "2023" and r["unit"] in
          {row[0] for row in t1.rows}}
    for row in t1.rows:
        assert row[-1].startswith("Linkage, then") == (st[row[0]] < 0.5)
    labels = [t.label for t in make_dmscrr.supplement_tables(ROOT)]
    assert labels == [f"Table S{k}" for k in range(1, 15)]
    assert set(make_dmscrr.SUPPLEMENT_ORDER) == {t.label for t in make_tables.build(ROOT)} - {"Table S14"}
    md = make_dmscrr.supplement_md(ROOT)
    assert md.count("\n## Table S") == 14 and "\n## Figure S1\n" in md and "\n## Notation\n" in md
    assert make_dmscrr.supplement_md(ROOT) == md
    assert make_online_material.tables(ROOT)[0].label == "Table S1"  # the public online material is unchanged
    with pytest.raises(ValueError):
        make_online_material.tables(ROOT, ["Table S1", "Table S1"])


def test_catalogue_has_dmscrr_values():
    cat = cmn.catalogue_for(ROOT, "dmscrr")
    assert cat["plan.mmol"][0] == "7.8 mmol/l"
    assert cat["nat.C3.2019"][0] == "52.1%" and cat["nat.C3.2023"][0] == cat["nat.C3"][0]
    assert cat["nat.notinit"][0] == "68 168"


def test_dmscrr_citation_checks(tmp_path):
    ex = tmp_path / "exhibits"
    ex.mkdir()
    (ex / "supplement.md").write_text("## Table S1. a\n\n## Table S2. b\n\n## Figure S1\n\nx\n", encoding="utf-8")
    legends = "\n\n## Figure legends\n\n**Figure 1.** a\n\n**Figure 2.** b\n\n**Figure 3.** c\n"
    body = "# T\n\n## Results\n\nA (Table 1; Table S1). B (Figure 1). C (Figure 2; Table S2). D (Figure 3, Figure S1)."
    assert cmn.exhibit_problems_dmscrr(body + legends, tmp_path) == []
    found = " ".join(cmn.exhibit_problems_dmscrr(body.replace("B (Figure 1). C (Figure 2;", "B (Figure 2). C (Figure 1;") + legends, tmp_path))
    assert "out of order" in found
    found = " ".join(cmn.exhibit_problems_dmscrr(body.replace("Table S1)", "Table S2)", 1) + legends, tmp_path))
    assert "never cited: ['S1']" in found and "S1, S2" in found
    found = " ".join(cmn.exhibit_problems_dmscrr(body + " (Table S3)" + legends, tmp_path))
    assert "not in the supplementary material" in found
    assert "beyond Table 1" in " ".join(cmn.exhibit_problems_dmscrr(body + " (Table 2)" + legends, tmp_path))
    assert "never cited: ['S1']" in " ".join(cmn.exhibit_problems_dmscrr(body.replace(", Figure S1", "") + legends,
                                                                          tmp_path))


def test_dmscrr_structure_rules():
    secs = "".join(f"## {h}\n\n{'x'}\n\n" for h in dmscrr.SECTION_ORDER)
    text = "# T\n\n" + secs
    text = text.replace("## Funding\n\nx", "## Funding\n\n" + dmscrr.FUNDING)
    text = text.replace(f"## {dmscrr.AI_HEADING}\n\nx", f"## {dmscrr.AI_HEADING}\n\n" + dmscrr.GENAI)
    text = text.replace("## Declaration of competing interest\n\nx", "## Declaration of competing interest\n\n"
                        + dmscrr.COMPETING)
    assert cmn.structure_problems_dmscrr(text) == []
    moved = text.replace("## Acknowledgements\n\nx\n\n", "").replace("## References", "## Acknowledgements\n\nx\n\n"
                                                                      "## References")
    assert cmn.structure_problems_dmscrr(moved) == []
    bad = text.replace(f"## {dmscrr.AI_HEADING}\n\n{dmscrr.GENAI}\n\n## Acknowledgements\n\nx",
                       f"## Acknowledgements\n\nx\n\n## {dmscrr.AI_HEADING}\n\n{dmscrr.GENAI}")
    assert any("directly before" in p for p in cmn.structure_problems_dmscrr(bad))
    assert any("no-funding" in p for p in cmn.structure_problems_dmscrr(text.replace("any specific", "a specific")))
    assert any("generative-AI" in p for p in cmn.structure_problems_dmscrr(text.replace("a large language model, ", "")))


def test_dmscrr_wording():
    assert dmscrr.wording_hits("People with TB; options for the programmes.") == []
    hits = " ".join(dmscrr.wording_hits("This is the first study; after review at Primary Care Diabetes; IJTLD; "
                                        "TB patients"))
    assert "first" in hits and "earlier journal" in hits and "person-first" in hits


def test_build_accepts_the_dmscrr_profile_only_for_its_folder(tmp_path):
    (tmp_path / "section_phrases.json").write_text('{"journal": "dmscrr", "sections": {"Abstract": ["x"]}}',
                                                   encoding="utf-8")
    with pytest.raises(SystemExit) as e:
        build_submission.main(["--manuscript-dir", str(tmp_path), "--profile", "ijtld", "--no-word"])
    assert "does not match" in str(e.value.code)
    assert "dmscrr" in build_submission.PROFILES


def test_dmscrr_mutations_are_named_uniquely():
    ids = [m[0] for m in mutate_manuscript.MUTATIONS_DMSCRR]
    assert len(set(ids)) == len(ids) and all(re.fullmatch(r"d\d+", i) for i in ids)


def test_frozen_check_detects_changes(tmp_path):
    sub = tmp_path / "submission"
    sub.mkdir()
    (sub / "01_a.docx").write_bytes(b"one")
    (sub / "02_b.tif").write_bytes(b"two")
    rec = "".join(f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {'*' if i else ''}{p.name}\n"
                  for i, p in enumerate(sorted(sub.iterdir())))
    (sub / "SUBMITTED_2026-11-24.txt").write_text("Submitted.\n\nSHA-256:\n" + rec, encoding="utf-8")
    (sub / "~$_a.docx").write_bytes(b"lock")
    assert check_frozen.problems(sub) == ([], 2)
    (sub / "01_a.docx").write_bytes(b"changed")
    assert "differs" in " ".join(check_frozen.problems(sub)[0])
    (sub / "01_a.docx").write_bytes(b"one")
    (sub / "03_new.docx").write_bytes(b"x")
    assert "added after submission" in " ".join(check_frozen.problems(sub)[0])
    (sub / "03_new.docx").unlink()
    (sub / "02_b.tif").unlink()
    assert "missing" in " ".join(check_frozen.problems(sub)[0])
