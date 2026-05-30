#!/usr/bin/env python3
"""Build the integrated-draft cover page.

Reuses the baseline CZC cover ART (the blue "CORE ZONING CODE / NEWCASTLE,
MAINE" wordmark, the effective/adopted/amended dates, the town-seal watermark)
by vector-copying baseline page 0, then:

  1. MASKS the handwritten town-clerk attestation block (lower-left:
     "Attested By:" + signature + date). That signature is a legal
     certification that the document is a true copy of the ADOPTED code; it must
     NOT appear on an unadopted draft that contains the proposed Article 3.
     The scan background is pure white (sampled 254,254,254), so the mask is
     invisible.

  2. Stamps a DRAFT banner in the upper white space: status, version, and a
     one-line provenance note.

Usage:
  build-cover.py BASELINE_PDF OUT_PDF VERSION DATE_STR
Example:
  build-cover.py "docs/Newcastle Core Zoning Code.pdf" /tmp/cover.pdf \
      v0.6-draft "May 30, 2026"
"""
import os
import sys
import fitz  # PyMuPDF

ARTICLE_BLUE = (0x36 / 255, 0x7A / 255, 0xAC / 255)
GRAY = (0x7C / 255, 0x76 / 255, 0x6F / 255)
WHITE = (1, 1, 1)
NEAR_WHITE = (254 / 255, 254 / 255, 254 / 255)  # matches the scan background

# Attestation block to mask (page points; measured from the 200-dpi crop).
# Stays left of "NEWCASTLE, MAINE" (x>=317) and covers label+signature+date.
ATTEST_RECT = fitz.Rect(48, 626, 306, 754)

FONTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "style", "fonts")
BARLOW_BOLD = os.path.join(FONTS_DIR, "Barlow-Bold.ttf")
BARLOW_MED = os.path.join(FONTS_DIR, "Barlow-Medium.ttf")
BARLOW_REG = os.path.join(FONTS_DIR, "Barlow-Regular.ttf")


def build_cover(baseline_pdf, out_pdf, version, date_str):
    src = fitz.open(baseline_pdf)
    w, h = src[0].rect.width, src[0].rect.height
    # Baseline page 0 is /Rotate 90 over a landscape mediabox: rendering to a
    # pixmap HONORS the rotation (upright 612x792), whereas show_pdf_page would
    # paste the un-rotated content. The cover is a scan anyway, so rasterize at
    # 300 dpi and place it as the page image — no fidelity lost, rotation correct.
    cover_pix = src[0].get_pixmap(dpi=300)

    out = fitz.open()
    page = out.new_page(width=w, height=h)

    # 1. Reuse the baseline cover art (upright) at full fidelity.
    page.insert_image(page.rect, pixmap=cover_pix)

    # 2. Mask the personal attestation (invisible white-on-white).
    page.draw_rect(ATTEST_RECT, color=None, fill=NEAR_WHITE)

    # 3. Draft banner in the upper white space (centered). A filled article-blue
    #    bar with white text = on-brand and unmistakable. Barlow (embedded) so
    #    the em-dash and middle-dot encode correctly.
    bar = fitz.Rect(96, 250, w - 96, 366)
    page.draw_rect(bar, color=None, fill=ARTICLE_BLUE)

    page.insert_textbox(
        fitz.Rect(bar.x0, bar.y0 + 14, bar.x1, bar.y0 + 52),
        "INTEGRATED DRAFT — NOT ADOPTED",
        fontfile=BARLOW_BOLD, fontname="barlow-bold", fontsize=20, color=WHITE,
        align=fitz.TEXT_ALIGN_CENTER,
    )
    page.insert_textbox(
        fitz.Rect(bar.x0 + 8, bar.y0 + 56, bar.x1 - 8, bar.y0 + 86),
        f"{version}  ·  includes proposed Article 3: Streets, Roads & Driveways",
        fontfile=BARLOW_MED, fontname="barlow-med", fontsize=12, color=WHITE,
        align=fitz.TEXT_ALIGN_CENTER,
    )
    page.insert_textbox(
        fitz.Rect(96, bar.y1 + 10, w - 96, bar.y1 + 48),
        f"Generated {date_str} from the adopted Core Zoning Code "
        f"(amended through March 24, 2025).\nFor review only — not a certified copy.",
        fontfile=BARLOW_REG, fontname="barlow-reg", fontsize=9.5, color=GRAY,
        align=fitz.TEXT_ALIGN_CENTER,
    )

    out.save(out_pdf, garbage=4, deflate=True)
    out.close()
    src.close()
    print(f"cover -> {out_pdf} ({version})")


if __name__ == "__main__":
    if len(sys.argv) != 5:
        sys.exit("usage: build-cover.py BASELINE_PDF OUT_PDF VERSION DATE_STR")
    build_cover(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4])
