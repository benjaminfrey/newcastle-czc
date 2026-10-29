# Applicant Portal — projects (revision to the task-list brief)

**Status:** approved by the Planning Board chair, 2026-10-25, with section 12's nine
questions settled the same day.
**Revises:** `specs/2026-10-25-applicant-portal-task-list.md` (tasks and cards, approved 2026-10-25)
and the portal design `specs/2026-10-14-applicant-portal-design.md` where it describes "Do I need a
permit?" (§3), applications (§4) and fees (P5, O1). Where they differ, this brief wins.
**Prototype:** "Newcastle Project Hub", https://claude.ai/artifact/V5GqmeZQ2RiVQhydtLjq2U (the chair
saw it on 2026-10-25). It is a picture of the flow; its permit names and fees are examples, and
sections 6–8 of this brief replace them.
**Lands before:** Milestone 5 (printing the official forms) and Milestone 6 (sending and the staff
inbox), so both are built on projects from the start.

## 1. Decisions already made by the chair (2026-10-25)

1. **Sign in first, always.** Nobody starts anything signed out. A new person's first sign-in
   creates their account, and everything they make is saved under it.
2. **"Do I need a permit?" goes.** The screener's questions move into the project, where each is
   asked once; the screener's approved rules keep working, reading the project instead (§6).
3. **Your details are saved once**, on your account, and every project starts from them.
4. **A project is sent as one unit.** A project may need several permits, as people understand
   permits today, but they are all part of the same project, sent together.
5. **You can add to your project until Town staff lock it** as sent for review to the reviewing
   authorities. After the lock the project is read-only to the applicant.
6. **The Code's clocks and schedules apply** (the ruleset's `clocks.json`), and **the Town's
   published fee schedule** (§7).

## 2. How it works today (for reference)

- **Accounts:** `applicant` (email unique and lower-cased; `name`, `phone` and `role` columns). The
  email is the username. Sign-in is a one-time link valid 15 minutes (`signin_token`, hash only); a
  sign-in makes a `session` (cookie `portal_session`, hash only). `name` and `phone` are never
  filled today: the cover sheet asks for them again as answers on every application.
- **An application is one form:** `application` (one `form_key`, `form_version`, `ruleset_key`,
  status always `draft`, a `revision` for safe saves), `property_snapshot` (one per application),
  `application_item` (buildings and additions), `answer` and `section_note` (insert-only: a change
  adds a row), `attachment` (scanned files in the store), `event` (the hash-chained log).
- **Sending is not built.** Status is only ever `draft`. Milestone 5 prints the forms, Milestone 6
  sends them. No real application exists yet (production refuses the forms until approved).

## 3. The applicant's journey

### 3.1 Home (signed out)

The Town seal, "Town of Newcastle — Permits", and the sign-in card: "Your email address", **Email me
a sign-in link** (near-black button), and "No password. We'll email you a link." Nothing else; the
old "Do I need a permit?" link and page are gone (`/start*` addresses go to Home).

### 3.2 Home (signed in)

- **Start a new application** — the near-black, full-width button.
- **Continue an application** — the plain, full-width button; it opens the most recently changed
  project in `draft` or `submitted` (§5.2), or, if there is none, says "You have no application in
  progress."
