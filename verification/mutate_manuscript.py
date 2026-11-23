# Adapted from hssling/india-tb-priority-tool v1.0.1 (MIT), verification/mutate_manuscript.py (itself
# adapted from hssling/india-tb-acf-campaign and hssling/india-state-tb-score); modified: the named
# mutations of this paper's Primary Care Diabetes set (numbers, the title page that a single-
# anonymized manuscript must carry, references, table cells, figure and graphical-abstract data,
# labels, signs, identifiers, wording, the highlight, abstract and main-text limits, Word's counts,
# declarations, caveats, figures, display items, the cover letter and the file set), applied to
# copies inside the git-ignored manuscript folder; the number-token sweeps kept as --sweep.
"""Mutation test of the manuscript checks (check_manuscript_numbers and check_docx_tie).

Run as: python -I verification/mutate_manuscript.py [--manuscript-dir DIR] [--sweep]

The manuscript folder DIR (default manuscript/; git-ignored) is copied for every mutation into
DIR/_mutations/ (removed afterwards); the real files are never written. The large binary files of
submission/ (TIFF, PDF) are hard-linked into each copy, and a mutation that changes one of them
replaces the link with a new file. Each named mutation (MUTATIONS) changes one thing in the copy,
and both checks run on it: check_manuscript_numbers.problems and check_docx_tie.problems. A
mutation is caught if either reports at least one problem. The unmutated copy must pass both, or
nothing is run.

The manuscript text a mutation edits (its anchor) quotes the manuscript, so it is not kept here: it
is read from "mutation_anchors" in the private DIR/section_phrases.json. A mutation whose anchor is
missing or not found counts as NOT APPLIED and fails the run.

--sweep also bumps the last digit of every number token (a) of manuscript.md outside the
References, which check_manuscript_numbers must catch, and (b) of the text of 02_manuscript.docx,
tables and references included, which check_docx_tie must catch.

Prints a table of the results; exits 1 if any mutation is not applied or not caught. Prints
"SKIPPED" and exits 0 when DIR/ or DIR/submission/ is absent.

An IJTLD folder (section_phrases.json "journal": "ijtld"; manuscript/v2) runs MUTATIONS_IJTLD
instead: numbers, table cells, citations and references, every IJTLD hard limit (title, running
head, keywords, abstract words and abbreviations, main-text words, references, display items),
"pre-registered", stigmatising and process words, the online material, the layout (line numbers,
spacing, justification), the figures and the file set.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path
from typing import Callable

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from verification import check_docx_tie as tie  # noqa: E402
from verification import check_manuscript_numbers as cmn  # noqa: E402

DOC = "word/document.xml"
S = "submission/"
T01, M02, H03, S08, C09 = (S + n for n in ("01_title_page.docx", "02_manuscript.docx", "03_highlights.docx",
                                           "08_supplementary_material.docx", "09_cover_letter.docx"))
FIG1_TIF, FIG1_PDF = (S + n for n in tie.FIGURES[1])
GA_TIF = S + tie.GA[0]
NUMBER = re.compile(r"\d+(?:,\d{3}(?!\d))*(?:\.\d+)?")
WORK = "_mutations"
LINKED = (".tif", ".pdf")
MS = cmn.MS_NAME
TABLES_MD = "exhibits/tables.md"


class NotApplied(Exception):
    """The mutation's anchor was not found in the copy."""


# --------------------------------------------------------------------------------------
# Editing helpers (on the copy; a file is replaced, never written through a hard link)
# --------------------------------------------------------------------------------------
def replace_bytes(path: Path, data: bytes) -> None:
    tmp = path.with_name(path.name + ".new")
    tmp.write_bytes(data)
    path.unlink()
    tmp.replace(path)


def edit_text(path: Path, old: str, new: str) -> None:
    s = path.read_text(encoding="utf-8")
    if old not in s:
        raise NotApplied(f"{path.name}: {old!r} not found")
    replace_bytes(path, s.replace(old, new, 1).encode("utf-8"))


def rewrite_part(path: Path, part: str, fn: Callable[[str], str]) -> None:
    tmp = path.with_name(path.name + ".mut")
    with zipfile.ZipFile(path) as zi, zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as zo:
        for item in zi.infolist():
            data = zi.read(item.filename)
            if item.filename == part:
                data = fn(data.decode("utf-8")).encode("utf-8")
            zo.writestr(item, data)
    path.unlink()
    tmp.replace(path)


