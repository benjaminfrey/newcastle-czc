# Applicant Portal — design specification (Phase 1)

**Town of Newcastle, Maine · Core Zoning Code · branch `claude/applicant-czc-review-system-60d388`**
Written 2026-10-14 against the Code adopted at the Special Town Meeting of September 14, 2026
(CZC v1.0, ruleset `adopted-v1.0`). Every decision in §2 was made by the Planning Board chair in
brainstorming on 2026-10-14.

**Approved by the Planning Board chair on 2026-10-14** as the basis for the implementation plan.

---

## 1. What this is for

A public web app where anyone in Newcastle can find out which permit their project needs, then
apply for it by answering short, plain-language questions. The answers build the Town's official
application form, filled in; the applicant can then edit it and add detail section by section,
attach plans and photos, sign and submit. Reviewing authorities (the Code Enforcement Officer, the
Planning Board) receive a complete, consistent form tied to the Code version it was built under.

Success: a resident with no zoning background completes a complete application without calling the
Town Office, and reviewers stop receiving forms with blank districts and sticky-note questions
("does he need a permit to do that?" — on the Verney Use Application of 2025-04-02).

**Two phases, two specs.**

- **Phase 1 (this spec): the Applicant Portal** — public wizards, official forms, submission, and a
  minimal staff inbox.
- **Phase 2 (its own spec, later): the reviewer tool** — CEO and Planning Board review, approvals,
  denials, Findings of Fact and Conclusions of Law. It grows out of the existing Planning Board
  Review app (`build/permit-review/`), which stays what it is: the Board's local review and drafting
  tool. Phase 1 must hand Phase 2 clean, structured submissions (§8).

**The principle carried over from the Board app: the software never decides.** It may say what the
Code asks for and set an applicant's numbers beside the Code's; it never says approved, denied,
compliant, meets or fails. Only a reviewing authority decides, and only in Phase 2.

## 2. Decisions

| # | Decision | Choice |
|---|---|---|
| P1 | First-release application types | **Use Permit** (Art. 8 §15), **Small Project Plan** (Art. 8 §10), **Entrance / Driveway Permit** (Art. 3 §13.c.1). The screener identifies every other type and explains it, with "contact the Town Office". |
| P2 | Submission | A hosted app with a database; real digital submission. |
| P3 | Hosting | A VM the chair controls for development; every component chosen so production can move to a managed platform by configuration, not rewrite. |
| P4 | Applicant sign-in | Email sign-in links; no passwords. |
| P5 | Fees | Shown from the Town's fee schedule, paid offline; staff mark paid. No online payment in Phase 1. (Per project, 2026-10-25: an application fee once per permit; see the projects brief §7.) |
| P6 | Official forms | A new form set in CZC house style (cover sheet + one form per type), not a copy of the current paper forms. |
| P7 | Property facts | Address lookup and map, from the **Maine GeoLibrary parcel layer** (kept current by the assessor) joined to our district and Street Type data. |
| P8 | Standards check | An **admin setting per application type**: *Off* (collect only), *Staff only* (default), *Show applicants*. Flags, never verdicts, in every mode. Each change is logged. |
| P9 | Staff side in Phase 1 | A minimal inbox: view, download, completeness, fee paid, "please add…" requests, admin settings. No review or decisions. |
| P10 | Architecture | React + TypeScript frontend, FastAPI backend, Postgres/PostGIS, S3-compatible file storage, Docker Compose. |
| P11 | UI components | **HeroUI** (React, built on Tailwind CSS and React Aria). Version pinned in the plan. |
| P12 | Location | A new top-level `portal/` folder in this repository. |
| P13 | Civic district (added 2026-10-15) | SD-Civic (Art. 2 §5: municipally owned land, "not subject to the standards of this Ordinance") is an adopted district and is named as such. **Chair's ruling:** only the Town builds on SD-Civic land, on the Select Board's recommendation and a Town Meeting vote; the Town does not follow the CZC there and does not apply for permits. The portal tells applicants so; no application is made for Civic land. |

## 3. Architecture

> Storage revised by `specs/2026-10-25-applicant-portal-projects.md` §5 (2026-10-25): `application` became
> `project` with parts, pinned forms, submissions and reviews.

