#!/usr/bin/env python3
"""Dump verso (standards) spans grouped by column, to learn its structure."""
import fitz, sys

doc = fitz.open("docs/Newcastle Core Zoning Code.pdf")
pno = int(sys.argv[1]) if len(sys.argv) > 1 else 11
pg = doc[pno]
rows = []
for blk in pg.get_text("dict")["blocks"]:
    for ln in blk.get("lines", []):
        for sp in ln.get("spans", []):
            t = sp["text"]
            if t.strip() == "":
                continue
            rows.append((round(sp["bbox"][0], 1), round(sp["bbox"][1], 1),
                         round(sp["bbox"][2], 1), round(sp["size"], 1),
                         sp["font"], f"#{sp['color']:06X}", t))
# group into left (x<300) / right (300<=x<560) / full, exclude chrome
def zone(x, y):
    if y < 60 or y > 735:
        return "chrome"
    return "L" if x < 290 else "R"
for z in ("L", "R"):
    print(f"\n===== {z} COLUMN =====")
    sub = [r for r in rows if zone(r[0], r[1]) == z]
    sub.sort(key=lambda r: r[1])
    for x, y, x1, sz, font, col, t in sub:
        print(f"  x={x:>5} y={y:>5} sz={sz:<4} {font:<26} {col} {t!r}")
