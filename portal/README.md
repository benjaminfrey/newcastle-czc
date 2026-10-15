# Applicant Portal

The public web app where applicants find out which permit they need and apply for it.
Design: `specs/2026-10-14-applicant-portal-design.md`. Plans: `plans/2026-10-14-applicant-portal-*.md`.

## Development

Development runs on a VM, not the Mac. The Mac holds the git checkout and the editor;
`portal/vm.sh` copies `portal/` to the VM (`~/newcastle-czc/portal/`) and runs commands there.
The VM is `ben@192.168.1.6` unless `PORTAL_DEV_VM` says otherwise. Everything on the VM listens
on 127.0.0.1 only; `portal/vm.sh tunnel` forwards the dev ports to the Mac.

Start the database and the mail catcher (Mailpit, web view at http://127.0.0.1:8025 through the tunnel):

    portal/vm.sh run 'sudo docker compose -f portal/deploy/compose.dev.yml up -d --wait'

API, first time:

    portal/vm.sh run 'cd portal/api && python3.14 -m venv .venv && .venv/bin/pip install -r requirements-dev.txt'

API, every time:

    portal/vm.sh run 'cd portal/api && .venv/bin/pytest'
    portal/vm.sh run 'cd portal/api && .venv/bin/python -m alembic upgrade head'
    portal/vm.sh run 'cd portal/api && PORTAL_COOKIE_SECURE=false PORTAL_ALLOW_STALE_PARCELS=true .venv/bin/uvicorn portal_api.main:create_app --factory --port 8000'

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

    .venv/bin/python -m portal_api.gis parcels --geolibrary
    .venv/bin/python -m portal_api.gis addresses --e911
    .venv/bin/python -m portal_api.gis districts --file ../../data/street-types/districts.geojson \
        --ruleset ../../build/permit-review/rulesets/adopted-v1.0/districts.json --source-date 2026-06-01
    .venv/bin/python -m portal_api.gis streets --inventory ../../source/exhibits/street-types/inventory.json \
        --types ../../source/exhibits/cross-sections/types.json --source-date 2026-09-14

**Parcels are the weak point.** Maine GeoLibrary's Newcastle parcels all date from April 1, 2012.
Current lot lines are in the Town's AxisGIS (CAI), which is not open for download; when the
assessor or CAI supplies an export, load it with

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

Districts come from a tracing of the District Map and are approximate; only districts in the
adopted ruleset are named (the trace's SD-Civic area is not in v1.0, so it shows as "staff will
confirm"). The basemap is self-hosted: see `portal/basemap/README.md`.
