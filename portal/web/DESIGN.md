---
name: Town of Newcastle Applicant Portal
description: A permit application as a document with sections, in the grammar of Apple's Settings, under the Town seal's teal.
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
  title:
    fontFamily: "-apple-system, BlinkMacSystemFont, \"SF Pro Text\", system-ui, \"Segoe UI\", Roboto, sans-serif"
    fontSize: "22px"
    fontWeight: 700
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
  button-ghost:
    textColor: "{colors.accent-text}"
    height: "44px"
  segment:
    rounded: "{rounded.lg}"
    padding: "0 16px"
    height: "44px"
  segment-selected:
    backgroundColor: "{colors.selection}"
    rounded: "{rounded.lg}"
  tile:
    backgroundColor: "{colors.row}"
    rounded: "{rounded.xl}"
    padding: "12px 16px"
    height: "56px"
  tile-selected:
    backgroundColor: "{colors.selection}"
    rounded: "{rounded.xl}"
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

**Creative North Star: "The Settings Pane"**

The portal is Apple's System Settings and iOS Settings, applied to a Town permit: a source-list sidebar of steps beside a content pane on a desktop, a large-title root list that pushes each step in on a phone, grouped inset lists of questions, and sheets for the repeating items (buildings, additions). The application reads as a document with sections, never a corridor of one-field screens: a step is one pane holding every question for that section in grouped rows.

The world is quiet and native. Type is the device's own system face; colour is Apple's system greys and grouped grounds; the only hue is the Town seal's teal, split into the seal's own teal for identity and a deeper teal for actions. Light and dark follow the device (`main.tsx` sets `data-theme`; a `prefers-color-scheme` media query covers first paint). Native grammar is used without imitating native chrome: there are no fake window controls, traffic lights or status bars.

**Key Characteristics:**
- Grouped inset lists on a grey grouped ground; white (or dark grey) rows divided by hairlines.
- Two-pane window at 1024 px and up; a push-navigation stack below.
- One accent hue, in two depths; selection is a pale (or deep) teal wash, never a saturated block.
- 44 px minimum height for every interactive row and control.
- Depth by tone, not shadow; in dark mode a sheet is lighter than the window beneath it.

## Colors

Apple's system neutrals with one civic accent, the teal of the Town seal. The `--app-*` custom properties in `src/index.css` are the source; `src/theme/tokens.ts` holds the same values and a test keeps them in step. Dark values are the `-dark` keys; tokens without one are identical in both modes.

### Primary
- **Harbour Teal** (accent): the fill of primary buttons (Continue, Start), done and started step glyphs, and the border of a selected segment, tile, chip, checkbox or radio. The same in light and dark.
- **Harbour Teal Text** (accent-text / accent-text-dark): teal used as text: links, ghost buttons (Done, Edit, Add), the phone's back chevron, the focus ring. In dark mode it lifts to a bright aqua so it stays legible on black.
- **On Accent** (on-accent): text and checkmarks on a teal fill.

### Secondary
- **Seal Teal** (seal): the seal's own teal (about 3.4:1 on white), kept for identity marks that need not carry text: the dot on a step glyph for answers left as "I don't know yet", and the outline of the lot in the lot diagram.
- **Selection Wash** (selection / selection-dark): the background of the current sidebar step (60% on hover) and of a selected segment, tile or chip; the lot fill in the lot diagram.

### Tertiary
- **System Red** (destructive / destructive-dark): Remove actions and error messages only.

### Neutral
- **Grouped Ground** (ground / ground-dark): the window, the sidebar and the ground under every inset group. Pure black in dark mode.
- **Row** (row / row-dark): inset group rows, tiles, the outer pages' header bar, the sheet header and the phone's action bar.
- **Raised Ground and Row** (ground-elevated-dark, row-elevated-dark): inside a sheet the ground and row variables are reassigned to these, so in dark mode the sheet sits one step lighter than the window. In light mode they equal ground and row.
- **Field Fill** (fill / fill-dark): text, number and select fields; iOS's tertiary fill, opaque.
- **Separator** (separator / separator-dark): hairlines between rows, toolbar and action-bar rules, segment, tile and chip outlines.
- **Label, Secondary Label, Tertiary Label**: primary text; help text, footnotes, save status and group headers; disclosure chevrons, empty step glyphs, unselected page dots and the 1.5 px edge of an empty checkbox or radio.

