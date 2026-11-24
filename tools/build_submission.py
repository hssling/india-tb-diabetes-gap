# Adapted from hssling/india-tb-priority-tool v1.0.1 (MIT), tools/build_submission.py (itself adapted
# from hssling/india-tb-acf-campaign and hssling/india-state-tb-score); modified: the Primary Care
# Diabetes (Elsevier) set of this paper. The journal's review is single anonymized, so there is no
# anonymised file: the manuscript carries its title page, and a separate title page, the highlights,
# the four figures, the supplement, the cover letter, the declaration of interest and the optional
# graphical abstract complete the set; --doi fills the Zenodo DOI everywhere; the build refuses to
# write into a submitted (SUBMITTED_*) folder and rejects unknown options. Added: --profile ijtld,
# the International Journal of Tuberculosis and Lung Disease set of manuscript/v2, and --profile
# dmscrr, the Diabetes & Metabolic Syndrome: Clinical Research & Reviews set of manuscript/v3 (see below).
"""Build the submission set into <manuscript folder>/submission/.

Run as: python -I tools/build_submission.py [--manuscript-dir DIR] [--profile pcd|ijtld|dmscrr]
                                            [--doi 10.5281/zenodo.NNNNNNN] [--no-word]

--profile pcd (the default) builds the Primary Care Diabetes set described below. --profile ijtld
builds the IJTLD set of an IJTLD folder (its section_phrases.json says "journal": "ijtld"; the
profile must match the folder) into <folder>/submission/:

  01_cover_letter.docx    the cover letter to the Editors-in-Chief
  02_manuscript.docx      ONE file: the title page (title_page_src.md), the abstract, the text
                          (the Introduction without a heading), the references, Table 1, then
                          Figures 1 and 2 embedded, each with its legend; double spacing,
                          continuous line numbers, left-aligned; headings in Arial
  03_declarations.docx    the title page's declarations, for the submission portal
  Figure_1.tif, Figure_2.tif   the figures (LZW, 600 dpi) rendered from exhibits/figureN.pdf

and records in <folder>/build_record.json the SHA-256 of each figure PDF, TIFF and embedded image,
which verification/check_docx_tie.py checks. Exhibits come from exhibits/make_ijtld.py.

--profile dmscrr builds the Diabetes & Metabolic Syndrome: Clinical Research & Reviews set of a
DMSCRR folder ("journal": "dmscrr", manuscript/v3) into <folder>/submission/, numbered in upload
order (the PCD path, single anonymized; file names in verification/dmscrr.py):

  01_title_page.docx            title page; Word's counts fill its [[...]] placeholders
  02_manuscript.docx            title-page block, structured abstract and keywords, text,
                                declarations, generative-AI section, Acknowledgements, references,
                                Table 1 and the figure legends; line numbers
  03_highlights.docx            the journal's highlights structure
  04_Figure_1.tif/.pdf ... 06_Figure_3.tif/.pdf   colour TIFF (LZW, 1000 dpi, line art) and the PDF
  07_supplementary_material.docx   Tables S1-S14 and Figure S1 (embedded), landscape
  08_cover_letter.docx          the cover letter; Word's counts fill its placeholders
  09_declaration_of_interest.docx  the prefilled declaration of competing interests

02 is built first and counted in Word (abstract; main text with subsection headings; Table 1 cells,
title and notes; figure legends: the journal's 5,000-word basis); the counts go to
<folder>/word_counts_word.json and fill the title page and the cover letter. Exhibits come from
exhibits/make_dmscrr.py; <folder>/build_record.json records the figure and embedded-image hashes.

The manuscript folder is DIR (default manuscript/; git-ignored and private); a relative DIR is taken
from the repository root. Unknown options are rejected (argparse, no abbreviations). The build
refuses to write when the folder or its submission/ holds a SUBMITTED_* file: a submitted set is
frozen, and changes after submission go into a new folder.

Needs pandoc on PATH, python-docx, Pillow and PyMuPDF (fitz); Microsoft Word (through PowerShell
COM) for the word counts unless --no-word. Sources (in the folder): manuscript.md (with its title-
page block), title_page_src.md, highlights.md, cover_letter.md and exhibits/ (tables.md, figure1.pdf
to figure4.pdf and graphical_abstract.pdf, from the committed exhibits/ scripts). Nothing is written
outside the folder.

Layout (manuscript/journal_rules.md; Elsevier): A4, 2.5 cm margins, Times New Roman 12 pt, double
spacing, page numbers at the foot, continuous line numbers in the manuscript, single column, no
justification. Tables are editable, with only the top, header and bottom rules (no vertical rules,
no shading).

  01_title_page.docx                   title page (author details, declarations, Word's counts)
  02_manuscript.docx                   title-page block, abstract, text, declarations, references,
                                       Table 1 and the figure captions
  03_highlights.docx                   3-5 bullets of at most 85 characters
  04_Figure_1.tif / 04_Figure_1.pdf    Figure 1: TIFF (LZW, 1000 dpi) rendered from the vector PDF, and the PDF
  05_Figure_2 ... 07_Figure_4          Figures 2 to 4, likewise
  08_supplementary_material.docx       Tables S1 to S13, landscape
  09_cover_letter.docx
  10_declaration_of_interest.docx      the summary declaration of interest (the journal's own form is
                                       completed in the submission system)
  11_graphical_abstract.tif / .pdf     optional graphical abstract (300 dpi, at least 1328 x 531 pixels)

--doi replaces the placeholder 10.5281/zenodo.XXXXXXX in every file; without it the placeholder is
highlighted in yellow. Word's own counts of 02 go to <folder>/word_counts_word.json
(tools/word_count_word.ps1); the title page must quote them (verification/check_docx_tie.py checks
it, and ties every .docx to its source).
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

from docx import Document
from docx.enum.section import WD_ORIENT
from docx.enum.style import WD_STYLE_TYPE
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_COLOR_INDEX
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt
from docx.text.run import Run

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from verification.check_docx_tie import DOI_STATEMENT, SUPP_NOTE  # noqa: E402  (the builder's own paragraphs)

DEFAULT_MS_DIR = "manuscript"
MS = ROOT / DEFAULT_MS_DIR
EX = MS / "exhibits"
OUT = MS / "submission"

FONT = "Times New Roman"
DOI_PLACEHOLDER = "10.5281/zenodo.XXXXXXX"
DOI_RE = re.compile(r"^10\.5281/zenodo\.\d+$")
TIFF_DPI = 1000  # Elsevier: line art at least 1000 dpi
GA_DPI = 300     # the graphical abstract: 13.28 x 5.31 in at 300 dpi = 3984 x 1593 pixels
N_FIGURES = 4
FIG_PREFIX = ("04", "05", "06", "07")
SUPPLEMENT = "08_supplementary_material.docx"
GA = ("11_graphical_abstract.tif", "11_graphical_abstract.pdf")
SUBMITTED = re.compile(r"^SUBMITTED_")
PAGEBREAK = '\n\n```{=openxml}\n<w:p><w:r><w:br w:type="page"/></w:r></w:p>\n```\n\n'
PANDOC_FROM = ("markdown+pipe_tables+superscript+fenced_divs+raw_attribute-smart-subscript-citations"
               "-tex_math_dollars-raw_html-auto_identifiers-implicit_figures-link_attributes")


PROFILES = ("pcd", "ijtld", "dmscrr")


def folder_journal(ms_dir: Path) -> str | None:
    """The journal a manuscript folder declares in section_phrases.json ("pcd" when it names none)."""
    p = ms_dir / "section_phrases.json"
    if not p.exists():
        return None
    return json.loads(p.read_text(encoding="utf-8")).get("journal", "pcd")


def configure(ms_dir: Path) -> None:
    global MS, EX, OUT
    MS, EX, OUT = ms_dir, ms_dir / "exhibits", ms_dir / "submission"


def figure_names(k: int) -> tuple[str, str]:
    """Figure k (1-based) as 04_Figure_1.tif and 04_Figure_1.pdf."""
    return f"{FIG_PREFIX[k - 1]}_Figure_{k}.tif", f"{FIG_PREFIX[k - 1]}_Figure_{k}.pdf"


def submitted_markers(ms_dir: Path) -> list[Path]:
    """SUBMITTED_* files in the folder or its submission/ (a frozen, submitted set)."""
    out = []
    for d in (ms_dir, ms_dir / "submission"):
        if d.is_dir():
            out += [p for p in d.iterdir() if p.is_file() and SUBMITTED.match(p.name)]
    return out


# --------------------------------------------------------------------------------------
# Markdown preparation (the sources are never written)
# --------------------------------------------------------------------------------------
def read(rel: str) -> str:
    return (MS / rel).read_text(encoding="utf-8")


def between(text: str, start: str, end: str | None) -> str:
    i = text.index("\n" + start) + 1 if not text.startswith(start) else 0
    j = text.index("\n" + end, i) + 1 if end else len(text)
    return text[i:j]


def escape_refs(md: str) -> str:
    """Reference list entries '[n] ...' kept as literal text (each its own paragraph)."""
    return re.sub(r"(?m)^\[(\d+)\] ", r"\\[\1\\] ", md)


def escape_dataset(md: str) -> str:
    return md.replace("[dataset]", "\\[dataset\\]").replace("[software]", "\\[software\\]")


def table_block(md: str) -> str:
    """One '## Table N. Title' section of tables.md as pandoc Markdown: the title as a 'Table Title'
    paragraph ('Table N.' bold), the table, and the notes below as 'Table Note' paragraphs."""
    lines = md.strip("\n").splitlines()
    m = re.match(r"## (Table S?\d+\.) (.*)", lines[0])
    if not m:
        raise SystemExit(f"not a table heading: {lines[0]!r}")
    out = ['::: {custom-style="Table Title"}', f"**{m.group(1)}** {m.group(2)}", ":::", ""]
    para: list[str] = []
    for ln in lines[1:] + [""]:
        if ln.startswith("|"):
            out.append(ln)
            continue
        if ln.strip():
            para.append(ln)
            continue
        if para:
            out += ["", '::: {custom-style="Table Note"}', " ".join(para), ":::", ""]
            para = []
        elif out[-1] != "":
            out.append("")
    return "\n".join(out) + "\n"


def tables(names_from: str, names_to: str | None) -> list[str]:
    part = between(read("exhibits/tables.md"), names_from, names_to)
    return [table_block(b) for b in re.split(r"(?m)^(?=## )", part) if b.startswith("## Table ")]


def manuscript_md() -> str:
    """The title-page block and the abstract on the first pages, then the text, the references,
    Table 1 and the figure captions, each starting a new page."""
    ms = read("manuscript.md")
    front = between(ms, "# ", "## Abstract")
    body = between(ms, "## Abstract", "## References")
    refs = between(ms, "## References", "## Figure captions")
    caps = between(ms, "## Figure captions", None)
    parts = [front.rstrip(), PAGEBREAK, body.rstrip(), PAGEBREAK, escape_dataset(escape_refs(refs)).rstrip()]
    for t in tables("## Table 1.", "## Table S1."):
        parts += [PAGEBREAK, t]
    parts += [PAGEBREAK, caps]
    return "".join(parts)


def title_page_md() -> str:
    tp = read("title_page_src.md")
    if tp.count(DOI_PLACEHOLDER) < 1:
        raise SystemExit(f"title_page_src.md must hold the DOI placeholder {DOI_PLACEHOLDER}")
    return tp


def supplement_md() -> str:
    title = read("manuscript.md").splitlines()[0]
    if not title.startswith("# "):
        raise SystemExit("manuscript.md must start with its '# ' title")
    parts = ["# Supplementary material\n\n", title[2:].strip(), "\n\n", SUPP_NOTE, "\n"]
    for t in tables("## Table S1.", None):
        parts += [PAGEBREAK, t]
    return "".join(parts)


def letter_md(name: str) -> str:
    """A letter without its '# ' heading; the lines of an address block kept apart by hard breaks."""
    lines = read(name).splitlines()
    if not lines[0].startswith("# "):
        raise SystemExit(f"{name} must start with a '# ' heading")
    blocks = re.split(r"\n\s*\n", "\n".join(lines[1:]).strip())
    out = []
    for b in blocks:
        bl = b.splitlines()
        if len(bl) > 1 and not any(ln.lstrip().startswith(("-", "|")) for ln in bl):
            b = "\\\n".join(bl)
        out.append(b)
    return "\n\n".join(out) + "\n"


def declaration_md() -> str:
    """The declaration of interest: the title, the author and the title page's summary statement,
    word for word, then the standard Elsevier wording for no competing interests."""
    tp = title_page_md()
    keep = []
    for key in ("**Title:**", "**Author:**", "**Declarations of interest:**"):
        hit = [ln for ln in tp.splitlines() if ln.startswith(key)]
        if len(hit) != 1:
            raise SystemExit(f"title_page_src.md: expected one line starting {key}")
        keep.append(hit[0])
    return "# Declaration of interest\n\n" + "\n\n".join(keep) + "\n\n" + DOI_STATEMENT + "\n"


# --------------------------------------------------------------------------------------
# The IJTLD set (manuscript/v2)
# --------------------------------------------------------------------------------------
FIG_WIDTH_CM = 16.5
EMBED_DPI = 300


def ijtld_legends() -> list[str]:
    """The figure legends: the paragraphs under '## Figure legends'."""
    caps = between(read("manuscript.md"), "## Figure legends", None).split("\n", 1)[1]
    return [b.strip() for b in re.split(r"\n\s*\n", caps) if b.strip()]


def ijtld_manuscript_md(images: dict[int, Path]) -> str:
    """Title page; abstract; the text from the Introduction (its heading dropped: the journal's
    Introduction has none) to the Discussion; references; Table 1; each figure with its legend."""
    from verification.check_docx_tie import drop_introduction_heading
    tp = title_page_md()
    ms = read("manuscript.md")
    abstract = between(ms, "## Abstract", "## Introduction")
    body = drop_introduction_heading(between(ms, "## Introduction", "## References"))
    refs = between(ms, "## References", "## Figure legends")
    parts = [tp.rstrip(), PAGEBREAK, abstract.rstrip(), PAGEBREAK, body.rstrip(), PAGEBREAK,
             escape_dataset(refs).rstrip()]
    for t in tables("## Table 1.", None):
        parts += [PAGEBREAK, t]
    legends = ijtld_legends()
    if len(legends) != len(images):
        raise SystemExit(f"{len(legends)} figure legends for {len(images)} figures")
    for (k, png), leg in zip(sorted(images.items()), legends):
        if not leg.startswith(f"**Figure {k}.**"):
            raise SystemExit(f"legend {k} does not start with **Figure {k}.**")
        parts += [PAGEBREAK, f"![]({png.as_posix()}){{width={FIG_WIDTH_CM}cm}}\n\n", leg, "\n"]
    return "".join(parts)


def ijtld_declarations_md() -> str:
    tp = title_page_md()
    keep = []
    for key in ("Title", "Author", "Funding", "Conflicts of interest", "Ethics", "Data availability",
                "Use of artificial intelligence", "Author contribution"):
        hit = [ln for ln in tp.splitlines() if ln.startswith(f"**{key}:**")]
        if len(hit) != 1:
            raise SystemExit(f"title_page_src.md: expected one line starting **{key}:**")
        keep.append(hit[0])
    return "# Declarations\n\n" + "\n\n".join(keep) + "\n"


def ijtld_reference_styles(path: Path) -> None:
    """IJTLD headings: Arial 12 bold; the major (level-2) headings in capitals."""
    doc = Document(str(path))
    for name in ("Heading 1", "Heading 2", "Heading 3", "Title"):
        st = doc.styles[name]
        st.font.name = "Arial"
        rpr = st.element.get_or_add_rPr()
        rf = rpr.find(qn("w:rFonts"))
        for a in ("w:ascii", "w:hAnsi", "w:cs", "w:eastAsia"):
            rf.set(qn(a), "Arial")
        st.font.size = Pt(12)
    doc.styles["Heading 2"].font.all_caps = True
    doc.styles["Heading 3"].font.bold = False
    doc.styles["Heading 3"].font.italic = True
    doc.save(str(path))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def render_png(pdf: Path, png: Path, dpi: int) -> None:
    import fitz  # PyMuPDF
    page = fitz.open(str(pdf))[0]
    page.get_pixmap(dpi=dpi, alpha=False, colorspace=fitz.csGRAY).save(str(png))


def ijtld_build(doi: str | None, no_word: bool) -> int:
    from verification import ijtld
    hl = not doi
    record: dict = {"figures": {}}
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        ref = tmp / "reference.docx"
        make_reference(ref)
        ijtld_reference_styles(ref)
        images = {}
        for k, tif_name in ijtld.FIGURE_FILES.items():
            pdf = EX / f"figure{k}.pdf"
            tif = OUT / tif_name
            print(render_tiff(pdf, tif, ijtld.TIFF_DPI, gray=True))
            png = tmp / f"figure{k}_embed.png"
            render_png(pdf, png, EMBED_DPI)
            images[k] = png
            record["figures"][str(k)] = {"pdf": f"exhibits/figure{k}.pdf", "pdf_sha256": sha256(pdf),
                                         "tif": tif_name, "tif_sha256": sha256(tif), "embedded_sha256": sha256(png)}
        jobs = [
            (ijtld.COVER, letter_md("cover_letter.md"), {}),
            (ijtld.MANUSCRIPT, ijtld_manuscript_md(images), dict(line_numbers=True, placeholder=hl, bold_header=False)),
            (ijtld.DECLARATIONS, ijtld_declarations_md(), dict(placeholder=hl)),
        ]
        for name, md, kw in jobs:
            out = OUT / name
            run_pandoc(with_doi(md, doi), out, ref, tmp, links=True)
            postprocess(out, **kw)
            print("built", name)
    names = {ijtld.COVER, ijtld.MANUSCRIPT, ijtld.DECLARATIONS} | set(ijtld.FIGURE_FILES.values())
    record["files"] = {n: sha256(OUT / n) for n in sorted(names)}
    (MS / ijtld.BUILD_RECORD).write_text(json.dumps(record, indent=1) + "\n", encoding="utf-8", newline="\n")
    for f in sorted(OUT.iterdir()):
        if f.is_file() and f.name not in names and not SUBMITTED.match(f.name):
            print(f"note: {f.name} is not part of this set (left from an earlier build?); remove it")
    if not no_word:
        w = word_counts(OUT / ijtld.MANUSCRIPT)
        print(f"Word counts: abstract {w['abstract']}, main text {w['main_text']} (with subsection headings "
              f"{w['main_with_headings']}) (limits {ijtld.LIMITS['abstract']} and {ijtld.LIMITS['main']})")
    print("built into", OUT)
    return 0


# --------------------------------------------------------------------------------------
# The DMSCRR set (manuscript/v3; verification/dmscrr.py holds the file names and rules)
# --------------------------------------------------------------------------------------
def dmscrr_manuscript_md() -> str:
    """The title-page block, then the abstract and text to the end of the declarations, the
    references, Table 1 and the figure legends, each starting a new page."""
    ms = read("manuscript.md")
    front = between(ms, "# ", "## Abstract")
    body = between(ms, "## Abstract", "## References")
    refs = between(ms, "## References", "## Figure legends")
    legends = between(ms, "## Figure legends", None)
    parts = [front.rstrip(), PAGEBREAK, body.rstrip(), PAGEBREAK, escape_dataset(refs).rstrip()]
    for t in tables("## Table 1.", None):
        parts += [PAGEBREAK, t]
    parts += [PAGEBREAK, legends]
    return "".join(parts)


def dmscrr_supplement_md(png: Path) -> str:
    """Supplementary material: the title, the builder's note, Tables S1-S14 and Figure S1 (the
    image, then its legend)."""
    from verification import dmscrr
    title = read("manuscript.md").splitlines()[0]
    if not title.startswith("# "):
        raise SystemExit("manuscript.md must start with its '# ' title")
    md = read("exhibits/supplement.md")
    parts = ["# Supplementary material\n\n", title[2:].strip(), "\n\n", dmscrr.SUPP_NOTE, "\n\n",
             between(md, "## Notation", "## Table S1.").rstrip(), "\n"]
    part = between(md, "## Table S1.", "## Figure S1")
    for b in re.split(r"(?m)^(?=## )", part):
        if b.startswith("## Table "):
            parts += [PAGEBREAK, table_block(b)]
    legend = between(md, "## Figure S1", None).split("\n", 1)[1].strip()
    parts += [PAGEBREAK, f"![]({png.as_posix()}){{width={dmscrr.SUPP_FIGURE_WIDTH_CM}cm}}\n\n", legend, "\n"]
    return "".join(parts)


def dmscrr_declaration_md() -> str:
    from verification import dmscrr
    tp = title_page_md()
    keep = []
    for key in ("**Title:**", "**Author:**", "**Declaration of competing interest:**"):
        hit = [ln for ln in tp.splitlines() if ln.startswith(key)]
        if len(hit) != 1:
            raise SystemExit(f"title_page_src.md: expected one line starting {key}")
        keep.append(hit[0])
    return "# Declaration of interest\n\n" + "\n\n".join(keep) + "\n\n" + dmscrr.COMPETING + "\n"


def render_png_rgb(pdf: Path, png: Path, dpi: int) -> None:
    import fitz  # PyMuPDF
    fitz.open(str(pdf))[0].get_pixmap(dpi=dpi, alpha=False, colorspace=fitz.csRGB).save(str(png))


def dmscrr_word_counts(path02: Path) -> dict:
    """Word's counts of 02 (tools/word_count_word.ps1) and the DMSCRR total: the main text with its
    subsection headings, plus Table 1 (cells, title and notes) and the figure legends."""
    w = word_counts(path02)
    w["display_words"] = w["table_cells"] + w["table_text"] + w["legends"]
    w["dmscrr_total"] = w["main_with_headings"] + w["display_words"]
    w["counted_by"] += ("; DMSCRR: dmscrr_total = main_with_headings + display_words (table_cells + table_text + "
                        "legends), the journal's 5,000-word basis (the abstract and references are not counted)")
    (MS / "word_counts_word.json").write_text(json.dumps(w, indent=1) + "\n", encoding="utf-8", newline="\n")
    return w


def dmscrr_build(doi: str | None, no_word: bool) -> int:
    from verification import dmscrr
    hl = not doi
    record: dict = {"figures": {}}
    names = set(dmscrr.DOCX) | {f for pair in dmscrr.FIGURE_FILES.values() for f in pair}
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        ref = tmp / "reference.docx"
        make_reference(ref)
        out02 = OUT / dmscrr.MANUSCRIPT
        run_pandoc(with_doi(dmscrr_manuscript_md(), doi), out02, ref, tmp)
        postprocess(out02, line_numbers=True, placeholder=hl, table_pt=9)
        print("built", dmscrr.MANUSCRIPT)
        if not no_word:
            w = dmscrr_word_counts(out02)
            print(f"Word counts: abstract {w['abstract']}, main text with headings {w['main_with_headings']}, Table 1 and "
                  f"legends {w['display_words']}, total {w['dmscrr_total']} (limits {dmscrr.LIMITS['abstract']} and "
                  f"{dmscrr.LIMITS['total']})")
        png = tmp / "figureS1_embed.png"
        render_png_rgb(EX / "figureS1.pdf", png, EMBED_DPI)
        record["supplement_figure"] = {"pdf": "exhibits/figureS1.pdf", "pdf_sha256": sha256(EX / "figureS1.pdf"),
                                       "embedded_sha256": sha256(png)}
        fill = lambda md: dmscrr.fill_counts(md, MS)  # noqa: E731
        jobs = [
            (dmscrr.TITLE_PAGE, fill(title_page_md()), dict(placeholder=hl), False),
            (dmscrr.HIGHLIGHTS, read("highlights.md"), {}, False),
            (dmscrr.SUPPLEMENT, dmscrr_supplement_md(png), dict(landscape=True, table_pt=8.5), True),
            (dmscrr.COVER, fill(letter_md("cover_letter.md")), {}, False),
            (dmscrr.DECLARATION, dmscrr_declaration_md(), {}, False),
        ]
        for name, md, kw, links in jobs:
            out = OUT / name
            run_pandoc(with_doi(md, doi), out, ref, tmp, links=links)
            postprocess(out, **kw)
            if name == dmscrr.SUPPLEMENT:
                resize_images(out, dmscrr.SUPP_FIGURE_WIDTH_CM)
            print("built", name)
    for k, (tif, pdf_name) in dmscrr.FIGURE_FILES.items():
        pdf = EX / f"figure{k}.pdf"
        shutil.copyfile(pdf, OUT / pdf_name)
        print(render_tiff(pdf, OUT / tif, dmscrr.TIFF_DPI))
        record["figures"][str(k)] = {"pdf": f"exhibits/figure{k}.pdf", "pdf_sha256": sha256(pdf), "tif": tif,
                                     "tif_sha256": sha256(OUT / tif)}
    record["files"] = {n: sha256(OUT / n) for n in sorted(names)}
    (MS / dmscrr.BUILD_RECORD).write_text(json.dumps(record, indent=1) + "\n", encoding="utf-8", newline="\n")
    for f in sorted(OUT.iterdir()):
        if f.is_file() and f.name not in names and not SUBMITTED.match(f.name):
            print(f"note: {f.name} is not part of this set (left from an earlier build?); remove it")
    left = [n for n in (dmscrr.TITLE_PAGE, dmscrr.COVER) if "[[" in docx_text(OUT / n)]
    if left:
        print(f"note: word-count placeholders left in {', '.join(left)} (build without --no-word to fill them)")
    print("built into", OUT)
    return 0


def resize_images(path: Path, width_cm: float) -> None:
    """Every inline image set to width_cm (pandoc caps images at the portrait text width of the
    reference document, before the landscape pages are set)."""
    cx_new = int(width_cm * 360000)

    def fn(xml: str) -> str:
        def one(m: re.Match) -> str:
            cx, cy = int(m.group(2)), int(m.group(4))
            return f"{m.group(1)}{cx_new}{m.group(3)}{round(cy * cx_new / cx)}{m.group(5)}"
        return re.sub(r'(<(?:wp:extent|a:ext) cx=")(\d+)(" cy=")(\d+)(")', one, xml)
    tmp = path.with_suffix(".resize")
    with zipfile.ZipFile(path) as zi, zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as zo:
        for item in zi.infolist():
            data = zi.read(item.filename)
            if item.filename == "word/document.xml":
                data = fn(data.decode("utf-8")).encode("utf-8")
            zo.writestr(item, data)
    tmp.replace(path)


def docx_text(path: Path) -> str:
    with zipfile.ZipFile(path) as z:
        return re.sub(r"<[^>]+>", "", z.read("word/document.xml").decode("utf-8"))


def with_doi(md: str, doi: str | None) -> str:
    return md.replace(DOI_PLACEHOLDER, doi) if doi else md


# --------------------------------------------------------------------------------------
# pandoc and the reference document
# --------------------------------------------------------------------------------------
def set_font(obj, size: float | None = 12) -> None:
    obj.font.name = FONT
    if size:
        obj.font.size = Pt(size)
    rpr = obj.element.get_or_add_rPr()
    rf = rpr.find(qn("w:rFonts"))
    if rf is None:
        rf = OxmlElement("w:rFonts")
        rpr.insert(0, rf)
    for a in ("w:ascii", "w:hAnsi", "w:cs", "w:eastAsia"):
        rf.set(qn(a), FONT)
    for a in ("w:asciiTheme", "w:hAnsiTheme", "w:cstheme", "w:eastAsiaTheme"):
        if rf.get(qn(a)) is not None:
            del rf.attrib[qn(a)]


def make_reference(path: Path) -> None:
    raw = subprocess.run(["pandoc", "--print-default-data-file", "reference.docx"],
                         capture_output=True, check=True).stdout
    path.write_bytes(raw)
    doc = Document(str(path))
    for name in ("Table Title", "Table Note"):
        if name not in [s.name for s in doc.styles]:
            doc.styles.add_style(name, WD_STYLE_TYPE.PARAGRAPH).base_style = doc.styles["Normal"]
    for st in doc.styles:
        if st.type == WD_STYLE_TYPE.PARAGRAPH:
            set_font(st, 12)
            st.font.color.rgb = None
            pf = st.paragraph_format
            pf.line_spacing = 2.0
            pf.space_before = Pt(0)
            pf.space_after = Pt(6)
            pf.alignment = WD_ALIGN_PARAGRAPH.LEFT
            pf.keep_together = False
            pf.widow_control = True
            if st.name.startswith("Heading") or st.name == "Title":
                st.font.bold = True
                st.font.italic = False
                pf.keep_with_next = True
                pf.space_before = Pt(12)
        elif st.type == WD_STYLE_TYPE.CHARACTER:
            set_font(st, None)
            st.font.color.rgb = None
    doc.styles["Heading 1"].font.size = Pt(14)
    doc.styles["Heading 3"].font.italic = True
    tt = doc.styles["Table Title"]
    tt.paragraph_format.keep_with_next = True
    tt.paragraph_format.line_spacing = 1.5
    tn = doc.styles["Table Note"]
    set_font(tn, 10)
    tn.paragraph_format.line_spacing = 1.0
    tn.paragraph_format.space_before = Pt(3)
    tn.paragraph_format.space_after = Pt(3)
    doc.save(str(path))


def run_pandoc(md: str, out: Path, ref: Path, tmp: Path, links: bool = False) -> None:
    src = tmp / (out.stem + ".md")
    src.write_text(md, encoding="utf-8")
    fmt = PANDOC_FROM.replace("-link_attributes", "+link_attributes") if links else PANDOC_FROM
    subprocess.run(["pandoc", str(src), "-f", fmt, "--reference-doc", str(ref), "-o", str(out)], check=True)


# --------------------------------------------------------------------------------------
# Post-processing with python-docx
# --------------------------------------------------------------------------------------
def page_setup(doc, landscape: bool = False, line_numbers: bool = False) -> None:
    for sec in doc.sections:
        if landscape:
            sec.orientation = WD_ORIENT.LANDSCAPE
            sec.page_width, sec.page_height = Cm(29.7), Cm(21.0)
        else:
            sec.orientation = WD_ORIENT.PORTRAIT
            sec.page_width, sec.page_height = Cm(21.0), Cm(29.7)
        sec.top_margin = sec.bottom_margin = sec.left_margin = sec.right_margin = Cm(2.5)
        sec.footer_distance = Cm(1.25)
        sp = sec._sectPr
        for e in sp.findall(qn("w:lnNumType")):
            sp.remove(e)
        if line_numbers:
            ln = OxmlElement("w:lnNumType")
            ln.set(qn("w:countBy"), "1")
            ln.set(qn("w:restart"), "continuous")
            ln.set(qn("w:distance"), "283")
            anchor = None
            for tag in ("w:pgBorders", "w:paperSrc", "w:pgMar"):
                anchor = sp.find(qn(tag))
                if anchor is not None:
                    break
            anchor.addnext(ln)
        p = sec.footer.paragraphs[0] if sec.footer.paragraphs else sec.footer.add_paragraph()
        for r in list(p.runs):
            r._r.getparent().remove(r._r)
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = p.add_run()
        for kind in ("begin", "instr", "separate", "text", "end"):
            if kind == "instr":
                e = OxmlElement("w:instrText")
                e.set(qn("xml:space"), "preserve")
                e.text = " PAGE "
            elif kind == "text":
                e = OxmlElement("w:t")
                e.text = "1"
            else:
                e = OxmlElement("w:fldChar")
                e.set(qn("w:fldCharType"), kind)
            run._r.append(e)
        set_font(run, 11)


def border(tag: str, val: str = "single", sz: int = 8) -> OxmlElement:
    e = OxmlElement(f"w:{tag}")
    e.set(qn("w:val"), val)
    if val != "nil":
        e.set(qn("w:sz"), str(sz))
        e.set(qn("w:space"), "0")
        e.set(qn("w:color"), "000000")
    return e


TBLPR_ORDER = ["tblStyle", "tblpPr", "tblOverlap", "bidiVisual", "tblStyleRowBandSize", "tblStyleColBandSize",
               "tblW", "jc", "tblCellSpacing", "tblInd", "tblBorders", "shd", "tblLayout", "tblCellMar", "tblLook",
               "tblCaption", "tblDescription"]
TCPR_ORDER = ["cnfStyle", "tcW", "gridSpan", "hMerge", "vMerge", "tcBorders", "shd", "noWrap", "tcMar",
              "textDirection", "tcFitText", "vAlign", "hideMark"]


def reorder(parent, order: list[str]) -> None:
    kids = sorted(list(parent), key=lambda e: order.index(e.tag.split("}")[1])
                  if e.tag.split("}")[1] in order else len(order))
    for e in kids:
        parent.remove(e)
    for e in kids:
        parent.append(e)


def text_of(el) -> str:
    return "".join(x.text or "" for x in el.iter(qn("w:t")))


def col_texts(t) -> list[list[str]]:
    """The cell texts of each column; a block-label row (it will span the table) is left out."""
    cols: list[list[str]] = [[] for _ in t.columns]
    spans = set(spanning_rows(t._tbl))
    for i, tr in enumerate(t._tbl.findall(qn("w:tr"))):
        tcs = tr.findall(qn("w:tc"))
        if len(tcs) != len(cols) or i in spans:
            continue
        for j, tc in enumerate(tcs):
            cols[j].append(text_of(tc))
    return cols


PAD = 2 * 108 + 20  # the cell margins and a little slack (twips)


def col_mins(t, size: float) -> list[float]:
    """Each column's minimum width (twips): its longest word (half an em per character)."""
    char = size * 20 * 0.52
    return [(max((len(w) for s in texts for w in s.split()), default=3) + 1) * char + PAD for texts in col_texts(t)]


