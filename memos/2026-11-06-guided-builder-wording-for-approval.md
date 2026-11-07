# MEMORANDUM

**To:** Ben Frey, Planning Board chair
**From:** Applicant Portal build (guided builder, plans 3 and 4)
**Date:** November 6, 2026
**Re:** The guided builder's wording, for approval
**Status:** **Answered on 2026-11-06 and built** (branch `portal-guided-4-drawing`). All approved except `covered` and `try_guide`, with six changes and a new form field (see "The chair's decisions"). Before the answers, 39 entries in the guide's definitions and 75 of the screens' 100 lines were draft.

---

The guided builder (spec `specs/2026-10-30-applicant-portal-guided-builder.md`, §11) shows the public only approved words. This memo lists every word it says: the questions and their help, the answers, the endings, the "Why" explanations, the labels under the opening pictures, and the screens' own words. Each one shows what applicants read and its status. The entries you approved on 2026-11-05 are listed as approved, so the record is complete.

The listing in sections 1–6 was generated from the definition files and `words.ts` as committed on branch `portal-guided-4-drawing` (b7c6e32), so it matches what the screens show. Nothing in it was retyped.

**Out of scope.** The use groups, their plain names and examples (approved with the screener on 2026-10-20). The application forms' own words (approved 2026-10-28). The pictures themselves (plan 5).

**How approval is recorded.** For an entry in `portal/api/portal_api/guide/definitions/`, `status: draft` becomes `status: approved`, with `approved_by: "Ben Frey, Planning Board chair"` and `approved_on`. Production refuses any conversation that would show a draft entry. The screens' words carry one status for the whole file (`WORD_STATUS` in `words.ts`). It changes to approved once every line in section 6 is approved. Every guide screen shows a "Draft wording, not approved" chip today. Approving `words.ts` makes the chip follow that status, so it comes off.

## The chair's decisions (2026-11-06)

Taken in interview on 2026-11-06. The proposals behind them follow under "Decisions for the chair". These decisions are built. The listing below is the record that was approved, so it shows the wording as it was before the decisions, and the statuses from before 2026-11-06. The new field is in the forms approval record (`memos/2026-10-21-application-forms-for-approval.md`).

1. **Secondary front setback.** A new field on the Small Project Plan form, approved as proposed:
   - Printed label: "Secondary front setback".
   - Question: "How far will it be from the lot line along the other road?"
   - Help: "On a corner lot, in feet, from the lot line along the other road to the closest part of the building."
   - Asked only on a corner lot, in place of "other side", which a corner lot is no longer required to fill in. Same number rules as the other setbacks.
2. **`town_judgment` body:** "Here is what we could settle and what we couldn't." Restore the sending sentence when the staff handoff is built.
3. **`ready` body:** "Here is what your project needs from the Town."
4. **`setback_front`:** "How far will the house be from the front lot line?"
5. **`reply_placeholder`:** "Anything the Town should know?"
6. **`lot_map_lot`:** "Map / Lot".
7. **`covered` and `try_guide`** stay drafts. Every other draft line in this memo is approved as written, with the changes above, by Ben Frey, Planning Board chair, on 2026-11-06.

## Decisions for the chair

You can approve the rest as written in the same answer.

1. **The secondary front setback on the form.** On a corner lot the guide asks "How far will it be from the lot line along the other road?" in place of "And from the other side lot line?". The approved application form has no field for the answer, and its required "other side" field stays empty, so Check and send lists it as missing.
   - **(a)** Add a "Secondary front setback" field to the Building Form. Its wording would come to you for approval. Recommended: the Code names this setback, and staff read it from the form.
   - **(b)** Write the answer into "other side".
2. **"This needs the Town's judgment" (`town_judgment`).** Its body says "Your questions go to the Code Enforcement Officer with this conversation." You ruled on 2026-11-05 that this ending saves the project and sends nothing until the staff handoff exists. The screen's own line already says "You can talk this through with the Town Office. Your project and this conversation are saved." Proposed body: "Here is what we could settle and what we couldn't." Restore the sentence when the handoff is built.
3. **"Your application is ready to send" (`ready`).** Its body promises "what it costs", but until the fee rules are in, the fees section says "Your fees show here once the Town's rules for them are ready." Proposed body: "Here is what your project needs from the Town." The fees section speaks for itself.
4. **The front setback question (`setback_front`).** "How far will the house be from the front lot line, the one along the road?" On a corner lot, both lines are along a road. Proposed: "How far will the house be from the front lot line?" The drawing marks the front.
5. **The notes box (`reply_placeholder`).** The interview put the box as "Anything the Town should know?". The screen says "Anything else the Town should know?". Pick one. Recommended: "Anything the Town should know?", since it is the only box.
6. **"Map-lot" (`lot_map_lot`).** The approved forms write "Map / Lot". Proposed: "Map / Lot" here too, so the two match.
7. **Two entries to leave as drafts.**
   - "You're already covered" (`covered`) is never shown: the Town has no permits on record by lot, and that work is parked.
   - "Try the guided version (preview)" (`try_guide`) appears only on the LAN copy's dashboard.

   Neither one blocks the production gate while it isn't shown. They need no approval now. `try_guide` is removed before launch, so `WORD_STATUS` can turn without it.

