"""Implements CONTRACT.md §1 (S3/S4/S6), §6 (HTTP API), §2 (directory layout).

The FastAPI app factory, safety middleware, the three v1 routes, and the
offline `--selftest` entry point.

W1 SCOPE (Phases 0-1 only): no uploads, no OCR, no LLM, no PII, no referral
tracking. This module is deliberately written to run and degrade gracefully
even before its sibling modules (app/db.py, app/audit.py, app/dates.py,
app/rulesets.py, render/worksheet.py) exist -- each is imported defensively
and a clear, non-crashing message is surfaced wherever one is missing. Once
those modules land (matching the signatures in CONTRACT.md), this file's
behavior upgrades automatically with no code change here.
"""

from __future__ import annotations

import hashlib
import importlib
import json
import re
import shutil
import tempfile
from contextlib import asynccontextmanager
from datetime import date, timedelta
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from . import citation

# F10 -- Starlette 1.6+'s own request-body-size-limit middleware. FastAPI
# (as of the version pinned in requirements.txt) does not yet expose this via
# a FastAPI(...)/`app.max_body_size` constructor kwarg the way plain
# Starlette does (FastAPI overrides build_middleware_stack() without that
# branch -- verified against this repo's pinned fastapi/starlette), so it has
# to be added explicitly as user middleware (see create_app()) rather than
# by setting `app.max_body_size`. Imported defensively, matching every other
# optional-dependency seam in this module: an older Starlette without this
# class simply means the guard degrades to "not installed" rather than the
# app failing to start (app/blobs.py's own in-route MAX_UPLOAD_BYTES check
# still applies either way, just later than F10 wants).
try:
    from starlette.middleware.body_limit import RequestBodyLimitMiddleware
except Exception:  # noqa: BLE001 - degrade-gracefully boundary, same as _try_import above
    RequestBodyLimitMiddleware = None

# --------------------------------------------------------------------------- #
# Defensive imports of sibling modules this workflow does not own.
# Each is optional at runtime: if absent, the affected feature degrades with a
# clear message instead of the app crashing on startup or on a request.
# --------------------------------------------------------------------------- #


def _try_import(module_name: str) -> tuple[Any, str | None]:
    try:
        return importlib.import_module(module_name), None
    except Exception as exc:  # noqa: BLE001 - deliberately broad; this is a degrade-gracefully boundary
        return None, f"{type(exc).__name__}: {exc}"


config_mod, _config_err = _try_import("app.config")
security_mod, _security_err = _try_import("app.security")
db_mod, _db_err = _try_import("app.db")
audit_mod, _audit_err = _try_import("app.audit")
dates_mod, _dates_err = _try_import("app.dates")  # CONTRACT.md §2's named home
meetings_mod, _meetings_err = _try_import("app.meetings")  # same §3.4 rule, shipped under this name too
rulesets_mod, _rulesets_err = _try_import("app.rulesets")
render_mod, _render_err = _try_import("render.worksheet")
cases_routes_mod, _cases_routes_err = _try_import("app.routes.cases")  # W3 case-lifecycle endpoints
documents_routes_mod, _documents_routes_err = _try_import("app.routes.documents")  # W3 upload/triage endpoints
extraction_routes_mod, _extraction_routes_err = _try_import("app.routes.extraction")  # W4 operator confirm UI
cases_mod, _cases_mod_err = _try_import("app.cases")  # W3 case business logic (dashboard/detail reads)
extraction_mod, _extraction_mod_err = _try_import("app.extraction")  # W4 field-review business logic
deadlines_mod, _deadlines_err = _try_import("app.deadlines")  # W3 statutory clocks (re-exports engine.deadlines)
blobs_mod, _blobs_err = _try_import("app.blobs")  # F10 -- MAX_UPLOAD_BYTES for the body-size guard below

MODULE_STATUS: dict[str, dict[str, Any]] = {
    "app.config": {"available": config_mod is not None, "error": _config_err},
    "app.security": {"available": security_mod is not None, "error": _security_err},
    "app.db": {"available": db_mod is not None, "error": _db_err},
    "app.audit": {"available": audit_mod is not None, "error": _audit_err},
    "app.dates": {"available": dates_mod is not None, "error": _dates_err},
    "app.meetings": {"available": meetings_mod is not None, "error": _meetings_err},
    "app.rulesets": {"available": rulesets_mod is not None, "error": _rulesets_err},
    "render.worksheet": {"available": render_mod is not None, "error": _render_err},
    "app.routes.cases": {"available": cases_routes_mod is not None, "error": _cases_routes_err},
    "app.routes.documents": {"available": documents_routes_mod is not None, "error": _documents_routes_err},
    "app.routes.extraction": {"available": extraction_routes_mod is not None, "error": _extraction_routes_err},
    "app.cases": {"available": cases_mod is not None, "error": _cases_mod_err},
    "app.extraction": {"available": extraction_mod is not None, "error": _extraction_mod_err},
    "app.deadlines": {"available": deadlines_mod is not None, "error": _deadlines_err},
    "app.blobs": {"available": blobs_mod is not None, "error": _blobs_err},
}


# --------------------------------------------------------------------------- #
# Paths + constants  (CONTRACT.md §2, §1 S3, §1 S5)
#
# app.config, when available, is the canonical source for all of these (it
# also honors a PERMIT_REVIEW_DATA_DIR override, useful for tests) -- prefer
# it and fall back to computing the same values locally so this module still
# works standalone.
# --------------------------------------------------------------------------- #

if config_mod is not None:
    APP_ROOT = config_mod.APP_ROOT
    APP_DIR = APP_ROOT / "app"
    MIGRATIONS_DIR = config_mod.MIGRATIONS_DIR
    RULESETS_DIR = config_mod.RULESETS_DIR
    OVERRIDES_PATH = config_mod.OVERRIDES_DIR / "dimension-qualifiers.json"
    DATA_DIR = config_mod.DATA_DIR
    DB_PATH = config_mod.DB_PATH
    EXPORTS_DIR = config_mod.EXPORTS_DIR
    TMP_DIR = config_mod.TMP_DIR
    HOST = config_mod.HOST
    DEFAULT_PORT = config_mod.DEFAULT_PORT
else:
    APP_ROOT = Path(__file__).resolve().parent.parent  # .../build/permit-review
    APP_DIR = APP_ROOT / "app"
    MIGRATIONS_DIR = APP_DIR / "migrations"
    RULESETS_DIR = APP_ROOT / "rulesets"
    OVERRIDES_PATH = APP_ROOT / "overrides" / "dimension-qualifiers.json"
    DATA_DIR = APP_ROOT / "data"
    DB_PATH = DATA_DIR / "permit-review.db"
    EXPORTS_DIR = DATA_DIR / "exports"
    TMP_DIR = DATA_DIR / "tmp"
    HOST = "127.0.0.1"  # CONTRACT.md §1 S3 -- a module constant, never a flag, never an env var.
    DEFAULT_PORT = 8781

APP_VERSION = "0.1.0-w1"
CONTRACT_VERSION = "contract/1.0.0"

# The bind HOST above is fixed and never configurable (§1 S3). The PORT is
# overridable, but ONLY via `run.py --port N` -- never an env var, never a
# config key (app/config.py's own rule, matching §1 S3). create_app() takes
# an optional `port` kwarg for exactly this; PORT below is only the default
# used when nothing overrides it.
PORT = DEFAULT_PORT


# --------------------------------------------------------------------------- #
# Deterministic dates (CONTRACT.md §3.4).  Prefers app.dates; falls back to an
# identical local implementation of the same rule so the worksheet still
# works, clearly, before app/dates.py exists.
# --------------------------------------------------------------------------- #


def _third_thursday(year: int, month: int) -> date:
    d = date(year, month, 1)
    days_to_first_thu = (3 - d.weekday()) % 7  # Mon=0 ... Thu=3
    first_thu = d + timedelta(days=days_to_first_thu)
    return first_thu + timedelta(days=14)


def _dates_source():
    """CONTRACT.md §2 names `app/dates.py`; a sibling task shipped the same
    §3.4 rule under `app/meetings.py` instead (see that module's own docstring
    note). Prefer the contract name, then the sibling, then a local copy of
    the same arithmetic -- three implementations of a legal-deadline rule are
    worse than one, so this is the single seam that picks among them."""
    return dates_mod or meetings_mod


def get_meeting_date(year: int, month: int) -> date:
    src = _dates_source()
    if src is not None:
        try:
            return src.meeting_date(year, month)
        except Exception:  # noqa: BLE001
            pass
    return _third_thursday(year, month)


def get_draft_due(meeting: date) -> date:
    src = _dates_source()
    if src is not None:
        try:
            return src.draft_due(meeting)
        except Exception:  # noqa: BLE001
            pass
    return meeting - timedelta(days=7)


