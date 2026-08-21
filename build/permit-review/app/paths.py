"""Implements CONTRACT.md §1.1 S5 (no writes outside `APP`).

`safe_path()` is the one helper CONTRACT.md's directory layout (§2) names for
this rule: resolve a target path and assert `APP_ROOT` (this project's own
root, `build/permit-review/`) is one of its parents, before any write touches
it. The one documented exception, `style/findings-template.typ`
(CONTRACT.md §8.2), is a compile-time file this project creates once, not a
runtime write target -- app/config.py's FINDINGS_TEMPLATE_PATH names it
separately and does not route through this function.

Every writer in this app already enforces its own containment inline
(app/main.py's `_rel_export_path()` for `data/exports/`,
`render/build-findings.sh`'s directory check for the same) -- this module
exists so a *new* writer has one shared, named place to call instead of
re-deriving the same check a third time.
"""

from __future__ import annotations

from pathlib import Path

from app.config import APP_ROOT


class UnsafePath(ValueError):
    """Raised when a target path resolves outside APP_ROOT (CONTRACT.md §1.1 S5)."""


def safe_path(p: str | Path) -> Path:
    """Resolve `p` and assert it is APP_ROOT itself or falls somewhere under
    it. Raises UnsafePath (never silently truncates or rewrites the path) if
    not -- path traversal (`../../etc`, an absolute path elsewhere, a symlink
    escaping APP_ROOT) is rejected before any I/O, per CONTRACT.md §1.1 S5.
    """
    root = APP_ROOT.resolve()
    target = (root / p).resolve() if not Path(p).is_absolute() else Path(p).resolve()
    if target != root and root not in target.parents:
        raise UnsafePath(f"{target} is outside APP_ROOT ({root}) -- refusing to write")
    return target
