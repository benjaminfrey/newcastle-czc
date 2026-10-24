# Applicant Portal — redesign brief

**Status:** draft for the Planning Board chair's approval (2026-10-23). No code is written until it
is approved.
**Builds on:** `specs/2026-10-14-applicant-portal-design.md` (unchanged except where this brief
says so); the critique of 2026-10-23 (21/40;
`.impeccable/critique/2026-10-24T01-25-15Z__portal-web-src.md`); `portal/web/PRODUCT.md`.

## Decisions already made by the chair (2026-10-23)

- Cut the application to about **ten steps**, by grouping questions.
- Show progress beyond a step number: the design recommends **a sidebar of steps with checkmarks**.
- **Easier controls**: steppers, sliders, switches, segmented controls and pickers instead of free text.
- **Look and work like a macOS / iOS app**, Back/Next included.
- Redesign **every applicant page**, with a **quiet civic** identity. The Town seal may be used.
- Serve **residents on phones and repeat applicants at desks equally**.
- **One continuous flow**: "Do I need a permit?" and "Where is it?" become the first steps of the
  same app.
- The desktop sidebar holds **the steps of the open application**; "My applications" is its own page.
- The four form-change proposals below may be put to the chair.

## 1. Job and audience

A resident (often older, often on a phone, applying once) or a builder (often, at a desk) wants to
know what permit they need and get a complete application done in one sitting, without calling
the Town Office. Mode: **Operate**. The visitor must always know where they are, what is left, and
that nothing they typed is lost.

## 2. Outcome and proof

- A Small Project Plan for one house addition takes **about 10 steps**, not 39–70 screens. The Use
  Permit and the Entrance / Driveway Permit take 9–10.
- Every step shows its state in the sidebar (○ not started, ◐ started, ✓ done; a small dot where an
  answer was left "I don't know yet").
- What only this product can prove: the Town's own map of *your* lot, carried from the first
  minute to the end (the critique's single high point), and the Code's own words one tap away.

## 3. Direction

**Visual authority:** the user pinned it. The bar is Apple's own apps (System Settings, iOS
Settings, Setup Assistant, Mail sheets), executed at full craft, plus a **quiet civic** layer:
- the Town seal and "Town of Newcastle" in the sidebar header (desktop) and the title area of the
  application's root list (phone);
- one accent colour from the seal's teal (measured **#1098A8**; about 3.4:1 on white, so it is used
  for identity and selection, with a deeper shade of the same teal for text and buttons to meet
  WCAG AA, measured in both modes);
- the parcel map as the visual anchor (Your property; Placement; Where it meets the road).
Typography is the system UI face (San Francisco on Apple devices, the platform's own elsewhere).
Light and dark follow the device, as Apple apps do.

**Structural thesis:** the application is a *document with sections*, not a corridor of questions.
Each step is a page of grouped inset lists (System Settings): row label on the left, control on the
right on wide screens; label above control on phones.

## 4. The step plans

The first three steps are signed out and shared. Signing in happens at "What you'll need", in a
sheet, and the same sidebar then continues with the application's steps.

**Shared start (signed out):**
1. **Your project.** What are you planning? A segmented and checkbox list, plus the size questions
   that apply.
2. **Your property.** Search or tap the map, then confirm the lot, or enter the map and lot yourself.
3. **What you'll need.** The applications, with who reviews each and the time the Code allows.
   Continue starts the one you choose and opens the sign-in sheet.

**Cover Sheet, as two steps (every application):**
- **Your lot.**
  - Group 1: the address (pre-filled), the map and lot (read only), and the deed book and page on
    one row (optional).
  - Group 2: lot area, frontage, width and depth (pre-filled where the map knows them, editable,
    "ft" and "acres" suffixes), and homes on the lot now (a stepper).
- **About you.**
  - Group 1: your name, phone and mailing address (with address autofill).
  - "I own this property" is a switch. Turn it off and the owner's group appears inline.
  - "Someone is helping me (builder, surveyor…)" is a switch. Turn it on and the agent's group
    appears inline.

**Use Permit (9 steps):**
Your project · Your property · What you'll need · Your lot · About you ·
**Uses today** (current uses as chips from the Code's list, plus a description) ·
**Your plan** (uses to start and uses that will stop, as chips, each with a description) ·
**Photos and plans** (uploads) · **Review and sign**.

**Small Project Plan (10 steps):**
Your project · Your property · What you'll need · Your lot · About you · **The work** (what kind of
work, a description, and a site sketch) ·
- **Buildings** (only when the work includes a building). A list of buildings, each row with its
  status. "Add a building" opens a **sheet** with four pages and its own dots:
  - *Basics:* a two-stage type choice (Home / A business / A smaller building that goes with… /
    Farm / Not sure, then a refinement only where needed); renovation only (a switch); homes in it
    (a stepper); an optional name, defaulting to the type ("House", "Garage").
  - *Placement:* the four setbacks around a drawing of the lot (proposal 4).
  - *Size:* width and depth; stories (a stepper); floor area; first-floor height; one floor-height
    field per story.
  - *Roof and walls:* roof style as tiles with small silhouettes; roof slope from a picker
    (proposal 3); exterior finish as chips (proposal 3); windows on a compass (proposal 2).
- **Additions, porches and decks.** The same list-and-sheet pattern: one page for kind, attached
  to (a picker, proposal 3) and renovation only; a second page for size, roof and windows, shown
  only for additions and attached garages.

Then **Review and sign**.

**Entrance / Driveway Permit (10 steps):**
Your project · Your property · What you'll need · Your lot · About you ·
- **The driveway:** the road (a picker of the roads along your lot, or "another road"); the work
  (a segmented control); homes served (steppers); shared with a neighbour (a switch, plus the
  easement upload when on).
- **Where it meets the road:** a pin on your lot's map; width; slope of the first 20 ft (a
  slider); angle (a slider, 45–90°, with a small diagram).
