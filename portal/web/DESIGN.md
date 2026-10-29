---
name: Town of Newcastle Applicant Portal
description: A permit application asked one question at a time, in the grammar of Apple's Settings and Setup Assistant, under the Town seal's teal.
colors:
  accent: "#0C727E"
  accent-text: "#0C727E"
  accent-text-dark: "#4CC9D8"
  on-accent: "#FFFFFF"
  seal: "#1098A8"
  selection: "#DCEFF1"
  selection-dark: "#123C42"
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
    fontWeight: 700
  question:
    fontFamily: "-apple-system, BlinkMacSystemFont, \"SF Pro Text\", system-ui, \"Segoe UI\", Roboto, sans-serif"
    fontSize: "22px"
    fontWeight: 600
    lineHeight: 1.25
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
  footnote:
    fontFamily: "-apple-system, BlinkMacSystemFont, \"SF Pro Text\", system-ui, \"Segoe UI\", Roboto, sans-serif"
    fontSize: "13px"
    fontWeight: 400
  group-header:
    fontFamily: "-apple-system, BlinkMacSystemFont, \"SF Pro Text\", system-ui, \"Segoe UI\", Roboto, sans-serif"
    fontSize: "13px"
    fontWeight: 600
    letterSpacing: "0.025em"
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
  inset-group:
    backgroundColor: "{colors.row}"
    rounded: "{rounded.xl}"
  inset-row:
    padding: "10px 16px"
    height: "44px"
  sidebar-row:
    rounded: "{rounded.lg}"
    padding: "0 12px"
    height: "44px"
  sidebar-row-current:
    backgroundColor: "{colors.selection}"
    textColor: "{colors.label}"
    rounded: "{rounded.lg}"
  button-primary:
    backgroundColor: "{colors.accent}"
    textColor: "{colors.on-accent}"
    rounded: "{rounded.full}"
    height: "44px"
  button-primary-phone:
    backgroundColor: "{colors.accent}"
    textColor: "{colors.on-accent}"
    typography: "{typography.body}"
    height: "48px"
  button-back:
    textColor: "{colors.label}"
    rounded: "{rounded.full}"
    height: "44px"
    width: "96px"
  button-ghost:
    textColor: "{colors.accent-text}"
    height: "44px"
  wizard-tile:
    backgroundColor: "{colors.row}"
    textColor: "{colors.label}"
    typography: "{typography.body}"
    rounded: "{rounded.xl}"
    padding: "12px 16px"
    height: "58px"
  wizard-tile-chosen:
    backgroundColor: "{colors.row}"
    rounded: "{rounded.xl}"
    padding: "11px 15px"
  trail-chip:
    backgroundColor: "{colors.row}"
    textColor: "{colors.label}"
    typography: "{typography.footnote}"
    rounded: "{rounded.full}"
    padding: "4px 12px"
  trail-chip-carried:
    backgroundColor: "{colors.row}"
    rounded: "{rounded.full}"
  dot:
    backgroundColor: "{colors.separator}"
    rounded: "{rounded.full}"
    size: "7px"
  dot-current:
    backgroundColor: "{colors.label}"
    rounded: "{rounded.full}"
    size: "7px"
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
  field:
    backgroundColor: "{colors.fill}"
    textColor: "{colors.label}"
    height: "44px"
---

# Design System: Town of Newcastle Applicant Portal

## Overview

**Creative North Star: "The Settings Pane, One Question at a Time"**

The portal is Apple's System Settings and iOS Settings applied to a Town permit, asked the way Setup Assistant asks: one centred question per screen, moving sideways. On a desktop a source-list sidebar of sections (with buildings and additions nested) sits beside the content pane, so the application still reads as a document with sections; on a phone the sections are one tap away behind "Steps". Inside a section, each question takes the pane: a large question, one line of help when it earns one, and the control. The answers given so far stack as chips in a trail across the top; plain dots at the bottom left say where you are; a single choice answers at a tap and moves on.

The world is quiet and native. Type is the device's own system face; colour is Apple's system greys and grouped grounds; the only hue is the Town seal's teal, split into the seal's own teal for identity and a deeper teal for actions. Light and dark follow the device (`main.tsx` sets `data-theme`; a `prefers-color-scheme` media query covers first paint). Native grammar is used without imitating native chrome: no fake window controls, traffic lights or status bars. Grouped inset lists remain the grammar of the read-only and summary pages (home, results, my applications, review); sheets remain only for "More detail" on review and "Add a use".

**Key Characteristics:**
- One centred question per screen; a tap on a single-choice tile answers and moves on.
- An answer trail of chips above, 7 px dots below; sections in the sidebar (desktop) or behind Steps (phone).
- Two-pane window at 1024 px and up; navigation bar, large title and fixed footer below.
- One accent hue, in two depths; a chosen tile is a 2 px accent edge, never a solid teal block.
- 44 px minimum for every interactive target; tiles 58 px.
- Depth by tone, not shadow.

