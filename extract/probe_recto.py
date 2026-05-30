#!/usr/bin/env python3
"""Dump the D1 recto (index 12) text spans in reading order with x/y/font/color
so we can see (a) the 3-column structure and (b) how the status glyphs are
encoded — real chars (which font?) or absent (=> vectors)."""
import fitz

doc = fitz.open("docs/Newcastle Core Zoning Code.pdf")
pg = doc[12]
d = pg.get_text("dict")
spans = []
for blk in d.get("blocks", []):
    for ln in blk.get("lines", []):
        for sp in ln.get("spans", []):
            t = sp["text"]
            if t.strip() == "":
                continue
            spans.append((round(sp["bbox"][0], 1), round(sp["bbox"][1], 1),
                          round(sp["size"], 1), sp["font"], f"#{sp['color']:06X}", t))
# sort by x-band then y
spans.sort(key=lambda s: (s[0] // 150, s[1]))
for x, y, sz, font, col, t in spans:
    # flag any non-ascii (likely glyphs)
    nonascii = any(ord(ch) > 127 for ch in t)
    mark = "  <<GLYPH?" if nonascii else ""
    print(f"x={x:>5} y={y:>5} sz={sz:<4} {font:<26} {col} {t!r}{mark}")

print("\n--- vector drawings count (potential glyph marks) ---")
drs = pg.get_drawings()
print("total drawings:", len(drs))
# show small filled drawings (potential dots/glyphs) in the matrix area
for dr in drs:
    r = dr["rect"]
    w, h = r.x1 - r.x0, r.y1 - r.y0
    if dr.get("fill") and w < 12 and h < 12 and r.y0 > 120:
        print(f"  small fill at x={r.x0:.1f} y={r.y0:.1f} w={w:.1f} h={h:.1f} fill={dr['fill']}")