def edit_docx(path: Path, old: str, new: str, part: str = DOC) -> None:
    def fn(xml: str) -> str:
        if old not in xml:
            raise NotApplied(f"{path.name}:{part}: {old!r} not found")
        return xml.replace(old, new, 1)
    rewrite_part(path, part, fn)


def bump(tok: str) -> str:
    return tok[:-1] + str((int(tok[-1]) + 1) % 10)


def bumped(s: str) -> str:
    m = NUMBER.search(s)
    if not m:
        raise NotApplied(f"no number in anchor {s!r}")
    return s[:m.start()] + bump(m.group()) + s[m.end():]


def flipped(s: str) -> str:
    m = NUMBER.search(s)
    if not m:
        raise NotApplied(f"no number in anchor {s!r}")
    if m.start() > 0 and s[m.start() - 1] == cmn.MINUS:
        return s[:m.start() - 1] + s[m.start():]
    return s[:m.start()] + cmn.MINUS + s[m.start():]


def anchor(d: Path, mid: str):
    try:
        a = cmn.load_phrase_file(d).get("mutation_anchors", {}).get(mid)
    except (OSError, ValueError) as e:
        raise NotApplied(f"{cmn.PHRASES}: {e}") from None
    if not a:
        raise NotApplied(f"no anchor for mutation {mid} in {cmn.PHRASES}")
    return a


def change(edit, rel: str, mid: str, how: Callable[[str], str]) -> Callable[[Path], None]:
    def fn(d: Path) -> None:
        a = anchor(d, mid)
        edit(d / rel, a, how(a))
    return fn


def insert(edit, rel: str, mid: str, extra: Callable[[Path], str], before: bool = False) -> Callable[[Path], None]:
    def fn(d: Path) -> None:
        a, x = anchor(d, mid), extra(d)
        edit(d / rel, a, x + a if before else a + x)
    return fn


def swap(edit, rel: str, mid: str) -> Callable[[Path], None]:
    """The anchor is a pair [old, new]."""
    def fn(d: Path) -> None:
        a = anchor(d, mid)
        if not (isinstance(a, list) and len(a) == 2):
            raise NotApplied(f"anchor of {mid} must be a pair [old, new]")
        edit(d / rel, a[0], a[1])
    return fn


def renumber_refs(d: Path) -> None:
    """02 References: the entry numbers [2] and [3] exchanged."""
    def fn(xml: str) -> str:
        for a, b in (("[2] ", "[@@] "), ("[3] ", "[2] "), ("[@@] ", "[3] ")):
            i = xml.find(">" + a, xml.find(">References<"))
            if i < 0:
                raise NotApplied(f"02: reference entry {a!r} not found")
            xml = xml[:i + 1] + b + xml[i + 1 + len(a):]
        return xml
    rewrite_part(d / M02, DOC, fn)


def low_dpi_tiff(d: Path) -> None:
    try:
        from PIL import Image
    except ImportError:
        raise NotApplied("Pillow not installed") from None
    p = d / FIG1_TIF
    p.unlink()
    Image.new("L", (100, 100), 255).save(p, format="TIFF", dpi=(300, 300))


def small_ga(d: Path) -> None:
    try:
        from PIL import Image
    except ImportError:
        raise NotApplied("Pillow not installed") from None
    p = d / GA_TIF
    p.unlink()
    Image.new("RGB", (1200, 480), "white").save(p, format="TIFF", dpi=(300, 300))


def other_figure(d: Path) -> None:
    replace_bytes(d / FIG1_PDF, (d / "exhibits" / "figure2.pdf").read_bytes())


def edit_csv(rel: str, old: str, new: str) -> Callable[[Path], None]:
    def fn(d: Path) -> None:
        p = d / "exhibits" / rel
        s = p.read_text(encoding="utf-8")
        if old not in s:
            raise NotApplied(f"{rel}: {old!r} not found")
        replace_bytes(p, s.replace(old, new, 1).encode("utf-8"))
    return fn


def second_table(d: Path) -> None:
    """02: Table 1 duplicated (six display items)."""
    def fn(xml: str) -> str:
        i, j = xml.find("<w:tbl>"), xml.find("</w:tbl>")
        if i < 0 or j < 0:
            raise NotApplied("02 has no table")
        t = xml[i:j + len("</w:tbl>")]
        return xml[:j + len("</w:tbl>")] + t + xml[j + len("</w:tbl>"):]
    rewrite_part(d / M02, DOC, fn)


