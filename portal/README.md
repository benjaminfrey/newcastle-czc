# Applicant Portal

The public web app where applicants find out which permit they need and apply for it.
Design: `specs/2026-10-14-applicant-portal-design.md`. Plans: `plans/2026-10-14-applicant-portal-*.md`.

## Development

Development runs on a VM, not the Mac. The Mac holds the git checkout and the editor;
`portal/vm.sh` copies `portal/` to the VM (`~/newcastle-czc/portal/`) and runs commands there.
The VM is `ben@192.168.1.6` unless `PORTAL_DEV_VM` says otherwise. Everything on the VM listens
on 127.0.0.1 only; `portal/vm.sh tunnel` forwards the dev ports to the Mac.

Start the database, the mail catcher (Mailpit, web view at http://127.0.0.1:8025 through the tunnel),
the upload store (RustFS, on 9000) and the virus scanner (ClamAV, on 3310; its first start downloads
signatures for a few minutes):

    portal/vm.sh run 'sudo docker compose -f portal/deploy/compose.dev.yml up -d --wait'

API, first time:

    portal/vm.sh run 'cd portal/api && python3.14 -m venv .venv && .venv/bin/pip install -r requirements-dev.txt'

API, every time:

    portal/vm.sh run 'cd portal/api && .venv/bin/pytest'
    portal/vm.sh run 'cd portal/api && .venv/bin/python -m alembic upgrade head'
    portal/vm.sh run 'cd portal/api && PORTAL_COOKIE_SECURE=false PORTAL_ALLOW_STALE_PARCELS=true PORTAL_ALLOW_DRAFT_RULES=true .venv/bin/uvicorn portal_api.main:create_app --factory --port 8000'

Web app:

    portal/vm.sh run 'cd portal/web && npm ci && npm test'
    portal/vm.sh run 'cd portal/web && npm run dev'      # then http://localhost:5173 through the tunnel

In another terminal on the Mac, while working in a browser:

    portal/vm.sh tunnel

## The portal on the local network

The production-shaped portal (Caddy, API, Postgres) also runs on the VM for every device on the
local network, so it can be tried on a phone: **https://192.168.1.6**. It is never port-forwarded
or put on the public internet during development. Rebuild it after changes with:

    portal/vm.sh lan

Its sign-in emails land in a separate Mailpit at http://192.168.1.6:8026, which asks for a login:
the `MAILPIT_UI_AUTH` line in `~/newcastle-czc/portal/deploy/.env` on the VM. Browsers warn about
the certificate once per device (Caddy signs it locally); `portal/deploy/README.md` says how to
trust it instead.

## Property data (GIS)

The "Where is it?" page looks properties up in four layers loaded into PostGIS by
`python -m portal_api.gis` (run from `portal/api`, or inside the API container). Each load records
its source and date and replaces the previous one:

    .venv/bin/python -m portal_api.gis parcels --axisgis
    .venv/bin/python -m portal_api.gis addresses --e911
    .venv/bin/python -m portal_api.gis districts --file ../../data/street-types/districts.geojson \
        --ruleset ../../build/permit-review/rulesets/adopted-v1.0/districts.json --source-date 2026-06-01
    .venv/bin/python -m portal_api.gis streets --inventory ../../source/exhibits/street-types/inventory.json \
        --types ../../source/exhibits/cross-sections/types.json --source-date 2026-09-14

**Parcels come from the Town's AxisGIS** (CAI's tax-map viewer, `axisgis.com/NewcastleME`), which
the assessor keeps current. `--axisgis` reads the token the public viewer page gives every visitor
and asks the "Parcel - Poly" layer for outlines and map/lot numbers only — never owner (CAMA) data.
AxisGIS publishes no revision date, so the import records the fetch date (the chair's choice,
2026-10-15); re-run it to refresh. Lots drawn as several pieces are merged into one per map/lot.
On 2026-10-15: 1,571 pieces, 1,503 map/lots.

Maine GeoLibrary (`--geolibrary`) also has Newcastle's parcels, but all are dated April 1, 2012; the
stale-parcel guard refuses them in production. A file from the assessor or CAI loads with

    .venv/bin/python -m portal_api.gis parcels --file PATH --map-lot-field FIELD \
        --location-field FIELD --source "Town tax maps (CAI export)" --source-date YYYY-MM-DD

**The stale-parcel guard.** By default the API refuses parcel data more than three years old
(`PORTAL_PARCEL_MAX_AGE_DAYS`, default 1095): lookup answers 503 and the page asks applicants to
enter their map and lot themselves. Only development sets `PORTAL_ALLOW_STALE_PARCELS=true` — the
dev API command above and the LAN stack (`compose.lan.yml`). The base `compose.yml` never does.

