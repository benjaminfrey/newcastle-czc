#!/usr/bin/env python3
"""The integrated Code's markdown: the document the Town adopts, in text.

Each Article keeps its frontmatter block exactly as the source has it (the three
keys build-adopted.sh's identity gate strips) and its body runs through
czc_md.body_markdown -- tables as markdown tables, pointer notes where native
pages sit, no build comments -- with Article 2's generated district appendix in
place of its pointer. There is NO title, provenance or mode line: the mode lives
in the file name and the PDF cover, never in the body, so the meeting and adopted
editions' markdown is byte-identical.

CLI:  integrated_md.py <src-dir> <out.md>     exit 0 written, 1 refused (nothing written)
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import czc_md  # noqa: E402
import manifest  # noqa: E402

MdError = czc_md.MdError


def render(src_dir: Path, *, doc: dict | None = None) -> str:
    src_dir = Path(src_dir)
    doc = manifest.load() if doc is None else doc
    parts = []
    for nn in range(1, 10):
        entry = czc_md._article_entry(doc, nn)
        prose = czc_md._prose_path(nn, entry, src_dir)
        text = prose.read_text(encoding="utf-8")
        body = czc_md.body_markdown(nn, text, src_dir=src_dir, doc=doc, appendix=True)
        fm = czc_md.frontmatter_block(text)
        parts.append((fm + "\n\n" if fm else "") + body.strip("\n") + "\n")
    return "\n".join(parts)


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 2:
        print("usage: integrated_md.py <src-dir> <out.md>", file=sys.stderr)
        return 1
    out = Path(argv[1])
    tmp = out.with_name(out.name + ".partial")
    try:
        text = render(Path(argv[0]))
        tmp.write_text(text, encoding="utf-8")
        os.replace(tmp, out)
    except (MdError, OSError) as e:
        tmp.unlink(missing_ok=True)
        print(f"integrated_md: refusing -- {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
