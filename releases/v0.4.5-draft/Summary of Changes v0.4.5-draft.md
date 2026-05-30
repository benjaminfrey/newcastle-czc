# Summary of Changes — v0.4.5-draft

**Release type:** Citation release on top of [v0.4.4-draft](../v0.4.4-draft/). Fills the two **Comprehensive Plan citation placeholders** that v0.4.4 carried forward — in **Article 3 §3.d** ("Basis for Right-of-Way Widths") and in the companion **justification memo §3.6** — with specific, page-cited policy references drawn from the Town's adopted **2018 Newcastle Comprehensive Plan**. **No regulatory standard, dimension, table value, ROW range, or page count changes.** This release only swaps a bracketed "[Drafter to insert…]" placeholder for real citations and reconciles two now-stale lines in the memo.

**Compares against:** [v0.4.4-draft](../v0.4.4-draft/).

**Why this release exists.** v0.4.4 added the §3.d basis note and shipped the companion memo, each carrying the placeholder *"[Drafter to insert the specific Comprehensive Plan policy citations here.]"* The adopted **2018 Comprehensive Plan** (188 pp., June 2018) was committed to the repository as a baseline (`docs/Newcastle Comprehensive Plan.pdf`) at the close of v0.4.4. This release reads that plan and fills both placeholders, so the §3.d note and the memo each stand on a cited policy basis and pre-empt the "where does the Plan say this?" question at hearing.

---

## 1. The citations added

The supporting policies sit almost entirely in the Plan's **Infrastructure: *Streets & Roads*** chapter (pp. 41–51), with the place-based growth chapters supplying the rural-character and land-efficiency hooks. They map nearly one-to-one onto the ROW reduction:

| Theme the ROW reduction serves | Comp Plan source (printed p.) | Policy language relied on |
|---|---|---|
| **A range of street types, not one uniform width** | *Road Standards = Land Use Goals* (p. 46) | Town's standards are "uniform and do not take into consideration whether the street is in a pedestrian-scaled neighborhood or … a rural conduit"; "new zoning will incorporate a **range of street types and standards** to accommodate local conditions and desired development goals" |
| **Right-sized infrastructure / lower lifecycle cost** | *Less road* (p. 43) | provide "the **right-sized infrastructure** for the community's needs"; road costs are "one of Newcastle's greatest financial challenges"; "adopt new road standards" and "**reduce its exposure to future costs**" |
| **Narrower streets are safer** | *Connectivity* (p. 44) | a connected network "enables individual streets to become **narrower, which then slows traffic and increases vehicular and pedestrian safety**" |
| **Walkability / on-street parking** | *Claim Main Street* (p. 74); *Modern Parking Standards* (p. 45) | streets "designed for a downtown Main Street condition, with a **design speed no greater than 20-25 mph**"; "**repurposing existing asphalt from too-wide travel lanes to create additional [on-street] parking**" |
| **Rural character / efficient use of land** | *Natural & Built Landscape* (p. 116); *Make Rural Work* (pp. 100–101) | "protection of **rural character**" is "an ongoing concern of citizens"; focus growth where "**infrastructure already exists** to support new growth" |

The Plan's **Regulatory Flowchart (p. 177)** designates the Character-Based Code as the implementing tool for these policies — i.e., this code is the Plan's named vehicle, and Article 3 is where the street-type policy lands.

## 2. Article 3 §3.d item 4 — before / after

**v0.4.4 (placeholder):**
> 4. These widths implement the policies of the Comprehensive Plan concerning village and rural character, walkability, and the efficient use of land and public investment. *[Drafter to insert the specific Comprehensive Plan policy citations here.]*

**v0.4.5 (filled):**
> 4. These widths implement the 2018 Newcastle Comprehensive Plan, which found the Town's street standards "uniform" and directed that "new zoning will incorporate a range of street types and standards to accommodate local conditions and desired development goals" (*Streets & Roads: Road Standards = Land Use Goals*, p. 46). The calibrated rights-of-way further the Plan's call for "right-sized infrastructure" that reduces the Town's exposure to future road costs (*Less road*, p. 43), its observation that allowing "individual streets to become narrower … slows traffic and increases vehicular and pedestrian safety" (*Connectivity*, p. 44), and its policies for a walkable, pedestrian-scaled Main Street and village center (*Claim Main Street*, pp. 73–74) and for the protection of rural character (*Natural & Built Landscape*, p. 116).

This is the **only** change to the code text; it renders on **integrated p. 29** (standalone p. 3).