def stale_counts(d: Path) -> None:
    p = d / "word_counts_word.json"
    w = json.loads(p.read_text(encoding="utf-8"))
    w["abstract"] = tie.LIMITS["abstract"] + 1
    replace_bytes(p, (json.dumps(w, indent=1) + "\n").encode("utf-8"))


def long_main(d: Path) -> None:
    """manuscript.md Discussion: 700 words added (the main text over 3,000 words)."""
    a = anchor(d, "9d")
    edit_text(d / MS, a, a + " " + " ".join(["filler"] * 700))


def extra_file(d: Path) -> None:
    (d / S / "12_notes.txt").write_text("x", encoding="utf-8")


def drop_file(d: Path) -> None:
    (d / C09).unlink()


# --------------------------------------------------------------------------------------
# The named mutations: (id, kind, what is changed, function of the copied folder)
# --------------------------------------------------------------------------------------
Mutation = tuple[str, str, str, Callable[[Path], None]]
MUTATIONS: list[Mutation] = [
    ("1a", "number, docx only", "02 Results: the H1 value changed in its last digit", change(edit_docx, M02, "1a", bumped)),
    ("1b", "number, docx only", "01 title page: Word's abstract count increased by 1", change(edit_docx, T01, "1b", bumped)),
    ("1c", "number, docx only", "08 Table S7: a screening-gap cell changed in its last digit", change(edit_docx, S08, "1c", bumped)),
    ("2a", "number, markdown only", "manuscript.md Results: the H2 value changed in its last digit", change(edit_text, MS, "2a", bumped)),
    ("2b", "number, markdown only", "manuscript.md Abstract: the identification-led count increased by 1", change(edit_text, MS, "2b", bumped)),
    ("2c", "number, markdown only", "highlights.md: the linkage count increased by 1", change(edit_text, cmn.HIGHLIGHTS, "2c", bumped)),
    ("2d", "number, markdown only", "manuscript.md Methods: the registration time changed", change(edit_text, MS, "2d", bumped)),
    ("2e", "number, markdown only", "manuscript.md Discussion: the benchmark multiplier changed", change(edit_text, MS, "2e", bumped)),
    ("3a", "title page, docx only", "02: the author's e-mail removed from the title-page block", swap(edit_docx, M02, "3a")),
    ("3b", "title page, markdown", "title_page_src.md: the corresponding-author line differs from the manuscript's",
     swap(edit_text, cmn.TITLE_PAGE, "3b")),
    ("3c", "title page, markdown", "manuscript.md: the ORCID removed from the title-page block", swap(edit_text, MS, "3c")),
    ("3d", "title page, markdown", "manuscript.md: the abbreviations footnote removed", swap(edit_text, MS, "3d")),
    ("4a", "reference number, markdown", "manuscript.md Introduction: a citation number increased by 1", change(edit_text, MS, "4a", bumped)),
    ("4b", "reference number, docx only", "02 Introduction: the same citation number increased by 1", change(edit_docx, M02, "4a", bumped)),
    ("4c", "reference number, docx only", "02 References: entries [2] and [3] renumbered [3] and [2]", renumber_refs),
    ("4d", "reference order, markdown", "manuscript.md Introduction: two first citations exchanged", swap(edit_text, MS, "4d")),
    ("5a", "table cell, docx only", "02 Table 1: the fixed-rule count changed", change(edit_docx, M02, "5a", bumped)),
    ("5b", "table cell, markdown only", "tables.md Table S7: an act-now unit moved to lower priority", swap(edit_text, TABLES_MD, "5b")),
    ("5c", "table cell, docx only", "08 Table S11: Gujarat's 2023 z changed", change(edit_docx, S08, "5c", bumped)),
    ("5d", "figure data, exhibits", "figure3_data.csv: an act-now unit set to lower priority",
     edit_csv("figure3_data.csv", ",act now", ",lower priority")),
    ("5e", "graphical-abstract data, exhibits", "graphical_abstract_data.csv: an act-now list changed",
     edit_csv("graphical_abstract_data.csv", "Bihar; Delhi", "Delhi")),
    ("6a", "label, markdown", "manuscript.md Results: H1 'supported' -> 'not established'", swap(edit_text, MS, "6a")),
    ("6b", "label, docx only", "02 Abstract: 'supported' -> 'not established'", swap(edit_docx, M02, "6b")),
    ("6c", "label, markdown", "manuscript.md Results: H1 called 'validated'", swap(edit_text, MS, "6c")),
    ("7a", "sign, markdown", "tables.md Table S11: Gujarat's negative z made positive", change(edit_text, TABLES_MD, "7a", flipped)),
    ("7b", "sign, docx only", "08 Table S11: Gujarat's negative z made positive", change(edit_docx, S08, "7a", flipped)),
    ("8a", "internal identifier, markdown", "manuscript.md Methods: '(Task 6)' inserted",
     insert(edit_text, MS, "8a", lambda d: " (Task 6)")),
    ("8b", "internal identifier, docx only", "08 supplement note: 'ITR2024' inserted",
     insert(edit_docx, S08, "8b", lambda d: "ITR2024 ", before=True)),
    ("8c", "wording, markdown", "manuscript.md Results: 'identified' written 'newly diagnosed'", swap(edit_text, MS, "8c")),
    ("8d", "wording, markdown", "manuscript.md Discussion: a causal claim inserted",
     insert(edit_text, MS, "8d", lambda d: " The programme caused these gaps.")),
    ("8e", "wording, docx only", "02 Results: ranking language inserted",
     insert(edit_docx, M02, "8e", lambda d: " Bihar ranked first.")),
    ("8f", "spelling, markdown", "manuscript.md Discussion: 'programme' written 'program'", swap(edit_text, MS, "8f")),
    ("8g", "wording, markdown", "manuscript.md Results: H3 called widespread", swap(edit_text, MS, "8g")),
    ("8h", "wording, markdown", "manuscript.md Results: 'identification-led' written 'detection-led'", swap(edit_text, MS, "8h")),
    ("8i", "wording, markdown", "manuscript.md Results: 'under-detection' without the k = 1 rule",
     insert(edit_text, MS, "8i", lambda d: " Bihar shows under-detection.")),
    ("9a", "highlight length, markdown", "highlights.md: a bullet made longer than 85 characters",
     insert(edit_text, cmn.HIGHLIGHTS, "9a", lambda d: " in every State and Union Territory")),
    ("9b", "highlight length, docx only", "03: a bullet made longer than 85 characters",
     insert(edit_docx, H03, "9a", lambda d: " in every State and Union Territory")),
    ("9c", "abstract limit, markdown", "manuscript.md Abstract: twelve words added",
     insert(edit_text, MS, "9c", lambda d: " This sentence adds exactly twelve more words to the abstract for this test.")),
    ("9d", "main-text limit, markdown", "manuscript.md Discussion: 700 words added", long_main),
    ("9e", "Word's counts", "word_counts_word.json: the abstract count set over 200", stale_counts),
    ("10a", "AI declaration, title page", "title_page_src.md: the AI declaration changed", swap(edit_text, cmn.TITLE_PAGE, "10a")),
    ("10b", "caveat, markdown", "manuscript.md Results: the H3 caveat removed", swap(edit_text, MS, "10b")),
    ("10c", "caveat, markdown", "manuscript.md Methods: the registry caveat removed", swap(edit_text, MS, "10c")),
    ("10d", "declaration, markdown", "manuscript.md: 'Declarations of interest: none' removed", swap(edit_text, MS, "10d")),
    ("11a", "figure, PDF", "04_Figure_1.pdf replaced by Figure 2", other_figure),
    ("11b", "figure, TIFF", "04_Figure_1.tif replaced by a 300 dpi image", low_dpi_tiff),
    ("11c", "graphical abstract, TIFF", "11_graphical_abstract.tif replaced by a 1200 x 480 image", small_ga),
    ("11d", "display items, docx only", "02: Table 1 duplicated (six display items)", second_table),
    ("12a", "file set", "an extra file in submission/", extra_file),
    ("12b", "file set", "09_cover_letter.docx removed", drop_file),
    ("12c", "cover letter, markdown", "cover_letter.md: a related manuscript removed", swap(edit_text, cmn.COVER, "12c")),
    ("13a", "builder text, docx only", "08: the supplement's note changed", swap(edit_docx, S08, "13a")),
]


