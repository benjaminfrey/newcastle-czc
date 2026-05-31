#!/usr/bin/env python3
"""Compose Streetmix-style cross-section SVGs for the Article 3 Street/Road Types.

Reads source/exhibits/cross-sections/types.json and, for each Type, lays its
ordered segments left-to-right at the genuine Streetmix render scale
(TILE_SIZE = 12/0.3048 = 39.37 px/ft, so vendored sprites place at natural pixel
size with no rescaling). Ground surfaces are flat fills sampled from the
Streetmix ground sprites; objects (cars, trees, people, buildings, markings) are
the genuine CC BY-SA Streetmix sprites, embedded as nested <svg> with their
internal ids namespaced so gradients/clip-paths don't collide between sprites.
Adds a per-segment dimension ruler and a right-of-way bracket in CZC typography
(Barlow / article-blue). Output: one self-contained SVG per Type, embedded
full-text-block-width into the native-Typst Type plate.

Usage:
  build-cross-sections.py [CODE ...]      # default: every Type in types.json
"""
import sys
import re
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
XS = ROOT / "source" / "exhibits" / "cross-sections"
SPRITES = XS / "sprites"

SCALE = 39.3700787          # px per foot (Streetmix TILE_SIZE); sprites are 1:1 at this scale
SPRITE_SCALE = 1.0          # = SCALE / 39.3700787

# --- vertical geometry (feet) -------------------------------------------------
HEAD_MARGIN_FT = 2.0       # sky kept clear above the tallest sprite in a section
HEAD_FLOOR_FT = 9.0        # minimum sky headroom even when all objects are short
CURB_FT = 0.5              # curb reveal: raised segments sit this high above roadway
GROUND_STRIP_FT = 2.6      # depth of the visible surface band below the baseline
GAP_FT = 0.55             # gap between surface band and the segment dimension line
SEG_LABEL_GAP_FT = 1.15   # baseline-to-width-label drop below the dim line
SEG_NAME_GAP_FT = 2.05    # baseline-to-name-label drop below the dim line
ROW_GAP_FT = 3.15         # dim line to ROW bracket
ROW_LABEL_GAP_FT = 1.15   # ROW bracket to its label
BOTTOM_PAD_FT = 1.7

# --- surface fills (sampled from Streetmix ground sprites) --------------------
SURFACE = {
    "asphalt":  "#292B29",   # rgb(41,43,41)
    "concrete": "#D8D3CB",   # rgb(216,211,203)
    "grass":    "#3D8140",   # rgb(53,129,63), with a lighter top edge
    "grass_lo": "#356B38",
    "gravel":   "#B8A77E",   # earth/sand blend
    "shoulder": "#5C5E5F",   # rgb(92,94,95) asphalt-gray
    "earth":    "#352D27",   # rgb(53,45,39)
    "sand":     "#ECDBB1",
}
SKY_TOP = "#DCEEF3"
SKY_HORIZON = "#CCE0E7"      # rgb sampled from sky-front

# --- CZC type tokens ----------------------------------------------------------
ARTICLE_BLUE = "#367AAC"
BODY_DARK = "#231F20"
GRAY = "#7C766F"
HAIR = "#9A938B"
CENTER_YELLOW = "#EFEE5E"   # Streetmix center-line yellow rgb(239,238,94)
LANE_WHITE = "#F4F2EC"      # lane-line white (slightly warm so it reads on dark asphalt)
FONT = "Barlow, 'Helvetica Neue', Helvetica, sans-serif"

# font sizes in px (canvas is ~3000-3600px wide; Typst downscales to text width)
FS_SEG_W = 56
FS_SEG_NM = 34
FS_ROW = 60
FS_EDGE = 42

_id_re = re.compile(r'id="([^"]+)"')
_svg_open_re = re.compile(r"<svg\b[^>]*>", re.S)
_vb_re = re.compile(r'viewBox="([^"]+)"')


def parse_sprite(text):
    """Return (viewbox[4], inner_svg_markup) for a standalone sprite file."""
    m = _svg_open_re.search(text)
    svg_open = m.group(0)
    vb = [float(x) for x in _vb_re.search(svg_open).group(1).replace(",", " ").split()]
    start = m.end()
    end = text.rstrip().rfind("</svg>")
    return vb, text[start:end]


