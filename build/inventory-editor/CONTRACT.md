# Thoroughfare Inventory Editor — Integration Contract

**Status:** normative. **Version:** `contract/1.0.0`
**Scope:** `build/inventory-editor/{serve.py,index.html,app.js,styles.css,README.md}`

This document is the single source of truth for the three build surfaces:

| Surface | Owner file | Consumes from this contract |
|---|---|---|
| Server | `serve.py` | §3 Constants · §4 On-disk formats · §5 HTTP API · §6 Validation · §7 Write algorithm · §11 Geometry maths |
| Markup | `index.html` | §3 Constants · §8 DOM contract (shell + `<template>`s) · §10 Keyboard |
| Behaviour | `app.js` | §5 HTTP API · §8 DOM contract · §9 Client state · §10 Keyboard · §11 Geometry maths |
| Styling | `styles.css` | §3 Constants (colours/type) · §8 DOM contract (class names) |

**Rule of ownership:** `index.html` contains **only** the static shell and `<template>` elements.
Every repeating node (segment row, road row, pending item, type chip, legend item, map path) is
**cloned or created by `app.js`**. The HTML author must never hand-author a segment row; the JS
author must never invent an element id that is not listed in §8.

Anything marked **MUST** is required for integration. Anything marked **SHOULD** is a quality bar.
Anything marked *(optional)* may be omitted in v1 without breaking the other two surfaces.

---

## Table of contents

