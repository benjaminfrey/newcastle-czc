"""Does every adopted Code's article map still describe its ruleset?

THE INVARIANT: mapping an adopted article number through its Code's map must
land on the draft article **with the same name**. The 2020 Code's Article 3 is
SITE STANDARDS; its map sends 3 -> 4; draft Article 4 is Site Standards. That
holds for every article of every adopted Code or the map is lying, and it is
checkable from the rulesets themselves rather than from a hardcoded expectation
of what a map should say.

WHY THIS EXISTS. `app/citation.py` owns the numbering maps. The 2020 Code's
`RENUM_ADOPTED_TO_DRAFT = {1:1, 2:2, 3:4, 4:5, 5:6, 6:7, 7:8, 8:9}` is the shift
Article 3 (Thoroughfares) opened. When Town Meeting adopted CZC v1.0 on
September 14, 2026, the adopted Code BECAME the nine-article numbering. Getting
that wrong is silent: citations keep rendering, just off by one from Article 3
on -- "Article 8 Section 12" printed for a standard at Article 9, plausible,
wrong, and attached to a real application.

HOW THE ROLLOVER WAS DONE, AND WHY NOT BY EDITING THE MAP. The obvious move --
reset `RENUM_ADOPTED_TO_DRAFT` to identity -- would renumber every citation of
every case decided under the 2020 Code. So the 2020 Code keeps its ruleset
(`rulesets/adopted`, status "superseded"), its scheme ("adopted") and its map,
permanently; v1.0 got its own binding ruleset (`rulesets/adopted-v1.0`), its own
scheme ("adopted-v1.0") and an identity map. This module checks EVERY binding
ruleset on disk against the draft, each through the map its manifest's
`article_scheme` names. The CZC side guards its own copy of the rollover with
`build/baseline_selfcheck.py`.

IT CATCHES BOTH DIRECTIONS, for each Code:

  - **Stale.** A nine-article ruleset read through the shifted map: its Article
    3 (Thoroughfares) lands on draft Article 4 (Site Standards) -> FAIL.
  - **Reset too early / wrong map.** The 2020 ruleset read through identity:
    its Article 3 (Site Standards) lands on draft Thoroughfares -> FAIL.

And it fails a binding ruleset whose `article_scheme` has no map at all -- the
shape a future adoption takes if someone builds its ruleset and forgets the map.

Reads the committed `rulesets/<key>/` artifacts only, never `source/` -- the
same rule `ruleset_build.verify_structure` follows and for the same reason.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from app.citation import RENUM_ADOPTED_TO_DRAFT, SCHEME_TO_DRAFT

RULESETS = Path(__file__).resolve().parent.parent / "rulesets"
ADOPTED_KEY = "adopted"  # the 2020 Code (superseded 2026-09-14); kept for its tests and callers
DRAFT_KEY = "draft-v0.22"


def _norm(s: str | None) -> str:
    """Compare article names by their words, not their casing or punctuation.

    The rulesets render the same article differently by design -- the 2020
    tree carries 'SITE STANDARDS', the draft list 'Site Standards'.
    """
    return re.sub(r"[^a-z0-9]+", " ", (s or "").lower()).strip()


def ruleset_articles(key: str) -> dict[int, str]:
    """{article number: name} for any ruleset, in either artifact shape.

    - The 2020 ruleset (`extract_adopted.py`, from the PDF) is a nested TREE:
      `articles[]` carry `heading`, and Definitions is Article 8 inside it.
    - A ruleset parsed from markdown (the draft, and CZC v1.0) is FLAT:
      `articles[]` carry `article_name`, and Definitions is built by a separate
      parser into `definitions.json`, which declares its own `source.article`.
      Reading only articles.json there reports that Definitions "does not
      exist" -- a false alarm about ruleset SHAPE, not numbering.
    """
    doc = json.loads((RULESETS / key / "articles.json").read_text(encoding="utf-8"))
    if isinstance(doc.get("nodes"), list):
        out = {int(a["article"]): a.get("article_name") or ""
               for a in doc.get("articles", []) if a.get("article") is not None}
        defs_path = RULESETS / key / "definitions.json"
        if defs_path.exists():
            src = json.loads(defs_path.read_text(encoding="utf-8")).get("source") or {}
            if src.get("article") is not None:
                out.setdefault(int(src["article"]), src.get("article_name") or "Definitions")
        return out
    return {int(a["article"]): a.get("heading") or ""
            for a in doc.get("articles", []) if a.get("article") is not None}


def adopted_articles(key: str = ADOPTED_KEY) -> dict[int, str]:
    """{article number: heading} for an adopted ruleset (default: the 2020 Code)."""
    return ruleset_articles(key)


def draft_articles(key: str = DRAFT_KEY) -> dict[int, str]:
    """{article number: article_name} for the draft ruleset, Definitions included."""
    return ruleset_articles(key)


def binding_rulesets() -> list[tuple[str, dict]]:
    """(ruleset_key, manifest) for every binding ruleset on disk -- the Code in
    force and every Code it superseded."""
    out = []
    for path in sorted(RULESETS.glob("*/manifest.json")):
        manifest = json.loads(path.read_text(encoding="utf-8"))
        if manifest.get("binding"):
            out.append((path.parent.name, manifest))
    return out


def _pair_problems(renum: dict[int, int], adopted: dict[int, str], draft: dict[int, str],
                   *, map_name: str = "RENUM_ADOPTED_TO_DRAFT") -> list[str]:
    out: list[str] = []
    for n in sorted(adopted):
        name = adopted[n]
        if n not in renum:
            out.append(
                f"adopted Article {n} ({name}) has no entry in {map_name} — "
                f"every adopted article must map somewhere, or its citations "
                f"cannot be rendered.")
            continue
        d = renum[n]
        if d not in draft:
            out.append(
                f"adopted Article {n} ({name}) maps to draft Article {d}, "
                f"which does not exist in the draft ruleset.")
            continue
        if _norm(name) != _norm(draft[d]):
            out.append(
                f"adopted Article {n} is {name!r} but {map_name} sends it to "
                f"draft Article {d}, which is {draft[d]!r}. The map no longer "
                f"describes these two rulesets.")
    return out


def edition_problems(key: str, manifest: dict, adopted: dict[int, str],
                     draft: dict[int, str]) -> list[str]:
    """Problems for ONE binding ruleset, read through the map its manifest's
    `article_scheme` names. Prefixed with the ruleset key."""
    scheme = manifest.get("article_scheme")
    renum = SCHEME_TO_DRAFT.get(scheme)
    if renum is None or scheme == "draft":
        return [f"[{key}] binding ruleset declares article_scheme {scheme!r}, which has no "
                f"adopted-Code map in app/citation.py SCHEME_TO_DRAFT — its citations "
                f"cannot be numbered."]
    return [f"[{key}] {p}" for p in _pair_problems(
        renum, adopted, draft, map_name=f"SCHEME_TO_DRAFT[{scheme!r}]")]


def problems(renum: dict[int, int] | None = None,
             adopted: dict[int, str] | None = None,
             draft: dict[int, str] | None = None) -> list[str]:
    """Everything wrong, as operator-readable lines. Empty == clean.

    With no arguments: every binding ruleset on disk, each through its own map.
    With any argument: ONE map against one pair of article-name tables (the
    2020 map and the 2020 ruleset by default) -- injectable so tests can pose a
    world without building a ruleset.
    """
    if renum is not None or adopted is not None or draft is not None:
        return _pair_problems(
            RENUM_ADOPTED_TO_DRAFT if renum is None else renum,
            adopted_articles() if adopted is None else adopted,
            draft_articles() if draft is None else draft,
        )
    rulesets = binding_rulesets()
    if not rulesets:
        return [f"no binding ruleset found under {RULESETS}"]
    draft_names = draft_articles()
    out: list[str] = []
    for key, manifest in rulesets:
        out.extend(edition_problems(key, manifest, ruleset_articles(key), draft_names))
    return out


def run(quiet: bool = False) -> int:
    found = problems()
    if not found:
        if not quiet:
            keys = ", ".join(k for k, _ in binding_rulesets())
            print(f"[renum] every adopted Code's article map matches the draft by name ({keys}).")
        return 0
    print("An adopted Code's article map no longer describes its ruleset:")
    for p in found:
        print(f"  - {p}")
    print("\nA Code adopted at Town Meeting gets its OWN binding ruleset, article_scheme and\n"
          "map in app/citation.py SCHEME_TO_DRAFT (identity if it keeps the draft's\n"
          "numbering). Never edit an existing Code's map: cases decided under it cite it.")
    return 1


if __name__ == "__main__":
    raise SystemExit(run())