# --------------------------------------------------------------------------------------
# The IJTLD set (manuscript/v2)
# --------------------------------------------------------------------------------------
I_COVER, I_MS, I_DECL = (S + n for n in ("01_cover_letter.docx", "02_manuscript.docx", "03_declarations.docx"))
I_FIG1, I_FIG2 = S + "Figure_1.tif", S + "Figure_2.tif"
TP = cmn.TITLE_PAGE


def both(mid: str) -> Callable[[Path], None]:
    """The anchor pair [old, new] replaced in manuscript.md and in title_page_src.md (the title)."""
    def fn(d: Path) -> None:
        a = anchor(d, mid)
        edit_text(d / MS, a[0], a[1])
        edit_text(d / TP, a[0], a[1])
    return fn


def ijtld_long_main(d: Path) -> None:
    a = anchor(d, "i12")
    edit_text(d / MS, a, a + " " + " ".join(["filler"] * 150))


def ijtld_many_refs(d: Path) -> None:
    """Four more references (33-36), cited in the Discussion: more than 35."""
    a = anchor(d, "i19")
    edit_text(d / MS, a, a + "^33–36^")
    extra = "".join(f"\n\n{k}\\. Author A. A title. J Test 2020; {k}: 1–2." for k in range(33, 37))
    s = (d / MS).read_text(encoding="utf-8")
    i = s.index("\n\n## Figure legends")
    replace_bytes(d / MS, (s[:i] + extra + s[i:]).encode("utf-8"))


