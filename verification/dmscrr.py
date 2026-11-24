"""The DMSCRR profile (Diabetes & Metabolic Syndrome: Clinical Research & Reviews, Elsevier,
Original research article): the journal's limits, structure and wording rules, shared by the build
(tools/build_submission.py), the number check (verification/check_manuscript_numbers.py), the docx
tie (verification/check_docx_tie.py), the mutation test and the reference audit.

A manuscript folder uses this profile when its section_phrases.json says "journal": "dmscrr"
(manuscript/v3). The rules (manuscript/v3/journal_rules.md, from the guide for authors) make the
checks FAIL when broken:

- at most 5000 words for the main text (Introduction to Discussion, subsection headings included)
  plus the text of the tables and the figure legends; at most five display items; at most 50
  references (not counted); an abstract (not counted) of at most 200 words headed Background and
  Aims, Methods, Results and Conclusions, without citations and without undefined abbreviations;
- the sections, in order: Abstract, Introduction, Subjects, Materials and Methods, Results,
  Discussion, the declarations, the generative-AI declaration, Acknowledgements (directly before
  the References), References, Figure legends;
- a title of at most 120 characters without abbreviations; 3 to 12 keywords, none a multi-word
  phrase joined by "and" or "of";
- highlights in the journal's structure: two lines under "What is known about this research
  topic?", then under "What this study adds and its future implications?" two new-findings lines
  and one impact line, each at most 85 characters;
- Vancouver references in the guide's punctuation ("Journal Year; Volume: pages.", page ranges
  shortened as in "312-9", all authors when six or fewer, otherwise the first six and "et al."),
  each article with the DOI recorded in reference_dois.json; web references with an access date;
  the study's data cited with "[dataset]";
- the exact no-funding sentence and generative-AI wording; no "first" or novelty claims, no
  "pre-registered", person-first wording, and no mention of earlier journals.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from verification import ijtld

LIMITS = {"total": 5000, "abstract": 200, "references": 50, "display_items": 5, "title_chars": 120,
          "keywords_min": 3, "keywords_max": 12, "highlight_chars": 85}
ABSTRACT_PARTS = ("Background and Aims", "Methods", "Results", "Conclusions")
MAIN_SECTIONS = ("Introduction", "Subjects, Materials and Methods", "Results", "Discussion")
AI_HEADING = ("Declaration of generative AI and AI-assisted technologies in the manuscript preparation "
              "process")
SECTION_ORDER = ["Abstract", *MAIN_SECTIONS, "Funding", "Declaration of competing interest", "Data availability",
                 "CRediT authorship contribution statement", AI_HEADING, "Acknowledgements", "References",
                 "Figure legends"]
FUNDING = ("This research did not receive any specific grant from funding agencies in the public, commercial, or "
           "not-for-profit sectors.")
GENAI = ("During the preparation of this work the author used Claude (Anthropic), a large language model, to assist "
         "with writing and checking analysis code and with drafting and editing the text. After using this tool, the "
         "author reviewed and edited the content as needed and takes full responsibility for the content of the "
         "published article.")
COMPETING = ("The author declares that they have no known competing financial interests or personal relationships "
             "that could have appeared to influence the work reported in this paper.")
TABLES = [1]
FIGURES = [1, 2, 3]

# The submission set (manuscript/v3/submission), numbered in upload order.
TITLE_PAGE = "01_title_page.docx"
MANUSCRIPT = "02_manuscript.docx"
HIGHLIGHTS = "03_highlights.docx"
FIGURE_FILES = {1: ("04_Figure_1.tif", "04_Figure_1.pdf"), 2: ("05_Figure_2.tif", "05_Figure_2.pdf"),
                3: ("06_Figure_3.tif", "06_Figure_3.pdf")}
SUPPLEMENT = "07_supplementary_material.docx"
COVER = "08_cover_letter.docx"
DECLARATION = "09_declaration_of_interest.docx"
DOCX = (TITLE_PAGE, MANUSCRIPT, HIGHLIGHTS, SUPPLEMENT, COVER, DECLARATION)
TIFF_DPI = 1000   # the guide: line art at least 1000 dpi (colour photographs 300)
BUILD_RECORD = "build_record.json"
SUPP_FIGURE_WIDTH_CM = 22
SUPP_NOTE = ("Tables S1 to S14 and Figure S1 are numbered in the order of their first citation in the manuscript. "
             "Every cell is generated from the study's committed outputs; units are listed alphabetically (tiers, not "
             "ranks).")

# Word-count placeholders in title_page_src.md and cover_letter.md, filled by the build from
# word_counts_word.json (Word's counts of 02_manuscript.docx) and the number of references.
PLACEHOLDER = re.compile(r"\[\[(abstract|main|display|total|references)\]\]")

HIGHLIGHT_KNOWN = "What is known about this research topic?"
HIGHLIGHT_ADDS = "What this study adds and its future implications?"
HIGHLIGHT_NEW = "New findings:"
HIGHLIGHT_IMPACT = "Impact and future directions:"

FIRST_CLAIM = [(r"\bfor the first time\b|\b(?:the )?first (?:study|analysis|report|paper|to)\b|\bnovel\b|\bunprecedented\b",
                "a 'first' or novelty claim (novelty must come from the findings)")]
EARLIER_JOURNALS = [(r"\bIJTLD\b|\bInternational Journal of Tuberculosis and Lung Disease\b|\bPrimary Care Diabetes\b"
                     r"|\bPCD-[SD]-|\bdesk[- ]reject\w*|\bresubmi\w*", "an earlier journal or submission is named")]


def wording_hits(text: str) -> list[str]:
    out = [h for h in ijtld.wording_hits(text)]
    for pat, what in FIRST_CLAIM:
        out += [f"{what}: {m.group()!r}" for m in re.finditer(pat, text, re.I)]
    for pat, what in EARLIER_JOURNALS:
        out += [f"{what}: {m.group()!r}" for m in re.finditer(pat, text)]
    return out


# --------------------------------------------------------------------------------------
# Title, keywords, abstract
# --------------------------------------------------------------------------------------
def title_problems(title: str) -> list[str]:
    out = []
    if len(title) > LIMITS["title_chars"]:
        out.append(f"TITLE: {len(title)} characters including spaces, limit {LIMITS['title_chars']}")
    ab = ijtld.abbreviations(title)
    if ab:
        out.append(f"TITLE: abbreviations {ab} (none allowed)")
    return out


def keyword_problems(keywords: list[str]) -> list[str]:
    out = []
    if not LIMITS["keywords_min"] <= len(keywords) <= LIMITS["keywords_max"]:
        out.append(f"KEYWORDS: {len(keywords)} keywords ({LIMITS['keywords_min']} to {LIMITS['keywords_max']} required)")
    for k in keywords:
        if re.search(r"\s(?:and|of)\s", k):
            out.append(f"KEYWORDS: {k!r} is a multi-word phrase joined by 'and' or 'of'")
    return out


ABSTRACT_HEAD = re.compile(r"\*\*([A-Z][A-Za-z ]*?):\*\*")


def abstract_heads(abstract: str) -> list[str]:
    return [h for h in ABSTRACT_HEAD.findall(abstract) if h != "Keywords"]


def undefined_abbreviations(abstract: str) -> list[str]:
    """Abbreviations used in the abstract but not defined there as '(ABBR)' after their full form."""
    text = ABSTRACT_HEAD.sub(" ", abstract)
    defined = set(re.findall(r"\(([A-Za-z0-9-]+)\)", text))
    return sorted({a for a in ijtld.abbreviations(text) if a not in defined})


def split_keywords(line: str) -> list[str]:
    return [x.strip().rstrip(".") for x in line.split(";") if x.strip()]


# --------------------------------------------------------------------------------------
# Highlights
# --------------------------------------------------------------------------------------
def highlight_structure(lines: list[str]) -> tuple[dict[str, list[str]], list[str]]:
    """lines: the highlights as text lines (Markdown without '#'/'- ' markers, or .docx units).
    Returns ({'known': [...], 'new': [...], 'impact': [...]}, problems)."""
    parts: dict[str, list[str]] = {"known": [], "new": [], "impact": []}
    order: list[str] = []
    state = None
    out: list[str] = []
    for ln in lines:
        s = ln.strip()
        if not s or s == "Highlights":
            continue
        if s == HIGHLIGHT_KNOWN:
            state = "known"
        elif s == HIGHLIGHT_ADDS:
            state = "adds"
        elif s == HIGHLIGHT_NEW:
            state = "new"
        elif s == HIGHLIGHT_IMPACT:
            state = "impact"
        elif state in parts:
            parts[state].append(s)
            continue
        else:
            out.append(f"HIGHLIGHTS: line outside the journal's structure: {s!r}")
            continue
        order.append(state)
    if order != ["known", "adds", "new", "impact"]:
        out.append(f"HIGHLIGHTS: headings {order}, expected the journal's: known, adds, new findings, impact")
    for key, n in (("known", 2), ("new", 2), ("impact", 1)):
        if len(parts[key]) != n:
            out.append(f"HIGHLIGHTS: {len(parts[key])} '{key}' line(s), the journal asks for {n}")
    for key in parts:
        for x in parts[key]:
            if len(x) > LIMITS["highlight_chars"]:
                out.append(f"HIGHLIGHTS: {len(x)} characters (limit {LIMITS['highlight_chars']}): {x!r}")
    return parts, out


def highlight_lines_md(md: str) -> list[str]:
    out = []
    for ln in md.splitlines():
        s = ln.strip()
        if s.startswith("#"):
            s = s.lstrip("#").strip()
        elif s.startswith("- "):
            s = s[2:].strip()
        out.append(s)
    return out


# --------------------------------------------------------------------------------------
# References (Vancouver, the guide's punctuation)
# --------------------------------------------------------------------------------------
REF_LINE = ijtld.REF_LINE
CITE = ijtld.CITE
ARTICLE = re.compile(r"[.?!] (?P<journal>[A-Z][^.;?!]*?) (?P<year>\d{4}); (?P<vol>\d+)(?: \((?P<supp>Suppl(?: \d+)?)\))?: "
                     r"(?P<pages>[^ .]+)\. https://doi\.org/(?P<doi>10\.\S+)$")
WEB = ijtld.WEB
ZENODO = re.compile(r"(?:Zenodo, v(?P<ver>\d+\.\d+\.\d+)(?: \[software\])?; \d{4}\. )https://doi\.org/"
                    r"(?P<doi>10\.5281/zenodo\.(?:\d+|X+))$")
AUTHOR = r"[^\W\d_][\w'’-]+(?: [^\W\d_][\w'’-]+)* [A-Z]{1,4}"  # family names with any letters (Lönnroth)


def entry_kind(entry: str) -> str:
    if ZENODO.search(entry):
        return "zenodo"
    if ARTICLE.search(entry):
        return "article"
    if WEB.search(entry):
        return "web"
    return "unknown"


def author_problems(n: int, entry: str) -> list[str]:
    """All authors when six or fewer; otherwise the first six and 'et al.' (a group is one name)."""
    head = re.sub(r"^\[dataset\] ", "", entry).split(". ", 1)[0]
    if head.endswith(", et al"):
        names = head[:-len(", et al")].split(", ")
        if len(names) != 6:
            return [f"REFERENCES: [{n}] 'et al.' after {len(names)} authors (list the first six)"]
        return []
    names = head.split(", ")
    if len(names) > 6 and all(re.fullmatch(AUTHOR, x) for x in names):
        return [f"REFERENCES: [{n}] lists {len(names)} authors (more than six: the first six and 'et al.')"]
    return []


def page_problems(n: int, pages: str) -> list[str]:
    """A page range shortened as in the guide ('312–9'): repeated leading digits dropped."""
    m = re.fullmatch(r"([A-Za-z]?)(\d+)(?:–([A-Za-z]?)(\d+))?", pages)
    if not m:
        return [f"REFERENCES: [{n}] pages {pages!r} not as in the guide"]
    if not m.group(4):
        return []
    a, b = m.group(2), m.group(4)
    if m.group(3) or len(b) > len(a):
        return [f"REFERENCES: [{n}] page range {pages!r} not shortened as in the guide (312–9)"]
    full = a[:len(a) - len(b)] + b
    common = 0
    for x, y in zip(a, full):
        if x != y:
            break
        common += 1
    if int(full) <= int(a) or len(b) != len(a) - common:
        return [f"REFERENCES: [{n}] page range {pages!r} not shortened as in the guide (312–9)"]
    return []


def reference_dois(ms_dir: Path) -> dict[str, str]:
    p = ms_dir / "reference_dois.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


def reference_problems(refs: list[tuple[int, str]], ms_dir: Path) -> list[str]:
    out = []
    dois = reference_dois(ms_dir)
    for k, e in refs:
        kind = entry_kind(e)
        if kind == "unknown":
            out.append(f"REFERENCES: [{k}] is not in the journal's style (article with DOI, web page with access date, "
                       f"or Zenodo record with version)")
            continue
        if kind == "article":
            m = ARTICLE.search(e)
            if dois.get(str(k)) != m.group("doi"):
                out.append(f"REFERENCES: [{k}] DOI {m.group('doi')} is not the verified DOI in reference_dois.json "
                           f"({dois.get(str(k))})")
            out += page_problems(k, m.group("pages"))
        if kind == "zenodo" and "zenodo.X" in e and not e.startswith("[dataset] "):
            out.append(f"REFERENCES: [{k}] the study's data must be cited with [dataset]")
        out += author_problems(k, e)
    articles = {str(k) for k, e in refs if entry_kind(e) == "article"}
    extra = sorted(set(dois) - articles, key=int)
    if extra:
        out.append(f"REFERENCES: reference_dois.json holds DOIs for entries that are not articles: {extra}")
    return out


# --------------------------------------------------------------------------------------
# Word counts: the placeholders of the title page and the cover letter
# --------------------------------------------------------------------------------------
def counts(ms_dir: Path) -> dict | None:
    p = ms_dir / "word_counts_word.json"
    if not p.exists():
        return None
    w = json.loads(p.read_text(encoding="utf-8"))
    return w if "dmscrr_total" in w else None


def n_references(ms_text: str) -> int:
    part = ms_text.split("\n## References", 1)
    if len(part) != 2:
        return 0
    return len(REF_LINE.findall(part[1].split("\n## ", 1)[0]))


def fill_counts(text: str, ms_dir: Path) -> str:
    """The word-count placeholders filled from word_counts_word.json (left as they are when the
    counts are absent, so that the tie then fails)."""
    w = counts(ms_dir)
    if w is None:
        return text
    ms = (ms_dir / "manuscript.md").read_text(encoding="utf-8")
    val = {"abstract": w["abstract"], "main": w["main_with_headings"], "display": w["display_words"],
           "total": w["dmscrr_total"], "references": n_references(ms)}
    return PLACEHOLDER.sub(lambda m: f"{val[m.group(1)]:,}", text)
