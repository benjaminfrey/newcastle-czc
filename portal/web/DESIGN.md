---
name: Town of Newcastle Applicant Portal
description: A permit project as a dashboard of parts, each part asked in contained cards, in the grammar of Apple's Settings under the Town seal's teal.
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
  warn-bg: "#FFF1D6"
  warn-bg-dark: "#3D2A08"
  warn-text: "#8A4B00"
  warn-text-dark: "#FFC266"
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
  tab-label:
    fontFamily: "-apple-system, BlinkMacSystemFont, \"SF Pro Text\", system-ui, \"Segoe UI\", Roboto, sans-serif"
    fontSize: "11px"
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
  button-disabled:
    textColor: "{colors.secondary-label}"
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
  sidebar:
    backgroundColor: "{colors.ground}"
    padding: "16px 10px"
    width: "250px"
  sidebar-item:
    textColor: "{colors.label}"
    typography: "{typography.body-compact}"
    rounded: "{rounded.lg}"
    padding: "0 12px"
    height: "44px"
  sidebar-item-current:
    backgroundColor: "{colors.selection}"
    textColor: "{colors.label}"
    rounded: "{rounded.lg}"
    padding: "0 12px"
    height: "44px"
  tab-bar-item:
    textColor: "{colors.secondary-label}"
    typography: "{typography.tab-label}"
    height: "48px"
  tab-bar-item-current:
    textColor: "{colors.accent-text}"
    typography: "{typography.tab-label}"
    height: "48px"
  box:
    backgroundColor: "{colors.row}"
    rounded: "{rounded.xl}"
  box-heading:
    textColor: "{colors.secondary-label}"
    typography: "{typography.footnote}"
    padding: "0 16px"
  project-row:
    textColor: "{colors.label}"
    typography: "{typography.body-compact}"
    padding: "11px 16px"
    height: "56px"
  list-row:
    textColor: "{colors.label}"
    typography: "{typography.row}"
    padding: "11px 16px"
    height: "48px"
  add-tile:
    backgroundColor: "{colors.row}"
    textColor: "{colors.label}"
    typography: "{typography.row}"
    rounded: "{rounded.lg}"
    padding: "10px 12px"
    height: "48px"
  side-column:
    width: "280px"
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
  pill-warn:
    backgroundColor: "{colors.warn-bg}"
    textColor: "{colors.warn-text}"
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

The portal is Apple's System Settings and iOS Settings applied to a Town permit. An application is a **project**: a lot and the parts of the work on it (a new building, an addition, a driveway, ...). The project's home is a dashboard: its title and a status pill, the parcel, a row per part with its status pill, tiles for the parts still to add, and beside them what the project will need, who is applying, and Check and send. Opening a part opens a card: a contained white panel on the grouped ground with three bands, a header that names the part and shows a thin segmented progress bar, a body that asks one question (or one small set of values), and a footer with Back on the left and the card's one filled button on the right. Only the body moves between questions; the card's edge, header and footer stay still. The dashboard is the recap: there is no long review page.

The window holds four places, Home, Project, Messages and You: a 250 px sidebar under the Town seal on a desktop, a bottom tab bar on a phone. The world is quiet and native. Type is the device's own system face; colour is Apple's system greys and grouped grounds; the only hue is the Town seal's teal, used for links, the current tab, the in-progress pill, focus rings and the seal itself, not for buttons. The card's primary action is near-black (near-white in dark mode). Done is a soft green pill; things still left are a soft amber pill. Light and dark follow the device (`main.tsx` sets `data-theme`; a `prefers-color-scheme` media query covers first paint). Native grammar is used without imitating native chrome: no fake window controls, traffic lights or status bars. Icons are Tabler outline icons, 18 px at stroke 1.75, never filled and never emoji.

The answer trail of chips, the page dots, the full-width question screens, the fixed footer action bar, the large-title navigation bar, the step sidebar with drawn glyphs, the teal Continue pill, the desktop toolbar, the task list and Save and close are gone.

