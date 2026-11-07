# Guided builder: the applicant's packet (plan 6 of 6) — design

**Status:** approved by the chair (Ben Frey) on 2026-11-06. He asked for it to be written straight
from the experience design without an interview, then approved it as written, including every
*builder's call* and the two calls in §10.

**Builds on:** `specs/2026-10-30-applicant-portal-guided-builder.md` (the experience design), §7
"The review packet", decision 8, §10.4 (accessibility) and §11 (every word approved). Plans 1–5 are
built (PRs #22–#27). The staff side (design 4) and the CEO handoff (§8) are later designs.

## 1. Why

The experience design (§7) promises the resident that **"nothing in the review comes as a
surprise"**: the applicant sees the same packet the Code Enforcement Officer or the Board will
read, without staff notes. Today the resident can see their answers in the guide and on Check and
send, but nowhere sees their project the way the Town will: what was settled, what still needs
judgment, who decides, and where on the lot.

The packet is also the first half of the staff side. Staff will read the same packet, with their
notes added, so it has to be built once and shown to both.

## 2. Goals

1. **One packet, built once.** The API assembles it. The applicant's view shows it now; the staff
   view (design 4) will show the same packet, with staff notes.
2. **The four parts of §7, in order:**
   1. **Summary.** The applicant's own words, unedited. A short plain statement of the project in
      the Code's terms. **Who decides.**
   2. **The back-and-forth.** The conversation, with the moments that matter highlighted: where the
      person confirmed a reading, said "I'm not sure yet", or accepted a suggested change.
   3. **The master checklist.** Every standard that applies: what's required, what's proposed, and
      the same explanation the applicant saw. Items needing judgment come first and are
      highlighted; routine passes are folded below them.
   4. **The lot drawing,** with the project on it and the limits shown.
3. **Lot-data corrections are flagged** (§7, §4.1): where the person said the Town's facts about
   their lot aren't right, the packet says so, with their note.
4. **It prints well,** on letter paper, for the person's records and for a Board packet.
5. **The four looks findings** from the old screens (two task lists, 44 vs 36 px fields, the
   property card's spacing, "No password" shown twice) are rechecked on the new screens, as
   recorded in `OPEN_ITEMS.md`, and fixed where they recur.

## 3. Non-goals

- **Staff notes, the CEO inbox and the handoff** (§8; design 4). The packet leaves a place for staff
  notes but shows none.
- **The Code-patterns view** (§9; design 5).
- **Changing anything from the packet.** It is read-only. Changes are made in the guide or on the
  form, as today.
- **Decisions.** The packet never says a project is approved, denied, compliant and so on (§10.3).
  It says what fits, what goes to the Town, and who decides.

## 4. Anti-goals: what would make this a failure even if it works

- **The applicant's packet and the staff's packet disagree.** That is the surprise §7 exists to
  prevent.
- **The packet reads like a decision.** "Fits" is a check against a number; it is not the Town's
  ruling. Judgment items must never look settled.
- **Something the person said is changed.** Their own words are shown exactly as written,
  unedited, never summarised or corrected.
- **It only works on a big screen.** Many residents use a phone.

## 5. What the packet holds

### 5.1 Summary

- **In your own words.** Every note the person wrote, in order, unedited: the scene's box (plan 5),
  the reply box, and Check and send's box. Shown as quoted text with its date.
- **The project in the Code's terms.** The "So you mean…" sentence the person confirmed (for
  example "So you'd like to build a new house on lot 4-36, in D1 Rural"), without the question.
  *Builder's call:* this reuses the approved template's wording rather than adding a new summary
  sentence.
- **Who decides.** The approved decision sentence for each review the project needs, from
  `applications.yaml` (for example "The Code Enforcement Officer decides within 10 days of accepting
  your project"). Where no review is settled yet, the packet says the Town decides which review
  applies.
- **Lot corrections, flagged.** If the person said "That's not right" about the lot, or the
  project's property was disputed when created, the summary carries a flag and the person's note.
  The same flag sits at the top of the checklist.

### 5.2 The back-and-forth

- Every question and answer, in order, as the guide's history shows them today (plan 3), including
  questions asked again after a Change.
- **Highlighted** (*builder's call:* a marker and a short tag, never colour alone):
  - the confirmed reading ("So you mean…", answered Yes);
  - every "I'm not sure yet";
  - every suggested change the person accepted ("Make it 15 ft");
  - every number kept past its limit ("Keep my number and ask the Town").
- *Builder's call:* shown as a plain list of question and answer, not chat bubbles. It prints well
  and reads well to a screen reader. The staff design may choose chat-style later (§7 leaves it
  open).

### 5.3 The master checklist

One row per standard the guide checked for this project, from the checks the engine already
records:
- **What's required:** the limit, in the Code's terms (for example "At least 15 ft").
- **What's proposed:** the person's number.
- **Where it stands:** "Fits" or "For the Town" (needs judgment). A limit the guide can't check
  is "For the Town" with the approved reason "A limit the guide can't check yet". These are all
  the screens' existing approved words.
- **Why:** the same explanation entry the person saw, with its picture where it has one (plan 5).

**Judgment first** (§7, decision 8):
- At the top, highlighted: every item that goes to the Town, with its reason in the existing
  approved words ("A number the Planning Board can allow", "Your lot is on more than one road, so
  the Town decides which is the front", and so on).
- Then, folded under a "Fits" heading the person can open: the routine passes.

### 5.4 The lot drawing

The plan 4 drawing, read-only: the outline labelled approximate, the front, the setback strips and
the house where the person's numbers put it, with the drawing's list beside it as its text
equivalent. It is omitted, with one line saying why, when the lot has no outline on the tax map.

## 6. Where the person finds it

- *Builder's call:* a "Your packet" link:
  - on Check and send;
  - on the ending page once the guide reaches one;
  - on the project page, once the project has a conversation.
- It is available before and after sending. Before sending it is marked "as it stands now"; after
  sending, "as sent", from the project's state at sending.
- *Builder's call:* at a computer's width the four parts sit in one column with the drawing beside
  the checklist; on a phone, one column in §7's order.

## 7. One packet for both sides

*Builder's call:* `GET /api/projects/{id}/packet` returns the whole packet as data:
- summary;
- history with its highlights;
- checklist rows, with their entries;
- the drawing's data;
- the corrections.

The applicant's page renders it. The staff view (design 4) will call the same assembly with staff
notes added, so the two cannot drift. The packet is built from what the API already stores (the
conversation, its checks, the notes, the snapshot, the needs); nothing new is stored.

## 8. Constraints

- **Every new word is approved before the public sees it** (§11). New words start as drafts in
  `words.ts` (screen words) and go to the chair in a memo with a sample of the packet, as plan 5's
  sheet did. Wherever an approved word already exists (the endings' "What we could settle", the
  checklist's "Fits", the unsettled reasons, the decision sentences), it is reused.
- **The banned words** never appear (approved, denied, granted, rejected, permit issued, compliant,
  violates).
- **Never guess a legal value** (CLAUDE.md rule 6). Every limit shown comes from the rulesets
  through the API, as the drawing's do.
- **Accessibility** (§10.4): one heading per part; highlights carry a text tag, not only colour;
  the folded passes are a real disclosure button; the drawing keeps its text list; axe runs on the
  packet's journeys.
- **Print:** the packet prints in §7's order, with the folded passes opened, the app bar and
  buttons hidden, and each part starting on a fresh page where it would otherwise split badly.
- The packet stays behind `VITE_GUIDE_PREVIEW=1` until launch, like the rest of the guide.

## 9. Left to the builder

- How the API assembles the packet (one module beside the engine is expected), and its exact JSON
  shape.
- How the page reuses plan 3's history, plan 4's drawing and plan 5's entry cards.
- The print stylesheet's details.
- How "as sent" is held (from the conversation and project state at sending, or a snapshot taken at
  sending), provided the sent packet never changes after sending.

## 10. Open for the chair

1. **Who decides, when a project needs more than one review** (for example a Large Project Plan,
   where the CEO and then possibly the Board decide). *Builder's call:* show every applicable
   decision sentence, in the order the reviews run.
2. **The "as it stands now" packet before sending.** Is it useful to the resident, or should the
   packet appear only once the project is sent? *Builder's call:* show it before sending too, so
   nothing is a surprise after.
