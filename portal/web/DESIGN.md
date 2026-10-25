---
name: Town of Newcastle Applicant Portal
description: A permit application as a short list of tasks, each asked in contained cards, in the grammar of Apple's Settings under the Town seal's teal.
colors:
  accent: "#0C727E"
  accent-text: "#0C727E"
  accent-text-dark: "#4CC9D8"
  on-accent: "#FFFFFF"
  seal: "#1098A8"
  selection: "#DCEFF1"
  selection-dark: "#123C42"
  done-bg: "#E3F5E6"
  done-bg-dark: "#12341B"
  done-text: "#1B7A31"
  done-text-dark: "#6FD089"
  destructive: "#D70015"
  destructive-dark: "#FF6961"
  ground: "#F2F2F7"
  ground-dark: "#000000"
  row: "#FFFFFF"
  row-dark: "#1C1C1E"
  ground-elevated-dark: "#1C1C1E"
  row-elevated-dark: "#2C2C2E"
  fill: "#EEEEF0"
  fill-dark: "#3A3A3C"
  separator: "#C6C6C8"
  separator-dark: "#38383A"
  edge: "#8E8E93"
  edge-dark: "#6C6C70"
  label: "#1C1C1E"
  label-dark: "#F2F2F7"
  secondary-label: "#636366"
  secondary-label-dark: "#AEAEB2"
  tertiary-label: "#8A8A8E"
typography:
  large-title:
    fontFamily: "-apple-system, BlinkMacSystemFont, \"SF Pro Text\", system-ui, \"Segoe UI\", Roboto, sans-serif"
    fontSize: "30px"
    fontWeight: 700
    lineHeight: 1.25
  confirm-value:
    fontFamily: "-apple-system, BlinkMacSystemFont, \"SF Pro Text\", system-ui, \"Segoe UI\", Roboto, sans-serif"
    fontSize: "30px"
    fontWeight: 600
    fontFeature: "\"tnum\""
  title:
    fontFamily: "-apple-system, BlinkMacSystemFont, \"SF Pro Text\", system-ui, \"Segoe UI\", Roboto, sans-serif"
    fontSize: "22px"
    fontWeight: 600
    lineHeight: 1.25
  question:
    fontFamily: "-apple-system, BlinkMacSystemFont, \"SF Pro Text\", system-ui, \"Segoe UI\", Roboto, sans-serif"
    fontSize: "20px"
    fontWeight: 500
    lineHeight: 1.3
  headline:
    fontFamily: "-apple-system, BlinkMacSystemFont, \"SF Pro Text\", system-ui, \"Segoe UI\", Roboto, sans-serif"
    fontSize: "17px"
    fontWeight: 600
  body:
    fontFamily: "-apple-system, BlinkMacSystemFont, \"SF Pro Text\", system-ui, \"Segoe UI\", Roboto, sans-serif"
    fontSize: "17px"
    fontWeight: 400
  body-compact:
    fontFamily: "-apple-system, BlinkMacSystemFont, \"SF Pro Text\", system-ui, \"Segoe UI\", Roboto, sans-serif"
    fontSize: "15px"
    fontWeight: 400
  row:
    fontFamily: "-apple-system, BlinkMacSystemFont, \"SF Pro Text\", system-ui, \"Segoe UI\", Roboto, sans-serif"
    fontSize: "14px"
    fontWeight: 400
  footnote:
    fontFamily: "-apple-system, BlinkMacSystemFont, \"SF Pro Text\", system-ui, \"Segoe UI\", Roboto, sans-serif"
    fontSize: "13px"
    fontWeight: 400
  group-header:
    fontFamily: "-apple-system, BlinkMacSystemFont, \"SF Pro Text\", system-ui, \"Segoe UI\", Roboto, sans-serif"
    fontSize: "13px"
    fontWeight: 600
    letterSpacing: "0.025em"
  caption:
    fontFamily: "-apple-system, BlinkMacSystemFont, \"SF Pro Text\", system-ui, \"Segoe UI\", Roboto, sans-serif"
    fontSize: "12px"
    fontWeight: 400
rounded:
  lg: "8px"
  xl: "12px"
  full: "9999px"
spacing:
  xs: "6px"
  sm: "8px"
  tile-gap: "10px"
  md: "12px"
  lg: "16px"
  xl: "24px"
  xxl: "32px"
  touch: "44px"
