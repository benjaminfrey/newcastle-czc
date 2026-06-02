# Summary of Changes — v0.17-draft

**Release type: Editorial — stop citing the repealed RDEO by name in incidental
prose.** The Newcastle Road, Driveway, and Entrance Ordinance is now named in only one
place — the clause that actually repeals and supersedes it. The three other spots that
mentioned it in passing are reworded to keep their substance without the citation. No
standard, dimension, definition, or Type changes. It also trims the two always-empty reference columns (ROW ft, Nonconformity) from the rendered Exhibit 3.1 table (see below).

**Compares against:** [v0.16-draft](../v0.16-draft/).

## What changed (Article 3 prose only)

- **§3.E ¶1 (basis for maximum grades):** "*The Newcastle Road, Driveway, and Entrance
  Ordinance, repealed concurrent with this Article, set a single maximum grade by
  ownership … (former Table 2.2)*" → "*Prior Town standards set a single maximum grade
  by ownership — 8% for a public road and 10% for a private road*". The rationale (old
  standard was ownership-based; this Article calibrates by transect) is unchanged.
- **§3.E ¶2:** "*the former Public-Road maximum*" → "*the prior 8% public-road
  maximum*"; the quoted instruction "*The repealed Ordinance itself directed that 'road
  grades shall conform … to the original topography'*" is folded in as the Code's own
  principle ("*… keeps road grades as close as possible to the original topography …*").
- **§14.D ¶2 (substantial reconstruction):** "*is defined in the same manner as in the
  prior Newcastle Road, Driveway, and Entrance Ordinance, namely:*" → "*means*". The
  definition itself is kept word-for-word.

## What was deliberately kept

- **§1.A ¶6 — the repeal/supersede clause:** "*To absorb, calibrate, and supersede the
  Newcastle Road, Driveway, and Entrance Ordinance adopted November 3, 2020, which is
  repealed concurrent with the adoption of this Article.*" This is the one place that
  *should* name the RDEO — it is the instrument that repeals it.
- **Article 9 "Driveway" entry** — references the *prior definition* (not the RDEO by
  name); left as-is.

## Exhibit 3.1 — empty columns trimmed

The rendered Inventory table dropped its two always-empty reference columns — **ROW ft**
and **Nonconformity** (both 0/215 populated: the free GIS layers carry no right-of-way
widths, and nonconformity is derived from them). The table now shows **Thoroughfare ·
From → To · Type · Ownership · District**. The `row_ft`, `traveled_ft`, and
`nonconformity` fields stay in `inventory.json` (nothing lost) and can be re-surfaced
once the review populates them. A non-binding presentation change — the Type remains the
binding content.

## Deliverables

- `Newcastle CZC (Integrated Draft v0.17-draft).pdf` / `.md`
- `Article 3 Thoroughfares (Standalone v0.17-draft).pdf` / `.md`
- `Redline — Full CZC v0.17-draft vs v0.16-draft.pdf` — the three rewrites (2 passages).
- `Redline — Full CZC v0.17-draft vs v0.1-baseline.pdf` — cumulative (unchanged counts).

## Verification

- The RDEO name appears **exactly once** in the rendered Code (the §1.A repeal clause).
- Substance preserved: the grade rationale and the "Substantial reconstruction"
  definition read the same, minus the citation.
- **Parity & pagination unchanged:** integrated 121 body pages; standalone 27 pages.