## Colors

Apple's system neutrals with one civic accent, the teal of the Town seal. The `--app-*` custom properties in `src/index.css` are the source; `src/theme/tokens.ts` holds the same values and a test keeps them in step. Dark values are the `-dark` keys; tokens without one are identical in both modes.

### Primary
- **Harbour Teal** (accent): the fill of primary buttons (Continue, Start this application), done and started step glyphs, the 2 px edge of a chosen wizard tile, and the border of a selected segment, chip, picker tile, checkbox or radio. The same in light and dark.
- **Harbour Teal Text** (accent-text / accent-text-dark): teal used as text: links, ghost buttons, "I don't know yet", the phone's ‹ Back and Steps, the check on a chosen multi-choice tile, the focus ring. In dark mode it lifts to a bright aqua so it stays legible on black.
- **On Accent** (on-accent): text and checkmarks on a teal fill.

### Secondary
- **Seal Teal** (seal): the seal's own teal (about 3.4:1 on white), kept for marks that carry no text: the follow-up dot on a step glyph for answers left as "I don't know yet", and the outline of the lot in the lot diagram.
- **Selection Wash** (selection / selection-dark): the background of the current sidebar section (60% on hover), of a selected segment, chip, picker tile or use tag, and the lot fill in the lot diagram. Wizard tiles do not take it.

### Tertiary
- **System Red** (destructive / destructive-dark): Remove actions and error messages only.

### Neutral
- **Grouped Ground** (ground / ground-dark): the window, the sidebar, the desktop footer and the ground under every inset group. Pure black in dark mode.
- **Row** (row / row-dark): inset rows, wizard tiles, trail chips, the sheet header and the phone footer (95% with blur).
- **Raised Ground and Row** (ground-elevated-dark, row-elevated-dark): inside a sheet the ground and row variables are reassigned to these, so in dark mode the sheet sits one step lighter than the window. In light mode they equal ground and row.
- **Field Fill** (fill / fill-dark): text, number and select fields; iOS's tertiary fill, opaque.
- **Separator** (separator / separator-dark): hairlines between rows, under the trail and navigation bar, above the footer; tile and chip outlines; the unlit dots.
- **Label**: primary text, the current dot, the desktop Back button's text.
- **Secondary Label**: help text, the save status, the trail's empty line, the source line under a confirmed value, the carried-answer line, "13 of 20".
- **Tertiary Label**: disclosure chevrons, empty step glyphs, the hover edge of an unchosen tile, the dashed edge of a carried chip, the 1.5 px edge of an empty checkbox or radio.

*Divergence from the direction contract:* the contract gives the seal's teal (#1098A8) to "identity and selection". The build shows selection with the deep accent (a 2 px edge on wizard tiles; wash plus 1 px edge elsewhere) and uses the seal teal only for the follow-up dot and the lot outline. The build is recorded here.

### Named Rules
**The Two Teals Rule.** A teal that carries text or fills a control is the deep accent (or the lifted accent-text in dark); the seal's own teal marks identity and never carries text.

**The Edge Not Block Rule.** Choice is shown by an accent edge, never a solid teal block: a wizard tile thickens its edge to 2 px accent on the row colour; the older controls (segments, chips, picker tiles, the current sidebar row) add the selection wash. The only solid teal fills are the primary button and a done step's glyph.

## Typography

**Display Font:** none; the system stack throughout.
**Body Font:** -apple-system, BlinkMacSystemFont, "SF Pro Text", system-ui, "Segoe UI", Roboto, sans-serif, antialiased.

**Character:** The device's own interface face at Apple's text sizes, so the portal reads as part of the phone or Mac rather than a website.

### Hierarchy
- **Large Title** (700, 30px, leading-tight): the phone's section title under the navigation bar, the phone step list "Your application", the home heading, each result's "You'll need a …".
- **Confirm Value** (600, 30px, tabular numerals): the value from the Town's map on an "Is this right?" screen, with "From the Town's map" in footnote below.
- **Title** (700, 22px): the desktop toolbar's section title.
- **Question** (600, 22px, leading-tight, centred, balanced, at most 30ch): the question on every wizard and start screen.
- **Headline** (600, 17px): the sheet title, the outer header's "Town of Newcastle".
- **Body** (400, 17px): tile labels, phone list rows, results prose, the phone's Continue, ‹ Back and Steps, number inputs on the start screens.
- **Body Compact** (400, 15px): the help line under a question (secondary label, centred, at most 46ch), "I don't know yet", wall labels, sidebar rows (14px when nested), error lines.
- **Footnote** (400, 13px): trail chips, the save status, "13 of 20", the item line ("Building 1") and short field names above set controls, the carried-answer line, captions.
- **Group Header** (600, 13px, uppercase, wide tracking, secondary label): the heading above an inset group, as in iOS Settings.