components:
  card:
    backgroundColor: "{colors.row}"
    rounded: "{rounded.xl}"
    width: "640px"
  card-wide:
    backgroundColor: "{colors.row}"
    rounded: "{rounded.xl}"
    width: "760px"
  card-header:
    textColor: "{colors.secondary-label}"
    typography: "{typography.footnote}"
    padding: "10px 16px"
  card-body:
    padding: "22px 24px 18px"
  card-footer:
    padding: "10px 16px"
  progress-segment:
    backgroundColor: "{colors.edge}"
    height: "3px"
  progress-segment-on:
    backgroundColor: "{colors.label}"
    height: "3px"
  button:
    textColor: "{colors.label}"
    typography: "{typography.body-compact}"
    rounded: "{rounded.lg}"
    padding: "7px 14px"
    height: "36px"
  button-filled:
    backgroundColor: "{colors.label}"
    textColor: "{colors.row}"
    typography: "{typography.body-compact}"
    rounded: "{rounded.lg}"
    padding: "7px 14px"
    height: "36px"
  link-action:
    textColor: "{colors.accent-text}"
    typography: "{typography.footnote}"
    height: "44px"
  tile:
    textColor: "{colors.label}"
    typography: "{typography.row}"
    rounded: "{rounded.lg}"
    padding: "10px 12px"
    height: "48px"
  tile-chosen:
    textColor: "{colors.label}"
    rounded: "{rounded.lg}"
    padding: "9px 11px"
    height: "48px"
  task-row:
    textColor: "{colors.label}"
    typography: "{typography.row}"
    padding: "11px 16px"
    height: "44px"
  task-row-current:
    backgroundColor: "{colors.selection}"
    rounded: "{rounded.lg}"
    padding: "11px 16px"
  pill-done:
    backgroundColor: "{colors.done-bg}"
    textColor: "{colors.done-text}"
    typography: "{typography.caption}"
    rounded: "{rounded.full}"
    padding: "2px 9px"
  pill-progress:
    backgroundColor: "{colors.selection}"
    textColor: "{colors.accent-text}"
    typography: "{typography.caption}"
    rounded: "{rounded.full}"
    padding: "2px 9px"
  pill-not-started:
    backgroundColor: "{colors.fill}"
    textColor: "{colors.secondary-label}"
    typography: "{typography.caption}"
    rounded: "{rounded.full}"
    padding: "2px 9px"
  field:
    backgroundColor: "{colors.fill}"
    textColor: "{colors.label}"
    height: "44px"
  field-in-set:
    backgroundColor: "{colors.fill}"
    textColor: "{colors.label}"
    height: "44px"
    width: "110px"
  inset-group:
    backgroundColor: "{colors.row}"
    rounded: "{rounded.xl}"
  inset-row:
    padding: "10px 16px"
    height: "44px"
  segment:
    rounded: "{rounded.lg}"
    padding: "0 16px"
    height: "44px"
  segment-selected:
    backgroundColor: "{colors.selection}"
    rounded: "{rounded.lg}"
  chip:
    rounded: "{rounded.full}"
    typography: "{typography.body-compact}"
    padding: "0 16px"
    height: "44px"
  chip-selected:
    backgroundColor: "{colors.selection}"
    rounded: "{rounded.full}"
---

# Design System: Town of Newcastle Applicant Portal

## Overview

**Creative North Star: "The Settings Pane, a Task at a Time"**

The portal is Apple's System Settings and iOS Settings applied to a Town permit. The application is a short list of tasks (Your lot, About you, The work, Buildings, ...; Check and send last), each row carrying a status pill. Opening a task opens a card: a contained white panel on the grouped ground with three bands, a header that names the task and shows a thin segmented progress bar, a body that asks one question (or one small set of values), and a footer with Back on the left and the card's one filled button on the right. Only the body moves between questions; the card's edge, header and footer stay still. On a desktop the task list stays in a 250 px sidebar beside the card; on a phone the task list is the home page and a task's card fills the screen under a 44 px bar.

The world is quiet and native. Type is the device's own system face; colour is Apple's system greys and grouped grounds; the only hue is the Town seal's teal, now used for links, the in-progress pill, focus rings and the seal itself, not for buttons. The card's primary action is near-black (near-white in dark mode). Done is a soft green pill. Light and dark follow the device (`main.tsx` sets `data-theme`; a `prefers-color-scheme` media query covers first paint). Native grammar is used without imitating native chrome: no fake window controls, traffic lights or status bars. Icons are Tabler outline icons, 18 px at stroke 1.75, never filled and never emoji.