def get_next_meeting(on: date) -> date:
    src = _dates_source()
    if src is not None:
        try:
            return src.next_meeting(on)
        except Exception:  # noqa: BLE001
            pass
    m = _third_thursday(on.year, on.month)
    if m >= on:
        return m
    year, month = (on.year + 1, 1) if on.month == 12 else (on.year, on.month + 1)
    return _third_thursday(year, month)


# --------------------------------------------------------------------------- #
# Ruleset loading (CONTRACT.md §4).  Prefers app.rulesets.load_ruleset() (which
# owns caching + the binding gate, §1 S8); falls back to reading the committed,
# fully-specified rulesets/<key>/*.json files directly -- those are the stable
# on-disk contract, so this remains correct even before app/rulesets.py exists.
# Runtime never re-parses repo *source* either way (§4 preamble).
# --------------------------------------------------------------------------- #


class RulesetNotFound(Exception):
    pass


class DistrictsBlocked(RulesetNotFound):
    """rulesets/<key>/districts.json is intentionally absent -- see
    DECISIONS-NEEDED.md D-0001/D-0002 (CONTRACT.md §7). This is a subclass of
    RulesetNotFound (not a sibling) so any existing `except RulesetNotFound`
    still catches it; callers that want the more specific message can catch
    this type first."""

    def __init__(self, ruleset_key: str):
        super().__init__(
            f"{ruleset_key}/districts.json is absent -- blocked by "
            f"DECISIONS-NEEDED.md D-0001/D-0002 (unqualified '20 ft' Frontage "
            f"Zone Setback in SD-Historic and SD-Marine; CONTRACT.md §7 forbids "
            f"guessing the qualifier)"
        )


def _read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _adapt_ruleset_obj(rs: Any) -> dict[str, Any] | None:
    """Best-effort adapter from whatever shape app.rulesets.load_ruleset()
    returns into {'manifest':…, 'districts':…, 'use_matrix':…}. Returns None
    (triggering the file-based fallback) if the shape isn't recognized."""
    out: dict[str, Any] = {}
    for key in ("manifest", "districts", "use_matrix"):
        val = rs.get(key) if isinstance(rs, dict) else getattr(rs, key, None)
        if val is None:
            return None
        out[key] = val
    return out


_RULESET_CACHE: dict[str, dict[str, Any]] = {}


def load_ruleset_data(ruleset_key: str) -> dict[str, Any]:
    if rulesets_mod is not None:
        try:
            rs = rulesets_mod.load_ruleset(ruleset_key)
            adapted = _adapt_ruleset_obj(rs)
            if adapted is not None:
                return adapted
        except Exception:  # noqa: BLE001
            pass  # fall through to the file-based loader below

    base = RULESETS_DIR / ruleset_key
    if not (base / "manifest.json").exists():
        raise RulesetNotFound(ruleset_key)
    if not (base / "districts.json").exists():
        # Deliberately absent for "adopted" -- see DECISIONS-NEEDED.md D-0001/
        # D-0002 and DistrictsBlocked's docstring above. Distinguished from a
        # plain RulesetNotFound so callers (selftest checks 4/5/8) can report
        # SKIP with the real reason instead of crashing on the districts.json
        # read below or mis-reporting FAIL/"not built yet".
        raise DistrictsBlocked(ruleset_key)
    return {
        "manifest": _read_json(base / "manifest.json"),
        "districts": _read_json(base / "districts.json"),
        "use_matrix": _read_json(base / "use-matrix.json"),
    }


def _index_ruleset(data: dict[str, Any]) -> dict[str, Any]:
    districts = data["districts"]["districts"]
    districts_by_key = {d["district_key"]: d for d in districts}
    um = data["use_matrix"]
    uses_by_key = {u["use_key"]: u for u in um["uses"]}
    cells_by_pair = {(c["district_key"], c["use_key"]): c for c in um["cells"]}
    return {
        "manifest": data["manifest"],
        "districts": districts,
        "districts_by_key": districts_by_key,
        "uses": um["uses"],
        "uses_by_key": uses_by_key,
        "categories": um.get("categories", []),
        "legend": um.get("legend", []),
        "cells_by_pair": cells_by_pair,
    }


def get_index(ruleset_key: str) -> dict[str, Any]:
    if ruleset_key not in _RULESET_CACHE:
        _RULESET_CACHE[ruleset_key] = _index_ruleset(load_ruleset_data(ruleset_key))
    return _RULESET_CACHE[ruleset_key]


def is_ruleset_binding(ruleset_key: str, manifest: dict[str, Any]) -> bool:
    """CONTRACT.md §1 S8 -- the binding gate. Prefers app.rulesets.require_binding()
    (the canonical enforcement point); falls back to reading manifest.json's own
    'binding' field, which mirrors the same fact (§4.5)."""
    if rulesets_mod is not None:
        try:
            rulesets_mod.require_binding(ruleset_key)
            return True
        except Exception:  # noqa: BLE001
            return False
    return bool(manifest.get("binding"))


# --------------------------------------------------------------------------- #
# The one write surface this app has: data/exports/.  Mirrors CONTRACT.md §1 S5.
# --------------------------------------------------------------------------- #


def _rel_export_path(p: Path) -> str:
    resolved = p.resolve()
    exports_resolved = EXPORTS_DIR.resolve()
    if exports_resolved != resolved and exports_resolved not in resolved.parents:
        raise ValueError("CONTRACT.md 1 S5: renderer wrote outside data/exports/")
    return str(resolved.relative_to(APP_ROOT.resolve()))


# --------------------------------------------------------------------------- #
# JSON envelope helpers (CONTRACT.md §6, preamble)
# --------------------------------------------------------------------------- #


def ok(data: Any) -> dict[str, Any]:
    return {"ok": True, "data": data}


def err(code: str, message: str, status: int, details: Any = None) -> JSONResponse:
    body: dict[str, Any] = {"ok": False, "error": code, "message": message}
    if details is not None:
        body["details"] = details
    return JSONResponse(status_code=status, content=body)


# --------------------------------------------------------------------------- #
# A plain-markdown rendition of the worksheet, for the "Copy markdown" button.
# --------------------------------------------------------------------------- #


def _worksheet_markdown(
    district_obj: dict[str, Any],
    review_rows: list[dict[str, Any]],
    dims: list[dict[str, Any]],
    building_matrix: dict[str, Any] | None,
    building_matrix_absent: dict[str, Any] | None,
    panels: list[dict[str, Any]],
    use_standards: dict[str, Any] | None,
) -> str:
    lines: list[str] = []
    lines.append(f"# Dimensional Worksheet — {district_obj.get('display_name', district_obj.get('code'))}")
    lines.append("")
    lines.append("## Required Review(s)")
    if review_rows:
        for row in review_rows:
            permit = row["permit"] or "(none — prohibited)"
            authority = row["authority"] or "—"
            lines.append(f"- **{permit}** | {authority} | {row['sentence']}")
    else:
        lines.append("_No use selected — pick a use to see its Required Review row._")
    lines.append("")
    lines.append("## Dimensional Standards")
    lines.append("| Label | Required (from the Code) | Proposed | Citation |")
    lines.append("|---|---|---|---|")
    for dim in dims:
        if dim.get("applicability") == "not_established":
            required = "Article 2 establishes no standard for this field."
        else:
            required = dim.get("raw", "")
        marker = " " + "".join(f"({r})" for r in dim.get("footnote_refs", [])) if dim.get("footnote_refs") else ""
        lines.append(f"| {dim.get('label')}{marker} | {required} | ______ | {dim.get('citation_rendered', '')} |")
    lines.append("")
    lines.append("## Permitted Buildings")
    if building_matrix:
        cols = building_matrix.get("cols", [])
        lines.append("| " + " | ".join(["Standard", *cols]) + " |")
        lines.append("|" + "---|" * (len(cols) + 1))
        for row in building_matrix.get("rows", []):
            lines.append("| " + " | ".join(str(v) for v in row) + " |")
    elif building_matrix_absent:
        lines.append(f"_{building_matrix_absent.get('finding', '')}_")
        if building_matrix_absent.get("board_question"):
            lines.append("")
            lines.append(f"**Board question:** {building_matrix_absent['board_question']}")
    lines.append("")
    if use_standards and use_standards.get("items"):
        lines.append(f"## {use_standards.get('title', 'Use Standards')}")
        for item in use_standards["items"]:
            text = item.get("text") if isinstance(item, dict) else item
            lines.append(f"- {text}")
        lines.append("")
    for panel in panels:
        lines.append(f"## {panel.get('title')}")
        body = panel.get("body")
        kind = panel.get("kind")
        if kind == "para":
            lines.append(str(body))
        elif kind == "lv":
            for pair in body or []:
                lines.append(f"- **{pair[0]}:** {pair[1]}")
        elif kind == "list":
            for entry in body or []:
                text = entry.get("text") if isinstance(entry, dict) else entry
                lines.append(f"- {text}")
        lines.append("")
    return "\n".join(lines)