*Divergence from the direction contract:* the contract gives the seal's teal (#1098A8) to "identity and selection". The build shows selection with the selection wash and a deep-accent border, and uses the seal teal only for the follow-up dot and the lot outline. The build is recorded here.

### Named Rules
**The Two Teals Rule.** A teal that carries text or fills a control is the deep accent (or the lifted accent-text in dark); the seal's own teal marks identity and never carries text.

**The Wash Rule.** Selection is shown by a selection-wash background plus an accent border, never by a solid teal block. The only solid teal fills are the primary button and a done step's glyph.

## Typography

**Display Font:** none; the system stack throughout.
**Body Font:** -apple-system, BlinkMacSystemFont, "SF Pro Text", system-ui, "Segoe UI", Roboto, sans-serif, antialiased.

**Character:** The device's own interface face at Apple's text sizes, so the portal reads as part of the phone or Mac rather than a website.

### Hierarchy
- **Large Title** (700, 30px, leading-tight): the phone's step title under the navigation bar, the phone root list "Your application", and the home page heading.
- **Title** (700, 22px): the desktop toolbar's step title.
- **Headline** (600, 17px): the sheet title, the outer header's "Town of Newcastle", primary button labels on the phone and home page.
- **Body** (400, 17px): phone list rows, hub rows, links in the outer header.
- **Body Compact** (400, 15px): question labels in inset rows, desktop sidebar rows (14px when nested), chips, help text beside layouts.
- **Footnote** (400, 13px): group footers, the save status ("Saving…", "Saved"), captions such as "Not to scale", the sidebar's seal caption.
- **Group Header** (600, 13px, uppercase, wide tracking, secondary label): the heading above an inset group, as in iOS Settings.

### Named Rules
**The System Face Rule.** Text is set in the device's system face at Apple's sizes (30 / 22 / 17 / 15 / 13); no other family is loaded.

## Layout

At 1024 px and wider the app is a two-pane window: a 17 rem sidebar on the grouped ground with a right hairline, beside a content column that tops out at 48 rem (max-w-3xl), centred, padded 32 px across and 24 px down. A 56 px toolbar holds the step title, save status and Done; Back and Continue sit bottom right under a hairline, Continue rightmost.

Below 1024 px the root is the step list; choosing a step pushes it in under a sticky 44 px navigation bar (back chevron, save status) and a large title. Content is padded 16 px with 128 px at the bottom to clear the fixed action bar, whose full-width Continue respects the safe-area inset.

Outer pages (home, start, my applications) use a 56 px header bar and a centred 48 rem column; the home page narrows to 32 rem.

Spacing runs on a 4 px grid: 6 px between a group's header, rows and footer; 8 px and 12 px inside rows and between choices; 16 px between list blocks; 24 px between groups in a pane or sheet. Inset rows are 44 px minimum with 16 px side and 10 px vertical padding. On a wide screen a row with a short control puts the label left and the control right (a 12 rem minimum label column, 1 : 1.4); long controls stack under the label, and rows inside a sheet always stack. A switch sits at the end of its question's line.

The compass and lot-diagram layouts are container-queried: at 42 rem (`@2xl`) and wider, the four walls or sides arrange around a central drawing; narrower, the drawing comes first and the sides stack.

## Elevation & Depth

