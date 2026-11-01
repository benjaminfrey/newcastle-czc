# Applicant Portal — the guided builder (a new direction)

**Status:** draft for the Planning Board chair's approval, 2026-10-30, revised the same day with
his answers to a reviewer's questions (decisions 12–15).
**Revises:** the portal's purpose and experience as set out in
`specs/2026-10-14-applicant-portal-design.md` (§1, §2, §4) and every later interface brief
(`2026-10-23-applicant-portal-redesign.md`, `2026-10-24-applicant-portal-wizard.md`,
`2026-10-25-applicant-portal-task-list.md`, `2026-10-25-applicant-portal-projects.md`). Where this
document and those differ on what the portal is for, how it talks, or how it looks, this one wins.
Their server-side decisions (accounts and sign-in, projects as one unit sent together, the lock,
storage, uploads, fees, the Code's clocks) stand unless a section below says otherwise.
**Research behind it:** `reports/Guided permit app design research.md` and its published page
https://claude.ai/artifact/GZPabKQJZzBbtWZLWnULqJ (both 2026-10-30).
**Mockups the chair chose from:** `.superpowers/brainstorm/` (direction B, "a conversation", and
the Material screen in `material-vs-apple.html`).

This is the first of five designs. It settles the experience as a whole and the interfaces the
other four must provide (§11). Each of the other four gets its own design before it is built.

---

## 1. Why

The usual permit process asks a resident to fill in forms without knowing whether what they want
is allowed. Most residents don't read the Code, or can't apply it with confidence. They submit;
the Code Enforcement Officer (CEO) or the Planning Board reviews; and too often the answer is "no"
for reasons the applicant never knew about. That order made sense before software could read the
Code. Newcastle's Code is precise enough to be written as rules (the ruleset in
`build/permit-review/rulesets/adopted-v1.0/`), so the order can be turned around: **help the
resident shape a project the Code allows, explaining as they go, so that what they send is
permittable by construction.**

The chair's own cases show what goes wrong today:

- **The Inn.** A B&B (a use made non-conforming by the 2020 Code) wanted to host a public dinner
  once a month. It applied for an Assembly use and went through a Board review, where the Board
  found that Assembly didn't fit and that the Inn's existing permit to serve food to guests already
  covered dinners. The applicant's mistake was translating their plan into the wrong Code
  category. The right answer was "you're already covered".
- **A deck** too close to the shoreland. The limit is fixed. The helpful answer is where on the lot
  a deck can go.
- **A house addition in the shoreland.** The Board found a way to yes. The house could grow
  sideways along the shore or toward the back, away from the water, within a total-footprint
  limit. This is design help, not a ruling.
- **A four-story apartment building in the Fabrication district.** No version of it works there.
  The honest answer is plain and early: what the district does allow.
- **A request to "waive" a setback in the Historic district** to set a new house farther back.
  The Board can waive little if anything in the Code. The person didn't know which rules are
  fixed, or why.
- **"A three-story house" where two stories are allowed.** The Code counts only stories with
  full-height outside walls. A floor inside the roof doesn't count, so the project may be fine.
  A tool that read "three stories" in the everyday sense would turn this person away wrongly.

The Town's standing practice is to look for any way to allow a project, to suggest tweaks that
make it conform, and to say "no" only when every option is exhausted. The portal should behave
the same way.

## 2. What it is, and what success means

The portal becomes **a guide that helps residents build a permittable application**. The finished
application is the record of that guidance.

