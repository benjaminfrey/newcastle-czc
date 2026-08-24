#!/usr/bin/env python3
"""
Newcastle Thoroughfare Inventory Editor — local server.

Implements `build/inventory-editor/CONTRACT.md` (contract/1.0.0):
  §3  constants          §4 on-disk formats     §5 HTTP API
  §6  validation         §7 write algorithm     §11 geometry maths

This process is the only thing in the project that writes
`build/street-types/overrides.json` — the version-controlled, permanent record of
human / Planning-Board classification decisions that the GIS pipeline merges on
every re-run and that always wins over auto-classification.  It holds 48
irreplaceable hand-written entries.  Every safety rule in §1 of the contract is
enforced here and nowhere else:

  S1  nothing is written until the whole payload validates
  S2  validate -> re-read -> apply -> serialise -> round-trip verify -> backup ->
      temp file in the same dir -> fsync -> os.replace   (never a truncating write)
  S3  unknown keys, `_README` and note-only entries survive every write untouched
  S4  a note is never replaced by "" and never silently dropped
  S5  an entry is removed only on an explicit {"delete": true}, and the discarded
      content is echoed back in the response
  S6  optimistic concurrency on a sha256 base_token; a mismatch is 409, writes nothing
  S7  binds 127.0.0.1 only; serves its own directory plus an allow-listed font dir

Python standard library only.

Usage:
    python3 build/inventory-editor/serve.py [--port 8765] [--no-browser]
    python3 build/inventory-editor/serve.py --selftest
"""

from __future__ import annotations

import argparse
import errno
import hashlib
import json
import math
import os
import re
import shutil
import socket
import sys
import threading
import webbrowser
from copy import deepcopy
from datetime import datetime, timezone
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlsplit

# --------------------------------------------------------------------------- #
# §2  Repository paths
# --------------------------------------------------------------------------- #

CONTRACT_VERSION = "1.0.0"
DEFAULT_PORT = 8765
HOST = "127.0.0.1"  # not configurable, by contract

REPO = Path(__file__).resolve().parents[2]
SELF_DIR = REPO / "build" / "inventory-editor"
OVERRIDES = REPO / "build" / "street-types" / "overrides.json"
INVENTORY = REPO / "source" / "exhibits" / "street-types" / "inventory.json"
FONT_DIR = REPO / "style" / "fonts"

MAX_BODY = 2 * 1024 * 1024  # 2 MiB
MAX_CHANGES = 1000
BACKUP_KEEP = 10

SAVE_LOCK = threading.Lock()


def rel(p: Path) -> str:
    """Repo-relative posix path, for display and for API responses."""
    try:
        return p.resolve().relative_to(REPO).as_posix()
    except ValueError:
        return p.name


# --------------------------------------------------------------------------- #
# §3  Constants  (shipped to the client in GET /api/data)
# --------------------------------------------------------------------------- #

TYPES = [
    {"code": "S1", "name": "Main Street", "family": "S", "color": "#103E66"},
    {"code": "S2", "name": "Village Street", "family": "S", "color": "#2E6FA0"},
    {"code": "S3", "name": "Neighborhood Street", "family": "S", "color": "#4E97C8"},
    {"code": "S4", "name": "Lane", "family": "S", "color": "#74B2D6"},
    {"code": "S5", "name": "Alley", "family": "S", "color": "#9AC8E4"},
    {"code": "R1", "name": "Connector Road", "family": "R", "color": "#3D4A1F"},
    {"code": "R2", "name": "Rural Road", "family": "R", "color": "#5E6E33"},
    {"code": "R3", "name": "Rural Lane", "family": "R", "color": "#84934A"},
    {"code": "R4", "name": "Highway Commercial", "family": "R", "color": "#A99A4B"},
    {"code": "R5", "name": "Rural Highway", "family": "R", "color": "#C2B777"},
]
TYPE_CODES = [t["code"] for t in TYPES]
TYPE_INDEX = {c: i for i, c in enumerate(TYPE_CODES)}
FAMILIES = [
    {"code": "S", "label": "Street (urban)"},
    {"code": "R", "label": "Road (rural)"},
    {"code": "D", "label": "Driveway (present use)"},
]
OWNERSHIP_CATEGORIES = ["Town Way", "Public Easement", "Private Road", "State Highway"]

# Art 3 §5.C.3.g -- PRESENT USE. Reference-only: it records what a segment is
# TODAY, and never changes `type`, which stays the Type that would apply on
# conversion (Exhibit 3.1 shows that as the "on conversion" column). Recording
# it is not what makes an access way a Driveway -- §7.C.8 does that regardless
# of what is recorded here or whether anything is -- so an unreviewed or even a
# mis-marked segment is still protected. Absent = not yet reviewed.
PRESENT_USE_VALUES = ["Driveway", "Thoroughfare"]
DRIVEWAY_DISPLAY = {"code": "D", "name": "Driveway (present use)", "family": "D",
                    "color": "#A2988C"}

# §4.1 allowed per-entry keys, in serialisation order
KEY_ORDER = ["type", "present_use", "ownership", "row_ft", "traveled_ft",
             "nonconformity", "exclude", "note"]
SETTABLE_FIELDS = set(KEY_ORDER)

ID_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
SEG_ID_RE = re.compile(r"^(?P<road_key>[a-z0-9]+(?:-[a-z0-9]+)*)-(?P<seq>\d+)$")
FONT_NAME_RE = re.compile(r"^[A-Za-z0-9._-]+\.(ttf|otf)$")

# §11 geometry
METRES_TO_FEET = 3.280839895013123
VBW = 1000
PAD = 16


# --------------------------------------------------------------------------- #
# §4.1.1  overrides.json serialisation — normative and byte-exact
# --------------------------------------------------------------------------- #


def natkey(s: str):
    """Natural sort: main-street-2 before main-street-10.

    Every element is a 3-tuple so heterogeneous positions can never raise TypeError.
    """
    return [
        (0, int(t), "") if t.isdigit() else (1, 0, t)
        for t in re.split(r"(\d+)", s)
    ]


def entry_line(sid: str, entry: dict) -> str:
    known = [k for k in KEY_ORDER if k in entry and k != "note"]
    unknown = [k for k in entry if k not in KEY_ORDER]  # preserved verbatim
    order = known + unknown + (["note"] if "note" in entry else [])
    inner = ", ".join(
        f"{json.dumps(k)}: {json.dumps(entry[k], ensure_ascii=True)}" for k in order
    )
    return f"    {json.dumps(sid)}: {{ {inner} }}" if inner else f"    {json.dumps(sid)}: {{}}"


def serialize_overrides(doc: dict) -> str:
    ids = sorted(doc["overrides"], key=natkey)
    lines = [entry_line(i, doc["overrides"][i]) for i in ids]
    body = (",\n".join(lines) + "\n") if lines else ""
    return (
        "{\n"
        f'  "_README": {json.dumps(doc["_README"], ensure_ascii=True)},\n'
        '  "overrides": {\n'
        + body
        + "  }\n"
        "}\n"
    )


def serialize_inventory(doc: dict) -> str:
    """§4.2 — json.dumps(indent=1), no trailing newline."""
    return json.dumps(doc, indent=1)


# --------------------------------------------------------------------------- #
# Errors
# --------------------------------------------------------------------------- #


class ApiError(Exception):
    def __init__(self, status: int, code: str, message: str, details=None):
        super().__init__(message)
        self.status = status
        self.code = code
        self.message = message
        self.details = details if details is not None else []

    def envelope(self) -> dict:
        return {
            "ok": False,
            "error": {"code": self.code, "message": self.message, "details": self.details},
        }


# --------------------------------------------------------------------------- #
# §7.1  File IO helpers
# --------------------------------------------------------------------------- #


def token_of_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()[:16]


