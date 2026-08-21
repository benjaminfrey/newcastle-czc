# Newcastle Permit Review

Local tool that drafts the Planning Board's *Findings of Fact & Conclusions of
Law* working paperwork. **This checkout implements Workflow 1 (W1): Phase 0**
(contract, schema, audit chain, offline self-test) **and Phase 1** (the
dimensional worksheet — district data, the use matrix, a house-style PDF).
No uploads, no OCR, no LLM, no PII, no referral tracking in this workflow.

The full rules this app must follow live in [`CONTRACT.md`](./CONTRACT.md).
Read that first if you're changing anything here — it is normative, this
README is not.

**The framing rule, restated:** this app produces *the working draft the
Board amends*, never a decision. It never states, implies, or stores that a
standard is met or not met. Honest blanks beat confident guesses.

## Requirements

- Python 3.14
- `pandoc` and `typst` on `PATH`, for PDF export (`brew install pandoc typst`
  on macOS). Everything else works without them; PDF rendering degrades with
  a clear `render_unavailable` error if either is missing.

## Setup

```bash
cd build/permit-review
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Running

```bash
python3 run.py                 # starts the server on http://127.0.0.1:8781/
python3 run.py --port 8900     # same, on a different port (host is always 127.0.0.1)
```

Open the URL it prints. Pick a district (and, optionally, a use) to see the
Required Review(s) table, the dimensional standards, the permitted-buildings
matrix, and the district's use/design standards panels. "Copy as Markdown"
copies a plain-text rendition of what's on screen. "Generate PDF…" opens a
small form (case label, meeting month, lots, notes) and renders a
house-style PDF into `data/exports/` — regeneration always happens from
inside the running app, never from a separate script.

## Self-test

```bash
python3 run.py --selftest
# or, matching CONTRACT.md §1 S6 exactly:
python -m app.main --selftest
```

Runs fully offline (no network, no server, no LLM, no PII) and prints one
`PASS` / `FAIL` / `SKIP` line per check, exiting `0` only if nothing failed.
A `SKIP` line means the check's dependency isn't available yet in this
checkout (a sibling module not yet built, or `pandoc`/`typst` not on `PATH`)
— it is never a silent pass. See `CONTRACT.md` §1 S6 for the full list of
required checks.

## Project status: modules this app imports but does not own

This task (the FastAPI app + worksheet page) is one slice of a larger,
parallel build. `app/main.py` imports the following by the exact names in
`CONTRACT.md`'s signature table, and **degrades gracefully with a clear
message — it never crashes — if one isn't present yet**:

| module | provides | if missing |
|---|---|---|
| `app.db` | `connect()`, `migrate()` | `/healthz` reports `db: "module_unavailable"`; the worksheet page and PDF export still work; audit logging is skipped with a printed warning |
| `app.audit` | `append_event()`, `verify_chain()` | same as above — the PDF still renders, just without an audit row |
| `app.dates` | `meeting_date()`, `draft_due()`, `next_meeting()` | tries `app.meetings` (a sibling module that implements the identical §3.4 rule under a different name) next, then falls back to a local copy of the same third-Thursday arithmetic |
| `app.rulesets` | `load_ruleset()`, `require_binding()` | falls back to reading `rulesets/<key>/*.json` directly (the fully-specified on-disk schema, §4) and to `manifest.json`'s own `binding` field for the gate |
| `render.worksheet` | `render_worksheet(payload, out_dir)` | `POST /api/worksheet/render` returns `500 render_unavailable` with a clear message; the worksheet page still displays |

Two more modules aren't named in the contract's signature table but exist
alongside it and are used opportunistically when present, each with the same
graceful-degradation pattern: `app.config` (canonical `APP_ROOT`/`HOST`/path
constants — falls back to computing the same values locally) and
`app.security` (`is_host_allowed()`/`is_origin_allowed()` for the §1 S4 guard,
plus `current_user()`/`ensure_synthetic_user()` so audit rows have an
`actor_user_id` that satisfies the `users` foreign key — falls back to an
inline equivalent of the same host/origin check, with `actor_user_id: NULL`
for audit rows).

`GET /healthz` also reports the availability of each of these under
`data.modules`, so you can see at a glance what's wired up.

`app/citation.py` (the citation renderer, CONTRACT.md §5) is fully
implemented here — it is not one of the deferred modules. Its four §5.5
golden strings are asserted both by an internal check
(`app.citation._golden_checks()`) and by `--selftest` check 7.

## Routes

Three endpoints, nothing else exposed (CONTRACT.md §6):

- `GET /healthz` — status, DB/pragma/migration state, which rulesets are on
  disk, which sibling modules are available.
- `GET /?district=<district_key>&use=<use_key>` — the dimensional worksheet
  page (both query params optional).
- `POST /api/worksheet/render` — validates a worksheet request, enforces the
  binding gate (a real, non-scratch render must cite the `adopted` ruleset),
  and renders a PDF into `data/exports/`.

Bound to `127.0.0.1` only, non-configurable (CONTRACT.md §1 S3). A
`Host`/`Origin`/`Referer` guard rejects anything else (§1 S4).

## Layout

```
app/
  main.py            # app factory, middleware, routes, --selftest
  citation.py         # THE ONLY citation renderer (CONTRACT.md §5)
  templates/           # Jinja2, server-rendered
  static/               # vanilla JS + CSS, no npm, no build step
run.py                  # entry point
requirements.txt
.env.example
data/                   # gitignored; created on first run
  exports/              # the ONLY PDF output directory
```

See `CONTRACT.md` §2 for the full intended layout, including the modules
this checkout does not own (`app/db.py`, `ruleset_build/`, `render/`, etc.).
