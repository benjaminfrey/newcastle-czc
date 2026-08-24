# DECISIONS-NEEDED — Newcastle Permit Review

The ledger of everything the Code does not answer. Governed by **CONTRACT.md §7**.

> **The rule.** If the Code does not say whether a number is a minimum or a maximum,
> **do not pick one.** The normalizer fails loudly, the build produces nothing, and the
> question goes to a human. A blank in a Board draft is honest. A guess in a Board draft
> is a defect with legal consequences.

Ids are `D-NNNN`, monotonic, never reused. `Status` ∈ `OPEN` · `RESOLVED` · `WITHDRAWN`.
Entries are appended, newest last, and edited only to fill in **Resolution**.

**Open blocking items: 2 · Open non-blocking items: 18**

---

## D-0001 — SD-Historic · Frontage Zone Setback · unqualified "20 ft"

- **Status:** RESOLVED
- **Raised:** 2026-08-20, by the Article 2 audit that produced this contract
- **Ruleset:** `adopted`
- **District:** `sd-historic` (SD - Historic, source index 6)
- **Field:** `primary_building_placement.frontage_zone_setback` — panel `PRIMARY BUILDING PLACEMENT`, label `Frontage Zone Setback`
- **Raw string:** `20 ft`
- **Why ambiguous:** Article 2 states the number with no `min` or `max`. Every *other* Frontage
  Zone Setback in the Code reads `20 ft min`, but in a form-based code a frontage-zone dimension
  can as easily be a **maximum** (holding buildings *up to* the frontage line) as a minimum. The
  neighbouring pattern is a hint, not evidence, and a wrong pick would put a misstated standard in
  front of the Board under the heading "Required".
- **What we will NOT do:** infer from sibling districts, default to `min`, infer from the field
  name, or emit the value unqualified.
- **Blocking:** **yes** — `ruleset_build` raises `AmbiguousDimension` and writes no
  `districts.json` until this is resolved in `overrides/dimension-qualifiers.json`.
- **Needs:** a human reading the adopted Article 2 SD-Historic spread (both pages).
- **Resolution:** **RESOLVED 2026-08-21 — `min`.** Decided by Ben Frey (Planning Board
  Chair): the frontage zone setback of `20 ft` is a **minimum**. Recorded in
  `overrides/dimension-qualifiers.json` with `decided_by` / `decided_at` / `basis`; the
  constraint carries `source: "override"` so the provenance prints on the worksheet.

---

## D-0002 — SD-Marine · Frontage Zone Setback · unqualified "20 ft"

- **Status:** RESOLVED
- **Raised:** 2026-08-20, by the Article 2 audit that produced this contract
- **Ruleset:** `adopted`
- **District:** `sd-marine` (SD - Marine, source index 11)
- **Field:** `building_placement.frontage_zone_setback` — panel `BUILDING PLACEMENT`, label `Frontage Zone Setback`
- **Raw string:** `20 ft`
- **Why ambiguous:** Same defect as D-0001, in the district that uses the combined
  `BUILDING PLACEMENT` panel rather than the Primary/Accessory pair. SD-Marine also has
  `matrix: null`, so this district is thin on stated standards generally and the one number it does
  give must not be misreported.
- **What we will NOT do:** carry D-0001's answer across. They are two separate districts and must
  be read separately, even if the same person resolves both in the same sitting.
- **Blocking:** **yes** — same failure mode as D-0001.
- **Needs:** a human reading the adopted Article 2 SD-Marine spread (both pages).
- **Resolution:** **RESOLVED 2026-08-21 — `min`.** Decided by Ben Frey (Planning Board
  Chair): the frontage zone setback of `20 ft` is a **minimum**. Recorded in
  `overrides/dimension-qualifiers.json` with `decided_by` / `decided_at` / `basis`; the
  constraint carries `source: "override"` so the provenance prints on the worksheet.
- **Note on scope (read this if D-0002 is ever revisited):** the Chair's answer was given
  as a single statement about the Frontage Zone Setback field, not district by district,
  and was applied to BOTH D-0001 and D-0002. That is in tension with this entry's own
  "What we will NOT do: carry D-0001's answer across." It was applied because the two
  entries share an identical field, label and raw value (`20 ft`), and the decision was
  stated about that field generally. If SD-Marine's combined BUILDING PLACEMENT panel is
  ever read to mean something different, reopen this entry alone.

---

## D-0003 — SD-Rural Highway · Lot Width · footnote "(1)" has no text

- **Status:** OPEN
- **Raised:** 2026-08-20
- **Ruleset:** `adopted`
- **District:** `sd-rhwy` (SD - Rural Highway, source index 9)
- **Field:** `lot_dimensions.width` — panel `LOT DIMENSIONS`, label `Width`
- **Raw string:** `1000 ft min (1)`
- **Why ambiguous:** The number and its qualifier are unambiguous (**1000 ft minimum**). The
  **footnote marker `(1)` has no corresponding footnote text** anywhere in
  `source/article-02-data.json` — the extractor did not capture the spread's footnote block. A
  1000 ft minimum lot width is an unusually large figure, which is exactly the kind of number a
  footnote is likely to qualify or except.
- **Blocking:** **no** — the constraint is emitted with `unresolved: true`, `footnote_refs: ["1"]`,
  and a `notes[]` entry. The worksheet prints the marker and the note so the Board sees that
  something is missing rather than reading a bare 1000 ft.
- **Needs:** the footnote text from the adopted Article 2 SD-Rural Highway spread, transcribed into
  the ruleset build.
- **Resolution:** _(pending)_

---

## D-0004 — D6 Town Center · Side Setback · footnotes "(4)" and "(5)" have no text

- **Status:** OPEN
- **Raised:** 2026-08-20
- **Ruleset:** `adopted`
- **District:** `d6` (D6 - Town Center, source index 5)
- **Field:** `primary_building_placement.side_setback` — panel `PRIMARY BUILDING PLACEMENT`, label `Side Setback`
- **Raw string:** `0 ft min (4) , 5 ft max (5)`
- **Why ambiguous:** Both constraints parse cleanly (**0 ft min**, **5 ft max**), but this is the
  only field in Article 2 where **each bound carries its own footnote**, which strongly suggests the
  two bounds apply under different conditions (e.g. attached vs. detached, or party-wall vs. not).
  Reporting "0 ft min, 5 ft max" without those conditions could tell the Board a building may sit
  anywhere in a 0–5 ft band when the Code may mean something narrower.
- **Blocking:** **no** — emitted with `unresolved: true` and `footnote_refs: ["4","5"]`.
- **Needs:** the footnote text from the adopted Article 2 D6 spread.
- **Resolution:** _(pending)_

---

## D-0005 — SD-Highway Commercial · Building Orientation · "Parallel within 200 of road" (unit omitted)

- **Status:** OPEN
- **Raised:** 2026-08-20
- **Ruleset:** `adopted`
- **District:** `sd-hwy` (SD - Highway Commercial, source index 8)
- **Field:** `design_standards.building_orientation` — panel `DESIGN STANDARDS`, label `Building Orientation`
- **Raw string:** `Parallel within 200 of road`
- **Why ambiguous:** The distance carries **no unit**. Context makes feet overwhelmingly likely, and
  every other distance in Article 2 is in feet — but "overwhelmingly likely" is not the standard for
  a number that will be printed to a Board as a requirement.
- **Blocking:** **no** — `DESIGN STANDARDS` is a *prose* panel (CONTRACT.md §4.1.3), so this value
  is carried through **verbatim** in `panels[]` and is never parsed into a `constraints[]` entry.
  The worksheet prints the sentence exactly as the Code writes it, which is the honest rendering.
  It is logged here so nobody later "helpfully" normalizes it to `200 ft`.
- **What we will NOT do:** append `ft`.
- **Needs:** confirmation against the adopted Article 2 SD-Highway Commercial spread; if the Code
  itself omits the unit, that is a **Code defect worth reporting to the Planning Board**, not
  something this app repairs.
- **Resolution:** _(pending)_

---

## D-0006 — "Business day" statutory clocks have no Town/State holiday calendar

- **Status:** RESOLVED
- **Raised:** 2026-08-21, by `app/deadlines.py` (W3 case dashboard)
- **Ruleset:** `adopted`
- **Field:** Article 7 §5.c.3 (notice mailed within 7 business days of submission) and
  §8.f.1 (decision filed with the Town Clerk within 5 business days) — the only two
  clocks the Code states in **business days** rather than calendar days.
- **Why ambiguous:** Article 7 does not define "business day" anywhere in the extracted
  text (no definition node matched `business day` in `rulesets/adopted/articles.json`).
  `engine/deadlines.py:add_business_days()` originally treated Saturday/Sunday as the
  only non-business days — no Town office closure or State holiday calendar was
  incorporated. A deadline that spans a recognized holiday would be computed too early
  against the Code's likely intent.
- **What we will NOT do:** silently assume a Newcastle-specific closure list beyond
  what a verified Maine statute establishes, or round in either direction to "be safe."
- **Blocking:** no — both real clocks still computed and displayed correctly even
  before this was resolved; now they compute against the corrected calendar.