def read_overrides() -> tuple[dict, bytes, str]:
    try:
        raw = OVERRIDES.read_bytes()
        doc = json.loads(raw.decode("utf-8"))
    except Exception as exc:  # noqa: BLE001
        raise ApiError(500, "corrupt_overrides",
                       "overrides.json could not be read or parsed; nothing was written.",
                       [{"detail": repr(exc)[:300]}]) from exc
    if not isinstance(doc, dict) or "overrides" not in doc or "_README" not in doc:
        raise ApiError(500, "corrupt_overrides",
                       "overrides.json is missing the _README or overrides key.", [])
    if not isinstance(doc["overrides"], dict):
        raise ApiError(500, "corrupt_overrides", "overrides.overrides is not an object.", [])
    for sid, entry in doc["overrides"].items():
        if not isinstance(entry, dict):
            raise ApiError(500, "corrupt_overrides",
                           f"override entry {sid!r} is not an object.", [])
    return doc, raw, token_of_bytes(raw)


def read_inventory() -> tuple[dict, bytes, str]:
    try:
        raw = INVENTORY.read_bytes()
        doc = json.loads(raw.decode("utf-8"))
    except Exception as exc:  # noqa: BLE001
        raise ApiError(500, "corrupt_inventory",
                       "inventory.json could not be read or parsed; nothing was written.",
                       [{"detail": repr(exc)[:300]}]) from exc
    if not isinstance(doc, dict) or not isinstance(doc.get("segments"), list):
        raise ApiError(500, "corrupt_inventory", "inventory.json has no segments array.", [])
    return doc, raw, token_of_bytes(raw)


def assert_still(path: Path, expected: bytes, what: str) -> None:
    """Re-read `path` and refuse to continue unless it still holds `expected`.

    SAVE_LOCK serialises this tool's own saves, but nothing stops an EXTERNAL
    writer — a GIS pipeline re-run in another terminal, an editor, a git
    checkout — from replacing the file between the read that produced the
    mutation and the os.replace that lands it. The optimistic base_token check
    happens at the top of do_save and is stale by then. The whole new document
    was computed from `expected`, so if the bytes have moved on, writing it
    would silently discard whatever the other writer put there.

    Called immediately before the backup + rename, this shrinks the window from
    "the length of a save" to "one stat + read", and turns the remaining case
    into a clean 409 instead of a clobber.
    """
    try:
        live = path.read_bytes()
    except OSError as exc:
        raise ApiError(500, "io_error",
                       f"{what} could not be re-read immediately before writing; "
                       f"nothing was written: {exc.strerror or exc}",
                       [{"stage": "pre_write_verify"}]) from exc
    if live != expected:
        raise ApiError(409, "stale_base",
                       f"{what} changed on disk while this save was being prepared; "
                       f"nothing was written. Reload to merge.",
                       [{"expected": token_of_bytes(expected),
                         "actual": token_of_bytes(live),
                         "stage": "pre_write_verify"}])


def make_backup(path: Path, stamp: str) -> Path:
    """§7.3 — <filename>.bak-%Y%m%d-%H%M%S beside the original, collision-suffixed."""
    cand = path.with_name(path.name + f".bak-{stamp}")
    n = 2
    while cand.exists():
        cand = path.with_name(path.name + f".bak-{stamp}-{n}")
        n += 1
    shutil.copy2(path, cand)
    return cand


def prune_backups(path: Path) -> list[str]:
    """Keep the BACKUP_KEEP newest .bak-*; return repo-relative paths removed."""
    removed: list[str] = []
    try:
        pattern = path.name + ".bak-"
        baks = sorted(
            (p for p in path.parent.iterdir() if p.name.startswith(pattern)),
            key=lambda p: p.name,
            reverse=True,
        )
        for p in baks[BACKUP_KEEP:]:
            try:
                p.unlink()
                removed.append(rel(p))
            except OSError:
                pass  # pruning failure is a warning, never an error
    except OSError:
        pass
    return removed


def atomic_write_text(path: Path, text: str) -> None:
    """§7 step 8 — temp file in the SAME directory, fsync, os.replace."""
    tmp = path.with_name(f"{path.name}.tmp-{os.getpid()}-{os.urandom(3).hex()}")
    try:
        with open(tmp, "w", encoding="utf-8", newline="") as fh:
            fh.write(text)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, path)
    finally:
        if tmp.exists():
            try:
                tmp.unlink()
            except OSError:
                pass
    # best effort: fsync the containing directory so the rename is durable
    try:
        dfd = os.open(str(path.parent), os.O_RDONLY)
        try:
            os.fsync(dfd)
        finally:
            os.close(dfd)
    except OSError:
        pass


# --------------------------------------------------------------------------- #
# §11  Geometry maths
# --------------------------------------------------------------------------- #


def compute_view(segments: list[dict]) -> dict:
    xs_min = ys_min = math.inf
    xs_max = ys_max = -math.inf
    for seg in segments:
        for pt in seg.get("geometry") or ():
            x, y = pt[0], pt[1]
            if x < xs_min:
                xs_min = x
            if x > xs_max:
                xs_max = x
            if y < ys_min:
                ys_min = y
            if y > ys_max:
                ys_max = y
    if xs_min is math.inf:
        xs_min = ys_min = 0.0
        xs_max = ys_max = 1.0
    spanx = max(xs_max - xs_min, 1e-9)
    spany = max(ys_max - ys_min, 1e-9)
    vbh = round((VBW - 2 * PAD) * spany / spanx + 2 * PAD)
    scale = min((VBW - 2 * PAD) / spanx, (vbh - 2 * PAD) / spany)
    offx = PAD + ((VBW - 2 * PAD) - spanx * scale) / 2
    offy = PAD + ((vbh - 2 * PAD) - spany * scale) / 2
    # Round to the precision that is transported, and project with the *rounded*
    # constants, so a client that recomputes the transform lands on identical
    # coordinates rather than drifting in the last decimal.
    scale = round(scale, 7)
    offx = round(offx, 3)
    offy = round(offy, 3)
    return {
        "vbw": VBW,
        "vbh": vbh,
        "pad": PAD,
        "minx": xs_min,
        "miny": ys_min,
        "maxx": xs_max,
        "maxy": ys_max,
        "scale": scale,
        "offx": offx,
        "offy": offy,
        "units_per_ft": round(scale / METRES_TO_FEET, 8),
    }


def _project(view: dict, x: float, y: float) -> tuple[float, float]:
    return (
        view["offx"] + (x - view["minx"]) * view["scale"],
        view["offy"] + (view["maxy"] - y) * view["scale"],
    )


def _fmt(v: float) -> str:
    s = f"{v:.2f}"
    if "." in s:
        s = s.rstrip("0").rstrip(".")
    return "0" if s in ("", "-0") else s


def geometry_stats(geom, view: dict) -> tuple[float, str, list | None]:
    """Return (length_ft, svg path 'd', projected midpoint-by-length)."""
    pts = [(float(p[0]), float(p[1])) for p in (geom or ()) if p is not None and len(p) >= 2]
    if len(pts) < 2:
        if len(pts) == 1:
            px, py = _project(view, *pts[0])
            return 0.0, "", [round(px, 2), round(py, 2)]
        return 0.0, "", None

    spans = [math.hypot(pts[i + 1][0] - pts[i][0], pts[i + 1][1] - pts[i][1])
             for i in range(len(pts) - 1)]
    length_m = math.fsum(spans)

    # §11.3 midpoint at 50% of cumulative length, interpolated within its span
    target = length_m / 2.0
    acc = 0.0
    mx, my = pts[-1]
    for i, d in enumerate(spans):
        if acc + d >= target or i == len(spans) - 1:
            t = 0.0 if d == 0 else (target - acc) / d
            t = min(max(t, 0.0), 1.0)
            ax, ay = pts[i]
            bx, by = pts[i + 1]
            mx, my = ax + (bx - ax) * t, ay + (by - ay) * t
            break
        acc += d

    px, py = _project(view, *pts[0])
    parts = [f"M{_fmt(px)} {_fmt(py)}"]
    for x, y in pts[1:]:
        px, py = _project(view, x, y)
        parts.append(f"L{_fmt(px)} {_fmt(py)}")

    pmx, pmy = _project(view, mx, my)
    return length_m * METRES_TO_FEET, "".join(parts), [round(pmx, 2), round(pmy, 2)]


