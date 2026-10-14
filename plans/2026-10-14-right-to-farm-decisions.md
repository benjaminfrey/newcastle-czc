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
no-primary-building, Art. 5 §2.c.2.b and §2.c.3.a — the spec's "§9" is a citation error, corrected 2026-10-14; storage and work-yard screening, Art. 5 §18): Commercial
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

## R27–R28 · The district use tables (spec §4, Article 2)

| # | Question | Decision |
|---|---|---|
| R27 | How Home/Personal Agriculture appears | **One row per tier** in the AGRICULTURAL category: Cultivation, Beekeeping, Small Stock, Medium Stock, Large Stock, each ○ where spec §3.3 allows that tier and blank elsewhere; plus **Farmstand** ○ in all thirteen (R19). Six new rows (63 → 69 uses) |
| R28 | Commercial Agriculture's statuses | **Unchanged**: ● in D1, D2, SD-Conservation, SD-Highway Commercial, SD-Rural Highway and SD-Campus |

## R29 · Small-stock housing and hives (spec §3.3, §3.6; Art. 5 Table 5.2)

Small-stock housing (coops, hutches) and hives are **permitted in every district notwithstanding
Table 5.2**. Where Table 5.2 reads "Not Permitted" or "n/a" (D6, SD-Campus, SD-Marine) they are
limited to **100 sq ft in total per lot**; elsewhere they count toward the Table 5.2 area as other
additional structures do. Accessory Building Placement setbacks and the §3 separations apply.

## R30–R35 · After the whole-branch review (2026-10-14)

The fresh-context review of the branch found that several approved values did not work together.
Ben Frey decided:

| # | Finding | Decision |
|---|---|---|
| R30 | F1: the dwelling distance, measured to the neighbor's lot line (spec §3.5 item 3), made the 120/220 ft lot-width gate unattainable with no relief | Measure **to the dwelling itself**. A dwelling built after the animal housing does not make that housing nonconforming |
| R31 | F2: "all Manure Storage 300 ft from a well" caught a backyard bedding pile and the owner's own well | The 300 ft rule applies only to **Manure Storage over 50 cubic yards**, measured from **a well on another lot, a public water supply, or a water body**. "Water body" goes to counsel to define |
| R32 | F3: pets read as stock; quail, pigeons and a seventh rabbit fit no tier | Agriculture **excludes household pets** (dogs, cats, animals kept indoors). Small Stock is **up to six small poultry birds** (hens, ducks, quail, pigeons; no roosters or drakes) **and up to six rabbits or similar small mammals**; a seventh of either makes Medium Stock |
| R33 | F4/F5: the §152-tied Commercial definition swallowed own-lot sales and let a resale yard claim the carve-outs | Commercial Agriculture is **production-based**: producing agricultural products on the lot for sale off the lot, wholesale, or processing. Own-lot sales stay Home/Personal (D7). Resale only as an accessory part of on-lot production; §3.j's carve-outs cover production areas only. The §152 tie leaves the definition (§3.h still cites §152 for the shield) |
| R34 | F6: Table 7.3 approval had no procedure; the safe harbour could disarm the Board | Table 7.3 approvals are **Special Permits under Article 8 Section 18**. The §3.h.3 safe harbour does not apply while the Board decides one |
| R35 | F9: the tiers withdrew the old "private, non-commercial agricultural uses permitted in every district" for new Medium Stock in D4–D6 and the districts mapped to D5, and new Large Stock in D3 | **Medium Stock by Special Permit** in D4, D5, D6, SD-Historic, SD-Highway Commercial, SD-Marine and SD-Fabrication; **Large Stock by Special Permit** in D3 (❷ in the use tables). **Disclose plainly in the Summary** |