**Success in a year (the chair's words):** applicants who used it tell the Town how easy it was to
get their permit.

**Goals**
- Start from what the person wants to do, in their own words, and translate it into the Code's
  terms for them. Never make them pick a Code category to begin.
- Explain every limit in plain language: what it is, why it exists, and where it is in the Code.
- When something doesn't fit, offer the nearest version that does.
- Reach "you don't need a permit" or "you're already covered" when that's the truth, and count it
  as success.
- Give the CEO and the Board an application they can review quickly, with the judgment calls
  surfaced first.
- Over time, show the Board where the Code pinches, as evidence for amendments (§9).

**Non-goals**
- The portal does not decide. It never approves or denies, and it never settles a question of
  judgment (§5). The CEO and the Board still do.
- It does not replace talking to the Town. A path to the CEO is always visible.
- It is not a general chat assistant. It talks only about this project, this lot and this Code.

**Anti-goals (what would make it a failure even if it works)**
- **A false "no"**: turning someone away because an everyday word was read in its everyday
  sense, not the Code's. This is the worst error, because the Town never hears about it.
- **Inconsistency**: two people asking the same question and getting different explanations.
- **Silent wrong assumptions** about the lot, stated as fact.
- **Hedged non-answers** ("your town may have more restrictions") where the Town has the answer.

## 3. Decisions the chair has made (2026-10-29 and 2026-10-30)

1. **A conversation** like a helpful Board member (mockup B). The lot drawing appears inside the
   answers when *where* matters.
2. **It opens the way a Board review does.** After the lot and contact details, the first
   question is "Tell us what you'd like to do, in your own words."
3. **Applicant screens may explain and cite.** This is a guidance tool, so plain-language
   explanations and Code references belong on applicant screens. This reverses the earlier rule
   that kept Code citations and verdict words off them (§10.3).
4. **Both a guided path and a bounded AI** (§5): clear numeric standards go through guided steps
   worked out by the rulesets; the AI handles the nuanced parts, inside tight limits.
5. **Absolute consistency.** The AI never writes explanations. It chooses from a library of
   explanations the Town has approved. A question with no approved answer goes to the CEO, and the
   answer joins the library (§6).
6. **Your own words, plus pictures.** The opening sets the text box beside pictures of common
   projects, and the app then confirms its reading in the Code's terms with Yes/No buttons (from
   the research).
7. **Full scope from the first version.** Every kind of project the Code covers, not a starter
   set.
8. **The review packet** opens with a summary, then the back-and-forth with the app, then one
   master checklist with judgment items sorted to the top and highlighted (§7).
9. **The app's records are evidence for amending the Code** (§9).
10. **The look is Material**, built with Material UI (MUI), with a swappable theme layer (§10).
11. **The way forward:** this experience design first, then the other four in turn (§11).

The chair accepted four more recommendations the same day, after a reviewer read the draft:

12. **The lot drawing never decides.** The applicant enters measured distances. The drawing starts
    from the tax map, is labeled approximate, and shows the applicant's numbers. The applicant
    confirms which lot line is the front (§4.1, §4.4).
13. **One public launch, at full scope.** The portal is built in stages on the VM and opened to
    the public only when the whole Code is covered (rulesets and approved library) and the CEO
    handoff works (§11). The current HeroUI wizard and task-list screens are then retired, not
    restyled in MUI.
14. **The portal's conversations are a new decision** about sending content to an outside AI. The
    2026-08-21 decision on filed applications (D-0025) does not stretch to cover them. Until the
    chair decides, the AI does not read applicants' words (§4.2, §12).
15. **The pictures are drawn in-house** as vector graphics in one consistent style. The chair
    approves a sample sheet before the full set is made (§4.2, §6).

## 4. The applicant's journey

Sign-in stays as it is (emailed link; a person signs in before starting anything). A project is
still one unit, sent together and locked by staff. What changes is everything the applicant sees
between starting and sending.

### 4.1 The lot, and what the Town already knows

The person gives the map-lot (or finds it on the map) and their contact details, saved once on
their account as today. The app then says **what it believes about the lot** and asks them to
confirm before anything depends on it:
- the district or districts, and any overlay (shoreland included, where the data has it);
- the lot's size and frontage from the parcel data, labeled approximate (they come from the tax
  maps, not a survey);
- which lot line is the front, which the applicant confirms or changes;
- the buildings already there, as far as the Town knows;
- uses and permits already on record for the lot, where the Town has them;
- anything the data can't tell, said plainly as unknown, never guessed.

Each item has a Change or "That's not right" path. A correction is recorded and shown to staff.
(This is PlanX's "Here's what we know" step. The research found that a silent wrong assumption is
what loses a resident's trust.)

### 4.2 "Tell us what you'd like to do"

One open question with a text box. Beside it, **pictures of common projects** drawn in the
illustrated style of the UK Planning Portal's house, made Newcastle's own: a house and lot with
tappable features (deck, addition, garage or shed, driveway, new house, fence or wall, sign,
business at home, change of use and so on). The full set comes from the Code and the library
(§6), not from this list. Tapping a picture starts the same conversation as typing, so a person
who struggles to write never has to. The pictures are drawn in-house as vector graphics in one
style, from a sample sheet the chair approves first (decision 15).

**Until the chair decides whether the AI may read applicants' words (decision 14, §12):** the text
box stays on screen and what the person writes is kept with the project for staff to read, but
nothing interprets it. The pictures start the conversation, and the "So you mean…" step confirms
the picture's reading instead of the text's.

### 4.3 "So you mean…": confirming the reading in the Code's terms

**This is the most important screen in the app.** After the person describes the project, the app
states what it understood, in the Code's terms, and asks Yes/No:

> So you'd like to serve meals to guests. Your Inn already has a permit to serve food, and it
> doesn't say which meals. Is this the same kitchen and dining room you use now?
> [Yes, same rooms] [No, somewhere new]

Rules:
- **The Code's definitions win over plain English.** Any everyday word the Code defines (story,
  structure, lot, frontage, footprint, use names) is flagged and confirmed in the Code's sense
  before a number is checked.