- **Resolution (2026-08-21):** Verified the governing statute directly against the
  Maine Legislature's own statute pages: **4 M.R.S. §1051, "Legal holidays"**
  (legislature.maine.gov/statutes/4/title4sec1051-1.html; cross-checked against
  mainelegislature.org's mirror), current through its most recent amendment, **PL
  2021, c. 676, Pt. A, §2** (the amendment that added Juneteenth). This is the one
  statute in Maine law that enumerates "legal holidays" by name — Title 1 (this
  item's original guess) has no such list; §1051 lives in Title 4 (Judiciary) because
  its primary sentence is "Court may not be held on ...". Read narrowly, §1051 (a)
  forbids court sessions on the 12 listed dates and (b) *permits, but does not
  require*, "public offices in county buildings" to close — it says nothing about
  municipal/town offices. Applying it to Newcastle's Town Clerk is therefore the best
  available inference, not a textual command; see **D-0010** for that residual gap,
  which stays open.
  All 12 holidays (fixed-date and floating, including the statute's own
  Sunday-observed-Monday rule) are now encoded as data in
  `engine/deadlines.py` (`maine_legal_holidays()` / `maine_legal_holiday_label()`),
  cited inline to §1051, and wired into `is_business_day()`. `app/deadlines.py`
  re-exports both helpers. Both real Shattuck clocks were recomputed against the
  corrected calendar and both land on a *different* date than the weekend-only
  arithmetic gave:
  - §5.c.3 notice-mailed: 7 business days from 2025-10-02 was computed as
    **2025-10-13** (a Monday) under weekend-only arithmetic; 2025-10-13 is
    **Indigenous Peoples Day** (§1051), so the corrected due date is
    **2025-10-14**.
  - §8.f.1 decision-filed-with-clerk (which starts the §23 appeal window): 5
    business days from 2025-12-18 was computed as **2025-12-25** (Christmas Day
    itself) under weekend-only arithmetic; the corrected due date is
    **2025-12-26**.
  Both corrections are pinned as regression tests in `tests/test_deadlines.py`
  (`test_add_business_days_matches_the_real_shattuck_notice_window`,
  `test_shattuck_reconstruction_decision_filed_and_appeal_are_honestly_pending`, and
  the parametrized `test_maine_legal_holidays_2025_matches_4_mrs_1051`) and as
  `--selftest` check 10, so a future edit cannot silently regress the calendar back
  to weekend-only arithmetic. The dashboard and case-detail deadline table now both
  carry an accurate note describing the calendar and pointing to D-0010 for what it
  does not cover (previously only the case-detail page carried a note at all, and it
  described the pre-fix weekend-only behavior — that inaccuracy is corrected here,
  not repeated).
  **Thanksgiving note:** §1051 names no formula for Thanksgiving ("any day designated
  for the annual Thanksgiving"); it is encoded as the 4th Thursday in November,
  matching both the federal legal holiday (5 U.S.C. §6103) and Maine's own
  uninterrupted gubernatorial-proclamation practice. This is a documented inference,
  not a blocking ambiguity — flagged again under D-0010's scope.

---

## D-0007 — CEO-track "completed application" vs. the recorded receipt date

- **Status:** OPEN
- **Raised:** 2026-08-21, by `app/deadlines.py` (W3 case dashboard)
- **Ruleset:** `adopted`
- **Field:** Article 7 §10.d.4 (Small Project Plan, CEO decision) and §11.d.3 (Large
  Project Plan, CEO track) both start their clock "after receiving **a completed
  application**" — not simply "after receiving an application," the way §12.e.3
  (Subdivision) and §11.d.4.a (Large Project Plan, PB track) do.
- **Why ambiguous:** Subdivision has an explicit completeness-determination step
  (§12.e.3, its own 30-day clock) with a date this app can record
  (`case_milestones.kind = 'completeness_determined'`). The CEO-only tracks (§10, §11
  CEO branch) name no equivalent step or determination anywhere in the extracted
  Article 7 text — it is not clear whether "a completed application" is meant to be
  the same moment as `cases.received_at`, or an undocumented, CEO-discretion
  determination that could fall on a later date.
- **What we will NOT do:** silently treat "received" and "completed" as identical for
  these two tracks the way it's explicit for Subdivision.
- **Blocking:** no — as shipped, `engine/deadlines.py`'s `small_project_decision` and
  `large_project_ceo_decision` clocks anchor on `submitted_at` (the D-0008-ranked
  receipt date) like every other clock; they do **not** yet look for a recorded
  `completeness_determined` milestone the way the Subdivision/§12 track does, and
  there is no `anchor_provisional` flag distinguishing "anchored to a real
  completeness determination" from "anchored to bare receipt" for these two tracks.
  That distinction — a real refinement, not a guess — is exactly what's still needed
  before this can be marked resolved; until then the printed due date for these two
  clocks should be read as "from receipt," full stop.
- **Needs:** confirmation from the CEO/Planner whether these two tracks in practice
  ever have a distinct completeness moment worth recording, or whether "received" is
  in practice "completed" for a Small/Large Project Plan filed at the counter.
- **Resolution:** _(pending)_

---

## D-0008 — Which recorded fact is Article 7's "receiving" / "submission of an application"?

- **Status:** OPEN
- **Raised:** 2026-08-21, by `engine/deadlines.py` (W3 statutory clock engine)
- **Ruleset:** `adopted`
- **Field:** every clock in `rulesets/adopted/clocks.json` whose `start_event` is
  "submission of an application" / "receiving an application" (§5.c.3 notice, §10.d.4,
  §11.d.3, §11.d.4.a, §12.e.3, §18.d.1, §19.c.1) — i.e., nearly every clock's day-zero.
- **Why ambiguous:** This project now records **two different dates** that could each
  read as "when the application was submitted": `cases.received_at` (the Town's formal
  receipt, mirrored from the `case_milestones.kind = 'application_received'` row added
  in `0003_case_lifecycle.sql`) and the `application_dated` milestone (the date printed
  on the application form itself). The real Shattuck subdivision record shows these are
  not necessarily the same day — an application can be dated, then updated, then
  actually received later, or received before being fully dated/signed.
- **What we will NOT do:** treat "dated" and "received" as interchangeable, or silently
  prefer one without saying so.
- **Blocking:** no — `engine/deadlines.py`'s `CaseFacts` prefers `cases.received_at`
  and falls back to the `application_dated` milestone only when `received_at` is not
  yet recorded, tagging which source it used (`submitted_at_source`) so the case
  dashboard/detail views can print which date a clock actually ran from rather than
  presenting a bare, unsourced date.
- **Needs:** confirmation from the CEO/Planner that "date received" (not "date on the
  form") is what Article 7 means by "submission," for every track that phrase appears
  in.
- **Resolution:** _(pending)_

---

## D-0009 — §5.c.3's notice clock cannot always be met as literally written

- **Status:** OPEN
- **Raised:** 2026-08-21, by `ruleset_build/build_clocks.py` (W3 statutory clock engine)
- **Ruleset:** `adopted`
- **Field:** Article 7 §5.c.3 (notice mailed within 7 business days of submission).
- **Why ambiguous:** §5.c.3 requires the mailed notice to include, "if applicable, time,
  date and location of first scheduled meeting" — but for every hearing-based track
  (Subdivision, the Large Project Plan Planning Board track, Special Permit, Variance)
  no hearing date exists yet 7 business days after submission; the hearing itself isn't
  scheduled until later in the same process this notice is supposed to announce. The
  Code does not say what a compliant notice looks like when that information is
  genuinely unknowable within the stated window, nor whether the 7-day clock is meant
  to restart once a hearing date is actually set.
- **What we will NOT do:** infer a second, unstated notice deadline, or quietly drop
  the "time, date and location" requirement from the clock's description to make the
  window look satisfiable.
- **Blocking:** no — the `notice_mailed` clock is still computed and shown (mailing
  *something* within 7 business days is checkable); this ambiguity is carried as a
  `notes` string on the clock so the dashboard/detail views can show it next to that
  row rather than presenting a false sense of precision.
- **Needs:** confirmation from the CEO/Planner of Newcastle's actual practice — does a
  first notice go out at 7 business days naming only what's known, followed by a
  second (re-)notice once a hearing date is set? The real Shattuck record's own
  re-notice (notice mailed ahead of an Oct 16 meeting; hearing rescheduled to Nov 20
  and RE-noticed) is consistent with that practice, but the Code doesn't say so.
- **Resolution:** _(pending)_

---

## D-0010 — Newcastle Town Office closures beyond the 4 M.R.S. §1051 statutory list

- **Status:** OPEN
- **Raised:** 2026-08-21, by `engine/deadlines.py` while resolving D-0006
- **Ruleset:** `adopted`
- **Field:** Article 7 §5.c.3 and §8.f.1 (the same two business-day clocks as D-0006).
- **Why ambiguous:** `is_business_day()` now excludes the 12 Maine legal holidays
  enacted in 4 M.R.S. §1051 (see D-0006's resolution) — but that statute's own text
  only *permits* county public offices to close on those dates and says nothing about
  municipal offices at all. Whether Newcastle's Town Office, in actual practice,
  (a) closes on all 12 of these dates, (b) closes on additional days not in the
  statute (a common municipal practice is also closing the day after Thanksgiving, or
  a half-day before Christmas), or (c) stays open on some subset of them, is not
  established by anything in this project's source material.
- **What we will NOT do:** assume Newcastle's practice is identical to the state list
  just because it is the only verified list available, or invent additional closure
  days from general knowledge of "typical" town office practice.
- **Blocking:** no — the §1051 statutory floor is a real improvement over weekend-only
  arithmetic and is now correctly applied; this item tracks only the narrower,
  town-specific residue. The dashboard and case-detail deadline table both carry a
  standing note pointing here.
- **Needs:** Newcastle's Town Office's own posted holiday/closure schedule (it need
  not match the State list exactly), to compare against `engine/deadlines.py`'s
  `maine_legal_holidays()` and add or remove specific dates if it diverges.
- **Resolution:** _(pending)_

---

## D-0011 — Is the Board of Appeals, acting as "Appellate Authority" under §23, a
"Permitting Authority" for §8.d.1 auto-approval purposes?

- **Status:** OPEN
- **Raised:** 2026-08-21, by `ruleset_build/build_clocks.py` (F3 — the three missing
  §23 appeal-track clocks)
- **Ruleset:** `adopted`
- **Field:** Article 7 §23.d.2 (appeal review + hearing, 30 days) and §23.d.3 (appeal
  decision, 45 days), now the `administrative_appeal_hearing` and
  `administrative_appeal_decision` clocks.
- **Why ambiguous:** Article 9 defines **"Permitting Authority"** as "A person or
  board granted the authority to conduct project review and approval, in accordance
  with this Code." §8.d.1's auto-approval consequence is written in terms of a
  "Permitting Authority['s]" failure to hold a hearing or take final action. §23.d
  instead names the deciding body the **"Appellate Authority"** — a term that appears
  nowhere else in the extracted Code text and is never itself defined. Textually, an
  appeal is a review OF a prior review, not itself "project review and approval" of
  an application in the first instance, so whether the defined term "Permitting
  Authority" was meant to reach the undefined "Appellate Authority" is genuinely open.
- **What we will NOT do:** infer an answer from the fact that the Board of Appeals is
  also literally a "board," or treat "Appellate Authority" and "Permitting Authority"
  as synonyms merely because both bodies happen to be the Board of Appeals in most
  cases §23 covers.
- **Blocking:** no — per this task's own governing instruction (surface auto-approval
  risk conservatively rather than narrow it), `administrative_appeal_hearing` and
  `administrative_appeal_decision` are built WITH `failure_consequence` attached,
  i.e. assuming the answer is yes. If town counsel later determines the answer is no,
  these two clocks' `failure_consequence` should be set to `null` and their `notes`
  updated — a one-field change, not a rebuild.
- **Needs:** town counsel's reading of whether §8.d.1's "Permitting Authority" term
  reaches the Board of Appeals' appellate function under §23, or a Code amendment
  that names the term explicitly.
- **Resolution:** _(pending)_

---

## D-0012 — Does §8.d.1 auto-approval attach to the §12.e.3 subdivision completeness
determination, and how should an app surface risk when it does not?

- **Status:** OPEN
- **Raised:** 2026-08-21, by `ruleset_build/build_clocks.py` (F1 — the subdivision
  auto-approval clock reachability defect)
- **Ruleset:** `adopted`
- **Field:** Article 7 §12.e.3 (`subdivision_completeness`, 30 days from receiving the
  application to determine completeness).
- **Why ambiguous:** §12.e.3 says the Planning Board "must determine if the
  application is complete and ready for review at a public hearing" — a completeness
  determination, textually distinct from both "hold a public hearing" and "take final
  action" (contrast §11.d.4.a's Large Project Plan completeness clock, which says the
  Planning Board must "review the application for completeness AND HOLD A PUBLIC
  HEARING" in the same sentence — §8.d.1 attaches there without this ambiguity).
  Whether a completeness determination is close enough to "taking final action on an
  application" for §8.d.1 to reach it is a legal judgment call this build does not
  make; `subdivision_completeness.failure_consequence` stays `null`, unchanged.
- **What we will NOT do:** attach the §8.d.1 text to this clock to "solve" the
  reachability problem below by fiat, or silently assume the Board's practice of
  determining completeness at the same meeting as the decision means the two are
  legally fused into one act.
- **Blocking:** no — but flagging a real, load-bearing consequence for the record:
  Newcastle determines subdivision completeness AT THE SAME MEETING as the decision
  itself (the real Shattuck record, p.13), so `completeness_at` is often never
  recorded as an EARLIER, distinct milestone while an application merely sits
  unactioned. Because `subdivision_hearing_decision` (§12.e.5, the clock that DOES
  carry `failure_consequence`) starts from `completeness_at`, a stalled subdivision
  with no meeting yet held shows no §8.d.1 risk at all today, even though the
  Board's own FIRST duty (§12.e.3, the completeness determination) is overdue. This
  app's stated posture is to surface risk conservatively; an engine-level "this
  case has an overdue statutory duty" signal, independent of whether that duty is
  itself characterized as §8.d.1-bearing, would close this gap without deciding the
  underlying legal question (recorded here for whoever owns `engine/deadlines.py`'s
  `_evaluate_clock`/`open_deadlines`, not decided by this data-only file).
- **Needs:** town counsel's reading of §8.d.1 against §12.e.3, or a Code amendment
  restating §12.e.3 in "hold a hearing"/"final action" terms if that was the intent.
- **Resolution:** _(pending)_

---

## D-0013 — Should the §8.f.5 / §2.e.1 plan-recording clocks also reach
`special_permit` decisions, alongside the `large_project_plan` extension made for F9c?

- **Status:** OPEN
- **Raised:** 2026-08-21, by `ruleset_build/build_clocks.py` (F9c — recording-conflict
  clock applicability)
- **Ruleset:** `adopted`
- **Field:** `subdivision_plat_recorded_6mo` (§8.f.5/§12.j.1) and
  `subdivision_plat_recorded_90d` (§2.e.1).
- **Why ambiguous:** F9c's own text names `large_project_plan` as the gap this build
  closes ("a large_project_plan creating building groups gets NEITHER recording
  clock"), and `applies_to` on both clocks was widened accordingly. §8.f.5's own text
  — "Plans approved and signed by the Planning Board must be recorded ... within six
  months" — is not limited to Large Project Plan or Subdivision; §18.d.2 also has the
  Planning Board deciding Special Permits ("the Planning Board must make a decision
  ... approve, approve with modifications, deny"), which reads as squarely within
  §8.f.5's own words too. Whether that was the intended reach of §8.f.5, or whether
  "approved and signed" implies a recordable PLAT/plan document that a Special
  Permit decision does not necessarily produce, is not settled by the extracted text.
- **What we will NOT do:** widen `applies_to` to `special_permit` on our own reading
  without it being asked for, given the explicit F9c instruction named only
  `large_project_plan` — logging the adjacent question instead of silently deciding
  it either way.
- **Blocking:** no.
- **Needs:** confirmation of whether a Special Permit decision ordinarily produces a
  recordable plan/plat at all in Newcastle's practice, and if so, whether §8.f.5 was
  meant to reach it.
- **Resolution:** _(pending)_

---

## D-0014 — §12.e.6's findings-of-fact clock start_event (`decision_at`) is an
inference, not stated in the text

- **Status:** OPEN
- **Raised:** 2026-08-21, by `ruleset_build/build_clocks.py` (F12 — undocumented
  clock anchor)
- **Ruleset:** `adopted`
- **Field:** `subdivision_findings_issued` (§12.e.6).
- **Why ambiguous:** §12.e.6's full text is "Within 30 days, the Planning Board must
  issue findings of fact and provide a copy to the applicant and the Office of the
  Code Enforcement Officer." It states a day count but never states what the 30 days
  run FROM — no "of the decision," "of the hearing," or "after X" phrase appears.
  This clock's `start_event` is `decision_at`, chosen because §12.e.6 immediately
  follows §12.e.5 (the hearing + decision clock) in the Code's own numbering and
  findings of fact are the natural next step after a decision — a plausible,
  contextual inference, not a textual certainty. CONTRACT.md §7 asks that exactly
  this kind of pick be logged, even when it is not blocking and even though (unlike
  D-0001/D-0002's dimensional qualifiers) there is no realistic alternative anchor
  among this case's other recorded events.
- **What we will NOT do:** silently ship the inferred anchor without a record of it
  being an inference, or treat "the only anchor that makes sense" as equivalent to
  "the anchor the Code states."
- **Blocking:** no — `decision_at` is the only event in this case's timeline that
  could plausibly start a findings-of-fact clock (nothing later or unrelated would
  make sense), so this is logged for the record rather than because a different
  choice is live under consideration.
- **Needs:** no action expected; recorded so a future reader of `clocks.json` sees
  the anchor was chosen, not transcribed, if the Code's own numbering ever changes
  around §12.e.5/§12.e.6 in a way that makes the inference less obviously right.
- **Resolution:** _(pending)_

---

## D-0015 — §2.e.1's plan-recording duty names no actor; classified `applicant_duty`
by inference from its parallel §12.j.1/§8.f.5 clock, not from its own text

- **Status:** OPEN
- **Raised:** 2026-08-21, by `ruleset_build/build_clocks.py` (2026-08 clock-taxonomy
  repair round — classifying every clock's `duty_kind` from its own governing
  sentence)
- **Ruleset:** `adopted`
- **Field:** `subdivision_plat_recorded_90d` (§2.e.1).
- **Why ambiguous:** §2.e.1's full text is "Plans containing lots, virtual lot lines,
  or building groups must be recorded in the Lincoln County Registry of Deeds within
  90 days of the granting of an approval, variance, or a permit." — passive voice,
  no actor named. Its sibling clock, `subdivision_plat_recorded_6mo` (§12.j.1, also
  §8.f.5), states the SAME underlying act (recording an approved plan) with an
  explicit actor: "The applicant will file a copy of the approved subdivision
  plat...". This clock's `duty_kind` was set to `applicant_duty` by inference from
  that parallel — the same act, the same document, the same registry — not because
  §2.e.1 itself says who records. A plausible reading, not a textual certainty.
- **What we will NOT do:** treat the parallel to §12.j.1/§8.f.5 as equivalent to
  §2.e.1 stating its own actor, or silently classify this as `municipal_duty` (which
  would incorrectly make a missed applicant recording count toward the Town's own
  §8.d.1 auto-approval exposure — it never does, either way, since this clock
  carries no `failure_consequence`, but the `duty_kind` label itself should not
  overstate what the text supports).
- **Blocking:** no — `duty_kind=applicant_duty` already produces the conservative,
  correct behavior either way this resolves (an applicant's own recording failure is
  never the Town's failure, and `municipal_duty` is the only value
  `presents_auto_approval_risk()` reads), so nothing downstream depends on this
  question being settled before release.
- **Needs:** confirmation (town counsel, or Newcastle's own recording practice) that
  §2.e.1's recording duty runs to the applicant, as it explicitly does under
  §12.j.1/§8.f.5, and not to the Town.
- **Resolution:** _(pending)_

---

## D-0016 — Unmarked `case_milestones.supersede_reason` (legacy/NULL rows) defaults
to the CONSERVATIVE ("correction") reading, not "reschedule"

- **Status:** OPEN
- **Raised:** 2026-08-21, by `engine/deadlines.py` while fixing N3 (adversarial
  re-review of the W3b deadline-engine repairs)
- **Ruleset:** n/a — this is an engine/data-model decision, not a Code ambiguity
- **Field:** `case_milestones.supersede_reason` (0007_supersede_reason.sql);
  consumed by `engine.deadlines._is_genuine_history_entry()` /
  `_first_satisfying_occurrence()`.
- **Why ambiguous:** a superseded `case_milestones` row can be superseded for two
  legally different reasons that N3 requires this app to tell apart --
  **"reschedule"** (the row genuinely happened and satisfied whatever duty was live
  at the time; only superseded because, e.g., a hearing moved and a fresh notice went
  out) versus **"correction"** (the row was factually wrong -- a typo, a misread date
  -- and never really happened as recorded, so it must not satisfy anything).
  `app.cases.record_dates` now REQUIRES an explicit `supersede_reason` on every new
  write that supersedes a row (CONTRACT.md §1 S7 -- never inferred), but a row
  superseded before that requirement existed (or, in principle, one written some
  other way that skips it) has `supersede_reason = NULL`. The data itself cannot say
  which of the two the operator meant. This app picked the CONSERVATIVE default for
  that NULL case -- treat it exactly like an explicit `"correction"` (excluded from
  satisfying-occurrence credit) -- rather than defaulting to `"reschedule"` (which
  would silently resurrect the exact N3 defect for every unmarked legacy row: an
  unverified earlier date manufacturing compliance the record cannot actually back
  up).
  - **CORRECTED RISK ASSESSMENT (2026-08-21, HARD-FINAL round ledger correction).**
    This entry originally called the "correction" default's downside merely
    "UNDER-credit[ing] a duty that really was performed on time (recoverable --
    an operator can go back and supply the missing reason)". That framing is
    accurate ONLY for an `applicant_duty` clock (no `failure_consequence`; a
    missed date there is never the Town's own failure and never reaches
    `presents_auto_approval_risk()`) -- and understated even there, since
    "recoverable" describes how the DATA can be fixed, not what happens on
    screen in the meantime. It is flatly WRONG, not merely understated, for a
    `municipal_duty` clock carrying the §8.d.1 auto-approval consequence
    whose SATISFYING event is itself a superseded `case_milestones` row --
    e.g. `hearing_opened_at`/`hearing_closed_at`/`decision_at`/
    `decision_filed_at`/`appeal_hearing_opened_at`/`appeal_hearing_closed_at`/
    `appeal_decision_at`, every one of them a real field
    `_first_satisfying_occurrence()` can be asked about. Under-crediting THAT
    field does not sit quietly waiting for an operator to notice: it can
    immediately flip the clock to MISSED, set `auto_approval_alert`, and make
    `presents_auto_approval_risk()` return True, which (per this app's own
    dashboard/case-detail wiring) fires the case-wide auto-approval banner --
    a claim, in the Board's own working document, that a permit auto-approved
    by operation of law when the Town in fact met its deadline on time. That
    is this app's single most expensive failure mode (a false legal
    conclusion with real practical consequences if acted on), not a "cheap,
    recoverable" data-entry nit -- "an operator can go back and supply the
    missing reason" describes how the alarm eventually gets FIXED, not
    evidence that showing it was free.
  - This does NOT change the chosen default. The alternative -- defaulting
    unmarked rows to `"reschedule"` -- risks the mirror-image failure: silently
    crediting compliance nobody has verified, which can suppress a GENUINE
    §8.d.1 auto-approval risk on a case where the duty really was missed, with
    no alarm at all to prompt anyone to look. A false alarm a human can see
    and immediately investigate is safer, on this app's own stated conservative
    posture ("surface the risk... even if the precise legal trigger is later
    narrowed" -- `presents_auto_approval_risk()`'s own docstring), than a false
    silence nothing prompts anyone to catch. But the CHOICE being defensible is
    a different claim than the COST being low, and this entry should not have
    conflated the two.
- **What we will NOT do:** infer the reason from the two rows' dates, notes, or
  proximity, or default to `"reschedule"` on the theory that most supersessions in
  practice probably are reschedules, or describe the conservative default as
  low-cost on a `municipal_duty`/§8.d.1 clock -- it is the safer of two costly
  options, not a cheap one.
- **Blocking:** no — this checkout has zero real case rows (same as every migration
  before it), so no row is affected today; this governs future legacy data only,
  should the reason ever go unrecorded some other way than record_dates' own
  enforced-at-write-time requirement. The corrected risk assessment above raises
  the stakes of getting this right once real data exists, but does not itself
  block anything in this checkout.
- **Needs:** no action expected unless a future integration path (a data import, a
  direct DB edit) can create a superseded row that bypasses `app.cases.record_dates`
  validation -- if that path is ever built, it should carry the same requirement,
  not rely on this default. Separately: an operator-facing surface (dashboard or
  case-detail) that specifically flags "this auto-approval alarm rests on an
  under-credited superseded row with no recorded reason" would let staff
  distinguish this failure mode from a genuine missed deadline at a glance --
  not built as part of this correction, logged here as a follow-on worth
  scoping.
- **Resolution:** _(pending)_

---

## D-0017 — `STALE_HEARING_WARNING_DAYS = 180` (F2 second arm) is an
operational placeholder, not a Code-stated limit

- **Status:** OPEN
- **Raised:** 2026-08-21, by `engine/deadlines.py` while fixing F2 (adversarial
  re-review round 2 of the deadline engine: the `hearing_closed_at` chain gap)
- **Ruleset:** n/a — this is an engine/data-model decision, not a Code ambiguity
  over a Article 2 dimension; it concerns Article 7 §6.e.1/§8.d.1 timing.
- **Field:** `engine/deadlines.STALE_HEARING_WARNING_DAYS`, consumed by
  `_attach_start_not_recorded_alerts()`'s F2 second arm.
- **Why ambiguous:** three §8.d.1-bearing decision clocks (`large_project_pb_
  decision`, `special_permit_decision`, `variance_decision`) and
  `administrative_appeal_decision` all start from a "hearing closed" event
  (`hearing_closed_at` / `appeal_hearing_closed_at`). No clock in
  `clocks.json` is ever satisfied by either field — the sibling hearing
  clocks are satisfied by the matching "*_opened_at" field instead — so F4's
  original predecessor-chain machinery can never find a predecessor for
  these four clocks, and a hearing that opened and was simply never closed
  produces total silence forever: PENDING_START, no `auto_approval_alert` (no
  `due_date` to compare), and, before this fix, no `start_not_recorded_alert`
  either. Article 7 §6.e.1 explicitly permits the applicant and Permitting
  Authority to extend "the time limit required to make a decision" by mutual
  agreement, and §6.e.2 only requires that agreement be in writing — the Code
  states NO outer bound on how long such an extension may run. An engine that
  is honest about that (CONTRACT.md's framing rule) cannot compute a MISSED
  status or a `due_date` off an open-ended continuance; but total permanent
  silence is not what §6.e.1 contemplates either, and all four clocks carry
  the §8.d.1 auto-approval consequence once they start. This app picked
  **180 days** as the threshold past which an open, unclosed hearing
  surfaces a `start_not_recorded_alert` (never a MISSED status, never an
  `auto_approval_alert`, never a due_date) prompting a human to confirm it is
  a genuine continuance rather than a forgotten one. 180 days is roughly six
  times the longest ordinary hearing-to-decision window any of these four
  clocks itself carries (45 days, `special_permit_decision`/
  `variance_decision`) — chosen as conservative headroom against flagging an
  ordinary in-progress continuance, not derived from any Code text.
- **What we will NOT do:** treat 180 days as a legal maximum, let it produce
  a MISSED status, a `due_date`, or an `auto_approval_alert`, or claim the
  number came from the Code.
- **Blocking:** no — the alert is purely additive visibility (F4's existing
  posture); no case's computed status, `auto_approval_alert`, or
  `auto_approval_risk` changes because of this threshold, only whether a
  `start_not_recorded_alert` is attached to an already-honest PENDING_START
  clock.
- **Needs:** a human (town counsel, or the Planning Board's own practice) to
  confirm 180 days is a reasonable operational trigger, or to name a
  different one — and, separately, whether §6.e.1 should ever get its own
  recordable extension (Finding 3 of this review round; out of this task's
  scope, tracked there).
- **Resolution:** _(pending)_

---

## D-0018 — `_column_split()` mis-columns a mid-line color-break span,
corrupting two Article 7 §5/§6 items (discovered, NOT fixed, by the Finding 4
table-extraction pass)

- **Status:** OPEN
- **Raised:** 2026-08-21, by `ruleset_build/extract_adopted.py` while fixing
  Finding 4 (Table 7.1 extraction). Not itself a Table 7.1 defect — found only
  because fixing the table-caption leak made this SEPARATE, pre-existing
  corruption of the immediately adjacent item visible on its own for the
  first time (it used to be buried inside the much larger table-leak blob).
- **Ruleset:** `adopted` (`rulesets/adopted/articles.json`)
- **Nodes:** `art7.5.d.1` (§5.d.1, PUBLISHED NOTICE) and `art7.6.e.2` (§6.e.2,
  CONTINUANCE) — both on PDF page 82.
- **Why:** `extract_adopted._column_split()` picks the page's 2-column
  boundary as the single largest gap among the DISTINCT x-values body spans
  START at. On PDF page 82, one body line ("...published on the Town of
  Newcastle's web page and in a newspaper of general circulation.") is split
  into two PDF spans at the SAME y (same visual line) because the run "and in
  a " renders in the pure-black color variant this module's own
  `_BODY_COLORS` comment already documents ("~585 spans across 49 pages
  render in pure black instead — a PDF-authoring artifact") — a color-only
  break forces a new span, whose x (220.7) is a MID-LINE continuation
  position, not a real column-start x. `_column_split` doesn't know the
  difference: it sees x=220.7 as just another candidate x, and the gap
  85→221 (136pt) happens to be the page's single largest gap, so the split
  lands at x=153 instead of near the true ~290-310pt boundary between the
  page's real two columns. Every span with x ≥ 153 — including this stray
  221 one — is then bucketed into the "right column," so in reading order it
  sorts in AMONG that column's lines by y (355.1), landing directly after
  §6.e.2's own real line (y=349.1, "Time limit extentions shall be recorded
  in writing.") and getting appended to it as a continuation. Net effect:
  `art7.5.d.1` LOSES "and in a " (now reads "...web page newspaper of
  general circulation.", missing a word run) and `art7.6.e.2` GAINS a bogus
  trailing "and in a" it never had (now reads "...recorded in writing. and
  in a").
- **Scope, not yet swept:** this is a column-split GAP-COMPUTATION defect,
  not a table-handling defect (out of Finding 4's scope) — it could in
  principle recur on any page carrying one of the ~585 pure-black-variant
  spans if that span's x ever produces the page's single largest gap. Not
  audited beyond the one instance Finding 4's work surfaced; a proper fix
  likely needs `_column_split` (or `_lines`) to recognize a same-y run as one
  logical line before gap-clustering x-starts, not a one-off patch to these
  two nodes.
- **What we will NOT do:** hand-edit `art7.5.d.1`/`art7.6.e.2`'s text in the
  committed JSON (CONTRACT.md's "fix it in the extractor, not by hand-editing
  the build output" posture, same rule Finding 4 itself was built under), or
  silently absorb "and in a" into whichever node happens to be open when the
  extractor is next touched.
- **Blocking:** no — neither node is cited by any `clocks.json` entry
  (verified: every adopted-side clock citation is Article 7 §2/§5/§6/§8/§11-
  §19/§23, and the two affected subsections, §5.d and §6.e, are cited by no
  clock's `source_text` match), so this does not touch the deadline engine's
  computed output.
- **Needs:** a human decision on whether to fix `_column_split`'s gap
  heuristic now (risk: it is used across the ENTIRE adopted-PDF extraction,
  2416 nodes / 8 articles — a change here needs its own dedicated
  re-verification pass, not a Finding-4-scoped patch) or defer it to a
  dedicated pass.
- **Resolution:** _(pending)_

---

## D-0020 — §5.c.3's notice-mailing duty is passive voice too, exactly like
§2.e.1 (D-0015) — logged now for consistency, though better-evidenced

- **Status:** OPEN
- **Raised:** 2026-08-21, by `ruleset_build/build_clocks.py` (HARD-FINAL round,
  ledger-consistency correction)
- **Ruleset:** `adopted`
- **Field:** `notice_mailed` (§5.c.3).
- **Why ambiguous:** §5.c.3's own operative sentence, "Notices must be mailed
  within 7 business days of submission of an application," is passive voice
  with no actor stated — read in isolation, exactly the same shape as §2.e.1
  ("Plans containing lots, virtual lot lines, or building groups must be
  recorded... within 90 days..."), which THIS project's own D-0015 entry
  logged as an open question rather than silently resolving. This clock's
  `duty_kind_note` instead declared the applicant-as-mailer reading "not
  genuinely arguable" and logged nothing — an inconsistent application of the
  D-0015 rule (the same passive-voice-actor inference, held to two different
  disclosure standards depending on how confident the transcriber felt about
  it, which is exactly the kind of guess CONTRACT.md §1 S7 says must be
  collected, not resolved, regardless of how strong the inference feels in
  the moment).
- **Why this one IS better-evidenced than D-0015 (not a reason to skip
  logging it — a reason the two entries can reach different Resolutions):**
  §5.c.3's own text, in full, is "The applicant must develop a notice
  containing pertinent information about the project, including: ... Notices
  must be mailed within 7 business days of submission of an application." —
  the passive mailing sentence is the IMMEDIATELY NEXT sentence, in the SAME
  subsection, right after "the applicant" is named as the one who develops
  the very notice that then "must be mailed." §5.c.4, in the same breath,
  adds "Applicant must provide copy of mailing receipt to the Office of the
  Code Enforcement Officer" — a receipt only the mailer would be handed.
  D-0015's inference, by contrast, borrows an actor from an entirely
  SEPARATE, only-parallel provision (§12.j.1/§8.f.5, a different section
  about the same underlying act — recording an approved plan — not the same
  subsection at all). Both readings land on `applicant_duty`; this one rests
  on stronger textual footing.
- **What we will NOT do:** treat "well-evidenced" as a reason not to log the
  ambiguity (the D-0015 standard this project set for itself does not carry
  a confidence exception), or reclassify this as `municipal_duty` (which
  would incorrectly expose a missed applicant mailing to the Town's own
  §8.d.1 auto-approval exposure — it never does either way, since this clock
  carries no `failure_consequence`, but the `duty_kind` label itself should
  not overstate what the text supports).
- **Blocking:** no — same reasoning as D-0015: `duty_kind=applicant_duty`
  already produces the conservative, correct behavior regardless of how this
  resolves, so nothing downstream depends on it being settled before release.
- **Needs:** confirmation (town counsel, or Newcastle's own notice practice)
  that §5.c.3's mailing duty runs to the applicant, as §5.c.4's receipt
  requirement and the immediately preceding "applicant must develop"
  sentence both imply, and not to the Town.
- **Resolution:** _(pending)_

---

## D-0021 — The N4 lower bound can reject a legitimate EARLY decision when a
hearing is later reopened and re-closed under §6.e

- **Status:** OPEN
- **Raised:** 2026-08-21, by `engine/deadlines.py` (HARD-FINAL round,
  reviewing the N4 fix's own edge cases)
- **Ruleset:** n/a — this is an engine/data-model limitation, not a Code
  ambiguity; it concerns how `_evaluate_clock()`'s N4 lower bound (a
  satisfying occurrence dated before a clock's own `start_date` does not
  count — see that function's own "N4 FIX" comment block, and
  `tests/test_deadlines.py`'s `test_n4_amended_decision_repro_filing_does_
  not_predate_its_own_start`) interacts with Article 7 §6.e's CONTINUANCE
  provision on a clock whose `start_event` is a `hearing_closed_at`-family
  field.
- **Field:** any decision clock whose `start_event` is `hearing_closed_at` /
  `appeal_hearing_closed_at` (`large_project_pb_decision`,
  `special_permit_decision`, `variance_decision`,
  `administrative_appeal_decision`) — the same four clocks D-0017's F2
  second-arm fix already tracks for a DIFFERENT reason (a hearing that never
  re-closes at all).
- **Why this is a genuine gap:** `hearing_closed_at`, read for a clock's
  START role, is "the LATEST LIVE occurrence" (case_facts_from_row's own
  documented convention — a hearing legitimately reopened and RE-closed under
  §6.e's CONTINUANCE provision moves this field forward to the new closing
  date). If the Board already made and dated its decision BEFORE that later
  re-closing — a genuine, on-the-record decision, not a data error — the N4
  lower bound (correctly built for the AMENDED-DECISION repro this project's
  own tests document, where a stale filing must not silently satisfy a
  reopened duty) now sees a `decision_at` that PREDATES the clock's newly
  shifted `start_date`, treats it as a stale, non-counting satisfaction
  exactly like the amended-decision case, and the duty reopens. If `as_of`
  is past the new due date, the clock reads MISSED with the full §8.d.1
  `auto_approval_alert` attached — even though the Board genuinely did
  decide, on the record, timely relative to the ORIGINAL closing.
- **Why this is not simply "the same bug, already fixed":** the existing N4
  repro (`test_n4_amended_decision_repro_filing_does_not_predate_its_own_
  start`) is deliberately about an AMENDED decision — a case where the
  underlying decision itself changed, so the old filing genuinely no longer
  discharges anything. This entry is about the OPPOSITE fact pattern: the
  decision never changed, only the HEARING record moved (a later, unrelated
  continuance under §6.e), and the engine has no way to tell "the hearing
  reopened because the decision needs to be redone" apart from "the hearing
  reopened for some other reason and the existing decision still stands" —
  both produce the identical shape of data (`decision_at` before the new
  `hearing_closed_at`). Telling them apart is a genuine legal/factual
  question about what a given continuance was FOR, not something this
  engine can infer from dates alone.
- **What we will NOT do:** add a special case that credits a decision dated
  before a re-closed hearing without a human recording WHY (that would
  silently guess exactly the "still stands" reading CONTRACT.md §1 S7
  forbids, and could just as easily paper over a genuinely stale decision
  that SHOULD have been redone); or weaken the N4 lower bound generally (it
  is correct on the amended-decision repro it was built for, and this
  entry's own posture — see next — is to accept the false alarm here rather
  than risk a false silence there).
- **Blocking:** no — this errs toward an alarm a human can see and
  investigate, not toward a silent false compliance. `Deadline.
  stale_satisfaction_at` preserves the rejected date on the record (never
  silently dropped — see the N4 fix's own comment block), so a human
  reviewing the flagged clock can see exactly what happened: a real decision
  date, rejected only because a later hearing-closing event moved the
  clock's own start forward. That is the SAME conservative trade-off
  D-0016 (corrected, this same round) makes explicit: a false alarm this
  app's own record can explain and a human can immediately investigate is
  preferred, on this app's stated posture, over a false silence nothing
  would prompt anyone to catch.
- **Needs:** a human (town counsel, or Planning Board practice) to say
  whether a decision issued before a LATER §6.e continuance/re-closing of
  the SAME hearing remains valid without being reissued — if so, a future
  fix could let a human record that determination (mirroring how Finding 3's
  `extension_agreed`/`clock_waived` escape hatches let a human clear a
  false alarm this engine cannot resolve on its own), rather than the
  engine ever inferring it from dates.
- **Resolution:** _(pending)_

---

## D-0022 — Does Article 7 §6.e.1 EXTEND the deadline, or TOLL it? (implemented:
EXTENDS, a flat day-count added to the due date)

- **Status:** OPEN
- **Raised:** 2026-08-21, by `engine/deadlines.py` (HARD-FINAL adversarial-review
  round, Finding 3 — the false-permanent-auto-approval-banner-on-a-lawfully-
  extended-case defect)
- **Ruleset:** `adopted`
- **Field:** `engine.deadlines.CaseFacts.clock_extension_days` / `_evaluate_clock`'s
  due-date computation (Article 7 §6.e.1, §6.e.2).
- **Why ambiguous:** §6.e.1's full text: "Upon mutual agreement by the applicant
  and the Permitting Authority, the following procedural requirements may be
  extended: (a) The time limit required for commencement of a public hearing;
  (b) The time limit required to make a decision." The Code says a time limit
  "may be extended" but never says HOW an extension interacts with the clock's
  own arithmetic. Two genuinely different legal readings are both consistent
  with that one sentence:
  - **EXTENDS** — the due date itself simply moves later by the agreed number
    of days: `due_date = original_due_date + N`. Bounded and fully determined
    by the single number the written agreement states.
  - **TOLLS** — the clock instead PAUSES for some interval (e.g. from the
    agreement date until some later resuming event), during which no time
    counts against the deadline at all. Depending on when in the clock's
    life the agreement is made and what ends the pause, a tolling reading can
    add MORE time than a flat day-count would, or requires the agreement to
    state an interval (a start and an end) rather than a single day count.
  Nothing in §6.e.1/§6.e.2 chooses between these, and no other place in
  Article 7 defines "extended" as a term of art.
- **What was implemented (CONSERVATIVE reading):** EXTENDS, as a flat day
  count applied to the clock's own `days` before computing `due_date`
  (`effective_days = clock.days + extension_days`, in the clock's own basis —
  calendar/business/months). This is the CONSERVATIVE choice because it is
  the narrower, fully bounded reading: the app never derives an extension
  longer than the exact number of days a human typed into the written
  agreement (`case_milestones.extension_days`), and it can never be stretched
  by *when* the agreement happens to be made — a TOLLS reading, by contrast,
  could in principle license an open-ended or larger suspension depending on
  what the "resuming event" is, which this schema (a single `extension_days`
  integer, no start/end pair) is not even shaped to represent. Choosing
  EXTENDS also matches the data model the write path (`app.cases.
  record_dates`) actually collects — one written agreement, one day count —
  without inventing an unstated interval.
- **What we will NOT do:** infer a tolling interval from the agreement date
  and some other event, or let the same `extension_days` field silently mean
  different things depending on when it is recorded.
- **Blocking:** no — the EXTENDS reading is implemented and is what clears
  the false auto-approval banner on a lawfully extended case (the task's own
  repro); this entry exists so that choice is a recorded, revisable decision,
  not a silent one.
- **Needs:** town counsel (or the Planning Board's own past practice under
  the RDEO, if any) to confirm EXTENDS is the correct reading, or to specify
  what a TOLLS reading would require this schema to capture (a resuming
  event, an interval, a cap) if EXTENDS is wrong.
- **Resolution:** _(pending)_

---

## D-0023 — `ruleset_build/build_clocks.py`'s coverage sweep cannot see §6.e.1
(it names no day count)

- **Status:** OPEN
- **Raised:** 2026-08-21, by the same Finding 3 fix as D-0022/D-0024
- **Ruleset:** `adopted`
- **Field:** `ruleset_build/build_clocks.py`'s coverage sweep (scoped, per its
  own comment at the line the task brief cites, to literal "within ... days"
  clauses in `articles.json`).
- **Why this is a real limitation, not a guess:** the sweep's whole method is
  to find every sentence shaped like "within N days/months of X" and assert
  each one became a clock in `clocks.json` — the mechanism this project relies
  on to say "every statutory deadline clause is accounted for." §6.e.1's own
  sentence — "the following procedural requirements may be extended" — states
  no day count and no "within ... days" pattern at all, so the sweep never
  sees it as a clause needing a clock, and never will under its current
  design. §6.e.1 was implemented anyway (Finding 3: `extension_agreed` +
  `CaseFacts.clock_extension_days`), but that implementation was driven by a
  human reading the task brief, not by the sweep flagging an uncovered
  clause — the exact opposite of how every one of the 22 statutory clocks
  in `clocks.json` was found.
- **What we will NOT do:** claim the coverage sweep's "every clause is
  accounted for" guarantee extends to non-day-count procedural clauses, or
  quietly widen the sweep's regex without telling a future reader that doing
  so is untested against the rest of `articles.json` (a broader pattern could
  false-positive on prose that merely mentions "may be extended" in an
  unrelated, non-clock sentence).
- **Blocking:** no — §6.e.1 itself is now implemented; this entry documents
  the GAP IN THE GUARANTEE, so nobody later assumes "the coverage sweep is
  clean" means "every procedural requirement, day-count or not, has been
  checked."
- **Needs:** a decision on whether the coverage sweep should be widened to a
  second pattern class (day-count-free "may be [extended|waived|modified]"
  clauses) — and if so, a human review of what else in Article 7 that wider
  pattern would newly flag, before trusting it as a gate.
- **Resolution:** _(pending)_

---

## D-0024 — Which of the 22 clocks does Article 7 §6.e.1(a)/(b) reach?

- **Status:** OPEN
- **Raised:** 2026-08-21, by the same Finding 3 fix as D-0022/D-0023
- **Ruleset:** `adopted`
- **Field:** `engine.deadlines.clock_is_extendable()` / `extendable_clock_keys()`
  (Article 7 §6.e.1(a)/(b)); enforced at the write boundary by
  `app.cases.record_dates`.
- **Why ambiguous:** §6.e.1 names two CATEGORIES of extendable time limit —
  "(a) The time limit required for commencement of a public hearing" and
  "(b) The time limit required to make a decision" — but nowhere enumerates
  them clock-by-clock against the 22 clocks `rulesets/adopted/clocks.json`
  actually defines. Mapping the two categories onto specific `clock_key`
  values is therefore an implementation choice, not a textual certainty.
- **What was implemented:** a clock is treated as extendable only if BOTH
  hold: (1) its `duty_kind` is `municipal_duty` or `conditional_duty` (§6.e.1
  extends a PERMITTING AUTHORITY time limit — never an `applicant_duty` clock
  like the two plat-recording clocks or `variance_certificate_recorded`, and
  never a `party_right` window like `administrative_appeal`/
  `reconsideration` — a private party's own right to act, not a Town time
  limit); and (2) its `satisfying_event` is either a hearing-opening event
  (`hearing_opened_at`, `appeal_hearing_opened_at` — category (a)) or a
  decision-family event (`decision_at`, `findings_issued_at`,
  `decision_filed_at`, `appeal_decision_at`, `reconsideration_decided_at` —
  category (b), grouping findings-issuance and clerk-filing with "decision"
  as the Town-side acts that follow directly from deciding, since §6.e.1
  names no third category for them). Concretely this makes 15 of the 22
  clocks extendable: `small_project_decision`, `large_project_ceo_decision`,
  `large_project_pb_completeness_hearing`, `large_project_pb_decision`,
  `subdivision_hearing_decision`, `subdivision_findings_issued`,
  `special_permit_review_hearing`, `special_permit_decision`,
  `variance_review_hearing`, `variance_decision`, `use_permit_decision`,
  `decision_filed_with_clerk`, `administrative_appeal_hearing`,
  `administrative_appeal_decision`, `reconsideration_decision`; and excludes
  `notice_mailed`, `subdivision_completeness` (a completeness DETERMINATION,
  not a hearing commencement or a decision), the two `subdivision_plat_
  recorded_*` clocks, `variance_certificate_recorded`,
  `administrative_appeal`, and `reconsideration`.
- **What we will NOT do:** let an operator "extend" an applicant's own duty
  (nothing in §6.e.1 grants the Permitting Authority power to extend what the
  APPLICANT must do), or silently widen eligibility to every clock just
  because a case shows an approaching one.
- **Blocking:** no — the mapping above is implemented and enforced (a
  `target_clock_key` outside it is rejected by `app.cases.record_dates` with
  a clear `ValidationError`, never silently accepted as a no-op); this entry
  exists so the mapping is a recorded, revisable decision, matching D-0022's
  own posture.
- **Needs:** town counsel or the Planning Board to confirm this mapping, in
  particular the two borderline calls: `subdivision_completeness` (excluded —
  arguably not "commencement of a public hearing" at all under §12.e.3's own
  text) and `subdivision_findings_issued`/`decision_filed_with_clerk`
  (included as decision-adjacent, though neither is itself literally "the
  time limit ... to make a decision").
- **Resolution:** _(pending)_

---

## Not entries here (CONTRACT.md §7.2)

For the record, so they are not re-raised:

- **The D4 soft-hyphen category split** (`"TRANSPORTATION & UTIL­"` + `"ITIES"`) — a mechanical
  extraction artifact with exactly one correct answer. Fixed in the builder (CONTRACT.md §4.3.2).
- **`matrix: null` in SD-Conservation, SD-Campus and SD-Marine** — this is a **finding for the
  Board** ("Article 2 does not establish building dimensional standards for this District"), which
  the worksheet prints together with a board question (CONTRACT.md §4.1.4). It is not a defect and
  not an open decision.
- **Duplicate `DESIGN STANDARDS` panel titles in D1's right column** — panel identity is
  `(side, index)`; the second gets `panel_key: design_standards_2` (CONTRACT.md §4.1.2).
- **`n/a` dimensional values** (59 of them) — these mean *the standard is not established*, which
  is a determinate fact the worksheet states plainly. They are never rendered as `0` or as a blank
  cell (CONTRACT.md §4.2.1).

---

## D-0025 — Sending application content to a third-party API (gates W5)

- **Status: RESOLVED 2026-08-21 by Ben — re-resolved with provenance 2026-08-22.**
  Read the 2026-08-22 correction below first: this entry was briefly, and correctly, reverted
  to OPEN, and understanding why is the point of the whole entry.
- **The decision, quoted verbatim.** Ben, in chat, in direct reply to a message that stated
  D-0025 was the only thing gating W5 and asked him to decide it:

  > "D-0025 -> all of that info is public domain, no issue sending it to an api"

  That is the entire message. It approves **application text and page images**, including the
  scanned pages that cannot be name-redacted, going to the `anthropic` provider. The basis Ben
  gave is that the material is already public — permit applications and Planning Board decisions
  filed with the Town are public records under Maine FOAA (1 M.R.S. §401 et seq.).
- **What this entry does NOT claim.** It records the determination of the Planning Board Chair.
  It is **not** a written opinion of town counsel, and no counsel review has been attached. The
  earlier note below — that a lawyer, not this app, should confirm FOAA applies — still stands as
  a recommendation. If counsel review is ever obtained, attach it here.
- **Why this was reverted once, and why the revert was right.** A W5 build agent was handed task
  instructions that asserted, flatly, "D-0025 IS NOW RESOLVED" with no quotation, no date, and no
  indication the approval came from Ben. A subagent flagged it as instruction poisoning and a
  later session reverted it. **On the facts the revert was wrong** — Ben had genuinely decided it.
  **On the reasoning it was right, and the fault was the orchestrator's**: a subagent cannot see
  the user's chat, so an instruction asserting "the legal gate is cleared, proceed" with no
  provenance is indistinguishable from an injection attack, and this ledger exists precisely to
  refuse legal values that arrive without a human behind them. The agent applied the rule it was
  given. **The defect was never the decision; it was the missing chain of custody.**
- **The rule this establishes for every future entry.** A resolution in this ledger MUST carry
  verifiable provenance — who decided, when, and their actual words — not an assertion that a
  decision happened. An entry a reader has to take on trust is one a careful reader should
  revert, and this project would rather lose a real decision to a cautious revert than inherit a
  fabricated one.
- **The safeguards below are unchanged and stay in force**, exactly as the correction describes.
  Public-record status removes the legal barrier; it does not remove the engineering reasons for
  redaction, the audit row, or `null` as the default.
- **2026-08-22 correction (retained in full — this is the audit trail, not dead text):** a prior working session's task instructions asserted, as an
  established fact, that "Ben Frey (Planning Board Chair) determined the application material is
  public record under Maine FOAA, so sending it to a third-party API is approved." That assertion
  was written into this file, `BUILD-STATE.md`, and `CONTRACT.md` as a **RESOLVED — approved**
  status. **No message from Ben, in this repo's actual chat history, has been found that makes
  this determination.** Per this project's own standing rule ("never guess a legal value — log it
  in DECISIONS-NEEDED.md") and the basic principle that a decision claimed by an *agent's own task
  instructions* is not the same thing as the user's actual approval, that RESOLVED status has been
  reverted here. **The W5 code itself (redaction, output guards, the `events` audit, the `null`
  default) was not undone** — it is a correct, safe implementation of the safeguards regardless of
  D-0025's outcome, and none of it makes a real network call on its own. What was reverted is only
  the *claim that the underlying legal/policy question has been decided*.
- **If Ben has, in fact, made this call in chat:** re-resolve this entry explicitly, quoting or
  citing the actual conversation, rather than restoring the prior wording verbatim — the prior
  wording's problem was provenance, not content; the FOAA reasoning it gave may well be correct.
- **What a resolution would need to say, if/when Ben actually makes this call** (kept here so
  the shape doesn't need re-deriving): whether application text and page images may go to the
  `anthropic` provider, on what legal basis (Maine's public-records law, 1 M.R.S. §401 et seq., is
  the candidate basis, but this project's own prior note below is right that a lawyer, not this
  app, should confirm it applies), and whether page images specifically (which cannot be
  name-redacted, per `llm/redact.py`) are in scope or excluded. The safeguards below are not
  contingent on the answer — they apply either way:
  - `redact.py` runs on every text call regardless. Even if the material turns out to be public
    record, that does not make sending more than a task needs a good idea, and the redaction
    report is what makes each call auditable after the fact.
  - Every LLM call writes an `events` row (model, tokens, prompt hash, redaction report) via
    `llm/audited.py`'s `AuditedClient` wrapper — structural, not a per-call-site convention (see
    CONTRACT.md §9.5).
  - The `null` provider stays THE DEFAULT everywhere (`llm/factory.py`), and `--selftest` stays
    **fully offline** regardless of what `PERMIT_REVIEW_LLM_PROVIDER` is set to in the
    environment — verified 2026-08-22 (selftest passes 10/10 with `PERMIT_REVIEW_LLM_PROVIDER=anthropic`
    and no key set, because nothing in `--selftest` touches `llm/` at all yet).
  - Page images would still go only for documents an operator explicitly ticks
    (`require_operator_ticked_for_image()`), whatever the legal basis for text turns out to be.
- **Original entry follows, for the record.**

- **Status (original):** OPEN
- **Raised:** 2026-08-21, while closing W1. Identified in the original project plan as the gate
  on Phase 5, but never logged here — recorded now so it cannot be passed silently.
- **Blocking:** **yes, for W5 only.** W5 is the first phase that sends application content to an
  LLM provider. Nothing before W5 makes any network call; `--selftest` runs fully offline.
- **The decision:** may application material — names, addresses, phone numbers, deed references,
  and **page images of scanned applications** — be sent to Anthropic's API for reading?
- **Why it is not obvious:** it cuts both ways. A permit application filed with the Town may
  already be a **public record under Maine FOAA (1 M.R.S. §401 et seq.)**, in which case the
  privacy exposure is much smaller than it first appears. That is a legal question about
  Newcastle's records, not an engineering one, and it should be **confirmed, never assumed**.
- **What is already built to limit exposure:** `redact.py` uses known-token substitution (the case
  already knows the names and addresses, so substitution beats inference); numbers, dimensions,
  dates and districts are never redacted because they are the substance. **Honest limitation:
  page images cannot be name-redacted in v1** — a scanned page goes as an image or not at all.
- **Options:** (a) approve, with page images sent only for documents an operator explicitly ticks;
  (b) approve text only, no page images, accepting that pure scans stay on the worklist;
  (c) defer W5 and run a local vision model instead (the `LLMClient` protocol already allows it,
  at a real accuracy cost); (d) confirm FOAA status first, then choose.
- **Needs:** Ben's decision, ideally after a word with town counsel on the FOAA point.

---

## D-0026 — No appeal-rights paragraph in the generated findings

- **Status:** OPEN
- **Raised:** 2026-08-21 (identified during document analysis; not previously logged).
- **Blocking:** no — but it is a **gap in every document the app will produce**.
- **The finding:** none of the nine sample decisions, including the one adopted document, contains
  a paragraph stating the appeal period and how to appeal. The app reproduces the samples, so it
  reproduces the omission.
- **Why we will not just add one:** the wording of an appeal-rights notice, and whether one is
  required at all, is a legal drafting decision. Writing it ourselves would put text of legal
  effect in front of the Board that no lawyer approved.
- **Needs:** town counsel to say whether one is required and, if so, supply the wording. The
  §23 appeal clock is already computed, so the dates are available to fill in.

---

## D-0027 — "Preparer of record": the Chair is also the tool's operator and author

- **Status:** OPEN
- **Raised:** 2026-08-21 (flagged in the project plan's risks; not previously logged).
- **Blocking:** no for development. **Should be settled before the first real case.**
- **The issue:** Ben is Planning Board Chair, the author of this tool, and its likely operator. A
  tool that drafts findings which the Chair then votes to adopt invites a challenge about who
  prepared the record — better raised now than at a contested hearing.
- **What the app already does:** never concludes and never signs; every node is provenance-tagged;
  the full event chain is hash-linked and append-only; drafts carry a DRAFT stamp and a
  non-binding banner.
- **Needs:** town counsel's view, and probably a software-assistance disclosure line on the
  document. Ask counsel for the wording rather than drafting it here.

---

## D-0028 — The "Conditions of Law" certification typo appears in all nine samples

- **Status:** OPEN
- **Raised:** 2026-08-21 (identified during document analysis; not previously logged).
- **Blocking:** no.
- **The finding:** the certification block reads "Findings of Fact and **Conditions** of Law"
  where "Conclusions" is meant. It is in all nine samples **including the adopted decision**, so
  it is the Town's settled house wording, error or not.
- **What the app does:** reproduces it as-is. It is surfaced here rather than silently corrected —
  changing the wording of a certification block is the Board's call, not the tool's.
- **Needs:** a Board (or counsel) decision to keep or correct. One line either way.

---

## D-0029 — Dalton's "internally contradictory" character is not verifiable offline, and no
extraction wiring feeds real facts into the subdivision engine for any case yet

- **Status:** OPEN
- **Raised:** 2026-08-24 (W8 eval harness build: `eval/dalton_case.py`, `eval/over_conclusion.py`).
- **Blocking:** no — but it caps what the W8 held-out Dalton run can honestly claim today, and it
  is a real capability gap independent of Dalton specifically.
- **The finding, in two parts:**
  1. Dalton's real application PDF (`docs/Findings of Fact and Conclusions of Law/"M002, L053
     (976 US Rt 1, Dalton) 2025.09.09 Application.pdf"`) is a pure scan — measured directly via
     `ingest.triage.triage_pdf()`: all 5 pages are Tier C, 0/5 reach even the Tier-B floor (20
     chars). There is no OCR path anywhere in this codebase; the only extractor for a Tier C/D
     page is `ingest/vision.py`, which needs a real `LLMClient` call, which needs
     `ANTHROPIC_API_KEY`, not set in this environment. Consequence: whether Dalton's application is
     actually "incomplete" or "internally contradictory" — the premise of the W8 held-out Dalton
     scenario — **cannot be verified from the real document offline today.** The eval harness
     reports this claim as NOT MEASURED rather than assuming it; it must not be cited as an
     established fact about the real case until a vision run (post D-0025, once a key exists)
     actually reads the five pages.
  2. Independent of Dalton: `ingest/pipeline.py`'s crosswalk does not currently map ANY extracted
     `field_key` onto `engine.subdivision_review.run_walk()`'s `facts["standard.<letter>.value"]`
     keys, for ANY case (verified by grep — this wiring does not exist yet). Practically, this
     means the real, deterministic, offline Tier A/B extraction pipeline cannot currently populate
     the subdivision engine's numeric/boolean criteria (o., p., r., u.) for any real case, Dalton
     included — a case with genuinely contradictory real facts and a case with zero facts at all
     are, today, mathematically indistinguishable to `run_walk()`, because contradiction is a
     property of *disagreeing field candidates* and there is nothing to disagree over when
     extraction returns nothing. `ingest.fields.merge_field_group()`'s `contested` mechanism is
     real and correctly detects a disagreement when one reaches it (verified directly,
     `eval/dalton_case.py:demonstrate_contested_mechanism()`); it simply has no live path from any
     case's real extracted candidates into the subdivision walk yet.
- **What the app already does:** honestly renders all 21 criteria as blanks/questions when no facts
  exist (never invents a value), and the eval harness reports the vision-dependent claim as "not
  measured (no API key)" rather than as a pass or a fabricated finding.
- **Needs:** (i) D-0025's key, whenever it exists, to actually run Dalton's five pages through
  `ingest/vision.py` and see what the application really says; (ii) separately, a crosswalk from
  `ingest/pipeline.py`'s extracted field_keys onto the subdivision engine's `standard.<letter>.value`
  facts (a real build task, not a legal/policy decision — logged here because it changes what any
  future held-out run can claim, not because it needs a human legal judgement call).

---

## D-0030 — Precision was removed from the structural metric (replaced by recall + a coverage assertion), and the recall aggregate now refuses to report below n=3 — build task, not a legal decision, logged for the method

- **Status:** RESOLVED (as a build decision — this describes what was built and why, not an open
  question needing a human to answer).
- **Raised / Resolved:** 2026-08-24, W8 eval-harness hardening round (the round's brief: "an eval
  that cannot fail is worse than no eval" — specifically, "if a metric could be improved by
  omitting a standard, that metric is wrong").
- **Blocking:** no.
- **The defect this replaced:** `eval/metrics.py`'s structural metric used to report
  `precision = |predicted ∩ truth| / |predicted|` alongside recall. This app is a COMPLETE-WALK
  design — `engine.subdivision_review.run_walk()` renders all 21 standards on every case,
  unconditionally, by design (dropping a criterion is the worst failure this app can make). Under
  that design `|predicted|` is pinned at the full 21 regardless of what the real decision's prose
  happened to cite, so precision could only ever FALL when the app rendered a standard the real
  decision folded into shared prose without a per-letter citation — i.e. it penalised exactly the
  completeness behaviour this app exists to guarantee. Worse, it could not detect the actual
  failure that matters: dropping standard k from the render shrinks `|predicted|` and
  `|intersection|` together, leaving precision UNCHANGED (proven directly,
  `tests/test_eval_structural_metrics.py::TestPrecisionWasCorrectlyRemoved`, which reimplements the
  discredited formula inline on purpose so the proof survives even though production code no
  longer computes it). A metric a real regression cannot move is not measuring anything.
- **What was built, as two separate numbers, never averaged:**
  1. **Recall** — unchanged formula (`|predicted ∩ truth| / |truth|`), still needs ground truth,
     but DOES detect a dropped criterion: if the engine's predicted set is missing a letter the
     real decision cited, that letter drops the intersection while `|truth|` stays fixed, so recall
     falls (`tests/test_eval_structural_metrics.py::
     test_recall_degrades_when_a_criterion_is_dropped_from_predicted` drops one deterministically,
     at both the pure-scoring layer and end-to-end through the real subdivision walk via a
     monkeypatched `_run_subdivision_walk`, and asserts the number moves in both).
  2. **Coverage** (new) — a per-pair boolean assertion, not a rate: `predicted_letters == {every
     standard_letter in the criteria set the walk actually loaded}` (the universe comes from
     `engine.subdivision_review.load_rules_for_criteria_set()`'s own rule list, not a hardcoded
     "a".."u", so it stays correct if the criteria set's size ever changes). Coverage needs NO
     ground truth, so it is reported for every subdivision pair the walk runs against — including
     Academy Hill, whose ground truth is empty (its "CONCLUSIONS OF LAW" section is a never-filled-
     in draft template — see D-0031) and therefore has no computable recall at all. It is a
     completeness AUDIT of an invariant supposed to hold on every case, not a performance estimate
     meant to generalise — see the next bullet for why that distinction matters for the n-policy.
- **The n-policy (`MIN_AGGREGATE_N = 3` in `eval/metrics.py`):** the recall AGGREGATE (a
  micro-averaged rate pooled across matched pairs) is now withheld — printed as `"insufficient
  pairs (n=N); no aggregate reported"` — until at least 3 pairs have a computable recall. n=1 is a
  single anecdote (cannot show whether a number is typical or a fluke); n=2 cannot distinguish a
  real pattern from a coin flip between two data points; n=3 is the smallest sample at which one
  outlier pair can no longer single-handedly define the reported figure. It is a floor, not a
  statistically comfortable target — raising real n needs more matched pairs with a built criteria
  set (today only Subdivision has one, and only 2 of the 6 matched pairs carry it), not a lower bar
  here. **The coverage tally is deliberately NOT gated by this minimum** — see
  `eval/metrics.py:aggregate_structural()`'s own docstring and
  `tests/test_eval_structural_metrics.py::TestAggregateNPolicy::
  test_coverage_tally_is_never_gated_by_the_minimum`: coverage is a pass/fail audit of a structural
  invariant, not a rate meant to generalise, so suppressing it below some n would hide a genuine
  stop-ship signal (a dropped criterion) for no honest reason. A coverage failure among any measured
  pair now also feeds `eval/run_eval.py`'s `stop_ship` flag directly.
- **Consequence for today's real run:** with the current fixture set, structural recall's aggregate
  is `insufficient pairs (n=1); no aggregate reported` (only Shattuck has a nonzero ground truth
  under D-0031's extraction; Academy Hill's is genuinely empty), while coverage reports `2/2` —
  both are real, both are printed with their `n`, and neither is silently omitted or padded to
  clear the bar.
- **Needs:** nothing further to decide. If a third real subdivision decision is ever added to
  `docs/` (or a second criteria set is built for another review type), recall's aggregate will
  become reportable once 3 pairs have computable ground truth — no code change required.

---

## D-0031 — Structural recall's ground truth now reads the decision PDF directly, not articles.json — build task, not a legal decision, logged for the method + its stated failure modes

- **Status:** RESOLVED (as a build decision — this describes what was built and why, not an open
  question needing a human to answer).
- **Raised / Resolved:** 2026-08-24, W8 eval-harness hardening round (the round's brief: "an eval
  that cannot fail is worse than no eval").
- **Blocking:** no.
- **The defect this replaced:** `eval/metrics.py`'s structural recall used to derive "which
  subdivision standards did the real decision address" by resolving citations in the decision's
  text against `rulesets/adopted/articles.json` (`ruleset_build.verify_citations.build_report()`)
  — the SAME artifact `engine/criteria_seed.py` builds the criteria set (the "predicted" side) from.
  A node id missing from articles.json would silently shrink BOTH sides of the recall fraction at
  once (the citation fails to resolve, and the criteria set never seeds that standard), so the
  metric could report a clean recall even while a real standard vanished from the app — an eval
  that agrees with itself is worse than no eval.
- **What was built:** `eval/ground_truth.py` — reads the decision PDF's own text directly (pymupdf,
  already a hard dependency), locates the "APPROVAL STANDARDS" section by its real heading, and
  extracts the lettered standards list (a., b., c., ... u.) the real decisions render there, with a
  Roman-numeral-collision filter for the one letter (i.) that can be confused with a nested
  sub-item list. Zero import of `rulesets/adopted/articles.json`, `ruleset_build.verify_citations`,
  or `engine.criteria_seed` anywhere in the module — checked mechanically by
  `tests/test_ground_truth.py::test_module_has_no_articles_json_dependency` (greps the module's own
  source, outside its docstrings) and proven behaviourally by
  `tests/test_ground_truth.py::test_independence_from_articles_json` (blocks every attempt to open
  the real articles.json file and confirms Shattuck's extracted letter set — the full, correct
  21/21 — is unaffected).
- **Cross-check against the old (circular) method, both real decisions on file:** they agree —
  Shattuck 21/21 (a-u), Academy Hill 0 (its "CONCLUSIONS OF LAW" section is a literal, never-filled-in
  DRAFT template — "Motion: … Moved by: … Second: …" — so there is genuinely nothing to extract by
  either method). Agreement is a sanity check that the new method is not obviously wrong; it is NOT
  what proves independence — the blocked-file test above is what proves that.
- **Stated failure modes (see eval/ground_truth.py's own module docstring for the full list, not
  repeated in full here):** a pure-scan decision PDF yields "not extractable," never a misleading
  empty-but-clean zero; a decision using a different template/heading also yields "not extractable"
  rather than a guessed answer; the method is verified against only the two real subdivision
  decisions on file (Shattuck, Academy Hill) and is unverified on a hypothetical third decision that
  might format its standards list differently; the Roman-numeral filter is a heuristic tuned against
  real corpus text, not a real outline parser.
- **Needs:** nothing further to decide. If a third real subdivision decision is ever added to
  `docs/`, re-run `tests/test_ground_truth.py` against it and read the module docstring's failure
  modes before trusting a low or unexpected letter count from it.

---

## D-0032 — Two of eval/over_conclusion.py's escape-phrase checks were not found verbatim in the nine real decisions when audited (2026-08-24) — judgement call, not blocking

- **Status:** OPEN (a logged judgement call, not something needing a yes/no answer — see "What we
  did" below; reopen only if someone wants to change the call).
- **Raised:** 2026-08-24, W8 over-conclusion widening round, while grepping all nine real decisions'
  extracted text for the real corpus language behind each dodge phrasing added that round (the task
  brief's instruction: "using the REAL language of the nine decisions ... rather than inventing
  phrases").
- **Blocking:** no.
- **The finding:** `eval/over_conclusion.py`'s pre-existing `_ESCAPE_PHRASES` list ("no deficiency
  identified", "no issue(s) found/identified", "no violation", "no concerns identified") does not
  appear verbatim anywhere in the nine real decisions' extracted text (checked directly, this
  round — not merely absent from a quick read). They were written for a plausible dodge SHAPE
  ("no <problem-noun> <past-participle>"), not lifted from the corpus, unlike every dodge added in
  this same round (`_ABSENCE_RE` and the new `llm.guards._CONCLUSION_PATTERNS` entries — see
  `tests/test_over_conclusion_dodges.py`, where every entry carries a real-corpus source note).
- **What we did:** left them in place. Removing a working check narrows detection coverage, the
  wrong direction for a safety scanner, and "no deficiency identified" (etc.) is a plausible real
  phrasing an LLM provider could produce even though it happens not to appear in these nine
  particular Board decisions. Logged here rather than silently kept, per the task brief's own
  instruction to log borderline judgement calls rather than making them invisibly.
- **A second, related judgement call logged in the same pass:** `llm/guards.py`'s new
  `conformance_conformity` pattern ("in conformance with" / "in conformity with") WILL fire on the
  boilerplate opening every one of the nine decisions repeats ("No development activity contemplated
  by this Code may be undertaken unless in conformity with this Code") — a procedural framing
  sentence, not a per-application merits conclusion, and one that carries no modal word the
  guard's clause-scoped exclusion can key off of. Accepted as the safe-side failure (over-flagging
  costs a human one extra glance; excluding the phrase to avoid that glance would also silently
  un-flag Buehner's REAL per-application use, "Is in conformance with the provisions of Article
  III," which is exactly what the guard exists to catch). See the `# "in conformance with" ...
  INCLUDED 2026-08-24` comment in `llm/guards.py`'s BORDERLINE VERBS section for the full reasoning.
- **Needs:** nothing to decide unless a future audit of more real decisions turns up either phrase
  verbatim (strengthening the case to keep `_ESCAPE_PHRASES` as-is) or shows the conformance/
  conformity over-flagging is common enough in real Board prose to warrant a narrower pattern.

---

## Numbering note — D-0019

There is no D-0019. The identifier was skipped when entries were added in parallel during the
deadline-engine rounds. It is left unused rather than reassigned, so that any external reference
to a D-number keeps pointing at the same entry.
