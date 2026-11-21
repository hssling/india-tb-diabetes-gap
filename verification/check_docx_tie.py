# Adapted from hssling/india-tb-priority-tool v1.0.1 (MIT), verification/check_docx_tie.py (itself
# adapted from hssling/india-tb-acf-campaign and hssling/india-state-tb-score); modified: the Primary
# Care Diabetes set of this paper (single anonymized: the manuscript carries its title page, so the
# anonymisation checks become title-page checks); Word's counts against the 200-word abstract and the
# 3,000-word main text; at most five display items; the highlights; the figures and the optional
# graphical abstract byte-equal to the exhibits and at their resolution.
"""Tie the submission files to their Markdown sources and check the journal's limits.

Run as: python -I verification/check_docx_tie.py [--manuscript-dir DIR]

The manuscript folder is DIR (default manuscript/; git-ignored). The files in <folder>/submission/
(built by tools/build_submission.py) are what the journal receives; the Markdown files in <folder>/
are what check_manuscript_numbers.py verifies. Reading the .docx files needs only zipfile and
ElementTree (the TIFF checks use Pillow when it is installed).

1. Text tie. Each .docx's units (paragraphs outside tables; table rows as their cells joined by
   " | ") equal, in order, the units of its Markdown source(s): headings, paragraphs, list items,
   table rows and reference entries, normalised the same way on both sides (emphasis markers and
   escapes removed, superscripts written ^...^, whitespace collapsed, the Zenodo DOI read as one
   token). A changed number, sign, cell, reference number or inserted word on either side is a
   difference. Every file of the set is present and no other file is in submission/ (except a
   SUBMITTED_* record and the _render folder).
2. Title page (single anonymized review). 02 names the author, the affiliation, the e-mail and the
   ORCID before its Abstract, and its title equals 01's.
3. Internal identifiers and wording (check_manuscript_numbers.BANNED and WORDING) do not occur in
   02 (before the References), 03 or 08.
4. Highlights: 3 to 5 bullets in 03, each at most 85 characters including spaces.
5. Word's counts. <folder>/word_counts_word.json (Word's ComputeStatistics on 02, written by the
   build) belongs to the current manuscript.md; the abstract is at most 200 words and the main text
   (Introduction to Discussion) at most 3,000; the title page quotes the counts.
6. Display items: 02 holds at most one table per exhibit and, with the figure files, at most five.
7. Figures: each NN_Figure_k.pdf equals exhibits/figurek.pdf byte for byte, and each TIFF is at least
   1000 dpi and at most 7480 pixels wide; the graphical abstract's PDF equals the exhibit and its
   TIFF is at least 1328 x 531 pixels.

Prints "SKIPPED" and exits 0 when <folder>/ or <folder>/submission/ is absent. Exit 1 on any problem.
"""
from __future__ import annotations

import difflib
import hashlib
import json
import re
import sys
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from verification import check_manuscript_numbers as cmn  # noqa: E402

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
# The release DOI: the placeholder in the Markdown, the DOI that --doi fills in the .docx. Zenodo DOIs
# cited as themselves (the released tbprio software) are compared digit for digit.
CITED_ZENODO = ("24411057",)
DOI = re.compile(r"10\.5281/zenodo\.(?:X{3,}|(?!(?:" + "|".join(CITED_ZENODO) + r")\b)\d+)")
LIMITS = {"abstract": 200, "main_text": 3000}
HIGHLIGHT_CHARS = 85
MIN_DPI, MAX_PX = 1000, 7480
GA_MIN = (1328, 531)
MAX_DISPLAY = 5
MS = cmn.MS_NAME
TP = cmn.TITLE_PAGE
# The paragraphs the build adds (tools/build_submission.py imports them from here).
SUPP_NOTE = ("Tables S1 to S14 are cited in the manuscript in this order. Every cell is generated from the study's "
             "committed outputs; units are listed alphabetically (tiers, not ranks).")
DOI_STATEMENT = ("The author declares that they have no known competing financial interests or personal relationships "
                 "that could have appeared to influence the work reported in this paper.")