def namespace_ids(inner, prefix):
    """Prefix every internal id (and url(#..)/href="#..") so sprites don't clash."""
    ids = sorted(set(_id_re.findall(inner)), key=len, reverse=True)
    for idv in ids:
        new = prefix + idv
        inner = inner.replace(f'id="{idv}"', f'id="{new}"')
        inner = inner.replace(f"url(#{idv})", f"url(#{new})")
        inner = inner.replace(f'href="#{idv}"', f'href="#{new}"')
    return inner


_sprite_cache = {}


def sprite_size(rel):
    """Natural (width, height) of a sprite in px at SPRITE_SCALE."""
    p = SPRITES / rel
    if p not in _sprite_cache:
        _sprite_cache[p] = parse_sprite(p.read_text())
    vb, _ = _sprite_cache[p]
    return vb[2] * SPRITE_SCALE, vb[3] * SPRITE_SCALE


def _txt_w(s, size, sp=0.0):
    """Rough rendered width (px) of a Barlow string at a given size + spacing."""
    return len(s) * size * 0.52 + max(0, len(s) - 1) * sp


def embed(rel, cx_px, baseline_px, prefix, anchor="bottom-center"):
    """Embed a sprite at natural size; bottom-aligned, centered on cx_px."""
    p = SPRITES / rel
    if p not in _sprite_cache:
        _sprite_cache[p] = parse_sprite(p.read_text())
    vb, inner = _sprite_cache[p]
    w = vb[2] * SPRITE_SCALE
    h = vb[3] * SPRITE_SCALE
    x = cx_px - w / 2.0
    y = baseline_px - h
    inner = namespace_ids(inner, prefix)
    vbstr = f"{vb[0]} {vb[1]} {vb[2]} {vb[3]}"
    return (f'<svg x="{x:.2f}" y="{y:.2f}" width="{w:.2f}" height="{h:.2f}" '
            f'viewBox="{vbstr}" preserveAspectRatio="xMidYMax meet">{inner}</svg>'), w, h


def centerline(x, baseline):
    """Bold double-yellow centerline drawn on the road surface band at boundary x."""
    bw = 0.36 * SCALE
    gap = 0.40 * SCALE
    top = baseline + 0.30 * SCALE
    h = 1.80 * SCALE
    x1 = x - gap / 2.0 - bw
    x2 = x + gap / 2.0
    return (f'<rect x="{x1:.2f}" y="{top:.2f}" width="{bw:.2f}" height="{h:.2f}" fill="{CENTER_YELLOW}"/>'
            f'<rect x="{x2:.2f}" y="{top:.2f}" width="{bw:.2f}" height="{h:.2f}" fill="{CENTER_YELLOW}"/>')


def laneline(x, baseline):
    """Dashed white lane line at boundary x (between same-direction lanes)."""
    bw = 0.32 * SCALE
    dash = 0.55 * SCALE
    skip = 0.45 * SCALE
    y = baseline + 0.35 * SCALE
    band = 1.75 * SCALE
    out = []
    yy = y
    while yy < y + band:
        out.append(f'<rect x="{x - bw / 2:.2f}" y="{yy:.2f}" width="{bw:.2f}" '
                   f'height="{min(dash, y + band - yy):.2f}" fill="{LANE_WHITE}"/>')
        yy += dash + skip
    return "".join(out)


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def text(x, y, s, size, fill, weight="400", anchor="middle", spacing=None):
    ls = f' letter-spacing="{spacing}"' if spacing else ""
    return (f'<text x="{x:.2f}" y="{y:.2f}" font-family="{FONT}" font-size="{size}" '
            f'font-weight="{weight}" fill="{fill}" text-anchor="{anchor}"{ls}>{esc(s)}</text>')