**Key Characteristics:**
- A project is a dashboard of parts; each part is a run of cards; Check and send is one tap from the dashboard.
- One contained card at a time: 640 px (760 px for the lot drawing and compass), 12 px corners, a 0.5 px hairline, no shadow.
- Progress is a 3 px segmented bar in the card header with "3 of 6"; status is a pill on the part's row.
- Lists are boxes: a 13px heading in its own case above a 12 px-cornered row-coloured box, rows under hairlines.
- Tiles are outlined, not filled; chosen is a 1.5 px label-coloured edge.
- One filled button per card or page, in the label colour; teal is for words, the current tab, the in-progress pill and focus.
- Depth by tone and hairline, not shadow.

## Colors

Apple's system neutrals with one civic accent, the teal of the Town seal, one green for Done and one amber for things left. The `--app-*` custom properties in `src/index.css` are the source; `src/theme/tokens.ts` holds the same values and a test keeps them in step. Dark values are the `-dark` keys; tokens without one are identical in both modes.

### Primary
- **Harbour Teal** (accent): the edge of a selected segment, chip, checkbox or radio outside the cards, and HeroUI's primary on the outer pages and the Send confirmation. It fills no button on a card.
- **Harbour Teal Text** (accent-text / accent-text-dark): teal as text: links, Change and Finish, "I don't know yet", ‹ Project on a phone, the current tab in the phone's tab bar, the rename pencil and the + on an add tile, the "2 of 4" pill's words, every focus ring. In dark mode it lifts to bright aqua so it stays legible on black.
- **On Accent** (on-accent): text on a teal fill (HeroUI primary).

### Secondary
- **Seal Teal** (seal): the seal's own teal (about 3.4:1 on white), kept for marks that carry no text: the lot outline in the lot diagram.
- **Selection Wash** (selection / selection-dark): the current item in the desktop sidebar, the in-progress and project-status pills ("2 of 4", Sent, With the Town), a selected segment or chip, and the lot fill in the lot diagram.
- **Done Green** (done-bg / done-text, with dark pairs): the Done, Ready to send and Decided pills only.
- **Warning Amber** (warn-bg / warn-text, with dark pairs): the "2 things left" pill only, on the dashboard's header.

### Tertiary
- **System Red** (destructive / destructive-dark): Delete, Remove and error messages, and "Still to answer".

### Neutral
- **Grouped Ground** (ground / ground-dark): the window, the desktop sidebar and main area, the phone's bar and tab bar (95% with blur). Pure black in dark mode.
- **Row** (row / row-dark): the card, every box, inset groups, the sign-in card and the add tiles; also the text colour of the filled button.
- **Raised Ground and Row** (ground-elevated-dark, row-elevated-dark): inside a sheet the ground and row variables are reassigned to these, so in dark mode a sheet sits one step lighter than the window. In light mode they equal ground and row.
- **Field Fill** (fill / fill-dark): text, number and select fields; the Not started and Draft pills.
- **Separator** (separator / separator-dark): the card's and every box's 0.5 px edge, the hairlines under the header and above the footer, between rows, above repeated floor values, the sidebar's right edge, the phone bar's foot and the tab bar's top.
- **Edge** (edge / edge-dark): the 0.5 px border of a tile, an add tile and a card button, and the unlit segments of the progress bar. A ruling set it at #8E8E93 light / #6C6C70 dark to reach 3:1 against the row; the brief's #AEAEB2 / #545458 did not.
- **Label**: primary text, a chosen tile's 1.5 px edge, the lit progress segments, the filled button's ground.
- **Secondary Label**: the card header, box headings and footnotes, help lines, row summaries and lot lines, fees, pill text for Not started, unchosen tile and row icons, a tile's hover edge, the phone's other tabs, a disabled button's label.
- **Tertiary Label**: a row's trailing chevron; the 1.5 px edge of an empty checkbox or radio.

