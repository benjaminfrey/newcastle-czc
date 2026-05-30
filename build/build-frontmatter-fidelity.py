#!/usr/bin/env python3
"""Side-by-side fidelity comparison of the front matter: baseline vs draft.

The integrated draft prepends a cover (baseline art + draft banner) and an
auto-derived Table of Contents. This builds a reviewer artifact placing each
baseline front-matter page next to its draft counterpart on one landscape
sheet, so the "reads as the same document" quality bar can be checked at a
glance. Mirrors the v0.5 "District Spread Fidelity" deliverable.

Pairing (baseline 0-indexed page -> draft 0-indexed page):
  cover     : baseline p0  ->  draft p0   (draft adds banner, masks signature)
  TOC page1 : baseline p1  ->  draft p2   (draft p1 is the blank verso)
  TOC page2 : baseline p2  ->  draft p3

Usage:
  build-frontmatter-fidelity.py BASELINE_PDF DRAFT_PDF OUT_PDF
"""
import sys
import fitz

PAIRS = [("COVER", 0, 0), ("TABLE OF CONTENTS — p.1", 1, 2),
         ("TABLE OF CONTENTS — p.2", 2, 3)]
DPI = 150
GAP = 24          # gutter between the two page images
MARGIN = 28       # outer margin
LABEL_H = 30      # caption band height
ARTICLE_BLUE = (0x36 / 255, 0x7A / 255, 0xAC / 255)
GRAY = (0x7C / 255, 0x76 / 255, 0x6F / 255)


def build(baseline_pdf, draft_pdf, out_pdf):
    base = fitz.open(baseline_pdf)
    draft = fitz.open(draft_pdf)
    out = fitz.open()

    for title, bp, dp in PAIRS:
        bpix = base[bp].get_pixmap(dpi=DPI)
        dpix = draft[dp].get_pixmap(dpi=DPI)
        # Scale each page to a common display height; lay out left|right.
        disp_h = max(bpix.height, dpix.height)
        bw = bpix.width * disp_h / bpix.height
        dw = dpix.width * disp_h / dpix.height
        page_w = MARGIN * 2 + bw + GAP + dw
        page_h = MARGIN * 2 + LABEL_H + disp_h
        page = out.new_page(width=page_w, height=page_h)

        # Caption band.
        page.insert_textbox(
            fitz.Rect(MARGIN, MARGIN - 6, page_w - MARGIN, MARGIN + LABEL_H),
            title, fontsize=15, color=ARTICLE_BLUE, fontname="hebo",
            align=fitz.TEXT_ALIGN_CENTER)
        y0 = MARGIN + LABEL_H
        lrect = fitz.Rect(MARGIN, y0, MARGIN + bw, y0 + disp_h)
        rrect = fitz.Rect(MARGIN + bw + GAP, y0, MARGIN + bw + GAP + dw, y0 + disp_h)
        page.insert_image(lrect, pixmap=bpix)
        page.insert_image(rrect, pixmap=dpix)
        # Sub-labels under each.
        for rect, lab in ((lrect, "BASELINE (adopted)"), (rrect, "INTEGRATED DRAFT")):
            page.insert_textbox(
                fitz.Rect(rect.x0, rect.y0 + 2, rect.x1, rect.y0 + 16),
                lab, fontsize=8, color=GRAY, fontname="hebo",
                align=fitz.TEXT_ALIGN_CENTER)
        # Hairline frames.
        page.draw_rect(lrect, color=GRAY, width=0.5)
        page.draw_rect(rrect, color=GRAY, width=0.5)

    out.save(out_pdf, garbage=4, deflate=True)
    out.close(); base.close(); draft.close()
    print(f"front-matter fidelity -> {out_pdf} ({len(PAIRS)} spreads)")


if __name__ == "__main__":
    if len(sys.argv) != 4:
        sys.exit("usage: build-frontmatter-fidelity.py BASELINE_PDF DRAFT_PDF OUT_PDF")
    build(sys.argv[1], sys.argv[2], sys.argv[3])