def fit_size(t, total: int, size: float, floor: float = 7.0) -> float:
    while sum(col_mins(t, size)) >= total and size - 0.5 >= floor:
        size -= 0.5
    return size


def col_widths(t, total: int, size: float) -> list[int]:
    char = size * 20 * 0.52
    mins, wants = col_mins(t, size), []
    for j, texts in enumerate(col_texts(t)):
        lengths = sorted(len(s.strip()) for s in texts[1:] if s.strip()) or [3]
        typical = lengths[int(0.9 * (len(lengths) - 1))]
        wants.append(max(min(typical, 150) * char + PAD, mins[j]))
    if sum(mins) >= total:
        raw = [total * m / sum(mins) for m in mins]
    elif sum(wants) <= total:
        raw = [w + (total - sum(wants)) * w / sum(wants) for w in wants]
    else:
        fixed: dict[int, float] = {}
        while True:
            free = total - sum(fixed.values())
            rest = sum(w for j, w in enumerate(wants) if j not in fixed)
            raw = [fixed.get(j, free * w / rest) for j, w in enumerate(wants)]
            low = [j for j, (x, m) in enumerate(zip(raw, mins)) if j not in fixed and x < m]
            if not low:
                break
            for j in low:
                fixed[j] = mins[j]
    widths = [int(round(x)) for x in raw]
    widths[-1] += total - sum(widths)
    return widths