# --------------------------------------------------------------------------- #
# Warnings
# --------------------------------------------------------------------------- #

WARNING_TEXT = {
    "override_drift": "The promoted inventory Type differs from the durable override; "
                      "apply to the inventory or re-run the pipeline.",
    "orphan_override": "Override id matches no segment in the inventory.",
    "blank_ownership": "Ownership Category is not recorded for this segment.",
    "unknown_key": "Override entry carries a key outside the documented schema; "
                   "it is preserved verbatim.",
    "note_missing": "The override entry ends up with no note; every existing entry carries one.",
    "note_preserved": "An empty note was supplied, so the note already on disk was kept.",
    "note_replaced": "A hand-written note already on disk is replaced by the new one; "
                     "the old wording survives only in the backup file.",
    "no_op": "The change leaves the entry exactly as it already is on disk.",
    "exclude_destructive": "Excluding a segment while applying to the inventory removes the "
                           "segment object, geometry included; only the backup will retain it.",
    "key_removed_not_restorable": "Removing type/ownership cannot be reflected in the inventory; "
                                  "the auto-classified value needs a pipeline re-run.",
    "exclude_not_restorable": "Removing an exclusion cannot restore the segment to the inventory; "
                              "its geometry needs a pipeline re-run.",
    "empty_entry": "The override entry has no keys left; it is kept as an empty object "
                   "(only an explicit delete removes an entry).",
    "inventory_format": "inventory.json is not in the pipeline's exact json.dump(indent=1) form; "
                        "applying to it would reformat the whole file.",
}


class WarnBag:
    """Aggregates {code, message, ids[]} warnings, first-seen order, unique ids."""

    def __init__(self):
        self._d: dict[str, dict] = {}

    def add(self, code: str, sid: str | None = None, message: str | None = None) -> None:
        w = self._d.setdefault(
            code, {"code": code, "message": message or WARNING_TEXT.get(code, code), "ids": []}
        )
        if sid is not None and sid not in w["ids"]:
            w["ids"].append(sid)

    def ids(self, code: str) -> list[str]:
        return list(self._d.get(code, {}).get("ids", []))

    def has(self, code: str) -> bool:
        return code in self._d

    def list(self) -> list[dict]:
        return list(self._d.values())


# --------------------------------------------------------------------------- #
# §5.3  Data assembly
# --------------------------------------------------------------------------- #


def compute_counts(overrides: dict, segments: list[dict]) -> dict:
    seg_ids = {s.get("id") for s in segments}
    by_type = {c: 0 for c in TYPE_CODES}
    by_type[""] = 0
    by_own = {c: 0 for c in OWNERSHIP_CATEGORIES}
    by_own[""] = 0
    road_keys = set()
    with_override = 0
    for s in segments:
        t = s.get("type") or ""
        by_type[t] = by_type.get(t, 0) + 1
        o = s.get("ownership") or ""
        by_own[o] = by_own.get(o, 0) + 1
        m = SEG_ID_RE.match(s.get("id") or "")
        road_keys.add(m.group("road_key") if m else (s.get("id") or ""))
        if s.get("id") in overrides:
            with_override += 1
    return {
        "segments": len(segments),
        "roads": len(road_keys),
        "overrides": len(overrides),
        "override_typed": sum(1 for e in overrides.values() if "type" in e),
        "override_note_only": sum(1 for e in overrides.values() if set(e) == {"note"}),
        "override_excluded": sum(1 for e in overrides.values() if e.get("exclude") is True),
        "override_orphan": sum(1 for k in overrides if k not in seg_ids),
        "with_override": with_override,
        "without_override": len(segments) - with_override,
        "by_type": by_type,
        "by_ownership": by_own,
    }


def build_data_payload() -> dict:
    ov_doc, _ov_raw, base_token = read_overrides()
    inv_doc, inv_raw, inv_token = read_inventory()
    overrides = ov_doc["overrides"]
    segments = inv_doc["segments"]
    view = compute_view(segments)
    warn = WarnBag()

    for sid, entry in overrides.items():
        for k in entry:
            if k not in SETTABLE_FIELDS:
                warn.add("unknown_key", sid)

    out_segments: list[dict] = []
    districts: set[str] = set()
    maindot: set[str] = set()
    roads: dict[str, dict] = {}
    seg_ids: set[str] = set()

    for seg in segments:
        sid = seg.get("id") or ""
        seg_ids.add(sid)
        m = SEG_ID_RE.match(sid)
        road_key = m.group("road_key") if m else sid
        seq = int(m.group("seq")) if m else 0
        entry = overrides.get(sid)
        has_override = entry is not None
        type_source = "override" if (has_override and "type" in entry) else "auto"
        length_ft, path_d, mid = geometry_stats(seg.get("geometry"), view)
        length_ft = round(length_ft, 1)

        for d in seg.get("districts") or ():
            districts.add(d)
        if seg.get("maindot"):
            maindot.add(seg["maindot"])
        if not seg.get("ownership"):
            warn.add("blank_ownership", sid)
        if has_override and "type" in entry and entry["type"] != seg.get("type"):
            warn.add("override_drift", sid)

        out_segments.append({
            "id": sid,
            "road_key": road_key,
            "seq": seq,
            "name": seg.get("name"),
            "termini": seg.get("termini"),
            "type": seg.get("type"),
            "ownership": seg.get("ownership"),
            "row_ft": seg.get("row_ft"),
            "traveled_ft": seg.get("traveled_ft"),
            "districts": seg.get("districts") or [],
            "maindot": seg.get("maindot"),
            "nonconformity": seg.get("nonconformity"),
            "present_use": seg.get("present_use"),
            # Art 3 §7.C.7 driveway threshold, as decision support only. See
            # 05_export.address_counts(): `unknown_type` matters as much as
            # `residential` -- a 0 beside a nonzero unknown means NOT REVIEWED,
            # not NOT PRESENT, and the UI must not let those read the same.
            "addresses": seg.get("addresses") or {"residential": 0, "unknown_type": 0, "total": 0},
            "length_ft": length_ft,
            "has_override": has_override,
            "override": deepcopy(entry) if has_override else None,
            "type_source": type_source,
            # The classifier's own answer for an overridden segment is not
            # recoverable from these two files (it needs district_fracs from
            # 03_join), so we refuse to guess it rather than fabricate a number
            # in a legal record.
            "auto_type": seg.get("type") if type_source == "auto" else None,
            "excluded": bool(has_override and entry.get("exclude") is True),
            "path": path_d,
            "mid": mid,
            "geometry": seg.get("geometry") or [],
        })

        r = roads.setdefault(road_key, {
            "road_key": road_key, "name": seg.get("name"), "segment_ids": [],
            "n": 0, "length_ft": 0.0, "types": [], "override_count": 0,
        })
        r["segment_ids"].append(sid)
        r["n"] += 1
        r["length_ft"] += length_ft
        t = seg.get("type") or ""
        if t not in r["types"]:
            r["types"].append(t)
        if has_override:
            r["override_count"] += 1

    for r in roads.values():
        r["length_ft"] = round(r["length_ft"], 1)
        r["types"].sort(key=lambda c: TYPE_INDEX.get(c, len(TYPE_CODES)))
    road_list = sorted(roads.values(), key=lambda r: ((r["name"] or "").casefold(), r["road_key"]))

    orphans = []
    for sid, entry in overrides.items():
        if sid in seg_ids:
            continue
        excluded = entry.get("exclude") is True
        orphans.append({"id": sid, "entry": deepcopy(entry),
                        "reason": "excluded" if excluded else "missing"})
        if not excluded:
            warn.add("orphan_override", sid)

    if serialize_inventory(inv_doc).encode("utf-8") != inv_raw:
        warn.add("inventory_format")

    district_list = sorted(districts, key=lambda d: (d.startswith("SD-"), d))
    maindot_order = ["Local", "Minor Collector", "Major Collector", "Other Principal Arterial"]
    maindot_list = ([m for m in maindot_order if m in maindot]
                    + sorted(m for m in maindot if m not in maindot_order))

    return {
        "ok": True,
        "contract": CONTRACT_VERSION,
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "base_token": base_token,
        "inventory_token": inv_token,
        "meta": inv_doc.get("_meta", {}),
        "types": TYPES,
        "families": FAMILIES,
        "ownership_categories": OWNERSHIP_CATEGORIES,
        "present_use_values": PRESENT_USE_VALUES,
        "driveway_display": DRIVEWAY_DISPLAY,
        "districts": district_list,
        "maindot_classes": maindot_list,
        "view": view,
        "roads": road_list,
        "segments": out_segments,
        "orphan_overrides": orphans,
        "counts": compute_counts(overrides, segments),
        "warnings": warn.list(),
    }


