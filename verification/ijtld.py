"""The IJTLD profile (International Journal of Tuberculosis and Lung Disease, Original Article):
the journal's hard limits and wording rules, shared by the build (tools/build_submission.py), the
number check (verification/check_manuscript_numbers.py), the docx tie (verification/
check_docx_tie.py), the mutation test and the reference audit.

A manuscript folder uses this profile when its section_phrases.json says "journal": "ijtld"
(manuscript/v2). Every rule here makes the checks FAIL when it is broken:

- main text (Introduction to Discussion, headings excluded) at most 2500 words;
- abstract at most 200 words, headed Background, Methods, Results and Conclusion, with no
  abbreviations and no citations;
- at most 35 references, cited as superscript numbers in order of first citation, in the
  journal's style (all authors when three or fewer, otherwise the first author and "et al.";
  "Journal Year; Volume: pages.");
- at most 3 display items (Table 1, Figures 1 and 2);
- a title of at most 110 characters with no abbreviations; a running head of at most 45
  characters; 3 to 5 keywords, none of whose words appears in the title;
- no "pre-registered" (the plan was time-stamped in a public repository before estimation);
- no stigmatising terms ("TB patients", "suspect", "defaulter") and no drafting-process words.
"""
from __future__ import annotations

import re

LIMITS = {"main": 2500, "abstract": 200, "references": 35, "display_items": 3, "title_chars": 110,
          "running_head_chars": 45, "keywords_min": 3, "keywords_max": 5}
ABSTRACT_PARTS = ("Background", "Methods", "Results", "Conclusion")
TABLES = [1]
FIGURES = [1, 2]
ONLINE_TABLES = [f"S{k}" for k in range(1, 16)]
ONLINE_FIGURES = ["S1", "S2"]
ONLINE_URL = "https://github.com/hssling/india-tb-diabetes-gap/tree/main/docs/online_material"

# The submission set (manuscript/v2/submission).
COVER = "01_cover_letter.docx"
MANUSCRIPT = "02_manuscript.docx"
DECLARATIONS = "03_declarations.docx"
FIGURE_FILES = {1: "Figure_1.tif", 2: "Figure_2.tif"}
TIFF_DPI = 600          # the journal: at least 300 dpi, preferably 500
MIN_DPI = 500
BUILD_RECORD = "build_record.json"   # in the manuscript folder: the figure sources and files of the last build
LINE_SPACINGS = (360, 480)           # 1.5 or double (twentieths of a point, w:line with lineRule auto)

# Abbreviations: two or more capitals in a word (TB, CI, NFHS-5, HbA1c, UT), a capital followed by a
# digit, or a lone capital letter used as a symbol (k, y aside, which are lower case).
ABBREV = re.compile(r"\b(?:[A-Za-z]*[A-Z][a-z]*[A-Z][A-Za-z0-9-]*|[A-Z]+\d[\w-]*)\b")
ALLOWED_CAPS = set()  # no exceptions: the abstract and title spell everything out

STIGMA = [
    (r"\b(?:TB|tuberculosis) patients?\b", "stigmatising: write 'people with TB' (person-first)"),
    (r"\bpatients? with (?:TB|tuberculosis)\b", "write 'people with TB' (person-first)"),
    (r"\bsuspects?\b", "stigmatising: 'suspect' (write 'people with presumptive TB')"),
    (r"\bdefault(?:er|ers|ed)\b", "stigmatising: 'defaulter' (write 'lost to follow-up')"),
    (r"\bdiabetics\b", "write 'people with diabetes'"),
]
PREREG = [(r"\bpre-?regist\w*", "not 'pre-registered': write 'an analysis plan time-stamped in a public repository "
                                "before estimation'")]
PROCESS = [(r"\breferee\w*|\breviewer\w*|\bmust-fix\b|\bSTRENGTHEN\b|\bdesk[- ]reject\w*|\bPrimary Care Diabetes\b"
            r"|\bPCD-[SD]-|\bresubmi\w*|\bearlier (?:version|submission)\b", "a drafting-process word")]
STOPWORDS = {"the", "a", "an", "of", "and", "in", "to", "for", "on", "at", "by", "with", "across", "beyond", "s"}


def abbreviations(text: str) -> list[str]:
    """Abbreviations in a text that must have none (the title, the abstract)."""
    text = re.sub(r"\*\*[^*]+:\*\*", " ", text)           # the run-in abstract headings
    return [m.group() for m in ABBREV.finditer(text) if m.group() not in ALLOWED_CAPS]


