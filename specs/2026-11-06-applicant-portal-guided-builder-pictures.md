# Guided builder: the pictures (plan 5 of 6) — design

**Status:** approved by the chair (Ben Frey) on 2026-11-06, in conversation. The parts marked
*builder's call* were the builder's, and the chair approved them with the rest.

**Builds on:** `specs/2026-10-30-applicant-portal-guided-builder.md` (the experience design), §4.2
"Tell us what you'd like to do", §6 (the explanation library), decision 15 (the pictures are drawn
in-house as vector graphics in one style; the chair approves a sample sheet before the full set).
Plans 1–4 are built (`plans/2026-10-3*` and `2026-11-0*`); plan 6 is the applicant packet view.

## 1. Why

Most residents who come to the Town Office are doing one of a handful of things. The pictures let a
person who doesn't want to write, or can't find the words, point at what they have in mind and
start the conversation from there. They also show the resident that the Town is talking about
*their* kind of place: a Newcastle lot, not a stock suburb.

The explanation pictures do the same for the hardest ideas in the Code. "How stories are counted"
(the 3-foot knee wall, the 5-foot exposed basement) is far easier to see than to read.

## 2. Goals

1. **An opening scene**: one illustration of a Newcastle lot, seen from above at an angle, whose
   parts are places to tap. Tapping one starts that project's conversation.
2. **Explanation pictures** for the library entries that need one, drawn in the same view.
3. **A sample sheet the chair approves** before the full set is drawn (decision 15).

## 3. Non-goals

- **The conversations for the new projects.** Decks, additions, solar panels, outbuildings and the
  rest get their walk-throughs in later plans, once this foundation is settled (the chair). Until
  then their spots say "coming soon".
- **Reading what a person types** (decision 14). The scene works without it.
- **The packet's drawing** (plan 6).

## 4. Anti-goals: what would make this a failure even if it works

- A picture that tells a resident something the Code doesn't say: a setback drawn at a distance
  that looks like a rule, a house that looks "approved". Pictures illustrate; the words and the
  numbers decide (decision 12's spirit).
- A scene that only works with a mouse. Many residents use a phone; some use a screen reader.
- A generic suburban look. It should read as Newcastle at a glance.
- Pictures that drift apart in style as more are added.

## 5. The look (the chair's choices)

- **The view: the lot from above, at an angle** (the chair chose this over a line drawing and flat
  colour on 2026-11-06). The whole lot in one tilted view, like the UK Planning Portal's
  interactive house, made Newcastle's own.
- **The subject:** a white cape with a centre chimney, its connected ell and a red barn, a stone
  wall along the road, a maple. Grey roofs, green lot, the road along the front.
- **Explanation pictures use the same view**: the same house at the same angle, cut away to show
  what the words explain (the chair chose this over a flat cross-section).
- *Builder's call:* one small palette (white clapboard, barn red, roof grey, lot green, stone grey,
  maple orange, door blue) set as named colours in one place, so every picture shares it and the
  theme can adjust it. Shapes are flat fills with light shading on the side faces; no outlines,
  gradients or texture.

## 6. The opening scene

### 6.0 Where it is

- **Inside a project** (the chair, 2026-11-06). The scene is the guide's first screen for an
  existing project. It replaces today's list of openings at the pick step.
- The project page's link to the guide shows **for every project**, not only those with a building
  or a use.
- Creating a project stays as it is.
- *Builder's call:* the scene shows only before a conversation has started. Once one has started,
  the guide opens on the conversation, as it does today. A project holds one conversation, and
  "No" on "So you mean…" already goes back to the start. Offering the scene again mid-conversation
  waits until there are more conversations to start.

### 6.1 What can be tapped

The chair named the most common projects: **decks, additions, solar panels, and garages, barns and
outbuildings.** The scene shows those clearly, plus the two the guide already covers and the rest
the experience design names. *Builder's call* on the full list and where each sits:

| Spot | Where in the scene | Today |
|---|---|---|
| A new house | an empty corner of the lot, a dashed outline of a house | guided (`new_house`) |
| A change of use | the barn, with an open door and a small sign | guided (`change_of_use`) |
| An addition | an ell-shaped outline off the side of the cape | coming soon |
| A deck | a deck at the back of the cape | coming soon |
| Solar panels | panels on the barn's south roof | coming soon |
| A garage, barn or shed | a small shed at the back of the lot | coming soon |
| A driveway | the drive from the road | coming soon |
| A fence or wall | the stone wall | coming soon |
| A sign | a sign by the road | coming soon |
| A business at home | the ell's door, with a small shingle | coming soon |

**Every spot shows, whatever parts the project has** (the chair).

### 6.2 What a tap does (the chair)

1. **The guide covers it, and the project has the matching part:** the conversation starts, as a
   tap on today's list does.