**Lookup limits.** Search, point lookup and facts allow 60 requests a minute per address
(`PORTAL_LOOKUP_LIMIT_PER_MINUTE`); map tiles 1,200 (`PORTAL_TILE_LIMIT_PER_MINUTE`). The limits
live in the API process's memory, which is right for the one process the portal runs. The
production API writes no access log, so searches are not recorded; errors still are.

Districts come from a tracing of the District Map and are approximate. They are named from the
adopted ruleset's district pages, plus the Civic district (SD-Civic, Article 2 §5), which has no
district page; an area the adopted Code does not have would show as "staff will confirm". On a
Civic lot the page explains that only the Town builds there (spec P13). The basemap is
self-hosted: see `portal/basemap/README.md`.

## What a project needs (the rules, fees and clocks)

"Do I need a permit?" is gone (`specs/2026-10-25-applicant-portal-projects.md`): its rules now run
inside each project (`portal_api/forms/needs.py`), once per part and once per chosen use, and the
dashboard shows the result as permits, reviews, fees and clocks. The rules come from data in
`portal/api/portal_api/forms/definitions/`:
`applications.yaml` (what each application is, who reviews it, the Code's time limits),
`rules.yaml` (when each applies, in the condition language of `forms/expr.py`, mirrored in
`web/src/forms/expr.ts`), `use-groups.yaml` (plain groups and examples for the 63 uses) and
`fees.yaml` (the Town's Planning Fee Schedule as of 2025.08.25, line for line, with which fee line
each review falls under; approved by the chair on 2026-10-25). Each application's clocks carry a
plain sentence (`clock_plain` in `applications.yaml`, each with its own approval); clocks start at
the staff lock, and after it each shows its due date. Every
entry cites the Code section it rests on, checked against the pinned adopted ruleset
(`portal_api/rulesets/adopted-v1.0/`, a SHA-verified copy of the Board app's ruleset).

**Drafts and approval.** The chair approved every entry on 2026-10-20; the record is
`memos/2026-10-15-screener-rules-for-approval.md`. A new or changed entry starts as `status: draft`. While any entry
(or clock sentence) is a draft, production withholds a project's needs (`"needs": {"refused":
"not_approved"}`) and the uses list (`503 screener_not_approved`). Only development
sets `PORTAL_ALLOW_DRAFT_RULES=true` — the dev API command and the LAN stack. To approve an entry,
set `status: approved`, `approved_by` and `approved_on` in its YAML. The review sheet lists every
draft with the Code text it rests on:

    .venv/bin/python -m portal_api.forms review-sheet > ../../memos/<date>-screener-rules-for-approval.md

**Rolling to a newly adopted Code:** vendor the new ruleset folder next to `adopted-v1.0`, change
`PINNED_KEY` in `portal_api/ruleset.py`, and run the tests — every citation is re-checked, and the
819-cell scenario table re-compares the screener with the new use table.

## Projects

A person signs in first (Home's sign-in card), then starts a **project**: how to reach them (saved
once on the account, `PUT /api/me`), where the work is, and its **parts** — a new building, an
addition, renovation, site work, a use, a driveway, dividing land, something else
(`definitions/parts.yaml`: each part's tile, the form sections it asks and the rule inputs it sets).
The project pins the official forms its parts need (`project_form`), at the version current when each
first applied, and the API builds one form for the project from them (`forms/parts.py`), served with
the project (`GET /api/projects/{id}`). Questions no official form prints (the renovation's size,
parking spaces, lots after a division) live in `project-questions.v1.yaml`. "Type of project" prints
from the parts (`source: parts`). The project is sent as one unit (`POST …/submit`) and stays
editable until staff lock it; the lock (a test seam, `POST …/lock`, behind `PORTAL_ALLOW_TEST_LOCK`,
until Milestone 6) freezes it as a `submission` with its `review` rows.

## The forms

Each official form is a definition in `portal_api/forms/definitions/forms/`: the Cover Sheet
(`cover-sheet.v1.yaml`, part of every form) plus `use-permit.v1.yaml`, `small-project-plan.v1.yaml` and
`entrance-permit.v1.yaml`. A definition lists the official form's sections and fields; each field says
where its value comes from (a plain question, the property lookup, the account, another field, the
signature at submit, or staff) and, for a question, when it is asked (`show_if`, the screener's
condition language). The fields carry the Town's Planning Application packet; the Entrance / Driveway
form is new. `forms/answers.py` decides what applies, what is still missing and what prints;
`web/src/forms/applicability.ts` is its browser twin, and both are checked against
`web/src/forms/form-fixtures.json`.

**Tasks, cards and controls.** A definition also says how the application is asked: a few tasks
(its `steps`), each a short run of cards (`specs/2026-10-25-applicant-portal-task-list.md`, which
revises the redesign and wizard briefs):

- `steps` — the form's steps in order (the Cover Sheet's come first); a section or a field names its
  `step`, and a field's own wins. Every question must be on a step.
- `screens` on a section and `screen` on its fields — a card: questions asked together (deed book
  and page; a building's size; the four setbacks), declared once per repeat by any of its sections,
  all on one step. A card may carry its own `title` and `help` (its question, "How big is the
  building?") and an optional `layout`: `lot-diagram` (setbacks around a drawing of the lot) or
  `compass` (the front's direction, then the window shares, walls named from it). Every other
  question is a card of its own. Each question on a shared card has a `short` name ("Width").
- `ask_first` — a rank (1, 2, …): asked before the rest of its building or addition (its type, then
  whether it is only being renovated), without changing the printed form's order.
- `icon` on an option — an outline icon beside the tile's words (`portal_api/forms/icons.txt`, which
  the web's `controls/Icon.tsx` draws); a question's options have icons on all or none.
- `copies` — "Copy Building 1" brings this answer to the new building (`POST …/parts` with
  `copy_from`); unknowns copy, blanks don't.
- `control` — how a question is asked: `stepper`, `slider`, `switch`, `segmented`, `tiles`,
  `picker`, `chips`, `building-picker`, `street-picker` or `building-type`, each only for the
  question types it suits; `step_size` for sliders and steppers; `autocomplete` for the browser's
  autofill. In the wizard every single choice (switches included) is tiles that answer at a tap.
- `default` — a value set when the question first applies to a project (or part), saved as the form's
  (`set_by = form-default`).

The loader checks every one of these (unknown steps, screens, controls, layouts; a control on the
wrong type; defaults that would fail their own field's check), and the forms sheet prints them for
the chair.

**The window.** The web app is a window (`web/src/shell/AppShell.tsx`): Home, Project, Messages and
You in a sidebar on a desktop and a tab bar on a phone. A project's home is its dashboard
(`app/Dashboard.tsx`): the parcel, a row per part, the parts still to add, and beside them what it
needs (`app/NeedsPanel.tsx`), who is applying, and Check and send (`app/SendPane.tsx`). Each row is
a short run of contained cards
(`shell/Card.tsx`; `forms/tasks.ts`, `forms/screens.ts`, `app/WizardPane.tsx`): a header with the
task's name and a bar counting its cards, the question, and a footer with Back and Continue. A single
choice answers at a tap and moves on; typed answers have Continue (Return presses it). A task ends on
its check page (Change comes back to it); buildings and additions have their own list
(`app/ItemsPane.tsx`: add, Copy Building 1, delete) and each building its check page. Check and send
lists what is left first; Send asks before it sends. Answers save as they are given (`app/ProjectStore.tsx`); Continue
waits for the saves. Light and dark follow the device. The design system is recorded in
`web/DESIGN.md`; the approved comp is `specs/assets/2026-10-25-task-list-comp.html`.

**Approval.** Every entry starts as `status: draft`; production refuses a form with any draft in it
(`503 form_not_approved`), as for the screener. The record for the chair:

    .venv/bin/python -m portal_api.forms forms-sheet > ../../memos/<date>-application-forms-for-approval.md

**Versions.** A project keeps each form at the version it was pinned at; a new version is a new
file (`use-permit.v2.yaml`), never an edit to one in use.

**Records.** Answers and section notes are insert-only (a change appends a row); every change bumps
the project's revision, so a save from a tab that fell behind is refused (409) and the page offers
"Load the latest". After the lock every change is refused (409 `locked`). Events name fields, never values.

**Uploads.** PDF, JPEG, PNG and HEIC, decided by the file's first bytes; 25 MB each; 60 a person an
hour. Each is scanned by ClamAV before anything is stored; if the scanner can't be reached, the upload
is refused. Files live in an S3-compatible store that only the API reaches (RustFS on the VM: MinIO no
longer publishes images; S3 or R2 in production, via `S3_ENDPOINT`), and go back only to their owner,
streamed through the API. The store's credentials are `STORE_ACCESS_KEY` / `STORE_SECRET_KEY` in the
VM's `.env`. Tests use an in-memory store and a fake scanner; two integration tests run against the
real ones when `PORTAL_TEST_S3_ENDPOINT` and `PORTAL_TEST_CLAMD_HOST` are set (CI sets the first).

**Journeys (Playwright).** `web/e2e/` drives projects end to end (sign in, start, every part, send), at desktop and phone width,
with an accessibility check (axe; serious and critical findings fail) on every kind of page. They run
on the VM against the dev stack, not in CI (ClamAV's signature download is refused from CI runners):

    portal/vm.sh run 'cd portal/web && npx playwright install --with-deps chromium'   # once
    # dev API as above, plus PORTAL_S3_ACCESS_KEY=portal PORTAL_S3_SECRET_KEY=portal-dev-secret
    # and PORTAL_SIGNIN_LIMIT_PER_IP=100000 (every journey signs in from 127.0.0.1); npm run dev running
    portal/vm.sh run 'cd portal/web && PORTAL_E2E_URL=http://127.0.0.1:5173 PORTAL_E2E_MAILPIT=http://127.0.0.1:8025 npm run e2e'