# --------------------------------------------------------------------------- #
# W3 case dashboard / case detail -- read-only view helpers.
#
# Reuses, never re-derives: app.cases owns case/date/history reads and the
# lifecycle vocabulary (CONTRACT.md-style "one source of truth" -- see that
# module's own docstring); app.deadlines re-exports engine.deadlines, the
# statutory-clock engine built from rulesets/<key>/clocks.json. This section
# is pure presentation glue -- display labels, and turning a case row + its
# live case_milestones into the CaseFacts shape app.deadlines.compute_deadlines()
# expects (its own case_facts_from_row() already does this from a real SELECT;
# _case_facts_for() below is the same join, done once per case here since the
# dashboard/detail routes read app.cases's case dicts, not raw cursor rows).
# --------------------------------------------------------------------------- #

APPLICATION_TYPE_LABELS: dict[str, str] = {
    "use": "Use Permit",
    "zoning": "Zoning Permit",
    "subdivision": "Subdivision",
    "shoreland": "Shoreland",
    "site_plan": "Site Plan",
    "special_permit": "Special Permit",
    "expanded_use": "Expanded Use Permit",
    "small_project_plan": "Small Project Plan",
    "large_project_plan": "Large Project Plan",
    "variance": "Variance",
    "other": "Other",
}

STATUS_LABELS: dict[str, str] = {
    "intake": "Intake",
    "extracting": "Extracting",
    "review": "Under Review",
    "draft_issued": "Draft Issued",
    "meeting": "At Meeting",
    "decided": "Decided",
    "closed": "Closed",
    "withdrawn": "Withdrawn",
}

DOC_ROLE_LABELS: dict[str, str] = {
    "application_form": "Application Form",
    "plan_sheet": "Plan Sheet",
    "survey": "Survey",
    "deed": "Deed",
    "engineer_letter": "Engineer Letter",
    "applicant_narrative": "Applicant Narrative",
    "staff_review": "Staff Review",
    "abutter_comment": "Abutter Comment",
    "state_permit": "State Permit",
    "other": "Other",
}

CLOCK_STATUS_LABELS: dict[str, str] = {
    "pending_start": "Not yet started",
    "open": "Open",
    "met": "Met",
    "missed": "Missed",
    "waived": "Waived",
    "n/a": "Not applicable",
    # 2026-08 clock-taxonomy statuses (engine.deadlines.ClockStatus) --
    # party_right windows and conditional_duty clocks never report MISSED.
    "not_triggered": "Not triggered yet",
    "elapsed": "Window elapsed",
}

MILESTONE_KIND_LABELS: dict[str, str] = {
    "application_dated": "Application dated",
    "application_received": "Application received",
    "pre_submittal_meeting": "Pre-submittal meeting",
    "circulated": "Circulated to departments",
    "notice_mailed": "Notice mailed",
    "notice_published": "Notice published",
    "completeness_determined": "Completeness determined",
    "hearing_opened": "Hearing opened",
    "hearing_closed": "Hearing closed",
    "meeting": "Board meeting",
    "forwarded_to_planning_board": "Forwarded to Planning Board",
    "decision_issued": "Decision issued",
    "decision_filed": "Decision filed with Town Clerk",
    "findings_issued": "Findings of fact issued",
    "certificate_recorded": "Certificate recorded",
    "plat_recorded": "Plat recorded",
    "appeal_filed": "Appeal filed",
    "reconsideration_requested": "Reconsideration requested",
    # N2 (0006_appeal_recordability.sql): the four §23 appeal-track events
    # administrative_appeal_hearing/_decision/reconsideration_decision
    # (rulesets/adopted/clocks.json) have named since F3 but that no
    # case_milestones.kind -- and so no operator UI option -- could ever
    # record before this fix. Named distinctly from "Hearing opened" /
    # "Hearing closed" / "Decision issued" above (the underlying case's OWN
    # original-review events) so an operator can never confuse the two
    # tracks in the dropdown.
    "appeal_hearing_opened": "Appeal hearing opened (Appellate Authority)",
    "appeal_hearing_closed": "Appeal hearing closed (Appellate Authority)",
    "appeal_decision": "Appeal decision issued (Appellate Authority)",
    "reconsideration_decided": "Reconsideration concluded (Board of Appeals)",
    # HARD-FINAL round, Finding 6: the §23.e.2/.e.3 vote TO reconsider --
    # distinct from "Reconsideration requested" above (the §23.e.1 request,
    # which does not by itself trigger reconsideration_decision) and from
    # "Reconsideration concluded" (the FINAL §23.e.4 outcome this vote, if
    # it passes, sets a 45-day clock toward).
    "reconsideration_voted": "Board voted to reconsider (§23.e.2-.e.3)",
    # Finding 3 (HARD-FINAL round): the two escape hatches
    # engine.deadlines.CaseFacts.waived_clocks/na_clocks and
    # clock_extension_days never had a write path before this fix -- see
    # app.cases.CASE_MILESTONE_KINDS and app/migrations/0010_clock_extensions.sql.
    "extension_agreed": "Deadline extension agreed in writing (§6.e.1-.e.2)",
    "clock_waived": "Clock waived",
    "clock_not_applicable": "Clock marked not applicable",
    "other": "Other",
}


def _case_facts_for(conn: Any, case_row: dict[str, Any]) -> Any:
    """One case's CaseFacts (app.deadlines.case_facts_from_row), built from
    ALL of its case_milestones -- live and superseded (F7: a satisfying-role
    clock like notice_mailed must see a superseded original notice, not just
    the live re-notice) -- and its generated_documents draft dates (F8) --
    the same joins app.deadlines.load_all_case_facts() does for every case at
    once, done here for exactly one so the detail page doesn't pay for every
    case's history on every request."""
    ruleset_row = conn.execute(
        "SELECT ruleset_key FROM rulesets WHERE id = ?;", (case_row["ruleset_id"],)
    ).fetchone()
    milestone_rows = conn.execute(
        "SELECT * FROM case_milestones WHERE case_id = ? ORDER BY occurred_on;",
        (case_row["id"],),
    ).fetchall()
    draft_rows = conn.execute(
        """
        SELECT generated_at FROM generated_documents
        WHERE case_id = ? AND kind IN ('findings_draft', 'findings_final');
        """,
        (case_row["id"],),
    ).fetchall()
    draft_documents = [
        d for d in (deadlines_mod.parse_date_or_none(r["generated_at"]) for r in draft_rows) if d is not None
    ]
    merged = dict(case_row)
    merged["ruleset_key"] = ruleset_row["ruleset_key"] if ruleset_row is not None else "adopted"
    return deadlines_mod.case_facts_from_row(merged, milestone_rows, draft_documents=draft_documents)


def _compute_deadlines_safe(
    conn: Any, case_row: dict[str, Any], *, include_meeting_clocks: bool = True,
) -> tuple[list[Any], str | None]:
    """F5 read-path hardening: `_case_facts_for` -> `case_facts_from_row`
    calls `engine.deadlines._parse_date`, which raises a bare `ValueError`
    on any `case_milestones.occurred_on` value that isn't a real ISO date.
    `app/cases.py:record_dates` now rejects such a value at the boundary
    (CONTRACT.md §1 S1), but a row written before that fix existed -- or any
    other not-yet-anticipated malformed historical value -- must never be
    allowed to 500 the dashboard or a case's own detail page for every case,
    forever, just because it sits in an append-only table (the original F5
    defect). Every caller that used to `try: ... except
    deadlines_mod.ClocksNotFound` now goes through this one function
    instead, so both failure modes degrade the same way: an empty deadlines
    list plus a message for the page to show, never a crash. See
    case_detail.html's per-row "correct this date" action (fed by
    dates_history's own `occurred_on_invalid` flag, set below in
    case_detail()) for the actual repair path -- superseding the bad row
    removes it from the LIVE query this function reads, so re-computing
    deadlines succeeds the moment it's fixed.
    """
    try:
        facts = _case_facts_for(conn, case_row)
        return deadlines_mod.compute_deadlines(facts, include_meeting_clocks=include_meeting_clocks), None
    except deadlines_mod.ClocksNotFound as exc:
        return [], str(exc)
    except ValueError as exc:
        return [], (
            "One or more of this case's recorded dates could not be read as a calendar "
            "date, so deadlines could not be computed. Open the case and use “correct "
            f"this date” on the flagged row in Key Dates to fix it. ({exc})"
        )


def _headline_deadline(rows: list[Any]) -> Any | None:
    """The single deadline a dashboard row should headline: a MISSED clock
    carrying the §8.d.1 auto-approval consequence first, then any other
    MISSED clock, then the soonest-due OPEN clock -- mirrors
    engine.deadlines.open_deadlines()'s own severity order (that function
    aggregates across cases; this picks the one row for ONE case's own
    dashboard cell)."""
    ClockStatus = deadlines_mod.ClockStatus
    candidates = [d for d in rows if d.status in (ClockStatus.OPEN.value, ClockStatus.MISSED.value)]
    if not candidates:
        return None

    def key(d: Any) -> tuple[int, Any]:
        if d.status == ClockStatus.MISSED.value and d.failure_consequence:
            rank = 0
        elif d.status == ClockStatus.MISSED.value:
            rank = 1
        else:
            rank = 2
        return (rank, d.due_date or date.max)

    return min(candidates, key=key)


