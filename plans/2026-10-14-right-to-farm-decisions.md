# Right to Farm — decisions taken for the implementation plans

Decided by Ben Frey (Planning Board chair) in chat on 2026-10-14, against the approved spec
`specs/2026-10-07-right-to-farm-design.md`. These fill values the spec left open; they are draft
values for the Board's review, not Board rulings. Questions only counsel can answer stay in spec §7.

## R1–R4 · The fifth use-table status (spec §3.2, §5.3; Wave 4c / P15)

| # | Value | Decision |
|---|---|---|
| R1 | Legend symbol | **○** (U+25CB WHITE CIRCLE), Apple Symbols, as ● is |
| R2 | Legend row | **"No Permit Required"**; Permitting Authority column **"—"** |
| R3 | Note | "Note: Uses without ●, ❶, ❷, ✪, or ○ are not allowed in this District. Uses marked ○ require no permit but must meet the standards of Article 7 Section 3." |
| R4 | Data code | **`br`** |

Co-occurrence with another code in one cell stays **illegal (build error)**, per decision D3 of
`specs/2026-10-07-release-deliverables-scope.md`.

## R5 · Release shape (spec §3.2)

D3's "ships separately" means **its own change, same release**: the status code lands as its own
reviewed change (Plan A) before the ordinance data, and both ship together in **v1.2-draft**.

## R6–R8 · Animals (spec §3.3)

| # | Question | Decision |
|---|---|---|
| R6 | A flock over six birds | Is **medium stock**: medium-tier districts, separations and lot-width gate |
| R7 | Roosters, drakes, turkeys, geese, guinea fowl | **Medium stock** |
| R8 | Head-count cap on medium and large stock | **None**; separation and the lot-width gate do the work |

## R9–R12 · Separation and placement (spec §3.5)

| # | Question | Decision |
|---|---|---|
| R9 | Pens, runs, paddocks, pasture | **Pens, runs and paddocks** take their tier's housing distance from a property line; **open pasture and grazing take none** |
| R10 | Front | Animal housing and manure storage meet the district's **Accessory Building Placement front setback**, and may not sit **forward of the primary building's front façade**, except in D1 and the districts mapped to it |
| R11 | Reduced separation below the lot-width gate | Planning Board may reduce to **no less than half** the table distances, on finding: (1) no dwelling on another lot lies within the full table distance, or its owner consents in writing; (2) screening or topography mitigates; (3) a manure management plan is in place |
| R12 | Nuisance Standards (§1.h) | Apply to **every tier**, with the §3.7.3 **safe harbour**: an activity meeting §3's numeric standards is not a violation |

## R13–R16 · Buildings (spec §3.6)

| # | Question | Decision |
|---|---|---|
| R13 | Agricultural Building column, D2–D5 | **Floor area governs**: CEO up to the §3.4 threshold (D2 5,000 sf · D3 3,000 sf · D4 and D5 2,000 sf), Planning Board above; width and depth "-"; 2 stories; first floor 16 ft; upper floor 10 ft. Districts mapped to D5 (SD-Historic, SD-Fabrication, SD-Highway Commercial) take D5's column; SD-Rural Highway, mapped to D1, takes D1's uncapped column |
| R14 | D6 | **No Agricultural Building column.** Farm buildings use the existing Commercial Accessory column (Planning Board); coops, hives and seasonal structures need no building |
| R15 | SD-Conservation, SD-Campus, SD-Marine (no matrix) | §3 states each **follows the envelope of its mapped district**: SD-Conservation as D1 (uncapped), SD-Campus as D2 (5,000 sf), SD-Marine as D5 (2,000 sf). No new matrices |
| R16 | Seasonal and unenclosed structures | Exempt from the additional-structure cap and the 3-month rule. **No size limit in D1, D2 and their mapped districts**; in D3–D6 and the districts mapped to D5, total footprint is capped at the district's agricultural-building threshold (3,000 sf D3; 2,000 sf D4–D6), Planning Board above. District accessory setbacks apply everywhere |

## R17 · Carve-outs (spec §3.9)

**Split by carve-out.** Fence materials and crossing (Art. 4 §8): any tier, only for fencing that
encloses the agricultural area itself. The other four (field review, Art. 4 §7; accessory cap and
no-primary-building, Art. 5 §9; storage and work-yard screening, Art. 5 §18): Commercial
Agriculture, or medium or large stock, or at least ½ acre in cultivation. A co-located
non-agricultural business gets no benefit from any of them.

## R18–R21 · Board routes and uses (spec §3.4, §4)

| # | Question | Decision |
|---|---|---|
| R18 | CEO referral to the Board (district pages D2–D6; Art. 8 §§10.c.3, 11.c.3) | **Displaced by §3** for any agricultural activity or building within §3's by-right limits, Home/Personal or Commercial. The referral text stays; §3 overrides it |
| R19 | Farmstand (§26) | **○ (`br`) in all thirteen districts** |
| R20 | Stables (§62) | **Split by activity**: keeping one's own horses is large stock; boarding others' horses, lessons, shows and events are §62, keeping its current statuses. The equine sentence of the Agricultural Use definition moves to §62 |
| R21 | Seasonal farm-worker housing | **Out of scope**; named in the Summary as a planned follow-up |

## R22–R25 · Operation (spec §3.7, §4)

| # | Question | Decision |
|---|---|---|
| R22 | Lighting (Art. 4 §12) | Add to §12.b's exemptions: **agricultural task lighting used only while work is underway**. Permanent fixtures still meet shielding and colour temperature; §12.c.10 stays |
| R23 | Outdoor storage (§46) and screening (Art. 4 §5.b.2) | **Active-use carve-out**: equipment, vehicles and materials in active agricultural use on the lot are not Outdoor Storage, and §5.b.2 does not apply to agriculture meeting §3. Unused or inoperable equipment remains storage |
| R24 | BMP conformance | The operator bears the burden; a written **§156 determination by the Commissioner** is the showing. When conformance is disputed the CEO requests one from DACF, and enforcement on that question waits for the answer. **For counsel** |
| R25 | Farm/Vendor Market (§25) | **Statuses unchanged** |

## R26 · Stock classes (spec §3.1, §3.3)

Alpacas, miniature horses and miniature donkeys are **medium stock**; standard donkeys and mules are
**large**, with horses. Each class is drafted as a list plus "other animals of similar size".

## Not decided here

Counsel's questions in spec §7 stand, including 7 M.R.S. §219-D (small stock in every district),
§§293/296 (no permit for cultivation), §154's reach, and the §155 clock. The drafting follows the
spec's working assumption on each. The §3.4 thresholds are the spec's starting numbers for the Board.
