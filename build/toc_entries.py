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
  * Type plates     — 19pt banner names (Article 3 only); the ten Street/Road
    Type pages (cross-section-plates.typ) carry the same banner chrome, matched
    against the Type names in source/exhibits/cross-sections/types.json and
    inserted as Article-3 sub-entries.

Page numbers are the body PDF's own printed numbers (the body numbers 1..N and
the front matter is unnumbered), so an entry's page == its 1-indexed page in
this PDF.

Usage:
  toc_entries.py BODY_PDF DATA_JSON OUT_JSON
"""
import json
import os
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

    # Physical page range [start, next_start) of an Article, used to confine the
    # banner-name scans below to their own Article. This matters because some
    # names collide across Articles: "HIGHWAY COMMERCIAL" and "RURAL HIGHWAY" are
    # both SD districts in Article 2 AND the R4 / R5 Street/Road Types in
    # Article 3. Without bounding, the first (Article-2) occurrence would steal
    # the Type's page. Returns None if the Article has no opener (no filtering).
    def art_range(n):
        for i, o in enumerate(openers):
            if o[0] == n:
                hi = openers[i + 1][2] if i + 1 < len(openers) else 10**9
                return (o[2], hi)
        return None

    r2 = art_range(2)
    r3 = art_range(3)

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
        if r2 and not (r2[0] <= page < r2[1]):
            continue  # only match district banners within Article 2's pages
        if sz >= BANNER_SZ and t in dnames and t not in dpage:
            dpage[t] = page  # first (verso) page of the spread
    districts = [(dpage[n], n) for n in dnames if n in dpage]

    # --- Street/Road Types (Article 3 plates): match Type names at banner size -
    # The ten native-Typst Type plates (cross-section-plates.typ) carry a 19pt
    # name banner identical in size to the Article-2 district banners. Match that
    # banner text against the Type names in types.json and file each as an
    # Article-3 sub-entry (page-ordered, nested after the "Street & Road Types"
    # section heading). The 19pt code badge ("S1" etc.) shares the banner size
    # but matches no name key, so it is harmlessly ignored.
    type_label = {}  # banner text ("MAIN STREET") -> TOC label ("S1 Main Street")
    types_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "..", "source", "exhibits", "cross-sections", "types.json")
    if os.path.exists(types_path):
        types_data = json.load(open(types_path))
        for k, v in types_data.items():
            if k.startswith("_"):
                continue
            nm = v.get("name", "").strip()
            if nm:
                type_label[nm.upper()] = (v.get("code", "") + " " + nm.title()).strip()
    tpage = {}
    for page, y, x, sz, col, t in spans:
        if r3 and not (r3[0] <= page < r3[1]):
            continue  # only match Type banners within Article 3's pages
        key = t.upper()
        if sz >= BANNER_SZ and key in type_label and key not in tpage:
            tpage[key] = page  # first page the Type's banner appears on
    type_entries = [(tpage[k], type_label[k]) for k in type_label if k in tpage]

    # --- Assemble: bucket sub-entries under their article by page range -------
    bounds = [(o[0], o[1], o[2]) for o in openers]
    starts = [b[2] for b in bounds] + [10**9]
    articles = []
    for i, (num, name, pg) in enumerate(bounds):
        lo, hi = starts[i], starts[i + 1]
        subs = [{"name": s_name, "page": s_pg}
                for (s_pg, s_name) in sections if lo <= s_pg < hi]
        # Article 2: merge in the district spreads, then order all by page.
        # Stable sort by page ONLY — `sections` is already in document order
        # (the scan walks pages top-to-bottom), so a page-key stable sort slots
        # the spread banners in by page while preserving the document order of
        # any two headings that share a page (a name tiebreak would reorder them
        # alphabetically, e.g. flipping §3 before §4 when both land on one page).
        if num == 2:
            subs += [{"name": d_name, "page": d_pg} for (d_pg, d_name) in districts]
            subs.sort(key=lambda e: e["page"])
        # Article 3: merge in the Street/Road Type plates, then order all by page.
        elif num == 3:
            subs += [{"name": t_name, "page": t_pg} for (t_pg, t_name) in type_entries]
            subs.sort(key=lambda e: e["page"])
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