```
portal/
  web/        React + TypeScript (Vite), HeroUI — applicant pages and the staff inbox
  api/        FastAPI — sign-in, drafts, submissions, uploads, property lookup,
              standards check, PDF rendering, staff endpoints
  forms/      one YAML definition per application type + cover sheet + screener
  render/     Typst templates for the official forms (reusing style/ fonts and template)
  gis/        parcel import and the property-facts join
  deploy/     Docker Compose, Caddy, backup scripts
```

**Components.**

1. **Applicant web app** — pages: start → property → what you'll need → wizard → review and edit →
   sign and submit → my applications. It reads form definitions from the API and holds no rules of
   its own.
2. **API** — the only thing that reads the database, the file store or the rulesets.
3. **Form definitions** — the wizards and forms as data (§5).
4. **Code data** — the API loads the **adopted** ruleset only, pinned by `ruleset_key` and its
   manifest's `content_sha256`, from `build/permit-review/rulesets/`. Today that is `adopted-v1.0`.
   A draft ruleset (e.g. `v1.2-draft`) never governs an application. Rolling the portal to a newly
   adopted ruleset is a deliberate, recorded step, as it is in the Board app.
5. **Property data** — a scheduled import of the GeoLibrary parcel layer into PostGIS, joined with
   the district polygons, a shoreland layer when one is supplied, and the Street Type inventory
   (`source/exhibits/street-types/inventory.json`). Every import is stamped with its source date.
6. **Form renderer** — Typst, using `style/czc-template.typ`'s fonts and typography, turns a
   submission into the official PDF. The same templates print blank paper forms for walk-in
   applicants.
7. **Staff inbox** — a staff-only area of the same React app.
8. **Storage and mail** — Postgres for records; an S3-compatible object store for uploads and PDFs;
   an SMTP relay for email.

**Deployment.** Docker Compose on the VM, Caddy in front for HTTPS. Production equivalents: any
managed Postgres with PostGIS, S3 or Cloudflare R2, any container host, any SMTP relay. No
component may depend on a feature only one vendor offers.

**CI.** Portal tests run as their own job, independent of the 15–20 minute document-build suite.

## 4. The applicant journey

> Superseded for the journey by `specs/2026-10-25-applicant-portal-projects.md` (2026-10-25): sign in
> first, a project of parts, a dashboard; "Do I need a permit?" folds into the project.

1. **"What are you planning?"** — no sign-in. Plain choices: build something new or add on · start a
   business or change how a building is used · put in or move a driveway · divide land · something
   else / not sure. Open to anyone, so it doubles as a public **"Do I need a permit?"** tool.
2. **"Where is it?"** — address search or a tap on the map. The app shows the parcel outline and what
   it found (map/lot, district, lot area, frontage, the street and its Type); the applicant confirms
   or says "this doesn't look right", which records a note for staff without blocking them.
3. **"Here's what you'll need."** — each application the Code calls for, with who reviews it, the
   time the Code gives the reviewer (Small Project Plan: 10 days after a complete application,
   Art. 8 §10.d.4; Use Permit: 30 days, Art. 8 §15.d.1), the fee, and what to gather (photos, a
   sketch, the MaineDOT entrance permit for a State highway, Art. 3 §12.d). Worded "Based on your
   answers, the Code calls for…" and "The Code Enforcement Officer confirms this when you apply."
   Types not yet in the portal get the same explanation and "contact the Town Office".
   **Sign-in by email link happens here**, the first time there is something to save.