FIGURES = {k: (f"{p}_Figure_{k}.tif", f"{p}_Figure_{k}.pdf") for k, p in zip(range(1, 5), ("04", "05", "06", "07"))}
GA = ("11_graphical_abstract.tif", "11_graphical_abstract.pdf")
SPEC: dict[str, list[tuple]] = {
    "01_title_page.docx": [("md", TP, None, None)],
    "02_manuscript.docx": [
        ("md", MS, None, "## Figure captions"),
        ("md", "exhibits/tables.md", "## Table 1.", "## Table S1."),
        ("md", MS, "## Figure captions", None),
    ],
    "03_highlights.docx": [("md", cmn.HIGHLIGHTS, None, None)],
    "08_supplementary_material.docx": [
        ("builder", "Supplementary material"),
        ("first", MS, "# "),
        ("builder", SUPP_NOTE),
        ("md", "exhibits/tables.md", "## Table S1.", None),
    ],
    "09_cover_letter.docx": [("md", cmn.COVER, "# Cover letter", None, "drop-first")],
    "10_declaration_of_interest.docx": [
        ("builder", "Declaration of interest"),
        ("first", TP, "**Title:**"),
        ("first", TP, "**Author:**"),
        ("first", TP, "**Declarations of interest:**"),
        ("builder", DOI_STATEMENT),
    ],
}
CHECKED_WORDING = ("02_manuscript.docx", "03_highlights.docx", "08_supplementary_material.docx")
SUBMITTED = re.compile(r"SUBMITTED_.*")


def all_files() -> set[str]:
    return set(SPEC) | {f for pair in FIGURES.values() for f in pair} | set(GA)


# --------------------------------------------------------------------------------------
# Normalisation (the same for both sides)
# --------------------------------------------------------------------------------------
def norm(s: str) -> str:
    s = s.replace("**", "").replace("*", "")
    s = re.sub(r"\\(?=[^\w\s])", "", s)
    s = s.replace("^^", "")
    s = s.replace("\u00a0", " ")
    s = DOI.sub("10.5281/zenodo.<DOI>", s)
    return re.sub(r"\s+", " ", s).strip()


def md_slice(text: str, start: str | None, end: str | None) -> str:
    lines = text.splitlines()
    i = 0 if start is None else next(k for k, ln in enumerate(lines) if ln.startswith(start))
    j = len(lines) if end is None else next(k for k, ln in enumerate(lines) if k > i and ln.startswith(end))
    return "\n".join(lines[i:j])


def row_unit(cells) -> str:
    cells = list(cells)
    while len(cells) > 1 and not cells[-1]:
        cells.pop()
    return " | ".join(cells)


def md_units(text: str) -> list[str]:
    """Headings, paragraphs, list items and table rows of a Markdown text, normalised."""
    units: list[str] = []
    para: list[str] = []

    def flush() -> None:
        if para:
            units.append(norm(" ".join(para)))
            para.clear()

    for ln in text.splitlines():
        s = ln.strip()
        if not s:
            flush()
        elif s.startswith("#"):
            flush()
            units.append(norm(s.lstrip("#")))
        elif s.startswith("|"):
            flush()
            body = s[1:-1] if s.endswith("|") else s[1:]
            cells = body.split("|")
            if all(re.fullmatch(r"\s*:?-{3,}:?\s*", c) for c in cells):
                continue
            units.append(row_unit(norm(c) for c in cells))
        elif re.match(r"[-*+] ", s):
            flush()
            para.append(s[2:])
        elif re.match(r"\[\d+\] ", s):
            flush()
            para.append(s)
        else:
            para.append(s)
    flush()
    return [u for u in units if u]