- **Safety at the road:** sight distance left and right; distance to the nearest intersection and
  whether it has a traffic light; any roadside ditch.
- **State permit and sketch:** MaineDOT permit status (a segmented control), a copy of it, and a
  sketch.

Then **Review and sign**.

**Review and sign:** the official form as grouped sections, in the paper form's order, with
Certification and Office use last. Each section has Edit, which opens that step in a sheet with
Done. "Add more detail" sits on each section. Sign and submit arrives in Milestone 6; until then
the page says "Your application is saved. Sending it to the Town arrives soon", with no disabled
Submit button.

## 5. Navigation: macOS and iOS

**Desktop and tablet (≥ 1024 px):**
- **Window layout.** A sidebar of steps with the seal on the left and a content pane on the right.
- **Toolbar.** The step title sits at the top left of the content pane. "Saved" status and **Done**
  (to My applications) sit at the top right.
- **Footer.** Back (secondary) and **Continue** (primary) sit together at the bottom right. Continue
  is always rightmost, and Return triggers it.
- **Sheets.** A building or addition opens as a sheet over the window, with Cancel on the left, the
  item title in the centre, and Done on the right. The sheet has its own page dots and Back/Next.
  Esc cancels it.
- **Free movement.** Any step in the sidebar can be clicked; nothing is locked.
- **Keyboard.** ⌘↑/⌘↓ (or Option-↑/↓) move between steps in the sidebar. The sidebar is also a
  normal list for the keyboard and screen readers.

**Phone (< 1024 px):**
- **The root page.** "Your application" opens as a large-title grouped list of the steps with
  their checkmarks. It replaces the sidebar.
- **Inside a step.** Tapping a step pushes it in. The title shrinks as you scroll, and a
  `‹ Application` chevron sits at the top left. Swiping in from the left edge goes back.
- **Continue.** A full-width button in a **fixed bottom bar**, clear of the home indicator. Back is
  only the top-left chevron, never a button beside Continue.
- **Sheets.** Buildings and additions open as full-height sheets, with Cancel and Done at the top.
- **Lists.** "Add Building" is a row with a plus sign at the end of the list. Removing a building is
  a red "Delete Building" row inside its sheet, with a confirmation sheet.

**Behaviour, both sizes:**
- **Autosave.** Each answer saves as it is given, on change for switches and pickers, and on leaving
  the field for typed text. "Saving…" then "Saved" shows in the toolbar. **Continue only moves on;
  it never saves.**
- **Validation.** Shown inline as the person types. Continue is never disabled; unfinished items
  are marked in the sidebar or root list and gathered on Review.
- **Done and Back never lose anything.** The only commitment is Submit, from Milestone 6, behind a
  confirmation sheet.
- **Two tabs.** The existing protection stays: a save from a tab that fell behind is refused, and
  the toolbar offers "Load the latest".
