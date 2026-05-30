# Summary of Changes — v0.6-draft

**Release type:** **Front-matter + cleanup release.** Adds the two pieces of document furniture the draft has lacked since the rebuild — a **cover page** and a **Table of Contents** — and clears three of the items the v0.5 carry-forward list flagged: stale table numbers from the Article renumbering, the undocumented road-grade calibration, and the absent front matter. **No new or altered regulatory standard** is introduced; every change is either document furniture, a corrected caption/cross-reference, or an explanatory note about figures that were already in the code.

**Compares against:** [v0.5-draft](../v0.5-draft/).

**Why this release exists.** Through v0.5 the integrated draft opened cold on Article 1 with no cover and no contents — fine for engineering review, wrong for a document headed to a Planning Board and Town Meeting. This release builds both, *reusing the adopted code's own cover art and its own TOC grammar* so the front matter reads as part of the same book rather than a generated wrapper. Two smaller debts are also retired: the table captions that still carried pre-renumbering numbers, and the absence of any written basis for why the draft's maximum road grades differ from the repealed Roads Ordinance.

---

## 1. What changed, in one picture

| | v0.5 | **v0.6** |
|---|---|---|
| **Cover** | none (opened on Article 1) | **baseline cover art reused** (wordmark, dates, town seal) + DRAFT banner; the handwritten clerk attestation is masked |
| **Table of Contents** | none | **2-page TOC, auto-derived by scanning the built body** — can never drift from the content |
| **Front-matter pages** | 0 | **4** (cover, blank verso, 2× TOC) — an even count, so the body's page parity is untouched |
| **Integrated length** | 97 pp | **101 pp** (97 body + 4 front matter) |
| **Stale table numbers** | Art. 4 read "3.x", Art. 5 "4.x", Art. 6 "5.x", Art. 8 "7.x" | **fixed** → 4.x / 5.x / 6.x / 8.x (commit `8d4f179`) |
| **Road-grade basis** | grades calibrated but unexplained | **Article 3 §3.e "Basis for Maximum Grades"** added (commit `30710f5`) |
| **Standalone Article 3** | 9 pp | **10 pp** (+1 from the §3.e note) |

## 2. Front matter — the cover (`build/build-cover.py`)

The cover is **not** redrawn; it reuses the adopted code's own art so the draft is visually anchored to the document it amends.

- **Baseline art, rotation-correct.** Baseline page 0 is a `/Rotate 90` landscape scan. Rendering it to a pixmap *honors* the rotation (upright 612×792), whereas vector-pasting would not — so the cover is rasterized at 300 dpi and placed as the page image. The blue "CORE ZONING CODE / NEWCASTLE, MAINE" wordmark, the Effective/Adopted/Amended dates, and the town-seal watermark all carry over at full fidelity.
- **The clerk attestation is masked.** The lower-left handwritten *"Attested By: …"* signature block is a legal certification that the document is a true copy of the **adopted** code; it must not appear on an unadopted draft that contains a proposed Article 3. A white rectangle (matched to the scan's near-white background, so it is invisible) covers the label + signature + date, staying clear of "NEWCASTLE, MAINE".
- **DRAFT banner.** An article-blue bar in the upper white space reads **"INTEGRATED DRAFT — NOT ADOPTED"**, then *"v0.6-draft · includes proposed Article 3: Streets, Roads & Driveways"*, then a gray provenance line: *"Generated May 30, 2026 from the adopted Core Zoning Code (amended through March 24, 2025). For review only — not a certified copy."* Set in embedded Barlow so the em-dash and middle-dot encode correctly.

## 3. Front matter — the Table of Contents (`build/toc_entries.py` + `build/toc.typ`)

The TOC is **derived from the rendered document, not hand-maintained**, so it cannot fall out of sync with the content.

- **It keys off the same visual signals the baseline's own TOC uses.** `toc_entries.py` scans the built body PDF: 33 pt article-blue spans are Article openers; 14 pt article-blue spans (numbered "N. NAME") are Section headings → sub-entries; the 19 pt district banner names (matched against `article-02-data.json`) become Article-2 sub-entries. A same-page guard prevents an un-numbered blue heading (e.g. the Definitions "DEFINITIONS ADDED FOR ARTICLE 3" divider) from being mis-merged into a real section.
- **Page numbers are the body's own printed numbers.** The body prints 1…N exactly as before; the TOC references *those* numbers, which are independent of front-matter length — so there is **no circularity** and the build needs no second pass.
- **It is rendered in the CZC's TOC grammar** (`toc.typ`), measured from baseline pages 2–3: identical page geometry to the body (inside 90 / outside 44, two 217 pt columns, 44 pt gutter), a "CONTENTS" running head and "TABLE OF CONTENTS" title, gray **ARTICLE N** labels, and blue sub-entries with dot leaders and right-aligned page numbers. A side-by-side check (this release's *Front Matter Fidelity* PDF) confirms the draft TOC and the baseline TOC read as the same family.
- **Coverage:** all 9 Articles with their sections — Art. 1 (5), Art. 2 (18, including the 13 district spreads merged in by page order), **Art. 3 Streets, Roads & Driveways (14)**, Art. 4 (12), Art. 5 (18), Art. 6 (7), Art. 7 (66 uses), Art. 8 (29). Article 9 Definitions is a glossary and carries no numbered sub-sections, exactly as the baseline lists it.

