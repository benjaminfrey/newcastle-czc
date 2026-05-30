#!/usr/bin/env python3
"""Extract exact band fill colors (badge vs banner) per district verso page
using vector drawings. The band is two filled rects in the y≈60..110 region:
a ~46pt-wide badge square at the fore edge and a wide banner beside it.
"""
import fitz

doc = fitz.open("docs/Newcastle Core Zoning Code.pdf")

# verso page index -> (code, name)
spreads = {
    11: ("D1", "RURAL"), 13: ("D2", "NEIGHBORHOOD RESIDENTIAL"),
    15: ("D3", "NEIGHBORHOOD BUSINESS"), 17: ("D4", "VILLAGE RESIDENTIAL"),
    19: ("D5", "VILLAGE BUSINESS"), 21: ("D6", "TOWN CENTER"),
    23: ("SD", "HISTORIC"), 25: ("SD", "CONSERVATION"),
    27: ("SD", "HIGHWAY COMMERCIAL"), 29: ("SD", "RURAL HIGHWAY"),
    31: ("SD", "CAMPUS"), 33: ("SD", "MARINE"), 35: ("SD", "FABRICATION"),
}

def hexof(c):
    if c is None:
        return None
    r, g, b = [int(round(v * 255)) for v in c]
    return f"#{r:02X}{g:02X}{b:02X}"

for pno in sorted(spreads):
    code, name = spreads[pno]
    pg = doc[pno]
    rects = []
    for dr in pg.get_drawings():
        f = dr.get("fill")
        if f is None:
            continue
        r = dr["rect"]
        # band region: top y in 55..115, with appreciable width & height
        if r.y0 > 55 and r.y0 < 115 and (r.y1 - r.y0) > 25 and (r.x1 - r.x0) > 20:
            rects.append((round(r.x0, 1), round(r.x1, 1), round(r.y0, 1),
                          round(r.y1, 1), hexof(f)))
    rects.sort()
    print(f"p.idx {pno}  {code} {name}")
    for x0, x1, y0, y1, hx in rects:
        w = round(x1 - x0, 1)
        kind = "badge" if w < 70 else "banner"
        print(f"    {kind:<6} x[{x0:>5}..{x1:>5}] w={w:<5} y[{y0}..{y1}] fill={hx}")