# --------------------------------------------------------------------------- #
# §6  Validation  (pure; collects ALL errors before returning)
# --------------------------------------------------------------------------- #


def _norm_text(v: str) -> str:
    return v.replace("\r\n", "\n").replace("\r", "\n").strip()


def _bad_control(s: str) -> bool:
    """C0 controls (except newline/tab) and lone UTF-16 surrogates.

    Surrogates matter because every serialiser here runs with ensure_ascii=True:
    a lone U+D800 would be written as the escape ``\\ud800``, which re-parses but
    is not valid text and cannot survive a UTF-8 round trip through any other
    tool that later reads the durable record (the GIS pipeline, git, an editor).
    Reject it at the door rather than storing an un-encodable note.
    """
    for ch in s:
        o = ord(ch)
        if o < 0x20 and ch not in ("\n", "\t"):
            return True
        if 0xD800 <= o <= 0xDFFF:
            return True
    return False


def _err(index, sid, field, code, message) -> dict:
    return {"index": index, "id": sid, "field": field, "code": code, "message": message}


def _check_number(v):
    """Return (ok, value) — bool is rejected (a Python bool is an int)."""
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        return False, None
    f = float(v)
    if not math.isfinite(f) or f <= 0 or f > 1000:
        return False, None
    return True, round(f, 2)


def validate_payload(payload, ov_doc, inv_doc):
    """§6 — returns (plan, errors, warn).  plan is None when errors is non-empty."""
    errors: list[dict] = []
    warn = WarnBag()

    if not isinstance(payload, dict):
        raise ApiError(400, "bad_payload", "The request body must be a JSON object.")

    allowed_top = {"contract", "base_token", "apply_to_inventory", "changes"}
    extra = [k for k in payload if k not in allowed_top]
    if extra:
        raise ApiError(400, "bad_payload",
                       f"Unexpected top-level key(s): {', '.join(sorted(extra))}.",
                       [{"field": k} for k in sorted(extra)])

    contract = payload.get("contract")
    if contract is not None:
        if not isinstance(contract, str) or contract.split(".")[0] != CONTRACT_VERSION.split(".")[0]:
            raise ApiError(400, "bad_payload",
                           f"Client contract {contract!r} is incompatible with "
                           f"server contract {CONTRACT_VERSION}.")

    base_token = payload.get("base_token")
    if not isinstance(base_token, str) or not base_token:
        raise ApiError(400, "bad_payload", "base_token is required and must be a non-empty string.")

    apply_inv = payload.get("apply_to_inventory")
    if not isinstance(apply_inv, bool):
        raise ApiError(400, "bad_payload", "apply_to_inventory is required and must be a boolean.")

    changes = payload.get("changes")
    if not isinstance(changes, list):
        raise ApiError(400, "bad_payload", "changes is required and must be an array.")
    if len(changes) > MAX_CHANGES:
        raise ApiError(400, "bad_payload",
                       f"changes has {len(changes)} entries; the maximum is {MAX_CHANGES}.")

    overrides = ov_doc["overrides"]
    seg_ids = {s.get("id") for s in inv_doc["segments"]} if inv_doc else set()
    known_ids = seg_ids | set(overrides)

    plan: list[dict] = []
    seen: set[str] = set()

    for i, ch in enumerate(changes):
        if not isinstance(ch, dict) or "id" not in ch:
            errors.append(_err(i, None, None, "bad_change",
                               "Each change must be an object carrying an \"id\"."))
            continue
        sid = ch.get("id")
        if not isinstance(sid, str) or len(sid) > 120 or not ID_RE.match(sid):
            errors.append(_err(i, sid if isinstance(sid, str) else None, "id", "invalid_id",
                               f"{sid!r} is not a valid segment id."))
            continue
        if sid not in known_ids:
            errors.append(_err(i, sid, "id", "unknown_id",
                               f"\"{sid}\" is not a segment in the inventory nor an existing "
                               f"override entry."))
            continue
        if sid in seen:
            errors.append(_err(i, sid, "id", "duplicate_id",
                               f"\"{sid}\" appears more than once in changes."))
            continue
        seen.add(sid)

        has_set = "set" in ch
        has_del = "delete" in ch
        stray = [k for k in ch if k not in ("id", "set", "delete")]
        if stray:
            errors.append(_err(i, sid, None, "bad_change",
                               f"Unexpected key(s) on the change: {', '.join(sorted(stray))}."))
            continue
        if has_set == has_del:
            errors.append(_err(i, sid, None, "bad_change",
                               "A change must carry exactly one of \"set\" or \"delete\": true."))
            continue

        if has_del:
            if ch["delete"] is not True:
                errors.append(_err(i, sid, "delete", "bad_change",
                                   "\"delete\" must be the boolean true."))
                continue
            if sid not in overrides:
                errors.append(_err(i, sid, "delete", "nothing_to_delete",
                                   f"\"{sid}\" has no override entry to delete."))
                continue
            plan.append({"index": i, "id": sid, "kind": "delete"})
            continue

        st = ch["set"]
        if not isinstance(st, dict) or not st:
            errors.append(_err(i, sid, "set", "bad_change",
                               "\"set\" must be a non-empty object."))
            continue

        ops: list[tuple[str, str, object]] = []
        bad = False
        for k, v in st.items():  # insertion order is the application order (§7.4)
            if k not in SETTABLE_FIELDS:
                errors.append(_err(i, sid, k, "unknown_field",
                                   f"\"{k}\" is not a settable field."))
                bad = True
                continue
            if k == "type":
                if v is None:
                    ops.append((k, "remove", None))
                elif isinstance(v, str) and v in TYPE_INDEX:
                    ops.append((k, "set", v))
                else:
                    errors.append(_err(i, sid, k, "invalid_type",
                                       f"{v!r} is not one of S1…S5, R1…R5."))
                    bad = True
            elif k == "present_use":
                if v is None:
                    ops.append((k, "remove", None))
                elif isinstance(v, str) and v in PRESENT_USE_VALUES:
                    ops.append((k, "set", v))
                else:
                    errors.append(_err(i, sid, k, "invalid_present_use",
                                       f"{v!r} is not one of "
                                       f"{', '.join(PRESENT_USE_VALUES)}."))
                    bad = True
            elif k == "ownership":
                if v is None:
                    ops.append((k, "remove", None))
                elif isinstance(v, str) and v in OWNERSHIP_CATEGORIES:
                    ops.append((k, "set", v))
                else:
                    errors.append(_err(i, sid, k, "invalid_ownership",
                                       f"{v!r} is not one of "
                                       f"{', '.join(OWNERSHIP_CATEGORIES)}."))
                    bad = True
            elif k in ("row_ft", "traveled_ft"):
                if v is None:
                    ops.append((k, "remove", None))
                else:
                    ok, num = _check_number(v)
                    if ok:
                        ops.append((k, "set", num))
                    else:
                        errors.append(_err(i, sid, k, "invalid_number",
                                           f"{v!r} must be a number greater than 0 and at "
                                           f"most 1000, or null."))
                        bad = True
            elif k == "nonconformity":
                if v is None:
                    ops.append((k, "remove", None))
                elif isinstance(v, str):
                    t = _norm_text(v)
                    if t == "":
                        ops.append((k, "remove", None))
                    elif _bad_control(t) or len(t) > 2000:
                        errors.append(_err(i, sid, k, "invalid_text",
                                           "nonconformity must be 1–2000 characters and "
                                           "contain no control characters."))
                        bad = True
                    else:
                        ops.append((k, "set", t))
                else:
                    errors.append(_err(i, sid, k, "invalid_text",
                                       f"{v!r} is not a string."))
                    bad = True
            elif k == "note":
                if v is None:
                    ops.append((k, "preserve", None))
                elif isinstance(v, str):
                    t = _norm_text(v)
                    if t == "":
                        ops.append((k, "preserve", None))
                    elif _bad_control(t) or len(t) > 4000:
                        errors.append(_err(i, sid, k, "invalid_text",
                                           "note must be 1–4000 characters and contain no "
                                           "control characters."))
                        bad = True
                    else:
                        ops.append((k, "set", t))
                else:
                    errors.append(_err(i, sid, k, "invalid_text", f"{v!r} is not a string."))
                    bad = True
            elif k == "exclude":
                if v is True:
                    ops.append((k, "set", True))
                elif v is False:
                    ops.append((k, "remove", None))
                else:
                    errors.append(_err(i, sid, k, "invalid_exclude",
                                       f"{v!r} must be the boolean true or false."))
                    bad = True
        if bad:
            continue
        plan.append({"index": i, "id": sid, "kind": "set", "ops": ops})

    if errors:
        return None, errors, warn

    result = apply_plan(ov_doc, plan, warn, apply_inv, seg_ids)
    result["base_token"] = base_token
    result["apply_to_inventory"] = apply_inv
    return result, errors, warn