## 4. Assembly & the parity arithmetic (`build/build-full-czc.sh`)

The body build is **unchanged** — it still renders Articles 1–9 to printed pages 1…N. Front matter is layered on afterward (Convention A): build body → scan body for the TOC → build cover → render TOC → prepend.

Two parity invariants govern the assembly, both satisfied by construction:

1. **The TOC must land where it was rendered.** The TOC is compiled standalone, so its header/footer and inside/outside binding margins bake in at compile time against its *own* physical page parity. For that to match the final document, the number of pages **before** the TOC must be even. Layout `[cover] [blank verso] [TOC…]` puts 2 pages before the TOC → it opens on a recto, and its margins/running-head sit on the correct edge (verified: recto outer edge = right, verso = left, matching the baseline).
2. **The body's parity must be preserved.** Total front matter is forced **even** (cover + blank + TOC, plus one trailing blank if the TOC page count is odd). An even shift keeps every Article opening on the same parity it had standalone. Confirmed in the assembled PDF: printed page "1" (Article 1) sits on physical page 5 (recto); footers run 1…97 continuously, number on the right fore-edge for odd/recto and left for even/verso.

**Documented deviation (unchanged from v0.5):** the body opens each Article on a **recto**, whereas the baseline opens on a **verso** (it paginates its front matter 1–3 and pads every Article to an even length). Replicating verso-opening would require either per-Article leading blanks (page bloat, not in the baseline) or abandoning Typst's automatic binding margins. Recto-opening is retained as a deliberate, parity-safe deviation; the even front matter does not change it.

## 5. Stale table numbers fixed (commit `8d4f179`)

When Articles 3–8 were renumbered to 4–9, their table captions and in-text references were not. This release corrects them, scoped strictly to captions/refs (no data changed):

- **Art. 4 Site Standards** — the baseline's two different "Table 3.1"s are disambiguated to **4.1 (Screening Formula)** and **4.2 (Site Lumens)**.
- **Art. 5 Building Standards** — 4.x → **5.x** (Tables 5.1–5.7; 11 references).
- **Art. 6 Design Standards** — 5.x → **6.x** (Tables 6.1–6.21; 23 references).
- **Art. 8 Administration** — 7.x → **8.x** (Table 8.1; 3 references).

Article 3's own tables (3.1a / 3.1b / 3.2 / 3.3 / 3.4) and Article 2's matrices were already correct and are untouched.

## 6. Road-grade basis documented — Article 3 §3.e (commit `30710f5`)

The v0.5 carry-forward flagged the draft's **R-2/R-3 12% maximum grade vs. the repealed RDEO's 10%** as an unexplained discrepancy. It is now a deliberate, written calibration — new **§3.e "Basis for Maximum Grades"** (4 numbered items), with the grade *values in Tables 3.1a/3.1b unchanged*:

- Urban Street Types are held at or below the former Public-Road maximum (S-1 Main Street 6%, S-2/S-3 8%) for pedestrian comfort, accessibility, and winter walkability.
- Rural Road Types tolerate steeper grades (R-1 10%, R-2/R-3 12%) to follow natural topography and reduce earthwork in the rural Districts — honoring the repealed Ordinance's own instruction that *"road grades shall conform as closely as possible to the original topography."*
- The steeper rural maximums relax **no safety-critical standard**: the 2% cap within 75 ft of an intersection (§9), the vertical-curve / stopping-sight-distance requirement (§10), and sight-distance / intersection geometry are fixed independently of a Type's maximum grade and apply to every Type.
- R-4/R-5 cartway grades defer to MaineDOT under §12 (US Route 1 is a State Highway).

## 7. What did NOT change

- **No regulatory standard added or altered.** Article 3's typology, ROW ranges, and Tables 3.1a–3.4 are unchanged (§3.e *explains* the existing grade figures, it does not move them). Articles 1, 2, 4–9 carry only the table-caption corrections of §5.
- **The body build is byte-stable** apart from the footer version string and the §3.e / table-caption text — the same 97-page body, same parity, same district spreads from v0.5.
- **The standalone Article 3** changes only by the +1 page the §3.e note adds (9 → 10 pp).

