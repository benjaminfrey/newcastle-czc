#!/usr/bin/env python3
"""The baseline redline's STRUCTURAL-CHANGES note (ADOPTION-SPEC.md §4.3).

WHY THIS PAGE EXISTS. A redline is a text diff, so three real changes cannot
be marked in it, and each of them is invisible in exactly the way that misleads
a reader rather than merely inconveniencing them:

  1. Article 2's district standards moved out of markdown into a native-Typst
     unit between the baseline and now (spec §1.2b). A text diff would report
     the move as ~2,319 DELETED lines -- in a warrant packet, "the Town deleted
     all of its district standards" -- so the article is reproduced UNMARKED
     instead. A reader who is not told will read zero marks as "Article 2 was
     untouched."
  2. Every article after 2 shifts up by one, and cross-references and table
     numbers were renumbered throughout. The normaliser suppresses ~126 of
     those marks deliberately, so that 151 real changes are not buried under
     them. That suppression is honest ONLY if the reader is told the fact once,
     plainly -- otherwise a citizen reads the packet as "nothing was
     renumbered."
  3. Figures, tables and maps render at current state, unmarked, because a text
     diff cannot mark a regenerated figure. This limitation was already
     disclosed on the cover; it belongs here with the others.

Before this module, `build-redline-full.sh` hardcoded ONE cover caveat for both
the draft-to-draft and the baseline runs, mentioning only (3). Points (1) and
(2) -- the two invented for this feature -- were disclosed nowhere.

The page is rendered as the verso facing the cover, i.e. before any marked
text, and is generated FROM `adoption-map.json` so the article map it prints
cannot drift from the map the renumbering suppression actually used.

Usage:  structural_note.py OUT_PDF [--map PATH] [--old-label LABEL]
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import fitz  # PyMuPDF

BUILD = Path(__file__).resolve().parent
sys.path.insert(0, str(BUILD))

import adoption_map  # noqa: E402

ARTICLE_BLUE = (0x36 / 255, 0x7A / 255, 0xAC / 255)
INK = (0x22 / 255, 0x22 / 255, 0x22 / 255)
REDLINE_RED = (0xCC / 255, 0, 0)
WHITE = (1, 1, 1)

FONTS_DIR = os.path.join(BUILD, "..", "style", "fonts")
BARLOW_BOLD = os.path.join(FONTS_DIR, "Barlow-Bold.ttf")
BARLOW_MED = os.path.join(FONTS_DIR, "Barlow-Medium.ttf")
BARLOW_REG = os.path.join(FONTS_DIR, "Barlow-Regular.ttf")

PAGE_W, PAGE_H = 612, 792
MARGIN = 90


def article_shift_sentence(amap) -> str:
    """The old->new article map, read from adoption-map.json rather than
    restated here, so this page and the renumbering suppression cannot
    disagree about which articles moved."""
    moved = [(o, n) for o, n in sorted(amap.article_numbers.items()) if o != n]
    if not moved:
        return ("No article was renumbered in this amendment, so no renumbering "
                "marks were suppressed.")
    unchanged = [o for o, n in amap.article_numbers.items() if o == n]
    pivot = max(unchanged) if unchanged else min(o for o, _ in moved) - 1
    pairs = ", ".join(f"{o} becomes {n}" for o, n in moved)
    return (
        f"Every article after Article {pivot} shifts up by one: {pairs}. "
        f"Cross-references and table numbers throughout were renumbered to match. "
        f"That renumbering is mechanical, and it is NOT marked anywhere in this "
        f"document — it is stated here once instead of appearing as a change on "
        f"more than a hundred separate lines. Do not read the absence of "
        f"renumbering marks as meaning nothing was renumbered."
    )


def note_blocks(amap, old_label: str) -> list[tuple[str, str]]:
    """(heading, body) blocks. The wording is deliberately plain: a citizen
    reads this page, not a drafter."""
    return [
        (
            "What this document compares",
            f"This redline compares the proposed Code against {old_label}. "
            f"Additions are shown in red; deletions are struck through.",
        ),
        (
            "Article 3, Thoroughfares, is new",
            "It has no counterpart in the adopted Code, so its entire text is "
            "marked as an addition.",
        ),
        (
            "The articles after Article 2 were renumbered",
            article_shift_sentence(amap),
        ),
        (
            "Article 2 is reproduced UNMARKED",
            "The district standards are now generated as full-page spreads from "
            "district data rather than written as prose, so a text comparison "
            "cannot mark them. Article 2 therefore carries NO marks in this "
            "document. That is not a statement that Article 2 was untouched, and "
            "it is not a statement that anything in it was deleted. What changed "
            "there is described in the Summary of Changes.",
        ),
        (
            "Figures, tables and maps show their current state",
            "Every figure, table, map and exhibit — including the Article 3 "
            "inventory and Type map — renders as it now stands and is not marked, "
            "because a text comparison cannot mark a regenerated figure. Those "
            "changes are described in the Summary of Changes.",
        ),
    ]


def build_note(out_pdf: str, *, map_path: str | None = None,
               old_label: str | None = None) -> None:
    amap = adoption_map.load(map_path)
    if old_label is None:
        old_label = ("the Core Zoning Code adopted November 3, 2020 and amended "
                     "through March 24, 2025")

    doc = fitz.open()
    page = doc.new_page(width=PAGE_W, height=PAGE_H)

    bar = fitz.Rect(MARGIN, 96, PAGE_W - MARGIN, 150)
    page.draw_rect(bar, color=None, fill=ARTICLE_BLUE)
    page.insert_textbox(
        fitz.Rect(bar.x0 + 12, bar.y0 + 12, bar.x1 - 12, bar.y1 - 6),
        "HOW TO READ THIS REDLINE",
        fontfile=BARLOW_BOLD, fontname="barlow-bold", fontsize=17, color=WHITE,
        align=fitz.TEXT_ALIGN_CENTER,
    )

    y = bar.y1 + 12
    page.insert_textbox(
        fitz.Rect(MARGIN, y, PAGE_W - MARGIN, y + 30),
        "Three real changes cannot be marked in a redline. They are stated here, "
        "once, before any marked text.",
        fontfile=BARLOW_MED, fontname="barlow-med", fontsize=10.5,
        color=REDLINE_RED, align=fitz.TEXT_ALIGN_CENTER,
    )
    y += 40

    for heading, body in note_blocks(amap, old_label):
        rect = fitz.Rect(MARGIN, y, PAGE_W - MARGIN, y + 20)
        page.insert_textbox(rect, heading, fontfile=BARLOW_BOLD,
                            fontname="barlow-bold", fontsize=11.5,
                            color=ARTICLE_BLUE)
        y += 17
        # Measure, then place: the blocks vary in length with the article map,
        # so a fixed per-block height would silently clip a longer one.
        box_w = PAGE_W - 2 * MARGIN
        height = 400.0
        rect = fitz.Rect(MARGIN, y, MARGIN + box_w, y + height)
        used = page.insert_textbox(rect, body, fontfile=BARLOW_REG,
                                   fontname="barlow-reg", fontsize=10,
                                   lineheight=1.35, color=INK)
        if used < 0:
            raise SystemExit(
                f"structural note: the block {heading!r} did not fit on the page "
                f"({-used:.0f}pt over). The note must stay one page — it is the "
                f"front matter's verso and the front-matter page count is parity-"
                f"critical. Shorten the wording rather than widening the box."
            )
        y += (height - used) + 14

    if y > PAGE_H - 72:
        raise SystemExit(
            f"structural note overflowed its single page (content ends at "
            f"{y:.0f}pt of {PAGE_H}). See the message above about parity.")

    doc.save(out_pdf, garbage=4, deflate=True)
    doc.close()
    print(f"structural note -> {out_pdf}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("out_pdf")
    ap.add_argument("--map", default=None)
    ap.add_argument("--old-label", default=None)
    a = ap.parse_args()
    build_note(a.out_pdf, map_path=a.map, old_label=a.old_label)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
