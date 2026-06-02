# Summary of Changes — v0.16-draft

**Release type: Reconcile Main Street — form vs. function/jurisdiction.** Newcastle's
Main Street is a **state-owned Major Collector** through the village, and the draft
classification had typed all of it **R1 (Connector Road — a *rural* type)**, leaving
the flagship **S1 "Main Street" type with zero segments**. This release fixes that two
ways: **(A)** types the Main Street core **S1** (and the next stretch **S2**) while
keeping its Ownership = State Highway, and **(B)** amends the §5.D classification
rubric so a road's MaineDOT function can no longer override its village *form*.

No dimension, standard, or Type definition changed — only one segment's-worth of
classification and one rubric paragraph.

**Compares against:** [v0.15-draft](../v0.15-draft/).

## 1. Why it was mis-typed

Three things compounded:
1. **District trace** put Main Street's segments in **D1 (Rural)** — whose Table 3.4
   default is a Road type. Almost certainly a tracing artifact (downtown belongs in
   D5/D6); it will be corrected in the official-District-Map review.
2. **Rubric ¶d** presumed "Collector → R1," overriding the District/form default.
3. **State Highway** status — an *ownership* fact — was effectively driving *form*.

§4.D already says Type and Ownership are independent and that *"a Main Street (S1)
may be … a State Highway,"* so the framework was sound; the rubric and the draft data
just hadn't honored it.

## 2. A — Data fix (form wins)

`build/street-types/overrides.json` now pins the four downtown-core segments, and the
promoted Inventory reflects it:

| Segment (From → To) | Type | Ownership | District |
|---|---|---|---|
| Mills Rd → Pump St | **S1** | State Highway | D1 |
| Pump St → Glidden St | **S1** | State Highway | D5 |
| Glidden St → Damariscotta bridge | **S1** | State Highway | D5 |
| Mills Rd → River Rd | **S2** | State Highway | D1 |

- **S1 went from 0 → 3 segments** — the flagship type finally carries its namesake.
- Ownership stays **State Highway** on all four; the S1/S2 *form* is the coordinated
  target, realized through the §12 MaineDOT protocol, not unilaterally imposed.
- The western approach to Route 1 is left to the rubric/district (it remains R-typed
  as the highway approach) per the agreed scope.
- The decision lives in `overrides.json`, so the full pipeline reproduces it when the
  exact district shapefile is run.

## 3. B — Rubric fix (durable, prevents recurrence)

§5.D ¶d (MaineDOT functional class test) rewritten so the functional-class presumption
(arterial → R4/R5, collector → R1) applies **only in Districts whose Table 3.4 default
is a Road type** (D1, SD-Conservation, SD-Highway Commercial, SD-Rural Highway). **In
all other Districts the Adjacent-District (form) test governs** regardless of MaineDOT
class — *"a Main Street that is a State Highway is classified S1"* — with the cartway
geometry reconciled with State control through §12 rather than by reclassifying to a
Road type. This stops function from overriding form in the village and will keep the
exact-shapefile re-run correct.

## 4. Deliverables

- `Newcastle CZC (Integrated Draft v0.16-draft).pdf` / `.md`
- `Article 3 Thoroughfares (Standalone v0.16-draft).pdf` / `.md`
- `Redline — Full CZC v0.16-draft vs v0.15-draft.pdf` — **one passage** (the §5.D ¶d
  rewrite; the Type/data change appears in the rendered Exhibits 3.1/3.2, not the text).
- `Redline — Full CZC v0.16-draft vs v0.1-baseline.pdf` — cumulative (unchanged counts).

## 5. Verification

- **Inventory (Exhibit 3.1):** Main Street's core rows now read **S1 ×3 / S2 ×1**, all
  **State Highway**; the western approach stays R1.
- **Type Map (Exhibit 3.2):** the legend now includes **S1 Main Street**; the downtown
  core renders S1 → Mills-to-River S2 → Route 1 R4/R5.
- **Rubric:** §5.D ¶d carries the new village-form-governs wording + the Main-Street-S1
  example.
- **Parity & pagination unchanged:** integrated still 121 body pages; standalone still
  27 pages (continuous, no blanks).

## 6. Notes & carry-forward

- Still a **DRAFT** classification. The district trace that placed Main Street in D1
  (Rural) will be corrected during the official-District-Map review (a pending human
  step); the override pins the *Type* correctly in the meantime, and the rubric fix
  makes the corrected trace yield the right result automatically.
- Two human steps remain before any vote, unchanged: (1) the district-layer eyeball;
  (2) Planning-Board review → Town-Meeting adoption.