The banned words ("approved", "denied", "granted", "rejected", "permit issued", "compliant", "violates"), which you approved on 2026-11-05, appear in none of the lines below. The chip's "not approved" is the one exception. It shows only while wording is draft, and it goes when this memo is approved.

## 1. The questions

In the order the guide asks them. Every question also offers “I'm not sure yet” (`unsure`, section 2).

### “Here's what the Town knows about your lot. Is it right?” (`lot`)

- Step: Your lot
- Asked: Every conversation, first.
- Help: The size and frontage come from the tax maps, not a survey, so they are approximate.
- Answers: “Yes, that's right” · “That's not right”
- Draft.

### “Which lot line is the front?” (`front_line`)

- Step: Your lot
- Asked: A new house, on a lot the tax map draws.
- Help: The front is the line along a road, or along water, an easement, a right of way or a civic space. We've drawn the lot from the tax map.
- Answers: each lot line along a road, as `front_along` or `front_along_length` (on a corner lot only the Code's front, as `front_primary`), and `front_other`
- Approved by Ben Frey, Planning Board chair, on 2026-11-05.

### So you mean… (`confirm`)

- Step: Your project
- Asked: Every conversation, after the lot.
- Applicants read: (from the opening's template: `confirm_build` or `confirm_use`, section 2)
- Answers: “Yes, that's right” · “No, something else”
- Draft.

### “How many full stories will the house have?” (`full_stories`)

- Step: The building
- Asked: A new house.
- Help: Count the floors whose outside walls are full height. Don't count a basement or a floor inside the roof yet.
- Answer: a number, 1 to 4; checked against the district's limit
- “Why” opens: `how_stories_count` (section 4)
- Draft.

### “How many floors will be inside the roof?” (`roof_floors`)

- Step: The building
- Asked: A new house.
- Help: A finished attic, or rooms under the roof slope. Enter 0 if none.
- Answer: a number, 0 to 2
- “Why” opens: `how_stories_count` (section 4)
- Draft.

### “On the top floor inside the roof, does the roof meet the wall more than 3 feet above the floor?” (`top_knee_over_3ft`)

- Step: The building
- Asked: A new house with a floor inside the roof.
- Help: Measure from the finished floor up to where the rafters sit on the wall.
- Answers: “Yes, more than 3 feet” · “No, 3 feet or less”
- “Why” opens: `how_stories_count` (section 4)
- Draft.

### “Will 5 feet or more of a basement wall show above the ground along the front?” (`basement_exposed_5ft`)

- Step: The building
- Asked: A new house.
- Answers: “Yes, 5 feet or more” · “No, or there's no basement”
- “Why” opens: `how_stories_count` (section 4)
- Draft.

### “What is the floor area of the main part of the house, in square feet?” (`floor_area`)

- Step: The building
- Asked: A new house.
- Help: Add up every story of the main part. Space inside the roof doesn't count. An estimate is fine for now.
- Answer: a number sq ft, 1 to 1000000
- Draft.

### “How many homes will it have?” (`dwelling_units`)

- Step: The building
- Asked: A new house.
- Help: A house with an apartment in it has 2.
- Answer: a number, 0 to 100
- Draft.

### “How far will the house be from the front lot line, the one along the road?” (`setback_front`)

- Step: Where it sits
- Asked: A new house.
- Help: Measure in feet from the lot line to the closest part of the house.
- Answer: a number ft, 0 to 50000; checked against the district's limit
- “Why” opens: `setbacks` (section 4)
- Draft.

### “How far will it be from the nearest side lot line?” (`setback_side_1`)

- Step: Where it sits
- Asked: A new house.
- Help: Measure in feet from the lot line to the closest part of the house.
- Answer: a number ft, 0 to 50000; checked against the district's limit
- “Why” opens: `setbacks` (section 4)
- Draft.

### “And from the other side lot line?” (`setback_side_2`)

- Step: Where it sits
- Asked: A new house, except on a corner lot.
- Help: Measure in feet from the lot line to the closest part of the house.
- Answer: a number ft, 0 to 50000; checked against the district's limit
- “Why” opens: `setbacks` (section 4)
- Draft.

### “How far will it be from the lot line along the other road?” (`setback_secondary`)

- Step: Where it sits
- Asked: A new house on a corner lot.
- Help: On a corner lot, the Code sets a secondary front setback along the other road. Measure in feet from the lot line to the closest part of the house.
- Answer: a number ft, 0 to 50000; checked against the district's limit
- “Why” opens: `setbacks` (section 4)
- Draft.

### “How far will it be from the rear lot line?” (`setback_rear`)

- Step: Where it sits
- Asked: A new house.
- Help: Measure in feet from the lot line to the closest part of the house.
- Answer: a number ft, 0 to 50000; checked against the district's limit
- “Why” opens: `setbacks` (section 4)
- Draft.

### “Which of these is closest to what you have in mind?” (`use_group`)

- Step: The use
- Asked: A change of use.
- Answers: the use groups, in the plain names approved with the screener
- “Why” opens: `use_table` (section 4)
- Draft.

### “Which one, in the Code's words?” (`use_key`)

- Step: The use
- Asked: A change of use, once its group is picked.
- Help: Each is the Code's own name for the use, with an example.
- Answers: each use in the group under its Code name, with its example, as approved with the screener
- “Why” opens: `use_table` (section 4)
- Draft.

## 2. The guide's shared words

Answers every question offers, the “So you mean…” templates, and the words that fill them. `{slots}` are filled in from the project.

| Key | Applicants read | Status |
|:---|:---|:---|
| `unsure` | I'm not sure yet | Draft |
| `talk_to_town` | Talk to the Town Office | Draft |
| `keep_mine` | Keep my number and ask the Town | Draft |
| `nearest` | Make it {value} {unit} | Draft |
| `doesnt_fit` | That's {gap} {unit} {direction} the limit here. Here's the nearest version that fits. | Draft |
| `direction_over` | over | Draft |
| `direction_short` | short of | Draft |
| `governs` | The adopted Code governs if anything here differs from it. | Draft |
| `front_along` | The line along {street} | Approved 2026-11-05 |
| `front_along_length` | The line along {street}, about {n} ft | Approved 2026-11-05 |
| `front_primary` | The line along {street} (the Code's front) | Approved 2026-11-05 |
| `front_help_corner` | Your lot is on more than one road. The Code makes the front the line along the busier road, by its Type. | Approved 2026-11-05 |
| `front_other` | A different line | Approved 2026-11-05 |
| `pick_opening` | What would you like to do? | Draft |
| `district_unknown` | a district the Town's map doesn't show | Draft |
| `map_lot_unknown` | (not found) | Draft |
| `confirm_build` | So you'd like to build {opening} on lot {map_lot}, in {districts}. Is that right? | Draft |
| `confirm_use` | So you'd like to change how lot {map_lot}, in {districts}, is used. Is that right? | Draft |

## 3. The endings

Where every conversation ends (spec §4.6). Each has a title and one sentence or two under it.

### “You don't need a permit for this” (`no_permit`)

- Body: As you've described it, the Code doesn't call for a review. Keep to what you told us. If anything changes, or you're unsure, ask the Town Office before you start.
- Draft.

### “You're already covered” (`covered`)

- Body: What you have on record already allows this.
- Draft.

### “Your application is ready to send” (`ready`)

- Body: Here is what your project needs from the Town, and what it costs.
- Draft.

### “This needs the Town's judgment” (`town_judgment`)

- Body: Here is what we could settle and what we couldn't. Your questions go to the Code Enforcement Officer with this conversation.
- Draft.

### “Not here, but…” (`not_here`)

- Body: No version of this use fits your lot's district. Here is what the district does allow.
- Draft.

## 4. The explanations (“Why”)

The first slice of the explanation library (spec §6). Each opens from the questions named in section 1.

### Why · how stories are counted (`how_stories_count`)

- Answer: Only floors with full-height outside walls count.
- Detail: Living space inside a pitched roof is not a story. If there is more than one floor inside the roof, all but the top one count. The top one counts if the roof meets the wall more than 3 feet above its floor. A basement counts if 5 feet or more of its wall shows above the ground along the front.
- Why: Height limits keep buildings in scale with their street. Counting only full walls lets people use the space under a roof.
- Cites: Art. 5 §7.c.3, Art. 5 §7.c.4, Art. 5 §7.c.5, Art. 5 §7.c.6
- Draft.

### Why · how far from the lot lines (`setbacks`)

- Answer: Each district sets how far a building sits from the lot lines.
- Detail: Measure from the lot line to the closest part of the building, in feet.
- Why: Setbacks keep light, air and room between neighbors, and keep the street's line.
- Cites: Art. 2 §3.c.3
- Draft.

### Why · uses by district (`use_table`)

- Answer: The Code lists which uses each district allows, and which permit each one needs.
- Detail: Your lot's district decides which list applies.
- Why: Each district has its own purpose, so each allows its own set of uses.
- Cites: Art. 8 §15.b.1
- Draft.

### Why · a use the district doesn't list (`use_not_listed`)

- Answer: The Code doesn't list this use in your lot's district.
- Detail: The Code doesn't allow a variance for a use. The Code Enforcement Officer can talk you through your options.
- Why: Which uses go where is set by the Town Meeting, not case by case.
- Cites: Art. 8 §19.b.1
- Draft.

## 5. The pictures a conversation starts from

The labels under the pictures (the pictures themselves are plan 5).

| Key | Applicants read | Status |
|:---|:---|:---|
| `new_house` | A new house | Draft |
| `change_of_use` | A change of use | Draft |

## 6. The screens' own words

Every word the guide's screens say themselves (`portal/web/src/guide/words.ts`), grouped as the file groups them. The lot drawing's words were approved on 2026-11-05; the rest are draft.

### The app bar and the page around the conversation

| Key | Applicants read | Status |
|:---|:---|:---|
| `back_to_project` | your project | Draft |
| `back_a_turn` | the last question | Draft |
| `back_to_conversation` | the conversation | Draft |
| `your_project` | Your project | Draft |
| `close` | Close | Draft |
| `loading` | Loading your project… | Draft |
| `pick_opening` | What would you like to do? | Draft |

### The lot as the Town knows it

| Key | Applicants read | Status |
|:---|:---|:---|
| `lot_map_lot` | Map-lot | Draft |
| `lot_districts` | District | Draft |
| `lot_acres` | Lot size | Draft |
| `lot_frontage` | Road frontage | Draft |
| `approximate` | approximate, from the tax maps | Draft |
| `unknown` | The Town doesn't know this yet | Draft |
| `acres` | acres | Draft |
| `ft` | ft | Draft |

### Numbers

| Key | Applicants read | Status |
|:---|:---|:---|
| `next` | Next | Draft |
| `unsure` | I'm not sure yet | Draft |
| `less` | Less | Draft |
| `more` | More | Draft |
| `not_a_number` | Please enter a number, like 25 or 1,800. | Draft |
| `out_of_range` | That number is outside what this question takes. | Draft |
| `room_left` | Within the limit · {room} {unit} to spare | Draft |
| `at_limit` | Within the limit, right at it | Draft |
| `past_limit_over` | {gap} {unit} over the limit here | Draft |
| `past_limit_short` | {gap} {unit} short of the limit here | Draft |
| `town_decides` | The Town will look at this one | Draft |
| `limit_mark` | Limit | Draft |

### The conversation

| Key | Applicants read | Status |
|:---|:---|:---|
| `reply_placeholder` | Anything else the Town should know? | Draft |
| `notes_kept` | The Town Office will read this. The guide's questions don't change because of it. | Draft |

### Notices

| Key | Applicants read | Status |
|:---|:---|:---|
| `notices.changed_elsewhere` | This project changed in another window, so we've brought this page up to date. | Draft |
| `notices.try_again` | That answer didn't go through. Please try again. | Draft |
| `locked` | The Town is reviewing this project, so it can't be changed now. | Draft |
| `reopened_one` | Changing that answer reopened 1 later question | Draft |
| `reopened_many` | Changing that answer reopened {n} later questions | Draft |

### Your project

| Key | Applicants read | Status |
|:---|:---|:---|
| `change` | Change | Draft |
| `fits_mark` | Fits | Draft |
| `for_the_town` | For the Town | Draft |

### The endings

| Key | Applicants read | Status |
|:---|:---|:---|
| `settled_heading` | What we could settle | Draft |
| `unsettled_heading` | What goes to the Town | Draft |
| `reviews_heading` | What your project needs | Draft |
| `may_apply_heading` | May also apply, depending on answers the Town's form still asks | Draft |
| `fees_heading` | Fees | Draft |
| `application_fees` | Application fees, due when you send | Draft |
| `permit_fees` | Permit fees, due later | Draft |
| `fee_varies` | Set by the Town Office | Draft |
| `fees_unknown` | Your fees show here once the Town's rules for them are ready. | Draft |
| `check_and_send` | Check and send | Draft |
| `no_permit_keep` | Keep to what you told us. If anything changes, ask the Town Office before you start. | Draft |
| `allowed_heading` | What {district} allows | Draft |
| `talk_to_town` | You can talk this through with the Town Office. Your project and this conversation are saved. | Draft |
| `contact_town` | Contact the Town Office | Draft |
| `unsettled.not_listed` | Whether this use is listed for your lot | Draft |
| `unsettled.not_listed_in_one_district` | Your lot is in two districts, and this use is listed in only one | Draft |
| `unsettled.unsure` | An answer you weren't sure of yet | Draft |
| `unsettled.kept_past_the_limit` | A number you kept past its limit | Draft |
| `unsettled.talk_to_town` | A number you'd like to talk over with the Town | Draft |
| `unsettled.lot_disputed` | The Town's facts about your lot, which you said aren't right | Draft |
| `unsettled.no_district` | Which district rules apply to your lot | Draft |
| `unsettled.not_checkable` | A limit the guide can't check yet | Draft |
| `unsettled.two_districts` | Your lot is in two districts with different limits | Draft |
| `unsettled.unknown_input` | A number that rests on an answer you weren't sure of | Draft |
| `unsettled.board_decides` | A number the Planning Board can allow | Draft |
| `unsettled.town_only` | Work only the Town Office can review | Draft |
| `unsettled.contact_town` | Something the Town Office needs to look at | Draft |
| `unsettled.more_than_one_frontage` | Your lot is on more than one road, so the Town decides which is the front | Draft |
| `unsettled.front_not_on_a_road` | Which line is your lot's front | Draft |

### The lot drawing

| Key | Applicants read | Status |
|:---|:---|:---|
| `drawing.approximate` | Approximate: from the Town's tax map, not a survey | Approved 2026-11-05 |
| `drawing.summary` | A drawing of your lot from the Town's tax map, with {lines} lot lines. The list beside it says the same in words. | Approved 2026-11-05 |
| `drawing.line_length` | about {n} ft | Approved 2026-11-05 |
| `drawing.swap_sides` | Swap sides | Approved 2026-11-05 |
| `drawing.list_heading` | The setbacks on your lot | Approved 2026-11-05 |
| `drawing.choose_front_first` | Choose the front, and the setbacks show here. | Approved 2026-11-05 |
| `drawing.rows.front` | Front | Approved 2026-11-05 |
| `drawing.rows.side_1` | Nearest side | Approved 2026-11-05 |
| `drawing.rows.side_2` | Other side | Approved 2026-11-05 |
| `drawing.rows.rear` | Rear | Approved 2026-11-05 |
| `drawing.rows.frontage` | Along {street} | Approved 2026-11-05 |
| `drawing.rows.secondary` | Along {street}: the secondary front setback | Approved 2026-11-05 |
| `drawing.at_least` | At least {n} {unit} | Approved 2026-11-05 |
| `drawing.at_most` | At most {n} {unit} | Approved 2026-11-05 |
| `drawing.between` | {min} to {max} {unit} | Approved 2026-11-05 |
| `drawing.no_limit` | No limit to show | Approved 2026-11-05 |
| `drawing.yours` | Yours: {n} {unit} | Approved 2026-11-05 |
| `drawing.not_entered` | Not entered yet | Approved 2026-11-05 |
| `drawing.frontage_town` | Along another frontage, the Town decides the setback | Approved 2026-11-05 |
| `drawing.not_shown` | Water, buildings already there and easements aren't in the Town's map data, so they aren't drawn. | Approved 2026-11-05 |

### Check and send

| Key | Applicants read | Status |
|:---|:---|:---|
| `check_heading` | Check your project | Draft |
| `send` | Send to the Town | Draft |
| `sending` | Sending… | Draft |
| `sent` | Sent. The Town has your project. | Draft |
| `to_project` | Go to your project | Draft |
| `still_needs` | Before you send, the Town's form still needs: | Draft |
| `finish_on_form` | Fill these in on your project's form | Draft |
| `refusals.signed_out` | You've been signed out. Please sign in again. | Draft |
| `refusals.not_found` | We couldn't find this project. | Draft |
| `refusals.not_approved` | The guide isn't open yet. Please contact the Town Office. | Draft |
| `refusals.busy` | Too many requests just now. Please wait a minute and try again. | Draft |
| `refusals.unavailable` | We couldn't reach the Town's server. Please check your connection and try again. | Draft |
| `refusals.locked` | The Town is reviewing this project, so it can't be changed now. | Draft |

### The HeroUI dashboard's link in

| Key | Applicants read | Status |
|:---|:---|:---|
| `try_guide` | Try the guided version (preview) | Draft |

