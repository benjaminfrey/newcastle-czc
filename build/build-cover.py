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

  3. Optionally stamps a REDLINE caveat line (when the formatted-redline build
     passes one) so a marked-up integrated draft is unmistakable on its face.

Usage:
  build-cover.py BASELINE_PDF OUT_PDF VERSION DATE_STR [REDLINE_CAVEAT]
                 [--mode draft|meeting|adopted] [--event-date DATE]
Example:
  build-cover.py "docs/Newcastle Core Zoning Code.pdf" /tmp/cover.pdf \
      v0.6-draft "May 30, 2026"
  build-cover.py "docs/Newcastle Core Zoning Code.pdf" /tmp/cover.pdf \
      v1.0 "March 15, 2027" --mode adopted --event-date "March 15, 2027"

mode defaults to "draft" (today's behaviour, unchanged). "meeting" and
"adopted" require --event-date: the Town Meeting date in meeting mode, the
adoption date in adopted mode. See build/ADOPTION-SPEC.md §4.
"""
import os
import sys
import fitz  # PyMuPDF

ARTICLE_BLUE = (0x36 / 255, 0x7A / 255, 0xAC / 255)
GRAY = (0x7C / 255, 0x76 / 255, 0x6F / 255)
WHITE = (1, 1, 1)
REDLINE_RED = (0xCC / 255, 0, 0)  # matches the added-text red in redline-text.py
NEAR_WHITE = (254 / 255, 254 / 255, 254 / 255)  # matches the scan background

# Attestation block to mask (page points; measured from the 200-dpi crop).
# Stays left of "NEWCASTLE, MAINE" (x>=317) and covers label+signature+date.
ATTEST_RECT = fitz.Rect(48, 626, 306, 754)

FONTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "style", "fonts")
BARLOW_BOLD = os.path.join(FONTS_DIR, "Barlow-Bold.ttf")
BARLOW_MED = os.path.join(FONTS_DIR, "Barlow-Medium.ttf")
BARLOW_REG = os.path.join(FONTS_DIR, "Barlow-Regular.ttf")


def build_cover(baseline_pdf, out_pdf, version, date_str, caveat=None,
                mode="draft", event_date=None):
    """mode: 'draft' | 'meeting' | 'adopted'.  See build/ADOPTION-SPEC.md §4.

    The clerk attestation is masked in EVERY mode (see module docstring): it
    certifies the originally adopted code, not an amendment to it.
    """
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

    # 3. Banner in the upper white space (centered). A filled article-blue bar
    #    with white text = on-brand and unmistakable. Barlow (embedded) so the
    #    em-dash and middle-dot encode correctly. Wording and layout vary by
    #    mode (see BANNERS below); the adopted mode drops the bar entirely.
    bar = fitz.Rect(96, 250, w - 96, 366)

    BANNERS = {
        "draft": (
            "INTEGRATED DRAFT — NOT ADOPTED",
            f"{version}  ·  includes proposed Article 3: Thoroughfares",
            f"Generated {date_str} from the adopted Core Zoning Code "
            f"(amended through March 24, 2025).\nFor review only — not a certified copy.",
        ),
        "meeting": (
            "TOWN MEETING EDITION — NOT YET ADOPTED",
            f"{version}  ·  for adoption at Town Meeting, {event_date}",
            f"Frozen {date_str}. The text put before the voters.\n"
            f"Not a certified copy.",
        ),
        "adopted": (
            None,
            f"{version}  ·  Adopted {event_date}",
            f"Adopted {event_date}, amending the Core Zoning Code "
            f"adopted November 3, 2020.",
        ),
    }
    if mode not in BANNERS:
        raise ValueError(f"unknown cover mode {mode!r}")
    if mode in ("meeting", "adopted") and not event_date:
        raise ValueError(f"mode {mode!r} requires event_date")

    headline, line2, line3 = BANNERS[mode]

    if headline is not None:
        page.draw_rect(bar, color=None, fill=ARTICLE_BLUE)
        page.insert_textbox(
            fitz.Rect(bar.x0, bar.y0 + 14, bar.x1, bar.y0 + 52), headline,
            fontfile=BARLOW_BOLD, fontname="barlow-bold", fontsize=20, color=WHITE,
            align=fitz.TEXT_ALIGN_CENTER,
        )
        page.insert_textbox(
            fitz.Rect(bar.x0 + 8, bar.y0 + 56, bar.x1 - 8, bar.y0 + 86), line2,
            fontfile=BARLOW_MED, fontname="barlow-med", fontsize=12, color=WHITE,
            align=fitz.TEXT_ALIGN_CENTER,
        )
    else:
        # Adopted: no blue bar. The version/date line sits in the white space, in
        # article blue on white, so the page reads as a code rather than a notice.
        page.insert_textbox(
            fitz.Rect(bar.x0, bar.y0 + 30, bar.x1, bar.y0 + 62), line2,
            fontfile=BARLOW_MED, fontname="barlow-med", fontsize=13,
            color=ARTICLE_BLUE, align=fitz.TEXT_ALIGN_CENTER,
        )

    page.insert_textbox(
        fitz.Rect(96, bar.y1 + 10, w - 96, bar.y1 + 48), line3,
        fontfile=BARLOW_REG, fontname="barlow-reg", fontsize=9.5, color=GRAY,
        align=fitz.TEXT_ALIGN_CENTER,
    )

    # 4. Optional redline caveat — a marked-up integrated draft says so on the
    #    cover (additions red / deletions struck; figures shown at current state).
    if caveat:
        page.insert_textbox(
            fitz.Rect(72, bar.y1 + 54, w - 72, bar.y1 + 116),
            caveat,
            fontfile=BARLOW_MED, fontname="barlow-med", fontsize=10, color=REDLINE_RED,
            align=fitz.TEXT_ALIGN_CENTER,
        )

    out.save(out_pdf, garbage=4, deflate=True)
    out.close()
    src.close()
    print(f"cover -> {out_pdf} ({version})")


if __name__ == "__main__":
    # Positional arguments: BASELINE_PDF OUT_PDF VERSION DATE_STR [REDLINE_CAVEAT]
    # --mode/--event-date are optional flags, filtered out before positional
    # parsing so build-full-czc.sh's existing call keeps working unchanged.
    args = sys.argv[1:]
    mode = "draft"
    event_date = None
    positional = []
    i = 0
    while i < len(args):
        arg = args[i]
        if arg == "--mode":
            mode = args[i + 1]
            i += 2
        elif arg == "--event-date":
            event_date = args[i + 1]
            i += 2
        else:
            positional.append(arg)
            i += 1

    if len(positional) not in (4, 5):
        sys.exit(
            "usage: build-cover.py BASELINE_PDF OUT_PDF VERSION DATE_STR "
            "[REDLINE_CAVEAT] [--mode draft|meeting|adopted] [--event-date DATE]"
        )
    caveat = positional[4] if len(positional) == 5 else None
    build_cover(positional[0], positional[1], positional[2], positional[3],
                caveat, mode=mode, event_date=event_date)