def is_bold_run(r) -> bool:
    rpr = r.find(qn("w:rPr"))
    b = rpr.find(qn("w:b")) if rpr is not None else None
    return b is not None and b.get(qn("w:val")) not in ("0", "false")


def spanning_rows(tbl, first: int = 1) -> list[int]:
    """Rows (after the header) whose first cell is wholly bold and whose other cells are empty
    (tables.md writes '| **Label** | | ... |'): each becomes one cell spanning the table."""
    out = []
    for i, tr in enumerate(tbl.findall(qn("w:tr"))):
        tcs = tr.findall(qn("w:tc"))
        if i < first or len(tcs) < 2:
            continue
        texts = [text_of(tc) for tc in tcs]
        runs = [r for r in tcs[0].iter(qn("w:r")) if text_of(r).strip()]
        if texts[0].strip() and not any(x.strip() for x in texts[1:]) and runs and all(map(is_bold_run, runs)):
            out.append(i)
    return out


def set_cell_border(tc, edge: str, val: str, sz: int = 6) -> None:
    tb = tc.get_or_add_tcPr().find(qn("w:tcBorders"))
    old = tb.find(qn(f"w:{edge}"))
    new = border(edge, val, sz)
    if old is not None:
        old.addprevious(new)
        tb.remove(old)
    else:
        tb.append(new)


