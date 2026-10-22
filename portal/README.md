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

## "Do I need a permit?" (the screener)

The screener's answers come from data in `portal/api/portal_api/forms/definitions/`:
`applications.yaml` (what each application is, who reviews it, the Code's time limits),
`rules.yaml` (when each applies, in the condition language of `forms/expr.py`, mirrored in
`web/src/forms/expr.ts`), and `use-groups.yaml` (plain groups and examples for the 63 uses). Every
entry cites the Code section it rests on, checked against the pinned adopted ruleset
(`portal_api/rulesets/adopted-v1.0/`, a SHA-verified copy of the Board app's ruleset).

**Drafts and approval.** The chair approved every entry on 2026-10-20; the record is
`memos/2026-10-15-screener-rules-for-approval.md`. A new or changed entry starts as `status: draft`. Production refuses any answer that
rests on a draft (`503 screener_not_approved`; the page says the tool isn't ready). Only development
sets `PORTAL_ALLOW_DRAFT_RULES=true` — the dev API command and the LAN stack. To approve an entry,
set `status: approved`, `approved_by` and `approved_on` in its YAML. The review sheet lists every
draft with the Code text it rests on:

    .venv/bin/python -m portal_api.forms review-sheet > ../../memos/<date>-screener-rules-for-approval.md

**Rolling to a newly adopted Code:** vendor the new ruleset folder next to `adopted-v1.0`, change
`PINNED_KEY` in `portal_api/ruleset.py`, and run the tests — every citation is re-checked, and the
819-cell scenario table re-compares the screener with the new use table.

## Applying (the three applications)

Each application is a form definition in `portal_api/forms/definitions/forms/`: the Cover Sheet
(`cover-sheet.v1.yaml`, part of every form) plus `use-permit.v1.yaml`, `small-project-plan.v1.yaml` and
`entrance-permit.v1.yaml`. A definition lists the official form's sections and fields; each field says
where its value comes from (a plain question, the property lookup, the account, another field, the
signature at submit, or staff) and, for a question, when it is asked (`show_if`, the screener's
condition language). The fields carry the Town's Planning Application packet; the Entrance / Driveway
form is new. `forms/answers.py` decides what applies, what is still missing and what prints;
`web/src/forms/applicability.ts` is its browser twin, and both are checked against
`web/src/forms/form-fixtures.json`.

**Approval.** Every entry starts as `status: draft`; production refuses a form with any draft in it
(`503 form_not_approved`), as for the screener. The record for the chair:

    .venv/bin/python -m portal_api.forms forms-sheet > ../../memos/<date>-application-forms-for-approval.md

**Versions.** An application keeps the form version and ruleset it started on; a new version is a new
file (`use-permit.v2.yaml`), never an edit to one in use.

**Records.** Answers and section notes are insert-only (a change appends a row); every change bumps
the application's revision, so a save from a tab that fell behind is refused (409) and the page offers
"Load the latest" or "Keep mine". Events name fields, never values.

**Uploads.** PDF, JPEG, PNG and HEIC, decided by the file's first bytes; 25 MB each; 60 a person an
hour. Each is scanned by ClamAV before anything is stored; if the scanner can't be reached, the upload
is refused. Files live in an S3-compatible store that only the API reaches (RustFS on the VM: MinIO no
longer publishes images; S3 or R2 in production, via `S3_ENDPOINT`), and go back only to their owner,
streamed through the API. The store's credentials are `STORE_ACCESS_KEY` / `STORE_SECRET_KEY` in the
VM's `.env`. Tests use an in-memory store and a fake scanner; two integration tests run against the
real ones when `PORTAL_TEST_S3_ENDPOINT` and `PORTAL_TEST_CLAMD_HOST` are set (CI sets the first).

**Journeys (Playwright).** `web/e2e/` drives each application end to end, at desktop and phone width,
with an accessibility check (axe; serious and critical findings fail) on every kind of page. They run
on the VM against the dev stack, not in CI (ClamAV's signature download is refused from CI runners):

    portal/vm.sh run 'cd portal/web && npx playwright install --with-deps chromium'   # once
    # dev API as above, plus PORTAL_S3_ACCESS_KEY=portal PORTAL_S3_SECRET_KEY=portal-dev-secret
    # and PORTAL_SIGNIN_LIMIT_PER_IP=100000 (every journey signs in from 127.0.0.1); npm run dev running
    portal/vm.sh run 'cd portal/web && PORTAL_E2E_URL=http://127.0.0.1:5173 PORTAL_E2E_MAILPIT=http://127.0.0.1:8025 npm run e2e'

