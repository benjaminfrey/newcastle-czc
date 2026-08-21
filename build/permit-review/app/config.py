"""Implements CONTRACT.md §1.1 (S3 loopback/port posture) and §2 (directory
layout). Central location for every filesystem path and runtime setting the
app uses — nothing else in the app should compute one of these paths itself.

NEVER logs secrets: safe_env_repr() redacts any environment variable whose
name looks like it holds a credential before it is ever put in a log line.
"""

from __future__ import annotations

import os
from pathlib import Path

# ---------------------------------------------------------------------------
# APP root — every other path in this module resolves relative to this
# directory. CONTRACT.md §1.1 S5: app/paths.py:safe_path() asserts this is a
# parent of every write target; nothing here writes on import.
# ---------------------------------------------------------------------------
APP_ROOT: Path = Path(__file__).resolve().parent.parent


# ---------------------------------------------------------------------------
# Network binding — CONTRACT.md §1.1 S3.
#
# HOST is a module constant. It is NEVER read from a CLI flag, an environment
# variable, or a config key — do not add a way to override it; that is the
# whole point of S3.
# ---------------------------------------------------------------------------
HOST: str = "127.0.0.1"

# CONTRACT.md §1.1 S3 states the default port as 8781, "overridable by
# --port N only" (never an env var, never a config key — same rule as HOST).
# app/main.py's CLI argument parser owns that override; this module only
# supplies the default.
#
# NOTE ON A DISCREPANCY: the task brief that commissioned this module named
# port 8790, but CONTRACT.md — the normative document other modules in this
# app are built against — says 8781. This file follows CONTRACT.md. Flag this
# for Ben/the orchestrator to reconcile if 8790 was actually intended; a
# one-line change here is all a correction would take.
DEFAULT_PORT: int = 8781


# ---------------------------------------------------------------------------
# Filesystem layout — CONTRACT.md §2.
# ---------------------------------------------------------------------------
def _env_path(name: str, default: Path) -> Path:
    """Read a directory override from the environment. Tests-only escape
    hatch (e.g. pointing DATA_DIR at a throwaway temp dir); never used for
    HOST or PORT — S3 forbids an env override for those two specifically.
    """
    raw = os.environ.get(name)
    return Path(raw).resolve() if raw else default


DATA_DIR: Path = _env_path("PERMIT_REVIEW_DATA_DIR", APP_ROOT / "data")
DB_PATH: Path = DATA_DIR / "permit-review.db"
BLOBS_DIR: Path = DATA_DIR / "blobs"
EXPORTS_DIR: Path = DATA_DIR / "exports"  # the ONLY PDF output dir (§2, §8.6)
TMP_DIR: Path = DATA_DIR / "tmp"

MIGRATIONS_DIR: Path = APP_ROOT / "app" / "migrations"
TEMPLATES_DIR: Path = APP_ROOT / "app" / "templates"
STATIC_DIR: Path = APP_ROOT / "app" / "static"

RULESETS_DIR: Path = APP_ROOT / "rulesets"
OVERRIDES_DIR: Path = APP_ROOT / "overrides"

DECISIONS_NEEDED_PATH: Path = APP_ROOT / "DECISIONS-NEEDED.md"

# The one file this project is allowed to write outside APP_ROOT
# (CONTRACT.md §8.2). Not a "safe_path" target — app/paths.py's runtime
# writer guard is APP-only by design; this constant exists so the one
# documented exception has a single named location instead of being
# hand-typed wherever it's needed.
FINDINGS_TEMPLATE_PATH: Path = APP_ROOT.parent.parent / "style" / "findings-template.typ"


# ---------------------------------------------------------------------------
# Misc runtime settings. All environment-overridable; none are secrets, and
# nothing here is a credential of any kind (this workflow handles no PII, no
# uploads, no LLM calls — see CONTRACT.md §1.2).
# ---------------------------------------------------------------------------
ENV: str = os.environ.get("PERMIT_REVIEW_ENV", "development")
LOG_LEVEL: str = os.environ.get("PERMIT_REVIEW_LOG_LEVEL", "INFO").upper()

_SECRET_NAME_MARKERS = ("KEY", "SECRET", "TOKEN", "PASSWORD", "PASSWD", "CREDENTIAL", "AUTH")


def is_secret_env_name(name: str) -> bool:
    """True if an environment variable's NAME looks like it holds a
    credential. Used defensively — this phase has no real secrets, but a
    later phase (llm/) will, and the redaction habit needs to already be in
    place so it's never an afterthought.
    """
    upper = name.upper()
    return any(marker in upper for marker in _SECRET_NAME_MARKERS)


def safe_env_repr() -> dict[str, str]:
    """Return this process's PERMIT_REVIEW_* environment variables in a form
    safe to log or print: any name that looks like it holds a credential is
    redacted, never emitted verbatim. NEVER logs secrets.
    """
    out: dict[str, str] = {}
    for name, value in sorted(os.environ.items()):
        if not name.startswith("PERMIT_REVIEW_"):
            continue
        out[name] = "<redacted>" if is_secret_env_name(name) else value
    return out


def ensure_data_dirs() -> None:
    """Create the gitignored runtime data directories if missing. Idempotent;
    safe to call on every startup and from tests.
    """
    for d in (DATA_DIR, BLOBS_DIR, EXPORTS_DIR, TMP_DIR):
        d.mkdir(parents=True, exist_ok=True)
