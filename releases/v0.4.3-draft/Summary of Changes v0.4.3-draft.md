# Summary of Changes — v0.4.3-draft

**Release type:** Content release on top of [v0.4.2-draft](../v0.4.2-draft/). The form-based Street/Road typology grows from **8 Types to 10**: a new **S-4 Lane** (narrow fronting street) split out from the old combined "Lane/Alley," and a new **R-3 Rural Lane** (rural yield roadway). The previously-researched **held findings** (S-1 Main Street right-of-way widened; the "cartway" row relabelled to separate moving lanes from parking) are applied in the same pass, and the master Type Standards matrix is split into **Table 3.1a (Streets)** and **Table 3.1b (Roads)** to stay legible at ten Types. **No regulatory standards were lost** — every value from the prior 8-Type matrix is preserved or intentionally calibrated.

**Compares against:** [v0.4.2-draft](../v0.4.2-draft/) and the baseline [docs/Newcastle Core Zoning Code.pdf](../../docs/) + [docs/Newcastle Roads Driveways and Entrances Ordinance.pdf](../../docs/).

**Why this release exists.** In review the Town confirmed two gaps in the 8-Type system:
1. **A rural yield roadway is missing.** Newcastle has many low-volume rural ways — including historic two-rod (33 ft) rights-of-way — that are narrower than the R-2 Rural Road's standard pavement and operate as two-way single-lane roads with passing pull-outs. The 8-Type matrix forced these into R-2, overstating their required width.
2. **A narrow urban street is missing.** Between the Neighborhood Street (S-3) and the service Alley sits a real type: a small fronting street with a smaller right-of-way — two narrow travel lanes, maybe a sidewalk on one side — that interconnects off neighborhood/village streets and "punches in" to the back of road-facing parcels to reach mid-block land. The old "S-4 Lane/Alley" conflated this fronting street with the rear service alley.

---

## 1. Two new Types (8 → 10)

### S-4 Lane (new) — split from the former "S-4 Lane/Alley"

The old combined Type tried to cover both a *fronting* slow street and a *service* rear lane. These are now distinct:

