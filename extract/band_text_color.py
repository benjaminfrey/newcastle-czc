#!/usr/bin/env python3
"""Read the color of the 19pt band text (badge code + banner name) per district."""
import fitz

doc = fitz.open("docs/Newcastle Core Zoning Code.pdf")
spreads = [11, 13, 15, 17, 19, 21, 23, 25, 27, 29, 31, 33, 35]

def hexof(intcol):
    return f"#{intcol:06X}"

for pno in spreads:
    pg = doc[pno]
    d = pg.get_text("dict")
    seen = []
    for blk in d.get("blocks", []):
        for ln in blk.get("lines", []):
            for sp in ln.get("spans", []):
                if sp["size"] > 15 and sp["bbox"][1] < 120:
                    seen.append((sp["text"].strip(), hexof(sp["color"]), sp["font"]))
    print(f"p.idx {pno}: {seen}")
