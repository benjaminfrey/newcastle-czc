#!/usr/bin/env python3
"""Extract the recto (use-matrix) of a district spread:
  - 2 use columns of categories; each use row carries a Wingdings status glyph
    right-aligned at its column's right edge.
  - col3 = USE TABLE LEGEND + USE STANDARDS list (numbered, with nested a/b/c).

Glyph map (from the on-page legend, identical every district):
  =u (Use Permit, CEO)         =rc (Residential Companion, CEO)
  =sp (Special Permit, PB)     =ex (Expanded Use, PB)
"""
import fitz, sys, re, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from verso import parse_list, clean

WING = {"": "u", "": "rc", "": "sp", "": "ex"}

def spans(pg):
    out = []
    for blk in pg.get_text("dict")["blocks"]:
        for ln in blk.get("lines", []):
            for sp in ln.get("spans", []):
                if sp["text"] == "":
                    continue
                out.append(dict(x=sp["bbox"][0], y=sp["bbox"][1],
                                x1=sp["bbox"][2], sz=round(sp["size"], 1),
                                font=sp["font"], col=f"#{sp['color']:06X}",
                                t=sp["text"]))
    return out

def extract_recto(pg):
    S = spans(pg)
    # exclude chrome (header y<40, footer y>740, band y in 60..115)
    body = [s for s in S if 118 < s["y"] < 730]

    # --- glyphs: Wingdings spans -> (x,y,status) ---
    glyphs = [(s["x"], s["y"], WING.get(s["t"][0], "?")) for s in body
              if s["font"].startswith("Wingdings")]

    # --- category headings: bold #7C766F, size 8..9.5 ---
    def is_heading(s):
        return ("Bold" in s["font"] and s["col"] == "#7C766F"
                and 7.5 < s["sz"] < 9.6)
    heads = [s for s in body if is_heading(s)]

    LEGEND = "USE TABLE LEGEND"
    USESTD = "USE STANDARDS"
    # column 3 left edge: the legend heading x
    leg = [h for h in heads if LEGEND in h["t"]]
    col3_x = leg[0]["x"] if leg else 348
    col3_left = col3_x - 8

    # category headings that are real use-categories (left of col3, not legend/std)
    cats = [h for h in heads if h["x"] < col3_left
            and LEGEND not in h["t"] and USESTD not in h["t"].upper()]
    cats.sort(key=lambda h: (h["x"], h["y"]))

    # split categories into the two use columns by x-cluster
    xs = sorted(set(round(h["x"]) for h in cats))
    # cluster: col1 ~ 90s, col2 ~ 200s
    col1_cats = [h for h in cats if h["x"] < (col3_left + 90) / 2 - 30]  # placeholder
    # robust: 2 clusters by gap
    col_split = None
    if len(xs) >= 2:
        gaps = [(xs[i+1]-xs[i], (xs[i+1]+xs[i])/2) for i in range(len(xs)-1)]
        col_split = max(gaps)[1]
    else:
        col_split = 150
    col1_cats = sorted([h for h in cats if h["x"] < col_split], key=lambda h: h["y"])
    col2_cats = sorted([h for h in cats if h["x"] >= col_split], key=lambda h: h["y"])

    # --- use-name spans: Light #231F20 size~8.5, left of col3 ---
    def is_use(s):
        return ("Light" in s["font"] and s["col"] == "#231F20"
                and 8.0 < s["sz"] < 8.9 and s["x"] < col3_left
                and not re.match(r"^[a-z0-9]+\.", s["t"].strip()))
    uses = [s for s in body if is_use(s)]

    def col_of_x(x):
        return 1 if x < col_split else 2

    # name-x cluster centers (mode) for each use column
    def cluster_center(vals):
        from collections import Counter
        if not vals:
            return None
        c = Counter(round(v) for v in vals)
        return c.most_common(1)[0][0]
    x1 = cluster_center([u["x"] for u in uses if col_of_x(u["x"]) == 1])
    x2 = cluster_center([u["x"] for u in uses if col_of_x(u["x"]) == 2])
    # glyph bands: a column's status glyph is right-aligned at the column's right
    # edge, i.e. between this column's name-x and the NEXT column's name-x (or the
    # col3 legend for col2). This excludes legend/inline-note glyphs (x>=col3_left).
    gband = {
        1: ((x1 or 0) + 3, (x2 or col3_left) - 3),
        2: ((x2 or 0) + 3, col3_left - 3),
    }

    def nearest_glyph(name_y, this_col):
        lo, hi = gband[this_col]
        cands = [g for g in glyphs if lo < g[0] < hi and abs(g[1]-name_y) < 6]
        if not cands:
            return ""
        cands.sort(key=lambda g: abs(g[1]-name_y))
        return cands[0][2]

    def build_column(cat_heads, this_col):
        result = []
        ch = sorted(cat_heads, key=lambda h: h["y"])
        for i, h in enumerate(ch):
            y0 = h["y"]
            y1 = ch[i+1]["y"] if i+1 < len(ch) else 1e9
            rows = [u for u in uses
                    if col_of_x(u["x"]) == this_col and y0 < u["y"] < y1]
            rows.sort(key=lambda u: u["y"])
            entries = [(u["t"].strip(), nearest_glyph(u["y"], this_col)) for u in rows]
            result.append(dict(title=h["t"].strip(), entries=entries))
        return result

    use_col1 = build_column(col1_cats, 1)
    use_col2 = build_column(col2_cats, 2)

    # --- USE STANDARDS (col3 numbered list, nested a/b/c) ---
    us_heads = sorted([h for h in heads if USESTD in h["t"].upper()],
                      key=lambda h: h["y"])
    use_standards = {"title": None, "items": []}
    if us_heads:
        uh = us_heads[0]
        use_standards["title"] = clean(uh["t"])
        us_body = [dict(x=s["x"], y=s["y"], t=s["t"]) for s in body
                   if s["x"] >= col3_left and s["y"] > uh["y"] + 2
                   and not s["font"].startswith("Wingdings")
                   and "#7C766F" != s["col"]]
        if us_body:
            use_standards["items"] = parse_list(us_body)
    return use_col1, use_col2, use_standards

# NB: build_column / nearest_glyph are redefined inside extract_recto via the
# closure below; see the column-bounded version that supersedes the naive one.

if __name__ == "__main__":
    doc = fitz.open("docs/Newcastle Core Zoning Code.pdf")
    pno = int(sys.argv[1]) if len(sys.argv) > 1 else 12
    c1, c2, us = extract_recto(doc[pno])
    import pprint
    print("=== USE_COL1 ===")
    for c in c1:
        print(f"  [{c['title']}]")
        for n, s in c["entries"]:
            print(f"      {s or '·':<3} {n}")
    print("=== USE_COL2 ===")
    for c in c2:
        print(f"  [{c['title']}]")
        for n, s in c["entries"]:
            print(f"      {s or '·':<3} {n}")
    print(f"=== {us['title']} ===")
    for it in us["items"]:
        if isinstance(it, dict):
            print(f"  - {it['text']}")
            for s in it["sub"]:
                print(f"      . {s}")
        else:
            print(f"  - {it}")
