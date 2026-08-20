# Thoroughfare Type Editor

A local, single-user web tool for assigning the **Thoroughfare Type** (S1–S5, R1–R5)
to the road segments in the Article 3 §5 Inventory. It edits
`build/street-types/overrides.json` — the durable, version-controlled record of
human decisions that the GIS pipeline merges on every re-run.

It replaces hand-editing that JSON one entry at a time. The unit of thought here is
the **road**, not the segment: search "Main Street", set the whole road to S1, write
one note, save. 214 segments across 148 roads, and 130 of those roads are a single
segment.

Nothing on disk changes until you press **Save changes**.

---

## Running it

```sh
python3 build/inventory-editor/serve.py
```

Then open <http://localhost:8765>. The server opens a browser for you unless you
pass `--no-browser`; `--port N` moves it off 8765.

- **Python standard library only.** No venv, no `pip install`, no build step. This
  is deliberately independent of `build/street-types/.venv` (the geospatial stack),
  so the editor runs even when that venv has been reclaimed.
- **Fully offline.** No CDN, no external fonts, no analytics. Barlow is served from
  `style/fonts/` so the tool matches the Code's typography; without it the page
  falls back to the system sans and loses nothing but the typeface.
- **Bound to 127.0.0.1 only**, non-configurably. It also rejects requests carrying a
  foreign `Host` or `Origin` header, and serves nothing outside its own directory —
  no path traversal, no reading `serve.py` or repo files over HTTP.

Check the data files parse and round-trip without starting a server:

```sh
python3 build/inventory-editor/serve.py --selftest
```

Fifteen checks, including "re-serialising the untouched file reproduces it
byte-for-byte" and the two published segment lengths (`eden-lane-1` = 277.1 ft,
`camp-road-1` = 303.1 ft).

---

## What it writes

### 1. `build/street-types/overrides.json` — always

The durable record. **The pipeline merges this file on every re-run and it always
wins over auto-classification**, so it is the permanent written record of
Planning-Board and staff decisions — not a cache. That is why every entry carries a
note, and why the tool prompts for one on every change.

The file's house style is preserved exactly: two-space indent, `_README` first, one
entry per line, keys in `type · ownership · row_ft · traveled_ft · nonconformity ·
exclude · note` order, ids in natural sort (`main-street-2` before
`main-street-10`), `ensure_ascii`. A one-segment edit changes one line in `git diff`.

### 2. `source/exhibits/street-types/inventory.json` — optional, on by default

The rendered inventory that Exhibit 3.1 (the table) and Exhibit 3.2 (the map) build
from. Ticking **"Also update the rendered inventory"** copies the same values into
it, so a corrected Type shows up in the next PDF build without waiting for a full
GIS re-run. That is exactly what has been done by hand until now. Untick it if you
would rather let `run.sh` regenerate the file.

One asymmetry worth knowing: *removing* a Type or Ownership override propagates to
`overrides.json` but is **skipped** in `inventory.json`, with a warning in the save
report. Recovering the value the classifier would have produced needs the District
overlap fractions that live in the pipeline's work files, and the tool will not
invent a plausible number in a legal record. Re-run the pipeline to settle it.

---

## Safety guarantees

`overrides.json` holds irreplaceable hand-written decisions. The write path is built
to be boring:

1. **Validate the entire batch before touching disk.** One bad value rejects the
   whole save; the error is mapped back to the offending row in the pending list and
   nothing is written.
2. **Stale-write detection, checked twice.** The page carries a hash of the file it
   loaded. If the file changed underneath (a pipeline run, another editor, a
   `git checkout`), the save is refused with a 409, your pending changes survive, and
   you choose whether to reload. The check runs again on the live bytes immediately
   before the backup and rename, so a writer that lands *during* a save is caught
   too rather than silently overwritten.
3. **Timestamped backup before every write** — `overrides.json.bak-YYYYMMDD-HHMMSS`
   beside the file. The ten most recent are kept and older ones pruned. Backups are
   git-ignored.
4. **Atomic write.** The new content goes to a temp file in the same directory,
   is `fsync`ed, then `os.replace`d over the original. A crash mid-write leaves the
   old file intact, never a truncated one.
5. **Round-trip assertion.** The serialised text is re-parsed and compared to the
   intended document — including `_README` — before anything is backed up or moved.
6. **A no-op save writes nothing.** Re-asserting values already on disk reports
   `no changes`, takes no backup, and leaves both files byte-identical.
7. **Notes are never silently destroyed.** An empty note preserves what is on disk.
   When any target already carries a note the dialog opens — *even with "use the
   suggested note without asking" ticked*, which is a convenience for entries that
   have nothing to lose, never consent to overwrite wording — and **Keep existing
   note** becomes the primary, focused button. A note that will be replaced is shown
   struck through in the pending list before you save, and the save report names
   every entry whose note was rewritten and points at the backup. Deleting an entry
   echoes the discarded note back in the save report.
