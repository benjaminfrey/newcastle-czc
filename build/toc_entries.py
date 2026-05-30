#!/usr/bin/env python3
"""Extract Table-of-Contents entries from a built CZC body PDF.

The TOC is derived from the rendered document, not hand-maintained, so it can
never drift from the content. It keys off the SAME visual signals the baseline
CZC's own TOC uses:

  * Article openers  — 33pt article-blue ("ARTICLE N" + name)
  * Section headings — 14pt article-blue ("N. NAME")  -> sub-entries
  * District spreads — 19pt banner names (Article 2 only); these render
    natively (article-02.typ) so they are matched against the known names in
    source/article-02-data.json and inserted as Article-2 sub-entries.

Page numbers are the body PDF's own printed numbers (the body numbers 1..N and
the front matter is unnumbered), so an entry's page == its 1-indexed page in
this PDF.

Usage:
  toc_entries.py BODY_PDF DATA_JSON OUT_JSON
"""
import json
import re
import sys

import fitz  # PyMuPDF

ARTICLE_BLUE = 0x367AAC
OPENER_SZ = (30.0, 35.0)
SECTION_SZ = (13.0, 15.0)
BANNER_SZ = 15.0  # district banner names render at ~19pt
NUM_PREFIX = re.compile(r"^\s*\d+\.\s*")
ARTICLE_RE = re.compile(r"^ARTICLE\s+(\d+)", re.I)


def _close(c, target=ARTICLE_BLUE, tol=18):
    return all(abs(((c >> s) & 255) - ((target >> s) & 255)) <= tol for s in (16, 8, 0))


def _spans(doc):
    """Yield (page1, y, x, size, color, text) for every non-empty span."""
    for pno in range(doc.page_count):
        for b in doc[pno].get_text("dict")["blocks"]:
            for line in b.get("lines", []):
                for s in line["spans"]:
                    t = s["text"].strip()
                    if t:
                        yield (pno + 1, round(s["bbox"][1], 1), round(s["bbox"][0], 1),
                               s["size"], s["color"], t)


def extract(body_pdf, data_json):
    doc = fitz.open(body_pdf)
    spans = list(_spans(doc))

    # --- Article openers (33pt blue): "ARTICLE N" then accumulate name spans ---
    openers = []  # (num:int, name:str, page:int)
    cur = None
    for page, y, x, sz, col, t in spans:
        if not (OPENER_SZ[0] <= sz <= OPENER_SZ[1] and _close(col)):
            continue
        m = ARTICLE_RE.match(t)
        if m:
            if cur:
                openers.append(cur)
            cur = [int(m.group(1)), "", page]
        elif cur is not None:
            cur[1] = (cur[1] + " " + t).strip()
    if cur:
        openers.append(cur)
    openers.sort(key=lambda o: o[2])

    # --- Section headings (14pt blue), merging wrapped continuation lines ------
    sections = []  # (page, text)
    cur_txt, cur_pg = None, None
    for page, y, x, sz, col, t in spans:
        if not (SECTION_SZ[0] <= sz <= SECTION_SZ[1] and _close(col)):
            continue
        if NUM_PREFIX.match(t):
            if cur_txt is not None:
                sections.append((cur_pg, cur_txt))
            cur_txt, cur_pg = NUM_PREFIX.sub("", t).strip(), page
        elif cur_txt is not None and page == cur_pg:
            # Only merge wrapped continuation lines on the SAME page. An
            # un-numbered blue heading on a later page (e.g. the Definitions
            # "DEFINITIONS ADDED FOR ARTICLE 3" divider) is NOT a continuation
            # of the previous numbered section and must not be appended.
            cur_txt = (cur_txt + " " + t).strip()
    if cur_txt is not None:
        sections.append((cur_pg, cur_txt))

    # --- Districts (Article 2 spreads): match known names at banner size ------
    districts_data = json.load(open(data_json))
    dnames = [d["name"] for d in districts_data]
    dpage = {}
    for page, y, x, sz, col, t in spans:
        if sz >= BANNER_SZ and t in dnames and t not in dpage:
            dpage[t] = page  # first (verso) page of the spread
    districts = [(dpage[n], n) for n in dnames if n in dpage]

    # --- Assemble: bucket sub-entries under their article by page range -------
    bounds = [(o[0], o[1], o[2]) for o in openers]
    starts = [b[2] for b in bounds] + [10**9]
    articles = []
    for i, (num, name, pg) in enumerate(bounds):
        lo, hi = starts[i], starts[i + 1]
        subs = [{"name": s_name, "page": s_pg}
                for (s_pg, s_name) in sections if lo <= s_pg < hi]
        # Article 2: merge in the district spreads, then order all by page.
        if num == 2:
            subs += [{"name": d_name, "page": d_pg} for (d_pg, d_name) in districts]
            subs.sort(key=lambda e: (e["page"], e["name"]))
        articles.append({"num": str(num), "name": name, "page": pg, "entries": subs})

    doc.close()
    return {"title": "TABLE OF CONTENTS", "articles": articles}


if __name__ == "__main__":
    if len(sys.argv) not in (3, 4):
        sys.exit("usage: toc_entries.py BODY_PDF DATA_JSON [OUT_JSON]")
    result = extract(sys.argv[1], sys.argv[2])
    if len(sys.argv) == 4:
        json.dump(result, open(sys.argv[3], "w"), indent=1)
    # Human-readable summary to stderr.
    for a in result["articles"]:
        print(f"ARTICLE {a['num']} {a['name']} .... {a['page']}  ({len(a['entries'])} entries)",
              file=sys.stderr)
