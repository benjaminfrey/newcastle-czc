# Summary of Changes — v0.15-draft

**Release type: Terminology — adopt "Thoroughfare" as the collective term; retitle
Article 3 "Thoroughfares."** This release changes *vocabulary only*. No standard,
dimension, Type, rubric, or process changes. Where the Code formerly used a
collective compound — "Street/Road Type," "Streets and Roads," "a street or road" —
it now uses the umbrella term **Thoroughfare**. **Street** and **Road** are retained
wherever they name one of the two families or a specific Type. The result is a
cleaner, more consistent vocabulary with no regulatory effect.

**Compares against:** [v0.14-draft](../v0.14-draft/). Same content, same exhibits,
same pagination — only the collective terminology differs.

## 1. Why this is clean (the Code was already built for it)

Article 9 already defined **Thoroughfare** as *"an umbrella term for any Street,
Road, or Driveway… all ten [Types] plus the Driveway category,"* and the **Street**
definition already read *"A thoroughfare classified under the Street family of
Types."* So this release promotes a term the Code had already established and retires
the clumsy "Street/Road" compound. The model:

```
THOROUGHFARE  (umbrella — already defined; includes driveways)
├── Street family (S1–S5)   ← kept
├── Road family   (R1–R5)   ← kept
└── Driveway (D)            ← kept (a thoroughfare, but not a numbered Type)
```

Because a driveway *is* a Thoroughfare under the existing definition, the title
**"Thoroughfares" legitimately covers §7 Driveways and §8 Entrances.**

## 2. What was renamed (collective → Thoroughfare)

- **Article 3 title:** "Streets, Roads & Driveways" → **"Thoroughfares"** (H1, running
  head, rotated tab, TOC entry, cover banner, the `article-08` cross-reference, and
  the standalone deliverable's filename).
- **Six section headings:** §2 "Thoroughfare Types," §3 "Thoroughfare Standards,"
  §5 + §5.c "…Existing Thoroughfares," §6 "New Thoroughfares," §14 "Nonconforming
  Thoroughfares."
- **Defined term:** `Street/Road Type` → **`Thoroughfare Type`** (and the entry moved
  to follow the `Thoroughfare` entry alphabetically; the `Thoroughfare` definition's
  body updated to "all ten Thoroughfare Types").
- **Table 3.4** column header → "Default Thoroughfare Type(s)."
- **~90 collective prose phrasings** across Article 3, the Article 2 prefatory lot
  standards, and the Article 8/9 cross-references ("every street and road," "a street
  or road," "new Streets and Roads," "the Type of a street or road" → "thoroughfare").
- **Rendered exhibit + plate labels:** Exhibit 3.2 "THOROUGHFARE TYPE MAP," Exhibit
  3.1 "INVENTORY OF EXISTING THOROUGHFARES" + its name column "Thoroughfare," the Type
  plate band's umbrella label "THOROUGHFARE TYPES."

## 3. What was deliberately kept (Street/Road for families & standards)

- **All ten Type names** — Main Street, Village Street, Rural Road, Rural Highway, etc.
- **Family language** — "the Street and Road families," "Street family"/"Road family,"
  "a Street Type"/"a Road Type," **"Streets take precedence over Roads"** (§2 hierarchy),
  and the per-plate family label ("Street Types"/"Road Types") shown beside the umbrella.
- **The `Street:` and `Road:` definitions** themselves.
- **Driveway / entrance connection phrases** — *"A Driveway is not a Street or Road,"*
  *"access from a Street or Road,"* *"intersect the adjacent Street or Road"* (§2.d, §7,
  §8, `article-04`, the Driveway definition). A driveway *is* a Thoroughfare but is
  neither a Street nor a Road, so these phrases must stay to preserve meaning.
- **The 2018 Comprehensive Plan citation** *"Streets & Roads: Road Standards = Land Use
  Goals"* (a verbatim source title).

## 4. Deferred (optional internal cleanup — not user-facing)

To keep the build stable, internal identifiers were **not** renamed: the file names
`street-type-map.typ` / `street-type-inventory.typ`, the `build/street-types/` pipeline
directory, the `<!-- STREET-TYPE-EXHIBITS -->` split marker, build-script variables,
JSON keys, and `.typ` code comments. These are invisible in the deliverables; renaming
them is a cosmetic follow-up that would touch the build wiring + git history.

## 5. Deliverables

- `Newcastle CZC (Integrated Draft v0.15-draft).pdf` / `.md`
- `Article 3 Thoroughfares (Standalone v0.15-draft).pdf` / `.md`
- `Redline — Full CZC v0.15-draft vs v0.14-draft.pdf` — **isolates the term swap**
  (33 passages, balanced 1:1 line substitutions).
- `Redline — Full CZC v0.15-draft vs v0.1-baseline.pdf` — counts unchanged from v0.14
  (Article 3 is wholly new relative to baseline either way).

## 6. Verification

- **Parity & pagination:** the integrated body is still 121 pages at the same even
  offsets as v0.14 — the rename shifted no layout. The **standalone Article 3 is now
  27 pages** (was 29): its two recto-opening parity blanks were removed so the excerpt
  flows continuously, while chrome stays correct (each unit threads the true running
  page count, logical == physical). The bound integrated CZC keeps its recto openings.
- **Old title fully gone:** 0 occurrences of "Streets, Roads & Driveways" in either PDF
  (cover banner, TOC, headings, and chrome all read "Thoroughfares").
- **Visual spot-checks:** the Type plate band reads "Street Types ┊ THOROUGHFARE TYPES";
  Exhibit 3.2 "THOROUGHFARE TYPE MAP"; Exhibit 3.1 "INVENTORY OF EXISTING THOROUGHFARES."
- **Keeps confirmed:** every surviving "Street or Road" is a driveway/entrance
  connection or the family reference; the Comp Plan citation and all ten Type names are
  intact.
- **Regulation-neutral:** the vs-v0.14 redline shows only terminological substitutions.