def _has_auto_approval_alert(rows: list[Any]) -> bool:
    # RECONCILIATION FIX (F1): delegates to engine.deadlines.
    # presents_auto_approval_risk() rather than checking d.auto_approval_alert
    # alone, so a clock stuck at PENDING_START behind a missed predecessor
    # duty (F4's start_not_recorded_alert) -- exactly F1's stalled-subdivision
    # repro -- still trips the dashboard/case-detail auto-approval banner,
    # not only a clock whose OWN due_date has arrived or passed.
    return any(deadlines_mod.presents_auto_approval_risk(d) for d in rows)


def _deadline_view_rows(rows: list[Any]) -> list[dict[str, Any]]:
    """Every computed Deadline, paired with a `days_remaining` int (None if
    the clock has no due date yet, or is already closed out), and sorted so
    the case-detail deadline table reads worst-first: a MISSED clock with the
    §8.d.1 auto-approval consequence leads, then other MISSED, then OPEN by
    soonest due date, then PENDING_START, then the terminal states
    (MET/WAIVED/N-A) trailing at the bottom as settled history."""
    ClockStatus = deadlines_mod.ClockStatus
    today = date.today()
    out = []
    for d in rows:
        days_remaining = (d.due_date - today).days if d.due_date is not None else None
        out.append({"d": d, "days_remaining": days_remaining})

    def key(row: dict[str, Any]) -> tuple[int, Any]:
        d = row["d"]
        if d.status == ClockStatus.MISSED.value and d.failure_consequence:
            rank = 0
        elif d.status == ClockStatus.MISSED.value:
            rank = 1
        elif d.status == ClockStatus.OPEN.value:
            rank = 2
        elif d.status == ClockStatus.PENDING_START.value:
            rank = 3
        else:
            rank = 4
        return (rank, d.due_date or date.max)

    out.sort(key=key)
    return out


# --------------------------------------------------------------------------- #
# App factory  (CONTRACT.md §6)
# --------------------------------------------------------------------------- #