4. **The wizard** — short screens, one idea each, grouped into chapters ("Your building", "Your
   driveway", "Who's applying"). Plain words ("How far will the front of the building be from the
   road?", not "front setback"); units and examples; a **"Why we ask"** panel that opens to the Code
   section; "I don't know yet" where staff can follow up. Answers save as they are given. Questions
   appear only when they apply.
5. **Review and edit** — the assembled official form, shown as it will print. Each section offers
   **Edit** (fields change in place, under the wizard's own validation; a change that alters which
   questions apply sends the applicant back through just those) and **Add more detail** (free text,
   printed under that section). Standards-check flags appear here when the mode is *Show applicants*.
6. **Sign and submit** — the applicant attests the information is true and types their name. If the
   applicant is not the owner, they upload the owner's authorization or the owner co-signs by email
   link. They receive the official PDF, a reference number and "what happens next".
7. **My applications** — status (Submitted → Being checked for completeness → Complete → Under
   review → Decided), fee due or paid, and staff "please add…" requests, answered in the app.

**Plain language.** A reviewed glossary maps Code terms to plain words; question text aims at about
an 8th-grade reading level. The **official form keeps the Code's exact terms**, so the record stays
precise. **Accessibility:** usable on a phone; WCAG 2.1 AA.

## 5. Form definitions and data

**Form definitions** (`portal/forms/<type>.v<N>.yaml`). Each question has:

- `id`, plain-language `label`, `help`, and `why` (a Code citation, e.g. `Art. 8 §15`);
- `type` (choice, number + unit, text, date, upload, map point) and validation;
- `show_if` — a condition over earlier answers and property facts (e.g. `property.on_state_highway`),
  written in a small declarative expression format, evaluated identically by the browser and the API
  from the same file, never executed as code;
- `fills` — the official-form field(s) the answer feeds;
- `compare` — optional; the standard the standards check sets this answer beside.

Each definition records its own version and the `ruleset_key` it was written against.

**The screener** is a definition too. Its outcomes read from the ruleset's use matrix rather than
restating it. In the adopted use table the cell code names the permit and its reviewer: `u` ● Use
Permit (CEO), `rc` Residential Companion Permit (CEO), `sp` Special Permit (Planning Board), `ex`
Expanded Use Permit (Planning Board). Only `u` leads to a Phase 1 wizard; the others are explained.
The fifth status, ○ "No Permit Required", exists only in the Right to Farm draft (v1.2-draft); the
screener can offer that answer only after a Town Meeting adopts it and the portal rolls to that
ruleset.

**Records (Postgres).**

| Record | Holds |
|---|---|
| `applicant` | email, name, phone; one per email address |
| `application` | reference number (e.g. `2026-0042`), type, status, applicant / owner / agent, **pinned `ruleset_key` and form version** |
| `property_snapshot` | the parcel and district facts as of application, with the import date, so a later parcel update never rewrites an application |
| `answer` | one row per question: value, who set it, when; edits keep the previous value |
| `section_note` | the applicant's "add more detail" text, per section |
| `attachment` | file name, type, size, SHA-256, storage key |
| `submission` | the frozen record at submit: answers, notes, flags, the official PDF and its checksum. Never edited; a reply to "please add…" creates a new revision that refers back |
| `staff_action` | completeness, fee paid, information requested — who and when |
| `event` | append-only, hash-chained audit log of every change, as in the Board app |
| `setting` | admin switches (standards-check mode per type), with change history |

**Standards-check flags.** Computed from the pinned ruleset and stored with the submission: rule,
standard, value given, citation — e.g. *"Minimum front setback in D2: 20 ft. Entered: 15 ft."*
There is **no pass/fail field**, so nothing downstream, Phase 2 included, can read a verdict out of
Phase 1.

**Fees.** Read from `portal/forms/fees.yaml`, transcribed from the Town's adopted fee schedule.
(Superseded 2026-10-25: the 2025.08.25 schedule is in force and transcribed in
`portal/api/portal_api/forms/definitions/fees.yaml`; O1 is closed. The text below is the original plan.)
The schedule is not in the repository (open decision O1). Until it is, every fee reads "Set by the
Town's fee schedule — the Town Office will tell you the amount." The app never shows a guessed
amount.

## 6. Security, privacy and failure handling

**Sign-in and access.** Sign-in links are single-use and expire after 15 minutes; sessions use
secure, HTTP-only cookies. Applicants see only their own applications; a co-signing owner sees only
the one they were asked to sign. Staff and admin are separate roles and sign in with an email link
**plus an authenticator-app code**. Sign-in, address lookup and uploads are rate-limited; no CAPTCHA.

**Uploads.** PDF, JPG, PNG and HEIC, up to 25 MB each; virus-scanned (ClamAV) before acceptance;
stored privately and served only through short-lived links to people allowed to see them.

**Records and privacy.** Submitted applications are likely public records under Maine's Freedom of
Access Act; the app says so at submit time in wording counsel approves (O2). Retention periods for
drafts, abandoned applications and submissions follow the Maine State Archives schedule (O3); until
set, nothing is deleted automatically. No third-party trackers or advertising analytics. **No AI in
Phase 1**: nothing an applicant enters goes to any outside service except the email relay.

**Never lose a submission.** Submitting saves the frozen record first; the PDF and emails follow as
separate, retried steps. If either fails, the submission stands, the applicant still sees their
reference number, and staff see a "needs attention" marker. If address lookup is down or the parcel
is not found, the applicant enters map/lot and picks a district, and the application is marked
"property not verified". A draft open in two tabs warns before a later save overwrites. Nightly
database dump and file-store copy go **off the VM**, with a scheduled restore drill.

**Version safety.** An application stays on the ruleset and form versions it started under. If the
Code is amended mid-draft, the app tells the applicant and staff; it never switches silently.

## 7. Testing

- **Form-definition checks (CI):** every question reachable; every official-form field filled by a
  question or marked "staff completes"; every `why` citation resolves in the pinned ruleset (reusing
  the Board app's citation verifier); `show_if` gives identical results in TypeScript and Python
  over one shared fixture set.
- **Screener scenarios:** a table generated from the use matrix — use × district → permit and
  reviewer — across every district in the pinned ruleset.
- **No-verdict guard:** fails if any flag, status or applicant-facing text contains verdict words
  (*approved, denied, compliant, meets, fails, violates*) outside a recorded staff decision.
- **Official PDFs:** a reference render of each form, checked against `style/style-analysis.md`.
- **End-to-end (Playwright):** a full journey for each of the three types at desktop and phone
  width; automated accessibility checks; one manual screen-reader pass per release.
- **Security:** applicant A can never read applicant B's records; disallowed types and oversized
  uploads are refused; expired and reused sign-in links are refused.

## 8. Build order and the Phase 2 link

Each milestone is demonstrable on the VM.

1. **Skeleton** — Compose, API, database, email sign-in, HTTPS, HeroUI shell.
2. **Property lookup** — GeoLibrary parcel import, joined with districts and Street Types; the
   address-and-map page.
3. **Form engine and screener** — the definition format; "Do I need a permit?".
4. **The three applications** — definitions, wizard, review and edit, notes, uploads.
5. **Official forms** — Typst cover sheet plus three forms; blank printable versions.
6. **Submit and staff inbox** — submissions, revisions, staff actions, email, admin settings, the
   standards-check modes.
7. **Hardening and pilot** — backups and a restore drill, a security review, a plain-language
   review, then a trial with the CEO on past applications.

**Phase 2 link.** Question ids align with the ruleset's rule ids, so a portal submission arrives
carrying the facts the Board app's review engine reads. That removes the need for OCR on portal
submissions and addresses the Board app's open item D-0029 (no case's facts reach the engine). The
engine today walks only the 21 subdivision criteria (Art. 8 §12.f); Phase 2 adds criteria sets for
the Phase 1 types.

## 9. Open decisions

Recorded for the chair, the Board or counsel; none is guessed in the build.

| # | Decision | Who |
|---|---|---|
| O1 | The Town's adopted **fee schedule** for the three types — closed 2026-10-25 (the 2025.08.25 schedule, `fees.yaml`) | Chair / Town Office |
| O2 | **Freedom of Access Act** notice wording at submit | Counsel |
| O3 | **Retention** periods for drafts, abandoned applications, submissions | Counsel / State Archives schedule |
| O4 | **Who adopts the new forms** — Planning Board, Select Board, or administrative | Chair / counsel |
| O5 | Plain-language **sign-off** on question wording | CEO and Planning Board |
| O6 | Source for a **shoreland** layer; arrival of the contractor's **district shapefile** | Chair |
| O7 | Production **host**, **email relay**, and **web address** | Chair / Select Board |
| O8 | The **staff list** and who holds the admin role | Chair / Town Office |
| O9 | Whether the owner's authorization may be an upload, or must be an owner co-signature | CEO / counsel |

## 10. Out of scope for Phase 1

Online payment; review, approvals, denials and Findings of Fact (Phase 2); application types beyond
P1 (explained by the screener, not built); AI-assisted anything; Shoreland, Floodplain and the other
Art. 8 §9.d permits beyond being named by the screener; any change to `build/permit-review/`.
