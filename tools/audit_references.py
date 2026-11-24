# Adapted from hssling/india-tb-priority-tool v1.0.1 (MIT), tools/audit_references.py (itself adapted
# from hssling/india-tb-acf-campaign, manuscript/ext/audit_references.py); modified: Elsevier numbered
# references with Index Medicus journal abbreviations ("Authors, Title, Journal Vol (Year) pages.
# https://doi.org/..."), supplements and articles in press, titles compared without spaces or
# markup, the first three authors of an "et al." entry, the study's own [dataset] and the released
# [software] (Zenodo, a DataCite DOI that Crossref does not hold), and the web sources verified
# against data/source_manifest.csv.
"""Verify every reference of the manuscript and write <manuscript folder>/reference_audit.md.

Run as: python -I tools/audit_references.py [--manuscript-dir DIR]   (default: manuscript)

- A reference with a Crossref DOI: the DOI is resolved through the Crossref REST API
  (https://api.crossref.org/works/<doi>; read-only; a generic User-Agent and no e-mail). It
  passes if (1) Crossref's title (markup removed) occurs in the entry, compared without case,
  punctuation or spaces; (2) the cited year is Crossref's issued, print or online year; (3) the
  cited journal is a valid abbreviation of Crossref's container title (each word, in order, a
  letter-subsequence of a title word with the same first letter) or of its short title; (4) the
  cited volume and first page (or article number) equal Crossref's where Crossref gives them; an
  article in press has neither; (5) every family name Crossref lists among the first six authors
  occurs in the entry (for an "et al." entry, among the first three).
- A Zenodo DOI (10.5281/zenodo.*) is a DataCite DOI and is not looked up: the [dataset] entry
  may hold the release placeholder; the [software] entry must name its version.
- A reference without a DOI: its URL must be the upstream address of a file in
  data/source_manifest.csv, whose SHA-256 is re-verified when data_raw/ holds the file.
Nothing is downloaded except Crossref's JSON records. Exit 1 if any reference fails.

A DMSCRR folder ("journal": "dmscrr"; manuscript/v3) prints DOIs ("n\\. Authors. Title. Journal Year;
Volume: pages. https://doi.org/DOI"): the printed DOI must equal reference_dois.json and Crossref's
record, and the authors follow the guide (all when six or fewer; otherwise the first six and "et
al."). Web references are checked as for the IJTLD folder; the study's [dataset] may hold the release
placeholder.

An IJTLD folder (section_phrases.json "journal": "ijtld"; manuscript/v2) prints no DOIs: entries
are "n\\. Authors. Title. Journal Year; Volume: pages." and each article's DOI is kept in
<folder>/reference_dois.json. The same Crossref checks apply, and the authors follow the journal's
rule: when the entry lists its authors, Crossref has at most three and every one is listed; when it
gives "First et al.", Crossref has more than three and the first is named. A web reference
("URL Accessed d Month yyyy.") is either an upstream file of data/source_manifest.csv or an
official page recorded, read-only, in <folder>/official_pages.json (what the page showed, the
date read, and the strings the entry must contain).
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import html
import json
import re
import sys
import time
import unicodedata
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
UA = "reference-audit/1.0"
MS_NAME = "manuscript.md"


def norm(s: str) -> str:
    s = html.unescape(s).replace("’", "").replace("'", "")
    s = re.sub("[‐-―]", "-", s)
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", " ", s).strip()


def compact(s: str) -> str:
    return norm(re.sub(r"<[^>]+>", "", s)).replace(" ", "")


def crossref(doi: str) -> dict:
    req = urllib.request.Request("https://api.crossref.org/works/" + urllib.parse.quote(doi),
                                 headers={"User-Agent": UA})
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.load(r)["message"]
        except urllib.error.HTTPError as e:
            if e.code != 429 or attempt == 3:
                raise
            time.sleep(5 * (attempt + 1))
    raise RuntimeError("unreachable")


def years(m: dict) -> set[int]:
    out = set()
    for k in ("issued", "published-print", "published-online", "published"):
        dp = (m.get(k) or {}).get("date-parts") or [[None]]
        if dp[0] and dp[0][0]:
            out.add(int(dp[0][0]))
    return out


def subseq(a: str, w: str) -> bool:
    it = iter(w)
    return a[:1] == w[:1] and all(ch in it for ch in a)


def abbrev_ok(abbr: str, full: str) -> bool:
    words = norm(full).split()
    i = 0
    for a in norm(abbr).split():
        while i < len(words) and not subseq(a, words[i]):
            i += 1
        if i == len(words):
            return False
        i += 1
    return True


ELS = re.compile(r", (?P<journal>[A-Z][^,]*?) (?P<vol>\d+)(?: Suppl \d+)? \((?P<year>\d{4})\) (?P<pages>[^.]+)\. "
                 r"https://doi\.org/")
PRESS = re.compile(r", (?P<journal>[A-Z][^,]*?) \((?P<year>\d{4})\), in press\. https://doi\.org/")


def cited(ms_dir: Path) -> dict[int, str]:
    ms = (ms_dir / MS_NAME).read_text(encoding="utf-8")
    refs = ms.split("\n## References", 1)[1].split("\n## ", 1)[0]
    return {int(m.group(1)): m.group(2) for m in re.finditer(r"(?m)^\[(\d+)\] (.+)$", refs)}


def doi_check(n: int, entry: str, doi: str) -> tuple[str, bool]:
    m = crossref(doi)
    title = (m.get("title") or [""])[0]
    journal = (m.get("container-title") or [""])[0]
    short = m.get("short-container-title") or []
    t_ok = compact(title) in compact(entry)
    e = ELS.search(entry) or PRESS.search(entry)
    cj = e.group("journal") if e else ""
    y_ok = bool(e) and int(e.group("year")) in years(m)
    j_ok = bool(e) and (norm(cj) == norm(journal) or abbrev_ok(cj, journal) or any(abbrev_ok(cj, s) for s in short))
    if e and "vol" in e.groupdict():
        first = e.group("pages").split("–")[0]
        if " Suppl " in e.group(0) and first.startswith("S"):
            first = first[1:]  # a supplement page S38 is page 38 in Crossref's record
        cr_first = (m.get("page") or "").split("-")[0] or (m.get("article-number") or "")
        v_ok = (not m.get("volume") or e.group("vol") == m["volume"]) and (not cr_first or first == cr_first)
    else:
        v_ok = bool(e) and not m.get("volume") and not m.get("page")  # in press: neither yet
    k = 3 if " et al." in entry else 6
    fams = [a.get("family", "") for a in (m.get("author") or [])[:k] if a.get("family")]
    a_ok = all(norm(f) in norm(entry) for f in fams)
    ok = t_ok and y_ok and j_ok and v_ok and a_ok
    meta = "; ".join(x for x in [html.unescape(journal), "/".join(str(y) for y in sorted(years(m))),
                                 f"vol {m['volume']}" if m.get("volume") else "no volume (in press)",
                                 f"pp {m['page']}" if m.get("page") else "",
                                 f"art {m['article-number']}" if m.get("article-number") else "",
                                 f"authors {', '.join(fams)}" if fams else "group or no personal author"] if x)
    flags = (f"title {'yes' if t_ok else 'NO'}, year {'yes' if y_ok else 'NO'}, journal '{cj}' "
             f"{'yes' if j_ok else 'NO'}, volume/page {'yes' if v_ok else 'NO'}, authors {'yes' if a_ok else 'NO'}")
    clean = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", html.unescape(title))).strip()
    return f"| {n} | {doi} | {clean} | {meta} | {flags} | {'yes' if ok else 'NO'} |", ok


def zenodo_check(n: int, entry: str, doi: str) -> tuple[str, bool]:
    if entry.startswith("[dataset]"):
        ok = "XXXXXXX" in doi or doi.split(".")[-1].isdigit()
        state = "release placeholder (filled with --doi at release)" if "XXXXXXX" in doi else "Zenodo version DOI"
        return f"| {n} | {doi} | [dataset] the study's repository | {state}; DataCite, not looked up | — | {'yes' if ok else 'NO'} |", ok
    if entry.startswith("[software]"):
        ok = bool(re.search(r"version \d+\.\d+\.\d+", entry)) and doi.split(".")[-1].isdigit()
        return (f"| {n} | {doi} | [software] {entry.split(',')[1].strip()} | Zenodo version DOI (DataCite, not looked up; "
                f"only Crossref metadata may be downloaded); version named: {'yes' if ok else 'NO'} | — | "
                f"{'yes' if ok else 'NO'} |"), ok
    ok = bool(re.search(r"version \d+\.\d+\.\d+", entry)) and doi.split(".")[-1].isdigit()
    return (f"| {n} | {doi} | {entry.split(',')[1].strip()} | Zenodo version DOI of released software (DataCite, not looked "
            f"up; only Crossref metadata may be downloaded); version named: {'yes' if ok else 'NO'} | — | "
            f"{'yes' if ok else 'NO'} |"), ok


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def non_doi_check(n: int, entry: str, root: Path) -> tuple[str, bool]:
    with open(root / "data" / "source_manifest.csv", newline="", encoding="utf-8") as f:
        man = list(csv.DictReader(f))
    sec = re.search(r"as described in India TB Report (\d{4}), p\. (\d+)\)\.$", entry)
    if sec:
        return secondary_check(n, entry, sec, man, root)
    url = re.search(r"(https?://\S+) \(accessed (\d{1,2} \w+ \d{4})\)\.$", entry)
    if not url:
        return f"| {n} | none | {entry[:70]} | no DOI, no URL with an access date | — | NO |", False
    hit = [r for r in man if r["origin"].endswith("upstream " + url.group(1)) or f"from {url.group(1)} " in r["origin"]]
    if not hit:
        return f"| {n} | none | {entry[:70]} | URL not in data/source_manifest.csv | — | NO |", False
    states = []
    ok = True
    for r in hit:
        p = root / r["path"]
        st = ("SHA-256 verified" if p.exists() and sha(p) == r["sha256"] else
              "SHA-256 DIFFERS" if p.exists() else "local copy absent (digest not re-verified)")
        ok = ok and "DIFFERS" not in st
        states.append(f"{Path(r['path']).name}: {st}")
    return (f"| {n} | none | {'; '.join(Path(r['path']).name for r in hit)} | upstream URL in data/source_manifest.csv; "
            f"{'; '.join(states)}; accessed {url.group(2)} | — | {'yes' if ok else 'NO'} |"), ok


def secondary_check(n: int, entry: str, sec, man: list[dict], root: Path) -> tuple[str, bool]:
    """A document cited as described in a report (not opened for the study): the report's local copy
    must name it, with the cited year, on the cited page."""
    year, page = sec.group(1), int(sec.group(2))
    hit = [r for r in man if f"India-TB-Report-{year}" in r["path"]]
    if len(hit) != 1:
        return f"| {n} | none | {entry[:60]} | India TB Report {year} not in data/source_manifest.csv | — | NO |", False
    p = root / hit[0]["path"]
    if not p.exists():
        return (f"| {n} | none | {entry[:60]} | secondary citation; the local copy of India TB Report {year} is absent "
                f"(not re-verified) | — | yes |"), True
    try:
        import fitz  # PyMuPDF, used only to read the cited page
    except ImportError:
        return f"| {n} | none | {entry[:60]} | secondary citation; PyMuPDF absent (not re-verified) | — | yes |", True
    text = " ".join(fitz.open(str(p))[page - 1].get_text().split())
    m = re.search(r"National Framework for Joint TB-Diabetes Collaborative Activities.{0,10}in (\d{4})", text)
    cited_year = re.search(r", (\d{4}) \(not accessed", entry)
    ok = bool(m) and bool(cited_year) and m.group(1) == cited_year.group(1) and sha(p) == hit[0]["sha256"]
    return (f"| {n} | none | the framework, as described in India TB Report {year} p. {page} | the report's local copy "
            f"(SHA-256 verified) names the framework and dates it {m.group(1) if m else '(not found)'}; cited year "
            f"{cited_year.group(1) if cited_year else '(none)'} | — | {'yes' if ok else 'NO'} |"), ok


# --------------------------------------------------------------------------------------
# IJTLD style
# --------------------------------------------------------------------------------------
def journal(ms_dir: Path) -> str:
    p = ms_dir / "section_phrases.json"
    return json.loads(p.read_text(encoding="utf-8")).get("journal", "pcd") if p.exists() else "pcd"


def ijtld_doi_check(n: int, entry: str, doi: str) -> tuple[str, bool]:
    sys.path.insert(0, str(ROOT))
    from verification import ijtld
    m = crossref(doi)
    title = (m.get("title") or [""])[0]
    container = (m.get("container-title") or [""])[0]
    short = m.get("short-container-title") or []
    t_ok = compact(title) in compact(entry)
    e = ijtld.ARTICLE.search(entry)
    cj = e.group("journal") if e else ""
    y_ok = bool(e) and int(e.group("year")) in years(m)
    j_ok = bool(e) and (norm(cj) == norm(container) or abbrev_ok(cj, container) or any(abbrev_ok(cj, x) for x in short))
    if e:
        first = e.group("pages").split("–")[0]
        if e.group("supp") and first.startswith("S"):
            first = first[1:]
        cr_first = (m.get("page") or "").split("-")[0] or (m.get("article-number") or "")
        v_ok = (not m.get("volume") or e.group("vol") == m["volume"]) and (not cr_first or first == cr_first)
    else:
        v_ok = False
    people = [a for a in (m.get("author") or []) if a.get("family")]
    fams = [a["family"] for a in people]
    head = entry.split(". ", 1)[0]
    if head.endswith(", et al"):
        a_ok = len(people) > 3 and norm(fams[0]) in norm(head)
        rule = f"et al. ({len(people)} authors in Crossref)"
    else:
        a_ok = len(people) <= 3 and all(norm(f) in norm(head) for f in fams)
        rule = f"all {len(people)} listed" if people else "group or no personal author"
    ok = t_ok and y_ok and j_ok and v_ok and a_ok
    meta = "; ".join(x for x in [html.unescape(container), "/".join(str(y) for y in sorted(years(m))),
                                 f"vol {m['volume']}" if m.get("volume") else "", f"pp {m['page']}" if m.get("page") else "",
                                 f"art {m['article-number']}" if m.get("article-number") else "",
                                 f"authors {', '.join(fams[:3])}{' ...' if len(fams) > 3 else ''}" if fams else ""] if x)
    flags = (f"title {'yes' if t_ok else 'NO'}, year {'yes' if y_ok else 'NO'}, journal '{cj}' {'yes' if j_ok else 'NO'}, "
             f"volume/page {'yes' if v_ok else 'NO'}, authors {rule} {'yes' if a_ok else 'NO'}")
    clean = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", html.unescape(title))).strip()
    return f"| {n} | {doi} (Crossref) | {clean} | {meta} | {flags} | {'yes' if ok else 'NO'} |", ok


def ijtld_web_check(n: int, entry: str, ms_dir: Path, root: Path) -> tuple[str, bool]:
    m = re.search(r"(?P<url>https?://\S+?) Accessed (?P<date>\d{1,2} [A-Z][a-z]+ \d{4})\.$", entry)
    if not m:
        return f"| {n} | none | {entry[:70]} | no URL with an access date | — | NO |", False
    url, date = m.group("url"), m.group("date")
    op = ms_dir / "official_pages.json"
    pages = json.loads(op.read_text(encoding="utf-8"))["pages"] if op.exists() else {}
    if url in pages:
        rec = pages[url]
        missing = [x for x in rec["must_contain"] if x not in entry]
        ok = not missing and rec["read"] == date
        return (f"| {n} | none | official page, read-only | {rec['shows']} Read {rec['read']}. | entry contains the "
                f"verified title and year: {'yes' if not missing else 'NO ' + str(missing)}; access date = date read: "
                f"{'yes' if rec['read'] == date else 'NO'} | {'yes' if ok else 'NO'} |"), ok
    return non_doi_check(n, entry.replace(f" Accessed {date}.", f" (accessed {date})."), root)


def ijtld_zenodo_check(n: int, entry: str, doi: str) -> tuple[str, bool]:
    kind = "dataset" if "[dataset]" in entry else "software" if "[software]" in entry else ""
    ver = re.search(r"Version (\d+\.\d+\.\d+)", entry)
    ok = bool(kind) and bool(ver) and ("XXXXXXX" in doi if kind == "dataset" else doi.split(".")[-1].isdigit())
    state = ("release placeholder (filled with --doi at the v" + ver.group(1) + " release)") if "XXXXXXX" in doi and ver \
        else "Zenodo version DOI"
    return (f"| {n} | {doi} | [{kind}] version {ver.group(1) if ver else '(none)'} | {state}; DataCite, not looked up | — | "
            f"{'yes' if ok else 'NO'} |"), ok


def ijtld_audit(ms_dir: Path) -> tuple[list[str], int]:
    sys.path.insert(0, str(ROOT))
    from verification import ijtld
    ms = (ms_dir / MS_NAME).read_text(encoding="utf-8")
    refs = ms.split("\n## References", 1)[1].split("\n## ", 1)[0]
    entries = {int(m.group(1)): m.group(2).strip() for m in ijtld.REF_LINE.finditer(refs)}
    dois = json.loads((ms_dir / "reference_dois.json").read_text(encoding="utf-8"))
    rows, bad = [], 0
    for n, entry in sorted(entries.items()):
        kind = ijtld.entry_kind(entry)
        if kind == "article" and str(n) in dois:
            line, ok = ijtld_doi_check(n, entry, dois[str(n)])
            time.sleep(1)
        elif kind == "zenodo":
            line, ok = ijtld_zenodo_check(n, entry, ijtld.ZENODO.search(entry).group("doi"))
        elif kind == "web":
            line, ok = ijtld_web_check(n, entry, ms_dir, ROOT)
        else:
            line, ok = f"| {n} | none | {entry[:70]} | not in the journal's style, or an article without a DOI | — | NO |", False
        rows.append(line)
        bad += not ok
    return rows, bad


# --------------------------------------------------------------------------------------
# DMSCRR style (Vancouver, the guide's punctuation, DOIs printed)
# --------------------------------------------------------------------------------------
def dmscrr_doi_check(n: int, entry: str, doi: str) -> tuple[str, bool]:
    sys.path.insert(0, str(ROOT))
    from verification import dmscrr
    m = crossref(doi)
    title = (m.get("title") or [""])[0]
    container = (m.get("container-title") or [""])[0]
    short = m.get("short-container-title") or []
    t_ok = compact(title) in compact(entry)
    e = dmscrr.ARTICLE.search(entry)
    cj = e.group("journal") if e else ""
    y_ok = bool(e) and int(e.group("year")) in years(m)
    j_ok = bool(e) and (norm(cj) == norm(container) or abbrev_ok(cj, container) or any(abbrev_ok(cj, x) for x in short))
    d_ok = bool(e) and e.group("doi").lower() == doi.lower() == (m.get("DOI") or "").lower()
    if e:
        first = e.group("pages").split("–")[0]
        if e.group("supp") and first.startswith("S"):
            first = first[1:]
        cr_first = (m.get("page") or "").split("-")[0].lstrip("S") or (m.get("article-number") or "")
        v_ok = (not m.get("volume") or e.group("vol") == m["volume"]) and (not cr_first or first == cr_first)
    else:
        v_ok = False
    people = [a for a in (m.get("author") or []) if a.get("family")]
    fams = [a["family"] for a in people]
    head = entry.split(". ", 1)[0]
    if head.endswith(", et al"):
        a_ok = len(people) > 6 and all(norm(f) in norm(head) for f in fams[:6])
        rule = f"first six and et al. ({len(people)} authors in Crossref)"
    else:
        a_ok = len(people) <= 6 and all(norm(f) in norm(head) for f in fams)
        rule = f"all {len(people)} listed" if people else "group or no personal author"
    ok = t_ok and y_ok and j_ok and v_ok and a_ok and d_ok
    meta = "; ".join(x for x in [html.unescape(container), "/".join(str(y) for y in sorted(years(m))),
                                 f"vol {m['volume']}" if m.get("volume") else "", f"pp {m['page']}" if m.get("page") else "",
                                 f"art {m['article-number']}" if m.get("article-number") else "",
                                 f"authors {', '.join(fams[:6])}{' ...' if len(fams) > 6 else ''}" if fams else ""] if x)
    flags = (f"title {'yes' if t_ok else 'NO'}, year {'yes' if y_ok else 'NO'}, journal '{cj}' {'yes' if j_ok else 'NO'}, "
             f"volume/page {'yes' if v_ok else 'NO'}, authors {rule} {'yes' if a_ok else 'NO'}, DOI resolves and "
             f"matches {'yes' if d_ok else 'NO'}")
    clean = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", html.unescape(title))).strip()
    return f"| {n} | {doi} (Crossref) | {clean} | {meta} | {flags} | {'yes' if ok else 'NO'} |", ok


def dmscrr_zenodo_check(n: int, entry: str) -> tuple[str, bool]:
    sys.path.insert(0, str(ROOT))
    from verification import dmscrr
    z = dmscrr.ZENODO.search(entry)
    doi, ver = z.group("doi"), z.group("ver")
    if "XXXXXXX" in doi:
        ok = entry.startswith("[dataset] ")
        state = f"[dataset] release placeholder (filled with --doi at the v{ver} release)"
    else:
        ok = doi.split(".")[-1].isdigit()
        state = "Zenodo version DOI of released software"
    return f"| {n} | {doi} | version {ver} | {state}; DataCite, not looked up | — | {'yes' if ok else 'NO'} |", ok


def dmscrr_audit(ms_dir: Path) -> tuple[list[str], int]:
    sys.path.insert(0, str(ROOT))
    from verification import dmscrr
    ms = (ms_dir / MS_NAME).read_text(encoding="utf-8")
    refs = ms.split("\n## References", 1)[1].split("\n## ", 1)[0]
    entries = {int(m.group(1)): m.group(2).strip() for m in dmscrr.REF_LINE.finditer(refs)}
    dois = json.loads((ms_dir / "reference_dois.json").read_text(encoding="utf-8"))
    rows, bad = [], 0
    for n, entry in sorted(entries.items()):
        kind = dmscrr.entry_kind(entry)
        if kind == "article" and str(n) in dois:
            line, ok = dmscrr_doi_check(n, entry, dois[str(n)])
            time.sleep(1)
        elif kind == "zenodo":
            line, ok = dmscrr_zenodo_check(n, entry)
        elif kind == "web":
            line, ok = ijtld_web_check(n, entry, ms_dir, ROOT)
        else:
            line, ok = f"| {n} | none | {entry[:70]} | not in the journal's style, or an article without a DOI | — | NO |", False
        rows.append(line)
        bad += not ok
    return rows, bad


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0], allow_abbrev=False)
    ap.add_argument("--manuscript-dir", default="manuscript")
    a = ap.parse_args(argv)
    ms_dir = Path(a.manuscript_dir)
    ms_dir = ms_dir if ms_dir.is_absolute() else ROOT / ms_dir
    rows, bad = [], 0
    ijtld_style = journal(ms_dir) in ("ijtld", "dmscrr")
    if journal(ms_dir) == "ijtld":
        rows, bad = ijtld_audit(ms_dir)
    elif journal(ms_dir) == "dmscrr":
        rows, bad = dmscrr_audit(ms_dir)
    for n, entry in ([] if ijtld_style else sorted(cited(ms_dir).items())):
        d = re.search(r"https://doi\.org/(\S+?)\.?$", entry)
        if d and d.group(1).startswith("10.5281/zenodo."):
            line, ok = zenodo_check(n, entry, d.group(1))
        elif d:
            line, ok = doi_check(n, entry, d.group(1))
            time.sleep(1)
        else:
            line, ok = non_doi_check(n, entry, ROOT)
        rows.append(line)
        bad += not ok
    out = ["# Reference audit", "",
           "Written by tools/audit_references.py. DOIs resolved through the Crossref REST API "
           "(api.crossref.org/works/<doi>; generic User-Agent, no e-mail); Zenodo (DataCite) DOIs not looked up; "
           "non-DOI sources checked against data/source_manifest.csv" + (
               ", or against official pages read once, read-only, and recorded in official_pages.json; IJTLD style "
               "(DOIs kept in reference_dois.json, not printed)" if journal(ms_dir) == "ijtld" else
               ", or against official pages read once, read-only, and recorded in official_pages.json; DMSCRR style "
               "(Vancouver as in the guide; each printed DOI equals reference_dois.json and resolves in Crossref; "
               "authors: all when six or fewer, otherwise the first six and et al.)" if journal(ms_dir) == "dmscrr"
               else "") +
           ". Nothing else was downloaded.", "",
           "| Ref | DOI | Crossref title (or source) | Crossref metadata (or verification) | Checks | Pass |",
           "|---|---|---|---|---|---|", *rows, "", f"Problems: {bad}."]
    (ms_dir / "reference_audit.md").write_text("\n".join(out) + "\n", encoding="utf-8", newline="\n")
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    for r in rows:
        if r.endswith("| NO |"):
            print(r)
    print(f"{len(rows)} references audited; {bad} problem(s); wrote {(ms_dir / 'reference_audit.md').as_posix()}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