- **The sentence is assembled from approved wording.** The AI's job is to extract the facts
  (use = serving food; rooms = existing). The sentence the person reads comes from approved
  templates and library entries, so its wording never varies between people (§5).
- **When in doubt, ask; never refuse.** If something can be read two ways, ask the question that
  could lead to yes.
- **"I'm not sure yet"** is always an answer, and it never ends the conversation.

### 4.4 Shaping the project

A conversation of short turns. Each turn is one question with tappable answers, plus suggestion
chips and a box to type more (the Material mockup). Inside it:

- **Guided steps for every clear standard** (setbacks, height, stories, footprint, lot coverage,
  frontage, whether a use is allowed in the district), worked out by the rulesets. Numbers are
  entered with controls suited to them (number fields, steppers, sliders), showing the limit and
  the room left as the value changes.
- **The lot drawing appears when *where* matters**: the lot, the water and other constraints,
  existing buildings, and the areas where the project can go, drawn on the person's own parcel.
  **The drawing never decides** (decision 12). The applicant enters measured distances (to each
  lot line, to the water); the rulesets check those numbers, and the drawing shows them on a
  tax-map outline labeled approximate. Sizes can be set with sliders or number fields, and
  dragging in the drawing only changes the entered numbers, which the person sees. A live
  checklist beside the drawing ticks each standard as the entered numbers meet it (from Symbium,
  the research's best example of this).
- **A "why" on every limit**, as a card in the illustrated-house format: the answer in one line,
  each condition as one short sentence with one number, a small picture where it helps, and
  "Read it in the Code ›" one tap away (§6).
- **A numbered step bar** at the top ("Step 3 of 6 · The building"), borrowed from the civic look.
  Its steps come from the project, so its length can change as the project takes shape.
- **Save and come back** at any point, as today.

### 4.5 When something doesn't fit

A limit is never shown as a red error. It gets its own page (GOV.UK's pattern, and the Town's
practice):
- the requirement, in neutral words, from the library;
- the gap, in numbers ("4 feet over the side setback");
- one or two **nearest versions that would work**, each applicable with one tap (shift it, shrink
  it, move it to the road side, lower it);
- "Talk to the Town Office" always available.

A "no" is allowed only after every path to yes has been checked, and it always comes with the
nearest alternative or a handoff to the CEO. **An uncertain "no" is never shown as a result.** It
becomes a question for the CEO.

### 4.6 The endings

Every conversation ends in one of these, each a success in its own right:

1. **You don't need a permit**, with the conditions that keep it true. (Whether the Town confirms
   this in writing is an open question for counsel and the Board, §12.)
2. **You're already covered** by an existing permit or established use, with the basis.
3. **Your application is ready to send**: the project, the permits it needs (as the projects brief
   defines them), the fees, then "Check and send".
4. **This needs the Town's judgment**: what the app could settle, what it couldn't, and the
   question going to the CEO, with the conversation attached.
5. **Not here, but…**: when no version works on this lot, say so plainly and show what the
   district does allow.

### 4.7 Check and send

A summary grouped into sections, each with a Change link back into the conversation (GOV.UK's
"check your answers"), then the fees and "Send to the Town". The projects brief's sending, lock
and fee rules stand.

### 4.8 Phone and computer

Phone first: one column, as in the mockup. On a computer, two columns: the conversation on the
left, the project summary and lot drawing on the right. Keyboard use and wider panes serve repeat
applicants (builders, surveyors) as today.

## 5. Who does what: the guided path, the AI, and people

| Job | Done by |
|---|---|
| Work out any number, limit or whether a use is listed in a district | **The rulesets**, always |
| Read the person's words; extract facts to confirm; notice which standards interact; choose which library entries to show and in what order; suggest tweaks | **The bounded AI** |
| The words the person reads | **Approved library entries and templates**, never AI-written text |
| Judgment calls (does this use fit that category; a standard the Board interprets) | **The CEO or the Board**, by handoff |
| New questions the library can't answer | **The CEO**; the answer becomes a library entry |