def merge_spanning_rows(tbl, total: int) -> None:
    rows = tbl.findall(qn("w:tr"))
    ncols = len(tbl.tblGrid.findall(qn("w:gridCol")))
    for i in spanning_rows(tbl, first=1):
        tcs = rows[i].findall(qn("w:tc"))
        for tc in tcs[1:]:
            rows[i].remove(tc)
        tcPr = tcs[0].get_or_add_tcPr()
        tcPr.find(qn("w:tcW")).set(qn("w:w"), str(total))
        for e in tcPr.findall(qn("w:gridSpan")):
            tcPr.remove(e)
        gs = OxmlElement("w:gridSpan")
        gs.set(qn("w:val"), str(ncols))
        tcPr.append(gs)
        reorder(tcPr, TCPR_ORDER)
        if i > 1:
            set_cell_border(tcs[0], "top", "single", 4)


def format_table(t, total: int, size: float, gap: float = 1, bold_header: bool = True) -> None:
    """Top, header and bottom rules only (a thin rule above each block label); fixed widths over the
    text block; the header row repeated on each page; single-spaced cells at `size` pt."""
    tbl = t._tbl
    pr = tbl.tblPr
    for tag in ("tblW", "tblInd", "tblLayout", "jc", "tblBorders"):
        for e in pr.findall(qn(f"w:{tag}")):
            pr.remove(e)
    tw = OxmlElement("w:tblW")
    tw.set(qn("w:w"), str(total))
    tw.set(qn("w:type"), "dxa")
    pr.append(tw)
    bd = OxmlElement("w:tblBorders")
    for edge, val in (("top", "single"), ("left", "nil"), ("bottom", "single"), ("right", "nil"),
                      ("insideH", "nil"), ("insideV", "nil")):
        bd.append(border(edge, val))
    pr.append(bd)
    lay = OxmlElement("w:tblLayout")
    lay.set(qn("w:type"), "fixed")
    pr.append(lay)
    reorder(pr, TBLPR_ORDER)
    widths = col_widths(t, total, size)
    for c, w in zip(tbl.tblGrid.findall(qn("w:gridCol")), widths):
        c.set(qn("w:w"), str(w))
    rows = tbl.findall(qn("w:tr"))
    for i, tr in enumerate(rows):
        trPr = tr.get_or_add_trPr()
        for tag in ("w:cantSplit", "w:tblHeader"):
            for e in trPr.findall(qn(tag)):
                trPr.remove(e)
        trPr.append(OxmlElement("w:cantSplit"))
        if i == 0:
            trPr.append(OxmlElement("w:tblHeader"))
        for tc, w in zip(tr.findall(qn("w:tc")), widths):
            tcPr = tc.get_or_add_tcPr()
            for tag in ("w:tcW", "w:tcBorders", "w:shd"):
                for e in tcPr.findall(qn(tag)):
                    tcPr.remove(e)
            e = OxmlElement("w:tcW")
            e.set(qn("w:w"), str(w))
            e.set(qn("w:type"), "dxa")
            tcPr.append(e)
            tb = OxmlElement("w:tcBorders")
            tb.append(border("top", "single") if i == 0 else border("top", "nil"))
            tb.append(border("left", "nil"))
            tb.append(border("bottom", "single", 6) if i in (0, len(rows) - 1) else border("bottom", "nil"))
            tb.append(border("right", "nil"))
            tcPr.append(tb)
            reorder(tcPr, TCPR_ORDER)
    merge_spanning_rows(tbl, total)
    for i, row in enumerate(t.rows):
        for c in row.cells:
            for p in c.paragraphs:
                pf = p.paragraph_format
                pf.line_spacing = 1.0
                pf.space_before = Pt(gap)
                pf.space_after = Pt(gap)
                pf.keep_with_next = i == 0 or i == len(t.rows) - 1
                p.alignment = WD_ALIGN_PARAGRAPH.LEFT
                mark_size(p, size)
                for r in p.runs:
                    set_font(r, size)
                    if i == 0 and bold_header:
                        r.font.bold = True
                    elif i == 0:
                        r.font.bold = False  # the IJTLD: no bolding in tables