def ijtld_low_dpi(d: Path) -> None:
    try:
        from PIL import Image
    except ImportError:
        raise NotApplied("Pillow not installed") from None
    p = d / I_FIG1
    p.unlink()
    Image.new("L", (100, 100), 255).save(p, format="TIFF", dpi=(300, 300))


def ijtld_other_tiff(d: Path) -> None:
    replace_bytes(d / I_FIG1, (d / I_FIG2).read_bytes())


def ijtld_extra_file(d: Path) -> None:
    (d / S / "tableS1.csv").write_text("online material in the upload folder", encoding="utf-8")


def ijtld_drop_cover(d: Path) -> None:
    (d / I_COVER).unlink()


def ijtld_stale_counts(d: Path) -> None:
    p = d / "word_counts_word.json"
    w = json.loads(p.read_text(encoding="utf-8"))
    w["abstract"] = 201
    replace_bytes(p, (json.dumps(w, indent=1) + "\n").encode("utf-8"))


def ijtld_no_line_numbers(d: Path) -> None:
    rewrite_part(d / I_MS, DOC, lambda x: re.sub(r"<w:lnNumType [^>]*/>", "", x))


def ijtld_justified(d: Path) -> None:
    def fn(x: str) -> str:
        if '<w:jc w:val="left"/>' not in x:
            raise NotApplied("styles.xml has no left alignment")
        return x.replace('<w:jc w:val="left"/>', '<w:jc w:val="both"/>', 1)
    rewrite_part(d / I_MS, "word/styles.xml", fn)


def ijtld_single_spaced(d: Path) -> None:
    def fn(x: str) -> str:
        m = re.search(r'(<w:style [^>]*w:styleId="Normal"[^>]*>.*?w:line=")480(")', x, re.S)
        if not m:
            raise NotApplied("Normal style has no double spacing")
        return x[:m.start()] + m.group(1) + "240" + m.group(2) + x[m.end():]
    rewrite_part(d / I_MS, "word/styles.xml", fn)


def ijtld_other_image(d: Path) -> None:
    """02: the embedded Figure 1 replaced by other image bytes."""
    p = d / I_MS
    with zipfile.ZipFile(p) as z:
        media = sorted(n for n in z.namelist() if n.startswith("word/media/"))
    if not media:
        raise NotApplied("02 embeds no image")
    from io import BytesIO
    try:
        from PIL import Image
    except ImportError:
        raise NotApplied("Pillow not installed") from None
    buf = BytesIO()
    Image.new("L", (50, 50), 0).save(buf, format="PNG")
    tmp = p.with_name(p.name + ".mut")
    with zipfile.ZipFile(p) as zi, zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as zo:
        for item in zi.infolist():
            zo.writestr(item, buf.getvalue() if item.filename == media[0] else zi.read(item.filename))
    p.unlink()
    tmp.replace(p)


def ijtld_six_keywords(d: Path) -> None:
    a = anchor(d, "i15")
    edit_text(d / TP, a, a + "; surveillance")