Rules for the AI:
- It **never sets a value** and never decides whether a standard is met.
- Anything it concludes is **a suggestion the person confirms**, and the rulesets then check it.
- It works only from the person's project, the lot data, the rulesets and the library. It answers
  nothing outside them.
- **Consistency is tested, not assumed.** The same description, run many times, must produce the
  same extracted facts and the same library entries. Where it can't be made consistent, that
  step becomes a guided question instead.

The AI's design (which model, how it is bounded and tested, what is sent where and what is kept)
is the third design (§11).

## 6. The explanation library (interface only; its own design follows)

Every explanation an applicant or reviewer reads comes from one library of entries the Town has
approved. This section fixes what the experience needs from it. Its own design settles how
entries are drafted, approved, stored and corrected.

Each entry has:
- **a plain-language answer**, in the illustrated-house card format (answer first; each condition
  one short sentence with one number; detail one tap away);
- **why the rule exists**, in a sentence or two;
- **its Code section or sections**, as real citations;
- **a picture** where it helps (the attic diagram in the mockup is the model);
- **a version, the approver and the date**;
- **the line "The adopted Code governs if anything here differs from it."**

Coverage at launch is **every standard in the Code**, because the first version covers every kind
of project (decision 7). Drafting and approving the library is the largest single piece of work in
the project. The expected approach is AI-drafted entries approved in batches by Article, as the
chair approved the form entries, but the library's design settles it.

Interpretations become entries. The Inn ruling (serving food covers every meal) would be one, so
the next B&B gets it right.

## 7. The review packet

What the CEO or the Board sees for each project, in this order:

1. **Summary.** The applicant's own words, unedited. A short plain statement of the project in the
   Code's terms. **Who decides**: the CEO alone or the Board.
2. **The back-and-forth.** The conversation between the applicant and the app, highlighting the
   moments where they confirmed a reading, chose "I'm not sure", or accepted a tweak. (Whether it
   is shown chat-style is still open; the staff-side design settles it.)
3. **The master checklist.** Every standard that applies: what's required, what's proposed, and
   the same library entry the applicant saw. **Items needing judgment are sorted to the top and
   highlighted.** Routine passes are folded below them.
4. **The lot drawing** with the project on it and the limits shown.

The applicant can see the same packet, without staff notes, so nothing in the review comes as a
surprise. Corrections the applicant made to the lot data (§4.1) are flagged in it.

## 8. The CEO handoff

When the app can't settle something, the person can send the question to the CEO from where they
are, with the conversation and the project attached. The CEO answers. If the answer is general,
it goes through approval into the library. The staff-side design (§11) settles the inbox, the
timing and the approval path.

## 9. The Code-patterns view for the Board

Every time an applicant hits a limit, backs up, takes a suggested tweak or sends a question to
the CEO, that is a data point about where the Code pinches. A Board-facing view gathers them
across all projects:
- which standards people run into most;
- which ones they work around the same way (a sign the rule may be wrong or unclear);
- which defined words are most often read in their everyday sense;
- which questions keep reaching the CEO.

**It shows counts and patterns, never a named person's attempts.** What is kept and for how long
depends on whether these records are public records under Maine law. That is a question for
counsel (§12), and the patterns view's design waits on the answer.

## 10. The look

### 10.1 Material, built with MUI

The interface follows Material Design, built with **Material UI (MUI)** for React (chosen
2026-10-30, replacing HeroUI and the macOS/iOS direction of 2026-10-23). The mockup was drawn in
Material 3's style. *Builder to confirm:* how far MUI's current components follow Material 3. The
theme should come as close to the mockup as MUI allows without building a parallel component set.

Borrowed pieces, done Material's way:
- the numbered step bar (from the civic look);
- tappable answer lists (from iOS);
- suggestion chips;
- the illustrated-house "why" card.

### 10.2 A swappable theme layer

Colors, fonts, corner rounding, spacing and density are all named theme settings from the start.
Every screen draws only from them, so the look can be warmed, cooled or rebranded later without
rebuilding screens. **Behavior is not themeable**: there is one way of asking questions and moving
around, so help pages, screenshots and phone support all describe the same app. The Town seal
stays available (chair, 2026-10-23).

### 10.3 Words on screen

Plain, calm, about an 8th-grade reading level, written to the person ("you"). Code terms appear
with their plain meaning beside them. The earlier rule against verdict words on applicant screens
is revised:

- **Allowed:** saying that a proposal fits a standard as the rulesets work it out ("within the
  limit", "fits"), and citing the Code.
- **Never:** "approved", "denied", "permit granted", or anything else that reads as the Town's
  decision, outside a recorded staff decision.

The test that enforces the old word list is rewritten to match. *Builder's call:* the exact list,
for the chair to approve.

### 10.4 Accessibility

As today: WCAG 2.1 AA, checked by axe in the Playwright journeys; usable one-handed on a phone;
large targets; no time limits. The lot drawing and the illustrated house each need a non-visual
equivalent, a list of the same features and limits.

## 11. The five designs, in order

| # | Design | Depends on | What it settles |
|---|---|---|---|
| 1 | **The experience** (this document) | — | The journey, screens, endings, packet shape, look |
| 2 | **The explanation library** | 1 | Entry format, drafting and approval at full scope, versioning, correction, templates for "So you mean…" |
| 3 | **The bounded AI** | 1, 2 | Model and vendor, what it may read and output, the consistency tests, data handling |
| 4 | **The staff side** | 1, 2 | The review packet in full, the CEO inbox and handoff, how answers join the library |
| 5 | **The Code-patterns view** | 1, 4; counsel's answer on records | What is recorded, kept and shown to the Board |

The experience is built in stages on the VM once its plan is written. It can run on the rulesets
and a first slice of the library before the AI exists: the guided path works without it, and the
opening starts with the pictures (§4.2).

**Before anything else, the rulesets need work.** The district standards in
`districts.json` are stored as display text ("100 ft min"), not as values a program can check.
Turning every standard the guided path uses into checkable rules is early work in this design's
plan, and the coverage audit (§12, item 7) sizes it.

**Every word an applicant reads is approved** before the public sees it, as the form entries
were: questions, answer buttons, chips, templates and library entries. Drafting the full-scope
set of questions and answers belongs to the library design (2). This design's plan builds the
conversation itself and runs it on draft wording, which the existing draft gate keeps out of
production.

**The public launch is one event** (decision 13). The portal opens to residents only when the
whole Code is covered (checkable rulesets and an approved library for every standard) and the
CEO handoff from the staff design (4) works. Until then it runs only on the VM. At launch the
HeroUI wizard and task-list screens are retired.

## 12. Open decisions (not for the builder to guess)

**For counsel**
1. How Maine law treats a resident's reliance on what the portal tells them, and what the Town
   should say about it.
2. Whether the Town gives written confirmation for "you don't need a permit" and "you're already
   covered", and what weight the portal's answer carries without it.
3. Whether conversation records and patterns are public records, and how long they must or may be
   kept.

**For the chair or the Board**
4. Who approves library entries: the chair, the Board, or the CEO for some kinds.
5. Which judgment calls always go to the Board and which the CEO can settle (the packet's "who
   decides").
6. **Whether applicants' conversations may be sent to an outside AI** (decision 14). This is new
   and separate from D-0025, which covered filed applications. A conversation may hold a
   resident's unfiled ideas. The bounded AI's design (3) waits on this answer, and until it is
   made the AI reads nothing the applicant writes.

**Facts to establish (the builder audits these and reports; nothing is guessed)**
7. **Ruleset coverage for full scope.** Which standards and kinds of project the adopted-v1.0
   ruleset already expresses, and which must be added before the portal can guide them.
8. **Shoreland.** Whether the shoreland standards (setback, expansion and footprint limits) sit in
   the CZC and its ruleset or in a separate ordinance, and what data maps the shoreland zone. The
   chair's example limits are examples, not values to encode.
9. **Existing permits and established uses on record**, by lot: whether the Town has them in a
   form the portal can read (needed for "you're already covered").

## 13. What carries over and what is replaced

**Carries over:** accounts and sign-in; projects as one unit, the lock and sending; storage and the
audit log; uploads and virus scanning; the Town's fee schedule and the Code's clocks; the
rulesets; the parcel, district and Street Type data; the chair's approved form entries, as the
official form's content; the API where it fits.

**Replaced:** the web app's screens and components (HeroUI, the iOS look, the task-list dashboard
and wizard), retired at the public launch rather than restyled (decision 13);
`portal/web/PRODUCT.md` and `DESIGN.md`, rewritten for this direction; the verdict-word test
(§10.3).

**Where it is built:** from `main`, which has the HeroUI redesign and projects merged (PRs #20 and
#21, 2026-10-29).

**Builder's latitude:** how the conversation is stored; whether the official form is generated
from the conversation or alongside it; the component breakdown; the order of building within the
experience; how the step bar's steps are derived. All of these are settled in the plan, consistent
with this document.
