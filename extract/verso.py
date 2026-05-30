#!/usr/bin/env python3
"""Extract the verso (standards) page of a district spread into panels.

Layout grammar (MEASURED):
  - Two columns: LEFT label-x~48 / value-x~156 ; RIGHT label-x~309 / value-x~415.
  - Panels are bold #7C766F headings (size 9). Body runs from heading.y to the
    next heading.y in the SAME column.
  - Body kinds: "para" (DESCRIPTION), "list" (numbered, possibly nested a/b/c),
    "lv" (label/value pairs).
  - PERMITTED BUILDINGS is a full-width matrix spanning both columns; handled
    specially (variable column count).
Cross-references to other Articles are renumbered for the integrated draft:
  old 3->4 (Site), 4->5 (Building), 5->6 (Design), 6->7 (Use), 7->8 (Admin),
  8->9 (Definitions); Articles 1,2 unchanged; new Article 3 = Streets.
"""
import fitz, sys, re

RENUM = {1:1, 2:2, 3:4, 4:5, 5:6, 6:7, 7:8, 8:9}

def renum_articles(s):
    def repl(m):
        n = int(m.group(1))
        return f"Article {RENUM.get(n, n)}"
    return re.sub(r"Article (\d+)", repl, s)

def spans(pg):
    out = []
    for blk in pg.get_text("dict")["blocks"]:
        for ln in blk.get("lines", []):
            for sp in ln.get("spans", []):
                if sp["text"].strip() == "":
                    continue
                out.append(dict(x=round(sp["bbox"][0], 1), y=round(sp["bbox"][1], 1),
                                x1=round(sp["bbox"][2], 1), sz=round(sp["size"], 1),
                                font=sp["font"], col=sp["color"], t=sp["text"]))
    return out

def is_head(s):
    return ("Bold" in s["font"] and s["col"] == 0x7C766F and s["sz"] > 8.5
            and 60 < s["y"] < 735)

def clean(t):
    return renum_articles(re.sub(r"\s+", " ", t).strip())

MARKER = re.compile(r"^\s*([0-9]+|[a-z])\.\s*$")
MARKER_INLINE = re.compile(r"^\s*([0-9]+|[a-z])\.\s+(.*)$", re.S)

def parse_list(body):
    """body: list of span dicts (sorted by y). Returns list of items; a nested
    item becomes a dict {text, sub:[...]} else a plain string."""
    # Determine marker x (leftmost) and nested marker x (next cluster).
    xs = sorted(set(s["x"] for s in body if MARKER.match(s["t"]) or MARKER_INLINE.match(s["t"])))
    top_x = xs[0] if xs else None
    items = []           # list of [marker_level, text]
    cur = None
    cur_level = None
    for s in sorted(body, key=lambda s: (round(s["y"]), s["x"])):
        t = s["t"]
        m = MARKER.match(t)
        mi = MARKER_INLINE.match(t)
        if m or mi:
            # flush
            if cur is not None:
                items.append((cur_level, cur.strip()))
            lvl = 0 if abs(s["x"] - top_x) < 4 else 1
            cur = mi.group(2) if mi else ""
            cur_level = lvl
        else:
            if cur is None:
                # body text with no marker yet (shouldn't happen) -> start item
                cur = t; cur_level = 0
            else:
                cur += " " + t
    if cur is not None:
        items.append((cur_level, cur.strip()))
    # fold level-1 items under preceding level-0
    result = []
    for lvl, txt in items:
        txt = clean(txt)
        if lvl == 0:
            result.append({"text": txt, "sub": []})
        else:
            if result:
                result[-1]["sub"].append(txt)
            else:
                result.append({"text": txt, "sub": []})
    # simplify: if no subs anywhere, return list of strings
    if all(not it["sub"] for it in result):
        return [it["text"] for it in result]
    return result

def parse_lv(body, label_x):
    """label/value: labels near label_x, values at the right cluster."""
    # cluster x: labels (~label_x) vs values (label_x + big gap)
    rows = {}
    for s in sorted(body, key=lambda s: (s["y"], s["x"])):
        key = round(s["y"] / 6)  # bucket by row
        rows.setdefault(key, []).append(s)
    out = []
    for key in sorted(rows):
        cells = sorted(rows[key], key=lambda s: s["x"])
        # label = spans near label_x; value = spans far right
        labs = [c["t"] for c in cells if c["x"] < label_x + 70]
        vals = [c["t"] for c in cells if c["x"] >= label_x + 70]
        lab = clean(" ".join(labs))
        val = clean(" ".join(vals)) if vals else ""
        if lab:
            out.append((lab, val))
    return out

def classify(title, body, label_x):
    if any(MARKER.match(s["t"]) or MARKER_INLINE.match(s["t"]) for s in body):
        return "list"
    # lv if there exist value spans far to the right of label_x
    if any(s["x"] >= label_x + 70 for s in body):
        return "lv"
    return "para"