# --------------------------------------------------------------------------------------
# .docx units
# --------------------------------------------------------------------------------------
def para_text(p: ET.Element) -> str:
    parts = []
    for r in p.iter(f"{W}r"):
        va = r.find(f"{W}rPr/{W}vertAlign")
        sup = va is not None and va.get(f"{W}val") == "superscript"
        txt = "".join((t.text or "") if t.tag == f"{W}t" else " " for t in r if t.tag in (f"{W}t", f"{W}tab", f"{W}br"))
        parts.append(f"^{txt}^" if sup and txt.strip() else txt)
    return "".join(parts)


def docx_units(path: Path) -> list[str]:
    with zipfile.ZipFile(path) as z:
        body = ET.fromstring(z.read("word/document.xml")).find(f"{W}body")
    units: list[str] = []
    for el in body:
        if el.tag == f"{W}p":
            u = norm(para_text(el))
            if u:
                units.append(u)
        elif el.tag == f"{W}tbl":
            for tr in el.iter(f"{W}tr"):
                cells = [" ".join(para_text(p) for p in tc.iter(f"{W}p")) for tc in tr.findall(f"{W}tc")]
                units.append(row_unit(norm(c) for c in cells))
    return units


def docx_tables(path: Path) -> int:
    with zipfile.ZipFile(path) as z:
        body = ET.fromstring(z.read("word/document.xml")).find(f"{W}body")
    return sum(1 for el in body if el.tag == f"{W}tbl")


def docx_all_text(path: Path) -> str:
    out = []
    with zipfile.ZipFile(path) as z:
        for name in z.namelist():
            if name.endswith((".xml", ".rels")):
                raw = z.read(name).decode("utf-8", errors="replace")
                out += [re.sub(r"<[^>]+>", "", raw), raw]
    return "\n".join(out)


# --------------------------------------------------------------------------------------
# Expected units
# --------------------------------------------------------------------------------------
def expected(ms_dir: Path, name: str) -> list[str]:
    out: list[str] = []
    for part in SPEC[name]:
        if part[0] == "builder":
            out.append(norm(part[1]))
        elif part[0] == "first":
            text = (ms_dir / part[1]).read_text(encoding="utf-8")
            if part[2] == "# ":
                hits = [norm(text.splitlines()[0].lstrip("#"))]
            else:
                hits = [u for u in md_units(text) if u.startswith(norm(part[2]))]
            if len(hits) != 1:
                raise ValueError(f"{part[1]}: {len(hits)} units start with {part[2]!r}")
            out.append(hits[0])
        else:
            text = (ms_dir / part[1]).read_text(encoding="utf-8")
            units = md_units(md_slice(text, part[2], part[3]))
            if len(part) > 4 and part[4] == "drop-first":
                units = units[1:]
            out += units
    return out


def compare(name: str, got: list[str], want: list[str], limit: int = 6) -> list[str]:
    if got == want:
        return []
    out = []
    sm = difflib.SequenceMatcher(None, want, got, autojunk=False)
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            continue
        md = " // ".join(want[i1:i2])[:300] or "(nothing)"
        dx = " // ".join(got[j1:j2])[:300] or "(nothing)"
        out.append(f"TIE {name}: {tag} at markdown unit {i1 + 1}, docx unit {j1 + 1}:\n    markdown: {md}\n    docx:     {dx}")
        if len(out) >= limit:
            out.append(f"TIE {name}: further differences not listed")
            break
    return out


# --------------------------------------------------------------------------------------
# Title page, wording, highlights, word counts, display items and figures
# --------------------------------------------------------------------------------------
def title_page_problems(units02: list[str], units01: list[str], ms_dir: Path) -> list[str]:
    """Single anonymized: 02 carries the author's details before its Abstract, and its title is 01's."""
    out = []
    head = units02[:units02.index("Abstract")] if "Abstract" in units02 else units02
    tp = (ms_dir / TP).read_text(encoding="utf-8")
    flat = " ".join(head)
    for what, pat in (("author", r"\*\*Author:\*\* ([^^\n]+)"), ("e-mail", r"([\w.+-]+@[\w-]+\.[\w.]+)"),
                      ("ORCID", r"(\d{4}-\d{4}-\d{4}-\d{3}[\dX])"), ("affiliation", r"\^a\^ ([^,\n]+)")):
        m = re.search(pat, tp)
        if not m or norm(m.group(1)) not in flat:
            out.append(f"TITLE PAGE: 02 does not give the {what} before its Abstract")
    t01 = next((u for u in units01 if u.startswith("Title:")), "")
    if not head or t01.removeprefix("Title:").strip() != head[0]:
        out.append("TITLE PAGE: 02's title differs from the title page's")
    return out


