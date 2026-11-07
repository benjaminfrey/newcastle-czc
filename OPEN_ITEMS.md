# Open items

What is open right now: amendments in progress, questions for counsel and the Planning Board,
and paused work. Moved out of CLAUDE.md on 2026-10-15 so it can change without touching the
instructions. Update it when an item opens or closes; move closed items to `HISTORY.md`.

- **Right to Farm amendment** (Articles 1, 2, 4, 5, 7, 9) — merged (PR #11, `e709b1d`) and cut as
  **v1.2-draft** on 2026-10-14 (`b4fb778`); the Comprehensive Plan consistency memo for the
  Planning Board followed (`250e5e4`). Spec `specs/2026-10-07-right-to-farm-design.md`; decisions
  R1–R35 in `plans/2026-10-14-right-to-farm-decisions.md`. Still open as of the v1.2-draft cut:
  counsel's questions in spec §7; the DACF notice (7 M.R.S. §155 — 90 days before the meeting or
  hearing that considers adoption); the permit app refuses `br` cells and 69 uses (D-0035).
- **Next major amendments, in this order** (Ben, 2026-10-26): more work on Right to Farm (above),
  then **Civic Buildings, Civic Spaces and Civic Amenities** on branch `civic-buildings-and-spaces`
  (created 2026-10-06 from `main`; no commits yet), then **Nonconformity** on branch
  `nonconformity` (one commit so far, `3a728e3`, the nonconformity review memo — the Code, Maine
  law and proposed language). Right to Farm spec §8 leaves the Article 8 §25 / Article 9
  nonconformity-definition disagreement to that branch. Keep both branches.
- **For counsel:** Article 9's Variance definition cites the Massachusetts Zoning Act (Maine's is
  30-A M.R.S. §4353); typos "Atricle" (Article 7), "extentions", "designnee" — fixing "designnee"
  also means updating the residue gate's expected sentence in the same commit.
- **Planning Board:** R2 vs R3 scope (memo in `memos/`, recommends a 600 ft test on private
  dead-end ways; Eden Lane vs Camp Rd inconsistency).
- **Ben to confirm:** Ownership Categories for `kavanagh-road-1` and `woods-island-road-1`
  (marker entries in `build/street-types/overrides.json`).
- **The contractor's district shapefile** — drop it in, re-run the pipeline from the join stage,
  re-promote `inventory.json`, rebuild; any change goes to the Board and Town Meeting.
- **Another planner's Fall-2026 redline** (`docs/CZC Redline 2026.06.docx`, untracked) — four
  analysis memos in `memos/`; open: merging their Article X into our Article 3, their "reviewing
  authority" rename vs our "Permitting Authority", the stale "Road" definition.
- **Permit-review app** (`build/permit-review/`) — paused; W5 blocked on decision D-0025 (may
  application content go to a third-party API?). Read `build/permit-review/BUILD-STATE.md` first.