### Named Rules
**The Teal Is for Words Rule.** Teal appears only as text and line icons (links, Change, ‹ Project, the current tab), the in-progress pill and the focus ring. The one filled button is the label colour, never teal.

**The Two Teals Rule.** Teal that carries text is accent-text (lifted in dark); the seal's own teal marks identity and never carries text.

**The Edge Not Block Rule.** Choice is shown by an edge, never a solid fill: a chosen tile thickens to a 1.5 px label edge with no fill; the older segments and chips add the selection wash under an accent edge.

**The One Tone per Meaning Rule.** Each pill tone says one thing: green is finished (Done, Ready to send, Decided), wash is under way (2 of 4, Sent, With the Town), fill is not begun (Not started, Draft), amber is things left. No other surface takes the green or the amber.

## Typography

**Display Font:** none; the system stack throughout.
**Body Font:** -apple-system, BlinkMacSystemFont, "SF Pro Text", system-ui, "Segoe UI", Roboto, sans-serif, antialiased.

**Character:** The device's own interface face at Apple's text sizes, so the portal reads as part of the phone or Mac rather than a website.

### Hierarchy
- **Large Title** (700, 30px, 1.25): the project's title on its dashboard; the You and Messages headings.
- **Confirm Value** (600, 30px, tabular): the value from the Town's map on an "Is this right?" card, its source in footnote below.
- **Title** (600, 22px, 1.25): "Town of Newcastle — Permits" under the seal on Home; headings on the outer property pages ("Where is the property?", "Is this your property?").
- **Question** (500, 20px, 1.3, balanced, at most 30ch): the question in every card body (including the three start cards), "Check your email", and each result's line in "What you'll need" on the outer pages.
- **Headline** (600, 17px): the sheet title.
- **Body** (400, 17px): ‹ Project on the phone's bar; the project-name field while renaming; results prose.
- **Body Compact** (400, 15px): card buttons, fields, sidebar items, row names on the dashboard and Home (500 for a project's title on Home), the parcel's Map and Lot (600), a permit's name in What you'll need (600), the stepper's number, error lines, Messages prose.
- **Row** (400, 14px): tile and add-tile labels, list rows (You, Check and send), a review in What you'll need, item rows, a set's short names, a check page's question and answer.
- **Footnote** (400, 13px): the card header, box headings ("Your project", "Add to your project", "What you'll need", "You") in their own case, box footnotes, lot lines and a project's where-and-how line, fees, reviewers and clocks, the sidebar's "Town of Newcastle" (600) and "Permits", Change / Finish / Delete / Remove, "I don't know yet", "A tap moves on", the save status.
- **Group Header** (600, 13px, uppercase, wide tracking, secondary label): the heading above an inset group on the outer property pages only.
- **Caption** (400, 12px): status pills, a part's one-line summary ("28 × 40 ft · 2 floors", "3 answers to go"), a field's name above its value on You, the form's term on Check and send.
- **Tab Label** (400, 11px): the four labels in the phone's tab bar, under 22 px icons, as on iOS.

### Named Rules
**The System Face Rule.** Text is set in the device's system face at the ramp's sizes (30 / 22 / 20 / 17 / 15 / 14 / 13 / 12, and 11 for the tab bar alone); no other family is loaded and no other size is used.

**The One Question Rule.** A card body carries one Question line; help is one footnote line 4 px under it and 16 px above the control (its space held when empty so the control does not jump).

## Layout

The window switches at 1024 px (`useWideLayout`).

At 1024 px and wider it is a two-column grid on the grouped ground: a 250 px sticky sidebar with a 0.5 px separator on its right, padded 16 px by 10 px with 16 px between its parts, holding the Town seal (40 px) beside "Town of Newcastle" and "Permits", the four places (Home, Project, Messages, You; 44 px items, 2 px apart), and at its foot the save status when a project is open. The main area is padded 32 px. A card sits centred in it at 640 px, or 760 px for the lot drawing and compass.

Below 1024 px a bottom tab bar holds the same four places (each at least 48 px tall, a 22 px icon over its 11px label), on the grouped ground at 95% with blur, a 0.5 px separator above, safe-area aware. Pages scroll above it in 12 px gutters. In a card, a 44 px bar (the same 95% ground and blur, a 0.5 px separator beneath) holds ‹ Project on the left and the save status on the right, and the card fills the screen between the bar and the tab bar in 12 px gutters, its footer its own bottom band; a long body scrolls between header and footer. The Project place goes to the project last opened, or Home when there is none.

**The dashboard** is a grid at most 1040 px wide with 24 px gaps: one column on a phone, and at 1024 px and up a flexible main column beside a 280 px side column. The main column stacks the header (title and pill, 8 px apart), the parcel box, Your project, and Add to your project; the side column stacks What you'll need, You, and the full-width Check and send button. Each section is a box heading, 8 px of space, the box, and an optional footnote. Add tiles sit in a grid, 8 px apart, two columns once their container is 400 px (25rem) wide.

**Home, You and Messages** are a single centred column at most 512 px (`max-w-lg`), 24 px between sections. Signed out, Home is the seal and the sign-in card in a 448 px column, with no window around it. Starting a project is a full-window card on the grouped ground, padded 12 px on a phone and 32 px at 1024 px and up.

Inside a card: the body is padded 22 px top, 24 px sides, 18 px bottom, centred. Tiles sit in a grid at most 500 px wide, 8 px apart, two columns once the card is 400 px (25rem, container query) wide, one below. A set of values is a two-column grid at most 380 px (480 px when it holds text), 14 px across and 10 px down: short name left, field right; repeated values (one per floor) sit under a 0.5 px separator 10 px below. A choice that leads a set comes first as tiles; what depends on it (the roof's slope) appears once it is answered, under its own small footnote question (a ruling). Header and footer are padded 10 px by 16 px, items 10 px apart. Check and send's card body is padded 20 px by 16 px and stacks its boxes 24 px apart.

The compass and lot-diagram layouts are container-queried: at 42 rem (`@2xl`) and wider the four walls or setbacks arrange around a central drawing; narrower, the drawing comes first and the sides stack.

Spacing runs on a 4 px grid with the iOS odd steps the comp uses: 6 px inside groups, 8 px between tiles and under box headings, 10 px in headers and footers, 11 px by 16 px in rows, 12 px gutters, 24 px between sections and on body sides, 32 px around the desktop main area.

## Elevation & Depth

Flat by tone. Surfaces separate by ground-versus-row colour and 0.5 px hairlines, not shadows: the card and every box is a row-coloured panel with a hairline edge on the grouped ground. A sheet raises itself by reassigning its ground and row variables to the elevated values, which in dark mode makes it lighter than the window, as on iOS. The phone's bar and tab bar, which float over scrolling content, are 95% opaque with a backdrop blur. The one cast shadow is the slider's knob (`0 1px 4px rgba(0,0,0,0.3)`), a white circle as on iOS. The card button's focus ring is drawn with box-shadow (2 px row gap, then 2 px accent-text); it is a ring, not elevation.

### Named Rules
**The Tone Not Shadow Rule.** Containers never take a drop shadow; depth comes from ground, row, elevated row and the hairline.

## Shapes

Softly rounded rectangles. Cards, boxes, the sign-in card and outer inset groups are 12 px; tiles, add tiles, card buttons, sidebar items, segments and the compass's house square are 8 px; progress segments are 2 px; pills, chips and the rename button are fully round. Card and box edges and the hairlines within them are 0.5 px; outer inset groups keep 1 px dividers. A tile's edge is 0.5 px edge-grey, 1.5 px label when chosen (its padding drops 1 px so nothing moves). Empty checkboxes and radios carry a 1.5 px tertiary-label ring. The upload target is a 2 px dashed outline.

## Components

### Window
- **Sidebar (desktop):** the seal block links Home. Each place is a 44 px link, 12 px side padding, 8 px corners, its 18 px icon 12 px before a 15px label in label colour. The current place sits on the selection wash at weight 500; Project counts as current whenever a project is open.
- **Tab bar (phone):** four equal items, the 22 px icon over the 11px label; current in accent-text, the rest in secondary label.
- **Bar in a card (phone):** ‹ Project in 17px accent-text at 44 px, the save status at the right.

### Card (signature)
The unit of the application. Row colour, 0.5 px separator edge, 12 px corners, content clipped, no shadow; 640 px or 760 px wide. With a submit handler it is a form, so Return in a field means Continue.
- **Header:** footnote in secondary label: the part's name (or "Building 1 · A home"), the progress bar filling the space, then "3 of 6" in tabular numerals. Without a count, a title and a note on the right ("2 added"); the start cards' header is "New application" after its icon.
- **Body:** centred; the Question, the help line, an optional carried-answer footnote ("Filled in from your answers at the start. Change it if you need to."), the control, and where allowed "I don't know yet" (or "I don't know some of these yet" on a set) as a 13px accent-text link 12 px below, 44 px tall. Focus moves to the question on arrival. When the Town has locked the project, a footnote says so above the controls and they take no changes.
- **Footer:** Back (a plain button; on a part's first card it returns to the dashboard) left; Continue (filled) right where the card needs it, or "Skip for now" (plain) on an optional card left blank. Where a tap moves on, the right side reads "A tap moves on" in footnote on the first such card of a visit, then nothing.
- **Motion:** only the body moves: forward slides in from 24% right, Back from 24% left, 300 ms on `cubic-bezier(0.32, 0.72, 0, 1)`; a 120 ms fade under reduced motion.

### Progress bar
One segment per card in the part, 3 px tall, 3 px apart, 2 px corners; answered and current in label, the rest in edge. `role="img"`, "Question 3 of 6". On a check page the bar is full.

### Box
The list container outside the cards: a footnote heading in secondary label, in its own case, inset 16 px; 8 px below it a row-coloured box with a 0.5 px separator edge, 12 px corners and clipped contents; rows under 0.5 px hairlines; an optional footnote beneath, inset 16 px. Used on the dashboard, Home, You and Check and send. A row is padded 11 px by 16 px with 12 px gaps: an 18 px outline icon in secondary label, the name with an optional summary line beneath, a pill, and a chevron in tertiary label when the whole row is a link.

### Project dashboard (signature)
- **Header:** the title in Large Title with a 44 px round accent-text pencil to rename it (the title becomes a 17px field with Save filled and Cancel plain); below, the project's pill and, once sent or locked, a footnote of what that means.
- **Parcel:** a one-row box linking to Your lot: "Map 4, Lot 36" in 15px semibold over two footnote lot lines (where · district; acres · frontage), Your lot's pill, chevron.
- **Your project:** a box of 56 px rows, one per part after the cover sheet: icon, name in 15px, a Caption summary, its pill, chevron; a 13px destructive Remove at the right of a single part when there is more than one, behind a confirmation.
- **Add to your project:** add tiles for the parts not yet added: row-coloured, 0.5 px edge, 8 px corners, 48 px, an 18 px secondary-label icon, the 14px label, and a + in accent-text at the right. Hidden once locked.
- **Side column:** What you'll need, You (a one-row box to About you: the name in 15px over "The owner" or "Helping the owner" · email in footnote, its pill), and Check and send as a full-width filled button.

### What you'll need
A box headed "What you'll need", with any notes as footnotes above. Each permit is a section under a hairline: its name in 15px semibold with its application fee right in footnote ("$50 when you send"). Its reviews sit beneath, indented 28 px so the two levels read apart, each padded 9 px by 16 px under a hairline: the review in 14px label with its permit fee right in footnote, then the reviewer, each clock in plain words, "May be needed — the Code Enforcement Officer confirms" and "Not in the portal yet — the Town Office takes this one", each a footnote line. When there is nothing to list, one 14px secondary-label line says why. A footnote below says permit fees are due before a permit is issued.

### Status pill
Caption, 2 px by 9 px, fully round, never wrapping; tones done, progress, todo and warn. On a part: Done (done), "2 of 4" (progress, read aloud as "2 of 4 answered"), Not started (todo). On a project: Draft (todo), Sent and With the Town (progress), Decided (done); on the dashboard's header a draft shows "2 things left" (warn) or Ready to send (done).

### Tiles
- **Pick one** (radio tiles): one tab stop, arrow keys between tiles. A tap answers and, after 200 ms to see the choice, moves on, even on the tile already chosen; inside a set a tap only answers.
- **Pick several** (checkbox tiles): toggle; Continue moves on. No check mark on a chosen multi tile (a ruling); the 1.5 px edge alone shows it. The start's "What are you doing here?" card is pick-several tiles.
- **Style:** transparent, 0.5 px edge, 8 px corners, 48 px minimum, 10 px by 12 px padding, Row label left-aligned in label; an 18 px outline icon 10 px before it in secondary label. Chosen: 1.5 px label edge, no fill. Hover (pointer devices only): the edge turns secondary label. Focus: a 2 px accent-text ring offset 2 px. A question's tiles all carry icons or none do; roof styles carry their drawn silhouette instead.

### Buttons
- **Card button** (plain): transparent, 0.5 px edge border, 8 px corners, 36 px minimum, 7 px by 14 px padding, 15px label; an optional 16 px icon 6 px before the words (+ Add a building, Copy Building 1). Back, Cancel, Skip for now, the stepper's − and +, Continue an application and Sign out.
- **Filled:** the same shape filled in label with row-coloured text, near-black in light, near-white in dark. One per card or page: Continue, Done, Done with buildings, Send to the Town, Save, Check and send, Start a new application.
- **Full width:** at full width a button centres its label (Home's two, Sign out, Check and send).
- **Unavailable:** a disabled button keeps its shape with its label in secondary label. Send to the Town turns plain while things are left, and pressing it names the first one.
- **Link action:** accent-text words at 13px with a 44 px hit area: Change, Finish, "I don't know yet"; Delete and Remove in destructive.
- **Focus:** a 2 px accent-text ring on every control (on card buttons, outside a 2 px row-coloured gap).
- The outer property pages, the sign-in card and confirmation dialogs use HeroUI's buttons (secondary, danger, and teal primary).

### Home and Your applications
Signed in: the 80 px seal over the Title, then Start a new application (filled) and Continue an application (plain), both full width and 12 px apart, then a box "Your applications": a 56 px row per project, its first part's icon, its title in 15px at 500 over "Map 4, Lot 36 · 2 things left" (or "sent Oct 3") in footnote, its status pill, chevron. Signed out: the seal, the Title and the sign-in card (row colour, 12 px corners, 20 px padding).

### You and Messages
You: Large Title, then a box of 48 px rows, each a Caption field name over its value in 14px label ("Not given yet" when blank), Change at the right opening the field in place with Save and Cancel; the sign-in email last, unchangeable; Sign out full width below. Messages: Large Title over a 15px secondary-label paragraph at most 46ch.

### Set of values and stepper
Short names (Row, label) beside 110 px right-aligned number fields with the unit after in secondary label; a count (floors above ground) is − and + card buttons, 36 px square, with the number between in 15px tabular. Repeated values sit under a hairline.

### Check page and items list
- **Check <part>:** a card with a full bar; one row per answer, padded 11 px by 16 px under hairlines: the question in Row label, the answer in Row secondary label (the tile's own words; "Not answered"), Change at the right. Footer: Back, and Done (filled).
- **Buildings / Additions:** a card with "2 added" in the header; one row per item: its type's 18 px icon, "Building 1 · A home" in Row, a Caption summary ("28 × 40 ft · 2 floors · ..." or "3 answers to go"); Change (or Finish) and Delete at the right, Delete behind a confirmation. Footer: + Add a building, Copy Building 1, and Done with buildings (filled).

### Check and send
A card headed "Check and send" whose scrolling body stacks boxes of 48 px list rows: "2 things to finish first" (a linked row per part still to finish), "Your project at a glance" (the parcel, the applicant and each part with its summary, each with Change), "What's due when you send" (a row per application fee, then the total in semibold, a footnote on permit fees) and "The official forms" (each form with a disabled View). Footer: Back, and Send to the Town (filled; plain while things are left; gone once sent). Sending asks first in a dialog listing the permits and the fees due.

### "Is this right?"
Inside the card body: the map's value in Confirm Value, its source in footnote, then tiles "Yes, that's right" and "No, I'll correct it" (and "Use the map's ..." once corrected).

### Inset Group
Kept, rounded, for the outer property pages and some field controls. 12 px corners, contents clipped; row on the grouped ground with 1 px separators; uppercase group header above and footnote below, inset 16 px; rows 44 px minimum.

### Inputs and other controls
Fields on the field fill, no border, 44 px tall (a ruling: the brief's 36 px is under the touch minimum), 15px text, numbers right-aligned. Segmented choices and choice chips outside the cards keep the wash-plus-accent-edge selection. Sliders carry the iOS knob. Upload is a dashed accent-text target.

### Sheet
Only "Add a use". A header row in the row colour: Cancel left, semibold 17px title centred, Done right in accent-text. Esc cancels; the backdrop does not dismiss.

### Lot diagram and compass
Plain line drawings that orient the questions, inside a 760 px card: the lot as a selection-wash polygon outlined 2 px in seal teal with the building as a row-coloured square outlined in label; the compass as a label-coloured north arrow and a 2 px label-outlined square for the house. Walls are named from the way the front faces ("Front (north, faces Sheepscot Road)"), asked once the front's direction is chosen.

## Do's and Don'ts

### Do:
- **Do** put every question in a card: header with bar and count, body with one question, footer with Back and at most one filled button.
- **Do** let a single choice answer at a tap and move on after 200 ms; give Continue only to what a tap cannot finish.
- **Do** show progress with the card header's segmented bar and a part's or project's status with its pill, one tone per meaning.
- **Do** put lists outside a card in boxes: a 13px heading in its own case, a 12 px-cornered row-coloured box, hairline rows.
- **Do** draw icons from the pinned Tabler outline set at 18 px, stroke 1.75 (22 px in the tab bar); give a question's tiles icons on every option or none.
- **Do** keep fields, sidebar items and every link action at 44 px; tiles, add tiles and list rows at 48 px; dashboard and project rows at 56 px.
- **Do** use the `--app-*` variables (or HeroUI's variables mapped onto them), never literal hex, so light, dark and sheet elevation all follow.
- **Do** keep Home, Project, Messages and You in the sidebar at 1024 px and up and in the bottom tab bar below; a card on a phone gets ‹ Project.

### Don't:
- **Don't** bring back the answer trail, page dots, a footer action bar, a large-title navigation bar inside a card, the task list or a long review page; the dashboard is the recap.
- **Don't** fill a card's button with teal; the filled button is the label colour.
- **Don't** fill a chosen tile; show it with the 1.5 px label edge.
- **Don't** use the done green or warning amber outside a pill.
- **Don't** imitate native window chrome: no traffic lights, fake status bars or title-bar controls.
- **Don't** drop-shadow a container; raise a sheet by tone.
- **Don't** set text in the seal teal; text teal is accent-text.
- **Don't** use filled icons, emoji or hand-drawn paths for icons (roof silhouettes and the two diagrams excepted).
- **Don't** load a web font or display face, or set a size off the ramp.