- **Your applications** — every project, newest change first, one row each: its icon (the first
  part's), its title, "Map 4, Lot 36 · 2 things left" (or "· sent October 3"), and a status pill
  (§5.2): Draft · Sent · With the Town · Decided.

### 3.3 Starting a project: three cards

The card, header, bar and footer of the task-list brief (§4), header "New application · n of 3".

1. **How can the Town reach you?** Full name, Phone, Mailing address (the email is the account's,
   shown, not editable here). Filled from the account; Continue saves changes back to the account
   (decision 3). A person who already has all three filled skips this card.
2. **Where is the work?** The property search and map from "Your property" today, then "Is this your
   property?" with the lot's facts (map/lot, address, district or districts, acres, frontage and
   roads, the map's date) and the three tiles: Yes, this is my property · This doesn't look right
   (opens the note) · No, search again. The manual fallback stays (property marked "not verified").
3. **What are you doing here?** "Choose all that apply. You can add more later." The parts (§4) as
   icon tiles, several allowed. Continue (named **Go to my project**) creates the project with those
   parts and opens its dashboard. At least one part is required to continue.

The project's title starts as the parts joined by "and" plus the street ("New building and driveway
at 461 Sheepscot Road") and can be renamed on the dashboard (pencil beside the title).

### 3.4 The project (the dashboard)

The application's home. Desktop: the window's sidebar (Home, Project, Messages, You) beside it;
phone: the bottom tab bar with the same four. Top to bottom:

1. **Title** (30 px bold) and a pill: "2 things left" (`--warn-*` tokens, new) or "Ready to send".
2. **The parcel card:** a small lot drawing (the parcel outline from the map), map/lot (15 px
   semibold), then "461 Sheepscot Road · Rural (D1)" and "2.73 acres · 675 ft on Sheepscot Road"
   (13 px secondary).
3. **Your project:** one row per part: its icon, its name, a one-line summary (for a building, the
   item summary of the task-list brief: "28 × 40 ft · 2 floors · 2,240 sq ft · front faces
   north"), its status pill (Done · "3 of 8" · Not started), a chevron. A tap opens the part's
   cards; a building or an addition with several items opens its list (the task-list brief §4.7).
4. **Add to your project:** the parts not yet in the project as icon tiles with a +. A tap adds the
   part and opens its first card.
5. **Beside these** (a 280 px column on a desktop, below on a phone):
   - **What you'll need** (§6, §7, §8): each permit, its reviews, its fees and its clocks.
   - **You:** name, "the owner" or "helping the owner", email; a tap opens the About-you cards
     (owner, helper).
   - **Check and send**, the near-black full-width button.

The dashboard is the recap: there is no separate long review page.

### 3.5 Check and send

A short screen, not a printout:

1. **"n things to finish first"** (only if any): one row per part (or the About-you task) with
   something required still blank, each opening the card it stops at.
2. **Your project at a glance:** the parcel row; the applicant row; one row per part with its
   summary and **Change**.
3. **What's due when you send:** each permit's application fee and the total (§7), "payable when
   you send", and "Permit fees are due before a permit is issued."
4. **The official forms:** one row per form the project fills ("Small Project Plan Application",
   "Driveway and Entrance Permit Application") with **View** (the printout, Milestone 5).
5. **Send to the Town** (near-black), only when nothing is left to finish; the confirmation (§5.3).

The long section-by-section review of today goes; each form's full content is its printout (item 4)
and its check pages (the task-list brief §4.7).

### 3.6 Messages and You

- **Messages:** empty until Milestone 6: "No messages yet. When the Town asks for something, or your
  application moves along, it shows here." Milestone 6 puts the Town's requests and status changes
  here, per project.
- **You:** name, email (not editable: it is the account), phone, mailing address, each with Change;
  **Sign out**.

## 4. Parts

A part is one piece of a project. Each has an id, an icon (Tabler outline, §5 of the task-list
brief) and the questions it brings. The building and addition parts repeat (several buildings) as
today's items do; the others occur once.

| Part (tile words) | id | Icon | Repeats | Its questions (today's form sections) |
|---|---|---|---|---|
| A new building | `building` | `building-cottage` | yes | Small Project Plan: building, building_location, building_details, building_mass, building_windows |
| An addition, porch or deck | `addition` | `home-plus` | yes | Small Project Plan: component |
| Renovating a building | `renovation` | `paint` | no | the renovation questions (§6.2) |
| Site work (parking, grading, landscaping) | `site` | `shovel` | no | the site questions (§6.2) |
| Start or change a use | `use` | `building-store` | no | Use Permit: existing, proposed, use_documents_section (uses, descriptions, photos and plans) |
| A driveway | `driveway` | `road` | no | Entrance Permit: entrance |
| Divide land | `divide` | `layout-grid` | no | the division questions (§6.2) |
| Something else | `other` | `help-circle` | no | "Tell us what you have in mind" (long text) |

Project-level questions, asked once whatever the parts: the cover sheet (location and deed, site,
applicant, owner, agent; the applicant's name, phone and address come from the account), and the
Small Project Plan's `project` section (`project_description`, `site_plan`) when any of building,
addition, renovation or site is in the project. The form field `work_kinds` ("Type of project") is
no longer asked: it prints from the parts (building → new_building, addition → addition,
renovation → renovation, site → site). Its fifth option, "A change to a nonconforming lot, use,
structure or site improvement" (`nonconforming`), has no part and the portal never sets it: the
Code Enforcement Officer raises it at review (§12.9).

## 5. Storage and sending

### 5.1 Tables (a migration, `0006_projects`)

- **`applicant`** gains `mailing_address text`. `name`, `phone` and `mailing_address` are the
  account's details (decision 3); `PUT /api/me` changes them; the cover sheet's `applicant_name`,
  `applicant_phone` and `applicant_address` print from them (they become `source: account`, as
  `applicant_email` is today).
- **`project`** replaces `application`: `id`, `applicant_id`, `title`, `ruleset_key`,
  `status` (§5.2), `revision`, `created_at`, `updated_at`, `submitted_at`, `locked_at`,
  `locked_by` (a staff account).
- **`property_snapshot`** is keyed by `project_id` (one per project, as today per application).
- **`project_part`** replaces `application_item`: `id`, `project_id`, `kind` (the part ids of §4),
  `position`, `created_at`, `removed_at`. Today's `building` items become `building` parts and
  `component` items become `addition` parts.
- **`project_form`**: the forms a project fills, worked out from its parts (§6) and pinned at the
  version current when the form first applied: `project_id`, `form_key`, `form_version`. A form
  stays pinned while it applies, so a project never changes version under the applicant.
- **`answer`**, **`section_note`**, **`attachment`**: `application_id` becomes `project_id`,
  `item_id` becomes `part_id`; still insert-only, still with `set_by`. One answer per field per
  part, shared by every form that prints that field.
- **`submission`**: the frozen copy made at the lock (§5.3): `id`, `project_id`, `seq` (1 for the
  first lock, 2 for a revision after a "please add…"), `locked_at`, `locked_by`, `snapshot jsonb`
  (the property snapshot, the parts, every current answer and note, the attachments' names and
  hashes, the forms and versions, the reviews, fees and clocks of §6–§8, the ruleset key), `sha256`
  of the snapshot. Insert-only.
- **`review`**: one row per review the project needs at the lock: `id`, `submission_id`,
  `review_key` (an `applications.yaml` key, or `structure` §7), `use_key` (for a use review, one
  per chosen use, §12.6), `permit_key` (§7), `reviewer`, `status` (`waiting`, `in_review`,
  `decided`), and the clock events of §8 (`submitted_at` = the lock, `decision_at`). Milestone 6
  builds the staff side on these.
- **`event`** gains the kinds `project.created`, `project.part_added`, `project.part_removed`,
  `project.submitted`, `project.locked`, `project.unlocked` (§5.3); payloads name ids, never answer
  values, as today.

Existing drafts (test data only) are converted 1:1: each `application` becomes a `project` with one
part per its form (`use_permit` → `use`, `small_project_plan` → `building`/`addition` from its items,
`entrance_permit` → `driveway`).

### 5.2 Statuses

| Status | Set by | Applicant can edit | Applicant sees |
|---|---|---|---|
| `draft` | creating the project | yes | Draft |
| `submitted` | **Send to the Town** | yes (decision 5) | Sent |
| `locked` | staff: **Lock and send for review** | no | With the Town |
| `decided` | staff, when every review is decided | no | Decided |

A change while `submitted` is saved as usual and shows the Town "Changed since you sent it" with
the time (Milestone 6). Sending again is not needed.

### 5.3 Sending and the lock

- **Send to the Town** (applicant): only when nothing required is blank. Confirmation sheet: "Send
  your project to the Town?", the permits and the application fees due (§7), "You can still add to
  your project until the Town locks it for review." Buttons: Cancel · **Send**. Sets `submitted`,
  `submitted_at`; event `project.submitted`; an email to the applicant ("We've received your
  project") and to the Town Office address in admin settings (Milestone 6).
- **Lock and send for review** (any staff account, §12.8; Milestone 6): freezes the project as
  `submission` seq 1, creates the `review` rows, sets `locked`, starts every review's clock (§8),
  and routes each review to its reviewer.
- **After the lock**, a staff "please add…" request (Milestone 6) unlocks only what it names; the
  applicant's answer and a new staff lock make `submission` seq 2. An unlock is the event
  `project.unlocked`.

### 5.4 The API (replacing `/api/applications…`)

`GET/PUT /api/me` · `POST /api/projects` {property, parts} · `GET /api/projects` ·
`GET /api/projects/{id}` (state, parts, answers, notes, attachments, forms, needs §6–§8, missing) ·
`PUT /api/projects/{id}/answers` · `POST/DELETE /api/projects/{id}/parts` (with `copy_from`, as
Copy Building 1 today) · `PUT /api/projects/{id}/notes` · `PUT /api/projects/{id}/title` ·
`POST /api/projects/{id}/submit` · uploads as today under `/api/projects/{id}/attachments`. Every
write carries `base_revision` (409 on a stale one, as today) and is refused after the lock
(409 `locked`). `POST /api/screener` is removed; its rules run inside `GET /api/projects/{id}`.

## 6. What a project needs: the screener's rules, reading the project

### 6.1 How the rules run

The approved `rules.yaml` and `applications.yaml` keep their content and their approval. Their
inputs, today filled from the screener's questions, are filled from the project:

| Rule input | From |
|---|---|
| `project` (build, use, driveway, divide, other) | the parts: building, addition, renovation, site → `build`; use → `use`; driveway → `driveway`; divide → `divide`; other → `other` |
| `building.kind` | run once per building-type part: building → `new`; addition → `addition`; renovation → `renovation`; site → `site` |
| `building.gross_floor_area_sf` | for a new building: its `floor_area` answer (the carry the chair approved on 2026-10-24); for an addition: §6.2 |
| `building.total_floor_area_sf` | the renovation part's question (§6.2) |
| `building.parking_spaces` | the site part's question (§6.2) |
| `building.new_dwelling_units` | the sum of `dwelling_units` across the project's new buildings |
| `building.homes_within_5_years` | the project question of §6.2 |
| `division.lots_after`, `division.divided_last_5_years` | the divide part's questions (§6.2) |
| `use_key` | each of the use part's `proposed_uses`: the rules run once per chosen use (§12.6) |
| `property.*` (district codes, on a State highway, Civic) | the property snapshot, as today |

A rule that fires for any building-type part counts once for the project. Its outcome names an
application (`small_project_plan`, `large_project_plan`, `subdivision`, `entrance_permit`,
`use_permit`, …) with `certainty` `needed` or `may_need`, as today. These outcomes are the
project's **reviews**. A `may_need` review shows "May be needed — the Code Enforcement Officer
confirms" and does not block sending.

### 6.2 The screener's questions, asked once, in the parts

Each is a new form question (`status: draft`, for the chair's approval with the forms), worded as
in today's screener:

- **Addition** (each): "How much floor area will the addition add, in square feet?" (→
  `building.gross_floor_area_sf` for that addition).
- **Renovation:** "What is the floor area of the whole building, in square feet?" and "Which
  building?" (an existing building, typed; the renovation has no Building Form of its own today).
- **Site work:** "How many parking spaces will there be?"
- **Project, when any new building has homes:** "How many homes were added on this lot in the last
  five years, before this project?"
- **Divide land:** "How many lots will there be afterwards?" and "Has this land been divided in the
  last five years?" (Yes · No · I don't know).

### 6.3 Reviews the portal doesn't take yet

`applications.yaml` marks `large_project_plan`, `subdivision`, `special_permit`, `expanded_use` and
`residential_companion` `in_portal: false`. Each will join the portal later and follow this brief's
path, as the Use Permit and the Small Project Plan do (§12.4). Until then a project that needs one
shows it under What you'll need as "Not in the portal yet — the Town Office takes this one", with
its reviewer and clocks; the project can still be sent, and staff see that review flagged when they
lock it.

## 7. Fees: the Town's Planning Fee Schedule

**Source:** "Planning Fee Schedule — as of 2025.08.25", linked as "Fee Schedule" from the Town's
home page (https://www.newcastlemaine.us), served as
https://drive.google.com/file/d/1f2ZNZcp0ESJU3uDRK7aEFEooCpzGo5uB/view. Read on 2026-10-25. Each
permit has an **application fee** ("payable upon submission of an application") and a **permit
fee** ("due prior to issuance of permit"), the permit fee being "cumulative of below as applicable".
"All fees are non-refundable."

| Permit | Application fee | Reviews within it (permit fee) |
|---|---|---|
| USE PERMIT | $30 | Basic Use $0 · Residential Companion Use $0 · Expanded Use $60 · Special $60 · Shoreland Use (CEO rev) $0 · Shoreland Use (PB rev) $60 |
| BUILDING PERMIT | $30 | Small Project Plan $0 · Small Project Plan Revisions $0 · Large Project Plan $240 · Large Project Plan Revisions $100 · Structure $30 · Entrances $0 · Demolition of Historic Assets $0 · Floodplain Management $60 · Mobile Home Park $60 · Tower $500 · Power Generation $0.10 /sf · Erosion & Sediment Control $60 |
| SUBDIVISION (PERMIT) | $300 | Subdivision (Major) $0 · Master Plan $1,000 |
| SIGN PERMIT | $30 | Sign $0 · Shoreland Sign $30 |
| PLUMBING PERMIT | Varies | Plumbing (interior) Varies · Subsurface Wastewater Varies · Tank Only Varies |
| ACTIVITY PERMIT | $30 | Tourist Rentals Annual Registration $70 · Temporary Structure $0 · Shoreland Vegetation Removal $60 |
| OTHER | — | Zoning Variance $300 · Administrative Appeal $300 |

It is transcribed into `portal/api/portal_api/forms/definitions/fees.yaml` (permit, application
fee, each review with its fee, the source URL, its "as of" date and the date read), loaded and
checked like the other definitions (approved by the chair on 2026-10-25 as the schedule in force,
§12.5), and shown:

- **What you'll need:** each permit with its application fee, and each review with its permit fee
  ("Small Project Plan · no permit fee"; "Structure · $30").
- **Check and send:** the application fees due when you send, and their total.
- "Varies" shows as "Set by the Town Office". Payment stays offline: staff mark fees paid (P5).

**Review to fee line** (`fees.yaml`): `small_project_plan` → BUILDING PERMIT · Small Project Plan;
`large_project_plan` → BUILDING PERMIT · Large Project Plan; `use_permit` → USE PERMIT · Basic Use;
`residential_companion` → USE PERMIT · Residential Companion Use; `expanded_use` → USE PERMIT ·
Expanded Use; `special_permit` → USE PERMIT · Special; `subdivision` → SUBDIVISION ·
Subdivision (Major); `entrance_permit` → BUILDING PERMIT · Entrances (§12.2: a driveway is a review
within the Building Permit, so a driveway-only project pays the Building Permit's $30 application
fee); and `structure` → BUILDING PERMIT · Structure, added once for **each new building** in the
project, $30 each (§12.3), not for additions, renovations or site work.

A permit's application fee counts once per project, however many of its reviews the project needs
(a new building and an addition: one BUILDING PERMIT, $30).

## 8. Clocks: the Code's own

From the ruleset's `clocks.json` through each application's `clock_keys` in `applications.yaml`
(today's data, unchanged).

- **They start at the staff lock** (§12.1): the lock is the Town's "receiving a completed
  application" (Art. 8 §10.d.4's words). The portal sets each review's `submitted_at` to the lock,
  for every clock whose `start_event` is `submitted_at`. The applicant's Send starts no clock.
- **In plain words, with the date** (§12.7): before the lock, "The Code Enforcement Officer decides
  within 10 days of accepting your project"; after it, "Decision due by November 14" (the lock's
  date plus the clock's days, on its `basis`: calendar days, business days or months). The
  ruleset's label stays for staff. Each clock's plain sentence is written in `applications.yaml`
  beside its `clock_keys` (`status: draft`, for the chair's approval).
- A review with no clock (`entrance_permit`, `subdivision` today) shows none.

## 9. What goes

- "Do I need a permit?": `pages/Start.tsx`, `pages/Results.tsx`, `pages/UsePicker.tsx`,
  `start/StartFlow.tsx`, `start/startScreens.ts`, `screener.ts`, `pendingStart.ts` and the carry
  (`NewApplication.carry`, `set_by = screener`); `/start*` addresses redirect to Home.
  `pages/Where.tsx`'s search, map and "Is this your property?" move into the second start card.
- `POST /api/screener` (the rules run inside the project).
- The per-form application (`application`, `application_item`, `/api/applications…`) and its
  task list (`TaskList`'s rows become the dashboard's part rows) and the review page
  (`ReviewPane`, `OfficialGroup` — the printout of Milestone 5 replaces it).
- The cover sheet's asking of the applicant's name, phone and address (they come from the account).

## 10. What stays

The cards and every rule of the task-list brief (§4: card, header, bar, body, tiles, footer;
grouped questions; check pages; the buildings list with Add, Copy Building 1 and Delete), the
form definitions and their approval, the rules and applications and their approval, sign-in,
insert-only answers with `revision`, uploads and scanning, the event log, light and dark, the
window's tokens and icons.

## 11. Proof

- A signed-out visit to any portal address lands on Home's sign-in card; `/start` redirects there.
- A new person: sign-in link → the three start cards → a project with a new building and a
  driveway → its dashboard shows one BUILDING PERMIT ($30 application fee) with Small Project
  Plan $0, Structure $30 and Entrances $0, and "The Code Enforcement Officer decides within 10 days
  of accepting your project" — checked against `rules.yaml`, `applications.yaml` and `fees.yaml` by
  a test that runs the real files. Two new buildings: Structure twice ($60). Two chosen uses: two
  Use Permit reviews under one $30 Use Permit application fee.
- Locked on a Monday: the Small Project Plan shows "Decision due by" that date plus 10 calendar
  days.
- The rules give the same applications for the same inputs whether filled from the screener (today)
  or from a project (a table test over every rule in `rules.yaml`).
- The account's details fill the cover sheet's applicant rows on two projects; a change on You shows
  on both.
- Send → `submitted`, still editable; a staff lock (a test seam until Milestone 6) → `locked`, every
  write refused with 409 `locked`, `submission` seq 1 holding the snapshot and its `sha256`.
- The migration converts the test drafts 1:1, and a project's forms print the same answers as the
  application they came from.
- Journeys on desktop and phone, dev and LAN; axe light and dark.

## 12. Decisions settled with the chair (2026-10-25)

1. **Clocks start at the staff lock**, which is the Town's receipt of a completed application; the
   applicant's Send starts none (§8).
2. **A driveway is the Entrances review within the Building Permit** ($0 permit fee); a
   driveway-only project pays the Building Permit's $30 application fee (§7).
3. **"Structure" ($30) is added for every new building**, once per building; not for additions,
   renovations or site work (§7).
4. **The application types not yet in the portal** (Large Project Plan, Subdivision, Special
   Permit, Expanded Use, Residential Companion) will be added once this paradigm is set, and will
   follow the same path as the Use Permit and the Small Project Plan. Until then: §6.3.
5. **The Planning Fee Schedule "as of 2025.08.25" is the schedule in force**; use it as is (§7). This
   closes the portal design's open decision O1.
6. **Each chosen use gets its own review**: the rules run once per use, each bringing its own
   Use Permit review and fee line (Basic, Expanded or Special), all under one Use Permit with one
   $30 application fee.
7. **Clocks read in plain words, with the due date** once the project is locked (§8).
8. **Any staff account may lock** a project and send it for review.
9. **Nonconforming changes are left to the Code Enforcement Officer**: the portal doesn't ask, and
   never sets the "Type of project" option for them (§4).