# --------------------------------------------------------------------------- #
# §7.4  Applying a plan
# --------------------------------------------------------------------------- #


def apply_plan(ov_doc: dict, plan: list[dict], warn: WarnBag,
               apply_inv: bool, seg_ids: set) -> dict:
    new_doc = deepcopy(ov_doc)
    entries = new_doc["overrides"]
    before = {k: deepcopy(v) for k, v in ov_doc["overrides"].items()}

    removed: list[dict] = []
    touched: list[str] = []
    notes_replaced: list[dict] = []

    for item in plan:
        sid = item["id"]
        if item["kind"] == "delete":
            entry = entries.pop(sid)
            removed.append({"id": sid, "entry": entry})
            # Dropping a type/ownership decision leaves the promoted inventory
            # holding the overridden value: the classifier's own answer needs a
            # pipeline re-run, so we say so rather than silently leaving drift.
            if apply_inv and sid in seg_ids and ("type" in entry or "ownership" in entry):
                warn.add("key_removed_not_restorable", sid)
            continue

        entry = entries.get(sid)
        if entry is None:
            entry = {}
        existing_note = entry.get("note")
        for k, action, value in item["ops"]:
            if k == "note":
                if action == "preserve":
                    if existing_note:
                        warn.add("note_preserved", sid)
                    # never write "", never touch what is already there
                else:
                    # A hand-written note being overwritten is the one loss this
                    # tool can inflict that no backup makes obvious, so it is
                    # counted and echoed back for the save report.
                    if existing_note and existing_note != value:
                        notes_replaced.append({"id": sid, "was": existing_note, "now": value})
                        warn.add("note_replaced", sid)
                    entry["note"] = value
            elif k == "exclude":
                if action == "set":
                    entry["exclude"] = True
                    if apply_inv and sid in seg_ids:
                        warn.add("exclude_destructive", sid)
                else:
                    if "exclude" in entry:
                        entry.pop("exclude", None)
                        if apply_inv and sid not in seg_ids:
                            warn.add("exclude_not_restorable", sid)
            elif action == "remove":
                entry.pop(k, None)
                if k in ("type", "ownership") and apply_inv:
                    warn.add("key_removed_not_restorable", sid)
            else:
                entry[k] = value
        entries[sid] = entry
        touched.append(sid)

        if not entry:
            warn.add("empty_entry", sid)
        if not entry.get("note"):
            warn.add("note_missing", sid)
        if sid in before and before[sid] == entry:
            warn.add("no_op", sid)

    created = [s for s in touched if s not in before]
    updated = [s for s in touched if s in before and before[s] != entries.get(s)]
    unchanged = [s for s in touched if s in before and before[s] == entries.get(s)]

    # §7.5 post-mutation invariants — a failure means nothing is written.
    assert set(new_doc) == {"_README", "overrides"}, "overrides doc grew a top-level key"
    assert new_doc["_README"] == ov_doc["_README"], "_README changed"
    for sid, entry in entries.items():
        assert isinstance(entry, dict), f"{sid}: entry is not an object"
        assert entry.get("note", "x") != "", f"{sid}: empty note would be written"
        if "type" in entry:
            assert entry["type"] in TYPE_INDEX, f"{sid}: invalid type"
        if "ownership" in entry:
            assert entry["ownership"] in OWNERSHIP_CATEGORIES, f"{sid}: invalid ownership"
        if "exclude" in entry:
            assert entry["exclude"] is True, f"{sid}: exclude is not exactly True"
    assert len(entries) == len(before) + len(created) - len(removed), "entry-count arithmetic"

    return {
        "doc": new_doc,
        "plan": plan,
        "created": created,
        "updated": updated,
        "unchanged": unchanged,
        "removed": removed,
        "notes_replaced": notes_replaced,
        "entries_before": len(before),
        "entries_after": len(entries),
    }


# --------------------------------------------------------------------------- #
# §7.6  Applying to inventory.json
# --------------------------------------------------------------------------- #

INV_FIELDS = {"type", "present_use", "ownership", "row_ft", "traveled_ft", "nonconformity"}


def apply_to_inventory(inv_doc: dict, plan: list[dict]) -> dict:
    """Returns {doc, fields_updated, segments_removed, skipped}.  Positive values only."""
    new_inv = deepcopy(inv_doc)
    by_id = {s.get("id"): s for s in new_inv["segments"]}
    fields_updated = 0
    to_remove: list[str] = []
    skipped: list[dict] = []

    for item in plan:
        sid = item["id"]
        seg = by_id.get(sid)
        if item["kind"] == "delete":
            skipped.append({"id": sid, "field": None, "reason": "override_deleted"})
            continue
        if seg is None:
            skipped.append({"id": sid, "field": None, "reason": "not_in_inventory"})
            continue
        for k, action, value in item["ops"]:
            if k == "note":
                continue
            if k == "exclude":
                if action == "set":
                    if sid not in to_remove:
                        to_remove.append(sid)
                else:
                    skipped.append({"id": sid, "field": "exclude",
                                    "reason": "exclude_not_restorable"})
                continue
            if k not in INV_FIELDS:
                continue
            if action == "remove":
                if k in ("type", "ownership"):
                    skipped.append({"id": sid, "field": k, "reason": "key_removed"})
                else:
                    if seg.get(k) is not None:
                        seg[k] = None
                        fields_updated += 1
            else:
                if seg.get(k) != value:
                    seg[k] = value
                    fields_updated += 1

    if to_remove:
        rm = set(to_remove)
        new_inv["segments"] = [s for s in new_inv["segments"] if s.get("id") not in rm]

    return {
        "doc": new_inv,
        "fields_updated": fields_updated,
        "segments_removed": to_remove,
        "skipped": skipped,
    }


# --------------------------------------------------------------------------- #
# §5.4 / §5.5  validate + save
# --------------------------------------------------------------------------- #