### Named Rules
**The System Face Rule.** Text is set in the device's system face at Apple's sizes (30 / 22 / 17 / 15 / 13); no other family is loaded.

**The One Question Rule.** A screen carries one Question line; help is one Body Compact line beneath it (its 20 px slot is held even when empty so the control does not jump).

## Layout

At 1024 px and wider the app is a two-pane window: a 17 rem sidebar on the grouped ground with a right hairline, beside the main column. The main column stacks a 56 px toolbar (section title, save status, Save and close), the answer trail full width under it, then a content column capped at 48 rem (max-w-3xl), centred, padded 32 px across and 24 px down. The footer is sticky to the bottom of the window on the grouped ground under a hairline: dots at the left, Back and Continue at the right, Continue rightmost.

Below 1024 px there is no sidebar. A sticky 44 px navigation bar (‹ Back left; save status and Steps right; 95% ground with blur) sits over a large title, then the trail, then the content padded 16 px with 128 px at the bottom to clear the fixed footer. The footer holds the dots at the left and Continue at the right (at least 8 rem, 48 px); when a screen has no dots Continue runs full width. Back lives only in the navigation bar on a phone. The footer respects the safe-area inset.

The question screen is centred: item line, question, help, an optional carried-answer line, then the control, with 8 px between them, 16 px before the control and 24 px above and below (32 px on the start screens). Tiles sit in a grid up to 36 rem (max-w-xl), one column on a phone and two from 640 px, 10 px apart; two choices or fewer keep one column at 28 rem (max-w-md). Fields asked together sit side by side from 640 px in a 32 rem grid, each under its short name.

The answer trail is one row: a single horizontally scrolling line of chips on a phone, wrapping from 640 px; 44 px minimum, padded 10 px by 20 px, 6 px between chips, a hairline beneath.

The compass and lot-diagram layouts are container-queried: at 42 rem (`@2xl`) and wider, the four walls or setbacks arrange around a central drawing; narrower, the drawing comes first and the sides stack.

Outer pages (home, results, my applications) use a centred column; the home page narrows to 32 rem. Spacing runs on a 4 px grid: 6 px inside groups and between chips, 8 / 10 / 12 px between choices, 16 px between blocks, 24 px between groups.

## Elevation & Depth

Flat by tone. Surfaces separate by ground-versus-row colour and hairline separators, not shadows. A sheet raises itself by reassigning its ground and row variables to the elevated values, which in dark mode makes it lighter than the window, as on iOS. The two phone bars that float over scrolling content (navigation bar and footer) are 95% opaque with a backdrop blur; the desktop footer is the solid ground. The one shadow is the slider's knob (`0 1px 4px rgba(0,0,0,0.3)`), a white circle as on iOS.

### Named Rules
**The Tone Not Shadow Rule.** Containers never take a drop shadow; depth comes from ground, row and elevated row.

## Shapes

Softly rounded rectangles and circles. Inset groups, wizard tiles, picker tiles, the map frame and the upload target are 12 px; sidebar rows, segments and the compass's house square are 8 px; trail chips, choice chips, dots, status glyphs and HeroUI's buttons are fully round. Outlines are 1 px separator hairlines; a chosen wizard tile's edge is 2 px accent (its padding drops by 1 px so nothing shifts); a carried chip's edge is dashed in tertiary label; the upload target is a 2 px dashed outline. Status glyphs are drawn SVG: an empty 1.5 px tertiary-label ring (not started), a half-filled accent disc (started), a filled accent disc with an on-accent check (done), plus a seal-teal dot when answers await follow-up.

## Components

### Question screen
Centred column: the item line in footnote when the question belongs to a building or addition, the Question, the help line, then the control. An answer carried from "Do I need a permit?" adds a footnote line, "Filled in from your answers at the start. Change it if you need to." Where a question allows it, "I don't know yet" sits under the control as a 44 px accent-text link in Body Compact. Focus moves to the question on arrival; screen readers hear "Question n of m: …".

### "Is this right?"
A value from the Town's map shown in Confirm Value, its source in footnote below, then two tiles, "Yes, that's right" and "No, I'll correct it". Correcting swaps the tiles for the field.