## 8. Deliverables & comparison-artifact decision

A page-by-page `diff-pdf` overlay against v0.5 is **not** shipped. The footer version stamp ("Draft v0.5-draft" → "Draft v0.6-draft") differs on *every* page, so an overlay flags all 97 body pages as changed — pure noise, and it ran to 62 MB. The substantive body deltas are two committed text edits (already enumerated in §5–§6 and visible in `git show 8d4f179 30710f5`). In its place this release ships a **focused fidelity comparison** for the genuinely new material:

- **`Front Matter Fidelity — Baseline vs v0.6-draft.pdf`** (3 spreads) — the cover and both TOC pages, **baseline on the left / v0.6 draft on the right**, so a reviewer can confirm the new front matter reads as the same document. (Mirrors v0.5's *District Spread Fidelity* deliverable; satisfies the plan's "visual integration check.")

## 9. Files changed

- **`build/build-cover.py`** *(new)* — reuses baseline cover art (rotation-honoring rasterize), masks the clerk attestation, stamps the DRAFT banner.
- **`build/toc_entries.py`** *(new)* — derives TOC entries by scanning the built body PDF (article openers / section headings / district banners); same-page merge guard.
- **`build/toc.typ`** *(new)* — renders the TOC in the baseline's two-column CZC grammar (dot leaders, parity-aware running head/footer, unnumbered front matter).
- **`build/build-frontmatter-fidelity.py`** *(new)* — the baseline-vs-draft cover/TOC side-by-side comparison builder.
- **`build/build-full-czc.sh`** — adds the front-matter stage (build cover, scan body, render TOC, prepend with even-page parity arithmetic) and a `DATE_STR` arg for reproducible cover dating; the body render loop is unchanged.
- **`source/article-03-streets-roads-driveways.md`** — new §3.e (committed `30710f5`).
- **`source/article-04/05/06/08-*.md`** — table-caption/reference renumber (committed `8d4f179`).
- **`style/style-analysis.md`** — new section documenting the front-matter architecture and the recto-vs-verso deviation.
- **`.gitignore`** — broadened `extract/_*.png` → `extract/_*` to cover scratch derivation dirs.
- **`releases/v0.6-draft/`** — Integrated Draft (101 pp) `.md`/`.pdf`, Article 3 standalone (10 pp) `.md`/`.pdf`, the Front Matter Fidelity `.pdf`, and this Summary.

## 10. Verification

- **Integrated PDF: 101 pp** = 4 front matter + 97 body. Front matter: p1 cover, p2 blank verso, pp3–4 TOC; body Article 1 begins on physical p5.
- **Cover** renders rotation-correct (wordmark horizontal); the clerk signature is masked (no text in the lower-left block); the DRAFT banner and provenance line encode the em-dash/middle-dot correctly.
- **TOC parity correct in context:** physical p3 (recto) carries the running head + wordmark on the **right** outer edge; physical p4 (verso) on the **left** — matching the baseline TOC. Left column x = 90 (recto) / 44 (verso), as measured from the baseline.
- **TOC accuracy:** all 9 Articles present with the section counts in §3; spot-checked openers resolve (Art. 3 → printed p33, Art. 7 → p65, Art. 9 → p91) and the 13 districts list in page order under Article 2.
- **Footers continuous & parity-correct:** printed 1…97 across physical pp5…101; odd/recto numbers at the right fore-edge, even/verso at the left; footer reads **"Draft v0.6-draft"**.
- **Every Article opener lands on a recto** (all at odd printed numbers → odd physical pages after the even front-matter shift).
- **Standalone Article 3: 10 pp**, includes §3.e.
- **Table captions:** zero residual pre-renumbering "Table 3.x" references survive outside Article 3's own 3.1a–3.4.

## 11. What's still off (carry forward)

1. **Cross-section graphics — 10 needed.** One annotated cross-section per Street/Road Type (S-1…S-5, R-1…R-5) is still unproduced. **Held by direction** — to be taken up as a dedicated effort.
2. **Comprehensive Plan citations are placeholders in spirit.** §3.d cites Comp Plan policy areas; the specific policy/section numbers should be re-verified against the adopted Comp Plan before public release.
3. **The ROW Justification Memo remains an unadopted discussion draft** — *by design*, not as a defect. (Correcting the v0.5 carry-forward, which erroneously listed a "blank FROM line": the memo was finalized in commit `59b6aec` — drafter attribution "Ben Frey" and the §3.6 Comp Plan citations are filled. It is retained as supporting justification, open to revision by the Board.)