def wording_problems(name: str, units: list[str]) -> list[str]:
    text = "\n".join(units)
    if name.startswith("02_"):
        text = text.split("\nReferences\n", 1)[0]
    out = []
    for pat, what in cmn.BANNED + cmn.WORDING:
        for m in re.finditer(pat, text, re.I if (pat, what) in cmn.WORDING else 0):
            out.append(f"WORDING in {name}: {what}: {m.group()!r}")
    return out


def highlight_problems(units: list[str]) -> list[str]:
    bullets = [u for u in units if u != "Highlights"]
    out = []
    if not 3 <= len(bullets) <= 5:
        out.append(f"HIGHLIGHTS: 03 has {len(bullets)} bullets (3 to 5 required)")
    for b in bullets:
        if len(b) > HIGHLIGHT_CHARS:
            out.append(f"HIGHLIGHTS: {len(b)} characters (limit {HIGHLIGHT_CHARS}): {b!r}")
    return out


def word_count_problems(ms_dir: Path, title_units: list[str], abstract_units: list[str]) -> list[str]:
    p = ms_dir / "word_counts_word.json"
    if not p.exists():
        return ["WORDS: word_counts_word.json missing (build with Word: python -I tools/build_submission.py)"]
    w = json.loads(p.read_text(encoding="utf-8"))
    out = []
    md5 = hashlib.md5((ms_dir / MS).read_text(encoding="utf-8").encode("utf-8")).hexdigest()
    if w.get("source_md5") != md5:
        out.append("WORDS: word_counts_word.json is stale (manuscript.md changed): rebuild")
    for k, lim in LIMITS.items():
        if w[k] > lim:
            out.append(f"WORDS: Word counts {w[k]} words in the {k}, over the limit of {lim}")
    own = sum(len(u.split()) for u in abstract_units)
    if own > LIMITS["abstract"]:
        out.append(f"WORDS: the abstract of 02 has {own} words, over the limit of {LIMITS['abstract']}")
    flat = " ".join(title_units)
    for want in (f"abstract {w['abstract']:,} words", f"main text (Introduction to Discussion, headings excluded) "
                 f"{w['main_text']:,} words"):
        if want not in flat:
            out.append(f"WORDS: the title page does not quote Word's count {want!r}")
    return out


def abstract_of(units: list[str]) -> list[str]:
    try:
        i = units.index("Abstract")
    except ValueError:
        return ["(no Abstract heading)"] * 999
    out = []
    for u in units[i + 1:]:
        if u.startswith("Keywords:"):
            break
        out.append(u)
    return out


def display_problems(path02: Path) -> list[str]:
    n_tab = docx_tables(path02)
    out = []
    if n_tab != len(cmn.TABLES):
        out.append(f"DISPLAY: 02 holds {n_tab} tables, the manuscript cites {len(cmn.TABLES)}")
    if n_tab + len(FIGURES) > MAX_DISPLAY:
        out.append(f"DISPLAY: {n_tab} tables and {len(FIGURES)} figures, more than {MAX_DISPLAY} display items")
    return out


def tiff_info(path: Path):
    try:
        from PIL import Image
    except ImportError:
        return None
    Image.MAX_IMAGE_PIXELS = None
    with Image.open(path) as im:
        return im.info.get("dpi", (0, 0)), im.size


