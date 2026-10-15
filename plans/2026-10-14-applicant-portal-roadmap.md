# Applicant Portal — Phase 1 roadmap

**Spec:** `specs/2026-10-14-applicant-portal-design.md` (approved 2026-10-14). Read it first.

This is the milestone map for Phase 1. Each milestone gets its own task-by-task plan, written when
the milestone before it has landed, so every plan is written against code that exists. Only
Milestone 1 has its detailed plan now: `plans/2026-10-14-applicant-portal-m1-skeleton.md`.

Each milestone ends demonstrable on the VM and with its own tests green in CI. A milestone's plan
may refine the files named here; it may not change a spec decision (§2 of the spec) without the
chair's approval.

| # | Milestone | Delivers | Done when |
|---|---|---|---|
| M1 | **Skeleton** | `portal/` layout; FastAPI + Postgres/PostGIS; Alembic; the hash-chained `event` log; email sign-in links and sessions; the React + HeroUI shell; CI job; Compose + Caddy on the VM | On the VM over HTTPS, a person requests a sign-in link, receives it, signs in, sees "My applications" (empty), signs out; `portal` CI job green |
| M2 | **Property lookup** | `portal/gis/`: GeoLibrary parcel import into PostGIS with source date; joins to districts (`data/street-types/work/districts.gpkg` until the contractor's shapefile) and the Street Type inventory; `GET /api/property/search`, `GET /api/property/{parcel_id}`; the "Where is it?" page with map (MapLibre GL) and confirm / "doesn't look right" | Typing a Newcastle address finds the parcel and shows map/lot, district, lot area, frontage, street and Type; refresh job re-runnable; lookup failure falls back to manual entry marked "property not verified" |
| M3 | **Form engine and screener** | Form-definition YAML schema and loader; the `show_if` expression evaluator in Python and TypeScript with one shared fixture file; ruleset loader pinned by `ruleset_key` + `content_sha256` (adopted only); the screener definition and "Here's what you'll need" page | Screener scenario table (use × district from `use-matrix.json`) passes; the two evaluators agree on every shared fixture; "Do I need a permit?" works signed out |
| M4 | **The three applications** | Definitions for Use Permit, Small Project Plan, Entrance/Driveway; wizard UI; autosave; review-and-edit with in-place edits and "Add more detail"; uploads (S3-compatible store — MinIO in dev — with ClamAV scan); Playwright journeys | A signed-in applicant completes each of the three to review-and-edit at desktop and phone width; every official field is filled or marked "staff completes"; uploads scanned and size/type-limited |
| M5 | **Official forms** | `portal/render/`: Typst cover sheet + three forms using `style/` fonts and typography; blank printable versions | Reference render of each form; typography checked against `style/style-analysis.md`; blank forms print |
| M6 | **Submit and staff inbox** | Sign and submit; owner co-sign; frozen `submission` + revisions; staff role with authenticator-app second factor; inbox (view, download, completeness, fee paid, "please add…"); admin settings incl. standards-check modes; email notifications with retry; "needs attention" marker | End-to-end: applicant submits, staff marks complete and fee paid, requests more info, applicant answers with a revision; no-verdict guard green; applicant A cannot read B |
| M7 | **Hardening and pilot** | Off-VM nightly backups + restore drill; security review; plain-language review; accessibility pass; pilot with the CEO on past applications | Restore drill recorded; review findings ruled on; pilot notes written up for the chair |

**Open decisions that gate milestones** (spec §9): O1 fee schedule (M3 shows the "set by the Town's
fee schedule" fallback until supplied); O2 FOAA wording (M6 submit page); O8 staff list (M6);
O7 web address (M1's VM can use an interim host name); O9 owner authorization (M6).
