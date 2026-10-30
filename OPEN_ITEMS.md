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
    order (§11); plan 1 of 6 for the first is `plans/2026-10-30-applicant-portal-guided-builder-1-foundations.md`
    (branch `portal-guided-1-foundations`). Open decisions are its §12.
  - **For the chair (rules coverage):** `memos/2026-10-30-guided-builder-rules-coverage.md` asks 19
    questions the Code leaves open (whether the Permitted Buildings numbers are maximums, seven
    floor areas without a unit, two missing footnotes, three districts without a buildings table),
    plus where the shoreland standards and map live and whether permits on record exist by lot.
  - **For the chair:** may applicants' conversations go to an outside AI (spec decision 14)? Separate
    from D-0025.

  For M4 and the redesign:
  - **Projects follow-ups:** the parcel card has no lot drawing (the snapshot drops the parcel's
    outline); the staff lock is a test seam until Milestone 6; the printouts (View) wait for
    Milestone 5.
  - **No "Add more detail" in projects:** the store can save a section's note, but no screen offers
    one, and the wizard's "too long" message still points to "Add more detail" on a review page that
    is gone. Give notes a place (Check and send is the natural one), or reword that message.
  - **To check on an iPhone:** with the keyboard up on a long card (materials, walls), the card's
    footer may sit behind the keyboard until it is dismissed.
  - **For the chair (looks, from the cards' finish review):** a desktop's application home shows the
    task list twice (the sidebar and the main card); fields stay 44 px tall for touch, where the
    comp drew 36 px; the property card's spacing; "No password" said twice on sign-in.
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