def figure_problems(ms_dir: Path) -> list[str]:
    sub, ex = ms_dir / "submission", ms_dir / "exhibits"
    out = []
    pairs = [(k, tif, pdf, ex / f"figure{k}.pdf") for k, (tif, pdf) in FIGURES.items()]
    pairs.append(("GA", GA[0], GA[1], ex / "graphical_abstract.pdf"))
    for k, tif, pdf, src in pairs:
        if (sub / pdf).exists() and src.exists() and (sub / pdf).read_bytes() != src.read_bytes():
            out.append(f"FIGURES: {pdf} differs from exhibits/{src.name} (rebuild)")
        if (sub / tif).exists():
            info = tiff_info(sub / tif)
            if info is None:
                continue
            dpi, size = info
            if k == "GA":
                if size[0] < GA_MIN[0] or size[1] < GA_MIN[1]:
                    out.append(f"FIGURES: {tif} is {size[0]} x {size[1]} pixels, below {GA_MIN[0]} x {GA_MIN[1]}")
                continue
            if min(float(dpi[0]), float(dpi[1])) < MIN_DPI:
                out.append(f"FIGURES: {tif} is {dpi} dpi, below {MIN_DPI}")
            if size[0] > MAX_PX:
                out.append(f"FIGURES: {tif} is {size[0]} pixels wide, more than {MAX_PX}")
    return out


def problems(ms_dir: Path | None = None, root: Path = ROOT) -> list[str]:
    ms_dir = ms_dir or root / cmn.DEFAULT_MS_DIR
    sub = ms_dir / "submission"
    out: list[str] = []
    units_of: dict[str, list[str]] = {}
    out += [f"EXTRA: {p.name} is not part of the submission set" for p in sorted(sub.iterdir())
            if p.is_file() and p.name not in all_files() and not SUBMITTED.fullmatch(p.name)]
    for name in SPEC:
        path = sub / name
        if not path.exists():
            out.append(f"MISSING: {name}")
            continue
        got = docx_units(path)
        units_of[name] = got
        out += compare(name, got, expected(ms_dir, name))
        if name in CHECKED_WORDING:
            out += wording_problems(name, got)
    for name in [f for pair in FIGURES.values() for f in pair] + list(GA):
        if not (sub / name).exists():
            out.append(f"MISSING: {name}")
    if "02_manuscript.docx" in units_of and "01_title_page.docx" in units_of:
        out += title_page_problems(units_of["02_manuscript.docx"], units_of["01_title_page.docx"], ms_dir)
        out += word_count_problems(ms_dir, units_of["01_title_page.docx"], abstract_of(units_of["02_manuscript.docx"]))
        out += display_problems(sub / "02_manuscript.docx")
    if "03_highlights.docx" in units_of:
        out += highlight_problems(units_of["03_highlights.docx"])
    out += figure_problems(ms_dir)
    return out


def notes(ms_dir: Path) -> list[str]:
    out = []
    for name in ("01_title_page.docx", "02_manuscript.docx"):
        p = ms_dir / "submission" / name
        if p.exists() and "zenodo.XXXXXXX" in docx_all_text(p):
            out.append(f"note: {name} still holds the Zenodo DOI placeholder (rebuild with --doi at release)")
    return out


def main(root: Path = ROOT, argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ms_dir, rest = cmn.manuscript_dir(root, argv)
    if rest:
        print(f"FAIL: unknown arguments {rest}")
        return 1
    name = cmn.rel(ms_dir, root)
    if not ms_dir.is_dir() or not (ms_dir / "submission").is_dir():
        print(f"SKIPPED: {name}/ or {name}/submission/ not present (kept private, not in this repository)")
        return 0
    found = problems(ms_dir, root)
    for ln in found:
        print(ln)
    for ln in notes(ms_dir):
        print(ln)
    n_units = sum(len(docx_units(ms_dir / "submission" / n)) for n in SPEC if (ms_dir / "submission" / n).exists())
    print(f"docx tie: {len(all_files())} files; {len(SPEC)} .docx, {n_units} paragraphs and table rows tied to the "
          f"Markdown; title page in the manuscript; highlights, abstract and main-text limits; at most "
          f"{MAX_DISPLAY} display items; figures and graphical abstract byte-equal to the exhibits; {len(found)} problem(s)")
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main())