def build_type(code, spec):
    segs = spec["segments"]
    street_w = sum(s["width"] for s in segs)
    left = spec.get("edges", {}).get("left")
    right = spec.get("edges", {}).get("right")
    left_show = (left or {}).get("show_ft", 0)
    right_show = (right or {}).get("show_ft", 0)

    total_w_ft = left_show + street_w + right_show
    W = total_w_ft * SCALE

    # dynamic sky headroom: just clear the tallest sprite drawn in this section
    tallest = 0.0
    for s in segs:
        for obj in s.get("objects", []):
            tallest = max(tallest, sprite_size(obj["sprite"])[1])
    for e in (left, right):
        if not e:
            continue
        if e.get("sprite"):
            tallest = max(tallest, sprite_size(e["sprite"])[1])
        for obj in e.get("objects", []):
            tallest = max(tallest, sprite_size(obj["sprite"])[1])
    baseline = max(HEAD_FLOOR_FT * SCALE, tallest + HEAD_MARGIN_FT * SCALE)
    curb = CURB_FT * SCALE
    ground_bottom = baseline + GROUND_STRIP_FT * SCALE
    dim_y = ground_bottom + GAP_FT * SCALE
    row_y = dim_y + ROW_GAP_FT * SCALE
    H = row_y + (ROW_LABEL_GAP_FT + BOTTOM_PAD_FT) * SCALE

    x_street0 = left_show * SCALE
    x_street1 = (left_show + street_w) * SCALE

    # surface level of the outermost segment on each side (curb-raised or roadway)
    top_left = baseline - curb if segs[0].get("raised") else baseline
    top_right = baseline - curb if segs[-1].get("raised") else baseline

    parts = []
    parts.append(
        f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" '
        f'xmlns:serif="http://www.serif.com/" '
        f'viewBox="0 0 {W:.2f} {H:.2f}" width="{W:.2f}" height="{H:.2f}">')

    # sky
    parts.append(
        f'<defs><linearGradient id="sky" x1="0" y1="0" x2="0" y2="1">'
        f'<stop offset="0" stop-color="{SKY_TOP}"/>'
        f'<stop offset="1" stop-color="{SKY_HORIZON}"/></linearGradient></defs>')
    parts.append(f'<rect x="0" y="0" width="{W:.2f}" height="{baseline:.2f}" fill="url(#sky)"/>')

    # ---- ground surface bands (per segment) ----
    x = x_street0
    seg_bounds = [x]
    for s in segs:
        w = s["width"] * SCALE
        raised = s.get("raised", False)
        top = baseline - curb if raised else baseline
        surf = SURFACE.get(s["surface"], "#999999")
        # surface band down to ground bottom
        parts.append(f'<rect x="{x:.2f}" y="{top:.2f}" width="{w:.2f}" '
                     f'height="{ground_bottom - top:.2f}" fill="{surf}"/>')
        if s["surface"] == "grass":
            parts.append(f'<rect x="{x:.2f}" y="{top:.2f}" width="{w:.2f}" '
                         f'height="{max(2, 0.18 * SCALE):.2f}" fill="{SURFACE["grass_lo"]}" opacity="0.5"/>')
        x += w
        seg_bounds.append(x)

    # subtle earth sliver at the very bottom of the surface band
    parts.append(f'<rect x="{x_street0:.2f}" y="{ground_bottom - 0.18 * SCALE:.2f}" '
                 f'width="{street_w * SCALE:.2f}" height="{0.18 * SCALE:.2f}" fill="{SURFACE["earth"]}" opacity="0.55"/>')

    # ground baseline + curb faces
    parts.append(f'<line x1="{x_street0:.2f}" y1="{baseline:.2f}" x2="{x_street1:.2f}" '
                 f'y2="{baseline:.2f}" stroke="{BODY_DARK}" stroke-width="1.5" opacity="0.35"/>')

    # ---- context edges: building (urban) or open ground + vegetation (rural) ----
    def render_edge(edge, side, prefix):
        if not edge:
            return
        if side == "left":
            zx0, zx1, top = 0.0, x_street0, top_left
        else:
            zx0, zx1, top = x_street1, W, top_right
        if edge.get("ground"):  # open / vegetated / lawn edge
            surf = SURFACE.get(edge["ground"], "#999999")
            parts.append(f'<rect x="{zx0:.2f}" y="{top:.2f}" width="{zx1 - zx0:.2f}" '
                         f'height="{ground_bottom - top:.2f}" fill="{surf}"/>')
            if edge["ground"] == "grass":
                parts.append(f'<rect x="{zx0:.2f}" y="{top:.2f}" width="{zx1 - zx0:.2f}" '
                             f'height="{max(2, 0.18 * SCALE):.2f}" fill="{SURFACE["grass_lo"]}" opacity="0.5"/>')
            for j, obj in enumerate(edge.get("objects", [])):
                cx = zx0 + obj.get("at", 0.5) * (zx1 - zx0)
                emb, _, _ = embed(obj["sprite"], cx, top, f"{prefix}{j}_")
                parts.append(emb)
        if edge.get("sprite"):  # building flush to the ROW line, clipped at canvas
            emb, w, h = embed(edge["sprite"], 0, top, prefix)
            ex = (x_street0 - w) if side == "left" else x_street1
            emb = re.sub(r'^<svg x="[^"]*"', f'<svg x="{ex:.2f}"', emb)
            parts.append(emb)

    render_edge(left, "left", "el_")
    render_edge(right, "right", "er_")

    # ---- objects (trees, cars, people) + lane markings ----
    x = x_street0
    for i, s in enumerate(segs):
        w = s["width"] * SCALE
        raised = s.get("raised", False)
        top = baseline - curb if raised else baseline
        for obj in s.get("objects", []):
            cx = x + obj.get("at", 0.5) * w
            emb, _, _ = embed(obj["sprite"], cx, top, f"o{i}_")
            parts.append(emb)
        if s.get("centerline_right"):
            parts.append(centerline(x + w, baseline))
        if s.get("lane_line_right"):
            parts.append(laneline(x + w, baseline))
        x += w

    # ---- segment dimension ruler ----
    parts.append(f'<line x1="{x_street0:.2f}" y1="{dim_y:.2f}" x2="{x_street1:.2f}" '
                 f'y2="{dim_y:.2f}" stroke="{ARTICLE_BLUE}" stroke-width="1.4"/>')
    tick_up = 0.42 * SCALE
    for bx in seg_bounds:
        parts.append(f'<line x1="{bx:.2f}" y1="{dim_y - tick_up:.2f}" x2="{bx:.2f}" '
                     f'y2="{dim_y + 0.18 * SCALE:.2f}" stroke="{ARTICLE_BLUE}" stroke-width="1.4"/>')
    x = x_street0
    for s in segs:
        w = s["width"] * SCALE
        cx = x + w / 2.0
        avail = w - 6
        # width callout (primary): shrink to fit a narrow segment, never below 30px
        wlabel = f"{s['width']:g} ft"
        wsize = FS_SEG_W
        if _txt_w(wlabel, wsize) > avail:
            wsize = max(30.0, avail / (len(wlabel) * 0.52))
        parts.append(text(cx, dim_y + SEG_LABEL_GAP_FT * SCALE, wlabel, wsize, ARTICLE_BLUE, "600"))
        # name (secondary): only when it fits the segment, else omit to avoid collisions
        nm = s["name"].upper()
        if _txt_w(nm, FS_SEG_NM, 0.4) <= avail:
            parts.append(text(cx, dim_y + SEG_NAME_GAP_FT * SCALE, nm, FS_SEG_NM, GRAY, "500", spacing="0.4"))
        x += w

    # ---- right-of-way bracket ----
    cap = 0.4 * SCALE
    parts.append(f'<line x1="{x_street0:.2f}" y1="{row_y:.2f}" x2="{x_street1:.2f}" '
                 f'y2="{row_y:.2f}" stroke="{GRAY}" stroke-width="1.4"/>')
    for bx in (x_street0, x_street1):
        parts.append(f'<line x1="{bx:.2f}" y1="{row_y - cap:.2f}" x2="{bx:.2f}" '
                     f'y2="{row_y + cap:.2f}" stroke="{GRAY}" stroke-width="1.4"/>')
    if spec.get("maindot"):
        rowlabel = "ILLUSTRATIVE SECTION  ·  CARTWAY & R.O.W. PER MAINEDOT"
    else:
        r = spec["row"]
        rowlabel = f"RIGHT-OF-WAY   {r['min']}–{r['max']} ft  ({r['typ']} ft typ.)"
    parts.append(text((x_street0 + x_street1) / 2.0, row_y + ROW_LABEL_GAP_FT * SCALE,
                      rowlabel, FS_ROW, BODY_DARK, "600", spacing="1.5"))

    parts.append("</svg>")
    return "\n".join(parts)


def main(argv):
    data = json.loads((XS / "types.json").read_text())
    codes = [a for a in argv if not a.startswith("-")] or \
            [k for k in data.keys() if not k.startswith("_")]
    for code in codes:
        if code not in data:
            print(f"!! no spec for {code}", file=sys.stderr)
            continue
        svg = build_type(code, data[code])
        out = XS / f"{code}.svg"
        out.write_text(svg)
        print(f"cross-section -> {out.relative_to(ROOT)} ({len(svg)//1024} KB)")


if __name__ == "__main__":
    main(sys.argv[1:])