- **Screen changes.** Focus moves to the new step's title and the page title updates.
- **Reduced motion.** When the device asks for it, push and sheet transitions become simple fades.

## 6. Proposals that change the forms (each needs the chair's approval)

The forms are still drafts that nobody uses in production, so these change version 1 in place. The
official form keeps printing the Code's terms. Each proposal goes on the forms review sheet.

1. **A garage can be a building.**
   - "Add a building" offers *Detached garage or shed*. Its Building Form is preset to Residential
     Accessory Building (Art. 5 §1.c.1.b), and the applicant can change it.
   - An *attached* garage stays an addition, in the Components Section, since Art. 5 §3.d covers
     attachments.
   - The "garage attached or detached" question goes away, because where the garage is added now
     answers it.
2. **Windows on a compass.**
   - The four per-wall percentages stay, because the packet and Art. 6 §6 measure them that way.
   - They become four sliders in steps of 5 %, set around a small plan of the building and labelled
     with the street side ("Front (faces Sheepscot Road)") as well as the compass point.
   - Each wall keeps "I don't know yet".
   - A Mostly / Some / Few choice was considered and rejected: turning it into the form's
     percentages would mean inventing values.
3. **Pickers instead of typing.**
   - *Roof slope:* Flat (under 2/12), 2/12 to 12/12 in whole steps, Steeper than 12/12, or I don't
     know. It prints as today, e.g. "8/12".
   - *Exterior finish:* chips for clapboard, wood shingle, vinyl siding, fibre-cement, brick, stone,
     board-and-batten, metal, asphalt shingle roof, metal roof and slate roof, plus Other (typed).
     It prints as a list.
   - *Attached to:* a picker of the buildings in this application, plus "Free-standing".
   - *The entrance's road:* a picker of the roads along the lot (from the map), plus "another road"
     (typed).
4. **Setbacks on a drawing of the lot.**
   - The lot's outline from the Town's map, with the building as a box and the four setback
     distances entered beside the side each measures. The front is the side facing the road; each
     side is labelled.
   - The drawing illustrates; it does not measure. The numbers are typed, and the page says "not to
     scale".
   - Without a lot outline (a property entered by hand), a plain square stands in for it.

## 7. States and ranges

- **Buildings:** 1 to 20. **Additions:** 0 to 30. **Uses:** 0 to about 5. **Uploads:** 0 to many,
  25 MB each.
- **Empty states:**
  - My applications with none: an empty-state page whose one action is "Start an application".
  - A list with no buildings: one "Add a building" row.
- **Loading and saving:** skeleton rows while a page loads; "Saving…" and "Saved" in the toolbar;
  "Couldn't save — retrying" with the answer kept.
- **Errors:** inline under the field; the two-tab conflict as a toolbar banner; lookup down, a busy
  server, and uploads that are refused, each with its own message.
- **Sign-in sheet:**
  - The email field.
  - Then a "Check your email" state naming the address and the 15-minute expiry, with "Send it
    again".
  - The emailed link resumes the exact step.
- **Uploads:** a large "Take a photo or choose a file" button that offers the camera on phones,
  thumbnails for images, progress, and the accepted types and size written on the control.

## 8. Constraints

- Everything rests on what the app already does: the answers model, revisions, uploads, the
  stale-parcel and draft guards, the pinned form version, and the no-verdict rule (checked by the
  existing test).
- WCAG 2.1 AA in light and dark: 44 px targets, visible focus, and screen-reader announcements on
  every step change.
- The `group` key for form fields and the list-and-sheet repeats are new form-definition features,
  with Python/TypeScript parity checked by the shared fixtures, as now.
- The no-verdict word list applies to every new label, including the sidebar's status words.
- The journeys are rewritten for the new flow at desktop and phone, with axe checks; the critique
  is re-run, aiming at 32/40 or better.
- **Not in this pass:** the staff inbox and submitting (Milestone 6), the printed forms
  (Milestone 5), and any change to the Code-facing wording, apart from the four proposals.

## 9. Open decisions

- **The Town seal** is in hand (`portal/web/public/town-seal.png`, 190 × 190 PNG, supplied by the chair
  2026-10-23): sharp at sidebar size. An SVG or a PNG of at least 512 px is needed only if the seal is
  shown larger.
- **The four proposals in section 6**, each approved or declined on the review sheet.
- **The exterior-finish chip list** (proposal 3) needs the chair's or CEO's check, so its terms
  match what staff expect.
