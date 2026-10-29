# Applicant Portal — one question at a time (revision to the redesign brief)

**Status:** approved by the Planning Board chair, 2026-10-24, with the three open decisions settled as
recorded in section 9.
**Revises:** `specs/2026-10-23-applicant-portal-redesign.md` (approved 2026-10-23). Where the two
differ, this brief wins; everything it does not mention stands.
**Prototype:** "Newcastle Permit Wizard", https://claude.ai/artifact/HVaTbirFXVbMfHYb1DxGjq (the chair
tried it and chose it, 2026-10-24). It is a picture of the flow, not the build: section 8 lists where
the build must differ from it.
**Built so far:** PR #20 (`portal-design-pass`), the window, autosave and controls this brief reuses.

## 1. Decisions already made by the chair (2026-10-24)

- **One question per screen, moving sideways.** The next question slides in from the right; Back
  slides it out to the right. No long pages of questions.
- **The answer trail with the dots** (the chair's pick from three mock-ups):
  - answers stack up as chips above the question, and tapping a chip goes back to that question;
  - a single choice moves on as soon as it is tapped;
  - small plain dots at the bottom left show where you are, the current one bright.
- **No "Why we ask" and no "Why the Code calls for it"**, anywhere an applicant sees. People want to
  know whether they can do what they want to do, not what the Code says.
- A labelled stepper bar across the top was considered and rejected.

## 2. What the applicant sees

**One screen, top to bottom:**
1. The window's toolbar: the section's name, "Saved", and **Save and close** once signed in.
2. **The answer trail:** this section's answers as chips. Tap one to change it.
   - In a building or an addition, the trail and the dots cover that one item.
   - An answer carried over from the start of the flow has a dashed outline (section 5).
   - Before the first answer the row says "Your answers appear here as you go".
3. **The question**, centred: a large question, one plain line of help when it earns it, and the
   control.
4. **The footer:** the dots at the bottom left; Back and Continue at the bottom right.
   - **Continue** appears only where a tap can't finish the question: choose-all-that-apply, a typed
     answer, a number, a stepper, a measurement set. Return presses it.
   - An optional question shows **Skip for now** in Continue's place until it has an answer.
   - With more than 12 questions in the group, the dots become "12 of 20".

**Desktop (≥ 1024 px):** the sidebar from the approved brief stays. It lists the sections with
○ ◐ ✓, nested buildings and additions, and any section can be opened from it. The dots count the
questions within the current section (or building).

**Phone (< 1024 px):** no sidebar. The toolbar has **‹ Back** at the top left. Back and Continue sit
in the bottom bar; the section list is one tap away, as now.

**Motion:** a 300 ms slide (the system's spring curve); a short cross-fade when the device asks for
reduced motion. Focus moves to the new question; screen readers hear "Question 3 of 7: …".

## 3. Kinds of screen

| Screen | Used for | Moves on |
| --- | --- | --- |
| Tiles, pick one | choices and yes / no | on tap |
| Tiles, pick several | "choose all that apply", exterior finish | Continue |
| Number with its unit | lot width, floor area | Continue |
| Stepper (− and +) | homes, stories | Continue |
| Text, one line or long | names, phone, description | Continue |
| A measurement set | deed book and page; width and depth | Continue |
| **"Is this right?"** | a value from the Town's map | on tap, or correct it |
| Setbacks around the lot drawing | the four setbacks | Continue |
| Four wall sliders | window and door share per wall | Continue |
| Upload | site sketch, photos, permits | Continue or Skip for now |

**"Is this right?"** is new. A value the Town's map supplies (the street address, the lot's acres,
its road frontage) is shown large with its source ("Measured from the Town's map"), and two tiles:
**Yes, that's right** moves on; **No, I'll correct it** opens the field. Today these sit pre-filled
in a field the applicant may not notice.

**"I don't know yet"** stays, as a quiet link under each question that allows it. It answers the
question as not known and moves on; review shows "Not known yet, staff will follow up".

**One question per screen, with one rule for exceptions:** values that are one measurement share
a screen (deed book and page; width and depth; the four setbacks; the four walls). Nothing else is
grouped.

## 4. The flow

**Do I need a permit?** (signed out, as now, one question per screen): what you're planning →
the kind of building work → about how much floor area → how many new homes → **Where is the
property?** (search, then the lot on its map: "Yes, this is my property" or "No, search again") →
**What you'll need**.

**What you'll need:** the answer as the title ("You'll need a Small Project Plan"), one sentence on
who reviews it, rows for reviewer, fees and the lot, and **Start this application**. No Code
citation. Signing in follows on the next screen: the email field, then "Check your email". The
emailed link returns to the first question of the application.

**The application** keeps the approved sections (Your lot · About you · The work · Buildings ·
Additions · and so on for each form), each now a run of single questions:
- **Owner and helper questions** slot in only when "Do you own this property?" is No or "Is someone
  helping?" is Yes. Those two become yes / no tiles rather than switches.
- **Buildings and additions are no longer sheets.** Each building is a run of questions in the main
  flow, ending with **"Is there another building in this project?"** (Yes, add another / No, that's
  all). Additions open with "Are you adding an addition, porch or deck?" and loop the same way.
  The sidebar nests each one ("Building 2: Barn"), and its dots cover just that item.
- The building's first question is its type, as tiles. A detached garage or shed is chosen there
  ("A smaller building that goes with a home"), which replaces the "Add a building" menu and its
  presets.

**Review and sign:** "Check your answers", every section's answers with **Change** beside each.
Change opens that question, and answering it returns to review. Unanswered questions say **Still
to answer**, in red. The page ends with **What happens next**: saved; nothing has gone to the Town
yet; signing and sending arrive in Milestone 6. The official form's printout keeps the Code's labels
and order, unchanged.

## 5. Answers carried from the start

What the applicant said before signing in is not asked again. **The work**'s "What kind of work is
this?" arrives answered from "What kind of building work?", with a dashed chip and the line "Filled
in from your answers at the start. Change it if you need to." The answer is saved as the
screener's (`set_by = screener`), not as typed.

The screener's floor area and new-home count also fill **Building 1**'s floor area and homes
(the chair's ruling, section 9), marked the same way.

## 6. What goes

- "Why we ask" under every question, and "Why the Code calls for it" on What you'll need. The
  citations stay in the form definitions and on the chair's approval sheet, for staff.
- Sheets for buildings and additions, their page dots, and the hub lists of items.
- The "Add a building" menu and its presets ("A detached garage or shed").
- The label-beside-control rows inside the application. The inset-list rows stay on Home, My
  applications and review.

## 7. What stays

The window and sidebar, autosave (an answer saves as it is given; Continue waits for it; Save and
close stays until everything is saved), light and dark, the seal and the teal, the controls built in
PR #20, the form content and its approval status, the official form's printout, and the
no-verdict rule for everything an applicant reads.

## 8. Where the build differs from the prototype

The prototype simplified to stay short. The build follows the forms:
- **Building types:** all nine of the form's types, not the prototype's five.
- **Window sliders:** 0 to 100 %, in steps of 5, as the form allows, not the prototype's 0 to 60.
- **Every form question**, including those the prototype left out (renovation only, first-floor
  elevation, a floor height per story, roof slope, the Use Permit's uses, and the Entrance Permit's
  map pin and sight distances), each as its own screen by section 3's kinds.
- **All three applications**, not only the Small Project Plan.
- The prototype's map is a drawing; the build shows the lot from the Town's map, as now.

## 9. Decisions settled with the approval (the chair, 2026-10-24)

- **Which way the walls face.** The official form asks for north, east, south and west wall
  percentages; front, back and sides read more easily but can't become compass points on their own.
  **Ruling:** each building asks "Which way does the front of the building face?" (north, east, south
  or west, as tiles) before its walls, and each slider is labelled with both, for example "Front
  (north, faces Sheepscot Road)". The new question goes on the forms review sheet as a draft, as a
  form change.
- **Carrying more from the start.** **Ruling:** the screener's floor area and new-home count fill
  Building 1's floor area and homes, marked as carried over (section 5). Further buildings ask.
- **Plain words on review.** **Ruling:** review shows each question as it was asked, with the
  official form's term small beneath it. The printout keeps the official labels and order.

## 10. Proof

- Each application can be completed one question per screen at desktop and phone width, in light
  and dark, with axe clean (the existing journeys, rewritten).
- No screen shows "Why we ask", "Why the Code calls for it", a Code citation, or a verdict word.
- A single choice moves on with one tap; Continue never appears for one.
- Changing an answer from a chip or from review returns the applicant to where they were.
- Values from the Town's map are confirmed or corrected on an "Is this right?" screen, and a
  corrected value is never credited to the map.
- The re-critique of the redesign is rerun; the 32 / 40 target stands.