Flat by tone. Surfaces separate by ground-versus-row colour and hairline separators, not shadows. A sheet raises itself by reassigning its ground and row variables to the elevated values, which in dark mode makes it lighter than the window, as on iOS. The two bars that float over scrolling content (the phone's navigation bar and action bar) are 95% opaque with a backdrop blur. The one shadow is the slider's knob (`0 1px 4px rgba(0,0,0,0.3)`), a white circle as on iOS.

### Named Rules
**The Tone Not Shadow Rule.** Containers never take a drop shadow; depth comes from ground, row and elevated row.

## Shapes

Softly rounded rectangles and circles. Inset groups, tiles, the upload target and the home page's start button are 12 px; sidebar rows, segments and the compass's house square are 8 px; chips, page dots, status glyphs and HeroUI's buttons are fully round. Outlines are 1 px separator hairlines, turning accent when selected; the upload target is a 2 px dashed separator outline. Status glyphs are drawn SVG: an empty 1.5 px tertiary-label ring (not started), a half-filled accent disc (started), a filled accent disc with an on-accent check (done), plus a seal-teal dot ringed in the row colour when answers await follow-up.

## Components

### Buttons
- **Shape:** HeroUI's fully round button, at least 44 px high.
- **Primary:** accent fill, on-accent text. Desktop: 44 px, at least 7 rem wide. Phone: full width, 48 px, 17px text, in the fixed action bar.
- **Secondary:** HeroUI's soft grey secondary for Back, Done in the toolbar and "Load the latest".
- **Ghost:** accent-text label, no fill, for Cancel and Done in a sheet header (Done semibold), Edit, Add and hub actions; destructive text for Remove.
- **Focus:** a 2 px ring in accent-text.

### Inset Group
- **Corner Style:** 12 px, contents clipped.
- **Background:** row on the grouped ground; separator hairlines between rows.
- **Header / Footer:** an optional group header above and a 13px secondary-label footnote below, both inset 16 px.

### Choice controls
- **Segmented choice** (2 to 4 options, and yes/no with neither picked until answered): 8 px outlined pills side by side, 44 px high, 16 px padding.
- **Tiles** (more options): 12 px rows in a one- or two-column grid, 56 px minimum, row background; roof styles carry a silhouette.
- **Chips** (choose several): fully round, 44 px, 15px text.
- **Selected state** for all three: selection wash plus an accent border.
- **Checkboxes and radios:** an empty control has a 1.5 px tertiary-label edge (3:1 against its row); selected takes the accent.
- **Switch:** HeroUI's switch at size lg, at the end of its question's line.

### Inputs / Fields
- **Style:** HeroUI fields on the field fill, 44 px minimum; numbers right-aligned with the unit in secondary label after the field; steppers add 44 px − and + buttons.
- **Upload:** a 56 px, 12 px-radius dashed target in accent-text, semibold 17px, then a list of files in an inset group with 40 px thumbnails.

### Navigation
- **Desktop sidebar:** seal (40 px) and the form's name at the top; each step a 44 px, 8 px-radius row with its status glyph at 15px; the current step semibold on the selection wash. Arrow keys move between steps; ⌥/⌘ + ↑/↓ change step from anywhere.
- **Phone:** the root list is an inset group of 48 px rows at 17px with a disclosure chevron; a step's navigation bar carries a back link in accent-text. A left-edge swipe goes back.
- **Motion:** a step pushes in on a phone (250 ms, `cubic-bezier(0.32, 0.72, 0, 1)`, from 24% right), cross-fades on a desktop (150 ms ease-out), and with reduced motion fades (120 ms ease-out).

### Sheet
Over the window on a desktop (HeroUI modal, size lg), full height on a phone. A header row in the row colour: Cancel left, semibold 17px title centred, Done right in accent-text. Body padded 16 px by 20 px with 24 px between groups. Items with pages show 8 px page dots (label colour current, tertiary label otherwise) in 44 px targets. Esc cancels; the backdrop does not dismiss.

### Lot diagram and compass (signature)
Plain line drawings that orient the questions: the lot as a selection-wash polygon outlined 2 px in seal teal with the building as a row-coloured square outlined in label, captioned "Not to scale"; the compass as a label-coloured north arrow and a 2 px label-outlined square for the house.

## Do's and Don'ts

### Do:
- **Do** put every question of a section in grouped inset rows on one pane; a step is a section, not a single question.
- **Do** give every interactive row, button and choice at least 44 px of height.
- **Do** use the `--app-*` variables (or HeroUI's variables mapped onto them), never literal hex, so light, dark and sheet elevation all follow.
- **Do** show selection with the selection wash and an accent border.
- **Do** keep the two-pane window at 1024 px and up and the push stack below.

### Don't:
- **Don't** imitate native window chrome: no traffic lights, fake status bars or title-bar controls.
- **Don't** drop-shadow a container; raise a sheet by tone.
- **Don't** set text in the seal teal; text teal is accent-text.
- **Don't** load a web font or display face; the system stack is the type.