def mark_size(p, size: float) -> None:
    """The paragraph mark at `size` pt, so that an empty cell does not set a 12 pt row height."""
    ppr = p._p.get_or_add_pPr()
    rpr = ppr.find(qn("w:rPr"))
    if rpr is None:
        rpr = OxmlElement("w:rPr")
        ppr.append(rpr)
    for tag in ("w:sz", "w:szCs"):
        for e in rpr.findall(qn(tag)):
            rpr.remove(e)
        e = OxmlElement(tag)
        e.set(qn("w:val"), str(int(round(2 * size))))
        rpr.append(e)


def move_page_breaks(doc) -> None:
    """A paragraph holding only a page break is removed and the next paragraph starts a new page."""
    from docx.text.paragraph import Paragraph
    body = doc.element.body
    for p in list(body.iterchildren(qn("w:p"))):
        brs = list(p.iter(qn("w:br")))
        if not brs or any(b.get(qn("w:type")) != "page" for b in brs) or text_of(p).strip():
            continue
        nxt = p.getnext()
        if nxt is None or nxt.tag != qn("w:p"):
            continue
        Paragraph(nxt, doc._body).paragraph_format.page_break_before = True
        body.remove(p)


def highlight(doc, pattern: re.Pattern) -> None:
    for p in doc.paragraphs:
        for run in list(p.runs):
            parts = pattern.split(run.text)
            if len(parts) == 1:
                continue
            anchor = run._r
            for part in parts:
                if not part:
                    continue
                r = copy.deepcopy(run._r)
                anchor.addnext(r)
                anchor = r
                nr = Run(r, p)
                nr.text = part
                if pattern.fullmatch(part):
                    nr.font.highlight_color = WD_COLOR_INDEX.YELLOW
            run._r.getparent().remove(run._r)


