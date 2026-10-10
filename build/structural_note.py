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

Every sentence that names an Article, a count or a "new" status is GENERATED
from adoption-map.json (or, for a single Article, from the change determination
and the ownership map), so under the identity map shipped after the v1.0
adoption the page claims none of the three. The page names KINDS of change --
wording, headings, tables or figures, data -- never line counts (czc_diff counts
a modified line twice).

Usage:  structural_note.py OUT_PDF [--map PATH] [--old-label LABEL]
            [--scope code|article:N] [--old REF] [--new-dir DIR]
            [--md OUT_MD] [--pad-to-even]
"""
from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path

import pymupdf  # PyMuPDF; `import fitz` is deprecated and prints a notice to stdout

BUILD = Path(__file__).resolve().parent
sys.path.insert(0, str(BUILD))

import adoption_map  # noqa: E402
import manifest  # noqa: E402

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


def _article_shift(amap):
    """(moved, pivot): the (old, new) pairs that changed number, and the last
    article that did not move. One computation, shared by the page's heading and
    its sentence so the two cannot disagree. moved == [] means no renumbering."""
    moved = [(o, n) for o, n in sorted(amap.article_numbers.items()) if o != n]
    if not moved:
        return [], None
    unchanged = [o for o, n in amap.article_numbers.items() if o == n]
    pivot = max(unchanged) if unchanged else min(o for o, _ in moved) - 1
    return moved, pivot


def article_shift_sentence(amap) -> str:
    """The old->new article map, read from adoption-map.json rather than
    restated here, so this page and the renumbering suppression cannot
    disagree about which articles moved."""
    moved, pivot = _article_shift(amap)
    if not moved:
        return ("No article was renumbered in this amendment, so no renumbering "
                "marks were suppressed.")
    pairs = ", ".join(f"{o} becomes {n}" for o, n in moved)
    return (
        f"Every article after Article {pivot} shifts up by one: {pairs}. "
        f"Cross-references and table numbers throughout were renumbered to match. "
        f"That renumbering is mechanical, and it is NOT marked anywhere in this "
        f"document — it is stated here once instead of appearing as a change on "
        f"more than a hundred separate lines. Do not read the absence of "
        f"renumbering marks as meaning nothing was renumbered."
    )


def _frontmatter_value(text: str, key: str) -> str:
    m = re.match(r"^---\n(.*?)\n---", text, re.S)
    for line in (m.group(1).split("\n") if m else []):
        if line.startswith(key + ":"):
            return line.split(":", 1)[1].strip().strip('"')
    return ""


def _article_of(basename: str) -> int | None:
    m = manifest.PROSE_RE.match(basename)
    return int(m.group(1)) if m else None


def _article_name(basename: str, source_dir: Path) -> str:
    p = Path(source_dir) / basename
    return (_frontmatter_value(p.read_text(encoding="utf-8"), "article-name")
            if p.is_file() else "") or "this Article"


CODE_INTRO = ("Some changes cannot be marked word by word in a redline. They are "
              "stated here, once, before any marked text.")
ARTICLE_INTRO = ("This page says what changed in this Article, and what a redline "
                 "cannot show. It is stated once, before any marked text.")


def _unit_labels() -> list[str]:
    """Every native unit's plain-words label across Articles 1-9, in Article
    order, each tagged with its Article. These pages come from data or scans and
    NEVER get an in-text note, so the page that promises notes must also name them."""
    doc = manifest.load()
    return [f"{u['label']} (Article {k})"
            for k in sorted((k for k in doc if k.isdigit()), key=int)
            for u in doc[k].get("units", []) if u.get("label")]


def _old_label(old_ref: str) -> str:
    if old_ref == adoption_map.load().baseline_version:
        return f"the previously adopted Code ({old_ref})"
    return f"the Code as of {old_ref}"


def note_blocks(amap, old_label: str, source_dir: Path | None = None) -> list[tuple[str, str]]:
    """(heading, body) blocks. The wording is deliberately plain: a citizen
    reads this page, not a drafter. Every block that names an Article or a
    "new" status exists only if the adoption map says it is true."""
    source_dir = Path(source_dir) if source_dir else BUILD.parent / "source"
    blocks = [(
        "What this document compares",
        f"This redline compares the proposed Code against {old_label}. "
        f"Additions are shown in red; deletions are struck through. Where a heading, "
        f"table or figure was added, removed or changed, a note in italics and square "
        f"brackets says so at that spot.",
    )]

    new_articles = sorted((_article_of(b), b) for b, old in amap.files.items()
                          if old is None and _article_of(b) is not None)
    for n, basename in new_articles:
        blocks.append((
            f"Article {n}, {_article_name(basename, source_dir)}, is new",
            "It has no counterpart in the adopted Code, so its entire text is "
            "marked as an addition.",
        ))

    moved, pivot = _article_shift(amap)
    if moved:
        blocks.append((f"The articles after Article {pivot} were renumbered",
                       article_shift_sentence(amap)))

    for n, basename in sorted((_article_of(b), b) for b in amap.not_text_comparable
                              if _article_of(b) is not None):
        blocks.append((
            f"Article {n} is reproduced UNMARKED",
            "The district standards are now generated as full-page spreads from "
            "district data rather than written as prose, so a text comparison "
            f"cannot mark them. Article {n} therefore carries NO marks in this "
            f"document. That is not a statement that Article {n} was untouched, and "
            "it is not a statement that anything in it was deleted. What changed "
            "there is described in the Summary of Changes.",
        ))

    units = _unit_labels()
    blocks.append((
        "Pages shown as they now stand, without marks",
        "These are reproduced from data or as exhibits rather than written as text, so a "
        "text comparison cannot mark them; each shows its current state: " + "; ".join(units)
        + ". What changed in them is described in the Summary of Changes. Tables and figures written within an Article's "
        "text are different: where one was added, removed or changed, a note in italics and "
        "square brackets says so at that spot.",
    ))
    return blocks


def article_blocks(n: int, *, old_ref: str, new_dir: Path,
                   old_label: str | None = None) -> tuple[str, list[tuple[str, str]]]:
    """(subtitle, blocks) for Article n. Every sentence that names an Article, a
    kind of change, a heading or a table is generated from the change
    determination and the ownership map (ruling 8: kinds, never line counts)."""
    import czc_diff

    doc = manifest.load()
    entry = doc.get(str(n), {})
    prose = entry.get("prose") or next(
        (p.name for p in sorted(Path(new_dir).glob(f"article-0{n}-*.md"))), None)
    if prose is None:
        raise SystemExit(f"structural note: no prose for Article {n} in {new_dir}")
    new_text = (Path(new_dir) / prose).read_text(encoding="utf-8")
    name = _frontmatter_value(new_text, "article-name") or f"Article {n}"
    old = czc_diff.Side(ref=old_ref)
    c = czc_diff.determine(old, czc_diff.Side(root=Path(new_dir)))[n]
    raw = old.read(prose)
    sc = czc_diff.structural_changes(raw.decode("utf-8") if raw is not None else None, new_text)

    blocks = [(
        "What this document compares",
        f"This is Article {n}, {name}, as proposed, compared against {old_label or _old_label(old_ref)}. "
        f"Text added is shown in red; text deleted is struck through. Where a heading, table "
        f"or figure was added, removed or changed, a note in italics and square brackets says "
        f"so at that spot.")]

    kinds = [k for k, v in (("its wording", c.prose), ("its headings", c.heading),
                            ("its tables or figures", c.table),
                            ("the data its pages are printed from", c.data)) if v]
    if c.verdict == "SUBSTANTIVE":
        said = kinds[0] if len(kinds) == 1 else ", ".join(kinds[:-1]) + " and " + kinds[-1]
        what = f"This Article changed in substance: {said}."
    elif c.verdict == "NEEDS-CALL":
        what = ("No change to its wording, headings, tables or data was found, but some of its "
                "files changed in a way that needs a person's judgement (listed below).")
    elif c.verdict == "RENUMBER-ONLY":
        what = "Only references to renumbered sections changed; that renumbering is not marked."
    else:
        what = "No change was found in this Article."
    blocks.append(("What changed in this Article", what))

    items = ([f"Heading added: “{h}”" for h in sc["headings_added"]]
             + [f"Heading removed: “{h}”" for h in sc["headings_removed"]]
             + [f"Heading changed from “{a}”\n   to “{b}”" for a, b in sc["headings_changed"]]
             + [f"Table or figure added: “{t}”" for t in sc["tables_added"]]
             + [f"Table or figure removed: “{t}”" for t in sc["tables_removed"]]
             + [f"Table or figure changed: “{t}”" for t in sc["tables_changed"]])

    units = entry.get("units", [])
    labels = [u["label"] for u in units if u.get("label")]
    if labels:
        body = ("These are reproduced from data or as exhibits rather than written as text, so a "
                "text comparison cannot mark them; they appear as they now stand: "
                + "; ".join(labels) + ".")
        # The Use Table Changes document is the record of district-page changes; point
        # to it only when Article 2's data (or its legend file) actually changed.
        if n == 2 and (c.data > 0 or any(note.startswith("article-02.typ:")
                                         for note in c.needs_call)):
            body += (" Every change to the district pages is listed item by item in the Use "
                     "Table Changes document.")
        blocks.append(("Shown in their current form, without marks", body))
    if c.needs_call:
        def resident(note: str) -> str:
            path, _, rest = note.partition(": ")
            lab = next((u.get("label") for u in units if u.get("typ") == path and u.get("label")),
                       None) or "an exhibit file"
            return f"• {lab} ({path}): {rest}"
        blocks.append(("Needs a person's judgement",
                       "\n".join(resident(note) for note in c.needs_call)))
    # The list goes LAST: it is the one block that may be long, and it flows item by
    # item (render), so it must never push a disclosure above it off the page.
    blocks.append(("Headings, tables and figures",
                   "\n".join(f"• {i}" for i in items) if items
                   else "None of this Article's headings, tables or figures was added, removed "
                        "or changed."))
    return f"Article {n} — {name}", blocks


MORE_LINE = "…and {n} more. The full list is in the markdown version of this redline."
TOP_FIRST = 96
TOP_NEXT = 72
BOTTOM = PAGE_H - 72


def render(out_pdf: str, title_sub: str | None, blocks, *, intro: str,
           max_pages: int, pad_to_even: bool, scope_name: str = "this note") -> int:
    """Flow (heading, body) blocks across pages; return the page count.
    PyMuPDF's insert_textbox writes NOTHING when the text does not fit and
    returns a negative number, so a block is placed by trying it in the space
    left, and moved to a fresh page when it does not fit."""
    doc = pymupdf.open()
    box_w = PAGE_W - 2 * MARGIN

    def new_page(first: bool):
        page = doc.new_page(width=PAGE_W, height=PAGE_H)
        if first:
            bar = pymupdf.Rect(MARGIN, TOP_FIRST, PAGE_W - MARGIN, 150)
            page.draw_rect(bar, color=None, fill=ARTICLE_BLUE)
            page.insert_textbox(
                pymupdf.Rect(bar.x0 + 12, bar.y0 + 12, bar.x1 - 12, bar.y1 - 6),
                "HOW TO READ THIS REDLINE",
                fontfile=BARLOW_BOLD, fontname="barlow-bold", fontsize=17, color=WHITE,
                align=pymupdf.TEXT_ALIGN_CENTER)
            y = bar.y1 + 12
            if title_sub:
                page.insert_textbox(
                    pymupdf.Rect(MARGIN, y, PAGE_W - MARGIN, y + 22), title_sub,
                    fontfile=BARLOW_BOLD, fontname="barlow-bold", fontsize=13,
                    color=ARTICLE_BLUE, align=pymupdf.TEXT_ALIGN_CENTER)
                y += 26
            page.insert_textbox(
                pymupdf.Rect(MARGIN, y, PAGE_W - MARGIN, y + 30), intro,
                fontfile=BARLOW_MED, fontname="barlow-med", fontsize=10.5,
                color=REDLINE_RED, align=pymupdf.TEXT_ALIGN_CENTER)
            return page, y + 40
        page.insert_textbox(
            pymupdf.Rect(MARGIN, TOP_NEXT - 20, PAGE_W - MARGIN, TOP_NEXT),
            "HOW TO READ THIS REDLINE (continued)", fontfile=BARLOW_BOLD,
            fontname="barlow-bold", fontsize=10, color=ARTICLE_BLUE)
        return page, TOP_NEXT + 8

    # Block heights are measured on a tall scratch page first, so the heading is
    # written BEFORE its body (reading order in the PDF's text layer) and only
    # when the whole block fits.
    scratch = pymupdf.open()
    tall = 4000.0
    sp = scratch.new_page(width=PAGE_W, height=tall + 20)

    def body_height(body: str) -> float:
        left = sp.insert_textbox(pymupdf.Rect(MARGIN, 0, MARGIN + box_w, tall), body,
                                 fontfile=BARLOW_REG, fontname="barlow-reg", fontsize=10,
                                 lineheight=1.35, color=INK)
        if left < 0:
            raise SystemExit("structural note: a single block is taller than any page. "
                             "Shorten its wording.")
        return tall - left

    def too_long(heading):
        return SystemExit(
            f"structural note: the block {heading!r} does not fit on an empty page. "
            f"Shorten its wording.")

    def overflowed(heading):
        return SystemExit(
            f"structural note: {scope_name} overflowed its {max_pages} page(s) at the block "
            f"{heading!r}. The page count is parity-critical; shorten the wording rather than "
            f"widening the box or shrinking the type.")

    def put(rect_y, text, height_hint=None):
        used = page.insert_textbox(
            pymupdf.Rect(MARGIN, rect_y, MARGIN + box_w, BOTTOM), text,
            fontfile=BARLOW_REG, fontname="barlow-reg", fontsize=10, lineheight=1.35, color=INK)
        if used < 0:
            raise SystemExit(f"structural note: text was measured to fit but did not place "
                             f"({-used:.0f}pt over): {text[:40]!r}")
        return BOTTOM - used

    def put_heading(h, at):
        page.insert_textbox(
            pymupdf.Rect(MARGIN, at, PAGE_W - MARGIN, at + 20), h,
            fontfile=BARLOW_BOLD, fontname="barlow-bold", fontsize=11.5, color=ARTICLE_BLUE)

    page, y = new_page(True)
    fresh = True                      # nothing but the title is on this page yet
    for heading, body in blocks:
        lines = body.split("\n")
        if not lines[0].startswith("• "):
            # A prose block: all or nothing, on a page of its own if need be.
            h = body_height(body)
            while y + 17 + h > BOTTOM:
                if fresh:
                    raise too_long(heading)
                if len(doc) >= max_pages:
                    raise overflowed(heading)
                page, y = new_page(False)
                fresh = True
            put_heading(heading, y)
            y = put(y + 17, body) + 14
            fresh = False
            continue

        # A bulleted list flows ITEM BY ITEM, so a long list can never make the
        # page refuse. An item is a "• " line plus any indented continuation lines.
        items: list[str] = []
        for line in lines:
            if line.startswith("• ") or not items:
                items.append(line)
            else:
                items[-1] += "\n" + line
        more_h = body_height(MORE_LINE.format(n=999))
        head_here = False             # has this list's heading been written on this page?
        i = 0
        while i < len(items):
            h = body_height(items[i])
            last_page = len(doc) >= max_pages
            reserve = more_h + 3 if (last_page and i < len(items) - 1) else 0
            head_h = 0 if head_here else 17
            if y + head_h + h + reserve <= BOTTOM:
                if not head_here:
                    put_heading(heading if i == 0 else f"{heading} (continued)", y)
                    y += 17
                    head_here = True
                y = put(y, items[i]) + 3
                fresh = False
                i += 1
                continue
            if not last_page:
                if fresh:
                    raise too_long(heading)
                page, y = new_page(False)
                fresh, head_here = True, False
                continue
            # The last page the scope allows is full: say how many are left.
            if not head_here:
                if y + 17 + more_h > BOTTOM:
                    raise overflowed(heading)
                put_heading(heading if i == 0 else f"{heading} (continued)", y)
                y += 17
            put(y, MORE_LINE.format(n=len(items) - i))
            y = BOTTOM                # nothing more fits on this page
            i = len(items)
        y += 11                       # 14 between blocks, less the item gap already added

    if pad_to_even and len(doc) % 2:
        doc.new_page(width=PAGE_W, height=PAGE_H)
    n = len(doc)
    doc.save(out_pdf, garbage=4, deflate=True)
    doc.close()
    return n


def to_markdown(title_sub: str | None, blocks, intro: str) -> str:
    out = ["## How to read this redline"]
    if title_sub:
        out.append(f"**{title_sub}**")
    out.append(intro)
    for heading, body in blocks:
        lines = [("- " + l[2:]) if l.startswith("• ") else l for l in body.split("\n")]
        out.append(f"### {heading}\n\n" + "\n".join(lines))
    return "\n\n".join(out) + "\n"


def build_note(out_pdf: str, *, map_path: str | None = None,
               old_label: str | None = None, md_path: str | None = None,
               pad_to_even: bool = False) -> None:
    amap = adoption_map.load(map_path)
    if old_label is None:
        old_label = f"the previously adopted Code ({amap.baseline_version})"
    blocks = note_blocks(amap, old_label)
    pages = render(out_pdf, None, blocks, intro=CODE_INTRO, max_pages=1,
                   pad_to_even=pad_to_even, scope_name="the whole-Code note")
    if md_path:
        Path(md_path).write_text(to_markdown(None, blocks, CODE_INTRO), encoding="utf-8")
    print(f"structural note -> {out_pdf} ({pages} page(s))")


def build_article_note(out_pdf: str, n: int, *, old_ref: str, new_dir: str,
                       old_label: str | None = None, md_path: str | None = None,
                       pad_to_even: bool = False) -> None:
    sub, blocks = article_blocks(n, old_ref=old_ref, new_dir=Path(new_dir), old_label=old_label)
    pages = render(out_pdf, sub, blocks, intro=ARTICLE_INTRO, max_pages=4,
                   pad_to_even=pad_to_even, scope_name=f"the Article {n} note")
    if md_path:
        Path(md_path).write_text(to_markdown(sub, blocks, ARTICLE_INTRO), encoding="utf-8")
    print(f"structural note -> {out_pdf} ({pages} page(s))")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("out_pdf")
    ap.add_argument("--map", default=None)
    ap.add_argument("--old-label", default=None)
    ap.add_argument("--scope", default="code", help="code | article:N")
    ap.add_argument("--old", default=None, help="git ref of the previous Code (article scope)")
    ap.add_argument("--new-dir", default=str(BUILD.parent / "source"))
    ap.add_argument("--md", default=None)
    ap.add_argument("--pad-to-even", action="store_true")
    a = ap.parse_args()

    m = re.fullmatch(r"article:([1-9])", a.scope)
    if a.scope != "code" and not m:
        ap.error(f"--scope must be 'code' or 'article:N' (N = 1..9), not {a.scope!r}")
    if m:
        if not a.old:
            ap.error("--scope article:N needs --old REF, the git ref to compare against")
        import czc_diff
        try:
            build_article_note(a.out_pdf, int(m.group(1)), old_ref=a.old, new_dir=a.new_dir,
                               old_label=a.old_label, md_path=a.md, pad_to_even=a.pad_to_even)
        except czc_diff.Refusal as e:
            print(f"structural note: {e}", file=sys.stderr)
            return 1
        return 0
    build_note(a.out_pdf, map_path=a.map, old_label=a.old_label, md_path=a.md,
               pad_to_even=a.pad_to_even)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
