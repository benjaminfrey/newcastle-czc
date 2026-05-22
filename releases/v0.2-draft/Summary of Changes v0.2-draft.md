# Summary of Changes — v0.2-draft

**Release type:** First substantive draft. Inserts the new Article 3 "Streets, Roads & Driveways," renumbers existing Articles 4–9, updates cross-references throughout, and adds Article 3-related definitions to Article 9.

**Compares against:** [v0.1-baseline](../v0.1-baseline/) (markdown-faithful baseline transcription).

## Contents of this release

| File | Purpose |
|---|---|
| `Newcastle CZC (Integrated Draft v0.2-draft).pdf` | Full integrated CZC, 9 Articles, 107 pages (v0.1-baseline was 95 pages; v0.2 adds ~12 pages of new Article 3 content + minor net additions in cross-references and definitions). |
| `Newcastle CZC (Integrated Draft v0.2-draft).md` | Concatenated source — view this for human reading. |
| `Article 3 Streets Roads & Driveways (Standalone v0.2-draft).pdf` | Standalone Article 3 deliverable for focused review, 11 pages. |
| `Article 3 Streets Roads & Driveways (Standalone v0.2-draft).md` | Markdown source of Article 3. |
| `Summary of Changes v0.2-draft.md` | This file. |

For line-level redline, use `git diff v0.1-baseline HEAD -- source/` — the canonical change record is the git history between tags.

## What's new

### Article 3 — entirely new

A new **Article 3 "Streets, Roads & Driveways"** has been inserted immediately after Article 2 District Standards. The new article is ~11 pages and contains 14 sections (1–14). Major elements:

- **§1 General** — Purpose, Applicability, Authority, Compliance, Relationship to Other Standards. Includes the formal repeal clause for the Newcastle Road, Driveway, and Entrance Ordinance (RDEO), to be enacted concurrent with adoption.
- **§2 Street & Road Types** — Defines 8 Types organized in two families:
    - **Streets** (urban; pedestrian primacy): S-1 Main Street, S-2 Village Street, S-3 Neighborhood Street, S-4 Lane/Alley
    - **Roads** (rural; vehicle primacy): R-1 Connector Road, R-2 Rural Road, R-3 Highway Commercial, R-4 Rural Highway
    - Plus **Driveway (D)** as a distinct private-access category.
- **§3 Type Standards Table** — Full calibration matrix (Table 3.1) across 14 dimensions (right-of-way, cartway, lanes, parking, curb, planting, sidewalk, trees, design speed, block length, intersection radius, grade, sight distance, pavement spec).
- **§4 Ownership Categories** — Independent of Type. Four categories under 23 MRSA: Town Way, Public Easement, Private Road, State Highway.
- **§5 Classification of Existing Streets & Roads** — Inventory at adoption (placeholder Exhibit 3.1), 5-test classification rubric, Default Type by District (Table 3.4), reclassification process.
- **§6 New Streets & Roads** — Process for designing and building new streets, including Type assignment at design, Planning Board review for subdivisions, Town Way acceptance path.
- **§7 Driveways** — Driveway standards calibrated by District. Retains shared-driveway provision from RDEO §2.C.2.
- **§8 Entrances** — Sight distance (Table 3.2 retained from RDEO Table 1.1), intersection angle, location, curb radius. Retains MaineDOT §704 entrance-permit requirement for state highways.
- **§9 Intersections** — Calibrated by Type pair.
- **§10 Water Management** — Culverts (fish passage retained), ditches, grade changes. Retained from RDEO §2.E.
- **§11 Construction Standards** — Pavement and base course (Table 3.3 derived from RDEO Table 2.2, calibrated by Type).
- **§12 Coordination with Maine DOT** — Authority division (MaineDOT controls cartway; Town controls frontage/setbacks/access management), entrance permits, functional classification clarification.
- **§13 Administration** — Permit authority (CEO for driveways/entrances; Planning Board for new streets/roads and reclassification), inspections, fees, validity, appeals, waivers.
- **§14 Nonconforming Streets & Roads** — Continuation, substantial reconstruction, reclassification, Town Way acceptance of nonconforming Private Roads.

### Article 9 (renumbered) — Definitions Added

A new block of definitions has been appended to Article 9 Definitions, in connection with the adoption of Article 3. These are presented as a labeled section at the end of Article 9 (per the markdown source) and will be merged alphabetically with the existing entries at the next consolidation pass. New or modified entries include:

- **Modified:** Driveway (form-based test replaces the prior use-based test), Road Public (legacy term, redirects to Ownership Categories), Road Private (redefined as Ownership Category)
- **New (8 Type definitions):** Connector Road (R-1), Highway Commercial (R-3), Lane / Alley (S-4), Main Street (S-1), Neighborhood Street (S-3), Rural Highway (R-4), Rural Road (R-2), Village Street (S-2)
- **New (4 Ownership Categories):** Town Way, Public Easement, Private Road [refinement], State Highway
- **New (general):** Cartway, Curb Return Radius, Ownership Category, Planting Strip, Street, Street/Road Type, Thoroughfare, Travel Lane

## What's renumbered

Existing Articles 3 through 8 have been renumbered to Articles 4 through 9. The source file naming reflects the new numbering:

| Old | New |
|---|---|
| Article 3 Site Standards | Article 4 Site Standards |
| Article 4 Building Standards | Article 5 Building Standards |
| Article 5 Design Standards | Article 6 Design Standards |
| Article 6 Use Standards | Article 7 Use Standards |
| Article 7 Administration | Article 8 Administration |
| Article 8 Definitions | Article 9 Definitions |

The renumber affected ~22 canonical "Article N Name" references and ~64 bare "Article N" references throughout the code. All were updated mechanically via `sed` and verified by inventory comparison.