8. **Setting a value back to what is on disk un-stages it.** Re-selecting the
   original Type clears the pending edit rather than reporting "already holds this
   value" and leaving the earlier edit in place. The same applies to un-excluding a
   segment you just excluded and to clearing a width field you just typed.
9. **Unknown keys survive.** A key the tool does not know about is carried through
   verbatim, in position.
10. **Pending work survives a reload.** Staged changes are mirrored into
    `sessionStorage` and restored on load — but only when `overrides.json` is still
    the file they were staged against; otherwise they are discarded and the page
    says so. "Revert all" offers an Undo.

Two entries are deliberately inert: `kavanagh-road-1` and `woods-island-road-1` are
**open items** — a note recording an unanswered question, with no value set. They
render as "—" and are never touched unless you edit them directly. `station-road-3`
is an **exclusion** (`"exclude": true`), an orphan E-911 fragment that is not a
thoroughfare; it has no segment in the inventory and appears under **Orphan
overrides** in the save panel.

---

## Where it sits in the GIS pipeline

```
01_fetch → 02_prepare → 03_join → 04_classify → 05_export
                                                    │
                              overrides.json ───────┤  merged here, always wins
                                                    ▼
                                    source/exhibits/street-types/inventory.json
                                                    │
                                    Exhibit 3.1 (table) · Exhibit 3.2 (map)
```

The classifier (`lib.classify_type`) implements the §5.D rubric and produces a Type
for every segment. `05_export` then applies `overrides.json` on top. So:

- **The editor never competes with the pipeline.** It writes only the override
  layer. Re-run `bash build/street-types/run.sh` whenever you like — every decision
  made here is re-applied.
- **The 100% map still comes from the contractor's district shapefile.** Drop it in,
  re-run from the join stage, re-promote `work/inventory.json`, rebuild. Overrides
  carry forward untouched.
- An override that no longer matches any segment (because the source data changed)
  is **preserved, not dropped** — it surfaces as an orphan rather than disappearing.

---

## Using it

**The table** groups segments under their road. A road row sets the Type for every
segment at once — **all** of it, including segments the current filter hides, which
the row says out loud ("6 of 9 segments shown · Type sets all 9"); the checkbox beside
it selects only what you can see. A segment row sets one. The left rail tells you where a value came
from: blue = an override on the durable record, amber = staged and unsaved, and a
"mixed" ring means the road carries more than one Type — usually worth a look.

**The map** draws all 214 segments coloured by Type. Hovering a row halos its line
and vice versa, so a stub typed like the highway it hangs off is visible rather than
deduced. Selecting on either side selects on both, and the ◎ button beside a road
both zooms to it *and* marks it. The town is ~16,800 ft across, so the village core
is tiny at full extent: **Expand** gives the map the full window width, and zoom goes
to 64×, which is what makes a 56 ft downtown segment clickable. Line weight does not
change with zoom.

**Filters** cover road name, id, terminus and note text (search), plus Type, family,
District, Ownership, and whether a segment has an override, is note-only, is
excluded, has drifted from the rendered inventory, or **differs from its road**.

That last one is the "what should I look at?" filter. On a road of three or more
segments where one Type holds a strict majority, the segments that disagree are
flagged with an amber ⚠ — which is the exact shape of the 42 Type corrections the
v0.22 audit made (Academy Hill all S3 bar one R2 trace artifact; Main Street all S1
bar the pieces still typed as River Road). It states a fact about the data — this
road is not internally consistent — never that a Type is wrong. On today's data it
finds seven, and all seven are *deliberate*: the two River Road pieces that are
really Main Street / Route 1B, the Town Way connector, and the four R4 Highway
Commercial stretches inside R5 Route 1.

**Pending changes** accumulate on the right as an explicit `old → new` list with a
count. Revert them one at a time or all at once. **Check** dry-runs the save against
the server without writing.

**Keyboard:** `/` focuses search; `1`–`5` apply S1–S5 to the selection and
`6 7 8 9 0` apply R1–R5; `s`/`r` then a digit does the same as a chord; `j`/`k` move
the row cursor, `Shift` extends; `x` toggles exclusion, `n` writes a note, `a`
selects all visible; `⌘S` saves, `⌘Z` reverts the last staged change;
`Shift+Delete` removes the focused segment's whole override entry. `?` opens the
full panel.

---

## Files

| file | role |
|---|---|
| `serve.py` | the whole server: static files, `/api/data`, `/api/validate`, `/api/save`, plus `--selftest` |
| `index.html` | the static shell and every `<template>` the client clones |
| `app.js` | client behaviour — one IIFE, no libraries |
| `styles.css` | house typography and colours, light and dark |
| `CONTRACT.md` | the normative spec the three files were written against |

The Type colours match Exhibit 3.2 exactly (S1 `#103E66` … R5 `#C2B777`), so the
screen and the printed map read the same.