def do_validate(payload: dict) -> dict:
    if not isinstance(payload, dict):
        raise ApiError(400, "bad_payload", "The request body must be a JSON object.")
    ov_doc, _raw, disk_token = read_overrides()
    apply_inv = payload.get("apply_to_inventory")
    inv_doc, _inv_raw, _inv_token = read_inventory()

    if payload.get("base_token") != disk_token and isinstance(payload.get("base_token"), str):
        raise ApiError(409, "stale_base",
                       "overrides.json changed on disk since this page loaded; "
                       "nothing was written.",
                       [{"expected": payload.get("base_token"), "actual": disk_token}])

    result, errors, warn = validate_payload(payload, ov_doc, inv_doc)
    if errors:
        raise ApiError(400, "validation_failed",
                       f"{len(errors)} problem(s) in the change set; nothing was written.",
                       errors)

    text = serialize_overrides(result["doc"])
    would_overrides = 0 if text == _raw.decode("utf-8") else (
        len(result["created"]) + len(result["updated"]) + len(result["removed"])
    )
    inv_plan = apply_to_inventory(inv_doc, result["plan"]) if apply_inv else None
    would_inventory = 0
    if inv_plan is not None:
        would_inventory = inv_plan["fields_updated"] + len(inv_plan["segments_removed"])

    return {
        "ok": True,
        "contract": CONTRACT_VERSION,
        "valid": True,
        "would_write": {"overrides": would_overrides, "inventory": would_inventory},
        "notes_missing": warn.ids("note_missing"),
        "notes_replaced": result["notes_replaced"] if result else [],
        "removals": [r["id"] for r in result["removed"]],
        "warnings": warn.list(),
    }


def do_save(payload: dict) -> dict:
    if not isinstance(payload, dict):
        raise ApiError(400, "bad_payload", "The request body must be a JSON object.")
    with SAVE_LOCK:
        # 1. read + parse
        ov_doc, ov_raw, disk_token = read_overrides()

        # 2. optimistic concurrency
        if payload.get("base_token") != disk_token and isinstance(payload.get("base_token"), str):
            raise ApiError(409, "stale_base",
                           "overrides.json changed on disk since this page loaded; "
                           "nothing was written. Reload to merge.",
                           [{"expected": payload.get("base_token"), "actual": disk_token}])

        # 3. inventory (always read: /api/data-grade validation needs its ids)
        inv_doc, inv_raw, inv_token = read_inventory()
        apply_inv = payload.get("apply_to_inventory")

        # 4. validate — nothing written on error
        result, errors, warn = validate_payload(payload, ov_doc, inv_doc)
        if errors:
            raise ApiError(400, "validation_failed",
                           f"{len(errors)} problem(s) in the change set; nothing was written.",
                           errors)

        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        saved_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        no_changes = len(result["plan"]) == 0

        ov_report: dict = {"written": False, "path": rel(OVERRIDES)}
        inv_report: dict = {"written": False, "reason": "not_requested"}

        # 5-6. serialise + round-trip verify
        text = serialize_overrides(result["doc"])
        try:
            if json.loads(text) != result["doc"]:
                raise ApiError(500, "internal", "round-trip mismatch; nothing was written.")
            if json.loads(text)["_README"] != ov_doc["_README"]:
                raise ApiError(500, "internal", "_README round-trip mismatch; nothing was written.")
        except ApiError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise ApiError(500, "internal", f"round-trip check failed: {repr(exc)[:300]}") from exc

        identical = text.encode("utf-8") == ov_raw

        if no_changes or identical:
            ov_report.update({
                "written": False,
                "reason": "no_changes",
                "backup": None,
                "entries_before": result["entries_before"],
                "entries_after": result["entries_after"],
                "created": [], "updated": [], "removed": [],
                "unchanged": result["unchanged"],
                "notes_replaced": result["notes_replaced"],
                "backups_pruned": [],
            })
        else:
            # 7-9. re-verify -> backup -> temp -> fsync -> os.replace -> prune
            assert_still(OVERRIDES, ov_raw, "overrides.json")
            try:
                backup = make_backup(OVERRIDES, stamp)
            except OSError as exc:
                raise ApiError(500, "io_error",
                               f"Could not back up overrides.json; nothing was written: "
                               f"{exc.strerror or exc}", [{"stage": "backup"}]) from exc
            try:
                atomic_write_text(OVERRIDES, text)
            except OSError as exc:
                raise ApiError(500, "io_error",
                               f"Could not write overrides.json: {exc.strerror or exc}. "
                               f"The original is intact; a backup is at {rel(backup)}.",
                               [{"stage": "write", "backup": rel(backup)}]) from exc
            ov_report.update({
                "written": True,
                "backup": rel(backup),
                "entries_before": result["entries_before"],
                "entries_after": result["entries_after"],
                "created": result["created"],
                "updated": result["updated"],
                "removed": result["removed"],
                "unchanged": result["unchanged"],
                "notes_replaced": result["notes_replaced"],
                "backups_pruned": prune_backups(OVERRIDES),
            })

        # 10. inventory — a failure here does NOT roll back the overrides write
        if apply_inv:
            if no_changes:
                inv_report = {"written": False, "reason": "no_changes"}
            else:
                inv_report = {"written": False, "path": rel(INVENTORY), "error": None}
                try:
                    ip = apply_to_inventory(inv_doc, result["plan"])
                    inv_text = serialize_inventory(ip["doc"])
                    if json.loads(inv_text) != ip["doc"]:
                        raise RuntimeError("inventory round-trip mismatch")
                    if ip["doc"].get("_meta") != inv_doc.get("_meta"):
                        raise RuntimeError("_meta must be passed through verbatim")
                    if inv_text.encode("utf-8") == inv_raw:
                        inv_report = {"written": False, "reason": "no_changes",
                                      "path": rel(INVENTORY),
                                      "segments_before": len(inv_doc["segments"]),
                                      "segments_after": len(inv_doc["segments"]),
                                      "fields_updated": 0, "segments_removed": [],
                                      "skipped": ip["skipped"], "error": None}
                    else:
                        # Same external-writer guard as the overrides write. A
                        # failure here is reported on its own and never rolls
                        # back overrides.json, which is the durable record.
                        assert_still(INVENTORY, inv_raw, "inventory.json")
                        inv_backup = make_backup(INVENTORY, stamp)
                        atomic_write_text(INVENTORY, inv_text)
                        inv_report = {
                            "written": True,
                            "path": rel(INVENTORY),
                            "backup": rel(inv_backup),
                            "segments_before": len(inv_doc["segments"]),
                            "segments_after": len(ip["doc"]["segments"]),
                            "fields_updated": ip["fields_updated"],
                            "segments_removed": ip["segments_removed"],
                            "skipped": ip["skipped"],
                            "backups_pruned": prune_backups(INVENTORY),
                            "error": None,
                        }
                except ApiError as exc:
                    # e.g. an external writer touched inventory.json mid-save.
                    # overrides.json is already written and stays written.
                    inv_report = {
                        "written": False,
                        "path": rel(INVENTORY),
                        "error": {"code": exc.code, "message": exc.message},
                    }
                except Exception as exc:  # noqa: BLE001
                    inv_report = {
                        "written": False,
                        "path": rel(INVENTORY),
                        "error": {"code": "io_error", "message": repr(exc)[:300]},
                    }

        # 11. recompute counts from what is now on disk
        new_ov_doc, _r, new_token = read_overrides()
        new_inv_doc, _r2, new_inv_token = read_inventory()
        counts = compute_counts(new_ov_doc["overrides"], new_inv_doc["segments"])
        for sid, entry in new_ov_doc["overrides"].items():
            seg = next((s for s in new_inv_doc["segments"] if s.get("id") == sid), None)
            if seg is not None and "type" in entry and entry["type"] != seg.get("type"):
                warn.add("override_drift", sid)

        return {
            "ok": True,
            "contract": CONTRACT_VERSION,
            "base_token": new_token,
            "inventory_token": new_inv_token,
            "saved_at": saved_at,
            "overrides": ov_report,
            "inventory": inv_report,
            "counts": counts,
            "warnings": warn.list(),
        }


# --------------------------------------------------------------------------- #
# §5.6  HTTP
# --------------------------------------------------------------------------- #