The answer trail of chips, the page dots, the full-width question screens, the fixed footer action bar, the phone navigation bar with a large title, the step sidebar with drawn ○ ◐ ✓ glyphs, the teal Continue pill and the desktop toolbar are gone.

**Key Characteristics:**
- The application is a task list; each task is a run of cards; Check and send opens when every task is done.
- One contained card at a time: 640 px (760 px for the lot drawing and compass), 12 px corners, a 0.5 px hairline, no shadow.
- Progress is a 3 px segmented bar in the card header with "3 of 6"; status is a pill on the task row.
- Tiles are outlined, not filled; chosen is a 1.5 px label-coloured edge.
- One filled button per card, in the label colour; teal is for links, the in-progress pill and focus.
- Depth by tone and hairline, not shadow.

## Colors

Apple's system neutrals with one civic accent, the teal of the Town seal, and one green for Done. The `--app-*` custom properties in `src/index.css` are the source; `src/theme/tokens.ts` holds the same values and a test keeps them in step. Dark values are the `-dark` keys; tokens without one are identical in both modes.

### Primary
- **Harbour Teal** (accent): the edge of a selected segment, chip, checkbox or radio outside the cards, and HeroUI's primary on the outer pages. It no longer fills any button on a card.
- **Harbour Teal Text** (accent-text / accent-text-dark): teal as text: links, Change and Finish, "I don't know yet", ‹ Tasks and Save and close on a phone, the "2 of 4" pill's words, every focus ring. In dark mode it lifts to bright aqua so it stays legible on black.
- **On Accent** (on-accent): text on a teal fill (HeroUI primary on outer pages).

### Secondary
- **Seal Teal** (seal): the seal's own teal (about 3.4:1 on white), kept for marks that carry no text: the lot outline in the lot diagram.
- **Selection Wash** (selection / selection-dark): the open task's row in the desktop sidebar (60% on hover), the "2 of 4" pill, a selected segment or chip, and the lot fill in the lot diagram.
- **Done Green** (done-bg / done-text, with dark pairs): the Done pill only.

### Tertiary
- **System Red** (destructive / destructive-dark): Delete, Remove and error messages, and "Still to answer" on Check and send.

### Neutral
- **Grouped Ground** (ground / ground-dark): the window, the desktop sidebar and main area, the phone bar (95% with blur). Pure black in dark mode.
- **Row** (row / row-dark): the card, the task-list card, inset groups; also the text colour of the filled button.
- **Raised Ground and Row** (ground-elevated-dark, row-elevated-dark): inside a sheet the ground and row variables are reassigned to these, so in dark mode a sheet sits one step lighter than the window. In light mode they equal ground and row.
- **Field Fill** (fill / fill-dark): text, number and select fields; the Not started pill.
- **Separator** (separator / separator-dark): the card's 0.5 px edge, the hairlines under the header and above the footer, between task rows and check rows, above repeated floor values, and the sidebar's right edge.
- **Edge** (edge / edge-dark): the 0.5 px border of a tile and of a card button, and the unlit segments of the progress bar. A ruling set it at #8E8E93 light / #6C6C70 dark to reach 3:1 against the row; the brief's #AEAEB2 / #545458 did not.
- **Label**: primary text, a chosen tile's 1.5 px edge, the lit progress segments, the filled button's ground.
- **Secondary Label**: the card header, help lines, hints, pill text for Not started, answers on a check page, unchosen tile icons, a tile's hover edge, Check and send while closed.
- **Tertiary Label**: the 1.5 px edge of an empty checkbox or radio.

### Named Rules
**The Teal Is for Words Rule.** On a card, teal appears only as text (links, Change, "I don't know yet"), the in-progress pill and the focus ring. The card's one filled button is the label colour, never teal.

**The Two Teals Rule.** Teal that carries text is accent-text (lifted in dark); the seal's own teal marks identity and never carries text.

**The Edge Not Block Rule.** Choice is shown by an edge, never a solid fill: a chosen tile thickens to a 1.5 px label edge with no fill; the older segments and chips add the selection wash under an accent edge.

## Typography

