# Summary of Changes — v0.4.4-draft

**Release type:** Calibration release on top of [v0.4.3-draft](../v0.4.3-draft/). Reduces the **right-of-way (ROW) minimums** for the four Street/Road Types that previously carried a **fixed 50-foot ROW**, converting each to a calibrated range with a **40-foot floor**; refines three S-2 / S-4 component requirements at the Town's direction; and adds a new **Article 3 §3.d "Basis for Right-of-Way Widths"** note. **No travel-lane, sight-distance, intersection, or construction standard is changed** — the reduction comes entirely out of the unallocated margin between the built cross-section and the ROW line.

**Compares against:** [v0.4.3-draft](../v0.4.3-draft/) and the baseline [docs/Newcastle Core Zoning Code.pdf](../../docs/) + [docs/Newcastle Roads Driveways and Entrances Ordinance.pdf](../../docs/).

**Why this release exists.** Planning Board experience administering the code showed the fixed 50-foot ROW is wider than these contexts require for most applications — taking land from buildable/taxable parcels, adding impervious surface, and committing the Town to pavement and drainage it must maintain in perpetuity, without a corresponding safety or function benefit. The full justification — the rod-survey origin of the "50-foot" figure, the absence of any Maine statutory ROW minimum (30-A MRSA §4404), the component-by-component cross-section math, and the safety case for narrower local streets — is set out in the companion memo [`memos/Right-of-Way Width Reduction — Justification Memo.md`](../../memos/). This release implements that memo's recommended **Moderate** posture.

---

## 1. Right-of-way minimums reduced (fixed 50 ft → ranges with a 40 ft floor)

| Type | v0.4.3 ROW | **v0.4.4 ROW** | Change to required minimum |
|---|:---:|:---:|:---:|
| S-2 Village Street | 50 ft (fixed) | **40–54 ft** | −10 ft floor (+4 ft ceiling) |
| S-3 Neighborhood Street | 50 ft (fixed) | **40–46 ft** | −10 ft floor |
| R-1 Connector Road | 50 ft (fixed) | **40–50 ft** | −10 ft floor |
| R-2 Rural Road | 50 ft (fixed) | **40–50 ft** | −10 ft floor |
| S-1, S-4, S-5, R-3 | (already ranges) | unchanged | — |
| R-4, R-5 | per MaineDOT | unchanged | — |

**Why a 40-foot floor.** It still holds a complete cross-section (e.g., 20 ft travel + planting + sidewalk + utility/snow/grading on an urban section, or 20 ft travel + shoulders + two full ditches on a rural one); it sits between the historic 2-rod (33 ft) and 3-rod (49.5 ft) survey widths, keeping the table rooted in the same New England rod tradition it already uses; and it is a round, administrable number applied without case-by-case derivation. 50 ft becomes an available *ceiling* rather than a *mandate*.

## 2. S-2 Village Street component refinements (Town direction)

| Standard | v0.4.3 | **v0.4.4** |
|---|---|---|
| On-street parking lane | 7–8 ft, optional both sides | **7–8 ft, one side** (required; second side optional) |
| Planting strip | 5 ft min, one side | **optional, both sides** |

A Village Street now always carries a parking lane on at least one side — the feature that justifies its 54-ft ceiling — while the planting strip becomes a flexible, optional element. The §2.e prose was reconciled to match: the **Description** ("optional on-street parking" → "on-street parking on at least one side") and the **Character** clause (now: parking required on at least one side, may be on both; planting strips optional on either or both sides).

## 3. S-4 Lane — sidewalk now required

| Standard | v0.4.3 | **v0.4.4** |
|---|---|---|
| Sidewalk | one side, 5 ft, optional | **one side, 5 ft min** (required) |

The Lane's ROW (30–40 ft) easily absorbs a required 5-ft walk (the 30-ft floor leaves ~9 ft of margin after a 16-ft travel surface + 5-ft walk). The change makes S-4 a true *walkable* lane and sharpens the **S-4 vs. S-5 distinction**: a **Lane carries a sidewalk; an Alley has none.** The §2.g prose was reconciled accordingly (Description and Character both now state the sidewalk is required; the Lane/Alley contrast now turns on the sidewalk).

## 4. Resolves the S-2 cross-section overflow (held finding)

The v0.4.3 cross-section audit flagged that S-2's *maximum* optional build — on-street parking on both sides at full width — reached **~51 ft, exceeding its fixed 50-ft ROW.** The new **40–54 ft** range resolves the inconsistency from both ends: the 54-ft ceiling clears the full-parking build, while the 40-ft floor comfortably carries the typical build (parking one side, walks both sides, ~38 ft). This was the one Type whose *maximum* build overran its own ROW; it no longer does.

## 5. New §3.d "Basis for Right-of-Way Widths"

A short explanatory note added to Article 3 §3 (after GENERAL), so the ranges carry their own rationale in the code and pre-empt the "why not 50?" question at hearing:

1. ROW is **calibrated to the cross-section** each Type carries — traveled way, parking, planting, sidewalks, shoulders, drainage — plus a margin for snow storage, dry utilities, and grading; not a single uniform width.
2. The widths remain rooted in the **New England rod** (S-1 = 4 rods / 66 ft; the historic town-road width = 3 rods / 49.5 ft; narrow ways descend to the 2-rod / 33 ft minimum); the ranges decline to default to the 3-rod width where the cross-section does not require it.
3. **No Maine statute prescribes a minimum ROW width**; 30-A MRSA §4404 requires only that a subdivision not cause unreasonable congestion or unsafe conditions. Widths are set under the Town's home-rule authority (§1.C), and the safety-critical dimensions — traveled way, sight distance (§8), intersection geometry (§9) — are fixed independently of the ROW range.
4. Implements the Comprehensive Plan, with a **bracketed drafter placeholder** for the specific policy citations (mirrors the placeholder in the companion memo).

## 6. What did NOT change (safety floors retained)

- **Traveled-way widths unchanged.** S-2 / S-3 / R-1 keep their 20-ft travel ways, which meet the **20-ft minimum fire-apparatus access width** (International Fire Code §503).
- **Planting strips, shoulders, rural ditches** all retained; R-1 and R-2 keep full open-drainage sections within the 40-ft floor.
- **Sight distance (Table 3.2) and intersection geometry (§9)** unchanged.
- **No existing road becomes nonconforming.** Reducing a *minimum* never creates nonconformity; roads at 50 ft or wider remain fully conforming, governed by §14 as before.

## 7. Files changed

- `source/article-03-streets-roads-driveways.md` — Table 3.1a: S-2 ROW (50 → 40–54), S-3 ROW (50 → 40–46), S-2 parking (optional both → one side), S-2 planting (5 ft one side → optional both), S-4 sidewalk (optional → required, one side 5 ft min); Table 3.1b: R-1 and R-2 ROW (50 → 40–50); §2.e (S-2) and §2.g (S-4) description/character prose reconciled; new **§3.d Basis for Right-of-Way Widths**.
- `memos/Right-of-Way Width Reduction — Justification Memo.md` (+ `.pdf`) — companion justification memo added to the repository (discussion draft; carries FROM-line and Comp Plan placeholders).
- `style/style-analysis.md` — new **§17** documenting the ROW reductions, the S-2/S-4 component changes, the §3.d note, and the held S-2 finding resolved.

**Article 9 (Definitions): no change.** No Type name or code changed; the Type definitions point to Article 3 for standards, so the reduced widths flow through automatically. No cross-reference in Articles 1–2 or 4–9 names a ROW figure, so none required editing (confirmed by grep).

## 8. Page count comparison

| | v0.4.3-draft | v0.4.4-draft |
|---|---|---|
| Full integrated CZC | 91 (4 blank pads: 36, 58, 68, 84) | **91** (same 4 blank pads) |
| Standalone Article 3 | 9 | **9** |

The new §3.d note (~5 lines) and the prose reconciliations absorb within Article 3's existing 9-page (+1 pad) block; no Article repaginated. Pads stay at verso pages 36, 58, 68, 84; footers remain continuous **1 → 91**.

## 9. Verification

- **Table values render.** Standalone/integrated Tables 3.1a/3.1b show S-2 **40–54**, S-3 **40–46**, R-1 **40–50**, R-2 **40–50**; S-2 parking **"7–8 ft, one side"**; S-2 planting **"optional, both sides"**; S-4 and S-3 sidewalk both **"one side 5 ft min"**.
- **§3.d Basis note renders** with the four/three/two-rod figures, "§4404", the home-rule clause, and the Comp Plan placeholder.
- **Prose reconciled** (whitespace-normalized confirmation): S-2 "On-street parking is required on at least one side and may be permitted on both sides"; "Planting strips are optional on a Village Street"; S-4 "a Lane carries a sidewalk, while an Alley provides only rear or side service access with no sidewalk".
- **No stale fixed-50 ROW.** The remaining "50" figures are all legitimate: S-2 maximum block length **500 ft**, R-3 ROW **33–50 ft**, and the §14 dead-end continuation **50 ft easement**.
- **Glyphs.** `@` in lane specs renders (8 occurrences across both tables); `§` renders. Page count 91; footers 1 → 91; standalone Article 3 = 9 pages.
- **Footer version** reads "Draft v0.4.4-draft" on both deliverables (set at build time).

## 10. What's still off (carry forward)

1. **Comprehensive Plan citations** — the §3.d placeholder and the memo's §3.6 placeholder both still need the specific Comp Plan policy references filled in.
2. **Memo finalization** — the companion memo is a discussion draft with a blank FROM line; it has not been adopted or folded into the code beyond the §3.d note.
3. **Stale table numbers from the Article renumbering (DEFERRED).** Art. 4 tables still read "3.x" (colliding with the new Article 3), Art. 5 "4.x", Art. 6 "5.x", Art. 8 "7.x". The new Article 3's own tables (3.1a/3.1b/3.2/3.3/3.4) are correct.
4. **Cross-section graphics — 10 needed.** One annotated cross-section per Type still unproduced; more relevant now that the four ROW ranges would benefit from a "what 40 ft holds" diagram.
5. **Front matter (cover + TOC)** still absent, so Articles open on recto rather than the baseline's verso.
6. **District-page banner styling**, **use-table status glyphs** (`❶ ❷ ✪` need a fallback font), and **R-2 maximum grade (12%) vs. RDEO's 10%** — all carried unchanged from v0.4.3.
