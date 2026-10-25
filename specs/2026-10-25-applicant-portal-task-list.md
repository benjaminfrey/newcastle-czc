# Applicant Portal — tasks and cards (revision to the wizard brief)

**Status:** approved by the Planning Board chair, 2026-10-25, with the recommendations in section 11
(Back in the card's footer, a near-black Continue, Copy Building 1 as written). Section 11's fifth
point, the front-facing question, is still open from PR #20.
**Revises:** `specs/2026-10-24-applicant-portal-wizard.md` (approved 2026-10-24). Where the two
differ, this brief wins; everything it does not mention stands.
**Reference comp:** `specs/assets/2026-10-25-task-list-comp.html`, the mock-up the chair saw on
2026-10-25, recoloured with the portal's own tokens. **The build must match it.** Section 4 is that
comp written down value by value; where this text and the comp disagree, the comp wins and the text
is corrected.
**Built so far:** PR #20 (`portal-design-pass`): the window, autosave, the wizard's screen model,
tiles, "Is this right?", carried answers and the review page. This brief reuses all of them.

## 1. Why change it

The chair tried the wizard on the LAN copy on 2026-10-25. Two problems:

- **It lost the look of the mock-up he chose.** The mock-up put the question in a contained card with
  a hairline edge, and gave tiles icons. The build ran the question edge to edge on the window's
  ground, with large filled tiles, no icons, a line of intro text above, and dots that changed
  count as he answered.
- **It splits too finely.** One question per screen became one *field* per screen. A building is
  about 20 screens, and the answer trail above the question grows to four rows of chips.

What long government applications do instead (research, 2026-10-25):

- **"One thing per page" means one decision, not one field.** GOV.UK starts there, but its own
  guidance counts a small set of related questions as one thing, and teams merged fields back onto
  one page when testing showed people understood them better together.
  [GDS](https://designnotes.blog.gov.uk/2015/07/03/one-thing-per-page/) ·
  [question pages](https://design-system.service.gov.uk/patterns/question-pages) ·
  [Nava](https://www.navapbc.com/uploads/Structuring%20a%20complex%20eligibility%20form%20for%20HealthCare.gov.pdf)
- **A long application that people may not finish in one sitting is a task list.** Each task has a
  status, and each is a short run of pages.
  [GDS](https://designnotes.blog.gov.uk/2023/12/15/working-as-a-community-to-iterate-the-task-list-pattern/) ·
  [MoJ](https://design-patterns.service.justice.gov.uk/pages/task-list/)
- **Repeated things (buildings) are "add to a list".** Each item gets a short loop of questions,
  then a check page, then a summary with Change, Remove and Add another.
  [DWP](https://design-system.dwp.gov.uk/patterns/add-another-thing/how-it-works) ·
  [HMRC](https://design.tax.service.gov.uk/hmrc-design-patterns/add-to-a-list)

## 2. The shape

```
Your application (task list)
  └─ a task: 2–8 cards, one after another, sliding sideways
       └─ "Check <task>": the task's answers, each with Change
            └─ back to the task list (the next task is highlighted)
  Buildings / Additions: the list of items → an item's cards → its check → the list
  Check and send (the review page from PR #20), once every task is done
```

- **The task list replaces the step sidebar's job and the answer trail.** On a desktop the task list
  is the sidebar while a task is open; on a phone it is the home screen of the application.
- **Tasks are today's steps** (cover sheet: Your lot, About you; then each form's own steps). No
  renaming in this brief beyond the task list's short hints (section 4.2).
- **Tasks can be done in any order**, except "Check and send", which opens when every other task is
  done. A new application opens on the first unfinished task's first card (as now).

## 3. What goes on a card

**The rule:** a card holds **one decision** (a tap), **or one set of values that are read off the
same thing** (a builder's plan, a deed, a survey). Never two decisions on one card, and never a
decision and a set of values on one card, with one exception: a decision that only reveals more of
the same set (choosing a roof shape reveals the slope; choosing "Another road" reveals the road's
name).

The grouping is form content, kept in the YAML (`screens:` and each field's `screen:`, as now), so
it shows on the forms sheet and the chair approves it with the forms. The cards for each form:

**Cover sheet — Your lot** (4 cards)
1. "Is this right?" the lot's size from the Town's map (unchanged).
2. **How big is your lot?** lot width, lot depth.
3. How many homes are on the property now? (stepper)
4. **Your deed** — book and page (unchanged group).

**Cover sheet — About you** (up to 5 cards)
1. **How can the Town reach you?** full name, phone, mailing address.
2. Do you own this property? (tap)
3. **The owner** — name, email, phone, address (only if not the owner).
4. Is someone else helping, like a builder or surveyor? (tap)
5. **Who is helping** — name or company, email, phone, address (only if Yes).

**Small Project Plan — The work** (3 cards): what kind of work (multi tiles) · in a few sentences
(long text) · site plan or sketch (upload).

**Small Project Plan — each building** (8 cards, down from about 20)
1. Which best describes this building? (tap, the two-step building type as now)
2. Is it only being renovated? (tap)
3. **About this building** — what you call it (optional), how many homes (homes only).
4. **Where it sits** — the four setbacks around the lot drawing (unchanged layout).
5. **How big is it?** width, depth, floors above ground, floor area, first floor's height above
   the ground, then one height per floor, for as many floors as are entered (one to four).
6. **The roof** — shape tiles; the slope appears under them once a shape is chosen.
7. **Outside walls and roof** — material tiles (multi), with "What other material?" when Other is
   chosen.
8. **The front and the windows** — which way the front faces (four compass tiles), then the four
   walls' window shares around the compass once a direction is chosen.

**Small Project Plan — each addition, porch or deck** (6 cards): what it is (tap, with its name when
Other) · only being renovated? (tap) · which building it is attached to (tap) · **its size** (width,
depth, height) · **its roof** (shape, slope) and **its outside** (materials) as two cards · **its
front and windows**.

**Entrance Permit** (8 cards)
1. Which road? (tap; "Another road" reveals the name and Continue)
2. What are you doing? (tap)
3. **Homes using it** — single-family and two-family (unchanged group).
4. Will a neighboring lot share it? (tap; Yes adds a card for the easement upload)
5. Where it meets the road (map point).
6. **The driveway** — width, slope of the first 20 feet, angle to the road.
7. **Seeing the road** — sight distance left and right; distance to the nearest intersection, and
   whether it has a traffic light.
8. Is there a roadside ditch? · MaineDOT entrance permit (tap; Yes adds the copy upload) · sketch
   (upload) — each its own card, as now.

**Use Permit** (unchanged: each "uses" picker and each description is its own card).

## 4. How it looks — the comp, value by value

All colours are the portal's tokens (`portal/web/src/index.css`), light and dark. Two tokens are new
(section 4.8). The type is the system font, as now.

### 4.1 The window

- **Desktop (≥ 1024 px):** the sidebar (250 px, `--app-grouped-ground`, a 0.5 px `--app-separator`
  edge on its right) holds the task list rows (4.2) under the Town seal and the form's name. The
  main area is `--app-grouped-ground`, and the card (4.3) sits centred in it, **640 px wide**
  (**760 px** for the lot drawing and the compass), 32 px from the top.
- **Phone:** a top bar (44 px, `--app-grouped-ground` at 95% with blur, as now): **‹ Tasks** on the
  left, the save status on the right. Below it the card, full width less a **12 px** gutter on each
  side, filling the screen down to 12 px above the home indicator; the card's footer (4.6) sits
  at the bottom of the card, not floating over the page.
- **No answer trail and no dots.** The progress bar in the card's header replaces both.
- **No intro sentence** above a question ("Answer a few questions…" goes).

### 4.2 The task list

A card (4.3) whose header row reads the form's name (15 px, weight 500, `--app-label`) on the left
and "Map 4, Lot 36 · saved" (13 px, `--app-secondary-label`) on the right.

Each task is a row, the whole row tappable:
- 11 px × 16 px padding, a 0.5 px `--app-separator` line between rows (none above the first);
- an outline icon, 18 px, `--app-label` (section 5 names them);
- the task's name, 14 px `--app-label`, and under it an optional hint, 12 px
  `--app-secondary-label` ("Size, frontage and what is there now");
- on the right, a **status pill**: 12 px text, 2 px × 9 px padding, fully rounded:
  - **Done** — `--app-done-bg` with `--app-done-text`;
  - **"2 of 4"** (cards answered of the task's cards) — `--app-selection` with `--app-accent-text`;
  - **Not started** — `--app-fill` with `--app-secondary-label`;
- **Check and send** has no pill until it opens; until then its name, icon and hint are all
  `--app-secondary-label`, and its hint says "Opens when the tasks above are done".
- The open task's row (in the desktop sidebar) has the `--app-selection` background, as the sidebar's
  current row does now.

### 4.3 The card

- `--app-row` background, a **0.5 px `--app-separator`** border, **12 px** corner radius, no shadow,
  content clipped to the corners.
- Three bands: header (4.4), body (4.5), footer (4.6). The header and footer are separated from the
  body by 0.5 px `--app-separator` lines.
- **Only the body slides.** Moving to the next card slides the body's content in from the right,
  300 ms on the system curve (`cubic-bezier(0.32, 0.72, 0, 1)`), and Back slides it from the left;
  the card's edge, header and footer stay still. With reduced motion, a 120 ms fade (as now).

### 4.4 The header

- 10 px × 16 px padding, 13 px `--app-secondary-label`, items 10 px apart, in one row:
  1. the task's name, or in a building "Building 1 · A home" (the item and its type, once known);
  2. **the progress bar**, filling the space between: one segment per card in the task (or item),
     segments 3 px tall, 3 px apart, 2 px radius; answered and current segments `--app-label`, the
     rest `--app-edge`;
  3. "3 of 6", the current card's number of the total.
- The total is the number of cards that apply now. It can change only when an answer adds or
  removes a card (the owner's card), never as a side effect of reaching the end.
- The bar has `role="img"` and an `aria-label` of "Question 3 of 6".

### 4.5 The body

- Padding **22 px top, 24 px sides, 18 px bottom**; everything centred.
- **The question:** 20 px, weight 500, line-height 1.3, `--app-label`, at most 30 characters wide
  before it wraps (balanced).
- **The help line:** 13 px `--app-secondary-label`, 4 px under the question, 16 px above the
  control. Only where the form has help. "Choose one." / "Choose all that apply." for tiles.
- **Tiles:** a two-column grid (one column under 400 px of card width), 8 px gaps, at most 500 px
  wide, left-aligned text:
  - each tile at least 48 px tall, 10 px × 12 px padding, **0.5 px `--app-edge`** border, 8 px
    radius, transparent background;
  - an outline icon (section 5), 18 px, `--app-secondary-label`, 10 px before the label; label
    14 px `--app-label`;
  - **chosen:** a **1.5 px `--app-label`** border (padding reduced by 1 px so nothing moves), and
    the icon turns `--app-label`; no fill;
  - hover (pointer only): the border turns `--app-secondary-label`;
  - keyboard focus: a 2 px `--app-accent-text` ring outside the border.
  - A question's tiles all have icons or none have; roof shapes keep their roof drawings.
- **A set of values:** a two-column grid, at most 380 px wide, 10 px × 14 px gaps: the value's short
  name on the left (14 px `--app-label`), its field on the right (110 px wide, right-aligned, the
  unit after it in `--app-secondary-label`). Steppers are − and + buttons with the number between.
  Repeated values (one per floor) sit under a 0.5 px `--app-separator` line, 10 px below the set.
- **Fields:** 36 px tall, `--app-fill` background, no border, 8 px radius, 15 px text.
- **"I don't know some of these yet"** (or "I don't know yet" on a single question): a link button,
  13 px `--app-accent-text`, 12 px under the control. On a set, it marks the set's blank values as
  not known and moves on.
- **"Is this right?"** keeps its layout from PR #20 (the value at 30 px, its source in 13 px), inside
  the body.
- **The lot drawing and the compass** keep their layouts, inside a 760 px card.

### 4.6 The footer

- 10 px × 16 px padding, items 10 px apart.
- **Back** on the left, on every card but the task's first (there it reads "Tasks" and goes to the
  task list): a plain button — transparent, 0.5 px `--app-edge` border, 8 px radius, 36 px tall,
  7 px × 14 px padding, 15 px `--app-label`.
- **Continue** on the right, where the card needs it: the same button, filled `--app-label` with
  `--app-row` text (near-black on light, near-white on dark). It is the card's one filled button.
- Where a tap moves on and nothing needs Continue, the right side reads "A tap moves on" in 13 px
  `--app-secondary-label` the first time in an application, and is empty after that.
- On a phone the footer is the card's bottom band, 12 px above the home indicator; the body scrolls
  between the header and the footer when it is taller than the screen.

### 4.7 Check pages and the list of items

- **"Check <task>"** is a card: header "Check The work" with the bar full; the body is the task's
  answers as rows (the question as asked, 14 px; the answer, 14 px `--app-secondary-label` under
  it; **Change**, 13 px `--app-accent-text`, on the right). A Change opens that card and Continue
  there comes back to the check. The footer: Back, and **Done** (filled) to the task list.
- **Buildings / Additions** is a card: header "Buildings" and "2 added" on the right. One row per
  item: its icon (its type's icon, 18 px), "Building 1 · A home" (14 px), and under it a summary
  line (12 px `--app-secondary-label`): "28 × 40 ft · 2 floors · 2,240 sq ft · front faces
  north", or "3 answers to go" while unfinished. On the right: **Change** (or **Finish** while
  unfinished) and **Delete** (13 px, Delete in `--app-destructive`, behind the confirmation from
  PR #20; not shown on the last building when one is required).
- The list's footer: **+ Add a building**, **Copy Building 1** (when there is a finished building;
  section 6), and on the right **Done with buildings** (filled).
- An item's last card goes to that item's check page, which goes back to the list.

### 4.8 New tokens

| Token | Light | Dark | Use |
|---|---|---|---|
| `--app-edge` | `#AEAEB2` | `#545458` | tile and button edges; the bar's empty segments |
| `--app-done-bg` | `#E3F5E6` | `#12341B` | the Done pill |
| `--app-done-text` | `#1B7A31` | `#6FD089` | the Done pill's text |

All three pairs need checking against WCAG AA (text 4.5:1; edges 3:1 against `--app-row`) before
they're used; adjust the value, not the rule, if one fails.

## 5. Icons

- **Tabler outline icons**, from `@tabler/icons-react` pinned to an exact version, 18 px, stroke 1.75.
  No filled icons, no emoji, no drawn-by-hand paths (the roof drawings stay).
- The icon for each option lives with the option in the form YAML (`icon: home-plus`), so it shows
  on the forms sheet; the loader refuses a name that isn't in the pinned set.
- A starting set (the build may swap an icon for a closer one; it may not add icons where this
  list has none):

| Question | Option → icon |
|---|---|
| What are you planning? (screener) | build → `home-plus` · use → `building-store` · driveway → `road` · divide → `layout-grid` · other → `help-circle` |
| What kind of building work? | new → `building-cottage` · addition → `home-plus` · renovation → `paint` · site → `shovel` |
| What kind of work is this? (form) | new_building → `building-cottage` · addition → `home-plus` · renovation → `paint` · site → `shovel` · nonconforming → `file-alert` |
| Building type, first step | home → `home` · business → `building-store` · smaller → `building-warehouse` · farm → `tractor` · other → `building` |
| What are you adding or changing? | addition → `home-plus` · garage → `car-garage` · porch → `armchair` · deck → `stairs` · patio → `square` · other → `dots` |
| Which way does the front face? | north → `arrow-up` · east → `arrow-right` · south → `arrow-down` · west → `arrow-left` |
| Task list | Your lot → `map-2` · About you → `user` · The work → `hammer` · Buildings → `building-cottage` · Additions → `stairs` · Driveway → `road` · Uses → `building-store` · Photos → `photo` · Check and send → `signature` |
| Yes / No questions | no icons |

## 6. Copy Building 1

"Copy Building 1" makes a new building with Building 1's answers to cards 1, 2, 5, 6 and 7 (type,
renovation, size, roof, outside), and none of its name, homes, setbacks, front or windows, which
differ by building. It opens the new building's check page, so the applicant sees what came across
and changes what differs. (Which answers copy is the chair's call; section 11.)

## 7. Behaviour that stays from PR #20

- A tap answers a single choice and moves on after 200 ms; a card answered before shows Continue
  when it is opened again.
- Autosave, "Saved", Save and close; a typed answer saves before any move.
- "Is this right?", carried answers ("Filled in from your answers at the start"), "I don't know
  yet", Skip for now on optional uploads.
- Review and sign (now "Check and send"), the official printout's labels and order, Change from
  review returning to review.
- Plain words only: no "Why", no Code citations, no verdict words on any applicant screen.

## 8. What goes

- The answer trail (chips) and the dots, on the application and on "Do I need a permit?".
- The step sidebar's ○ ◐ ✓ marks, replaced by the task list's pills.
- The teal filled Continue pill in the wizard (teal stays for links, focus rings and the seal).
- Large filled tiles; the intro sentence above the first question.

## 9. "Do I need a permit?"

The same card, header and footer, with its own short bar ("Your project · 2 of 5"). Its total counts
the questions that apply to what has been chosen so far, and the bar never shows fewer segments than
already answered. The property search and "Is this your property?" sit in the same card. "What
you'll need" is a card with the result as its question line (20 px) and the rows from PR #20.

## 10. Proof

- The comp and the build side by side, desktop and phone, light and dark: the task list, a tap card,
  a set card, a check page and the buildings list. The finish review compares them value by value
  with section 4.
- A building takes 8 cards and an addition 6, counted by a test against the form definitions.
- Every tile question has icons on every option or on none (a form-content test).
- The progress total doesn't change while the applicant moves forward without changing an answer
  (a unit test).
- Copy Building 1 copies exactly the answers section 6 lists (an API test).
- The journeys pass on desktop and phone, dev and LAN; axe passes in light and dark.

## 11. Decisions settled with the approval (the chair, 2026-10-25)

Points 1–3 are settled as recommended; point 4 is how the forms come back for approval; point 5 is
still open.

1. **Back on a phone:** this brief puts Back in the card's footer, on the left, on every card (as in
   the comp), and the top bar's ‹ goes to the task list. *Recommended* — it is also the open
   question from PR #20.
2. **Continue's colour:** near-black (near-white in dark mode), as in the comp, instead of the teal
   pill. *Recommended* — it is what the chair liked in the comp; teal stays for links.
3. **Copy Building 1:** copy type, renovation, size, roof and outside; not name, homes, setbacks,
   front or windows. *Recommended.*
4. **The regrouped cards (section 3)** change the forms' grouping again, so the forms sheet is
   regenerated and comes back to the chair for approval, as in Milestone 4.
5. **"Which way does the front face?"** stays a required question that prints on the form (the
   fifth proposal in OPEN_ITEMS), or not — still open from PR #20.
