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
  application wizards) merged (PR #19); the chair answered the forms
  sheet's six questions on 2026-10-23, and the forms are drafts awaiting approval
  (`memos/2026-10-21-application-forms-for-approval.md`). The redesign (about ten steps, the macOS /
  iOS window, new controls; `specs/2026-10-23-applicant-portal-redesign.md`) is built on
  `portal-design-pass` (PR #20), now as tasks and cards (`specs/2026-10-25-applicant-portal-task-list.md`,
  approved 2026-10-25, after one question at a time, `specs/2026-10-24-applicant-portal-wizard.md`);
  it regrouped the forms into cards, so the sheet was regenerated and every entry is a draft (130
  entries). For M4 and the redesign:
  - **For the chair:** approve the application forms (130 entries), including the steps, the cards
    (which questions share one, each shared card's own question and help, and each question's
    short name on it), the controls, the tiles' icons, which answers "Copy Building 1" copies, and
    the five proposals — the fifth is the new "Which way does the front of the building face?"
    question (and its addition twin), now asked on the walls' card (chair's ruling 2026-10-24).
    Also on the sheet: "Where it joins the road" (was "meets"), and yes/no help reworded for tiles
    ("Choose No if…").
  - **For the chair (forms, from the cards' review):** a building's "What do you call this building?"
    is required and "How many homes will this building have?" is asked of every type (a garage
    too), where the cards brief said "optional" and "homes only" — say which; Your lot's cards
    follow the official form's order (address, deed, then the lot's size), not the brief's.
  - **To check on an iPhone:** with the keyboard up on a long card (materials, walls), the card's
    footer may sit behind the keyboard until it is dismissed.
  - **For the chair (looks, from the cards' finish review):** a desktop's application home shows the
    task list twice (the sidebar and the main card); fields stay 44 px tall for touch, where the
    comp drew 36 px; the property card's spacing; "No password" said twice on sign-in.
  - **For the chair (wording, from the wizard's finish review):** "sf" on the Building Form against "sq
    ft" in "Do I need a permit?"; the street-frontage help points to "Add more detail" before the
    applicant has seen it; "storey" against "story"; the work option "A change … that doesn't fit
    today's Code"; the building-type help mentions the CEO deciding; the lot-size help repeats the
    line under the value ("Measured from the Town's map").
  - **For the chair or the CEO:** check the exterior-finish chip list (clapboard, wood shingle,
    vinyl siding, fibre-cement, brick, stone, …, plus "Other") so its terms match what staff expect.
  - **For the chair (forms):** a building may have up to 10 stories, but the Building Form asks a
    floor height for the first four only — cap stories at 4, or say how taller buildings are
    described.
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