- **S-4 Lane** — a narrow **fronting** street; buildings front on it. Small, interconnected, slow (design speed 15 mph), with two narrow travel lanes and an optional one-side sidewalk. It connects to other Street Types or "punches in" to reach the interior of a block. Target districts: internal to blocks in D2/D3/D4/D5, with mid-block segments in the village districts.
- **S-5 Alley** — the **service** rear lane (the old combined Type's standards live here). Buildings do **not** front on it; it carries parking, loading, accessory-building access, and utility easements. Remains the only allowed rear-lot vehicular access type in D6.

Design basis: SmartCode's distinction between a *Lane* (a slow-movement fronting thoroughfare) and a *Rear Lane / Alley* (service), and NACTO's narrow yield-street geometry (a <15 ft travel area operates as a two-way single lane).

### R-3 Rural Lane (new) — rural yield roadway

A lower-volume rural Road Type inserted between R-2 Rural Road and the highway Types:

- For rural ways carrying **ADT ≤ 400**. Where the traveled way is **15 ft or narrower it functions as a two-way single-lane roadway**, with **passing pull-outs** (sized for two vehicles to pass and for fire-apparatus deployment) at intervals of **no more than 300 ft**. Gravel surface acceptable; drainage by open ditch; no curb.
- Gives the Town a **conforming designation for existing narrow rural ways**, including historic **two-rod (33 ft)** rights-of-way that cannot meet the R-2 standard pavement width.

Design basis: AASHTO's Very Low-Volume Local Roads guidance (ADT ≤ 400) and the FHWA/Maine *Rural Design Guide* yield-roadway model — less-restrictive width/lane criteria are justified at these volumes without a crash penalty.

> **R-2 Rural Road stays clean.** R-2 remains the *standard* rural Road at a 50 ft ROW; its description was softened from "the most rural Type" to "the standard rural Road Type… the Rural Lane (R-3) is a lower-volume variant for narrower rural ways." This is how the new R-3 resolves the earlier open question of whether R-2 needed a narrow-ROW sub-case — it does not; the narrow case is now its own Type.

## 2. Type-code renumbering (highway Types shift down one)

Inserting R-3 Rural Lane pushed the two highway Types down a number. Every code reference and the §2 description-letter scheme were updated to match:

| Type | v0.4.2 code | v0.4.3 code |
|---|---|---|
| Highway Commercial | R-3 | **R-4** |
| Rural Highway | R-4 | **R-5** |

The Street family also gained a member, so the family count notation changed everywhere: **"S-1 through S-4" → "S-1 through S-5"** and **"R-1 through R-4" → "R-1 through R-5"** (the pedestrian-weighting paragraph in §2.c.3 keeps a deliberate "S-1 through S-4 primary / S-5 secondary" sub-grouping). The §2 Type descriptions now run **d (Main Street) through n (Driveway)**.

## 3. Table 3.1 split into 3.1a (Streets) + 3.1b (Roads)

Ten Types do not fit one legible full-width matrix. The single Type Standards Table was split by family:

- **TABLE 3.1a STREET TYPE STANDARDS** — columns S-1 Main St., S-2 Village St., S-3 Neighborhood St., S-4 Lane, S-5 Alley.
- **TABLE 3.1b ROAD TYPE STANDARDS** — columns R-1 Connector, R-2 Rural Road, R-3 Rural Lane, R-4 Hwy Commercial, R-5 Rural Highway.

Both are full-width bottom-floats (the established Typst pattern), at 8 pt with tighter cell insets so six columns fit the text block. **Tables 3.2, 3.3, and 3.4 keep their numbers**, so none of the "see Table 3.2 / 3.3" cross-references had to move. §3.c.1 now reads "…described by the standards in Table 3.1a (Street Type Standards), and each Road Type by the standards in Table 3.1b (Road Type Standards)."

### Calibration of the two new Types (new columns added to the split tables)

| Standard | **S-4 Lane** (new) | **R-3 Rural Lane** (new) |
|---|---|---|
| Right-of-Way width | 30–40 ft | 33–50 ft |
| Traveled way (moving lanes) | 16–20 ft | 12–18 ft |
| Travel lanes | 2 @ 8–10 ft | 1 shared, or 2 @ 8–9 ft |
| On-street parking lane | 7–8 ft optional, one side | none |
| Curb type | rolled or none | none (shoulder + ditch) |
| Planting strip width | optional | none |
| Sidewalk | one side, 5 ft, optional | none |
| Street trees | encouraged | permitted |
| Design speed | 15 mph | 15–25 mph |
| Maximum block length | n/a | n/a |
| Curb return radius | 10–15 ft | 15–25 ft |
| Maximum grade | 10% | 12% |
| Surface | paved | gravel acceptable |
| Minimum sight distance | per Table 3.2 | per Table 3.2 |
| Pavement specification | per Table 3.3 | per Table 3.3 |

(S-5 Alley carries the former combined-Type values: 16–20 ft ROW, 12–16 ft traveled way, no parking/curb/planting/sidewalk, 10–15 mph, 5–10 ft curb return, 10% grade, paved.)

## 4. Held findings applied (from the prior research pass)

Two improvements identified earlier and explicitly held for integration are applied here:

- **S-1 Main Street right-of-way widened to 66–80 ft** (was a single narrower figure). A true main street needs room for two parking lanes, two wide sidewalks, street trees, and travel lanes; 66–80 ft matches the built D6 condition and standard main-street practice.
- **"Cartway" row relabelled.** The matrix row that previously blended moving lanes and parking is now **"Traveled way (moving lanes)"** with a separate **"On-street parking lane (each side)"** row. This removes a long-standing ambiguity — readers can no longer mistake a parking-inclusive width for the moving-lane width. The new "On-Street Parking Lane" definition (Art. 9) states the parking lane is counted separately from the traveled way in Tables 3.1a/3.1b.

## 5. Definition changes (Article 9)

- **Added — Lane (S-4):** narrow fronting slow-movement street; "punch in" language; §2.G.
- **Added — Alley (S-5):** narrow service street, buildings do not front on it; notes it was formerly combined with the Lane as "S-4 Lane/Alley"; §2.H.
- **Added — Rural Lane (R-3):** rural yield roadway, ADT ≤ 400, two-way single-lane where ≤ 15 ft, two-rod (33 ft) ways; §2.K.
- **Added — On-Street Parking Lane:** typically 7–8 ft per side; counted separately from the traveled way in Tables 3.1a/3.1b.
- **Modified — Rural Road (R-2):** softened to "a rural Road Type … narrowest *standard* pavement"; section ref 2.I → 2.J.
- **Modified — Street / Thoroughfare:** "S-4 Lane/Alley" → "S-4 Lane, S-5 Alley"; Thoroughfare now "all **ten** Street/Road Types (S-1 through S-5 and R-1 through R-5)."
- **Renumbered — highway defs:** Highway Commercial (R-3 → R-4, §2.J → 2.L); Rural Highway (R-4 → R-5, §2.K → 2.M); Connector Road §2.H → 2.I.

## 6. Cross-reference updates in other Articles

- **Article 4 (Site Standards) §3.f.1** — vehicular access to off-street parking now reads "from a **Lane or Alley (Types S-4 or S-5** per Article 3 Section 2.G–H)" (was "Lane/Alley (Type S-4)").
- **Article 2 and Articles 5–8** — **no change required.** They reference Special-District *names* (e.g., "SD-Highway Commercial") and district names, not Type *codes*, so the renumbering does not touch them. (Confirmed by a full grep sweep.)

## 7. Files changed

- `source/article-03-streets-roads-driveways.md` — split Lane/Alley into S-4 Lane + S-5 Alley; inserted R-3 Rural Lane; renumbered highway Types R-3/R-4 → R-4/R-5 throughout §§2–12; restructured §2 descriptions to letters d–n; split Table 3.1 into full-width bottom-float Tables 3.1a + 3.1b; applied the S-1 ROW (66–80 ft) and traveled-way/parking relabel; updated Tables 3.3 (header) and 3.4 (Default Type by District) for the new Types.
- `source/article-09-definitions.md` — four new entries (Lane S-4, Alley S-5, Rural Lane R-3, On-Street Parking Lane); softened Rural Road (R-2); renumbered highway/connector defs; updated Street and Thoroughfare.
- `source/article-04-site-standards.md` — parking-access reference updated to Types S-4 / S-5.
- `style/style-analysis.md` — new **§16** documenting the two new Types, the code renumbering, the Table 3.1 split, the applied held findings, and the new page count.

## 8. Page count comparison

| | v0.4.2-draft | v0.4.3-draft |
|---|---|---|
| Full integrated CZC | 90 (4 blank pads: 36, 58, 68, 84) | **91** (same 4 blank pads) |
| Standalone Article 3 | 9 | **9** |

The **+1 page is Article 9 (Definitions)** growing from 6 to 7 pages to hold the four new/expanded entries — **not** Article 3, which absorbs both new Types and the split table within its existing 9-page (+1 pad) block. The 4 blank pads are unchanged at verso pages 36, 58, 68, 84; footers remain continuous **1 → 91**; Articles 1–8 paginate identically to v0.4.2.

## 9. Verification

- **No stale Type codes.** Grep across `source/` finds no surviving "R-3 (Highway Commercial)", "R-4 (Rural Highway)", "R-3 and/or R-4" (old highway pairing), "eight Street/Road Types", or "R-1 through R-4". The lone "S-1 through S-4" and "Lane/Alley" hits are intentional (the pedestrian sub-grouping and a historical note in the Alley definition).
- **New Types resolve everywhere.** Rural Lane (R-3), Highway Commercial (R-4), and Rural Highway (R-5) appear consistently in both `article-03` and `article-09`.
- **§2 descriptions run d–n** sequentially; both new definitions (Lane S-4, Alley S-5) present in Article 9.
- **Tables render.** TABLE 3.1a STREET TYPE STANDARDS on integrated **p. 29** (5 Type columns S-1…S-5); TABLE 3.1b ROAD TYPE STANDARDS on **p. 30** (5 Type columns R-1…R-5, including the new R-3 Rural Lane). No `\@` escape leak; the `@` glyph in lane specs (`2@10`) renders.
- **Pagination intact.** Integrated 91 pages; 4 blank pads at 36/58/68/84; footer numbers match physical pages on every non-pad page (continuous 1 → 91). Standalone Article 3 = 9 pages.
- **Footer version** reads "Draft v0.4.3-draft" on both deliverables (set at build time by the version argument).

## 10. What's still off (carry forward)

1. **Stale table numbers from the Article renumbering (still DEFERRED).** Art. 4 (Site Standards) tables still read "3.x" (and collide with the new Article 3); Art. 5 reads "4.x"; Art. 6 reads "5.x"; Art. 8 reads "7.x". The new Article 3's own tables (3.1a, 3.1b, 3.2, 3.3, 3.4) are correct. Fixing requires renumbering ~35 captions plus every in-text cross-reference; deferred to its own pass.
2. **Cross-section graphics — now 10, not 8.** One annotated cross-section per Type is still unproduced, and the count rose with the two new Types. Slightly more relevant now that S-4 Lane and R-3 Rural Lane are new and unfamiliar.
3. **Front matter (cover + TOC).** Still absent, so Articles open on recto (vs. the baseline's verso). Adding a cover + TOC is the proper fix and will restore verso openers.
4. **District-page banner styling** — colored badge ("D1") + name banner ("RURAL") still render as standard headings, not the baseline's full-width colored block.
5. **Use-table status glyphs** `●` `❶` `❷` `✪` — `●` renders; the enclosed numerals/star still need a symbol fallback font.
6. **R-2 maximum grade (12%) vs. RDEO's 10%** — a deliberate-but-unreconciled value carried since the original Article 3 draft; flagged for a future engineering-standards reconciliation.