APP_XML = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
           '<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties">'
           '<Company></Company><Manager></Manager></Properties>')


def scrub_app_xml(path: Path) -> None:
    tmp = path.with_suffix(".scrub")
    with zipfile.ZipFile(path) as zi, zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as zo:
        for item in zi.infolist():
            data = zi.read(item.filename)
            if item.filename == "docProps/app.xml":
                data = APP_XML.encode("utf-8")
            zo.writestr(item, data)
    tmp.replace(path)


def postprocess(path: Path, *, landscape: bool = False, line_numbers: bool = False, table_pt: float = 10,
                placeholder: bool = False, bold_header: bool = True) -> None:
    doc = Document(str(path))
    page_setup(doc, landscape=landscape, line_numbers=line_numbers)
    move_page_breaks(doc)
    total = (16838 if landscape else 11906) - 2 * 1417
    for t in doc.tables:
        wide = not landscape and len(t.columns) >= 6
        format_table(t, total, fit_size(t, total, table_pt - 1 if wide else table_pt), gap=0 if landscape else 1,
                     bold_header=bold_header)
    if placeholder:
        highlight(doc, re.compile("(" + re.escape(DOI_PLACEHOLDER) + ")"))
    cp = doc.core_properties
    for attr in ("author", "last_modified_by", "title", "comments", "keywords", "subject", "category",
                 "identifier", "content_status", "language", "version"):
        setattr(cp, attr, "")
    cp.revision = 1
    doc.save(str(path))
    scrub_app_xml(path)


