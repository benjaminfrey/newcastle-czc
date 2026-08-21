"""W2 Phase 2: parses source/article-09-definitions.md into
rulesets/<ruleset-key>/definitions.json — 272 flat term entries.

Article 9 does NOT follow the "## N. SECTION / ### x. SUBSECTION" grammar
ruleset_build/parse_articles.py handles (it has neither — just a single
"# Article 9 Definitions" H1 over a flat list of bold terms), so it is
parsed here, separately, rather than shoehorned into that module's state
machine.

THE GRAMMAR (verified against the real file):

    # Article 9 Definitions
    **Term:**
    Definition text (one or more lines, blank-line-separated paragraphs).

    **Next Term:**
    ...

270 of 272 entries close the bold term with a colon inside the markers
(`**Term:**`). TWO do not (`**Single Unit Commercial Building**`,
`**Single Unit Residential Building**` — verified at source lines 679/682) —
the colon is simply missing from those two headings in the source. The regex
below treats the colon as optional so all 272 are captured the same way;
this is a mechanical extraction detail with one correct reading (CONTRACT.md
§7.2's "not a DECISIONS-NEEDED item" standard — there is no legal ambiguity
here, just an inconsistent typographic marker), not a judgement call.

A definition may run more than one paragraph (verified: "Road, Primary" and
"Significant Street Tree" each do); `definition` joins all paragraph lines
with a single '\\n' between them, verbatim, never reflowed.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

APP_ROOT = Path(__file__).resolve().parent.parent
REPO_ROOT = APP_ROOT.parent.parent
DEFAULT_SRC = REPO_ROOT / "source" / "article-09-definitions.md"
DEFAULT_RULESET_KEY = "draft-v0.22"

SCHEMA = "newcastle.definitions/1.0.0"
TITLE_RE = re.compile(r"^# Article (\d+) (.+)$")
TERM_RE = re.compile(r"^\*\*(.+?):?\*\*\s*$")


class DefinitionsShapeError(RuntimeError):
    """Raised when article-09-definitions.md doesn't match the grammar this
    module documents. FAIL LOUDLY rather than silently dropping a term."""


def parse_definitions_file(path: Path, ruleset_key: str) -> tuple[dict, list[dict]]:
    raw_text = path.read_text(encoding="utf-8")
    lines = raw_text.split("\n")
    if lines and lines[-1] == "":
        lines = lines[:-1]

    if not lines or lines[0].strip() != "---":
        raise DefinitionsShapeError("file does not start with YAML frontmatter '---'")
    i = 1
    while i < len(lines) and lines[i].strip() != "---":
        i += 1
    if i >= len(lines):
        raise DefinitionsShapeError("frontmatter opened but never closed")
    i += 1

    article_num: int | None = None
    article_name: str | None = None
    title_seen = False

    entries: list[dict] = []
    cur_term: str | None = None
    cur_term_line: int | None = None
    cur_def_lines: list[str] = []

    def flush() -> None:
        nonlocal cur_term, cur_term_line, cur_def_lines
        if cur_term is None:
            return
        # Join collected paragraph lines; a blank line inside a definition
        # separates paragraphs (only 2 of 272 have more than one) — represented
        # as an empty string in the joined-by-'\n' text, matching the source
        # verbatim rather than collapsing it away.
        definition = "\n".join(cur_def_lines).strip("\n")
        if not definition:
            raise DefinitionsShapeError(
                f"source/article-09-definitions.md:{cur_term_line}: term "
                f"{cur_term!r} has no definition text"
            )
        entries.append(
            {
                "id": f"{ruleset_key}:a9.def.{_slug(cur_term)}",
                "article": 9,
                "term": cur_term,
                "definition": definition,
                "source_ref": {"file": "source/article-09-definitions.md", "line": cur_term_line},
            }
        )
        cur_term = None
        cur_term_line = None
        cur_def_lines = []

    n = len(lines)
    while i < n:
        line_no = i + 1
        raw = lines[i]
        stripped = raw.strip()

        if stripped == "":
            i += 1
            continue

        if not title_seen:
            m = TITLE_RE.match(raw)
            if not m:
                raise DefinitionsShapeError(f"line {line_no}: expected '# Article N ...' title")
            article_num = int(m.group(1))
            article_name = m.group(2).strip()
            title_seen = True
            i += 1
            continue

        m = TERM_RE.match(raw)
        if m:
            flush()
            cur_term = m.group(1).strip()
            cur_term_line = line_no
            i += 1
            continue

        if cur_term is None:
            raise DefinitionsShapeError(f"line {line_no}: body text before any '**Term:**' heading")
        cur_def_lines.append(stripped)
        i += 1

    flush()

    seen_terms: dict[str, int] = {}
    for e in entries:
        seen_terms[e["term"]] = seen_terms.get(e["term"], 0) + 1
    dupes = sorted(t for t, c in seen_terms.items() if c > 1)
    if dupes:
        raise DefinitionsShapeError(f"duplicate term(s): {dupes}")

    meta = {
        "article": article_num,
        "article_name": article_name,
        "source_file": "source/article-09-definitions.md",
        "sha256": hashlib.sha256(raw_text.encode("utf-8")).hexdigest(),
        "term_count": len(entries),
    }
    return meta, entries


def _slug(term: str) -> str:
    import unicodedata

    s = term.casefold()
    s = unicodedata.normalize("NFKD", s)
    s = s.replace("\xad", "")
    s = re.sub(r"[^a-z0-9]+", "_", s)
    return s.strip("_")


def build_definitions(ruleset_key: str, src: Path = DEFAULT_SRC) -> dict:
    meta, entries = parse_definitions_file(src, ruleset_key)
    return {
        "schema": SCHEMA,
        "ruleset_key": ruleset_key,
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source": meta,
        "counts": {"terms": len(entries)},
        "definitions": entries,
    }


def find_term(defs_doc: dict, term: str) -> dict | None:
    target = " ".join(term.strip().casefold().split())
    for e in defs_doc["definitions"]:
        if " ".join(e["term"].casefold().split()) == target:
            return e
    return None


def run_verify(src: Path = DEFAULT_SRC, ruleset_key: str = DEFAULT_RULESET_KEY) -> bool:
    try:
        doc = build_definitions(ruleset_key, src)
    except DefinitionsShapeError as exc:
        print(f"FAIL {src.name} — {exc}")
        return False
    if doc["counts"]["terms"] != 272:
        print(f"FAIL {src.name} — expected 272 terms, got {doc['counts']['terms']}")
        return False
    print(f"OK   {src.name} — {doc['counts']['terms']} terms")
    return True


def _atomic_write_json(target: Path, obj: dict) -> None:
    text = json.dumps(obj, indent=2, ensure_ascii=False) + "\n"
    if json.loads(text) != obj:
        raise RuntimeError("round-trip verification failed before write — refusing to write")
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.parent / f"{target.name}.tmp-{os.getpid()}-{os.urandom(3).hex()}"
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            f.write(text)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, target)
        try:
            dir_fd = os.open(target.parent, os.O_RDONLY)
            try:
                os.fsync(dir_fd)
            finally:
                os.close(dir_fd)
        except OSError:
            pass
    finally:
        if tmp.exists():
            tmp.unlink()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ruleset-key", default=DEFAULT_RULESET_KEY)
    parser.add_argument("--src", type=Path, default=DEFAULT_SRC)
    parser.add_argument("--out", type=Path, default=None)
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args(argv)

    if args.verify:
        return 0 if run_verify(args.src, args.ruleset_key) else 1

    doc = build_definitions(args.ruleset_key, args.src)
    out = args.out or (APP_ROOT / "rulesets" / args.ruleset_key / "definitions.json")
    _atomic_write_json(out, doc)
    print(f"wrote {out}")
    print(f"  terms: {doc['counts']['terms']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
