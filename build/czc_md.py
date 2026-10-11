#!/usr/bin/env python3
"""The honest standalone markdown for one Article of the Core Zoning Code.

Until now a standalone Article's ``.md`` was a byte copy of its source: raw
Typst blocks where its tables sit, build comments, a stale "Draft v0.2-draft"
footer line, and -- for Article 2 -- none of the thirteen district pages at all.
This module builds the markdown instead: the Article's own text, its tables as
markdown tables, a note naming each page the PDF has and the markdown cannot
hold (at the place it sits), and a line saying the integrated Code governs and
this extract does not.

What an Article's ``.md`` holds is declared in build/article-manifest.json as
``md_completeness``:

  complete             all of the Article (it has no native pages)
  prose-only           its text; native pages are named by pointer notes
  prose-plus-appendix  its text plus a generated appendix of its native pages

A declaration that contradicts the Article's units is refused: claiming
"complete" for an Article with native pages would ship the gap silently.

CLI:  czc_md.py <article-NN> <out.md> [--src-dir DIR] [--mode draft|meeting|adopted]
                [--version V]            exit 0 written, 1 refused (nothing written)
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import manifest  # noqa: E402
import structure_text  # noqa: E402
import typst_tables  # noqa: E402
import use_table_changes  # noqa: E402
import version_state  # noqa: E402

SOURCE = HERE.parent / "source"
MODES = ("draft", "meeting", "adopted")
COMPLETENESS = ("complete", "prose-only", "prose-plus-appendix")
# nn -> callable(src_dir: Path) -> str.  Article 2's is registered below.
APPENDICES: dict = {}

_FENCE = re.compile(r"^[ \t]*(`{3,}|~{3,})(.*)$")


class MdError(Exception):
    """A refusal: the markdown would not be honest, so nothing is written."""


def _check_version(mode: str, version: str) -> None:
    """The version must say what the mode says: a whole vN.0 is an adoption
    version, a decimal is a draft -- the rule build/adoption-footer.sh enforces
    for the PDF."""
    if not version:
        raise MdError("a version is required (the provenance line names it)")
    try:
        version_state.parse(version)
    except ValueError as e:
        raise MdError(str(e)) from None
    adoption = version_state.is_adoption_version(version)
    if mode == "draft" and adoption:
        raise MdError(f"mode draft cannot carry the adoption version {version}")
    if mode != "draft" and not adoption:
        raise MdError(f"mode {mode} needs an adoption version (vN.0), not {version}")


def _join_labels(labels: list) -> str:
    if len(labels) <= 2:
        return " and ".join(labels)
    return "; ".join(labels[:-1]) + "; and " + labels[-1]


def _article_entry(doc: dict, nn: int) -> dict:
    entry = doc.get(str(nn))
    if not isinstance(entry, dict) or "units" not in entry:
        raise MdError(f"Article {nn} is not in the manifest")
    return entry


def _check_completeness(nn: int, entry: dict) -> str:
    kind = entry.get("md_completeness")
    if kind not in COMPLETENESS:
        raise MdError(f"Article {nn} declares md_completeness {kind!r}; "
                      f"it must be one of {', '.join(COMPLETENESS)}")
    if kind == "complete" and entry["units"]:
        raise MdError(f"Article {nn} declares md_completeness 'complete' but has native "
                      f"pages ({', '.join(u['label'] for u in entry['units'])}); "
                      f"the markdown would silently omit them")
    if kind in ("prose-only", "prose-plus-appendix") and not entry["units"]:
        raise MdError(f"Article {nn} declares md_completeness {kind!r} but has no native "
                      f"pages; it is 'complete'")
    if kind == "prose-plus-appendix":
        stray = [u["label"] for u in entry["units"] if u.get("splice") != "after-prose"]
        if stray:
            raise MdError(f"Article {nn} declares an appendix but {', '.join(stray)} "
                          f"sit inside the text, not after it")
        if nn not in APPENDICES:
            raise MdError(f"Article {nn} declares an appendix but no appendix generator "
                          f"is registered for it")
    return kind


def _prose_path(nn: int, entry: dict, src_dir: Path) -> Path:
    name = entry.get("prose")
    if name:
        path = src_dir / name
        if not path.is_file():
            raise MdError(f"Article {nn}'s prose {name} is not in {src_dir}")
        return path
    found = sorted(p for p in src_dir.glob(f"article-0{nn}-*.md") if manifest.PROSE_RE.match(p.name))
    if len(found) != 1:
        raise MdError(f"Article {nn}: expected exactly one article-0{nn}-*.md in {src_dir}, "
                      f"found {len(found)}")
    return found[0]


def _split_frontmatter(text: str) -> tuple[list[str], str]:
    lines = text.split("\n")
    if lines and lines[0].strip() == "---":
        for i in range(1, len(lines)):
            if lines[i].strip() == "---":
                return lines[1:i], "\n".join(lines[i + 1:])
    return [], text


def _unit_pointer(label: str) -> str:
    return f"*[{label} — in the PDF edition; not reproduced in this markdown version.]*"


def _active_units(entry: dict, src_dir: Path) -> list:
    """Units that actually render: a unit conditional on a missing file is skipped,
    as in the PDF build."""
    out = []
    for u in entry["units"]:
        cond = u.get("conditional_on")
        if cond and not (src_dir / cond).exists():
            continue
        out.append(u)
    return out


def _walk_body(body: str, entry: dict, units: list) -> tuple[str, set]:
    markers = entry.get("split_markers", [])
    out: list[str] = []
    placed: set = set()
    lines = body.split("\n")
    i = 0
    while i < len(lines):
        line = lines[i]
        fence = _FENCE.match(line)
        if fence:
            ticks, info = fence.group(1), fence.group(2).strip()
            j = i + 1
            while j < len(lines):
                m = _FENCE.match(lines[j])
                if m and m.group(1)[0] == ticks[0] and len(m.group(1)) >= len(ticks) \
                        and not m.group(2).strip():
                    break
                j += 1
            block_lines = lines[i:j + 1]
            if info == "{=typst}":
                block = "\n".join(block_lines)
                table = typst_tables.to_markdown(block) if j < len(lines) else None
                if table is None:
                    cap = structure_text.block_caption(block)
                    out.append(f"*[{cap} — shown in the PDF edition; "
                               f"it could not be reproduced as text here.]*")
                else:
                    out.append(table.strip("\n"))
            else:
                out.extend(block_lines)
            i = j + 1
            continue
        stripped = line.strip()
        if stripped.startswith("<!--"):
            j = i
            while j < len(lines) and "-->" not in lines[j]:
                j += 1
            if j >= len(lines):
                raise MdError(f"unclosed HTML comment starting at line {i + 1} of the body; "
                              f"it would hide the rest of the markdown")
            comment = "\n".join(lines[i:j + 1])
            # a whole-line comment only: nothing may follow the closing "-->"
            if j < len(lines) and lines[j].strip().endswith("-->"):
                hit = [m for m in markers if m in comment]
                for m in hit:
                    ptrs = [_unit_pointer(u["label"]) for u in units
                            if u.get("splice") == f"at-marker:{m}"]
                    if ptrs:
                        out.append("\n\n".join(ptrs))
                        placed.update(id(u) for u in units if u.get("splice") == f"at-marker:{m}")
                i = j + 1
                continue
        out.append(line)
        i += 1
    return "\n".join(out), placed


# --- Article 2's appendix: the thirteen district pages ---------------------------

def _esc_text(s: str) -> str:
    """A leading '#' would read as a heading."""
    s = str(s)
    return "\\" + s if s.startswith("#") else s


def _cell(s) -> str:
    return str(s).replace("|", "\\|")


def _list_lines(items: list) -> list[str]:
    out: list[str] = []
    for it in items:
        if isinstance(it, dict):
            out.append(f"- {_esc_text(it.get('text', ''))}")
            out.extend(f"  - {_esc_text(sub)}" for sub in it.get("sub") or [])
        else:
            out.append(f"- {_esc_text(it)}")
    return out


def _panel(panel: dict) -> str:
    lines = [f"**{panel['title']}**", ""]
    kind, body = panel["kind"], panel["body"]
    if kind == "lv":
        lines += ["| Item | Standard |", "| :--- | :--- |"]
        lines += [f"| {_cell(a)} | {_cell(b)} |" for a, b in body]
    elif kind == "list":
        lines += _list_lines(body)
    elif kind == "para":
        lines.append(_esc_text(body))
    else:
        raise MdError(f"a district panel of unknown kind {kind!r}")
    return "\n".join(lines)


def _matrix(m: dict | None) -> str:
    if not m:
        return "*No Permitted Buildings matrix.*"
    cols = m["cols"]
    lines = [f"**{m['title']}**", "", "|  | " + " | ".join(_cell(c) for c in cols) + " |",
             "| " + " | ".join([":---"] * (len(cols) + 1)) + " |"]
    for row in m["rows"]:
        lines.append("| " + " | ".join(_cell(c) for c in row) + " |")
    return "\n".join(lines)


def article2_appendix(src_dir: Path) -> str:
    """All thirteen districts as markdown, from the data and the legend the PDF's
    district pages are printed from (one legend reader: use_table_changes)."""
    src_dir = Path(src_dir)
    try:
        legend = use_table_changes.parse_legend((src_dir / "article-02.typ").read_text(encoding="utf-8"))
        data = json.loads((src_dir / "article-02-data.json").read_text(encoding="utf-8"))
    except (OSError, ValueError, use_table_changes.LegendError) as e:
        raise MdError(f"the Article 2 appendix cannot be built: {e}") from None
    blocks = [
        "## Appendix — District Standards",
        "*Generated from the district data the PDF edition's district pages are printed from. "
        "Use statuses are given in words; the PDF shows them as symbols.*",
    ]
    bullets = [f"- {label.removesuffix(' Required')} — issued by {authority}"
               for label, authority in legend["rows"].values()]
    bullets.append("- A use with no status is not allowed in that District.")
    blocks.append("**Use table legend**\n\n" + "\n".join(bullets))
    for rec in data:
        blocks.append(f"### {rec['code']} {rec['name']}")
        for panel in list(rec.get("left") or []) + list(rec.get("right") or []):
            blocks.append(_panel(panel))
        blocks.append(_matrix(rec.get("matrix")))
        for col in ("use_col1", "use_col2"):
            for cat in rec.get(col) or []:
                if not cat["entries"]:
                    continue
                lines = [f"**{use_table_changes._category(rec, col, cat['title'])}**", "",
                         "| Use | Status |", "| :--- | :--- |"]
                lines += [f"| {_cell(u)} | {_cell(use_table_changes.status_words(s, legend))} |"
                          for u, s in cat["entries"]]
                blocks.append("\n".join(lines))
        us = rec.get("use_standards")
        if us:
            blocks.append(f"**{us['title']}**\n\n" + "\n".join(_list_lines(us["items"])))
    return "\n\n".join(blocks) + "\n"


APPENDICES[2] = article2_appendix


def render(nn: int, *, src_dir: Path = SOURCE, mode: str = "draft",
           version: str = "", doc: dict | None = None) -> str:
    if mode not in MODES:
        raise MdError(f"unknown mode {mode!r}; it must be one of {', '.join(MODES)}")
    _check_version(mode, version)
    src_dir = Path(src_dir)
    doc = manifest.load() if doc is None else doc
    entry = _article_entry(doc, nn)
    kind = _check_completeness(nn, entry)
    prose = _prose_path(nn, entry, src_dir)
    fm_lines, body = _split_frontmatter(prose.read_text(encoding="utf-8"))
    kept = [ln for ln in fm_lines
            if ln.strip().startswith(("article-number:", "article-name:"))]
    units = _active_units(entry, src_dir)

    text, placed = _walk_body(body, entry, units)
    text = text.strip("\n")

    unplaced = [u["label"] for u in units
                if u.get("splice", "").startswith("at-marker:") and id(u) not in placed]
    if unplaced:
        raise MdError(f"Article {nn}: the split marker for {', '.join(unplaced)} is not in "
                      f"{prose.name}; the markdown cannot say where they sit")

    after = [u for u in units if u.get("splice") == "after-prose"]
    tail = ""
    if kind == "prose-plus-appendix":
        tail = "\n\n" + str(APPENDICES[nn](src_dir)).strip("\n")
    elif after:
        tail = "\n\n" + "\n\n".join(_unit_pointer(u["label"]) for u in after)

    ver = f" ({version})"
    phrase = {"draft": f"a working draft{ver}",
              "meeting": f"the Town Meeting edition{ver}, not yet adopted",
              "adopted": f"adopted{ver}"}[mode]
    head = [f"*This is a standalone extract of one Article of the Newcastle Core Zoning Code — "
            f"{phrase}. The integrated Code is the document the Town adopts; this extract "
            f"does not govern.*"]
    if kind != "complete":
        labels = _join_labels([u["label"] for u in units])
        where = ("The district pages are reproduced below as a generated appendix."
                 if kind == "prose-plus-appendix"
                 else "They are named below where they appear.")
        if labels:
            head.append(f"*The PDF edition also contains {labels}. {where} "
                        f"The PDF edition is authoritative for them.*")

    return ("---\n" + "\n".join(kept) + "\n---\n\n" + "\n\n".join(head) + "\n\n"
            + text + tail + "\n")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("article", help="Article number, e.g. 03 or 3")
    ap.add_argument("out", help="markdown file to write")
    ap.add_argument("--src-dir", default=str(SOURCE))
    ap.add_argument("--mode", default="draft", choices=MODES)
    ap.add_argument("--version", default="")
    a = ap.parse_args(argv)
    try:
        nn = int(a.article)
        text = render(nn, src_dir=Path(a.src_dir), mode=a.mode, version=a.version)
    except (MdError, ValueError) as e:
        print(f"czc_md: refusing -- {e}", file=sys.stderr)
        return 1
    Path(a.out).write_text(text, encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