**Display Font:** none; the system stack throughout.
**Body Font:** -apple-system, BlinkMacSystemFont, "SF Pro Text", system-ui, "Segoe UI", Roboto, sans-serif, antialiased.

**Character:** The device's own interface face at Apple's text sizes, so the portal reads as part of the phone or Mac rather than a website.

### Hierarchy
- **Large Title** (700, 30px, 1.25): the home heading, My applications, Sign in.
- **Confirm Value** (600, 30px, tabular): the value from the Town's map on an "Is this right?" card, its source in footnote below.
- **Title** (600, 22px, 1.25): headings on the outer pages ("Where is the property?", "Is this your property?", the use picker, "Check your email").
- **Question** (500, 20px, 1.3, balanced, at most 30ch): the question in every card body, on "Do I need a permit?", and each result's line in "What you'll need".
- **Headline** (600, 17px): the sheet title.
- **Body** (400, 17px): the phone bar's ‹ Tasks, ‹ Home and Save and close; results prose; the start screens' number inputs.
- **Body Compact** (400, 15px): card buttons, fields, inset rows, the task-list card's form name (at weight 500), the stepper's number, error lines.
- **Row** (400, 14px): tile labels, task names, item rows, a set's short names, a check page's question and answer.
- **Footnote** (400, 13px): the card header, the help line under a question, the small question above a dependent value (the roof's slope), Change / Finish / Delete, "I don't know yet", "A tap moves on", the save status, captions.
- **Group Header** (600, 13px, uppercase, wide tracking, secondary label): the heading above an inset group on the outer pages. Inside a card (`plain`), the heading is 13px in its own case.
- **Caption** (400, 12px): status pills, task hints, an item's summary line, the form's term under a question on Check and send.

### Named Rules
**The System Face Rule.** Text is set in the device's system face at the ramp's sizes (30 / 22 / 20 / 17 / 15 / 14 / 13 / 12); no other family is loaded and no other size is used.

**The One Question Rule.** A card body carries one Question line; help is one footnote line 4 px under it and 16 px above the control (its space held when empty so the control does not jump).

## Layout

At 1024 px and wider the app is a two-column window on the grouped ground: a 250 px sidebar with a 0.5 px separator on its right, padded 16 px by 10 px, holding the Town seal (40 px) beside "Town of Newcastle" and the form's name, the task rows (8 px corners, 2 px apart), and at its foot the save status and Save and close (a ruling: the brief had no place for it). The main area is padded 32 px; the card sits centred in it at 640 px, or 760 px for the lot drawing and compass. With no task open, the task list itself is the card in the main area.

Below 1024 px the task list is the page, as a card in 12 px gutters under a 44 px bar holding Save and close. In a task, the 44 px bar (grouped ground at 95% with blur, a 0.5 px separator beneath) holds ‹ Tasks on the left and the save status on the right; the card fills the screen in 12 px gutters, ending 12 px above the home indicator (safe-area aware), its footer its own bottom band. A long body scrolls between the header and footer.

Inside a card: the body is padded 22 px top, 24 px sides, 18 px bottom, centred. Tiles sit in a grid at most 500 px wide, 8 px apart, two columns once the card is 400 px (25rem, container query) wide, one below. A set of values is a two-column grid at most 380 px (480 px when it holds text), 14 px across and 10 px down: short name left, field right; repeated values (one per floor) sit under a 0.5 px separator 10 px below. A choice that leads a set comes first as tiles; what depends on it (the roof's slope) appears once it is answered, under its own small footnote question (a ruling). Header and footer are padded 10 px by 16 px, items 10 px apart.

The compass and lot-diagram layouts are container-queried: at 42 rem (`@2xl`) and wider the four walls or setbacks arrange around a central drawing; narrower, the drawing comes first and the sides stack.

Spacing runs on a 4 px grid with the iOS odd steps the comp uses: 6 px inside groups, 8 px between tiles, 10 px in headers and footers, 12 px gutters, 16 px row insets, 24 px body sides, 32 px around the desktop card.

## Elevation & Depth

Flat by tone. Surfaces separate by ground-versus-row colour and 0.5 px hairlines, not shadows: the card is a row-coloured panel with a hairline edge on the grouped ground. A sheet raises itself by reassigning its ground and row variables to the elevated values, which in dark mode makes it lighter than the window, as on iOS. The phone bar, which floats over scrolling content, is 95% opaque with a backdrop blur. The one cast shadow is the slider's knob (`0 1px 4px rgba(0,0,0,0.3)`), a white circle as on iOS. The card button's focus ring is drawn with box-shadow (2 px row gap, then 2 px accent-text); it is a ring, not elevation.

### Named Rules
**The Tone Not Shadow Rule.** Containers never take a drop shadow; depth comes from ground, row, elevated row and the hairline.

## Shapes

Softly rounded rectangles. Cards, the task-list card and outer inset groups are 12 px; tiles, card buttons, sidebar task rows, segments and the compass's house square are 8 px; progress segments are 2 px; pills and chips are fully round. Card edges and the hairlines within cards are 0.5 px; outer inset groups keep 1 px dividers. A tile's edge is 0.5 px edge-grey, 1.5 px label when chosen (its padding drops 1 px so nothing moves). Empty checkboxes and radios carry a 1.5 px tertiary-label ring. The upload target is a 2 px dashed outline.

## Components

### Card (signature)
The unit of the application. Row colour, 0.5 px separator edge, 12 px corners, content clipped, no shadow; 640 px or 760 px wide. With a submit handler it is a form, so Return in a field means Continue.
- **Header:** footnote in secondary label: the task's name (or "Building 1 · A home"), the progress bar filling the space, then "3 of 6" in tabular numerals. Without a count, a title and a note on the right ("2 added").
- **Body:** centred; the Question, the help line, an optional carried-answer footnote ("Filled in from your answers at the start. Change it if you need to."), the control, and where allowed "I don't know yet" (or "I don't know some of these yet" on a set) as a 13px accent-text link 12 px below, 44 px tall. Focus moves to the question on arrival.
- **Footer:** Back (a plain button; "Tasks" on a task's first card) left; Continue (filled) right where the card needs it. Where a tap moves on, the right side reads "A tap moves on" in footnote on the first such card of a visit, then nothing.
- **Motion:** only the body moves: forward slides in from 24% right, Back from 24% left, 300 ms on `cubic-bezier(0.32, 0.72, 0, 1)`; a 120 ms fade under reduced motion.

### Progress bar
One segment per card in the task, 3 px tall, 3 px apart, 2 px corners; answered and current in label, the rest in edge. `role="img"`, "Question 3 of 6". On a check page the bar is full.

### Task list (signature)
A card whose header carries the form's name (15px, 500) and, right, "Map 4, Lot 36 ·" and the save status. Each task is a whole-row link, 44 px minimum, padded 11 px by 16 px, 0.5 px separators between: its 18 px outline icon in label, its name in Row, an optional Caption hint beneath, and a status pill at the right. Check and send has no pill; until it opens its icon, name and hint ("Opens when the tasks above are done") are secondary label. In the desktop sidebar the rows drop the separators, take 8 px corners, and the open task sits on the selection wash; there the "2 of 4" pill takes the row colour so it stays visible.

### Status pill
Caption, 2 px by 9 px, fully round. Done: done-bg with done-text. "2 of 4": selection with accent-text (read aloud as "2 of 4 answered"). Not started: fill with secondary label.

### Tiles
- **Pick one** (radio tiles): one tab stop, arrow keys between tiles. A tap answers and, after 200 ms to see the choice, moves on, even on the tile already chosen; inside a set a tap only answers.
- **Pick several** (checkbox tiles): toggle; Continue moves on. No check mark on a chosen multi tile (a ruling); the 1.5 px edge alone shows it.
- **Style:** transparent, 0.5 px edge, 8 px corners, 48 px minimum, 10 px by 12 px padding, Row label left-aligned in label; an 18 px outline icon 10 px before it in secondary label. Chosen: 1.5 px label edge, no fill. Hover (pointer devices only): the edge turns secondary label. Focus: a 2 px accent-text ring offset 2 px. A question's tiles all carry icons or none do; roof styles carry their drawn silhouette instead.

### Buttons
- **Card button** (plain): transparent, 0.5 px edge border, 8 px corners, 36 px minimum, 7 px by 14 px padding, 15px label; an optional 16 px icon 6 px before the words (+ Add a building, Copy Building 1). Back, Save and close, and the stepper's − and +.
- **Filled:** the same shape filled in label with row-coloured text, near-black in light, near-white in dark. One per card: Continue, Done, Done with buildings; also "Start this application" on results and "Email me a sign-in link".
- **Link action:** accent-text words at 13px with a 44 px hit area: Change, Finish, "I don't know yet"; Delete in destructive.
- **Focus:** a 2 px accent-text ring on every control (on card buttons, outside a 2 px row-coloured gap).
- Outer pages and sheets still use HeroUI's buttons (secondary, ghost, and teal primary on Where, Verify and the use search).

### Set of values and stepper
Short names (Row, label) beside 110 px right-aligned number fields with the unit after in secondary label; a count (floors above ground) is − and + card buttons, 36 px square, with the number between in 15px tabular. Repeated values sit under a hairline.

### Check page and items list
- **Check <task>:** a card with a full bar; one row per answer, padded 11 px by 16 px under hairlines: the question in Row label, the answer in Row secondary label (the tile's own words; "Not answered"), Change at the right. Footer: Back, and Done (filled).
- **Buildings / Additions:** a card with "2 added" in the header; one row per item: its type's 18 px icon, "Building 1 · A home" in Row, a Caption summary ("28 × 40 ft · 2 floors · ..." or "3 answers to go"); Change (or Finish) and Delete at the right, Delete behind a confirmation. Footer: + Add a building, Copy Building 1, and Done with buildings (filled).

### Check and send
A card whose body stacks `plain` inset groups: no rounded inset, a 0.5 px hairline above, below and between rows, the heading 13px in its own case. Each answer is the question in 14px with the form's term beneath in Caption, the answer in 14px secondary label, Change at the right; "Still to answer" in destructive when required. Add more detail sits at each group's foot.

### "Is this right?"
Inside the card body: the map's value in Confirm Value, its source in footnote, then tiles "Yes, that's right" and "No, I'll correct it" (and "Use the map's ..." once corrected).

### Inset Group
Kept, rounded, for the outer pages: home, results, my applications and the property pages. 12 px corners, contents clipped; row on the grouped ground with 1 px separators; group header above and footnote below, inset 16 px; rows 44 px minimum.

### Inputs and other controls
Fields on the field fill, no border, 44 px tall (a ruling: the brief's 36 px is under the touch minimum), 15px text, numbers right-aligned. Segmented choices and choice chips outside the cards keep the wash-plus-accent-edge selection. Sliders carry the iOS knob. Upload is a dashed accent-text target.

### Sheet
Only "More detail" (Check and send) and "Add a use". A header row in the row colour: Cancel left, semibold 17px title centred, Done right in accent-text. Esc cancels; the backdrop does not dismiss.

### Lot diagram and compass
Plain line drawings that orient the questions, inside a 760 px card: the lot as a selection-wash polygon outlined 2 px in seal teal with the building as a row-coloured square outlined in label; the compass as a label-coloured north arrow and a 2 px label-outlined square for the house. Walls are named from the way the front faces ("Front (north, faces Sheepscot Road)"), asked once the front's direction is chosen.

## Do's and Don'ts

### Do:
- **Do** put every question in a card: header with bar and count, body with one question, footer with Back and at most one filled button.
- **Do** let a single choice answer at a tap and move on after 200 ms; give Continue only to what a tap cannot finish.
- **Do** show progress with the card header's segmented bar and a task's status with its pill.
- **Do** draw icons from the pinned Tabler outline set at 18 px, stroke 1.75; give a question's tiles icons on every option or none.
- **Do** keep fields and every link action at 44 px; tiles at 48 px.
- **Do** use the `--app-*` variables (or HeroUI's variables mapped onto them), never literal hex, so light, dark and sheet elevation all follow.
- **Do** keep the task list in the sidebar at 1024 px and up, and one tap away (‹ Tasks) below.

### Don't:
- **Don't** bring back the answer trail, page dots, a footer action bar or a large-title navigation bar inside the application.
- **Don't** fill a card's button with teal; the filled button is the label colour.
- **Don't** fill a chosen tile; show it with the 1.5 px label edge.
- **Don't** imitate native window chrome: no traffic lights, fake status bars or title-bar controls.
- **Don't** drop-shadow a container; raise a sheet by tone.
- **Don't** set text in the seal teal; text teal is accent-text.
- **Don't** use filled icons, emoji or hand-drawn paths for icons (roof silhouettes and the two diagrams excepted).
- **Don't** load a web font or display face, or set a size off the ramp.
