#!/usr/bin/env python3
"""The integrated redline's markdown edition.

Why this exists (decision D1): the redline PDF is gitignored, so the markdown is the
only redline that survives in the repository. The integrated redline never produced
one. This assembles it from a PLAIN-marked stage (czc_redline_stage ... --plain):
one "Redline key:" legend, then every Article under its own heading, its tables and
page notes handled by czc_md's own walker (body_markdown), not a copy of it.

  redline_md.py <plain-stage-dir> <out.md> --title TITLE

Exit 0 = written; 1 = refused (nothing written). The file is written atomically,
and only after every Article succeeded.
"""
from __future__ import annotations

import argparse
import os
import re
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import czc_md  # noqa: E402
import manifest  # noqa: E402

FRONT_RE = re.compile(r"^---\n(.*?)\n---\n", re.S)


class RedlineMdError(Exception):
    pass


def _meta(front: str, key: str) -> str:
    m = re.search(rf'^{key}:\s*"?(.*?)"?\s*$', front, re.M)
    return m.group(1).strip() if m else ""


def assemble(stage: Path, title: str) -> str:
    files = sorted(p for p in stage.glob("article-0*.md") if manifest.PROSE_RE.match(p.name))
    if not files:
        raise RedlineMdError(f"no article-0*.md files in {stage}")
    legend = None
    parts: list[str] = []
    for f in files:
        text = f.read_text(encoding="utf-8")
        m = FRONT_RE.match(text)
        front = m.group(1) if m else ""
        rest = text[m.end():] if m else text
        rest = rest.lstrip("\n")
        this_legend, _sep, body = rest.partition("\n\n")
        if not this_legend.startswith("Redline key:"):
            raise RedlineMdError(f"{f.name} does not open with its 'Redline key:' legend; "
                                 f"it is not a plain-marked file")
        if legend is None:
            legend = this_legend
        elif this_legend != legend:
            raise RedlineMdError(f"{f.name} carries a different 'Redline key:' legend from "
                                 f"the first Article's")
        num = _meta(front, "article-number")
        if not num:
            d = re.match(r"article-0(\d)", f.name)
            num = d.group(1) if d else ""
        if not num.isdigit():
            raise RedlineMdError(f"{f.name}: no article-number in its frontmatter and none "
                                 f"in its filename")
        name = _meta(front, "article-name")
        try:
            body_md = czc_md.body_markdown(int(num), body.lstrip("\n"), src_dir=stage)
        except czc_md.MdError as e:
            raise RedlineMdError(f"{f.name}: {e}") from e
        body_md = body_md.strip("\n")
        first = next((ln for ln in body_md.split("\n") if ln.strip()), "")
        if re.match(rf"# Article {num}\b", first):
            parts.append(body_md)
        else:
            heading = f"# Article {num}: {name}" if name else f"# Article {num}"
            parts.append(heading + "\n\n" + body_md)
    return f"# {title}\n\n{legend}\n\n" + "\n\n".join(parts) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("stage")
    ap.add_argument("out")
    ap.add_argument("--title", required=True)
    a = ap.parse_args(argv)
    try:
        text = assemble(Path(a.stage), a.title)
    except RedlineMdError as e:
        print(f"redline_md: {e}", file=sys.stderr)
        return 1
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=out.parent, prefix=out.name + ".")
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        fh.write(text)
    os.replace(tmp, out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