STATIC = {
    "/": ("index.html", "text/html; charset=utf-8"),
    "/index.html": ("index.html", "text/html; charset=utf-8"),
    "/app.js": ("app.js", "text/javascript; charset=utf-8"),
    "/styles.css": ("styles.css", "text/css; charset=utf-8"),
}

PLACEHOLDER_HTML = """<!doctype html><meta charset="utf-8">
<title>Thoroughfare Type Editor</title>
<style>body{font:16px/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI",Helvetica,Arial,sans-serif;
color:#231F20;max-width:38rem;margin:12vh auto;padding:0 1.5rem}
h1{color:#367AAC;font-size:1.35rem;margin:0 0 .6rem}code{background:#F6F5F3;padding:.1em .35em}
p{color:#7C766F}</style>
<h1>Thoroughfare Type Editor</h1>
<p>The server is running and the API is live, but <code>index.html</code> has not been
written yet.</p>
<p>Try <code>/api/health</code> or <code>/api/data</code>.</p>
"""


class Handler(BaseHTTPRequestHandler):
    server_version = "NewcastleInventoryEditor/1.0"
    sys_version = ""
    protocol_version = "HTTP/1.1"
    port = DEFAULT_PORT

    # -- plumbing ---------------------------------------------------------- #

    def log_request(self, code="-", size="-"):  # noqa: D102
        code = code.value if hasattr(code, "value") else code
        sys.stderr.write(f"{self.command} {self._safe_path()} -> {code}\n")

    def log_message(self, fmt, *args):  # noqa: A003
        # Never echo the raw request line; keep everything to one safe line.
        try:
            msg = fmt % args
        except Exception:  # noqa: BLE001
            msg = str(fmt)
        sys.stderr.write(f"{self.command or '-'} {self._safe_path()} -- "
                         f"{msg[:200].replace(chr(10), ' ')}\n")

    def _safe_path(self) -> str:
        p = urlsplit(self.path or "").path
        return p[:200].replace("\n", " ").replace("\r", " ")

    def _send(self, status: int, body: bytes, ctype: str, cache: str = "no-store",
              extra: dict | None = None) -> None:
        self.send_response(status)
        if status != HTTPStatus.NO_CONTENT:
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", cache)
        self.send_header("X-Content-Type-Options", "nosniff")
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()
        if self.command != "HEAD" and status != HTTPStatus.NO_CONTENT:
            self.wfile.write(body)

    def _json(self, status: int, obj: dict, extra: dict | None = None) -> None:
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self._send(status, body, "application/json; charset=utf-8", "no-store", extra)

    def _fail(self, exc: ApiError) -> None:
        extra = {"Allow": "GET, HEAD, POST"} if exc.code == "method_not_allowed" else None
        self._json(exc.status, exc.envelope(), extra)

    # -- guards ------------------------------------------------------------ #

    def _check_host(self) -> None:
        host = (self.headers.get("Host") or "").strip()
        allowed = {f"127.0.0.1:{self.port}", f"localhost:{self.port}"}
        if self.port == 80:
            allowed |= {"127.0.0.1", "localhost"}
        if host not in allowed:
            raise ApiError(403, "forbidden_host",
                           "This tool only answers to 127.0.0.1 or localhost.")

    def _check_origin(self) -> None:
        allowed = {f"http://127.0.0.1:{self.port}", f"http://localhost:{self.port}"}
        origin = self.headers.get("Origin")
        if origin is not None and origin not in allowed:
            raise ApiError(403, "forbidden_origin", "Cross-origin requests are refused.")
        ref = self.headers.get("Referer")
        if origin is None and ref is not None:
            if not any(ref.startswith(a + "/") or ref == a for a in allowed):
                raise ApiError(403, "forbidden_origin", "Cross-origin requests are refused.")

    def _decoded_path(self) -> str:
        raw = urlsplit(self.path or "").path
        path = unquote(raw)
        if ".." in path or "\\" in path or "\x00" in path or path.startswith("//"):
            raise ApiError(404, "not_found", "Not found.")
        return path

    # -- verbs ------------------------------------------------------------- #

    def do_GET(self):  # noqa: N802
        try:
            self._check_host()
            path = self._decoded_path()
            if path.startswith("/api/"):
                return self._api_get(path)
            return self._static(path)
        except ApiError as exc:
            self._fail(exc)
        except Exception as exc:  # noqa: BLE001
            self._fail(ApiError(500, "internal", repr(exc)[:300]))

    do_HEAD = do_GET

    def do_POST(self):  # noqa: N802
        try:
            self._check_host()
            self._check_origin()
            path = self._decoded_path()
            if path not in ("/api/save", "/api/validate"):
                if path in STATIC or path.startswith("/api/"):
                    raise ApiError(405, "method_not_allowed", "POST is not allowed on this path.")
                raise ApiError(404, "not_found", "Not found.")
            payload = self._read_json_body()
            result = do_save(payload) if path == "/api/save" else do_validate(payload)
            self._json(200, result)
        except ApiError as exc:
            self._fail(exc)
        except AssertionError as exc:
            self._fail(ApiError(500, "internal",
                                f"post-mutation invariant failed, nothing written: "
                                f"{repr(exc)[:250]}"))
        except Exception as exc:  # noqa: BLE001
            self._fail(ApiError(500, "internal", repr(exc)[:300]))

    def _read_json_body(self) -> dict:
        ctype = (self.headers.get("Content-Type") or "").split(";")[0].strip().lower()
        if ctype != "application/json":
            raise ApiError(400, "bad_content_type",
                           "POST requires Content-Type: application/json.")
        try:
            length = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            raise ApiError(400, "bad_payload", "Content-Length is not a number.") from None
        if length > MAX_BODY:
            self.close_connection = True
            raise ApiError(413, "payload_too_large",
                           f"The request body is {length} bytes; the limit is {MAX_BODY}.")
        raw = self.rfile.read(length) if length > 0 else b""
        try:
            return json.loads(raw.decode("utf-8"))
        except Exception as exc:  # noqa: BLE001
            raise ApiError(400, "bad_json", "The request body is not valid JSON.",
                           [{"detail": repr(exc)[:200]}]) from exc

    # -- routes ------------------------------------------------------------ #

    def _api_get(self, path: str) -> None:
        if path == "/api/health":
            return self._json(200, {
                "ok": True, "contract": CONTRACT_VERSION, "port": self.port,
                "overrides_path": rel(OVERRIDES), "inventory_path": rel(INVENTORY),
            })
        if path == "/api/data":
            return self._json(200, build_data_payload())
        if path in ("/api/save", "/api/validate"):
            raise ApiError(405, "method_not_allowed", "This endpoint requires POST.")
        raise ApiError(404, "not_found", "Not found.")

    def _static(self, path: str) -> None:
        if path in STATIC:
            name, ctype = STATIC[path]
            f = SELF_DIR / name
            if not f.is_file():
                if name == "index.html":
                    return self._send(200, PLACEHOLDER_HTML.encode("utf-8"),
                                      "text/html; charset=utf-8")
                raise ApiError(404, "not_found", "Not found.")
            return self._send(200, f.read_bytes(), ctype)

        if path == "/favicon.ico":
            f = SELF_DIR / "favicon.ico"
            if f.is_file():
                return self._send(200, f.read_bytes(), "image/x-icon", "max-age=86400")
            return self._send(204, b"", "image/x-icon")

        if path.startswith("/fonts/"):
            name = path[len("/fonts/"):]
            if not FONT_NAME_RE.match(name) or ".." in name:
                raise ApiError(404, "not_found", "Not found.")
            if not FONT_DIR.is_dir() or name not in {p.name for p in FONT_DIR.iterdir()}:
                raise ApiError(404, "not_found", "Not found.")
            target = (FONT_DIR / name).resolve()
            if FONT_DIR.resolve() not in target.parents or not target.is_file():
                raise ApiError(404, "not_found", "Not found.")
            ctype = "font/ttf" if name.lower().endswith(".ttf") else "font/otf"
            return self._send(200, target.read_bytes(), ctype, "max-age=86400")

        raise ApiError(404, "not_found", "Not found.")