### Tiles
- **Pick one** (radio tiles): a radio group with one tab stop and arrow keys between tiles. A tap answers and, after 200 ms to see the choice, moves on, even on the tile already chosen. Yes/no questions and loop questions ("Is there another building…?") are two tiles.
- **Pick several** (checkbox tiles): each chosen tile shows a 20 px accent-text check at its end; Continue moves on.
- **Style:** row background, 1 px separator edge (tertiary label on hover), 12 px radius, 58 px minimum, 12 px by 16 px padding, 17px label left-aligned; chosen is a 2 px accent edge. Roof styles carry a drawn silhouette before the label.

### Answer trail
Chips of this section's (or this building's) answers, 13px on the row colour with a 1 px separator edge, fully round, truncated at 18 rem. Yes/no and number answers read "Name: value". A tap returns to that question. A carried answer has a dashed tertiary-label edge. Before the first answer the row reads "Your answers appear here as you go" in secondary label.

### Dots
7 px circles 7 px apart: the current one in label, the rest in separator. Past twelve questions they become "13 of 20" in footnote, tabular. The dots count the questions in the current section or item.

### Footer
- **Desktop:** sticky, grouped ground, hairline above, 32 px by 16 px padding. Dots left; Back (HeroUI secondary, at least 6 rem, text in label) and Continue (primary, at least 7 rem) right.
- **Phone:** fixed, 68 px minimum, 95% row with blur. Dots left, Continue right at 48 px and 17px.
- *Divergence from the wizard spec:* it puts Back in the phone's bottom bar; the build (like the contract's FIRST VIEWPORT) keeps Back only in the navigation bar.
- A screen that a tap answers has no Continue. An optional question shows "Skip for now" in Continue's place until answered.

### Phone navigation bar
44 px, sticky. ‹ Back in accent-text at 17px goes to the previous question (an edge swipe does the same); Steps in accent-text opens the section list. Outside the wizard the left link returns to the list under its own name.

### Motion
Each question slides: forward pushes in from 24% right, back pulls in from 24% left, both 300 ms on `cubic-bezier(0.32, 0.72, 0, 1)`, on desktop and phone alike. Changing section on a desktop cross-fades (150 ms ease-out). With reduced motion every change is a 120 ms fade.

### Buttons
- **Primary:** accent fill, on-accent text, fully round, 44 px (48 px and 17px on a phone and on results).
- **Secondary:** HeroUI's soft grey, for Back on a desktop (text in label) and Save and close.
- **Ghost:** accent-text label, no fill, for sheet Cancel and Done, "I can't find my property", Edit and Add; destructive text for Remove.
- **Focus:** a 2 px ring in accent-text on every control.

### Inset Group
Kept for home, results, my applications, "Is this your property?" and review. 12 px corners, contents clipped; row on the grouped ground with separator hairlines; optional group header above and footnote below, inset 16 px; rows 44 px minimum.

### Other controls
Fields on the field fill at 44 px (48 px on the start screens), numbers right-aligned with the unit in secondary label after; steppers add 48 px − and + buttons on the start screens. Segmented choices, choice chips and picker tiles (building and street pickers) keep the wash-plus-edge selection. Sliders carry the iOS knob. Upload is a 12 px dashed accent-text target.

### Sheet
Only "More detail" (review) and "Add a use". Over the window on a desktop (HeroUI modal, size lg), full height on a phone. A header row in the row colour: Cancel left, semibold 17px title centred, Done right in accent-text. Body padded 16 px by 20 px with 24 px between groups. Esc cancels; the backdrop does not dismiss.

### Lot diagram and compass (signature)
Plain line drawings that orient the questions: the lot as a selection-wash polygon outlined 2 px in seal teal with the building as a row-coloured square outlined in label; the compass as a label-coloured north arrow and a 2 px label-outlined square for the house. On the setbacks and walls screens the fields arrange around the drawing at 42 rem and wider; walls are named from the way the front faces ("Front (north, faces Sheepscot Road)").

## Do's and Don'ts

### Do:
- **Do** ask one question per screen, centred, with at most one line of help.
- **Do** let a single choice answer at a tap; give Continue only to what a tap cannot finish.
- **Do** show progress with the trail above and 7 px dots below; never a labelled stepper bar.
- **Do** give every interactive target at least 44 px; tiles 58 px.
- **Do** use the `--app-*` variables (or HeroUI's variables mapped onto them), never literal hex, so light, dark and sheet elevation all follow.
- **Do** keep the sidebar of sections at 1024 px and up, and Steps one tap away below.

### Don't:
- **Don't** imitate native window chrome: no traffic lights, fake status bars or title-bar controls.
- **Don't** drop-shadow a container; raise a sheet by tone.
- **Don't** set text in the seal teal; text teal is accent-text.
- **Don't** fill a chosen tile with solid teal.
- **Don't** put a building or addition in a sheet, or page dots in a sheet; sheets are for "More detail" and "Add a use".
- **Don't** load a web font or display face; the system stack is the type.