def content_words(s: str) -> set[str]:
    return {w for w in re.findall(r"[a-z]+", s.lower().replace("'s", "")) if w not in STOPWORDS}


def keyword_problems(keywords: list[str], title: str) -> list[str]:
    out = []
    if not LIMITS["keywords_min"] <= len(keywords) <= LIMITS["keywords_max"]:
        out.append(f"KEYWORDS: {len(keywords)} keywords ({LIMITS['keywords_min']} to {LIMITS['keywords_max']} required)")
    tw = content_words(title)
    for k in keywords:
        clash = content_words(k) & tw
        if clash:
            out.append(f"KEYWORDS: {k!r} repeats the title ({', '.join(sorted(clash))})")
    return out


def title_problems(title: str) -> list[str]:
    out = []
    if len(title) > LIMITS["title_chars"]:
        out.append(f"TITLE: {len(title)} characters including spaces, limit {LIMITS['title_chars']}")
    ab = abbreviations(title)
    if ab:
        out.append(f"TITLE: abbreviations {ab} (none allowed)")
    return out


def running_head_problems(head: str) -> list[str]:
    if not head:
        return ["TITLE PAGE: no running head"]
    if len(head) > LIMITS["running_head_chars"]:
        return [f"TITLE PAGE: running head {len(head)} characters, limit {LIMITS['running_head_chars']}"]
    return []


def wording_rules() -> list[tuple[str, str]]:
    return STIGMA + PREREG + PROCESS


def wording_hits(text: str) -> list[str]:
    out = []
    for pat, what in wording_rules():
        for m in re.finditer(pat, text, 0 if (pat, what) in PROCESS else re.I):
            out.append(f"{what}: {m.group()!r}")
    return out


# --------------------------------------------------------------------------------------
# The title page (title_page_src.md): "**Label:** value" lines
# --------------------------------------------------------------------------------------
def field(text: str, label: str) -> str | None:
    hits = [ln for ln in text.splitlines() if ln.startswith(f"**{label}:**")]
    return hits[0].split(":**", 1)[1].strip() if len(hits) == 1 else None


def keywords_of(title_page: str) -> list[str]:
    k = field(title_page, "Keywords") or ""
    return [x.strip().rstrip(".") for x in k.split(";") if x.strip()]


# --------------------------------------------------------------------------------------
# References: IJTLD style
# --------------------------------------------------------------------------------------
REF_LINE = re.compile(r"(?m)^(\d+)\\\. (.+)$")
CITE = re.compile(r"\^(\d+(?:[,–]\d+)*)\^")
# "Journal Year; Volume: pages." with an optional supplement "Volume (Suppl 1): S38–S42."
ARTICLE = re.compile(r"\. (?P<journal>[A-Z][^.;]*?) (?P<year>\d{4}); (?P<vol>\d+)(?: \((?P<supp>Suppl(?: \d+)?)\))?: "
                     r"(?P<pages>[^ .]+)\.$")
WEB = re.compile(r"(?P<url>https?://\S+?) Accessed (?P<date>\d{1,2} [A-Z][a-z]+ \d{4})\.$")
ZENODO = re.compile(r"https://doi\.org/(?P<doi>10\.5281/zenodo\.(?:\d+|X+))$")
AUTHOR = r"[A-Z][A-Za-z'’-]+(?: [A-Z][A-Za-z'’-]+)* [A-Z]{1,3}"


def author_problems(n: int, entry: str) -> list[str]:
    """All authors when three or fewer ("Brown LD, Cai TT, DasGupta A."), otherwise the first and
    'et al.'; a group or corporate author is one name."""
    head = entry.split(". ", 1)[0]
    if head.endswith(", et al"):
        names = head[:-len(", et al")].split(", ")
        if len(names) != 1:
            return [f"REFERENCES: [{n}] 'et al.' after {len(names)} authors (give only the first)"]
        return []
    names = head.split(", ")
    if len(names) > 3 and all(re.fullmatch(AUTHOR, x) for x in names):
        return [f"REFERENCES: [{n}] lists {len(names)} authors (more than three: first author and 'et al.')"]
    return []


def entry_kind(entry: str) -> str:
    if ZENODO.search(entry):
        return "zenodo"
    if WEB.search(entry):
        return "web"
    if ARTICLE.search(entry):
        return "article"
    return "unknown"