# --------------------------------------------------------------------------------------
# Figures and the graphical abstract
# --------------------------------------------------------------------------------------
def render_tiff(pdf: Path, tif: Path, dpi: int, gray: bool = False) -> str:
    import fitz  # PyMuPDF
    from PIL import Image
    Image.MAX_IMAGE_PIXELS = None
    page = fitz.open(str(pdf))[0]
    pix = page.get_pixmap(dpi=dpi, alpha=False, colorspace=fitz.csRGB)
    im = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
    r, g, b = im.split()
    if gray:
        im = im.convert("L")  # the IJTLD figures are black and white
    elif r.tobytes() == g.tobytes() == b.tobytes():
        im = r
    im.save(tif, format="TIFF", compression="tiff_lzw", dpi=(dpi, dpi))
    chk = Image.open(tif)
    w_in, h_in = page.rect.width / 72, page.rect.height / 72
    return (f"{tif.name}: {chk.mode} {chk.size[0]}x{chk.size[1]} px, {chk.info.get('dpi')} dpi, "
            f"{chk.info.get('compression')}, {w_in:.2f} x {h_in:.2f} in ({w_in * 2.54:.1f} x {h_in * 2.54:.1f} cm)")


def figures() -> list[str]:
    lines = []
    for k in range(1, N_FIGURES + 1):
        tif_name, pdf_name = figure_names(k)
        pdf = EX / f"figure{k}.pdf"
        shutil.copyfile(pdf, OUT / pdf_name)
        lines.append(render_tiff(pdf, OUT / tif_name, TIFF_DPI))
    pdf = EX / "graphical_abstract.pdf"
    shutil.copyfile(pdf, OUT / GA[1])
    lines.append(render_tiff(pdf, OUT / GA[0], GA_DPI))
    return lines


