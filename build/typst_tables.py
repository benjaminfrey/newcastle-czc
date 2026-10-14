#!/usr/bin/env python3
"""Article 3's raw-Typst tables, as readable markdown tables.

Article 3 authors Tables 3.2-3.5 as raw-Typst blocks so each caption stays locked
to its grid in the PDF. In a markdown deliverable those blocks are Typst source,
not a table a resident can read. This converts the ONE measured shape:

    ```{=typst}
    // optional comment lines
    #block(breakable: false)[
      TABLE n.m TITLE

      #table(
        columns: (<fr list>),
        align: left,
        table.header([A], [B], ...),
        [cell], [cell], ...,
        ...
      )
    ]
    ```

into a caption paragraph and a pipe table, the form the Code's markdown tables
already take (Article 4's TABLE 4.1). Anything else -- another argument, a
table.cell, a span, Typst code or markup (# $ \\ ~ @ <) in a cell or the
caption, a header line after a data row, a short row -- returns None, and the
caller writes a note naming the table instead. Garbled output is never right; a
note is.
"""
from __future__ import annotations

import re

_CAPTION = re.compile(r"((?:TABLE|FIGURE|EXHIBIT)\s+\d+(?:\.\d+)?[A-Za-z]?\b.*)")
_COLUMNS = re.compile(r"columns\s*:\s*\(([^()]*)\)\s*,?")
_ALIGN = re.compile(r"align\s*:\s*left\s*,?")
_HEADER = re.compile(r"table\.header\((.*)\)\s*,?")
_ROW = re.compile(r"(?:\[[^\[\]]*\]\s*,\s*)*\[[^\[\]]*\]\s*,?")
_CELL = re.compile(r"\[([^\[\]]*)\]")
_BOLD = re.compile(r"(?<![*\w])\*([^*\n]+)\*(?![*\w])")


def _cell(text: str) -> str | None:
    text = " ".join(text.split())
    if any(ch in text for ch in "#$\\~@<"):
        return None                                # Typst code, not text: refuse
    return _BOLD.sub(r"**\1**", text).replace("|", r"\|")


def to_markdown(block: str) -> str | None:
    lines = block.split("\n")
    if len(lines) < 3 or not lines[0].strip().startswith("```{=typst}") or lines[-1].strip() != "```":
        return None
    body = [ln.strip() for ln in lines[1:-1]]
    body = [ln for ln in body if ln and not ln.startswith("//")]
    if len(body) < 6 or body[0] != "#block(breakable: false)[" or body[-1] != "]":
        return None
    m = _CAPTION.fullmatch(body[1])
    if not m or body[2] != "#table(" or body[-2] != ")":
        return None
    caption = _cell(m.group(1))
    if caption is None:
        return None
    ncols, header, rows = None, None, []
    for ln in body[3:-2]:
        c = _COLUMNS.fullmatch(ln)
        if c:
            ncols = len([x for x in c.group(1).split(",") if x.strip()])
            continue
        if _ALIGN.fullmatch(ln):
            continue
        h = _HEADER.fullmatch(ln)
        if h:
            if header is not None or rows or not _ROW.fullmatch(h.group(1).strip()):
                return None
            header = _CELL.findall(h.group(1))
            continue
        if _ROW.fullmatch(ln):
            rows.append(_CELL.findall(ln))
            continue
        return None
    if not ncols or header is None or len(header) != ncols or not rows:
        return None
    if any(len(r) != ncols for r in rows):
        return None
    cells = [[_cell(x) for x in r] for r in [header, *rows]]
    if any(x is None for r in cells for x in r):
        return None
    out = [caption, "",
           "| " + " | ".join(cells[0]) + " |",
           "| " + " | ".join(":---" for _ in range(ncols)) + " |"]
    out += ["| " + " | ".join(r) + " |" for r in cells[1:]]
    return "\n".join(out)