- **Applicant Portal** (`portal/`; roadmap `plans/2026-10-14-applicant-portal-roadmap.md`) — M1–M3
  merged; the chair ruled on the screener's nine questions on 2026-10-18 and approved every screener
  entry on 2026-10-20 (`memos/2026-10-15-screener-rules-for-approval.md`). Milestone 4 (the three
  application wizards) merged (PR #19); the chair answered the forms sheet's six questions on
  2026-10-23 and **approved every form entry on 2026-10-28** (161 entries, through eleven decisions
  recorded in `memos/2026-10-21-application-forms-for-approval.md`: the five redesign proposals, a
  building's name optional, homes asked of every building, stories capped at 4, "story" / "Fiber-cement"
  / "sq ft", four help-wording fixes, the finish list, the parts, the project questions, the clock
  sentences, and the rest as written). The redesign (`specs/2026-10-23-applicant-portal-redesign.md`)
  and projects (`specs/2026-10-25-applicant-portal-task-list.md`,
  `specs/2026-10-25-applicant-portal-projects.md`) merged as PRs #20 and #21 on 2026-10-29.
  - **New direction, the guided builder** (`specs/2026-10-30-applicant-portal-guided-builder.md`,
    approved 2026-10-30): a conversation that helps residents shape a permittable project, an
    approved explanation library, Material UI, one public launch at full scope. Five designs in
    order (§11). Plan 1 of 6 (`plans/2026-10-30-applicant-portal-guided-builder-1-foundations.md`) merged
    as PR #22 on 2026-11-01; plan 2, the conversation engine
    (`plans/2026-11-01-applicant-portal-guided-builder-2-engine.md`), merged as PR #23 on 2026-11-02,
    and the chair's coverage answers as PR #24 the same day. Plan 3, the conversation screens
    (`plans/2026-11-02-applicant-portal-guided-builder-3-screens.md`), is on branch
    `portal-guided-3-screens` (PR #25). Plan 4, the lot drawing
    (`plans/2026-11-03-applicant-portal-guided-builder-4-drawing.md`), is on branch
    `portal-guided-4-drawing` (PR #26, stacked on #25). Plan 5, the pictures, is built (below); next is plan 6. Open decisions are the
    spec's §12.
  - **Answered by the chair 2026-11-05 (interview); built on `portal-guided-4-drawing`** (b7c6e32,
    in PR #26; the screen items below as well):
    - *Corner lots:* the guide suggests the front from the road Type (Article 2: Streets before
      Roads, then the lower code), the rule written for newly created lots, which the chair applies
      to existing lots too. The other road gets the district's Secondary Front Setback. The applicant
      can't pick another road; choosing one sends the lot to the Town. Two roads of the same Type, a
      through lot (roads on opposite sides; Article 9 defines a secondary frontage only on corner
      lots), and a lot touching no road all go to the Town. *For the next amendment:* say what applies
      along a through lot's second road, and whether §2's rule for new lots covers existing ones.
    - *Alleys:* a line along an S5 Alley is never a front and adds no frontage. It may be the rear
      (Article 2: "except an alley") or a side.
    - *The front question's help* names all five fronts: a road, water, an easement, a right of way or
      a civic space. A line not along a road still goes to the Town.
    - *Change of use:* not asked the front (no setbacks are checked).
    - *Nearest side:* drawn on the left as seen from the road; "Swap sides" stays.
    - *The drawing's words are approved*, with the new lines: the corner-lot help ("Your lot is on
      more than one road. The Code makes the front the line along the busier road, by its Type."),
      the answer "The line along {street} (the Code's front)", the row "Along {street}: the
      secondary front setback, at least {n} ft", and the five-fronts help.
    - *"This needs the Town's judgment"* saves the project and sends nothing until the staff handoff
      exists.
    - *A Change* lists the later questions it reopened.
    - *The Town Office:* no phone, hours or address on the screens. Show "Contact the Town Office"
      linking to the Citizens Request Center (https://www.newcastlemaine.us/citizens_request_center/index.php,
      checked 2026-11-05; it lists Code Enforcement).
    - *Words never used on applicant screens:* approved as proposed (approved, denied, granted,
      rejected, permit issued, compliant, violates), enforced by a test.
    - *A new house* is checked against the Residential column and Primary Building Placement.
    - *Outside AI (decision 14):* no, not at launch. Revisit after launch.
    - *Shoreland:* a separate ordinance and map outside the CZC. The chair will send them; until then
      shoreland lots go to the Town. *Permits on record:* none known by lot; parked.
    - *Notes:* one optional "Anything the Town should know?" box on Check and send, read by staff
      only (the guide never reads it). The "too long" message points there.
    - *The old cards' looks findings* (task list twice, 44 vs 36 px fields, property card spacing,
      "No password" twice) are closed as superseded; recheck the same four on the new screens in
      plan 6.
  - **Plan 5, the pictures**, is built on branch `portal-guided-5-pictures`, stacked on #26:
    - design: `specs/2026-11-06-applicant-portal-guided-builder-pictures.md`;
    - plan: `plans/2026-11-06-applicant-portal-guided-builder-5-pictures.md`.

    What's built:
    - the opening scene, with ten places to tap (two guided, eight "coming soon");
    - the "add to this project?" question;
    - the stories and setbacks pictures.

    The chair approved the sample sheet on 2026-11-06
    (`memos/2026-11-06-guided-builder-pictures-sample-sheet.md`), and the scene's and the setbacks
    picture's descriptions the same day. Every word plan 5 shows is approved.
  - **The guided builder's wording, answered by the chair 2026-11-06 and built** on
    `portal-guided-4-drawing` (`memos/2026-11-06-guided-builder-wording-for-approval.md`). All of it
    is approved except two drafts that aren't shown to the public:
    - "You're already covered" (`covered`), which stays a draft until permits are on record by lot.
    - The LAN copy's "Try the guided version (preview)" link (`TRY_GUIDE` in
      `app/Dashboard.tsx`), which is removed before launch.

    The Small Project Plan form has a new "Secondary front setback" field, asked when the
    tax-map outline shows a corner lot. The "Draft wording" chip now shows only while something on
    the screen is a draft. *When the staff handoff is built:* restore the `town_judgment` sentence
    that sends the questions to the Code Enforcement Officer.
  - **Rules coverage, answered by the chair 2026-11-02** (`memos/2026-10-30-guided-builder-rules-coverage.md`,
    regenerated; answers in `portal/api/portal_api/standards_overrides.json`, each with its basis):
    the Permitted Buildings numbers are maximums, floor heights included. D2–D6 already say so on
    their pages (BUILDINGS STANDARDS note 1: "Unless otherwise noted, all measurements represent the
    maximum permitted values"), and the chair reads the same rule into D1 and the SD districts. The
    seven unitless floor areas are square feet. D6's side setback: 0–5 ft fits, and up to 15 ft is
    the Board's call (notes 4 and 5, DECISIONS-NEEDED D-0004). Checkable standards: 111 → 315.
  - **For the Board (rules coverage):** whether SD-Rural Highway's 1,000 ft minimum lot width applies
    to every lot or only to lots on Route 1 (its note 1; D-0003); and what building standards, if any,
    apply in SD-Conservation, SD-Campus and SD-Marine, which have no Permitted Buildings table.
  - **For the next Code amendment (from the coverage answers):** put "max." on the bare Permitted
    Buildings numbers, or the "maximum" note on D1's and the SD districts' pages; add "sf" to the
    seven floor areas (D5 Mixed-Use; SD-Highway Commercial; SD-Fabrication); and reconcile §5.14.c.1.a
    (a public mezzanine needs an 18 ft story) with first-floor maximums of 10–16 ft, which allow
    one only in SD-Fabrication.

  For M4 and the redesign:
  - **Projects follow-ups:** the parcel card has no lot drawing (the snapshot drops the parcel's
    outline); the staff lock is a test seam until Milestone 6; the printouts (View) wait for
    Milestone 5.
  - **To check on an iPhone:** with the keyboard up on a long card (materials, walls), the card's
    footer may sit behind the keyboard until it is dismissed.
  - **For the chair (wording):** the work option "A change to a lot, use or building that doesn't fit
    today's Code" (approved as written; applicants no longer pick it, since "Type of project" prints
    from the parts).
  - **Planning Board (next amendment):** Article 5 §1.c lists "Special Use Building", but Article 9
    does not define it; the forms keep it (chair's ruling, 2026-10-23).
  - **O5 (CEO and Planning Board):** plain-language sign-off on the question wording — still open; M7.
  Raised by the screener rulings:
  - **Planning Board (next amendment):** Article 8 §11.b lists no line for additions; the chair ruled
    additions over 10,000 sf are a Large Project Plan — add it to §11.b so the Code says so.
  - **Planning Board / counsel:** Article 3 §8.c.1 says "State Highway (R4 or R5)" while §12.d.1 says
    "State Highway"; the inventory has 14 State-owned S1 segments (Main Street, River Road). The
    portal applies MaineDOT to any State-owned road (chair's ruling).
  - **For counsel:** confirm 30-A M.R.S. §4401(4) applies the 5-year window to dwelling units, which
    the chair's ruling on Article 8 §12.b.3 assumes.
  - **For counsel / typo list:** Article 2 §5.b.1 says "Zoning Map"; the rest of the Code says
    "District Map".
  - **Permit-review app:** its `clocks.json` omits the Residential Companion permit from the §15.d.1
    30-day clock, though §17.c.1 sends that procedure to §15.D (chair's ruling).
- **The adopted v1.0 edition** lacks chrome on physical page 12 and has the old margins; it cannot
  be re-rendered and the next amendment supersedes it.