# --------------------------------------------------------------------------------------
# Word counts (Microsoft Word, through PowerShell COM)
# --------------------------------------------------------------------------------------
def word_counts(docx: Path) -> dict:
    out = MS / "word_counts_word.json"
    subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File",
                    str(ROOT / "tools" / "word_count_word.ps1"), str(docx), str(out)], check=True)
    w = json.loads(out.read_text(encoding="utf-8-sig"))
    end = ("the first paragraph that starts a new page (the IJTLD Introduction has no heading)"
           if folder_journal(MS) == "ijtld" else "the Keywords line")
    w["counted_by"] = ("Microsoft Word (ComputeStatistics) on 02_manuscript.docx: abstract = the paragraphs between the "
                       f"Abstract heading and {end}; main text = Introduction to Discussion, headings "
                       "excluded (main_with_headings includes the subsection headings); tables excluded")
    w["source_md5"] = hashlib.md5(read("manuscript.md").encode("utf-8")).hexdigest()
    out.write_text(json.dumps(w, indent=1) + "\n", encoding="utf-8", newline="\n")
    return w


def built_names() -> set[str]:
    names = {"01_title_page.docx", "02_manuscript.docx", "03_highlights.docx", SUPPLEMENT, "09_cover_letter.docx",
             "10_declaration_of_interest.docx"} | set(GA)
    for k in range(1, N_FIGURES + 1):
        names |= set(figure_names(k))
    return names


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0], allow_abbrev=False)
    ap.add_argument("--doi", help="the Zenodo version DOI (10.5281/zenodo.NNNNNNN), filled in every file")
    ap.add_argument("--no-word", action="store_true", help="skip Word's word counts")
    ap.add_argument("--manuscript-dir", default=DEFAULT_MS_DIR, help="the manuscript folder (default manuscript)")
    ap.add_argument("--profile", choices=PROFILES, default="pcd",
                    help="the journal set to build: pcd (default), ijtld (manuscript/v2) or dmscrr (manuscript/v3)")
    a = ap.parse_args(argv)  # an unknown option stops the build (argparse exits with status 2)
    if a.doi and not DOI_RE.match(a.doi):
        raise SystemExit(f"--doi must look like 10.5281/zenodo.NNNNNNN, not {a.doi!r}")
    d = Path(a.manuscript_dir)
    configure(d if d.is_absolute() else ROOT / d)
    if not MS.is_dir():
        raise SystemExit(f"{a.manuscript_dir} not present (it is private)")
    frozen = submitted_markers(MS)
    if frozen:
        raise SystemExit(f"refusing to write: {', '.join(p.name for p in frozen)} marks {MS} as submitted; "
                         f"put post-submission changes in a new folder (for example a _v2 folder)")
    declared = folder_journal(MS)
    if declared is not None and declared != a.profile:
        raise SystemExit(f"--profile {a.profile} does not match the folder, whose section_phrases.json says "
                         f"journal {declared!r}")
    OUT.mkdir(exist_ok=True)
    if a.profile == "ijtld":
        return ijtld_build(a.doi, a.no_word)
    if a.profile == "dmscrr":
        return dmscrr_build(a.doi, a.no_word)
    hl = not a.doi
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        ref = tmp / "reference.docx"
        make_reference(ref)
        jobs = [
            ("01_title_page.docx", title_page_md(), dict(placeholder=hl)),
            ("02_manuscript.docx", manuscript_md(), dict(line_numbers=True, placeholder=hl)),
            ("03_highlights.docx", read("highlights.md"), {}),
            (SUPPLEMENT, supplement_md(), dict(landscape=True, table_pt=8.5)),
            ("09_cover_letter.docx", letter_md("cover_letter.md"), {}),
            ("10_declaration_of_interest.docx", declaration_md(), {}),
        ]
        for name, md, kw in jobs:
            out = OUT / name
            run_pandoc(with_doi(md, a.doi), out, ref, tmp)
            postprocess(out, **kw)
            print("built", name)
    for ln in figures():
        print(ln)
    for f in sorted(OUT.iterdir()):
        if f.is_file() and f.name not in built_names() and not SUBMITTED.match(f.name):
            print(f"note: {f.name} is not part of this set (left from an earlier build?); remove it")
    if not a.no_word:
        w = word_counts(OUT / "02_manuscript.docx")
        print(f"Word counts: abstract {w['abstract']}, main text {w['main_text']} (with subsection headings "
              f"{w['main_with_headings']}) (limits 200 and 3,000)")
    print("built into", OUT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