def ijtld_figure_data(d: Path) -> None:
    p = d / "exhibits" / "figure2_data.csv"
    s = p.read_text(encoding="utf-8")
    if ",screening-led," not in s:
        raise NotApplied("figure2_data.csv has no screening-led row")
    replace_bytes(p, s.replace(",screening-led,", ",mixed,", 1).encode("utf-8"))


MUTATIONS_IJTLD: list[Mutation] = [
    ("i1a", "number, docx only", "02 Results: the H1 value changed in its last digit", change(edit_docx, I_MS, "i1", bumped)),
    ("i2a", "number, markdown only", "manuscript.md Abstract: the identification-led count increased by 1", change(edit_text, MS, "i2", bumped)),
    ("i3a", "number, markdown only", "manuscript.md Results: the number identified in 2023 changed", change(edit_text, MS, "i3", bumped)),
    ("i4a", "table cell, docx only", "02 Table 1: Bihar's identification ratio changed", change(edit_docx, I_MS, "i4", bumped)),
    ("i5a", "table cell, markdown only", "tables.md Table 1: a largest-gap flag removed", swap(edit_text, TABLES_MD, "i5")),
    ("i5b", "figure data, exhibits", "figure2_data.csv: a screening-led unit set to mixed", ijtld_figure_data),
    ("i6a", "citation order, markdown", "manuscript.md Introduction: a superscript citation changed", swap(edit_text, MS, "i6")),
    ("i7a", "reference number, docx only", "02 References: entry 2 renumbered 3", swap(edit_docx, I_MS, "i7")),
    ("i8a", "title limit", "title over 110 characters (manuscript and title page)", both("i8")),
    ("i9a", "title abbreviation", "title with the abbreviation TB (manuscript and title page)", both("i9")),
    ("i10a", "abstract abbreviation", "manuscript.md Abstract: 'tuberculosis' written 'TB'", swap(edit_text, MS, "i10")),
    ("i11a", "abstract limit", "manuscript.md Abstract: twelve words added",
     insert(edit_text, MS, "i11", lambda d: " This sentence adds exactly twelve more words to the abstract for this test.")),
    ("i12a", "main-text limit", "manuscript.md Discussion: 150 words added (over 2500)", ijtld_long_main),
    ("i13a", "running head limit", "title_page_src.md: running head over 45 characters", swap(edit_text, TP, "i13")),
    ("i14a", "keyword in the title", "title_page_src.md: a keyword that repeats the title", swap(edit_text, TP, "i14")),
    ("i15a", "keyword count", "title_page_src.md: six keywords", ijtld_six_keywords),
    ("i16a", "pre-registered", "manuscript.md Methods: 'pre-registered' inserted", swap(edit_text, MS, "i16")),
    ("i17a", "stigmatising term, markdown", "manuscript.md Results: 'TB patients' inserted", swap(edit_text, MS, "i17")),
    ("i18a", "stigmatising term, docx only", "02 Discussion: 'defaulters' inserted",
     insert(edit_docx, I_MS, "i18", lambda d: " Defaulters were excluded.")),
    ("i19a", "reference limit", "manuscript.md: 36 references", ijtld_many_refs),
    ("i20a", "display items, docx only", "02: Table 1 duplicated (four display items)", second_table),
    ("i21a", "display items, markdown", "manuscript.md Results: a Figure 3 cited", swap(edit_text, MS, "i21")),
    ("i22a", "figure, TIFF", "Figure_1.tif replaced by a 300 dpi image", ijtld_low_dpi),
    ("i23a", "figure, TIFF", "Figure_1.tif replaced by Figure 2", ijtld_other_tiff),
    ("i24a", "file set", "online material (tableS1.csv) put in the upload folder", ijtld_extra_file),
    ("i25a", "file set", "01_cover_letter.docx removed", ijtld_drop_cover),
    ("i26a", "cover letter", "cover_letter.md: a related manuscript removed", swap(edit_text, cmn.COVER, "i26")),
    ("i27a", "cover letter", "cover_letter.md: the earlier journal named", swap(edit_text, cmn.COVER, "i27")),
    ("i28a", "Word's counts", "word_counts_word.json: the abstract count set to 201", ijtld_stale_counts),
    ("i29a", "Word's counts, docx only", "02 title page: the quoted abstract count changed", change(edit_docx, I_MS, "i29", bumped)),
    ("i30a", "layout, docx only", "02: line numbers removed", ijtld_no_line_numbers),
    ("i31a", "layout, docx only", "02: text justified", ijtld_justified),
    ("i32a", "layout, docx only", "02: body text single spaced", ijtld_single_spaced),
    ("i33a", "figure, docx only", "02: the embedded Figure 1 replaced", ijtld_other_image),
    ("i34a", "caveat, markdown", "manuscript.md Results: the built-in split caveat removed", swap(edit_text, MS, "i34")),
    ("i35a", "label, markdown", "manuscript.md Results: H1 'supported' -> 'not established'", swap(edit_text, MS, "i35")),
    ("i36a", "online material", "manuscript.md: a Table S16 cited (it does not exist)", swap(edit_text, MS, "i36")),
    ("i37a", "online material", "manuscript.md: the online-material link changed", swap(edit_text, MS, "i37")),
    ("i38a", "citation style", "manuscript.md: a bracketed citation [3]", swap(edit_text, MS, "i38")),
    ("i39a", "reference style", "manuscript.md: four authors listed before the title", swap(edit_text, MS, "i39")),
    ("i40a", "wording", "manuscript.md Discussion: a causal claim inserted",
     insert(edit_text, MS, "i40", lambda d: " The programme caused these gaps.")),
    ("i41a", "spelling", "manuscript.md Discussion: 'programme' written 'program'", swap(edit_text, MS, "i41")),
    ("i42a", "process word", "title_page_src.md: a drafting-process word", swap(edit_text, TP, "i42")),
    ("i43a", "declarations, docx only", "03: the funding statement changed", swap(edit_docx, I_DECL, "i43")),
    ("i44a", "online citation order", "manuscript.md Methods: the first online citation changed from Table S1 to S2",
     swap(edit_text, MS, "i44")),
    ("i45a", "online citation missing", "manuscript.md Results: the only citation of Table S4 removed", swap(edit_text, MS, "i45")),
]


