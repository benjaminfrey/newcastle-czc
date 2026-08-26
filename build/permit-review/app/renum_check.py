"""Is `RENUM_ADOPTED_TO_DRAFT` still true of the rulesets it claims to relate?

THE INVARIANT: mapping an adopted article number through the map must land on
the draft article **with the same name**. Adopted Article 3 is SITE STANDARDS;
the map sends 3 -> 4; draft Article 4 is Site Standards. That holds for every
adopted article or the map is lying, and it is checkable from the two rulesets
themselves rather than from a hardcoded expectation of what the map should say.

WHY THIS EXISTS. `app/citation.py` holds the single definition of
`RENUM_ADOPTED_TO_DRAFT = {1:1, 2:2, 3:4, 4:5, 5:6, 6:7, 7:8, 8:9}` -- the 2020
Code's eight articles mapped onto the draft's nine, the shift Article 3
(Thoroughfares) opened. **That map stops being true the moment the draft is
adopted.** The adopted Code then IS the nine-article numbering, and the map must
become identity.

Nothing forces that edit, and getting it wrong is silent: citations keep
rendering, they are just off by one from Article 3 on. "Article 8 Section 12"
would print for a standard that now lives at Article 9 -- plausible, wrong, and
attached to a real application. The CZC side has the identical hazard in
`build/adoption-map.json` and guards it with `build/baseline_selfcheck.py`
(baseline compared against itself must mark zero lines); this is the same idea
for the app's own copy of the problem.

IT CATCHES BOTH DIRECTIONS, which is the point:

  - **Stale after adoption.** A new adopted ruleset built from the adopted Code
    has Article 3 = THOROUGHFARES. The map still says 3 -> 4, and draft Article
    4 is Site Standards. Names disagree -> FAIL.
  - **Reset too early.** Someone sets the map to identity while the adopted
    ruleset is still the 2020 Code: adopted Article 3 (Site Standards) maps to
    draft Article 3, which is Thoroughfares. Names disagree -> FAIL.

A map that is merely *plausible* passes neither check; only one that actually
matches both rulesets does.

Reads the committed `rulesets/<key>/` artifacts only, never `source/` -- the
same rule `ruleset_build.verify_structure` follows and for the same reason.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from app.citation import RENUM_ADOPTED_TO_DRAFT

RULESETS = Path(__file__).resolve().parent.parent / "rulesets"
ADOPTED_KEY = "adopted"
DRAFT_KEY = "draft-v0.22"


def _norm(s: str | None) -> str:
    """Compare article names by their words, not their casing or punctuation.

    The two rulesets render the same article differently by design -- the
    adopted tree carries 'SITE STANDARDS', the draft list 'Site Standards'.
    """
    return re.sub(r"[^a-z0-9]+", " ", (s or "").lower()).strip()


def adopted_articles(key: str = ADOPTED_KEY) -> dict[int, str]:
    """{article number: heading} from the adopted ruleset's nested tree."""
    doc = json.loads((RULESETS / key / "articles.json").read_text(encoding="utf-8"))
    return {int(a["article"]): a.get("heading") or ""
            for a in doc.get("articles", []) if a.get("article") is not None}


def draft_articles(key: str = DRAFT_KEY) -> dict[int, str]:
    """{article number: article_name} for the draft ruleset.

    Merges TWO artifacts, because the draft splits what the adopted tree keeps
    together: `articles.json` carries Articles 1-8, and Definitions is built by
    a separate parser into `definitions.json`, which declares its own
    `source.article` (9) and `source.article_name`. Reading only articles.json
    would make this check report that adopted Article 8 (DEFINITIONS) maps to a
    draft Article 9 "which does not exist" -- a false alarm about a real
    difference in ruleset SHAPE, not in the numbering the map describes. The
    adopted ruleset has no separate definitions artifact; its Definitions is
    Article 8 inside articles.json.
    """
    doc = json.loads((RULESETS / key / "articles.json").read_text(encoding="utf-8"))
    out = {int(a["article"]): a.get("article_name") or ""
           for a in doc.get("articles", []) if a.get("article") is not None}
    defs_path = RULESETS / key / "definitions.json"
    if defs_path.exists():
        src = json.loads(defs_path.read_text(encoding="utf-8")).get("source") or {}
        if src.get("article") is not None:
            out.setdefault(int(src["article"]), src.get("article_name") or "Definitions")
    return out


def problems(renum: dict[int, int] | None = None,
             adopted: dict[int, str] | None = None,
             draft: dict[int, str] | None = None) -> list[str]:
    """Everything wrong with the map, as operator-readable lines. Empty == clean.

    Arguments are injectable so the tests can pose a post-adoption world
    without building a ruleset.
    """
    renum = RENUM_ADOPTED_TO_DRAFT if renum is None else renum
    adopted = adopted_articles() if adopted is None else adopted
    draft = draft_articles() if draft is None else draft
    out: list[str] = []

    for n in sorted(adopted):
        name = adopted[n]
        if n not in renum:
            out.append(
                f"adopted Article {n} ({name}) has no entry in "
                f"RENUM_ADOPTED_TO_DRAFT — every adopted article must map "
                f"somewhere, or its citations cannot be rendered.")
            continue
        d = renum[n]
        if d not in draft:
            out.append(
                f"adopted Article {n} ({name}) maps to draft Article {d}, "
                f"which does not exist in the draft ruleset.")
            continue
        if _norm(name) != _norm(draft[d]):
            out.append(
                f"adopted Article {n} is {name!r} but the map sends it to "
                f"draft Article {d}, which is {draft[d]!r}. The map no longer "
                f"describes these two rulesets.")
    return out


def run(quiet: bool = False) -> int:
    found = problems()
    if not found:
        if not quiet:
            print(f"[renum] RENUM_ADOPTED_TO_DRAFT matches both rulesets "
                  f"({len(adopted_articles())} adopted articles checked by name).")
        return 0
    print("RENUM_ADOPTED_TO_DRAFT no longer describes the rulesets:")
    for p in found:
        print(f"  - {p}")
    print("\nIf the draft has been adopted, the adopted Code IS the new numbering: "
          "set\nRENUM_ADOPTED_TO_DRAFT (app/citation.py) to identity and rebuild the "
          "adopted\nruleset from the ADOPTED edition, keeping the superseded one for "
          "cases decided\nunder it.")
    return 1


if __name__ == "__main__":
    raise SystemExit(run())