# --------------------------------------------------------------------------- #
# §4.1.1 / §13  Startup self-test
# --------------------------------------------------------------------------- #


def selftest(verbose: bool = True) -> list[str]:
    """Returns a list of failure strings (empty == pass)."""
    fails: list[str] = []

    def check(label: str, ok: bool, detail: str = "") -> None:
        if verbose:
            print(f"  [{'PASS' if ok else 'FAIL'}] {label}{(' — ' + detail) if detail and not ok else ''}")
        if not ok:
            fails.append(label + ((" — " + detail) if detail else ""))

    ov_raw = OVERRIDES.read_bytes()
    ov_doc = json.loads(ov_raw.decode("utf-8"))
    text = serialize_overrides(ov_doc)
    check("overrides.json round-trips byte-identically (empty-diff invariant)",
          text.encode("utf-8") == ov_raw,
          f"{len(text.encode())} bytes vs {len(ov_raw)} on disk")
    check("natkey reproduces the on-disk entry order",
          sorted(ov_doc["overrides"], key=natkey) == list(ov_doc["overrides"]))
    check("_README survives serialisation",
          json.loads(text)["_README"] == ov_doc["_README"])
    check("re-serialising the parsed document is stable",
          serialize_overrides(json.loads(text)) == text)

    inv_raw = INVENTORY.read_bytes()
    inv_doc = json.loads(inv_raw.decode("utf-8"))
    check("inventory.json round-trips byte-identically (json.dumps indent=1)",
          serialize_inventory(inv_doc).encode("utf-8") == inv_raw)

    # natkey must never raise on heterogeneous ids
    try:
        sorted(["a-1", "1-a", "abc", "9", "a-01-b", ""], key=natkey)
        check("natkey handles heterogeneous ids without TypeError", True)
    except TypeError as exc:
        check("natkey handles heterogeneous ids without TypeError", False, repr(exc))

    # a single type edit touches exactly one line
    ids = [k for k, v in ov_doc["overrides"].items() if v.get("type") == "R2"]
    if ids:
        probe = deepcopy(ov_doc)
        probe["overrides"][ids[0]]["type"] = "R3"
        new_lines = serialize_overrides(probe).splitlines()
        old_lines = text.splitlines()
        diff = sum(1 for a, b in zip(old_lines, new_lines) if a != b)
        check("a single type edit changes exactly one line", diff == 1 and
              len(old_lines) == len(new_lines), f"{diff} lines differ")

    counts = compute_counts(ov_doc["overrides"], inv_doc["segments"])
    check("counts arithmetic: typed + note-only + excluded == overrides",
          counts["override_typed"] + counts["override_note_only"]
          + counts["override_excluded"] == counts["overrides"])
    check("counts arithmetic: with_override + without_override == segments",
          counts["with_override"] + counts["without_override"] == counts["segments"])
    check("counts arithmetic: sum(by_type) == sum(by_ownership) == segments",
          sum(counts["by_type"].values()) == sum(counts["by_ownership"].values())
          == counts["segments"])
    check("by_type carries all ten codes plus the untyped slot",
          all(c in counts["by_type"] for c in TYPE_CODES) and "" in counts["by_type"])

    view = compute_view(inv_doc["segments"])
    px, py = _project(view, 456979.49, 4875907.50)
    check("§11.1 projection check: (456979.49, 4875907.50) -> [787.32, 914.88]",
          (round(px, 2), round(py, 2)) == (787.32, 914.88),
          f"got [{round(px,2)}, {round(py,2)}]")
    check("§11.1 viewBox is 1000 x 1549", view["vbw"] == 1000 and view["vbh"] == 1549,
          f"got {view['vbw']} x {view['vbh']}")

    by_id = {s["id"]: s for s in inv_doc["segments"]}
    for sid, want in (("eden-lane-1", 277.1), ("camp-road-1", 303.1)):
        if sid in by_id:
            got = round(geometry_stats(by_id[sid]["geometry"], view)[0], 1)
            check(f"§11.2 length: {sid} == {want} ft", got == want, f"got {got}")

    return fails


# --------------------------------------------------------------------------- #
# main
# --------------------------------------------------------------------------- #


def preflight() -> tuple[int, int]:
    missing = [p for p in (OVERRIDES, INVENTORY) if not p.is_file()]
    if missing:
        print("Newcastle Thoroughfare Inventory Editor — cannot start.", file=sys.stderr)
        for p in missing:
            print(f"  missing data file: {p}", file=sys.stderr)
        sys.exit(2)
    try:
        ov = json.loads(OVERRIDES.read_text(encoding="utf-8"))
        inv = json.loads(INVENTORY.read_text(encoding="utf-8"))
        return len(ov["overrides"]), len(inv["segments"])
    except Exception as exc:  # noqa: BLE001
        print("Newcastle Thoroughfare Inventory Editor — cannot start.", file=sys.stderr)
        print(f"  a data file could not be parsed: {exc}", file=sys.stderr)
        sys.exit(2)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description="Local editor for the Article 3 §5 Thoroughfare Type inventory.")
    ap.add_argument("--port", type=int, default=DEFAULT_PORT,
                    help=f"TCP port on 127.0.0.1 (default {DEFAULT_PORT})")
    ap.add_argument("--no-browser", action="store_true",
                    help="do not open a browser window on start")
    ap.add_argument("--selftest", action="store_true",
                    help="run the data-format self-test and exit")
    args = ap.parse_args(argv)

    if args.selftest:
        print("Newcastle Thoroughfare Inventory Editor — self-test (contract/"
              f"{CONTRACT_VERSION})")
        fails = selftest()
        print()
        if fails:
            print(f"{len(fails)} check(s) FAILED.")
            return 1
        print("All checks passed.")
        return 0

    n_ov, n_seg = preflight()

    # §4.1.1: the empty-diff invariant is asserted at startup. If the durable
    # record does not round-trip byte-for-byte we must not offer to write it —
    # a save would reformat 48 hand-made entries into one enormous diff.
    fails = selftest(verbose=False)
    fatal = [f for f in fails if f.startswith("overrides.json round-trips")
             or f.startswith("_README")]
    if fatal:
        print("Newcastle Thoroughfare Inventory Editor — refusing to start.", file=sys.stderr)
        print("  The durable record does not round-trip byte-for-byte through the "
              "house serialiser,", file=sys.stderr)
        print("  so saving would rewrite entries this tool did not touch.", file=sys.stderr)
        for f in fatal:
            print(f"    - {f}", file=sys.stderr)
        print("  Run with --selftest for the full report.", file=sys.stderr)
        return 2

    Handler.port = args.port
    try:
        httpd = ThreadingHTTPServer((HOST, args.port), Handler)
    except OSError as exc:
        if exc.errno in (errno.EADDRINUSE, errno.EACCES):
            print(f"Port {args.port} on {HOST} is already in use "
                  f"(is the editor already running?).", file=sys.stderr)
            print(f"  Try:  python3 {rel(Path(__file__))} --port {args.port + 1}",
                  file=sys.stderr)
            return 3
        raise
    httpd.daemon_threads = True

    url = f"http://{HOST}:{args.port}"
    print("Newcastle Thoroughfare Inventory Editor")
    print(f"  overrides : {rel(OVERRIDES):<52} ({n_ov} entries)")
    print(f"  inventory : {rel(INVENTORY):<52} ({n_seg} segments)")
    if fails:
        print(f"  note      : {len(fails)} self-test check(s) reported "
              f"(run --selftest for detail)")
    print(f"  ->  {url}")
    print("  Ctrl-C to stop. Saves are backed up beside each file as .bak-<timestamp>.")
    sys.stdout.flush()

    if not args.no_browser:
        threading.Timer(0.4, lambda: webbrowser.open(url)).start()

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        httpd.server_close()
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except BrokenPipeError:
        sys.exit(0)
    except socket.error:
        sys.exit(0)
