#!/usr/bin/env python3
"""Add clickable GoTo links to the integrated CZC's Table of Contents.

Each TOC row renders as "NAME <dot-leader> <page>". The TOC page number is the
body PDF's 1-indexed position (== the page's printed number, since the body
numbers pn = here().page() + page_offset == its position). The body is appended
after FRONT_COUNT unnumbered front-matter pages, so the physical target of TOC
page P is simply  FRONT_COUNT + P  (1-indexed). Self-contained + layout-robust.

Usage:  toc_links.py OUTPUT.pdf FRONT_COUNT
"""
import os
import re
import sys

import fitz

ROW = re.compile(r"(?:\.\s*){3,}(\d+)\s*$")   # name <dot leader> <page>


def main() -> int:
    pdf, front = sys.argv[1], int(sys.argv[2])
    doc = fitz.open(pdf)
    n = doc.page_count
    added = 0
    for pno in range(min(front, n)):          # TOC lives in the front matter
        page = doc[pno]
        for b in page.get_text("dict")["blocks"]:
            for line in b.get("lines", []):
                text = "".join(s["text"] for s in line["spans"])
                m = ROW.search(text)
                if not m:
                    continue
                target = front + int(m.group(1)) - 1   # 0-indexed physical page
                if not (0 <= target < n):
                    continue
                page.insert_link({
                    "kind": fitz.LINK_GOTO,
                    "from": fitz.Rect(line["bbox"]),
                    "page": target,
                    "to": fitz.Point(0, 0),
                })
                added += 1
    tmp = pdf + ".linked.tmp"
    doc.save(tmp, garbage=3, deflate=True)
    doc.close()
    os.replace(tmp, pdf)
    print(f"[toc-links] added {added} TOC links")
    return 0


if __name__ == "__main__":
    sys.exit(main())