def create_app(*, port: int | None = None) -> FastAPI:
    """CONTRACT.md's signature table lists `create_app() -> FastAPI`; `port`
    here is an additive, optional keyword (default: PORT / app.config.DEFAULT_PORT)
    so a bare `create_app()` call still works exactly as specified. It exists
    because app/config.py is explicit that the bind port may be overridden
    ONLY by `run.py --port N` -- never an env var, never a config key, the
    same rule §1 S3 states for HOST -- so the override has to reach here as a
    plain argument."""
    bound_port = port if port is not None else PORT

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        if db_mod is not None:
            try:
                conn = db_mod.connect(DB_PATH)
                try:
                    db_mod.migrate(conn, MIGRATIONS_DIR)
                    if security_mod is not None:
                        # Seeds the synthetic local-operator user so any
                        # actor_user_id FK this app writes (e.g. audit events)
                        # resolves -- app/security.py's documented seam.
                        security_mod.ensure_synthetic_user(conn)
                finally:
                    conn.close()
            except Exception as exc:  # noqa: BLE001
                print(f"[permit-review] WARNING: startup migration failed: {exc}")
        else:
            print("[permit-review] NOTE: app.db not available yet -- running without a database "
                  "(the worksheet page and PDF export still work; /healthz and audit logging degrade).")
        yield

    app = FastAPI(title="Newcastle Permit Review", version=APP_VERSION, lifespan=lifespan)
    app.state.port = bound_port

    templates = Jinja2Templates(directory=str(APP_DIR / "templates"))
    app.mount("/static", StaticFiles(directory=str(APP_DIR / "static")), name="static")

    # W3 case-lifecycle endpoints (POST/GET /api/cases, GET /api/cases/{id},
    # PATCH .../dates, POST .../status) -- a self-contained APIRouter, see
    # app/routes/cases.py + app/cases.py. Defensive-import degrade, same
    # pattern as every other sibling module this file does not own.
    if cases_routes_mod is not None:
        app.include_router(cases_routes_mod.router)

    # W3 upload/triage endpoints (POST /api/cases/{id}/documents, GET .../documents)
    # -- app/routes/documents.py, built self-contained and deliberately left
    # unmounted for this integration pass (see that module's docstring).
    if documents_routes_mod is not None:
        app.include_router(documents_routes_mod.router)

    # W4 operator confirm UI (GET /cases/{id}/extraction, POST .../fields/
    # confirm|override|not-applicable, GET /api/blobs/{id}) -- a self-
    # contained APIRouter, see app/routes/extraction.py + app/extraction.py.
    # Same defensive-import degrade as every sibling router above.
    if extraction_routes_mod is not None:
        app.include_router(extraction_routes_mod.router)

    # ----------------------------------------------------------------- #
    # CONTRACT.md §1 S4 -- Host / Origin guard.
    # ----------------------------------------------------------------- #
    @app.middleware("http")
    async def host_origin_guard(request: Request, call_next):
        port = request.app.state.port
        host = request.headers.get("host")
        origin = request.headers.get("origin")
        referer = request.headers.get("referer")

        if security_mod is not None:
            host_ok = security_mod.is_host_allowed(host, port)
            origin_ok = security_mod.is_origin_allowed(request.method, origin, referer, port)
        else:
            allowed_hosts = {f"127.0.0.1:{port}", f"localhost:{port}"}
            host_ok = host in allowed_hosts
            origin_ok = True
            if request.method in ("POST", "PUT", "PATCH", "DELETE"):
                src = origin or referer
                if src:
                    allowed = {f"http://127.0.0.1:{port}", f"http://localhost:{port}"}
                    origin_ok = any(src == a or src.startswith(a + "/") for a in allowed)

        if not host_ok:
            return JSONResponse(
                status_code=403,
                content={"ok": False, "error": "forbidden_host",
                         "message": f"Host header {host!r} is not allowed on this loopback-only server."},
            )
        if not origin_ok:
            return JSONResponse(
                status_code=403,
                content={"ok": False, "error": "forbidden_origin",
                         "message": f"Origin/Referer {origin or referer!r} is not allowed."},
            )
        return await call_next(request)

    # ----------------------------------------------------------------- #
    # F10 -- request body size cap, enforced BEFORE anything is spooled.
    #
    # app/blobs.py's MAX_UPLOAD_BYTES used to be checked only inside the
    # upload route's own streaming re-copy (app/blobs.py:_Sink.feed) -- but
    # `file: UploadFile` as a FastAPI route parameter means Starlette has
    # already fully parsed the multipart body (spooling it to a temp file if
    # it's past the small in-memory threshold) BEFORE the route function, or
    # that re-copy check, ever runs. A 20 GB body would already have filled
    # the temp filesystem by the time our own check fired.
    #
    # Starlette 1.6 ships exactly the right fix as a first-class feature:
    # `starlette.middleware.body_limit.RequestBodyLimitMiddleware`. Added
    # HERE, AFTER the Host/Origin guard above -- Starlette's `add_middleware`
    # PREPENDS to its internal list (`user_middleware.insert(0, ...)`), so
    # the LAST middleware registered ends up OUTERMOST (verified against
    # this repo's pinned starlette/fastapi by inspecting the built stack:
    # registering it here, not earlier, is what actually puts it outside
    # host_origin_guard). Outermost is what F10 needs: this must run before
    # ANYTHING else in this app, including routing and FastAPI's dependency
    # resolution, which is what would otherwise start parsing/spooling a
    # multipart body. It enforces the cap in the two layers CONTRACT F10
    # asks for:
    #   1. a Content-Length pre-check -- rejects with 413 having read ZERO
    #      bytes of the body, whenever the client honestly declares an
    #      oversized body (every real browser file upload does);
    #   2. a streaming byte-count guard wrapping `receive()` -- protects
    #      against a chunked-encoding request that omits/understates
    #      Content-Length, aborting as soon as the running total crosses the
    #      cap, before Starlette's own body/multipart buffering can spool
    #      any more of it to disk.
    # It is applied to EVERY route, not just the upload one -- every other
    # endpoint here is small JSON, so the cap is generous enough to never be
    # felt, and one global guard is simpler and safer than trying to scope a
    # size limit to one route path.
    #
    # A small overhead margin above the per-FILE cap accounts for multipart
    # boundaries/headers around the file part -- a legitimate upload sitting
    # right at MAX_UPLOAD_BYTES must not be rejected by the outer guard only
    # to have never reached app/blobs.py's own (exact, no-margin) check.
    if RequestBodyLimitMiddleware is not None:
        _upload_cap = blobs_mod.MAX_UPLOAD_BYTES if blobs_mod is not None else 150 * 1024 * 1024
        app.add_middleware(RequestBodyLimitMiddleware, max_body_size=_upload_cap + (64 * 1024))
    else:
        print("[permit-review] WARNING: starlette.middleware.body_limit is unavailable -- "
              "the F10 pre-spool upload size guard is NOT active; app/blobs.py's own "
              "in-route check still applies, later than intended.")

    # ----------------------------------------------------------------- #
    # GET /healthz  (CONTRACT.md §6.1)
    # ----------------------------------------------------------------- #
    @app.get("/healthz")
    def healthz():
        pragmas = {"foreign_keys": None, "journal_mode": None, "busy_timeout": None}
        db_status = "module_unavailable"
        migrations: list[str] = []
        if db_mod is not None:
            try:
                conn = db_mod.connect(DB_PATH)
            except Exception as exc:  # noqa: BLE001
                return err("db_unavailable", f"database could not be opened: {exc}", 503)
            try:
                db_status = "ok"
                pragmas["foreign_keys"] = conn.execute("PRAGMA foreign_keys").fetchone()[0]
                pragmas["journal_mode"] = conn.execute("PRAGMA journal_mode").fetchone()[0]
                pragmas["busy_timeout"] = conn.execute("PRAGMA busy_timeout").fetchone()[0]
                try:
                    rows = conn.execute("SELECT name FROM schema_migrations ORDER BY name").fetchall()
                    migrations = [r[0] for r in rows]
                except Exception:  # noqa: BLE001
                    pass
            finally:
                conn.close()

        rulesets_list: list[str] = []
        binding_ruleset = None
        if RULESETS_DIR.exists():
            for child in sorted(RULESETS_DIR.iterdir()):
                manifest_path = child / "manifest.json"
                if manifest_path.exists():
                    rulesets_list.append(child.name)
                    try:
                        m = _read_json(manifest_path)
                        if m.get("binding"):
                            binding_ruleset = child.name
                    except Exception:  # noqa: BLE001
                        pass

        return ok({
            "status": "ok",
            "version": APP_VERSION,
            "contract": CONTRACT_VERSION,
            "db": db_status,
            "migrations": migrations,
            "rulesets": rulesets_list,
            "binding_ruleset": binding_ruleset,
            "pragmas": pragmas,
            "modules": {k: v["available"] for k, v in MODULE_STATUS.items()},
        })

    # ----------------------------------------------------------------- #
    # GET /  --  the dimensional worksheet  (CONTRACT.md §6.2)
    # ----------------------------------------------------------------- #
    @app.get("/", response_class=HTMLResponse)
    def worksheet_page(request: Request, district: str | None = None, use: str | None = None):
        ruleset_key = "adopted"
        try:
            idx = get_index(ruleset_key)
        except RulesetNotFound:
            return templates.TemplateResponse(
                request,
                "worksheet.html",
                {
                    "ruleset_available": False,
                    "modules": MODULE_STATUS,
                },
            )

        if district is not None and district not in idx["districts_by_key"]:
            return err("unknown_district", f"unknown district {district!r}", 404,
                       details=sorted(idx["districts_by_key"]))
        if use is not None and use not in idx["uses_by_key"]:
            return err("unknown_use", f"unknown use {use!r}", 404, details=sorted(idx["uses_by_key"]))

        district_obj = idx["districts_by_key"].get(district) if district else None
        review_rows: list[dict[str, Any]] = []
        dims: list[dict[str, Any]] = []
        building_matrix = None
        building_matrix_absent = None
        use_standards = None
        panels: list[dict[str, Any]] = []
        markdown_text = ""

        if district_obj is not None:
            if use:
                use_obj = idx["uses_by_key"][use]
                cell = idx["cells_by_pair"].get((district, use))
                if cell:
                    review_rows = [citation.required_review_row(district_obj, use_obj, cell)]
            else:
                for u in idx["uses"]:
                    cell = idx["cells_by_pair"].get((district, u["use_key"]))
                    if cell:
                        review_rows.append(citation.required_review_row(district_obj, u, cell))
            for row in review_rows:
                row["citation_text"] = citation.render(row["citation"], style="short")

            for dim in district_obj.get("dimensions", []):
                dims.append({
                    **dim,
                    "citation_rendered": citation.render(citation.from_dimension(ruleset_key, district_obj, dim)),
                })

            building_matrix = district_obj.get("building_matrix")
            building_matrix_absent = district_obj.get("building_matrix_absent")
            use_standards = district_obj.get("use_standards")
            panels = district_obj.get("panels", [])

            markdown_text = _worksheet_markdown(
                district_obj, review_rows, dims, building_matrix, building_matrix_absent, panels, use_standards,
            )

        return templates.TemplateResponse(
            request,
            "worksheet.html",
            {
                "ruleset_available": True,
                "districts": idx["districts"],
                "uses": idx["uses"],
                "categories": idx["categories"],
                "legend": idx["legend"],
                "selected_district": district,
                "selected_use": use,
                "district_obj": district_obj,
                "review_rows": review_rows,
                "dims": dims,
                "building_matrix": building_matrix,
                "building_matrix_absent": building_matrix_absent,
                "use_standards": use_standards,
                "panels": panels,
                "markdown_text": markdown_text,
                "modules": MODULE_STATUS,
                "render_available": render_mod is not None,
            },
        )

    # ----------------------------------------------------------------- #
    # POST /api/worksheet/render  (CONTRACT.md §6.3)
    # ----------------------------------------------------------------- #
    @app.post("/api/worksheet/render")
    async def render_worksheet_endpoint(request: Request):
        try:
            body = await request.json()
        except Exception:  # noqa: BLE001
            return err("validation_failed", "request body is not valid JSON", 400)
        if not isinstance(body, dict):
            return err("validation_failed", "request body must be a JSON object", 400)

        details: list[dict[str, str]] = []

        ruleset_key = body.get("ruleset_key")
        if not isinstance(ruleset_key, str) or not ruleset_key:
            details.append({"field": "ruleset_key", "message": "required string"})

        district_key = body.get("district_key")
        if not isinstance(district_key, str) or not district_key:
            details.append({"field": "district_key", "message": "required string"})

        use_keys = body.get("use_keys", [])
        if not (isinstance(use_keys, list) and all(isinstance(u, str) for u in use_keys)):
            details.append({"field": "use_keys", "message": "must be a list of strings"})

        case_label = body.get("case_label", "")
        if not isinstance(case_label, str):
            details.append({"field": "case_label", "message": "must be a string"})

        meeting_month = body.get("meeting_month")
        if meeting_month is not None and not re.fullmatch(r"\d{4}-\d{2}", meeting_month):
            details.append({"field": "meeting_month", "message": "must be YYYY-MM"})

        lots = body.get("lots", [])
        if not isinstance(lots, list):
            details.append({"field": "lots", "message": "must be a list"})

        notes = body.get("notes", "")
        if not isinstance(notes, str):
            details.append({"field": "notes", "message": "must be a string"})

        scratch = bool(body.get("scratch", False))

        if details:
            return err("validation_failed", "the request body failed validation", 400, details=details)

        try:
            idx = get_index(ruleset_key)
        except RulesetNotFound:
            return err("unknown_ruleset", f"ruleset {ruleset_key!r} not found under rulesets/", 404)

        if not scratch and not is_ruleset_binding(ruleset_key, idx["manifest"]):
            return err(
                "non_binding_ruleset",
                f"ruleset {ruleset_key!r} is not binding; a real case must cite the adopted Code "
                f"(pass \"scratch\": true to dry-run a draft ruleset)",
                403,
            )

        district_obj = idx["districts_by_key"].get(district_key)
        if district_obj is None:
            return err("unknown_district", f"unknown district {district_key!r}", 404,
                       details=sorted(idx["districts_by_key"]))

        unknown_uses = [u for u in use_keys if u not in idx["uses_by_key"]]
        if unknown_uses:
            return err("unknown_use", f"unknown use(s): {unknown_uses}", 404, details=sorted(idx["uses_by_key"]))

        if meeting_month:
            y, m = (int(x) for x in meeting_month.split("-"))
            meeting = get_meeting_date(y, m)
        else:
            meeting = get_next_meeting(date.today())
        due = get_draft_due(meeting)

        if render_mod is None:
            return err(
                "render_unavailable",
                "render/worksheet.py is not available yet in this workflow "
                "(pandoc -> Typst rendering is built by a later/parallel task)",
                500,
            )
        if shutil.which("pandoc") is None or shutil.which("typst") is None:
            missing = "pandoc" if shutil.which("pandoc") is None else "typst"
            return err("render_unavailable", f"required tool not found on PATH: {missing}", 500)

        payload = {
            "ruleset_key": ruleset_key,
            "district_key": district_key,
            "use_keys": use_keys,
            "case_label": case_label,
            "meeting_month": meeting_month,
            "meeting_date": meeting.isoformat(),
            "draft_due": due.isoformat(),
            "lots": lots,
            "notes": notes,
            "scratch": scratch,
        }

        EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
        try:
            out_path = Path(render_mod.render_worksheet(payload, EXPORTS_DIR))
        except Exception as exc:  # noqa: BLE001
            return err("render_failed", f"{type(exc).__name__}: {exc}", 500)

        try:
            rel = _rel_export_path(out_path)
        except ValueError as exc:
            return err("render_failed", str(exc), 500)
        if not out_path.exists():
            return err("render_failed", "renderer reported success but wrote no file", 500)

        data_bytes = out_path.read_bytes()
        if not data_bytes:
            return err("render_failed", "renderer produced a zero-byte file", 500)
        sha = hashlib.sha256(data_bytes).hexdigest()

        unresolved: list[dict[str, Any]] = []
        for dim in district_obj.get("dimensions", []):
            if dim.get("unresolved"):
                unresolved.append({
                    "kind": "dimension", "field_key": dim.get("field_key"),
                    "label": dim.get("label"), "notes": dim.get("notes", []),
                })
        if district_obj.get("building_matrix_absent"):
            unresolved.append({"kind": "building_matrix_absent", **district_obj["building_matrix_absent"]})

        if audit_mod is not None and db_mod is not None:
            actor_user_id = security_mod.current_user().id if security_mod is not None else None
            try:
                conn = db_mod.connect(DB_PATH)
                try:
                    audit_mod.append_event(
                        conn, actor_user_id=actor_user_id, kind="worksheet.rendered",
                        payload={
                            "ruleset_key": ruleset_key, "district_key": district_key,
                            "use_keys": use_keys, "rel_path": rel, "sha256": sha,
                            "byte_size": len(data_bytes),
                        },
                    )
                finally:
                    conn.close()
            except Exception as exc:  # noqa: BLE001
                # A mutation happened on disk (the PDF); the audit row is best-effort
                # here because app.audit/app.db are not yet built in this workflow.
                # We do not fail the request over it, but we do not stay silent either.
                print(f"[permit-review] WARNING: could not append audit event: {exc}")

        return ok({
            "path": rel,
            "bytes": len(data_bytes),
            "sha256": sha,
            "meeting_date": meeting.isoformat(),
            "draft_due": due.isoformat(),
            "unresolved": unresolved,
        })

    # ----------------------------------------------------------------- #
    # GET /cases -- the case dashboard (W3)
    #
    # Every case, its lifecycle status, review track, and the single
    # deadline that should headline its row -- an auto-approval risk first,
    # then any other missed clock, then the soonest-due open one (mirrors
    # engine.deadlines.open_deadlines()'s own severity order, per-case).
    # Cases in a terminal status (closed/withdrawn) show no deadlines --
    # nothing is still running against them.
    # ----------------------------------------------------------------- #
    @app.get("/cases", response_class=HTMLResponse)
    def cases_dashboard(request: Request):
        if db_mod is None or cases_mod is None or deadlines_mod is None:
            return templates.TemplateResponse(
                request, "cases_dashboard.html",
                {"cases_available": False, "modules": MODULE_STATUS},
            )

        conn = db_mod.connect(DB_PATH)
        try:
            case_rows = cases_mod.list_cases(conn)
            rows: list[dict[str, Any]] = []
            urgent_count = 0
            for c in case_rows:
                case_deadlines: list[Any] = []
                headline = None
                auto_risk = False
                deadlines_error = None
                # F11 FIX: a CLOSED case's post-decision statutory duties (plat
                # recording, the appeal window) are still live obligations --
                # closure must not silently drop them from the dashboard, only
                # from cases_mod.TERMINAL_STATUSES = {closed, withdrawn} did
                # before this fix, for EITHER status. A withdrawn application
                # never reached a decision (ALLOWED_TRANSITIONS has no path
                # from 'decided'/'closed' to 'withdrawn'), so it genuinely has
                # no post-decision clocks to lose; only 'closed' is exempted
                # below, and only from the forward-looking meeting/draft_due
                # pair, which a finished case no longer needs.
                if c["status"] != "withdrawn":
                    case_deadlines, deadlines_error = _compute_deadlines_safe(
                        conn, c, include_meeting_clocks=c["status"] not in cases_mod.TERMINAL_STATUSES,
                    )
                    if deadlines_error is None:
                        headline = _headline_deadline(case_deadlines)
                        auto_risk = _has_auto_approval_alert(case_deadlines)
                if auto_risk:
                    urgent_count += 1
                days_remaining = None
                if headline is not None and headline.due_date is not None:
                    days_remaining = (headline.due_date - date.today()).days
                rows.append({
                    "case": c,
                    "application_type_label": APPLICATION_TYPE_LABELS.get(
                        c["application_type"], c["application_type"]),
                    "status_label": STATUS_LABELS.get(c["status"], c["status"]),
                    "headline": headline,
                    "days_remaining": days_remaining,
                    "auto_approval_risk": auto_risk,
                    "deadlines_error": deadlines_error,
                })

            def sort_key(r: dict[str, Any]) -> tuple[int, Any, str]:
                h = r["headline"]
                return (
                    0 if r["auto_approval_risk"] else 1,
                    h.due_date if (h is not None and h.due_date is not None) else date.max,
                    r["case"]["label"],
                )

            rows.sort(key=sort_key)

            return templates.TemplateResponse(
                request, "cases_dashboard.html",
                {
                    "cases_available": True,
                    "rows": rows,
                    "urgent_count": urgent_count,
                    "today": date.today().isoformat(),
                    "modules": MODULE_STATUS,
                },
            )
        finally:
            conn.close()

    # ----------------------------------------------------------------- #
    # GET /cases/{case_id} -- case detail (W3)
    # ----------------------------------------------------------------- #
    @app.get("/cases/{case_id}", response_class=HTMLResponse)
    def case_detail(request: Request, case_id: str):
        if db_mod is None or cases_mod is None:
            return templates.TemplateResponse(
                request, "case_detail.html",
                {"case_available": False, "modules": MODULE_STATUS},
            )

        conn = db_mod.connect(DB_PATH)
        try:
            case = cases_mod.get_case(conn, case_id)
            if case is None:
                return err("case_not_found", f"no case with id {case_id!r}", 404)

            ruleset_row = conn.execute(
                "SELECT ruleset_key, label, binding FROM rulesets WHERE id = ?;", (case["ruleset_id"],)
            ).fetchone()
            ruleset_info = dict(ruleset_row) if ruleset_row is not None else None
            if ruleset_info is not None:
                ruleset_info["binding"] = bool(ruleset_info["binding"])

            # CONTRACT.md-style graceful degradation: a case's district_key is
            # always shown as plain text; a live link to the dimensional
            # worksheet is offered only if that district's data actually
            # loads (rulesets/adopted/districts.json is blocked -- D-0001/
            # D-0002 -- so this never errors, it just falls back to text).
            district_display = case.get("district_key")
            district_worksheet_available = False
            district_note = None
            if case.get("district_key") and ruleset_info is not None:
                try:
                    idx = get_index(ruleset_info["ruleset_key"])
                    d_obj = idx["districts_by_key"].get(case["district_key"])
                    if d_obj is not None:
                        district_display = d_obj.get("display_name", case["district_key"])
                        district_worksheet_available = True
                except DistrictsBlocked:
                    district_note = ("District dimensional standards are unavailable for the adopted "
                                      "ruleset -- see DECISIONS-NEEDED.md D-0001/D-0002.")
                except RulesetNotFound:
                    district_note = "This case's ruleset has not been built yet."

            dates_history_raw = cases_mod.case_dates_for(conn, case_id)
            _by_id = {m["id"]: m for m in dates_history_raw}
            dates_history = []
            for m in dates_history_raw:
                view = dict(m)
                view["kind_label"] = MILESTONE_KIND_LABELS.get(m["kind"], m["kind"])
                superseding = _by_id.get(m["superseded_by"]) if m["superseded_by"] else None
                view["superseded_by_occurred_on"] = superseding["occurred_on"] if superseding else None
                # F5 repair-path support: this row predates app/cases.py's
                # boundary validation (or slipped in some other way) if its
                # occurred_on can't be read as a real date -- flag it so the
                # template can offer a "correct this date" action (a new,
                # valid entry with supersedes_id=this row's id) rather than
                # just silently excluding it from every deadline computation.
                view["occurred_on_invalid"] = deadlines_mod is not None and (
                    deadlines_mod.parse_date_or_none(m["occurred_on"]) is None
                )
                dates_history.append(view)
            audit_trail = cases_mod.case_history_for(conn, case_id)

            case_deadlines: list[Any] = []
            deadlines_error = None
            if deadlines_mod is not None:
                case_deadlines, deadlines_error = _compute_deadlines_safe(conn, case)
            else:
                deadlines_error = "app.deadlines is not available."

            documents: list[dict[str, Any]] = []
            doc_rows = conn.execute(
                "SELECT * FROM documents WHERE case_id = ? ORDER BY created_at;", (case_id,)
            ).fetchall()
            for d in doc_rows:
                page_rows = conn.execute(
                    "SELECT * FROM pages WHERE document_id = ? ORDER BY page_number;", (d["id"],)
                ).fetchall()
                tier_counts = {"A": 0, "B": 0, "C": 0, "D": 0}
                for p in page_rows:
                    if p["tier"] in tier_counts:
                        tier_counts[p["tier"]] += 1
                documents.append({
                    "document": dict(d),
                    "doc_role_label": DOC_ROLE_LABELS.get(d["doc_role"], d["doc_role"] or "—"),
                    "tier_census": tier_counts,
                    "page_count": len(page_rows),
                })

            doc_role_choices = (
                sorted(documents_routes_mod.DOC_ROLE_TO_KIND.keys())
                if documents_routes_mod is not None else sorted(DOC_ROLE_LABELS.keys())
            )

            deadline_rows = _deadline_view_rows(case_deadlines)

            # Finding 3 -- the two clock-override dropdowns' option lists,
            # derived straight from THIS case's own applicable clocks
            # (case_deadlines), so they can never drift from what actually
            # applies to this case's review track. "extendable" is the
            # narrower §6.e.1 subset (engine.deadlines.deadline_is_extendable
            # -- DECISIONS-NEEDED D-0024); "overridable" is every non-
            # informational clock (the synthetic meeting/draft_due rows are
            # never a statutory duty to waive or mark n/a).
            extendable_clock_choices: list[dict[str, str]] = []
            overridable_clock_choices: list[dict[str, str]] = []
            if deadlines_mod is not None:
                seen_extendable: set[str] = set()
                seen_overridable: set[str] = set()
                for d in case_deadlines:
                    if d.duty_kind == deadlines_mod.DutyKind.INFORMATIONAL.value:
                        continue
                    if d.clock_key not in seen_overridable:
                        seen_overridable.add(d.clock_key)
                        overridable_clock_choices.append(
                            {"clock_key": d.clock_key, "label": d.label, "citation": d.citation_short}
                        )
                    if d.clock_key not in seen_extendable and deadlines_mod.deadline_is_extendable(d):
                        seen_extendable.add(d.clock_key)
                        extendable_clock_choices.append(
                            {"clock_key": d.clock_key, "label": d.label, "citation": d.citation_short}
                        )
                extendable_clock_choices.sort(key=lambda c: c["label"])
                overridable_clock_choices.sort(key=lambda c: c["label"])

            # W4 -- a headline summary linking through to the extraction
            # review screen (app/routes/extraction.py). Computed defensively:
            # a case with no field_candidates/field_values rows yet (every
            # case today, until a Tier A/B extraction pass exists) simply
            # shows zero, never an error.
            extraction_summary = None
            if extraction_mod is not None:
                try:
                    ext_fields = extraction_mod.list_case_fields(conn, case_id)
                    extraction_summary = {
                        "field_count": len(ext_fields),
                        "contested_count": sum(1 for f in ext_fields if f["contested"]),
                        "worklist_count": extraction_mod.list_absence_worklist(
                            conn, case_id, actor_user_id=security_mod.current_user().id
                            if security_mod is not None else None,
                        )["count"],
                        "generation": extraction_mod.case_form_generation(conn, case_id),
                    }
                except extraction_mod.ExtractionError:
                    extraction_summary = None

            return templates.TemplateResponse(
                request, "case_detail.html",
                {
                    "case_available": True,
                    "case": case,
                    "application_type_label": APPLICATION_TYPE_LABELS.get(
                        case["application_type"], case["application_type"]),
                    "status_label": STATUS_LABELS.get(case["status"], case["status"]),
                    "allowed_transitions": sorted(cases_mod.ALLOWED_TRANSITIONS.get(case["status"], frozenset())),
                    "ruleset_info": ruleset_info,
                    "district_display": district_display,
                    "district_worksheet_available": district_worksheet_available,
                    "district_note": district_note,
                    "dates_history": dates_history,
                    "milestone_kind_labels": MILESTONE_KIND_LABELS,
                    "milestone_kinds": sorted(cases_mod.CASE_MILESTONE_KINDS),
                    "audit_trail": audit_trail,
                    "deadlines": deadline_rows,
                    "deadlines_error": deadlines_error,
                    "clock_status_labels": CLOCK_STATUS_LABELS,
                    "auto_approval_risk": _has_auto_approval_alert(case_deadlines),
                    "extendable_clock_choices": extendable_clock_choices,
                    "overridable_clock_choices": overridable_clock_choices,
                    "documents": documents,
                    "doc_role_choices": doc_role_choices,
                    "doc_role_labels": DOC_ROLE_LABELS,
                    "upload_available": documents_routes_mod is not None,
                    "extraction_summary": extraction_summary,
                    "extraction_review_available": extraction_routes_mod is not None,
                    "today": date.today().isoformat(),
                    "modules": MODULE_STATUS,
                },
            )
        finally:
            conn.close()

    return app