## 3. Companion memo updates (`memos/…Justification Memo.md` + `.pdf`)

- **§3.6 "Narrower ROW advances Town and State policy"** — the *Comprehensive Plan* bullet's placeholder is replaced with a five-point, quoted, page-cited list (the same sources as the table above, plus *Modern Parking Standards* for the S-2 parking calibration), closing with the Regulatory-Flowchart point and a verify-before-hearing caveat.
- **§7.4 "Recommended next steps"** — item 4 changed from *"Cite the specific Comprehensive Plan policies … (fill the … placeholder)"* to *"Confirm the Comprehensive Plan citations now incorporated in §3.6 above and in Article 3 §3.d against the adopted June 2018 plan text before relying on them at hearing"* (the task is now done; what remains is verification).
- **Status line** — corrected the two now-false clauses (it said no code change had been written and that "v0.4.3 still carries the existing 50-foot figures"). It now records that the Moderate option was written into the draft at v0.4.4 and the Comp Plan citations are now filled, while preserving that the memo is still an unadopted discussion draft open to Board revision.

The memo's **FROM line remains blank** and it remains a discussion draft — "memo finalization" is a separate carried-forward item, not this release.

## 4. What did NOT change

- **No dimensional or regulatory standard.** No ROW range, travel-lane width, parking/planting/sidewalk cell, sight distance, intersection geometry, or construction spec is touched. The §3.d *substance* (items 1–3) is unchanged; only the citation in item 4 is filled.
- **No new nonconformity.** Nothing in this release alters any minimum.
- **Page counts hold:** integrated **91 pp** (same 4 blank pads at verso 36/58/68/84; footers continuous 1 → 91), standalone Article 3 **9 pp**. The expanded §3.d item 4 (1 line → ~6 lines) absorbs within Article 3's existing 9-page block; no Article repaginated. The memo grew **7 → 8 pp**.

## 5. Files changed

- `source/article-03-streets-roads-driveways.md` — §3.d item 4: placeholder → five cited Comp Plan policies.
- `memos/Right-of-Way Width Reduction — Justification Memo.md` (+ `.pdf` rebuilt) — §3.6 citations filled; §7.4 and Status line reconciled.
- `style/style-analysis.md` — new **§18** recording the citation fill (no template/layout change).
- `releases/v0.4.5-draft/` — integrated (91 pp) + standalone Article 3 (9 pp), both `.md`/`.pdf`; this Summary; and a 2-page redline of the one changed integrated page (p. 29–30) vs v0.4.4.

**Articles 1–2 and 4–9: no change.** The citation lives only in Article 3 §3.d; nothing else references it.

## 6. Verification

- **Citations render** (whitespace-normalized confirmation, standalone + integrated): "2018 Newcastle Comprehensive Plan", "range of street types and standards", "Road Standards = Land Use Goals", "p. 46", "right-sized infrastructure", "Less road", "slows traffic and increases vehicular and pedestrian safety", "Connectivity", "Claim Main Street", "73", "Natural & Built Landscape", "p. 116" — all present.
- **Page geometry** unchanged: integrated 91 pp, standalone 9 pp, §3.d on integrated p. 29 / standalone p. 3.
- **Memo PDF rebuilt** (Typst 0.14.2, letter, 8 pp); new §3.6 content, §7.4 revision, and corrected Status line all confirmed present.
- **Footer version** reads "Draft v0.4.5-draft" on both deliverables (set at build time).
- **Page references are to the adopted June 2018 plan** and are flagged in both the code note and the memo for confirmation against the primary source before reliance at a public hearing.

## 7. What's still off (carry forward)

1. **Memo finalization** — blank FROM line; still a discussion draft, not adopted or folded into the code beyond the §3.d note.
2. **Stale table numbers from the Article renumbering (DEFERRED).** Art. 4 tables still read "3.x" (colliding with Article 3), Art. 5 "4.x", Art. 6 "5.x", Art. 8 "7.x". The new Article 3's own tables (3.1a/3.1b/3.2/3.3/3.4) are correct.
3. **Cross-section graphics — 10 needed.** One annotated cross-section per Type still unproduced.
4. **Front matter (cover + TOC)** still absent, so Articles open on recto rather than the baseline's verso.
5. **District-page banner styling**, **use-table status glyphs** (`❶ ❷ ✪` need a fallback font), and **R-2 maximum grade (12%) vs. RDEO's 10%** — all carried unchanged from v0.4.4.