def extract_verso(pg):
    S = spans(pg)
    # drop the rotated white "ARTICLE N" tab (x~7, white) and the band text (size>15)
    body_spans = [s for s in S if 118 < s["y"] < 735 and s["x"] >= 42
                  and s["col"] != 0xFFFFFF and not (60 < s["y"] < 115 and s["sz"] > 15)]
    heads = sorted([s for s in body_spans if is_head(s)], key=lambda s: s["y"])

    # PERMITTED BUILDINGS heading (full width) — split point
    pb_head = next((h for h in heads if "PERMITTED BUILDING" in h["t"] and "GROUP" not in h["t"]), None)
    pb_y = pb_head["y"] if pb_head else 1e9

    def col_of(x): return "L" if x < 290 else "R"

    # panels above the matrix, per column
    def build_panels(zone, label_x):
        zh = [h for h in heads if col_of(h["x"]) == zone and h["y"] < pb_y - 1]
        zh = sorted(zh, key=lambda h: h["y"])
        panels = []
        for i, h in enumerate(zh):
            y0 = h["y"]
            y1 = zh[i+1]["y"] if i+1 < len(zh) else pb_y
            body = [s for s in body_spans if col_of(s["x"]) == zone
                    and not is_head(s) and y0 + 2 < s["y"] < y1 - 1]
            kind = classify(h["t"], body, label_x)
            if kind == "list":
                content = parse_list(body)
            elif kind == "lv":
                content = parse_lv(body, label_x)
            else:
                content = clean(" ".join(s["t"] for s in sorted(body, key=lambda s: s["y"])))
            panels.append({"title": clean(h["t"]), "kind": kind, "body": content})
        return panels

    left = build_panels("L", 47.9)
    right = build_panels("R", 308.9)

    # matrix
    matrix = None
    if pb_head:
        mb = [s for s in body_spans if s["y"] > pb_y + 2 and not is_head(s)]
        ys = sorted(set(round(s["y"]) for s in mb))
        if ys:
            # columns = clusters of value-span x (x>120), gap>40 starts a new col
            val_xs = sorted(s["x"] for s in mb if s["x"] > 120)
            col_x = []
            for x in val_xs:
                if not col_x or x - col_x[-1] > 40:
                    col_x.append(x)
                # else: same column (col_x[-1] stays the cluster's left edge)
            bounds = col_x + [1e9]

            def col_index(x):
                for i in range(len(col_x)):
                    if bounds[i] - 6 <= x < bounds[i+1] - 6:
                        return i
                return None

            def row_at(yy):
                cells = [s for s in mb if abs(s["y"] - yy) < 4]
                label = clean(" ".join(c["t"] for c in sorted(cells, key=lambda s: s["x"]) if c["x"] < 120))
                vals = [""] * len(col_x)
                for c in cells:
                    if c["x"] < 120:
                        continue
                    ci = col_index(c["x"])
                    if ci is not None:
                        vals[ci] = (vals[ci] + " " + c["t"]).strip()
                # baseline fills not-applicable matrix cells with a plain hyphen
                # (U+002D), not an em-dash — keep it for fidelity.
                vals = [("-" if v.strip() in ("-", "—", "") else clean(v)) for v in vals]
                return label, vals

            hdr_label, hdr_vals = row_at(ys[0])
            col_titles = hdr_vals
            rows = []
            for yy in ys[1:]:
                label, vals = row_at(yy)
                if label:
                    rows.append((label, *vals))
            matrix = {"title": clean(pb_head["t"]), "cols": col_titles, "rows": rows}

    return left, right, matrix

if __name__ == "__main__":
    doc = fitz.open("docs/Newcastle Core Zoning Code.pdf")
    pno = int(sys.argv[1]) if len(sys.argv) > 1 else 11
    left, right, matrix = extract_verso(doc[pno])
    def show(panels, name):
        print(f"===== {name} =====")
        for p in panels:
            print(f"  [{p['title']}]  ({p['kind']})")
            if p["kind"] == "lv":
                for lab, val in p["body"]:
                    print(f"      {lab:<32} | {val}")
            elif p["kind"] == "list":
                for it in p["body"]:
                    if isinstance(it, dict):
                        print(f"      - {it['text']}")
                        for s in it["sub"]:
                            print(f"          . {s}")
                    else:
                        print(f"      - {it}")
            else:
                print(f"      {p['body']}")
    show(left, "LEFT")
    show(right, "RIGHT")
    print("===== MATRIX =====")
    if matrix:
        print("  cols:", matrix["cols"])
        for r in matrix["rows"]:
            print("   ", r)
    else:
        print("  (none)")
