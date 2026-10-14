"""A superseded ruleset's content is immutable. This refuses to overwrite it.

THE HAZARD. `build_ruleset.py` orchestrates the 2020 Code's extraction, and two of
its steps write into `rulesets/adopted/` from whatever is in the working tree:
`extract_adopted.main([])` rebuilds `articles.json` from the baseline PDF, and
`lift_use_matrix.main([])` rebuilds `use-matrix.json` from
`source/article-02-data.json` — which has moved on since 2020 (Article 2's district
pages were restored in the v1.0 cycle, and the Right-to-Farm amendment will add a
fifth status code to it). Re-running the orchestrator for any reason therefore
rewrites the record of a Code that is no longer in force, from source text that Code
never contained.

WHY THAT MATTERS. `rulesets/adopted` is the Code adopted November 3, 2020 and
superseded by CZC v1.0 on September 14, 2026. It is kept, rather than deleted,
precisely so that a case decided under it keeps citing the law that applied to it —
`rulesets` plus per-case pinning exist for that. Nine sample decisions cite it, and
`run.py --verify-citations` resolves 157 citations against it. Silently rebuilding it
would move the ground under decided cases, and nothing in the app would notice: the
rebuild succeeds, the counts look plausible, and the manifest's `content_sha256`
updates to match the new bytes.

THE RULE. A ruleset whose manifest says `status: "superseded"` may not have its
CONTENT rewritten. Its `manifest.json` may still be written — that is how
supersession is recorded, and how `build_edition.py` marks the Code it replaces —
so the guard exempts that one filename and nothing else.

To build a newly adopted Code, use `ruleset_build/build_edition.py`, which renders
from the release tag rather than the working tree.
"""

from __future__ import annotations

import json
from pathlib import Path

APP_ROOT = Path(__file__).resolve().parent.parent
RULESETS_DIR = APP_ROOT / "rulesets"

#: The one file a superseded ruleset may still have written: supersession is
#: recorded in it, by build_edition.py.
MANIFEST = "manifest.json"


class SupersededRuleset(RuntimeError):
    """An attempt to rewrite the content of a superseded ruleset. Nothing was written."""


def _status(ruleset_key: str) -> str | None:
    path = RULESETS_DIR / ruleset_key / MANIFEST
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8")).get("status")
    except json.JSONDecodeError:
        return None


def refuse_if_superseded(ruleset_key: str, *, writing: str = "content") -> None:
    """Raise SupersededRuleset if `ruleset_key`'s manifest says it is superseded.

    Call before building, not after: the point is that nothing is written, and a
    rebuild of the 2020 Code takes minutes before it would reach its first write.
    """
    if _status(ruleset_key) != "superseded":
        return
    manifest = json.loads((RULESETS_DIR / ruleset_key / MANIFEST).read_text(encoding="utf-8"))
    by = (manifest.get("superseded_by") or {}).get("ruleset_key", "a later adoption")
    on = (manifest.get("superseded_by") or {}).get("on", "an unrecorded date")
    raise SupersededRuleset(
        f"refusing to write {writing} into ruleset {ruleset_key!r}: it was superseded by "
        f"{by!r} on {on}, and its content is the record decided cases cite.\n"
        f"Nothing was written.\n"
        f"  - To build a newly adopted Code, run ruleset_build/build_edition.py, which renders "
        f"from the release tag rather than the working tree.\n"
        f"  - To rebuild the CURRENT Code's artifacts, pass that ruleset's key explicitly.\n"
        f"  - If you genuinely mean to change a superseded record, say so in "
        f"DECISIONS-NEEDED.md first; this guard is not the place to decide it."
    )


def refuse_if_superseded_path(out_path: Path | str) -> None:
    """Path-shaped form of the guard, for writers that take an --out.

    A path of the form `rulesets/<key>/<file>` is checked against `<key>`; anything
    else — a temp directory in a test, an export, a path outside rulesets/ — is left
    alone, because this guard protects one specific thing and should not become a
    general write interceptor.
    """
    p = Path(out_path).resolve()
    if p.name == MANIFEST:
        return
    try:
        p.parent.relative_to(RULESETS_DIR)
    except ValueError:
        return
    refuse_if_superseded(p.parent.name, writing=p.name)