# --------------------------------------------------------------------------------------
# Running the checks on a copy
# --------------------------------------------------------------------------------------
def copy_manuscript(src: Path, dst: Path) -> Path:
    """A copy of the folder, without the render output, the PNG previews and the mutation work
    folder; the large binary files of submission/ are hard-linked."""
    def ignore(d: str, names: list[str]) -> set[str]:
        return {n for n in names if n in ("_render", "_render_qa", "__pycache__", WORK) or n.endswith(".png")}

    def copy_fn(s: str, t: str) -> None:
        if s.endswith(LINKED) and "submission" in Path(s).parts:
            try:
                os.link(s, t)
                return
            except OSError:
                pass
        shutil.copy2(s, t)
    shutil.copytree(src, dst, ignore=ignore, copy_function=copy_fn)
    return dst


def cmn_problems(ms_dir: Path) -> list[str]:
    if not (ms_dir / cmn.PHRASES).exists():
        return [f"PHRASES: {cmn.PHRASES} missing"]
    return cmn.problems(ROOT, ms_dir)


def tie_problems(ms_dir: Path) -> list[str]:
    return tie.problems(ms_dir, ROOT)


def run_named(src: Path, mutations: list[Mutation] | None = None) -> list[dict]:
    mutations = MUTATIONS if mutations is None else mutations
    checks = {"check_manuscript_numbers": cmn_problems, "check_docx_tie": tie_problems}
    rows = []
    work = src / WORK
    shutil.rmtree(work, ignore_errors=True)
    work.mkdir()
    try:
        base = copy_manuscript(src, work / "base")
        for name, fn in checks.items():
            found = fn(base)
            if found:
                raise SystemExit(f"the unmutated copy fails {name}; fix that first:\n" + "\n".join(found[:5]))
        shutil.rmtree(base, ignore_errors=True)
        for mid, kind, what, fn in mutations:
            d = copy_manuscript(src, work / f"m{mid}")
            row = {"id": mid, "kind": kind, "what": what, "applied": True, "by": [], "first": ""}
            try:
                fn(d)
            except NotApplied as e:
                row.update(applied=False, first=str(e))
                rows.append(row)
                shutil.rmtree(d, ignore_errors=True)
                continue
            for name, check in checks.items():
                try:
                    found = check(d)
                except Exception as e:  # a check that crashes on the mutated copy has caught it
                    found = [f"{name} raised {type(e).__name__}: {e}"]
                if found:
                    row["by"].append(name)
                    row["first"] = row["first"] or found[0].splitlines()[0]
            rows.append(row)
            shutil.rmtree(d, ignore_errors=True)
    finally:
        shutil.rmtree(work, ignore_errors=True)
    return rows