1. [Purpose and safety posture](#1-purpose-and-safety-posture)
2. [Repository paths](#2-repository-paths)
3. [Constants](#3-constants)
4. [On-disk data formats](#4-on-disk-data-formats)
5. [HTTP API](#5-http-api)
6. [Server-side validation rules](#6-server-side-validation-rules)
7. [File-write algorithm](#7-file-write-algorithm)
8. [DOM contract](#8-dom-contract)
9. [Client state model](#9-client-state-model)
10. [Keyboard contract](#10-keyboard-contract)
11. [Geometry maths](#11-geometry-maths)
12. [Auto-generated note text](#12-auto-generated-note-text)
13. [Acceptance checks](#13-acceptance-checks)

---

## 1. Purpose and safety posture

The tool lets one local user (Ben) bulk-assign a **Thoroughfare Type** to road segments and write
the result into `overrides.json` — the version-controlled, permanent record of human/Planning-Board
decisions that the GIS pipeline merges on every re-run and that **always wins** over
auto-classification (`04_classify.py` → `lib.classify_type(..., override)` returns
`(override, "override")` before any other rule; `05_export.py` honours `"exclude": true`).

`overrides.json` today holds **48 irreplaceable hand-written entries**. Therefore:

- **S1.** Nothing is written to disk until the *entire* payload has passed validation (§6).
- **S2.** Every write is: **validate → re-read → apply → serialise → round-trip verify → backup →
  temp file in the same directory → `os.fsync` → `os.replace`**. Never an in-place truncating write.
- **S3.** Unknown keys, the `_README`, and note-only entries survive every write untouched.
- **S4.** A `note` is never replaced by an empty string, and never silently dropped.
- **S5.** An override entry is removed only on an explicit `"delete": true`, and its discarded
  content is echoed back in the response.
- **S6.** Optimistic concurrency: the client must present the `base_token` it read; a mismatch is a
  `409` and writes nothing.
- **S7.** The server binds `127.0.0.1` only, serves only its own directory plus an allow-listed font
  directory, and rejects path traversal and cross-origin POSTs.

---

## 2. Repository paths

`serve.py` resolves the repository root as `Path(__file__).resolve().parents[2]` and asserts that
both data files exist at startup, exiting non-zero with a clear message if not.

```
REPO        = <repo root>                                          # .../Newcastle Core Zoning Code
SELF_DIR    = REPO/"build"/"inventory-editor"                      # static root
OVERRIDES   = REPO/"build"/"street-types"/"overrides.json"         # durable record  (WRITE)
INVENTORY   = REPO/"source"/"exhibits"/"street-types"/"inventory.json"  # rendered    (WRITE, opt-in)
FONT_DIR    = REPO/"style"/"fonts"                                 # READ ONLY
```

Backups are written **beside the file they back up**:
`build/street-types/overrides.json.bak-YYYYMMDD-HHMMSS`,
`source/exhibits/street-types/inventory.json.bak-YYYYMMDD-HHMMSS`.

`serve.py` **MUST** print the following at startup and then serve:

```
Newcastle Thoroughfare Inventory Editor
  overrides : build/street-types/overrides.json           (48 entries)
  inventory : source/exhibits/street-types/inventory.json (214 segments)
  ->  http://127.0.0.1:8765
```

Port: `8765`, overridable by `--port N`. Bind host is hard-coded `127.0.0.1` and is **not**
configurable. `--no-browser` suppresses the optional `webbrowser.open` convenience call.

---

## 3. Constants

These values **MUST** be identical in `serve.py`, `app.js` and `styles.css`. The server ships them
in `GET /api/data` so the client never hard-codes a second copy; `styles.css` restates the colours
as CSS custom properties.

### 3.1 Thoroughfare Types (order is normative — it is the display and legend order)

| # | code | name | family | colour |
|---|---|---|---|---|
| 1 | `S1` | Main Street | `S` | `#103E66` |
| 2 | `S2` | Village Street | `S` | `#2E6FA0` |
| 3 | `S3` | Neighborhood Street | `S` | `#4E97C8` |
| 4 | `S4` | Lane | `S` | `#74B2D6` |
| 5 | `S5` | Alley | `S` | `#9AC8E4` |
| 6 | `R1` | Connector Road | `R` | `#3D4A1F` |
| 7 | `R2` | Rural Road | `R` | `#5E6E33` |
| 8 | `R3` | Rural Lane | `R` | `#84934A` |
| 9 | `R4` | Highway Commercial | `R` | `#A99A4B` |
| 10 | `R5` | Rural Highway | `R` | `#C2B777` |

Family labels: `S` = "Street (urban)", `R` = "Road (rural)".
Untyped/unknown renders as `—` with colour `#BFBFBF` (`--type-none`).

### 3.2 Ownership Categories (order normative)

`"Town Way"`, `"Public Easement"`, `"Private Road"`, `"State Highway"`.
Blank/unrecorded is a legal state and renders `—`. Two segments are blank today
(`kavanagh-road-1`, `woods-island-road-1`) and carry OPEN-ITEM note-only overrides.

### 3.2b Present use (order normative) — Article 3 §5.C.3.g

`"Driveway"`, `"Thoroughfare"`. Blank/unreviewed is a legal state and renders `—`.

**Present use is REFERENCE, not classification.** It records what a segment *is today*. It
**MUST NOT** change `type`, which continues to hold the Type that would apply *on conversion*
(Article 3 §7.F) — Exhibit 3.1 shows that as the "on conversion" column. Recording it is also not
what makes an access way a Driveway: Article 3 §7.C.8 does that regardless of what is recorded
here, or whether anything is. An unreviewed or even a mis-marked segment is therefore protected
either way, and nothing in the Code turns on this field being complete.

A segment with `present_use == "Driveway"` displays as **`D`** — swatch, map stroke, and legend —
with colour `#A2988C` (`--t-D`; dark theme `#B5AB9E`). `D` is **not** an eleventh Type: it has no
entry in `TYPES`, no option in the Type `<select>`, and no `filter-type` value. The legend row for
`D` appears only once at least one segment is marked, and clicking it **MUST** set `filter-use`,
never `filter-type`.

### 3.3 House typography and palette

```css
--article-blue: #367AAC;   /* headings, links, active affordances */
--body-dark:    #231F20;   /* body text */
--muted:        #7C766F;   /* secondary text, hairlines */
--hair:         #BFBFBF;
--bg:           #FFFFFF;
--bg-alt:       #F6F5F3;   /* zebra rows, panel fill */
--danger:       #A33A2A;   /* destructive / exclusion */
--pending:      #B4761F;   /* pending-change accent */
```

Font stack **MUST** be
`font-family: "Barlow", -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;`
with `@font-face` rules loading from `/fonts/…` (§5.6). No CDN, no `@import` of a remote sheet.
Faces to declare: `Barlow-Regular.ttf` (400), `Barlow-Medium.ttf` (500), `Barlow-SemiBold.ttf` (600),
`Barlow-Bold.ttf` (700), all `font-display: swap`. If `style/fonts/` is missing the server returns
404 for `/fonts/*` and the system stack takes over — the page **MUST** remain fully usable.

---

## 4. On-disk data formats

### 4.1 `overrides.json` — the durable record (read + write)

Top-level shape, key order normative:

```json
{ "_README": "<long string>", "overrides": { "<segment-id>": { … }, … } }
```

Allowed per-entry keys and value domains:

| key | type | domain |
|---|---|---|
| `type` | string | one of the 10 codes in §3.1 |
| `present_use` | string | one of the 2 values in §3.2b |
| `ownership` | string | one of the 4 categories in §3.2 |
| `row_ft` | number | `> 0`, `<= 1000` |
| `traveled_ft` | number | `> 0`, `<= 1000` |
| `nonconformity` | string | 1–2000 chars |
| `note` | string | 1–4000 chars |
| `exclude` | boolean | **only** `true` — `false` is never written, the key is removed instead |

Current census (do not regress): 45 × `{type,note}`, 2 × `{note}` (the OPEN ITEM markers
`kavanagh-road-1`, `woods-island-road-1`), 1 × `{exclude,note}` (`station-road-3`).

#### 4.1.1 Serialisation format — normative and byte-exact

The following algorithm reproduces the current `overrides.json` **byte-for-byte**. It is verified;
do not substitute `json.dump`.

```python
KEY_ORDER = ["type", "present_use", "ownership", "row_ft", "traveled_ft", "nonconformity",
             "exclude", "note"]

def natkey(s):
    # natural sort: main-street-2 before main-street-10. Every element is a
    # 3-tuple so heterogeneous positions can never raise TypeError.
    return [(0, int(t), "") if t.isdigit() else (1, 0, t)
            for t in re.split(r"(\d+)", s)]

def entry_line(sid, entry):
    known   = [k for k in KEY_ORDER if k in entry and k != "note"]
    unknown = [k for k in entry if k not in KEY_ORDER]        # preserved verbatim
    order   = known + unknown + (["note"] if "note" in entry else [])
    inner = ", ".join(f"{json.dumps(k)}: {json.dumps(entry[k], ensure_ascii=True)}"
                      for k in order)
    return f"    {json.dumps(sid)}: {{ {inner} }}" if inner else f"    {json.dumps(sid)}: {{}}"

def serialize_overrides(doc):
    ids   = sorted(doc["overrides"], key=natkey)
    lines = [entry_line(i, doc["overrides"][i]) for i in ids]
    return ("{\n"
            f'  "_README": {json.dumps(doc["_README"], ensure_ascii=True)},\n'
            '  "overrides": {\n'
            + ",\n".join(lines) + "\n"
            "  }\n"
            "}\n")
```

Properties that **MUST** hold:

- 2-space indent; `_README` first, `overrides` second; each entry on **one** line at 4-space indent.
- `ensure_ascii=True` — the existing notes contain `—` (em dash) as an escape; changing this
  would rewrite 2 lines gratuitously and pollute the diff.
- `note` is always the **last** key in an entry; unknown keys keep their relative order and sit
  immediately before `note`.
- Exactly one trailing newline (`}\n`), no `\r`.
- Ids sorted by `natkey`. Verified: `natkey` reproduces the present on-disk order exactly.
- **Empty-diff invariant:** saving zero changes, or re-saving an unchanged document, produces a file
  byte-identical to the input. `serve.py` **MUST** carry a self-test asserting this at startup
  (`--selftest` runs it and exits).

### 4.2 `inventory.json` — the rendered inventory (read; write only on opt-in)

```json
{ "_meta": { "note": "…", "banner": "…", "crs": "EPSG:26919", "town": "NEWCASTLE" },
  "segments": [ … 214 … ] }
```

Segment object (all 13 keys always present; `null` is used for "not recorded"):

```json
{ "id": "academy-hill-1", "name": "Academy Hill",
  "termini": ["Main Street / Mills Road", "Route 1"],
  "type": "S3", "ownership": "Town Way",
  "row_ft": null, "traveled_ft": null,
  "districts": ["SD-Fabrication", "D1"], "maindot": "Local",
  "nonconformity": null, "present_use": null,
  "addresses": {"residential": 11, "unknown_type": 2, "total": 13},
  "geometry": [[456979.49, 4875907.5], …] }
```

`addresses` is the per-segment E-911 address-point count (nearest segment within 60 m), written by
`build/street-types/05_export.py`. It is a **REVIEW AID ONLY** — decision support for the Article 3
§5.C.3.g present-use review, never a determination; §7.C.8 decides what is a Driveway whatever is
counted here. **`unknown_type` matters as much as `residential`:** 311 of Newcastle's 1227 address
points carry no `PLACE_TYPE` at all, so `residential: 0, unknown_type: 2` means NOT REVIEWED, not
NOT PRESENT. The UI **MUST** render the two distinctly (`.seg-homes` + `.seg-homes-unk`, "0 +2?")
and **MUST NOT** fold them into one number — a confident-looking zero that is not one is exactly
the failure this record cannot afford. Address RANGES on the road layer (`L_ADD_FROM`/`L_ADD_TO`)
are **not** a substitute: measured 2026-08-24, Barrol Point Road (a driveway serving one house)
reads 2-24, identical to Academy Hill, a real Neighborhood Street. Ranges are addressing capacity,
not structures.

The `districts` and `maindot` fields remain in the data but are **no longer displayed** (columns
removed 2026-08-24) — the same treatment `row_ft`/`traveled_ft` received when Exhibit 3.1's columns
were trimmed. The District *filter* is retained; only the columns went.

Serialisation: `json.dumps(doc, indent=1)` — **no trailing newline**, `ensure_ascii=True` (default).
Verified byte-identical against the current file. Segment order **MUST** be preserved exactly as
read (it is the pipeline's order; the exhibits number rows 1..N from it).

Observed value domains (for building filter menus, but the client **MUST** derive them from the
data, not hard-code them):
`districts` ∈ {D1, D2, D3, D4, D5, D6, SD-Campus, SD-Civic, SD-Conservation, SD-Fabrication,
SD-Highway Commercial, SD-Historic, SD-Marine, SD-Rural Highway};
`maindot` ∈ {null, Local, Minor Collector, Major Collector, Other Principal Arterial};
`row_ft`, `traveled_ft`, `nonconformity` are `null` for all 214 segments today.

### 4.3 Id ↔ road grouping

Every id matches `^(?P<road_key>[a-z0-9]+(?:-[a-z0-9]+)*)-(?P<seq>\d+)$`. Verified over all 214
segments: 148 distinct `road_key`s, and `road_key ↔ name` is a **bijection** (no road_key maps to
two names, no name maps to two road_keys). Grouping by `road_key` and grouping by `name` are
therefore equivalent; **group by `road_key`** (stable, no punctuation/whitespace ambiguity) and
**display `name`**. Max segments in a road: 12 (`main-street`, `route-1`); 130 roads have one.

### 4.4 Excluded and orphan overrides

`station-road-3` carries `"exclude": true` and is consequently **absent** from `inventory.json`
(214 segments, not 215). An override id with no matching segment is an **orphan**, reported
separately (§5.4). The client **MUST** render orphans in a distinct, non-editable-by-default list —
they must never be mistaken for missing data and never be silently dropped on save.

---

## 5. HTTP API

All responses are `application/json; charset=utf-8` unless stated. All API responses carry
`Cache-Control: no-store`. Request bodies are UTF-8 JSON, max **2 MiB** (larger → `413`).

### 5.1 Envelope

Success: the body is an object with `"ok": true` plus endpoint-specific keys.
Failure: **always** exactly this shape:

```json
{ "ok": false,
  "error": { "code": "validation_failed",
             "message": "3 problems in 2 changes; nothing was written.",
             "details": [ … ] } }
```

`error.code` is a stable machine token; `error.message` is one human sentence; `error.details` is an
array (possibly empty) whose element shape depends on the code.

| HTTP | `code` | when |
|---|---|---|
| 400 | `bad_json` | body is not valid JSON |
| 400 | `bad_content_type` | POST without `Content-Type: application/json` |
| 400 | `bad_payload` | top-level payload shape wrong (§6.1) |
| 400 | `validation_failed` | one or more changes invalid (§6.2); `details` = §6.4 |
| 403 | `forbidden_host` | `Host` header not `127.0.0.1:<port>` / `localhost:<port>` |
| 403 | `forbidden_origin` | POST with an `Origin`/`Referer` that is not this server |
| 404 | `not_found` | unknown path |
| 405 | `method_not_allowed` | wrong verb; response carries `Allow:` |
| 409 | `stale_base` | `base_token` ≠ current on-disk token (§7.2); `details` = `[{"expected","actual"}]` |
| 413 | `payload_too_large` | body > 2 MiB |
| 500 | `corrupt_overrides` | `overrides.json` unreadable/unparseable |
| 500 | `corrupt_inventory` | `inventory.json` unreadable/unparseable |
| 500 | `io_error` | backup/temp/replace failed; `details` carries the stage |
| 500 | `internal` | anything else; message is `repr(exc)` truncated to 300 chars |

**Invariant:** every non-2xx response guarantees **no file on disk was modified**, with the single
documented exception of a partial success in §5.5 (`overrides` written, `inventory` failed) which is
reported as **200 with `ok: true`** and a populated `inventory.error`.

### 5.2 `GET /api/health`

```json
{ "ok": true, "contract": "1.0.0", "port": 8765,
  "overrides_path": "build/street-types/overrides.json",
  "inventory_path": "source/exhibits/street-types/inventory.json" }
```

### 5.3 `GET /api/data`

No parameters. Re-reads both files from disk on every call (never cached in memory across requests),
so an external edit is picked up by a browser reload.

```json
{
  "ok": true,
  "contract": "1.0.0",
  "generated_at": "2026-08-20T18:04:11Z",
  "base_token": "130d46a2c3534dec",
  "inventory_token": "a1b2c3d4e5f60718",

  "meta": { "note": "…", "banner": "DRAFT — Types auto-derived…",
            "crs": "EPSG:26919", "town": "NEWCASTLE" },

  "types": [ { "code": "S1", "name": "Main Street", "family": "S", "color": "#103E66" }, … ],
  "families": [ { "code": "S", "label": "Street (urban)" },
                { "code": "R", "label": "Road (rural)" } ],
  "ownership_categories": ["Town Way", "Public Easement", "Private Road", "State Highway"],
  "districts": ["D1", "D2", "D3", "D4", "D5", "D6", "SD-Campus", … ],
  "maindot_classes": ["Local", "Minor Collector", "Major Collector", "Other Principal Arterial"],

  "view": { "vbw": 1000, "vbh": 1549, "pad": 16,
            "minx": 449758.99, "miny": 4870123.17,
            "maxx": 458820.65, "maxy": 4884320.17,
            "scale": 0.1068240, "offx": 16.0, "offy": 16.212,
            "units_per_ft": 0.032566 },

  "roads": [ { "road_key": "academy-hill", "name": "Academy Hill",
               "segment_ids": ["academy-hill-1", …], "n": 6,
               "length_ft": 4821.3, "types": ["S3"], "override_count": 2 }, … ],

  "segments": [ … §5.3.1 … ],
  "orphan_overrides": [ { "id": "station-road-3",
                          "entry": { "exclude": true, "note": "Not a thoroughfare: …" },
                          "reason": "excluded" } ],

  "counts": { "segments": 214, "roads": 148,
              "overrides": 48, "override_typed": 45, "override_note_only": 2,
              "override_excluded": 1, "override_orphan": 1,
              "with_override": 47, "without_override": 167,
              "by_type": { "S1": 14, "S2": 5, "S3": 18, "S4": 2, "S5": 0,
                           "R1": 25, "R2": 132, "R3": 4, "R4": 6, "R5": 8, "": 0 },
              "by_ownership": { "Town Way": 79, "Public Easement": 0,
                                "Private Road": 105, "State Highway": 28, "": 2 } },
  "warnings": []
}
```

`counts.by_type` **MUST** include all 10 codes even at zero (so the summary bar has stable slots),
plus `""` for untyped segments. `roads` is sorted by `name` (locale-independent
`str.casefold()`), and `segments` preserves the file order (§4.2).

#### 5.3.2 `counts` definitions — normative, and the verified baseline

These are easy to get subtly wrong (an override entry is not the same thing as an overridden
segment). Each key has exactly one definition:

| key | definition | today |
|---|---|---|
| `segments` | `len(inventory["segments"])` | 214 |
| `roads` | distinct `road_key` over segments | 148 |
| `overrides` | `len(overrides)` — **entries in the file**, including orphans | 48 |
| `override_typed` | entries with a `type` key | 45 |
| `override_note_only` | entries whose key set is exactly `{"note"}` | 2 |
| `override_excluded` | entries with `exclude is True` | 1 |
| `override_orphan` | entries whose id is not a current segment id | 1 |
| `with_override` | **segments** where `id in overrides` (includes note-only) | **47** |
| `without_override` | `segments - with_override` | **167** |
| `by_type` | segments grouped by `type`; all 10 codes present, `""` for untyped | Σ = 214 |
| `by_ownership` | segments grouped by `ownership`; all 4 categories present, `""` for blank | Σ = 214 |

Baseline arithmetic that **MUST** hold on load: `45 + 2 + 1 = 48`; `47 + 167 = 214`;
`45 typed entries` all resolve to live segments; `Σ by_type = Σ by_ownership = 214`.
`override_drift` is **0** today — the promoted inventory is currently in step with the durable
record, so any non-zero drift after a save means the inventory was not applied.

`warnings` is an array of `{ "code": …, "message": …, "ids": [ … ] }`. Emitted cases:

| `code` | meaning |
|---|---|
| `override_drift` | `overrides[id].type` ≠ `segment.type` — the promoted inventory is out of step with the durable record (a pipeline re-run or an apply-to-inventory is due) |
| `orphan_override` | an override id matches no segment and is not an exclusion |
| `blank_ownership` | segment ownership is null (the 2 OPEN ITEMs) |
| `unknown_key` | an override entry carries a key outside §4.1 (preserved, but flagged) |

#### 5.3.1 Segment object in `GET /api/data`

```json
{
  "id": "academy-hill-1",
  "road_key": "academy-hill",
  "seq": 1,
  "name": "Academy Hill",
  "termini": ["Main Street / Mills Road", "Route 1"],
  "type": "S3",
  "ownership": "Town Way",
  "row_ft": null,
  "traveled_ft": null,
  "districts": ["SD-Fabrication", "D1"],
  "maindot": "Local",
  "nonconformity": null,
  "length_ft": 412.7,
  "has_override": false,
  "override": null,
  "type_source": "auto",
  "auto_type": "S3",
  "excluded": false,
  "path": "M787.32 914.88L786.33 916.0…",
  "mid": [788.4, 910.2],
  "geometry": [[456979.49, 4875907.5], …]
}
```

Field notes, all normative:

- `length_ft` — §11.2, rounded to **1 decimal place**.
- `override` — the **verbatim** entry from `overrides.json`, or `null`. Unknown keys included.
- `has_override` — `id in overrides` (true even for a note-only marker).
- `type_source` — `"override"` if the override entry has a `type` key, else `"auto"`.
- `auto_type` — `segment.type` when `type_source == "auto"`, otherwise **`null`**. The
  auto-classification for an overridden segment is *not recoverable* from these two files (it needs
  `district_fracs` from `03_join`), so the server **MUST NOT** guess it. The UI must not claim to
  show "what the classifier said" for an overridden segment.
- `excluded` — `override.exclude is True`. Always `false` for segments present in `inventory.json`;
  a segment only becomes `excluded: true` here after a save that wrote the flag but did **not**
  apply to the inventory.
- `path` — the SVG `d` attribute, pre-projected into the `view` box (§11.1), coordinates rounded to
  2 dp, `M x y` then `L x y` per point, no trailing space. Server-computed so the map cannot drift
  from the contract; the client **MAY** recompute with the identical formula.
- `mid` — projected midpoint of the polyline **by cumulative length** (not the middle vertex), for
  placing the selection marker.
- `geometry` — passed through verbatim so the client can recompute projections when zooming.

### 5.4 `POST /api/validate`

Dry run. **Identical** request shape and validation path as `/api/save`, but never touches disk.
Returns `200` with:

```json
{ "ok": true, "valid": true, "would_write": { "overrides": 7, "inventory": 6 },
  "notes_missing": ["timber-lane-2"], "removals": [], "warnings": [] }
```

or the ordinary `400 validation_failed` envelope. `base_token` **is** checked (so the client can
detect staleness before assembling a save).

### 5.5 `POST /api/save`

Request:

```json
{
  "contract": "1.0.0",
  "base_token": "130d46a2c3534dec",
  "apply_to_inventory": true,
  "changes": [
    { "id": "timber-lane-1",
      "set": { "type": "R2", "note": "Board correction: R4 -> R2." } },

    { "id": "eden-lane-1",
      "set": { "ownership": "Private Road" } },

    { "id": "kavanagh-road-1",
      "set": { "ownership": "Town Way",
               "note": "Ownership confirmed against the Town's road records (2026-08-20)." } },

    { "id": "some-fragment-2",
      "set": { "exclude": true, "note": "Not a thoroughfare: orphan E-911 fragment." } },

    { "id": "old-entry-1", "delete": true }
  ]
}
```

**`set` semantics — normative:**

| value in `set` | effect on the override entry |
|---|---|
| a valid value | set that key |
| `null` | **remove** that key from the entry |
| `"exclude": true` | set `"exclude": true` |
| `"exclude": false` | **remove** the `exclude` key (`false` is never written) |
| `"note": ""` or `"note": null` | **preserve** the existing note; if none exists, write no `note` key and emit a `note_missing` warning. Never writes `""`. |
| key absent from `set` | that key is left exactly as it is on disk |

`{"id": X, "delete": true}` removes the whole entry, and **only** that form does. `delete` and `set`
are mutually exclusive on one change object. The response echoes the removed entry.

Response `200`:

```json
{
  "ok": true,
  "contract": "1.0.0",
  "base_token": "77aa11bb22cc33dd",
  "inventory_token": "44ee55ff66007788",
  "saved_at": "2026-08-20T18:07:44Z",
  "overrides": {
    "written": true,
    "path": "build/street-types/overrides.json",
    "backup": "build/street-types/overrides.json.bak-20260820-180744",
    "entries_before": 48, "entries_after": 51,
    "created": ["some-fragment-2"],
    "updated": ["timber-lane-1", "eden-lane-1", "kavanagh-road-1"],
    "removed": [ { "id": "old-entry-1",
                   "entry": { "type": "R2", "note": "…the discarded note, verbatim…" } } ],
    "unchanged": [],
    "backups_pruned": ["build/street-types/overrides.json.bak-20260731-091203"]
  },
  "inventory": {
    "written": true,
    "path": "source/exhibits/street-types/inventory.json",
    "backup": "source/exhibits/street-types/inventory.json.bak-20260820-180744",
    "segments_before": 214, "segments_after": 213,
    "fields_updated": 6,
    "segments_removed": ["some-fragment-2"],
    "skipped": [ { "id": "eden-lane-1", "field": "type", "reason": "key_removed" } ],
    "error": null
  },
  "counts": { "…exactly the §5.3 `counts` object, recomputed post-write…" },
  "warnings": [ { "code": "note_missing", "message": "…", "ids": ["eden-lane-1"] } ]
}
```

If `apply_to_inventory` is `false`, `inventory` is
`{ "written": false, "reason": "not_requested" }` and no backup is taken.

**Partial success.** If `overrides.json` was written and the inventory write then failed, the
response is `200 ok:true` with `overrides.written: true` and
`inventory: { "written": false, "error": { "code": "io_error", "message": "…" } }`. The client
**MUST** surface this as a warning state (not success, not failure) and **MUST** clear the pending
list, because the durable record already reflects the change; the inventory can be regenerated.

**Empty change list.** `changes: []` is valid, is a no-op, writes nothing (not even a backup), and
returns `overrides.written: false, reason: "no_changes"`.

### 5.6 Static file serving

| path | serves | `Content-Type` | cache |
|---|---|---|---|
| `/` | `index.html` | `text/html; charset=utf-8` | `no-store` |
| `/index.html` | same | `text/html; charset=utf-8` | `no-store` |
| `/app.js` | `app.js` | `text/javascript; charset=utf-8` | `no-store` |
| `/styles.css` | `styles.css` | `text/css; charset=utf-8` | `no-store` |
| `/favicon.ico` | — | — | `204 No Content` if absent |
| `/fonts/<name>` | `style/fonts/<name>` | `font/ttf` or `font/otf` | `max-age=86400` |

Rules, all **MUST**:

1. The static allow-list is exactly `{"/", "/index.html", "/app.js", "/styles.css", "/favicon.ico"}`
   plus the `/fonts/` prefix. Every other path → `404 not_found`. **No directory listing**, no
   walking, no `SimpleHTTPRequestHandler` default behaviour.
2. `/fonts/<name>`: `name` must match `^[A-Za-z0-9._-]+\.(ttf|otf)$`, must not contain `..`, and the
   `Path(FONT_DIR/name).resolve()` must have `FONT_DIR.resolve()` as a parent. Additionally `name`
   must be in the on-disk listing of `FONT_DIR` (no invention).
3. Percent-decode **before** the traversal check; reject any decoded path containing `..`, a
   backslash, a NUL, or a leading `//`.
4. Reject requests whose `Host` header is not `127.0.0.1:<port>` or `localhost:<port>` → `403
   forbidden_host` (DNS-rebinding guard).
5. On `POST`, if an `Origin` header is present it must equal `http://127.0.0.1:<port>` or
   `http://localhost:<port>`; otherwise `403 forbidden_origin`.
6. Send `X-Content-Type-Options: nosniff` on every response.
7. `log_message` is overridden to a one-line `METHOD path -> status` on stderr; the request line is
   never echoed into HTML.

---

## 6. Server-side validation rules

Validation is a **pure function** `validate(payload, overrides_doc, inventory_doc) -> (plan, errors,
warnings)`. It runs to completion collecting **all** errors before returning; the caller writes only
when `errors == []`. `/api/validate` and `/api/save` call the same function.

### 6.1 Payload shape

- Body **MUST** be a JSON object.
- `contract` — optional string; if present and its major version ≠ `1`, → `bad_payload`.
- `base_token` — **required** non-empty string (§7.2).
- `apply_to_inventory` — **required** boolean.
- `changes` — **required** array, length `0..1000`. Longer → `bad_payload`.
- Any unexpected top-level key → `bad_payload` (fail closed; catches client/server skew).

### 6.2 Per-change rules

For `changes[i]`:

1. **MUST** be an object with an `id` key.
2. `id` **MUST** be a string matching `^[a-z0-9]+(?:-[a-z0-9]+)*$`, ≤ 120 chars → else
   `invalid_id`.
3. `id` **MUST** exist as a segment id in `inventory.json` **or** as a key in
   `overrides.json` → else `unknown_id`. (Blocks typo'd and invented ids.)
4. Exactly one of `set` (object) or `delete` (boolean `true`) → else `bad_change`.
5. Ids **MUST** be unique across `changes` → else `duplicate_id` on the second and later
   occurrences.
6. If `delete`: the id must currently exist in `overrides.json` → else `nothing_to_delete`.
7. If `set`: it **MUST** be a non-empty object whose keys are a subset of
   `{type, ownership, row_ft, traveled_ft, nonconformity, note, exclude}` → else `unknown_field`
   (naming the offending key). *Unknown keys already on disk are preserved (§7.4) but may not be
   introduced through the API.*

### 6.3 Per-field rules

| field | accepted | error code |
|---|---|---|
| `type` | one of the 10 codes (case-sensitive) or `null` | `invalid_type` |
| `ownership` | one of the 4 categories (exact string) or `null` | `invalid_ownership` |
| `row_ft` | `int`/`float`, finite, `> 0`, `<= 1000`, or `null`. **`bool` is rejected** (Python `bool` is an `int`). Stored rounded to 2 dp. | `invalid_number` |
| `traveled_ft` | same as `row_ft` | `invalid_number` |
| `nonconformity` | string, after `strip()` 1–2000 chars, or `null`/`""` (→ remove key) | `invalid_text` |
| `note` | string, after `strip()` 1–4000 chars, or `null`/`""` (→ preserve existing, §5.5) | `invalid_text` |
| `exclude` | `true` or `false` only (not `1`/`0`/`"true"`) | `invalid_exclude` |

Text normalisation applied to `note` and `nonconformity` before length checks and before writing:
strip leading/trailing whitespace; replace `\r\n` and `\r` with `\n`; reject any remaining C0
control character other than `\n` and `\t` → `invalid_text`. Unicode is allowed and is escaped by
`ensure_ascii=True` on write.

### 6.4 Error detail shape

```json
{ "index": 3, "id": "timber-lane-9", "field": "type",
  "code": "invalid_type", "message": "\"R9\" is not one of S1…S5, R1…R5." }
```

`field` is `null` for change-level errors. `index` is the position in the request's `changes` array.

### 6.5 Warnings (never block a write)

| `code` | condition |
|---|---|
| `note_missing` | a change creates or modifies an entry that ends up with no `note` |
| `note_preserved` | the change supplied an empty note and an existing note was kept |
| `no_op` | the change would leave the entry byte-identical to what is on disk |
| `exclude_destructive` | `exclude: true` with `apply_to_inventory: true` — the segment will be **removed** from `inventory.json` |
| `key_removed_not_restorable` | a `null` removal for `type`/`ownership`; the auto value cannot be restored without a pipeline re-run (§7.6) |
| `override_drift` | as §5.3 |

---

## 7. File-write algorithm

`serve.py` **MUST** implement exactly this order. Any exception before step 7 leaves both files
untouched.

```
 1. Read overrides.json bytes  -> parse (OrderedDict). Fail -> 500 corrupt_overrides.
 2. token = sha256(bytes).hexdigest()[:16]; if token != payload.base_token -> 409 stale_base.
 3. If apply_to_inventory: read + parse inventory.json. Fail -> 500 corrupt_inventory.
 4. plan, errors, warnings = validate(...). If errors -> 400 validation_failed. NOTHING WRITTEN.
 5. new_doc = deepcopy(overrides_doc); apply plan (§7.4).
 6. text = serialize_overrides(new_doc)                                   (§4.1.1)
    ASSERT json.loads(text) == new_doc            -> else 500 internal ("round-trip mismatch")
    ASSERT json.loads(text)["_README"] == overrides_doc["_README"]  -> else 500 internal
    If text == original_bytes.decode(): no-op -> return written:false, reason:"no_changes".
 7. backup:  shutil.copy2(overrides.json, overrides.json.bak-YYYYMMDD-HHMMSS)   (§7.3)
 8. write:   tmp = overrides.json.tmp-<pid>-<6 hex>  in the SAME directory
             f.write(text); f.flush(); os.fsync(f.fileno()); close
             os.replace(tmp, overrides.json)
             (best effort) fsync the containing directory fd
 9. prune backups to the 10 most recent                                      (§7.3)
10. If apply_to_inventory: repeat 6-9 for inventory.json with §7.6 rules.
    A failure here does NOT roll back step 8; report partial success (§5.5).
11. Recompute and return the §5.3 `counts`, the new base_token and inventory_token.
```

`tmp` files **MUST** be removed in a `finally` on any failure. `tmp` and `.bak-` files **MUST** be
excluded from the fonts/static allow-list (they are outside `SELF_DIR`, so §5.6 already blocks
them).

### 7.1 Token computation

`token(path) = hashlib.sha256(path.read_bytes()).hexdigest()[:16]`. `base_token` covers
`overrides.json`; `inventory_token` covers `inventory.json` and is informational (returned, not
enforced — the inventory is regenerable).

### 7.2 Optimistic concurrency

If `base_token` mismatches, respond `409 stale_base` with
`details: [{"expected": "<client>", "actual": "<disk>"}]`. The client **MUST** show a blocking
notice ("the file changed on disk — reload to merge") and **MUST NOT** auto-retry or auto-reload
(that would discard pending work). The user reloads deliberately via `#reload-btn`.

### 7.3 Backups

- Name: `<filename>.bak-%Y%m%d-%H%M%S` (local time), beside the original.
- Collision (two saves in the same second): append `-2`, `-3`, … until free.
- Pruning: after a successful write, list `<filename>.bak-*` in that directory, sort by name
  descending (the timestamp format sorts lexicographically = chronologically), keep the **10**
  newest, `unlink()` the rest. Report deleted paths in `backups_pruned`. Pruning failure is a
  warning, never an error.
- Backups are **not** created for a no-op save.
- `.gitignore` **MUST** be extended by the implementer to ignore `*.bak-*` and `*.tmp-*` under
  `build/street-types/` and `source/exhibits/street-types/`. *(Do not commit; standing rule #1.)*

### 7.4 Applying a plan to the overrides document

For each change, in `changes` array order:

```
delete:  entry = doc["overrides"].pop(id)   -> record {"id": id, "entry": entry} in `removed`

set:     entry = doc["overrides"].get(id)   (existing dict, or {} if new)
         existing_note = entry.get("note")
         for k, v in change["set"].items():
             if k == "note":
                 if v is None or v.strip() == "":  keep existing_note (do not touch)
                 else:                             entry["note"] = normalised(v)
             elif k == "exclude":
                 if v is True:  entry["exclude"] = True
                 else:          entry.pop("exclude", None)
             elif v is None:    entry.pop(k, None)
             else:              entry[k] = coerced(v)
         doc["overrides"][id] = entry
```

**Preservation guarantees, all MUST:**

- Keys of `entry` not named in `set` are untouched — including keys outside §4.1 (`unknown_key`
  warning is emitted, the key is written back verbatim in its original relative position, §4.1.1).
- `_README` is never read into the mutation path and never rewritten — it is re-emitted from the
  parsed original string.
- A **note-only** entry (`{"note": …}` with no other key) is a first-class state: it is never
  pruned, never auto-completed, and survives a save that does not name it. The two OPEN ITEM
  markers **MUST** be byte-identical after any save that does not target them.
- An entry that ends up `{}` after removals is written as `"id": {}` and flagged
  `warning: empty_entry`. It is **not** auto-deleted (only `delete: true` deletes).
- Ordering is irrelevant to the on-disk result — the serialiser re-sorts by `natkey`.

### 7.5 Post-mutation invariants (assert before writing)

1. `set(new_doc) == {"_README", "overrides"}`.
2. `new_doc["_README"]` is the identical string object value as read.
3. Every entry is a `dict` with ≥ 0 keys and only JSON scalars/strings as values.
4. Every `type` value ∈ §3.1; every `ownership` ∈ §3.2; every `exclude` is exactly `True`.
5. No entry contains `"note": ""`.
6. `len(new_doc["overrides"]) == 48 + len(created) - len(removed)` for the current baseline.

A failed assert → `500 internal`, nothing written.

### 7.6 Applying to `inventory.json`

Only **positive** values propagate. Mapping:

| override key | inventory segment field | on `null` removal |
|---|---|---|
| `type` | `type` | **skip**, warn `key_removed_not_restorable`, record in `inventory.skipped` |
| `ownership` | `ownership` | **skip**, same |
| `row_ft` | `row_ft` | set to `null` (the pipeline emits `null` for these anyway) |
| `traveled_ft` | `traveled_ft` | set to `null` |
| `nonconformity` | `nonconformity` | set to `null` |
| `note` | — | never propagated (the inventory has no note field) |
| `exclude: true` | — | **remove the whole segment object** from `segments` |
| `exclude` removed | — | cannot restore geometry; **skip**, warn `exclude_not_restorable` |

Rules:

- Segment order is preserved; removals are done with a filtering list comprehension.
- `_meta` is passed through **verbatim**, including the DRAFT `banner`. The editor **MUST NOT**
  edit `_meta` — the banner is a legal statement about adoption status.
- A change whose id is not a current segment (an orphan) is silently skipped for the inventory and
  recorded in `inventory.skipped` with `reason: "not_in_inventory"`.
- Serialise with `json.dumps(doc, indent=1)` and **no** trailing newline (§4.2), then the same
  backup → temp → `os.replace` dance.
- `fields_updated` counts individual field assignments, not segments.

---

## 8. DOM contract

Every id below is **reserved**; `app.js` binds to it by `getElementById` / `querySelector`. Ids are
`kebab-case`. Repeating elements carry a **class** and a `data-*` key, never a generated id.

### 8.0 Page skeleton

```html
<body>
  <header id="topbar"> … §8.1 … </header>
  <section id="filters"> … §8.2 … </section>
  <main id="main">
    <section id="table-panel"> … §8.3 … </section>
    <section id="map-panel">  … §8.4 … </section>
  </main>
  <aside id="pending-panel"> … §8.5 … </aside>
  <dialog id="note-dialog">   … §8.6 … </dialog>
  <dialog id="confirm-dialog">… §8.7 … </dialog>
  <dialog id="help-dialog">   … §8.8 … </dialog>
  <div id="toast-container"></div>
  <div id="shortcut-hint" hidden></div>
  <div id="blocking-overlay" hidden><p id="blocking-message"></p></div>
  <!-- templates, §8.9 -->
</body>
```

Layout: `#main` is a CSS grid, `#table-panel` flexible and `#map-panel` a fixed-width column
(≈ 380–460 px, min 320 px) that is `position: sticky` to the viewport height. `#pending-panel` is a
right-hand drawer, `hidden` when the pending count is 0, shown otherwise; it **MUST NOT** overlay
the save button. Below 1100 px the map column collapses under the table (`#map-panel` gets
`.is-stacked`).

### 8.1 `#topbar` — identity, summary bar, global actions

| id | element | purpose |
|---|---|---|
| `#app-title` | `h1` | "Thoroughfare Type Editor" |
| `#app-subtitle` | `p` | "Newcastle Core Zoning Code · Article 3 §5 Inventory" |
| `#data-banner` | `div` | renders `meta.banner` (the DRAFT statement). `hidden` if empty. |
| `#summary-bar` | `div` | container for the live summary |
| `#summary-total` | `span` | "214 segments" — `counts.segments` |
| `#summary-roads` | `span` | "148 roads" |
| `#summary-overrides` | `span` | "45 Type overrides" — `counts.override_typed` (**not** `with_override`; the planner cares about typed decisions) |
| `#summary-noteonly` | `span` | "2 open items" — `counts.override_note_only` |
| `#summary-excluded` | `span` | "1 excluded" — `counts.override_excluded` |
| `#summary-pending` | `span` | "3 pending" — pending count; gets `.is-active` when > 0 |
| `#summary-types` | `div` | flow container of type chips (clone `#tpl-type-chip`) |
| `#reload-btn` | `button` | re-`GET /api/data`; **MUST** confirm if pending > 0 |
| `#help-btn` | `button` | opens `#help-dialog` |
| `#conn-status` | `span` | `.is-ok` / `.is-error` / `.is-saving`; text is one short phrase |

**Type chip** (from `#tpl-type-chip`), root class `.type-chip`, attribute `data-type="S1"`:
`.type-chip-swatch` (background = type colour) · `.type-chip-code` (`S1`) · `.type-chip-count`
(integer). Clicking a chip **MUST** set `#filter-type` to that code. A chip with count 0 gets
`.is-empty` and is dimmed but still rendered (stable slots, §5.3).

### 8.2 `#filters` — search and filter controls

| id | element | binding |
|---|---|---|
| `#filter-search` | `input[type=search]` | free text over `name`, `id`, `termini[0]`, `termini[1]`, and the override `note`; case- and diacritic-insensitive substring; debounced 120 ms |
| `#filter-type` | `select` | `""` = "All Types", then the 10 codes as `S1 — Main Street`, plus `__none__` = "Untyped" |
| `#filter-family` | `select` | `""` / `S` / `R` *(optional)* |
| `#filter-district` | `select` | `""` = "All Districts", then `data.districts` |
| `#filter-ownership` | `select` | `""` = "All Ownership", then the 4 categories, plus `__blank__` = "Not recorded" |
| `#filter-override` | `select` | `""` = "Any", `has` = "Has override", `none` = "No override", `typed` = "Type overridden", `noteonly` = "Note-only", `excluded` = "Excluded", `drift` = "Drift vs inventory" |
| `#filter-pending` | `input[type=checkbox]` | "Only pending changes" |
| `#filter-clear` | `button` | resets every control above and clears selection |
| `#filter-result-count` | `span` | "Showing 27 of 214 segments in 6 roads" |

Filters compose with **AND**. A road group row is rendered when ≥ 1 of its segments passes; only
passing segments are rendered inside it. Filtering **MUST NOT** alter the selection set or the
pending set — a pending change on a filtered-out segment stays pending and stays visible in
`#pending-list`.

### 8.3 `#table-panel` — bulk bar and the segment table

#### 8.3.1 `#bulk-bar` (sticky above the table)

| id | element | purpose |
|---|---|---|
| `#selection-count` | `span` | "6 segments selected · 2 roads · 4,812 ft" |
| `#type-palette` | `div` | ten `button.type-btn[data-type][data-index]`, in §3.1 order. Each shows a colour swatch, the code, the name, and the shortcut digit. `disabled` when selection is empty. |
| `#bulk-ownership` | `select` | `""` = "Set ownership…", the 4 categories, `__blank__` = "Clear (not recorded)" |
| `#bulk-ownership-apply` | `button` | stages an ownership change on the selection |
| `#bulk-exclude` | `button` | `.is-danger`; toggles `exclude` on the selection; **MUST** route through `#confirm-dialog` |
| `#bulk-clear-note` | `button` | *(optional)* opens `#note-dialog` to re-note the selection without changing values |
| `#select-all` | `input[type=checkbox]` | selects/deselects every **currently visible** segment; supports `indeterminate` |
| `#selection-clear` | `button` | clears selection |
| `#selection-invert` | `button` | *(optional)* |

#### 8.3.2 `#segment-table`

```html
<table id="segment-table">
  <thead>
    <tr id="segment-head">
      <th class="col-check">…contains #select-all…</th>
      <th class="col-name"      data-sort="name">Road / Segment</th>
      <th class="col-termini"   data-sort="termini">From → To</th>
      <th class="col-type"      data-sort="type">Type</th>
      <th class="col-length"    data-sort="length">Length</th>
      <th class="col-ownership" data-sort="ownership">Ownership</th>
      <th class="col-homes"     data-sort="homes">Homes</th>
      <th class="col-source"    data-sort="source">Source</th>
      <th class="col-actions"></th>
    </tr>
  </thead>
  <tbody id="segment-tbody"></tbody>
</table>
<p id="empty-state" hidden>No segments match these filters.</p>
```

Sortable headers carry `data-sort`; the active one gets `.is-sorted` plus `data-dir="asc|desc"`.
Default sort: road `name` ascending, then `seq` ascending. Sorting reorders **road groups**;
segments within a road are **always** ordered by `seq` (they are a physical sequence).

#### 8.3.3 Road group row — clone of `#tpl-road-row`

```html
<tr class="road-row" data-road-key="main-street">
  <td class="cell-check"><input type="checkbox" class="road-check" aria-label="Select all of this road"></td>
  <td class="cell-road" colspan="2">
    <button class="road-toggle" aria-expanded="true">▾</button>
    <span class="road-name">Main Street</span>
    <span class="road-count">12 segments</span>
    <span class="road-flag-override">10 overridden</span>
  </td>
  <td class="cell-type">
    <select class="road-type-select" aria-label="Set Type for the whole road">
      <option value="">— set whole road —</option>
      <!-- 10 type options, injected by app.js -->
    </select>
    <span class="road-types"><!-- .type-pill per distinct type present --></span>
  </td>
  <td class="cell-length"><span class="road-length">8,144 ft</span></td>
  <td class="cell-ownership" colspan="4"><span class="road-ownership">State Highway</span></td>
  <td class="cell-actions"><button class="road-zoom" title="Show on map">◎</button></td>
</tr>
```

- `.road-type-select` firing `change` **MUST** stage a type change for **every** segment in that
  road (the "all of Main Street is S1" action) and then reset itself to `""`.
- `.road-check` selects/deselects all of the road's **visible** segments; supports `indeterminate`.
- `.road-toggle` collapses the road's segment rows (`.is-collapsed` on the `<tr class="road-row">`
  and `hidden` on its segment rows). Collapsed state is client-only, not persisted.
- `.road-types` holds one `span.type-pill[data-type]` per distinct type in the road; a road with
  more than one type gets `.is-mixed` on the road row (this is the "suspicious road" tell).
- `.road-ownership` shows the single ownership if uniform, else "mixed".

#### 8.3.4 Segment row — clone of `#tpl-segment-row`

```html
<tr class="segment-row" data-id="main-street-3" data-road-key="main-street" data-seq="3" tabindex="-1">
  <td class="cell-check"><input type="checkbox" class="seg-check"></td>
  <td class="cell-name">
    <span class="seg-name">Main Street</span>
    <span class="seg-seq">#3</span>
    <code class="seg-id">main-street-3</code>
  </td>
  <td class="cell-termini">
    <span class="seg-from">Mills Road</span>
    <span class="seg-arrow">→</span>
    <span class="seg-to">River Road</span>
  </td>
  <td class="cell-type">
    <span class="type-swatch"></span>
    <select class="seg-type-select" aria-label="Thoroughfare Type">
      <option value="">—</option>
      <!-- 10 type options, injected by app.js -->
    </select>
  </td>
  <td class="cell-length"><span class="seg-length">1,204 ft</span></td>
  <td class="cell-ownership">
    <select class="seg-ownership-select" aria-label="Ownership Category">
      <option value="">—</option>
      <!-- 4 options, injected by app.js -->
    </select>
  </td>
  <td class="cell-homes"><span class="seg-homes">11</span><span class="seg-homes-unk"> +2?</span></td>
  <td class="cell-source"><span class="seg-source" data-source="override">override</span></td>
  <td class="cell-actions">
    <button class="seg-detail-btn" title="Inspect">i</button>
    <button class="seg-note-btn"   title="Edit note">✎</button>
    <button class="seg-exclude-btn" title="Exclude from inventory">⊘</button>
  </td>
</tr>
```

State classes on `tr.segment-row`, all set by `app.js`:

| class | meaning |
|---|---|
| `.is-selected` | in the selection set |
| `.is-focused` | the keyboard cursor row (exactly one at a time) |
| `.is-pending` | has a staged, unsaved change |
| `.is-hovered` | mirrors a map hover |
| `.has-override` | `has_override` is true |
| `.is-note-only` | override exists but sets no value |
| `.is-excluded` | `exclude` is (or will be) true — render struck through |
| `.is-drift` | override type ≠ inventory type |
| `.is-blank-ownership` | ownership is null |

`.seg-source` `data-source` ∈ `auto | override | pending`. `.type-swatch` background = the current
(post-pending) type colour. When a row is pending, the type cell **MUST** show the change as
`old → new` via `.cell-type` gaining `.is-changed` and a `span.seg-type-was` holding the old code.

**`aria`:** `#segment-table` gets `aria-rowcount`; `.seg-check` gets an `aria-label` of
`"Select {name} #{seq}"`; the tbody is `aria-live="off"` (updates are user-initiated and noisy).

### 8.4 `#map-panel` — linked SVG map and inspector

```html
<div id="map-toolbar">
  <button id="map-zoom-in">+</button>
  <button id="map-zoom-out">−</button>
  <button id="map-zoom-reset">Fit</button>
  <label><input type="checkbox" id="map-dim-filtered" checked> Dim filtered-out</label>
  <span id="map-hover-label"></span>
</div>
<svg id="map" viewBox="0 0 1000 1549" preserveAspectRatio="xMidYMid meet" role="img"
     aria-label="Newcastle thoroughfare map coloured by Type">
  <g id="map-viewport">
    <g id="map-lines"></g>
    <g id="map-halo"></g>
    <g id="map-markers"></g>
  </g>
</svg>
<div id="map-legend"></div>
<section id="detail-panel"> … §8.4.2 … </section>
```

#### 8.4.1 Map elements

- `#map` `viewBox` is set by `app.js` from `data.view` (`0 0 {vbw} {vbh}`); the HTML author's
  literal is a placeholder only.
- `#map-lines` holds one `path.map-seg` per segment, created with
  `document.createElementNS("http://www.w3.org/2000/svg", "path")`, carrying:
  `d` = `segment.path`, `data-id`, `data-road-key`, `data-type`,
  `stroke` = type colour, `fill="none"`, `stroke-linecap="round"`, `stroke-linejoin="round"`,
  `vector-effect="non-scaling-stroke"` (so stroke width is stable under zoom).
- Base stroke widths (CSS px, because of `non-scaling-stroke`): `1.6` normal, `2.6` `.is-hovered`,
  `3.4` `.is-selected`, `3.4` `.is-pending` (with `stroke-dasharray: 5 3`).
- State classes on `path.map-seg` mirror §8.3.4 exactly: `.is-selected`, `.is-hovered`,
  `.is-pending`, `.is-filtered-out` (opacity `0.12` when `#map-dim-filtered` is checked),
  `.is-excluded` (dashed, `--danger`).
- `#map-halo` holds a wider, low-opacity duplicate path for the selection so it reads over
  neighbours; `#map-markers` holds `circle.map-mid[data-id]` at `segment.mid` for the focused
  segment only.
- Each `path.map-seg` **MUST** carry a `<title>` child: `"{name} #{seq} — {TYPE} — {length} ft"`.
- Zoom: `#map-viewport` gets `transform="translate(tx ty) scale(k)"`, `k ∈ [1, 12]`. Wheel zooms
  about the pointer; drag pans. `#map-zoom-reset` restores `k = 1, tx = ty = 0`.

**Linkage (both directions, MUST):**

| event | effect |
|---|---|
| pointer over `tr.segment-row` | matching `path.map-seg` gains `.is-hovered`; `#map-hover-label` shows the title text |
| pointer over `path.map-seg` | matching `tr.segment-row` gains `.is-hovered` and is scrolled into view (`block: "nearest"`, only if not already visible) |
| click `path.map-seg` | same as clicking that row's `.seg-check` label area: plain = select only it; `shift` = range from anchor; `meta/ctrl` = toggle |
| selection change | both surfaces re-apply `.is-selected` in one pass |

Hover updates **MUST** be throttled with `requestAnimationFrame` and must mutate only the two
affected nodes (no full re-render).

#### 8.4.2 `#detail-panel` — the "why is this suspicious" inspector

Shows the **focused** segment (§9.3). `hidden` when nothing is focused.

| id | shows |
|---|---|
| `#detail-name` | "Main Street #3" |
| `#detail-id` | `main-street-3` |
| `#detail-termini` | "Mills Road → River Road" |
| `#detail-length` | "1,204 ft (0.23 mi)" |
| `#detail-type` | current type as swatch + `S1 — Main Street` |
| `#detail-source` | `override` / `auto`, plus "auto-classified as R1" only when `auto_type` is non-null |
| `#detail-ownership` | ownership or "not recorded" |
| `#detail-districts` | comma list |
| `#detail-maindot` | class or "—" |
| `#detail-note` | the existing override note, verbatim, in a `<blockquote>`; "no note" if absent |
| `#detail-row-ft` | `input[type=number]` — stages a `row_ft` change |
| `#detail-traveled-ft` | `input[type=number]` — stages a `traveled_ft` change |
| `#detail-nonconformity` | `input[type=text]` — stages a `nonconformity` change |
| `#detail-neighbors` | the sibling segments of the same road as clickable `button.detail-neighbor[data-id]`, each with its type pill — this is what exposes "this stub is typed like the highway it hangs off" |
| `#detail-raw` | `<pre>` of the verbatim override entry JSON; `hidden` if none |
| `#detail-note-btn` | opens `#note-dialog` for this segment |
| `#detail-exclude-btn` | toggles exclusion for this segment |

### 8.5 `#pending-panel` — staged changes and save controls

| id | element | purpose |
|---|---|---|
| `#pending-header` | `div` | header row |
| `#pending-count` | `span` | "7 pending changes" |
| `#pending-clear` | `button` | reverts **all** pending changes; **MUST** confirm |
| `#pending-list` | `ul` | clones of `#tpl-pending-item` |
| `#pending-empty` | `p` | "No unsaved changes." shown when the list is empty |
| `#apply-inventory` | `input[type=checkbox]` | **`checked` by default**; label: "Also update the rendered inventory (`source/exhibits/street-types/inventory.json`) so the exhibits pick these up without a GIS re-run" |
| `#validate-btn` | `button` | `POST /api/validate`; renders result into `#save-status` |
| `#save-btn` | `button` | `POST /api/save`; disabled when pending is 0 or a save is in flight |
| `#save-status` | `div` | `data-state` ∈ `idle \| validating \| saving \| ok \| warn \| error` |
| `#save-report` | `div` | after a save: counts written, backup path, skipped/removed lists |
| `#last-save` | `span` | "Last saved 18:07:44 — backup …bak-20260820-180744" |

**Pending item** (from `#tpl-pending-item`), root `li.pending-item[data-id]`:

```html
<li class="pending-item" data-id="timber-lane-1">
  <span class="pending-road">Timber Lane #1</span>
  <code class="pending-id">timber-lane-1</code>
  <ul class="pending-fields">
    <li class="pending-field" data-field="type">
      <span class="pending-field-name">Type</span>
      <span class="pending-from">R4</span>
      <span class="pending-arrow">→</span>
      <span class="pending-to">R2</span>
    </li>
  </ul>
  <p class="pending-note"></p>
  <span class="pending-note-missing" hidden>no note</span>
  <button class="pending-note-edit" title="Edit note">✎</button>
  <button class="pending-revert" title="Revert this change">⨯</button>
  <button class="pending-locate" title="Show on map">◎</button>
</li>
```

`.pending-revert` reverts **that one segment's** whole pending entry. `li.pending-item` gains
`.is-delete` for a `delete: true` change and `.is-exclude` for an exclusion.

### 8.6 `#note-dialog`

| id | purpose |
|---|---|
| `#note-dialog-title` | "Note for this change" / "Note for 12 changes" |
| `#note-dialog-summary` | one line describing the action, e.g. "Main Street → S1 (12 segments)" |
| `#note-dialog-targets` | `ul` of affected ids, capped at 20 with "+N more" |
| `#note-existing` | `<blockquote>` of the existing note when exactly one target has one; `hidden` otherwise. Label: "Existing note (will be replaced):" |
| `#note-input` | `textarea`, pre-filled with §12's generated default, `maxlength="4000"`, autofocused, text selected |
| `#note-suggest-btn` | restores the generated default |
| `#note-keep-btn` | "Keep existing note" — stages the change with `note` omitted (§5.5 preservation); `disabled` when no target has a note |
| `#note-cancel` | cancels the whole staging action (nothing is staged) |
| `#note-confirm` | stages the change(s) with the textarea text |
| `#pref-auto-note` | `input[type=checkbox]` inside the dialog: "Use the suggested note without asking (editable later)". Persisted in `localStorage` under `nczc.editor.autoNote`. When set, `openNoteDialog` resolves immediately with the generated default and no dialog is shown. |

`#note-dialog` **MUST** use the native `<dialog>` `showModal()`; `Escape` cancels; `#note-confirm`
is the default (`Enter` with `Ctrl`/`Cmd`, since the field is a textarea).

### 8.7 `#confirm-dialog`

Generic confirm. `#confirm-title`, `#confirm-message`, `#confirm-detail` (a `ul` of ids),
`#confirm-cancel`, `#confirm-ok`. `#confirm-ok` gets `.is-danger` when
`opts.danger` is true. Used for: exclusions, `#pending-clear`, `#reload-btn` with pending work, and
override deletion.

Exclusion confirm copy **MUST** state the consequence explicitly when `#apply-inventory` is checked:
"This removes the segment from the rendered inventory. Restoring it requires a GIS pipeline re-run or
the backup file."

### 8.8 `#help-dialog`

Static content authored in `index.html`: the 10 types with colours, the keyboard map (§10), a plain
explanation of what Save writes and where the backups go, and the "always wins over
auto-classification" semantics. `#help-close` closes it.

### 8.9 Templates (all in `index.html`, all `<template>`)

`#tpl-road-row` · `#tpl-segment-row` · `#tpl-pending-item` · `#tpl-type-chip` ·
`#tpl-legend-item` · `#tpl-detail-neighbor` · `#tpl-toast` · `#tpl-orphan-item`

`#tpl-legend-item` → `div.legend-item[data-type]` containing `.legend-swatch`, `.legend-code`,
`.legend-name`, `.legend-count`. The legend **MUST** render only types with `count > 0` (matching
the published exhibits' convention that legends show only types present) — currently 9 of 10
(`S5` Alley is absent). Clicking a legend item sets `#filter-type`.

`#tpl-orphan-item` → `li.orphan-item[data-id]` with `.orphan-id`, `.orphan-reason`, `.orphan-note`,
rendered into `#orphan-list` (inside `#pending-panel`, under an `#orphan-section` that is `hidden`
when empty).

`#tpl-toast` → `div.toast[data-level="info|warn|error"]` with `.toast-message` and `.toast-close`,
appended to `#toast-container`, auto-dismissed after 6 s (errors are sticky).

---

## 9. Client state model

One module-scoped object. No framework, no global mutation from event handlers other than through
the listed mutators.

```js
const state = {
  // ---- server data (replaced wholesale by loadData(), never mutated in place) ----
  loaded: false,
  contract: "1.0.0",
  baseToken: "130d46a2c3534dec",
  inventoryToken: "a1b2c3d4e5f60718",
  meta: { note, banner, crs, town },
  types: [ {code, name, family, color} ],       // §3.1 order
  typeByCode: Map<string, Type>,
  ownershipCategories: [ … ],
  districts: [ … ],
  maindotClasses: [ … ],
  view: { vbw, vbh, pad, minx, miny, maxx, maxy, scale, offx, offy, units_per_ft },
  segments: [ Segment ],                        // file order, §5.3.1 verbatim
  segById: Map<string, Segment>,
  roads: [ Road ],                              // §5.3 `roads`, sorted by name
  roadByKey: Map<string, Road>,
  orphans: [ {id, entry, reason} ],
  counts: { … },                                // as loaded; NOT live
  warnings: [ … ],

  // ---- pending edits ----
  pending: Map<string, PendingChange>,           // keyed by segment id, insertion-ordered

  // ---- selection & focus ----
  selection: Set<string>,                        // segment ids
  anchorId: null,                                // shift-range anchor
  focusId: null,                                 // keyboard cursor + #detail-panel subject

  // ---- view state ----
  filters: { search: "", type: "", family: "", district: "", ownership: "",
             override: "", pendingOnly: false },
  sort: { key: "name", dir: "asc" },
  collapsedRoads: Set<string>,
  zoom: { k: 1, tx: 0, ty: 0 },
  dimFiltered: true,
  hoverId: null,

  // ---- io ----
  saving: false,
  lastSave: null,          // the §5.5 response object
  autoNote: false,         // localStorage-backed
};
```

### 9.1 `PendingChange`

```js
{
  id: "timber-lane-1",
  name: "Timber Lane",
  seq: 1,
  kind: "set" | "delete",
  fields: {                       // only fields the user actually changed
    type:           { from: "R4", to: "R2" },
    ownership:      { from: null, to: "Private Road" },
    row_ft:         { from: null, to: 40 },
    traveled_ft:    { from: null, to: 18 },
    nonconformity:  { from: null, to: "ROW 33 ft, narrower than Type" },
    exclude:        { from: false, to: true },
  },
  note: "Board correction: R4 -> R2.",   // string, or null = "preserve existing"
  noteFrom: "…existing note or null…",   // display only
  ts: 1755712064123,
}
```

`from` values are read from the **loaded** segment/override, never from another pending change —
so a `from` is always the on-disk truth and reverting is exact.

### 9.2 Pending mutators (the only functions permitted to write `state.pending`)

| function | behaviour |
|---|---|
| `stageField(ids, field, value, note)` | For each id: compute `from`; if `value === from`, **remove** that field from the pending entry (a change back to the original is not a change); else set it. If a pending entry ends with no fields and `note === null`, delete the entry entirely. |
| `stageDelete(id)` | sets `kind: "delete"` (override removal) |
| `stageNote(ids, note)` | sets `note` only |
| `revert(id)` | `pending.delete(id)` |
| `revertAll()` | `pending.clear()` |
| `clearAfterSave()` | `pending.clear()`, then re-`loadData()` |

**Effective value** helper, used by every renderer:
`effective(seg, field)` = `pending.get(seg.id)?.fields[field]?.to ?? seg[field]`.
The table, the map, the summary bar and the legend all render the **effective** value, so the UI
always shows the world as it will be after Save.

### 9.3 Selection and focus

- `selection` is a `Set` of ids. `focusId` is a single id and is **independent** of selection.
- Plain click on a row (not on a control) → `selection = {id}`, `anchorId = id`, `focusId = id`.
- `Shift`+click → `selection = range(anchorId, id)` over the **currently visible, currently sorted**
  row order; `anchorId` unchanged.
- `Meta`/`Ctrl`+click → toggle `id` in `selection`; `anchorId = id`.
- Checkbox click → toggle only; `anchorId = id`.
- `.road-check` → add/remove all visible segments of that road.
- `#select-all` → add/remove all visible segments.
- Applying a type does **not** clear the selection (bulk work continues); it **does** set
  `focusId` to the first affected id.
- `state.selection` **MUST** be pruned to visible-or-not? **No** — selection persists across filter
  changes. `#selection-count` reports the full selection; a bulk apply acts on the **full**
  selection, and the bulk bar **MUST** say "6 selected (2 hidden by filters)" when they differ.

### 9.4 Rendering discipline

- `renderAll()` on load/save/sort/filter change: rebuilds `#segment-tbody` from a document fragment.
- `renderRowState(id)` / `renderMapState(id)` on selection/hover/pending change: mutates only the
  classes and the type cell of the affected nodes. A 214-row full re-render on every hover is a
  contract violation.
- `renderSummary()` recomputes `by_type` from **effective** values, so the chips move as the user
  works. `#summary-pending` = `state.pending.size`.
- `renderPending()` rebuilds `#pending-list` wholesale (it is short).
- Number formatting: lengths use `toLocaleString("en-US")` with 0 decimals and a `" ft"` suffix;
  miles to 2 dp.

### 9.5 Save flow

1. `#save-btn` → build the payload: `changes = [...state.pending.values()].map(toChange)` where
   `toChange` emits `{id, set: {field: to, …, note}}` or `{id, delete: true}`.
   `note: null` is **omitted** from `set` when the user chose "keep existing", and sent as `""`
   never.
2. `POST /api/save` with `base_token: state.baseToken` and
   `apply_to_inventory: #apply-inventory.checked`.
3. `200 ok` → render `#save-report`, toast, `clearAfterSave()` (which re-`GET`s and so refreshes
   `baseToken`, counts and drift warnings).
4. `409 stale_base` → `#blocking-overlay` with `#blocking-message` explaining the external change;
   the only exit is `#reload-btn` (which will warn about losing pending work) or dismissing to keep
   working. **Never auto-reload.**
5. `400 validation_failed` → map `error.details[].index` back to the pending item and mark
   `li.pending-item.is-invalid` with a `.pending-error` message; nothing is cleared.
6. Network failure → `#conn-status.is-error`, sticky error toast, pending untouched.

`beforeunload` **MUST** be guarded while `state.pending.size > 0`.

---

## 10. Keyboard contract

Shortcuts are **suppressed** when the event target is an `input`, `textarea`, `select`, or
`[contenteditable]`, or when any `<dialog>` is open — except `Escape` and `Meta/Ctrl+S`.

| keys | action |
|---|---|
| `/` or `Meta/Ctrl+K` | focus and select `#filter-search` |
| `1`…`5` | apply `S1`…`S5` to the selection |
| `6`,`7`,`8`,`9`,`0` | apply `R1`…`R5` to the selection |
| `s` then `1`…`5` | apply `S1`…`S5` (chord; 1500 ms window, shown in `#shortcut-hint`) |
| `r` then `1`…`5` | apply `R1`…`R5` (chord) |
| `↓` / `j` | move `focusId` to the next visible segment row |
| `↑` / `k` | move `focusId` to the previous visible segment row |
| `Shift`+`↓`/`↑` | extend the selection from `anchorId` |
| `Space` | toggle selection of `focusId` |
| `a` | select all visible (same as `#select-all`) |
| `Escape` | close dialog · else clear selection · else blur search |
| `x` | toggle exclusion on the selection (routes through `#confirm-dialog`) |
| `n` | open `#note-dialog` for the selection |
| `Meta/Ctrl+S` | `#save-btn` (`preventDefault`) |
| `Meta/Ctrl+Z` | revert the most recently staged pending change |
| `?` | open `#help-dialog` |

Applying a type with an empty selection is a no-op plus an info toast
("Select segments first — click a row, a road checkbox, or a line on the map").
`#shortcut-hint` shows the pending chord prefix (e.g. `S…`) and is `hidden` otherwise.

Focus management: `.is-focused` row gets `tabindex="-1"` and `.focus()`; the table itself is
reachable by `Tab`. Every icon button carries a `title` **and** an `aria-label`.

---

## 11. Geometry maths

### 11.1 Projection: EPSG:26919 → viewBox

`inventory.json` geometry is **UTM Zone 19N metres** (`_meta.crs = "EPSG:26919"`) — a planar,
metric, equal-scale coordinate system, so a single linear transform is a correct projection for
display. This is exactly the transform `source/street-type-map.typ` uses, so the tool's map and the
published Exhibit 3.2 agree.

```
bbox over ALL segments (including geometry of segments hidden by filters):
  minx, miny, maxx, maxy
  spanx = max(maxx - minx, 1e-9)
  spany = max(maxy - miny, 1e-9)

VBW = 1000
PAD = 16
VBH = round((VBW - 2*PAD) * spany / spanx + 2*PAD)

scale = min((VBW - 2*PAD) / spanx, (VBH - 2*PAD) / spany)
offx  = PAD + ((VBW - 2*PAD) - spanx * scale) / 2
offy  = PAD + ((VBH - 2*PAD) - spany * scale) / 2

project(x, y) -> [ offx + (x - minx) * scale,
                   offy + (maxy - y) * scale ]      # y flipped: SVG y grows downward
```

Concrete values for the present data (a useful implementation check):

```
minx = 449758.99   maxx = 458820.65   spanx =  9061.66
miny = 4870123.17  maxy = 4884320.17  spany = 14197.00
VBW  = 1000   VBH = 1549   PAD = 16
scale = 0.1068240   offx = 16.000   offy = 16.212
project(456979.49, 4875907.50) -> [787.32, 914.88]
1 viewBox unit ≈ 9.36 m ≈ 30.71 ft
```

`units_per_ft = scale / 3.280839895013123` is returned in `view` so the client can draw a scale bar.

Path string: `"M" + x0 + " " + y0 + "L" + x1 + " " + y1 + …`, each coordinate
`round(v, 2)` rendered without trailing zeros. Degenerate geometry (`< 2` points) yields `""` and the
segment gets no `path.map-seg`; it **MUST** still appear in the table.

### 11.2 Length in feet

```
METRES_TO_FEET = 3.280839895013123      # exact: 1 m = 1/0.3048 ft

length_m  = Σ hypot(x[i+1] - x[i], y[i+1] - y[i])   over consecutive vertices
length_ft = length_m * METRES_TO_FEET
```

Reported as `round(length_ft, 1)`; displayed rounded to the nearest foot with thousands separators.
Verified against values already quoted in the project's Board memo: `eden-lane-1` = **277.1 ft**
(memo: 277 ft), `camp-road-1` = **303.1 ft** (memo: 303 ft). Whole-network total ≈ **77.28 mi**;
shortest segment 56.0 ft, longest 17,812.6 ft.

Road length = Σ of its segments' `length_ft` (segments are non-overlapping).
Selection length = Σ over the selection.

*Note (do not "fix"):* these are UTM **grid** distances; ground distance differs by the UTM scale
factor (≈ 0.9996 at the central meridian, ≈ 1.0000 near Newcastle's easting). The project already
quotes grid feet, so grid feet is the contract.

### 11.3 Midpoint

`mid` is the point at 50 % of cumulative polyline length, linearly interpolated within the
containing span, then projected — **not** the middle vertex (segments have 2–605 vertices and the
vertex distribution is not uniform).

---

## 12. Auto-generated note text

`generateNote(action)` produces the `#note-input` default. ASCII `->` (matching every existing note
in the file), one sentence, ends with a period. Never contains a file path, an id list longer than
3, or a mention of this tool.

| case | template | example |
|---|---|---|
| 1 segment, type change | `Board correction: {OLD} -> {NEW}.` | `Board correction: R4 -> R2.` |
| 1 segment, type change, no prior type | `Board classification: {NEW}.` | `Board classification: R2.` |
| whole road (all N segments), one prior type | `{Road}: {NEW} for its full length ({N} segments); corrects {OLD}.` | `Main Street: S1 for its full length (12 segments); corrects R1.` |
| whole road, mixed prior types | `{Road}: {NEW} for its full length ({N} segments); corrects {OLD1}/{OLD2}.` | `Mills Road: S3 for its full length (7 segments); corrects R1/R2.` |
| N>1, same road, subset | `{Road} ({N} segments): {NEW}, corrects {OLDLIST}.` | `Timber Lane (2 segments): R2, corrects R4.` |
| N>1, mixed roads | `Board correction: {NEW} applied to {N} segments (was {OLDLIST}).` | `Board correction: R2 applied to 6 segments (was R4/S3).` |
| ownership change | `Ownership Category recorded as {NEW}{, was {OLD} if present}.` | `Ownership Category recorded as Town Way.` |
| exclusion | `Not a thoroughfare: excluded from the Inventory.` | — |
| unsetting a type | `Type override removed; reverts to the pipeline classification on the next re-run.` | — |

`{OLDLIST}` = distinct prior values in §3.1 order, joined `/`; `—` when all are empty.
`{Road}` = the segment `name`. Where a change touches several fields, the templates are joined with
a single space in field order `type, ownership, row_ft, traveled_ft, nonconformity, exclude`.

The generated text is a **default only** — `#note-input` is always editable, and `#note-keep-btn`
preserves whatever is already on disk.

---

## 13. Acceptance checks

An implementation is contract-complete when all of the following pass.

**Server**

1. `python3 build/inventory-editor/serve.py --selftest` exits 0, asserting that
   `serialize_overrides(json.load(overrides.json))` is **byte-identical** to the file on disk, and
   that `json.dumps(inventory, indent=1)` is byte-identical to `inventory.json`.
2. `POST /api/save` with `changes: []` writes nothing, creates no backup, returns
   `overrides.written: false, reason: "no_changes"`.
3. A save that changes one type leaves the other 47 entries **byte-identical** (`git diff` shows
   exactly one changed line, or two with an insertion).
4. `kavanagh-road-1` and `woods-island-road-1` are byte-identical after any save that does not
   target them; `station-road-3` keeps `"exclude": true` and its note.
5. `POST /api/save` with a stale `base_token` returns `409` and leaves both files untouched
   (compare sha256 before/after).
6. An invalid `type` anywhere in a 50-change payload writes **nothing** and returns all errors.
7. `note: ""` on an entry with an existing note leaves that note intact and emits `note_preserved`.
8. `GET /../../CLAUDE.md`, `GET /fonts/../../../etc/passwd`, and a `Host: evil.test` request are all
   rejected without disclosing paths.
9. After 12 saves, exactly 10 `overrides.json.bak-*` files remain.
10. Killing the process mid-save never leaves a truncated `overrides.json` (the `os.replace` is
    atomic; only a stray `.tmp-*` may remain).

**Client**

11. Setting `#filter-search` to `main street`, checking the road checkbox, and pressing `1` stages
    12 pending changes to `S1` with one shared note.
12. Hovering a map line highlights its table row and vice versa; clicking a line selects that
    segment.
13. Reverting every pending change restores `#save-btn` to disabled and `#summary-types` to the
    loaded counts.
14. With `#apply-inventory` checked, a save reports both files written and both backup paths.
15. The page loads and is fully usable with `style/fonts/` renamed away (system font fallback).
16. `#help-dialog`, `#note-dialog` and `#confirm-dialog` are all reachable and dismissible by
    keyboard alone.
17. No network request leaves `127.0.0.1` (check DevTools with the machine offline).

---

## 14. Amendments after the adversarial review

The implementation was reviewed for data safety, correctness and fitness-for-purpose before
release. The following behaviours **supersede** the sections named. None changes the wire format,
so `contract` stays at `1.0.0`.

**Server**

| § | amendment |
|---|---|
| §7 write order | A second staleness check runs on the live bytes of each file immediately before its backup + `os.replace` (`assert_still`). The `base_token` check at the top of `do_save` is stale by write time, and `SAVE_LOCK` only serialises *this tool's* saves — an external writer (a pipeline re-run) could land inside the window and be silently overwritten. Now returns `409 stale_base` with `details[0].stage = "pre_write_verify"`. A failure on the inventory side is reported in `inventory.error` and never rolls back the already-written overrides. |
| §6 text validation | `_bad_control` also rejects lone UTF-16 surrogates (U+D800–DFFF). With `ensure_ascii=True` a lone surrogate is stored as a `\udXXX` escape that re-parses but is not valid text for any other reader of the durable record. |
| §7.4 / save report | `apply_plan` returns `notes_replaced: [{id, was, now}]` and raises a `note_replaced` warning. Echoed in `overrides.notes_replaced` on both `/api/save` and `/api/validate`. A hand-written note is the one loss a backup does not make obvious, so it is reported by name. |

**Client**

| § | amendment |
|---|---|
| §9.2 no-op filter | Would-change tests compare against `currentValue()` (staged value, including an explicit `null`), **not** `baseValue()`. Comparing against disk meant a second edit over an already-staged segment was dropped while the earlier, wrong value stayed staged and was written. |
| §9.2 staging | An action that returns every named field to its on-disk value **un-stages** the pending edit instead of prompting for a note. This is the only way to take an edit back through the value controls. |
| §8.7 note dialog | The "use the suggested note without asking" preference is honoured **only when no target carries a note** (on disk or staged). Otherwise the dialog opens regardless, says why, makes **Keep existing note** the primary focused button, and relabels the other to "Replace the note". |
| §8.5 pending item | A pending item whose note replaces an existing one shows the old wording struck through (`.pending-note-replaced`). |
| §8.4.2 inspector | `#detail-note` renders the staged note when there is one, and names what it replaces in its `title`. |
| §8.3.3 road row | The road Type select acts on the **whole** road; the road checkbox acts on the **visible** part. Both scopes are now stated in the row text and the select's tooltip, and the note dialog's summary names the hidden count. |
| §8.4.1 map | `#map-halo` is painted **before** `#map-lines` (it is an under-glow, not a tint); a `#map-hits` layer of transparent 10 px non-scaling strokes sits between them so hairline segments are clickable while a direct hit on the visible line still wins. `.map-seg` uses `vector-effect: non-scaling-stroke`. Drag-pan translates by `Δp`, not `Δp · k`. `clampK` caps at **64**. Hover draws a halo. `#map-expand` toggles the previously unreachable `.is-stacked` layout. |
| §8.2 filters | New `override` value `odd` — "differs from its road": on a road of 3+ segments where one Type holds a strict majority, the segments that disagree. Row class `.is-odd-type`. |
| §8.1 summary | Counts account for staged **deletes** (a delete removes the entry, Type and all) and for open items that gain a value. |
| §9 model | `state.pending` is mirrored into `sessionStorage` under `nczc.editor.pending` and restored on load only when `base_token` still matches; otherwise discarded with an explicit message. "Revert all" offers an Undo. |
| §9.3 selection | Clearing filters no longer clears the selection. A selection reaching outside the current filters shows `#selection-hidden-warn`, which drops the hidden ids. A bulk exclude names any hidden or note-only OPEN ITEM targets in its confirm dialog. |
| misc | A note cannot be staged against an entry with a pending delete (it would be discarded); sortable `th`s respond to Enter/Space; the Source badge renders sentence-case so "Override" cannot clip to "OVERRI"; generated notes use correct plurals ("1 segment"). |

New reserved DOM ids: `#map-hits` `#map-expand` `#selection-hidden-warn` `#pref-auto-note-override`,
plus `.pending-note-replaced` `.seg-odd-flag` `.map-hit` `.map-halo-hover` `.toast-action` and row
classes `.is-odd-type` `.is-note-replaced` `.is-partly-filtered`.

---

*End of contract. Changes to this file require a version bump in `contract` and a matching bump in
`serve.py`'s `/api/health`; the client refuses to save against a mismatched major version.*
