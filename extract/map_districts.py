#!/usr/bin/env python3
"""Map every district spread in the baseline CZC.

A district 'verso' (standards) page is identifiable by the big colored band
near the top: a square badge with the district code (D1..D6 or an SD code) and
a wide banner with the name in large (~19pt) NON-condensed type. The recto
(use-matrix) page repeats the same band.

Strategy: scan every page, pull the text 'dict', and look for large spans
(size > 15) near the top (y < 120) of the page. Those are the band's badge+name.
Record page index, the big-text strings, and sample the band fill color.
"""
import fitz
from PIL import Image
import io

doc = fitz.open("docs/Newcastle Core Zoning Code.pdf")
print(f"TOTAL PAGES: {doc.page_count}\n")

def band_color(pno):
    """Sample a pixel inside the band (badge area) at ~ (x=70, y=88) on a
    300dpi render -> but we sample the page pixmap at 150dpi for speed."""
    pg = doc[pno]
    pix = pg.get_pixmap(dpi=150)
    img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
    # band sits ~ y 67..108 pt; at 150dpi that's *150/72. Sample center-ish of
    # the banner (not the badge) to get the name's background.
    # verso: banner on the right of badge (x ~ 200pt). recto: banner on left.
    samples = {}
    for label, (xpt, ypt) in {
        "badge": (66, 88), "banner_L": (200, 88), "banner_R": (430, 88)
    }.items():
        x = int(xpt * 150 / 72); y = int(ypt * 150 / 72)
        if 0 <= x < img.width and 0 <= y < img.height:
            samples[label] = img.getpixel((x, y))
    return samples

found = []
for pno in range(doc.page_count):
    pg = doc[pno]
    d = pg.get_text("dict")
    bigs = []
    for blk in d.get("blocks", []):
        for ln in blk.get("lines", []):
            for sp in ln.get("spans", []):
                if sp["size"] > 15 and sp["bbox"][1] < 120:
                    txt = sp["text"].strip()
                    if txt:
                        bigs.append((round(sp["bbox"][0]), round(sp["bbox"][1]),
                                     round(sp["size"], 1), sp["font"], txt))
    if bigs:
        found.append((pno, bigs))

for pno, bigs in found:
    print(f"--- page index {pno} (1-based PDF p.{pno+1}) ---")
    for x, y, sz, font, txt in bigs:
        print(f"    x={x:>3} y={y:>3} sz={sz} {font:<28} {txt!r}")
    cols = band_color(pno)
    print(f"    colors: {cols}")