## Cross-reference updates (specific)

Per the implementation plan:

| Location (current numbering) | Change |
|---|---|
| Article 2 §2.C.1 | "Public Road or Private Road which conforms with the Newcastle Driveway, Road, and Entrance Ordinance" → "Street or Road of a Type defined in Article 3 Section 2" |
| Article 2 §2.C.4.b | "primary frontage along the Public or Private Road of greatest significance" → "primary frontage along the Street or Road of the highest Type per Article 3 Section 2 hierarchy" |
| Article 4 §2 Driveways | Full section replaced with cross-reference: "Driveways are regulated under Article 3 Section 7" |
| Article 4 §3.F Vehicular Access | "off-street parking accessed from an alley or secondary road" → "from a Lane/Alley (Type S-4 per Article 3 §2.G) or from a secondary frontage" |
| Article 8 §12 Subdivision §F.1.b | "The Newcastle Road, Driveway, and Entrance Ordinance" → "The standards of Article 3 Streets, Roads & Driveways" |
| Article 8 §13 Master Plan §A.2 | "mandatory compliance standards for blocks, shopfront streets, roads" → "blocks, Street and Road Types per Article 3" |
| Article 9 Definitions: Road, Public / Road, Private | Replaced "See Newcastle Road Ordinance" pointers with substantive definitions referencing Article 3 Section 4 Ownership Categories |

## Baseline corrections (collateral fixes)

The baseline CZC contained two clusters of erroneous cross-references that propagated through the mechanical renumber:

1. **Article 9 Definitions** — Eight definition entries originally referenced "Article 4 Use Standards" (incorrect: Use Standards was Article 6 in the baseline, not Article 4). After renumber these had become "Article 5 Use Standards." All eight have been corrected to **Article 7 Use Standards** (the correct new numbering for Use Standards). Affected entries: Auto-Oriented, Civic Use, Industrial, Lodging, Office, Residential, Retail, Unit.

2. **Baseline typos NOT corrected** in this draft (preserved for fidelity; flagged for future cleanup):
    - "Atricle 4 Section 17 Building Groups" (Article 7 Use Standards, Section 2.C.1.a; original baseline) — the spelling typo "Atricle" and the section-number mismatch are preserved. Building Groups is actually Section 18, not 17.
    - "Article 5.5 Architectural Components" (Article 5 Building Standards, Section 7.D.2; original baseline) — should be "Article 6.4 Architectural Components" in new numbering. The baseline cross-reference was internally inconsistent. Preserved as-is.
    - "Article 3 Section 3 Nonconforming Buildings" (referenced from SD-Highway Commercial and SD-Fabrication pages; original baseline) — was wrong in baseline (Nonconforming Buildings is in Article 5 Section 15, not Article 3 Section 3). After mechanical renumber these now read "Article 4 Section 3" which is still incorrect. Should be "Article 5 Section 15" in new numbering. Preserved as-is for v0.2; flagged for cleanup in v0.3.

## What is NOT in this release

- **RDEO repeal language as a separate document** — The repeal of the RDEO is referenced within Article 3 §1.A.6, intended to be enacted by the same Town Meeting that adopts the new Article 3. A separate repeal-and-amendment ordinance for the Town Meeting warrant has not yet been drafted.
- **Inventory of Existing Streets and Roads** — Article 3 §5 references an Inventory and an Exhibit 3.1 that will be produced during the Inventory Phase (per the implementation plan, Phase 3). The current Article 3 source contains the methodology but no actual inventory entries.
- **Cross-section graphics** — Each Type's cross-section illustration (e.g., a labeled drawing of a Main Street showing sidewalks, planting strip, parking, lanes) is called out in the style analysis as essential but has not yet been produced. Placeholder for `source/exhibits/cross-sections/*.svg`.
- **District-badge styling** — The colored badge + name banner used on Article 2 district pages is rendered with standard heading styles in this draft. A custom Typst show rule for district headings is deferred.
- **Per-Type Article-tab coloring** — All margin tabs render in Article blue. Coloring tabs by Type on new Article 3 pages is deferred.

## Verification performed

- All 9 articles render without pandoc or Typst errors
- Full integrated CZC concatenates to 107 pages
- Standalone Article 3 renders to 11 pages
- Cross-reference inventory after renumber confirms: zero remaining "Article 5 Use Standards" stragglers, zero remaining "Newcastle Road, Driveway, and Entrance Ordinance" references outside of Article 3's repeal clause
- All RDEO-superseding cross-references updated as specified in the implementation plan

## Notes on visual redline

A page-level visual diff (`diff-pdf`) was attempted against v0.1-baseline and produced a ~113 MB output, again dominated by page-shift artifacts caused by the v0.2 page count (107) exceeding v0.1's (95). The file was removed as before. **The authoritative content-level change record is the git diff between tags `v0.1-baseline` and `v0.2-draft`.**

To inspect changes:
```
git diff v0.1-baseline v0.2-draft -- source/
```

## Open questions for review

1. **Type colors** for use on the District Map are currently proposed in `style/czc-colors.yml` (S-1 deep red, S-2 burnt orange, R-2 forest teal, etc.). User review and lock-in needed before v0.3.
2. **Calibration values** in Table 3.1 are working defaults. Local engineering review (Road Commissioner, Planning Board) should validate before public review.
3. **Initial inventory scope** — Should the inventory at adoption cover named roads only (~60–100 segments) or include all unnamed driveways and lanes? Currently sized for named roads only.
4. **Maine DOT coordination** — Section 12 sets the authority division but does not yet contain a formal coordination MOU. To be developed if MaineDOT requests one.