# --------------------------------------------------------------------------- #
# CONTRACT.md §1 S6 -- offline --selftest.  No network, no LLM, no uploads,
# no PII. Every check prints one PASS/FAIL/SKIP line; SKIP marks a check whose
# dependency (a sibling module, or pandoc/typst) is not available yet -- never
# a silent pass.
# --------------------------------------------------------------------------- #


def selftest() -> int:
    print(f"newcastle-permit-review selftest ({CONTRACT_VERSION})")
    all_ok = True

    def report(n: str, status: str, detail: str = "") -> None:
        nonlocal all_ok
        line = f"{status:<4}  {n}"
        if detail:
            line += f" -- {detail}"
        print(line)
        if status == "FAIL":
            all_ok = False

    # 1 + 2: migrations + pragmas
    if db_mod is None:
        report("1. migrations apply to a temp DB and are idempotent", "SKIP", "app.db not available")
        report("2. connection pragmas match §3.1", "SKIP", "app.db not available")
    else:
        try:
            with tempfile.TemporaryDirectory() as td:
                tmp_db = Path(td) / "selftest.db"
                conn = db_mod.connect(tmp_db)
                applied1 = db_mod.migrate(conn, MIGRATIONS_DIR)
                applied2 = db_mod.migrate(conn, MIGRATIONS_DIR)
                fk = conn.execute("PRAGMA foreign_keys").fetchone()[0]
                jm = conn.execute("PRAGMA journal_mode").fetchone()[0]
                bt = conn.execute("PRAGMA busy_timeout").fetchone()[0]
                conn.close()
            ok1 = isinstance(applied1, list) and len(applied1) >= 1 and applied2 == []
            report("1. migrations apply to a temp DB and are idempotent", "PASS" if ok1 else "FAIL")
            ok2 = fk == 1 and jm == "wal" and bt == 5000
            report("2. connection pragmas match §3.1", "PASS" if ok2 else "FAIL",
                   f"foreign_keys={fk} journal_mode={jm} busy_timeout={bt}")
        except Exception as exc:  # noqa: BLE001
            report("1. migrations apply to a temp DB and are idempotent", "FAIL", str(exc))
            report("2. connection pragmas match §3.1", "FAIL", str(exc))

    # 3: audit chain + append-only triggers
    if db_mod is None or audit_mod is None:
        report("3. audit chain verifies + UPDATE/DELETE triggers raise", "SKIP",
               "app.db and/or app.audit not available")
    else:
        try:
            with tempfile.TemporaryDirectory() as td:
                tmp_db = Path(td) / "selftest.db"
                conn = db_mod.connect(tmp_db)
                db_mod.migrate(conn, MIGRATIONS_DIR)
                for i in range(3):
                    audit_mod.append_event(conn, actor_user_id=None, kind="selftest.probe", payload={"i": i})
                good, _bad_seq = audit_mod.verify_chain(conn)
                update_raised = False
                try:
                    conn.execute("UPDATE events SET kind='x' WHERE seq=1")
                except Exception:  # noqa: BLE001
                    update_raised = True
                delete_raised = False
                try:
                    conn.execute("DELETE FROM events WHERE seq=1")
                except Exception:  # noqa: BLE001
                    delete_raised = True
                conn.close()
            ok3 = bool(good) and update_raised and delete_raised
            report("3. audit chain verifies + UPDATE/DELETE triggers raise", "PASS" if ok3 else "FAIL")
        except Exception as exc:  # noqa: BLE001
            report("3. audit chain verifies + UPDATE/DELETE triggers raise", "FAIL", str(exc))

    # 4: rulesets load + §4 counts
    try:
        idx = get_index("adopted")
        d_count, u_count, c_count = len(idx["districts"]), len(idx["uses"]), len(idx["cells_by_pair"])
        ok4 = d_count == 13 and u_count == 63 and c_count == 819
        report("4. rulesets/adopted loads and matches §4 counts", "PASS" if ok4 else "FAIL",
               f"districts={d_count} uses={u_count} cells={c_count}")
    except DistrictsBlocked:
        report("4. rulesets/adopted loads and matches §4 counts", "SKIP",
               "rulesets/adopted/districts.json blocked -- see DECISIONS-NEEDED.md D-0001/D-0002")
    except RulesetNotFound:
        report("4. rulesets/adopted loads and matches §4 counts", "SKIP", "rulesets/adopted/*.json not built yet")
    except Exception as exc:  # noqa: BLE001
        report("4. rulesets/adopted loads and matches §4 counts", "FAIL", str(exc))

    # 5: every dimensional value qualified or overridden
    try:
        idx = get_index("adopted")
        overrides = _read_json(OVERRIDES_PATH).get("entries", {}) if OVERRIDES_PATH.exists() else {}
        bad: list[str] = []
        for d in idx["districts"]:
            for dim in d.get("dimensions", []):
                if dim.get("applicability") != "established":
                    continue
                for con in dim.get("constraints", []):
                    if con.get("qualifier") in ("min", "max"):
                        continue
                    key = f'{d["district_key"]}:{dim["field_key"]}'
                    entry = overrides.get(key)
                    if not entry or entry.get("qualifier") not in ("min", "max") \
                            or not entry.get("decided_by") or not entry.get("basis"):
                        bad.append(key)
        report("5. every dimensional value is qualified or overridden", "PASS" if not bad else "FAIL",
               f"{len(bad)} unresolved: {bad[:5]}" if bad else "")
    except DistrictsBlocked:
        report("5. every dimensional value is qualified or overridden", "SKIP",
               "rulesets/adopted/districts.json blocked -- see DECISIONS-NEEDED.md D-0001/D-0002")
    except RulesetNotFound:
        report("5. every dimensional value is qualified or overridden", "SKIP",
               "rulesets/adopted/districts.json not built yet")
    except Exception as exc:  # noqa: BLE001
        report("5. every dimensional value is qualified or overridden", "FAIL", str(exc))

    # 6: meeting dates
    try:
        ok6 = True
        for m in range(1, 13):
            md = get_meeting_date(2026, m)
            if md.weekday() != 3:
                ok6 = False
            if get_draft_due(md) != md - timedelta(days=7):
                ok6 = False
        note = "" if _dates_source() is not None else "(fallback math -- app.dates/app.meetings not available)"
        report("6. app.dates reproduces the twelve 2026 meeting + draft-due dates", "PASS" if ok6 else "FAIL", note)
    except Exception as exc:  # noqa: BLE001
        report("6. app.dates reproduces the twelve 2026 meeting + draft-due dates", "FAIL", str(exc))

    # 7: citation golden strings
    try:
        checks = citation._golden_checks()
        ok7 = all(passed for _, passed in checks)
        report("7. citation renders the four §5.5 golden citations byte-for-byte", "PASS" if ok7 else "FAIL")
        for desc, passed in checks:
            if not passed:
                print(f"      FAIL detail: {desc}")
    except Exception as exc:  # noqa: BLE001
        report("7. citation renders the four §5.5 golden citations byte-for-byte", "FAIL", str(exc))

    # 8: worksheet renders a non-zero PDF
    have_tools = shutil.which("pandoc") and shutil.which("typst")
    if render_mod is None:
        report("8. worksheet renders to a non-zero PDF", "SKIP", "render/worksheet.py not available")
    elif not have_tools:
        report("8. worksheet renders to a non-zero PDF", "SKIP", "pandoc and/or typst not on PATH")
    else:
        try:
            idx = get_index("adopted")
            district_key = next(iter(idx["districts_by_key"]))
            # CONTRACT.md §6.3/§8.6: data/exports/ is the ONLY PDF output
            # directory, and render/build-findings.sh enforces that with a hard
            # path guard. The selftest is not exempt -- it renders into a dotted
            # subdirectory of exports/ and removes it again, rather than the
            # guard growing a data/tmp/ carve-out. (A carve-out in a path guard
            # is how the guard stops meaning anything.)
            selftest_dir = EXPORTS_DIR / ".selftest"
            selftest_dir.mkdir(parents=True, exist_ok=True)
            payload = {
                "ruleset_key": "adopted", "district_key": district_key, "use_keys": [],
                "case_label": "SELFTEST", "meeting_month": None, "lots": [], "notes": "", "scratch": True,
            }
            try:
                out = Path(render_mod.render_worksheet(payload, selftest_dir))
                ok8 = out.exists() and out.stat().st_size > 0
                report("8. worksheet renders to a non-zero PDF", "PASS" if ok8 else "FAIL", str(out))
            finally:
                shutil.rmtree(selftest_dir, ignore_errors=True)
        except DistrictsBlocked:
            report("8. worksheet renders to a non-zero PDF", "SKIP",
                   "rulesets/adopted/districts.json blocked -- see DECISIONS-NEEDED.md D-0001/D-0002")
        except RulesetNotFound:
            report("8. worksheet renders to a non-zero PDF", "SKIP", "rulesets/adopted not built yet")
        except Exception as exc:  # noqa: BLE001
            report("8. worksheet renders to a non-zero PDF", "FAIL", str(exc))

    # 9: structural guarantee (ruleset_build/verify_structure.py) -- the W2 gate
    # hardening. Not a CONTRACT.md §1 S6-numbered check (that list predates this
    # module), folded into --selftest anyway per the same "offline, no network,
    # print one line per check, exit non-zero on any failure" discipline, so the
    # structural guarantee over BOTH rulesets' Article/Section/Standard node
    # indexes is part of the standing self-test, not a check a runner can skip.
    try:
        from ruleset_build import verify_structure
        struct_result = verify_structure.run_checks()
        report("9. ruleset_build.verify_structure -- structural gate over both rulesets",
               "PASS" if struct_result.ok else "FAIL")
        if not struct_result.ok:
            for line in struct_result.lines:
                if line.startswith("FAIL"):
                    print(f"      {line}")
    except Exception as exc:  # noqa: BLE001
        report("9. ruleset_build.verify_structure -- structural gate over both rulesets", "FAIL", str(exc))

    # 10: Maine legal holiday calendar (4 M.R.S. §1051) -- DECISIONS-NEEDED
    # D-0006. A pure-computation regression gate: reproduces both real
    # Shattuck business-day clocks (§5.c.3 notice mailed, §8.f.1 decision
    # filed with the Town Clerk) with the holiday-aware calendar wired in,
    # so a future edit to engine.deadlines cannot silently regress back to
    # weekend-only arithmetic without this check failing.
    if deadlines_mod is None:
        report("10. Maine legal holiday calendar (4 M.R.S. §1051) matches the real Shattuck clocks",
               "SKIP", "engine.deadlines not available")
    else:
        try:
            from datetime import date as _date

            bad: list[str] = []
            # §5.c.3: 7 business days from 2025-10-02. Weekend-only arithmetic
            # gives 2025-10-13 -- but that Monday is Indigenous Peoples Day,
            # a §1051 holiday, so the correct due date is 2025-10-14.
            notice_due = deadlines_mod.add_business_days(_date(2025, 10, 2), 7)
            if notice_due != _date(2025, 10, 14):
                bad.append(f"§5.c.3 notice-mailed due date: expected 2025-10-14, got {notice_due}")
            # §8.f.1: 5 business days from 2025-12-18. Weekend-only arithmetic
            # gives 2025-12-25 -- Christmas Day, a §1051 holiday -- so the
            # correct due date is 2025-12-26.
            decision_filed_due = deadlines_mod.add_business_days(_date(2025, 12, 18), 5)
            if decision_filed_due != _date(2025, 12, 26):
                bad.append(f"§8.f.1 decision-filed due date: expected 2025-12-26, got {decision_filed_due}")
            for d, expect_label in (
                (_date(2025, 10, 13), "Indigenous Peoples Day"),
                (_date(2025, 12, 25), "Christmas Day"),
                (_date(2025, 11, 27), "Thanksgiving"),
            ):
                if deadlines_mod.is_business_day(d):
                    bad.append(f"{d} ({expect_label}) is not excluded as a business day")
                label = deadlines_mod.maine_legal_holiday_label(d)
                if label != expect_label:
                    bad.append(f"{d} label: expected {expect_label!r}, got {label!r}")
            report("10. Maine legal holiday calendar (4 M.R.S. §1051) matches the real Shattuck clocks",
                   "PASS" if not bad else "FAIL", "; ".join(bad))
        except Exception as exc:  # noqa: BLE001
            report("10. Maine legal holiday calendar (4 M.R.S. §1051) matches the real Shattuck clocks",
                   "FAIL", str(exc))

    print("selftest:", "ALL OK" if all_ok else "FAILURES ABOVE (see FAIL lines)")
    return 0 if all_ok else 1


if __name__ == "__main__":
    import sys

    if "--selftest" in sys.argv:
        raise SystemExit(selftest())
    print("Use `python3 run.py` to start the server, or `python -m app.main --selftest` to self-test.")