# --------------------------------------------------------------------------------------
# Sweeps over every number token
# --------------------------------------------------------------------------------------
def md_token_spans(text: str) -> list[tuple[int, int]]:
    """Number tokens of the checked sections (the title, the '## ' sections but the References);
    the title-page block between the title and the Abstract is checked by the title-page tie."""
    spans, pos, state = [], 0, None
    for line in text.splitlines(keepends=True):
        take = False
        if state is None and line.startswith("# "):
            take, state = True, "front"
        elif line.startswith("## "):
            state = "refs" if line.strip() == "## References" else "body"
        elif state == "body":
            take = True
        if take:
            spans += [(pos + m.start(), pos + m.end()) for m in NUMBER.finditer(line)]
        pos += len(line)
    return spans


def sweep_md(ms: Path) -> tuple[int, int, list[str]]:
    text = (ms / cmn.MS_NAME).read_text(encoding="utf-8")
    gold, required = cmn.load_gold(ms), cmn.section_phrases(ms)
    hl = cmn.read_opt(ms, cmn.HIGHLIGHTS)
    caught, escaped = 0, []
    spans = md_token_spans(text)
    for a, b in spans:
        mutated = text[:a] + bump(text[a:b]) + text[b:]
        if cmn.problems(ROOT, ms, mutated, gold, required, hl, exhibits=False):
            caught += 1
        else:
            escaped.append(f"...{text[max(0, a - 30):b + 10]}...".replace("\n", " "))
    return caught, len(spans), escaped


def sweep_docx(path: Path, want: list[str]) -> tuple[int, int, list[str]]:
    with zipfile.ZipFile(path) as z:
        xml = z.read(DOC).decode("utf-8")
    spans = []
    for m in re.finditer(r"<w:t(?: [^>]*)?>([^<]*)</w:t>", xml):
        spans += [(m.start(1) + t.start(), m.start(1) + t.end()) for t in NUMBER.finditer(m.group(1))]
    caught, escaped = 0, []
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td) / path.name
        for a, b in spans:
            shutil.copyfile(path, tmp)
            rewrite_part(tmp, DOC, lambda _x, a=a, b=b: xml[:a] + bump(xml[a:b]) + xml[b:])
            if tie.compare(path.name, tie.docx_units(tmp), want):
                caught += 1
            else:
                escaped.append(xml[max(0, a - 40):b + 10])
    return caught, len(spans), escaped


def main(argv: list[str] | None = None, root: Path = ROOT) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ms, rest = cmn.manuscript_dir(root, argv)
    unknown = [a for a in rest if a != "--sweep"]
    if unknown:
        print(f"FAIL: unknown arguments {unknown}")
        return 1
    name = cmn.rel(ms, root)
    if not ms.is_dir() or not (ms / "submission").is_dir():
        print(f"SKIPPED: {name}/ or {name}/submission/ not present (kept private, not in this repository)")
        return 0
    ijtld_set = cmn.journal_of(ms) == "ijtld"
    rows = run_named(ms, MUTATIONS_IJTLD if ijtld_set else None)
    bad = 0
    print("| # | Kind | Mutation | Caught by | First problem reported |")
    print("|---|------|----------|-----------|------------------------|")
    for r in rows:
        res = "NOT APPLIED" if not r["applied"] else (" and ".join(r["by"]) if r["by"] else "NOT CAUGHT")
        bad += res in ("NOT APPLIED", "NOT CAUGHT")
        print(f"| {r['id']} | {r['kind']} | {r['what']} | {res} | {r['first'].replace('|', '/')[:110]} |")
    print(f"named mutations: {len(rows) - bad} of {len(rows)} caught")
    if "--sweep" in rest:
        c, t, e = sweep_md(ms)
        print(f"sweep, manuscript.md number tokens (check_manuscript_numbers): caught {c} of {t}")
        for x in e:
            print("  UNCAUGHT", x)
        p = ms / M02
        if ijtld_set:
            p = ms / I_MS
        c2, t2, e2 = sweep_docx(p, tie.expected(ms, p.name, tie.spec_ijtld() if ijtld_set else None))
        print(f"sweep, {p.name} number tokens (check_docx_tie): caught {c2} of {t2}")
        for x in e2:
            print("  UNCAUGHT", x)
        bad += len(e) + len(e2)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
