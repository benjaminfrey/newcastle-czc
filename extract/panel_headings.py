#!/usr/bin/env python3
"""List the bold #7C766F panel headings on each verso page, with column (L/R)
and y, to check whether all districts share one panel structure."""
import fitz

doc = fitz.open("docs/Newcastle Core Zoning Code.pdf")
versos = {11:"D1 RURAL",13:"D2 NBHD RES",15:"D3 NBHD BUS",17:"D4 VIL RES",
          19:"D5 VIL BUS",21:"D6 TOWN CTR",23:"SD HISTORIC",25:"SD CONSERV",
          27:"SD HWY COMM",29:"SD RURAL HWY",31:"SD CAMPUS",33:"SD MARINE",
          35:"SD FABRICATION"}

for pno in sorted(versos):
    pg = doc[pno]
    heads = []
    for blk in pg.get_text("dict")["blocks"]:
        for ln in blk.get("lines", []):
            for sp in ln.get("spans", []):
                if ("Bold" in sp["font"] and sp["color"] == 0x7C766F
                        and sp["size"] > 8.5 and 60 < sp["bbox"][1] < 735):
                    x = sp["bbox"][0]
                    heads.append((round(sp["bbox"][1]), "L" if x < 290 else "R",
                                  sp["text"].strip()))
    heads.sort()
    print(f"\n{versos[pno]} (idx {pno}):")
    for y, col, t in heads:
        print(f"   {col} y={y:<4} {t}")
