#!/usr/bin/env python3
"""Generate source/article-02-data.json — the per-district data that drives the
native-Typst Article 2 renderer (source/article-02.typ).

For each of the 13 district spreads in docs/Newcastle Core Zoning Code.pdf we
read the verso (standards) page and the following recto (use-matrix) page, plus
the band metadata (code, name, band-text color, fill color) straight from the
PDF — nothing is hand-transcribed, so the ~8 hand-entry errors that plagued the
earlier D1 dict cannot recur.

Spread map (verso page index → recto = verso+1), from extract/map_districts.py:
  Core:    11 D1, 13 D2, 15 D3, 17 D4, 19 D5, 21 D6
  Special: 23 Historic, 25 Conservation, 27 Highway Commercial,
           29 Rural Highway, 31 Campus, 33 Marine, 35 Fabrication
"""
import fitz, json, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from verso import extract_verso
from recto import extract_recto

PDF = "docs/Newcastle Core Zoning Code.pdf"
VERSO_IDX = [11, 13, 15, 17, 19, 21, 23, 25, 27, 29, 31, 33, 35]

def hexcolor(fill):
    """fitz fill (r,g,b floats 0..1) -> '#RRGGBB'."""
    if fill is None:
        return None
    if isinstance(fill, (int, float)):
        v = int(fill)
        return f"#{v:06X}"
    return "#%02X%02X%02X" % tuple(max(0, min(255, round(c * 255))) for c in fill[:3])

def band_meta(pg):
    """Read code, name, band-text color from the two ~19pt band spans, and the
    band fill from the filled rectangle behind the badge."""
    big = []
    for blk in pg.get_text("dict")["blocks"]:
        for ln in blk.get("lines", []):
            for sp in ln.get("spans", []):
                if sp["text"].strip() == "":
                    continue
                if sp["size"] > 15 and 60 < sp["bbox"][1] < 110:
                    big.append((sp["bbox"][0], sp["text"].strip(), sp["color"]))
    big.sort()  # by x: leftmost = code (verso badge sits at fore-edge/left)
    code = big[0][1]
    name = " ".join(t for _, t, _ in big[1:])
    band_text = f"#{big[0][2]:06X}"
    # fill: a filled rect covering the badge area (x near left fore-edge, band y)
    fill = None
    for dr in pg.get_drawings():
        if not dr.get("fill"):
            continue
        r = dr["rect"]
        if r.x0 < 90 and 60 < r.y0 < 75 and (r.y1 - r.y0) > 30:
            fill = dr["fill"]
            break
    return code, name, band_text, hexcolor(fill)

def panelize(plist):
    """verso left/right panel list -> JSON-ready (kind body shape preserved)."""
    out = []
    for p in plist:
        out.append({"title": p["title"], "kind": p["kind"], "body": p["body"]})
    return out

def main():
    doc = fitz.open(PDF)
    districts = []
    for vidx in VERSO_IDX:
        verso_pg = doc[vidx]
        recto_pg = doc[vidx + 1]
        code, name, band_text, color = band_meta(verso_pg)
        group = "Special Zoning Districts" if code.upper() == "SD" else "Core Zoning Districts"
        left, right, matrix = extract_verso(verso_pg)
        use_col1, use_col2, use_standards = extract_recto(recto_pg)
        districts.append({
            "code": code,
            "name": name,
            "group": group,
            "color": color,
            "band_text": band_text,
            "left": panelize(left),
            "right": panelize(right),
            "matrix": matrix,            # dict {title,cols,rows} or None
            "use_col1": use_col1,
            "use_col2": use_col2,
            "use_standards": use_standards,
        })
        mx = "matrix" if matrix else "NO-matrix"
        print(f"  {code:<3} {name:<22} fill={color} text={band_text} "
              f"L={len(left)} R={len(right)} {mx} "
              f"u1={len(use_col1)} u2={len(use_col2)} std={len(use_standards['items'])}")
    out_path = "source/article-02-data.json"
    with open(out_path, "w") as f:
        json.dump(districts, f, ensure_ascii=False, indent=1)
    print(f"\nWrote {out_path}  ({len(districts)} districts)")

if __name__ == "__main__":
    main()
