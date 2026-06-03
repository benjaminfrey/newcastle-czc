# Summary of Changes — v0.18-draft

**Release type: Classification-engine improvement — the §5.D rubric is now implemented
in code, and the draft village classification is auto-corrected.** Two related things:
(1) the v0.16 "form governs in the village" rubric had lived only in the prose — the
classify engine still did "collector → R1 everywhere," so the village Types depended on
hand overrides; this release makes the engine actually apply the rubric. (2) A
"most-urban-district-wins-in-the-village" tweak (with an overlap gate) re-types **9
village segments** the distorted trace had left as Road types.

No regulatory text changes (the engine/data changed, not Article 3's words).

**Compares against:** [v0.17-draft](../v0.17-draft/). The vs-v0.17 redline is empty —
the change is in the classification data + the rendered Exhibits 3.1/3.2, not the
markdown.

## 1. The rule (now in `lib.classify_type`)

The §5.D classification rule is centralized in `build/street-types/lib.py` so the
pipeline and any re-classification share one implementation:

- **Arterials stay R4/R5** in every District (they're the regional highways — a Route 1
  segment no longer becomes a neighborhood street just because the trace runs it through
  a campus polygon).
- **Road-default Districts** (D1, SD-Conservation, SD-Highway Commercial, SD-Rural
  Highway): MaineDOT functional class governs (Collector → R1, else the District default).
- **Form Districts** (D2–D6, SD-Historic, SD-Campus, …): the Adjacent-District test
  governs regardless of functional class — a collector through the village takes the
  village Type (this is what makes Main St → S1 fall out of the rule, not just the override).
- **Most-urban-wins, gated:** where a segment touches several Districts, the more urban
  *form* District governs **only if it covers ≥ 25 %** of the segment — so a rural road
  merely clipping a village edge stays rural.

`03_join.py` now emits per-District overlap **fractions** (`district_fracs`); `04_classify.py`
consumes them via `lib.classify_type`. The eventual exact-shapefile re-run applies all of
this automatically.

## 2. The 9 reclassifications (all R → S, collectors/locals in form Districts)

| Street | Change | Driver |
|---|---|---|
| Mills Road (×4) | R1 → **S3** | collector through SD-Campus / D2 / SD-Fabrication |
| River Road | R1 → **S2** | 31 % D5 (village business) |
| Stonebridge Circle | R2 → **S3** | 39 % D2 |
| Teague Street | R2 → **S2** | 29 % D5 |
| Austin Road | R1 → **S3** | 40 % SD-Historic |
| High Street | — → **S3** | resolves the last unclassified segment |

Result: **215 / 215 typed (0 unclassified)**; S2 6 → 8, S3 14 → 21, R1 42 → 36. Arterials,
the Route 1 corridor, the rural R2 majority, and the Main St overrides are unaffected.

## 3. Deliverables

- `Newcastle CZC (Integrated Draft v0.18-draft).pdf` / `.md`
- `Article 3 Thoroughfares (Standalone v0.18-draft).pdf` / `.md`
- `Redline — Full CZC v0.18-draft vs v0.17-draft.pdf` — **empty by design** (no prose
  change; the reclassification appears in the rendered Exhibits 3.1/3.2).
- `Redline — Full CZC v0.18-draft vs v0.1-baseline.pdf` — cumulative (unchanged counts).

## 4. Verification

- Engine: `lib`, `03_join`, `04_classify` compile; `lib.classify_type` unit-spot-checked
  (village collector → S2; rural-edge clip → R1 via the gate; arterial → R4/R5; override
  wins).
- Map (Exhibit 3.2): the village now reads S2/S3; the legend dropped "Unclassified."
- Parity unchanged: integrated 121 body pages; standalone 27.

## 5. Notes & carry-forward

- Still a **DRAFT**. This sharpens the *village* classification on the existing
  approximate trace; it does not make the district *layer* itself accurate. The clean,
  100 % layer still comes from dropping in the contractor's exact district shapefile and
  re-running — at which point this same rule (now in the engine) produces the right Types
  automatically.
- The 25 % overlap gate is the main dial; it can be tuned if the exact shapefile suggests.