2. **The guide covers it, but the project lacks the part:** a question pops up asking whether to
   add it to the project ("Add a new house to this project?"). Yes adds the part and starts the
   conversation; No closes the question and leaves the project as it was.
3. **The guide doesn't cover it yet:** a "coming soon" notice pops up, naming the project, and the
   person stays on the scene.

*Builder's call on "the matching part":*
- A `building` part means a new building (`parts.yaml`), so a project with one starts "A new house"
  straight away.
- With two buildings, the conversation attaches to the first, as the guide's bridge does today.
- A spot the guide doesn't cover is "coming soon" even when the project already has its part (an
  addition or a driveway, say). Those parts keep their forms.

### 6.3 Phones, keyboards and screen readers (*builder's call*)

- On a phone the scene fills the width; each spot has a visible marker and a tap target at least
  48 px across (spec §10.4), larger than the drawn object where the object is small.
- **The same projects as a list** under the scene, one button each, in the same order. This is
  the way in for a screen reader or keyboard, and a fallback when the scene is hard to see. The
  scene itself is one image with a text description; its spots are not separate tab stops, so a
  keyboard user meets each project once, in the list.
- Each spot shows its name on hover and focus on a computer; on a phone the name sits by its marker.

### 6.4 The text box

Per §4.2 the text box sits beside the pictures. Until decision 14 is made, what a person writes is
kept with the project for staff, and nothing interprets it.

*Builder's call:*
- The box comes in this plan, beside the scene.
- The guide's notes need a started conversation, so what is typed is held on the page and saved as
  the conversation's first note the moment it starts. Staff then read it with the other guide notes.
- After a "coming soon" tap or a "No" to adding a part, the text stays in the box.
- The question the box asks is draft wording for the chair.

## 7. The explanation pictures

- **Which entries get one (*builder's call*):** "how stories are counted" (full stories, a floor in
  the roof and its 3-foot test, the basement's 5-foot test) and "how far from the lot lines" (the
  front, side and rear setbacks measured to the nearest part of the house). The two entries about
  uses by district stay words only. Later entries say whether they have a picture.
- **The pictures carry no numbers of their own.** The 3-foot and 5-foot tests are labelled as the
  Code states them; a setback is shown as "measured from here to here", never at a distance that
  could read as a limit.
- Each picture has a text description for screen readers. Its labels and description are approved
  wording, like every word an applicant reads (spec §11), and live with the entry.
- They appear in the existing "Why" card, which already has a place for a picture.
- *Builder's call:* "how stories are counted" is **one** cut-away carrying all three tests, so the
  sample sheet shows whether it reads at phone size. If it doesn't, the chair can ask for three
  views shown in turn. The rough `<Attic />` sketch in `GuidePreview` is replaced.

## 8. The sample sheet and its approval (decision 15; the chair's choice of review)

Before the full set:

1. **A working preview on the LAN copy**: the whole scene with every spot, the tap behaviour (the
   conversation, the "add to this project?" question, "coming soon"), the list beneath it, and the
   "how stories are counted" explanation with its picture. The chair opens it on a phone and a
   computer.
2. **A sample-sheet memo** in `memos/`, rendered as a PDF: the scene, close-ups of three spots, the
   stories explanation, each with its label and text description, and the decisions for the chair
   (palette, the buildings, labels, the spots and their places).

The chair approves it in an interview, as he did the wording; the answers go into the memo. Only
then is the rest drawn: the setbacks explanation and any spot the chair changes.

## 9. Constraints

- **Drawn in-house as vector graphics** (decision 15), in code, so every part can be a button and
  stays sharp at any size. No stock art, no photographs, nothing downloaded.
- **Every word is approved** before the public sees it: spot names, pop-up wording, the "coming
  soon" notice, the text box's question, picture labels and descriptions. New words start as drafts
  and go to the chair in a memo, as before.
- *Builder's call:* **every spot is an opening in the API's content** (`openings.yaml`), with its
  name, its place in the scene, its part, and whether the guide covers it yet. The scene and the
  list under it both come from that one list, so they can't disagree. Approval is gated the same
  way as today:
  - On the LAN copy, draft words show under `allow_draft_rules` with the draft chip.
  - Production refuses the scene until its words are approved.
  - `change_of_use`'s picture moves from the shopfront to the barn, as §6.1 says.
- The new words never use the banned list (approved, denied, granted, rejected, permit issued,
  compliant, violates).
- Works in the existing MUI shell and theme; the colours come from the theme layer so a later
  theme can change them.

## 10. Left to the builder

- How the scene is built in code (one SVG with named groups, or one component per spot), as long
  as the palette is shared and each spot can be tested on its own.
- The exact geometry and composition, within §5 and the sample sheet the chair approves.
- How the "coming soon" and "add to this project?" pop-ups are built (dialog or sheet), within the
  MUI shell's patterns.
- How the opening list and the scene share their data, so they can't disagree.
