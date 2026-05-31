# Summary of Changes — v0.8-draft

**Release type:** **Reorganization release.** Moves the ten Street/Road Type pages from the back of Article 3 **up into Section 2**, where each Type's standards live, and turns each page into a **one-stop Type page** — description, target Districts, character, full design standards, and the cross-section illustration, all on one leaf. This makes the Type pages work exactly like Article 2's District pages: open to a Type and find almost everything you need about it in one place. The former §2.D–§2.M per-Type **prose subsections are removed** (their text is rolled onto the pages) and the Section 3 **comparison matrices (Tables 3.1a / 3.1b) are retired** (each page is now the standards home). **No regulatory standard is added, removed, or altered** — every width, range, speed, and grade is preserved, and the one rule that lived only in deleted prose (the R-3 passing pull-out) is relocated intact into Section 3.

**Compares against:** [v0.7-draft](../v0.7-draft/). A `diff-pdf` overlay against v0.7 ships as *Redline — Full CZC v0.8-draft vs v0.7-draft.pdf*.

**Why this release exists.** The direction was explicit: *"I love the Street/Road pages… instead of having those pages way down at the bottom, I'd like to move them up to be in Section 2. They should take the place of items 2.D thru 2.M, and we should roll what is currently in each of those sub-sections onto the new pages… we're trying to replicate the idea behind the District Pages, where we can go to a Street/Road Type page and get almost all the information we need about the Street/Road Type right there in one place."* v0.7 placed the plates at the end of Article 3 — page-number-safe, but the reader had to hold each Type's prose (in §2) and its cross-section (after §14) in two different places, and consult Tables 3.1a/3.1b in §3 for the numbers. v0.8 collapses all three into a single page per Type, seated where the Type is introduced.

---

## 1. What changed, in one picture

| | v0.7 | **v0.8** |
|---|---|---|
| **Type-page location** | end of Article 3, after §14 | **inside §2**, where each Type is introduced |
| **Per-Type prose (§2.D–§2.M)** | 10 subsections of prose | **removed** — rolled onto the Type pages |
| **What's on a Type page** | cross-section + standards strip | **description + target Districts + character + full standards + cross-section** |
| **Comparison matrix (§3)** | Tables 3.1a / 3.1b (11-col split) | **retired** — each page is the standards home |
| **Section 3 title** | "TYPE STANDARDS TABLE" | **"STREET & ROAD STANDARDS"** (rules of general application) |
| **Driveway (D)** | §2.N prose, no page | **§2.D prose, no page** (unchanged in substance) |
| **Auto-TOC** | flat Article 3 heading list | **10 Type pages nested** under Article 3, in page order |
| **Integrated length** | 111 pp | **111 pp** (unchanged) |
| **Standalone Article 3** | 20 pp (10 prose + 10 plates) | **19 pp** (shorter prose + 10 inline pages) |
| **Downstream Articles 4–9** | pp 53 / 59 / 67 / 75 / 85 / 101 | **identical** — pp 53 / 59 / 67 / 75 / 85 / 101 |
| **Regulatory standards** | — | **none changed** (R-3 pull-out rule relocated, not lost) |

The ten Type pages, now at integrated printed pages 35–44:

| Page | Code | Name | Family |
|---|---|---|---|
| 35 | **S-1** | Main Street | Street |
| 36 | **S-2** | Village Street | Street |
| 37 | **S-3** | Neighborhood Street | Street |
| 38 | **S-4** | Lane | Street |
| 39 | **S-5** | Alley | Street |
| 40 | **R-1** | Connector Road | Road |
| 41 | **R-2** | Rural Road | Road |
| 42 | **R-3** | Rural Lane | Road |
| 43 | **R-4** | Highway Commercial | Road |
| 44 | **R-5** | Rural Highway | Road |

## 2. The Type page — what one leaf now shows

Each page is built to read as a torn-out leaf of the adopted code, mirroring an Article 2 District page. Top to bottom:

- **Code badge + name banner** — the *identical* Article 2 district-band chrome, article blue for Streets, muted olive for Roads, badge at the fore-edge.
- **Context kicker** — e.g. *"STREET TYPE · D6 Town Center · designated D5 segments."*
- **Description** *(new on the page)* — the authoritative one-paragraph regulatory text for the Type, rolled on from the former §2 prose subsection. This is the page's binding descriptive language.
- **Type-specific note** *(new, where applicable)* — a colored left-bar callout in the Type's family color. S-1 carries the **Shopfront Required** rule (subsuming the District-Map overlay under the S-1 classification); S-2 carries **Shopfront by designation** (Article 5 §12). R-4/R-5 carry the **state-aid / MaineDOT** coordination note.
- **Cross-section illustration** — the right-of-way drawn to typical width (travel lanes, parking, planting strips, sidewalks, shoulders, curbs, context), with per-segment width callouts and the right-of-way bracket. Height cap tightened from 225 pt to 180 pt so the illustration shares the page with the rolled-on prose without crowding.
- **Credit line** — CC BY-SA 4.0 attribution (unchanged obligation; see v0.7 §5). The line no longer points at the retired Tables 3.1a/3.1b — it now reads "widths are typical values within the ranges in the Design Standards below."
- **Design Standards strip** — the Type's full **14-row** standard set (Right-of-way, Traveled way, On-street parking, Curb, Planting strip, Sidewalk, Street trees, Design speed, Max. grade, Max. block length, Curb return radius, Sight distance, Pavement, Surface), values verbatim from the retired tables. This strip **is** the standards home now.
- **Target Districts** and **Character** columns *(renamed)* — formerly "Applies In" / "Key Attributes." These carry the scannable district list and qualitative character that the District pages of Article 2 carry, de-duplicated against the description above.

**R-4 and R-5 remain explicitly illustrative.** US Route 1 is a State Highway; its cartway geometry and right-of-way are MaineDOT's. Those two pages keep the "ILLUSTRATIVE SECTION · CARTWAY & R.O.W. PER MAINEDOT" override on the bracket and the credit line, and read "Per MaineDOT" for cartway dimensions while showing the Town-controlled rows plainly.

## 3. Section 2 prose surgery

The Section 2 changes are the heart of this release:

- **§2.C (GENERAL)** items 4–5 reworded: item 4 now states the full design standards are on each Type's page (referencing §8 sight distance and §11 construction by name); item 5 describes the Type pages and states the binding/illustrative relationship (*"The cross-section illustration is representative; the design standards stated on the page govern"*) and the absence of a Driveway page.
- **The `<!-- TYPE-PAGES -->` marker** is inserted at the point where the per-Type prose used to begin. The build splits Article 3 here (see §5).
- **§2.D MAIN STREET through §2.M RURAL HIGHWAY are deleted** — ten prose subsections, ~150 lines. Their Description / Target Districts / Character / Shopfront / State-aid content is rolled onto the corresponding Type pages via `types.json`.
- **§2.N DRIVEWAY is renumbered §2.D DRIVEWAY** — it is now the only prose subsection after the Type pages, kept as prose by design (a Driveway is not a Street or Road Type and gets no page).

## 4. Section 3 slimmed — matrices retired, rules retained

Section 3 is renamed **"STREET & ROAD STANDARDS"** (was "TYPE STANDARDS TABLE") and reframed as the **rules of general application** that govern the per-page standards rather than a place that holds a comparison table:

- **The Table 3.1a (Streets) and Table 3.1b (Roads) raw-Typst comparison matrices are deleted.** Every value they held is preserved on the Type pages' Design Standards strips. An HTML comment marks where they were and explains the retirement.
- **§3.A–§3.C reworded** to point at the Type pages and explain how ranges and "per MaineDOT" entries are read; the binding-minimum rule is retained.
- **§3.C gains item 5** — the **R-3 passing pull-out rule** (pull-outs at ≤300 ft intervals where the traveled way is ≤15 ft, sized for two vehicles to pass and for fire apparatus). This rule previously lived *only* in the deleted §2.K Rural Lane prose; relocating it to §3 of general application is what guarantees **no standard is lost** in the prose deletion.
- **§3.D (Basis for ROW Widths)** and **§3.E (Basis for Maximum Grades)** retain their full justification text; the only edit is "Table 3.1a and Table 3.1b" → "the Type pages in Section 2."

## 5. Build mechanism — two passes around the native plate block

Native-Typst pages cannot be emitted mid-pandoc-flow (pandoc paginates the markdown as one stream and forbids `pagebreak()` inside `columns()`). To seat the plates *inside* §2 rather than at the article's end, the build now renders Article 3 in **two pandoc passes around the Typst plate block**, split at the `<!-- TYPE-PAGES -->` marker:

1. **`build/split-article-03.py`** *(new)* — splits the source at the marker into **03a** (frontmatter + opener + §1 + §2.A–§2.C) and **03b** (frontmatter + §2.D Driveway + §3 … §14). It copies the YAML frontmatter to both halves and inserts `continuation: true` into 03b's frontmatter.
2. **`style/czc-template.typ`** — gains a `continuation` flag. When set, the template suppresses **only** the big "ARTICLE 3" opener + divider, so 03b resumes mid-article without repeating the title. The rotated Article tab and the running head still render (they key off `article-number` / `article-name`, which both halves carry).
3. **`build/build-full-czc.sh`** and **`build/build-article-3.sh`** render the sequence **03a → (pad blank if odd) → 10 plates → 03b**, each segment at its cumulative page offset.

**The parity invariant holds by construction.** The plate block requires an **even** `page_offset` (its chrome keys off logical page = `here().page() + page_offset`, so even offset keeps logical parity equal to physical parity and the badge sits on the correct fore-edge). 03a is padded to an even length before the plates if needed, and 10 plates is itself even, so 03b and everything downstream stay on an even offset. Verified: footers run continuously across the 03a→plates→03b seams; S-1 opens recto; Articles 4–9 land on exactly the pages they occupied in v0.7.

## 6. Auto-TOC now nests the Type pages (`build/toc_entries.py`)

The table of contents is derived from the rendered body PDF, not hand-maintained, so it cannot drift. It already scanned for 33 pt blue Article openers, 14 pt blue Section headings, and 19 pt district banner names (Article 2). This release teaches it the Type pages:

- **Type-banner scan added.** The scanner reads `source/exhibits/cross-sections/types.json`, builds a banner-text → label map (`"MAIN STREET"` → `"S-1 Main Street"`), and matches the 19 pt banner on each plate, filing each as an Article-3 sub-entry in page order, nested after the "Street & Road Types" heading.

Two defects surfaced and were fixed while wiring this up:

- **Cross-Article name collision (fixed).** R-4 "HIGHWAY COMMERCIAL" and R-5 "RURAL HIGHWAY" are *also* the names of two Article 2 Special Districts. Because Article 2 precedes Article 3, an unbounded scan stole those Types' page numbers from the Article 2 spreads. Fixed by computing each Article's physical page range (`art_range`) and **bounding the district-banner scan to Article 2's pages and the Type-banner scan to Article 3's pages.** Verified: R-4 → printed 43, R-5 → printed 44 (their plate pages), and the Article 2 SD spreads keep their own page numbers.
- **Same-page section reorder (fixed).** Section 3 ("STREET & ROAD STANDARDS") and Section 4 ("OWNERSHIP CATEGORIES") both begin on printed page 45. A `sort(key=(page, name))` placed §4 before §3 alphabetically. Switched both the Article-2 and Article-3 assembly branches to a **page-only stable sort** — `sections` is already in document order from the top-to-bottom scan, so a stable sort by page slots the plates in by page while preserving document order for any two headings that share a page.

The resulting Article 3 TOC (page targets): Streets, Roads & Driveways 33 · General 33 · Street & Road Types 33 · **S-1 Main Street 35 · S-2 Village Street 36 · S-3 Neighborhood Street 37 · S-4 Lane 38 · S-5 Alley 39 · R-1 Connector Road 40 · R-2 Rural Road 41 · R-3 Rural Lane 42 · R-4 Highway Commercial 43 · R-5 Rural Highway 44** · Street & Road Standards 45 · Ownership Categories 45 · Classification of Existing Streets & Roads 46 · New Streets & Roads 47 · Driveways 47 · Entrances 48 · Intersections 49 · Water Management 49 · Construction Standards 49 · Coordination with Maine DOT 50 · Administration 50 · Nonconforming Streets & Roads 50.

## 7. Cross-reference updates

Because the per-Type prose subsection letters (§2.D–§2.M) and the comparison tables (3.1a/3.1b) no longer exist, every reference that pointed at them is repointed to "Section 2 (Type X-n)" or "the Type's page in Section 2":

- **`source/article-03-…md`** internal refs: §6.D (new-street design standards), §9.C.1 (intersection curb return radius), §13.H (waivers), §14.B (nonconforming applicability) — all moved off "Section 3 Tables 3.1a/3.1b" onto the Type pages / Section 3 rules.
- **`source/article-04-site-standards.md`** §1.F.1 (vehicular access): "Types S-4 or S-5 per Article 3 Section 2.G–H" → "per Article 3 Section 2."
- **`source/article-09-definitions.md`**: each Street/Road Type definition's "Defined in Article 3 Section 2.D" (… 2.E … 2.M) → "Section 2 (Type S-1)" (… etc.); the "On-Street Parking Lane" entry's "counted separately … in Tables 3.1a and 3.1b" → "on each Type's page in Article 3 Section 2."
- **`memos/Right-of-Way Width Reduction — Justification Memo.md`**: references to "Tables 3.1a & 3.1b" updated to "the per-Type pages in Article 3 §2." The memo remains an unadopted discussion draft by design.

## 8. The `types.json` enrichment & plate-layout changes

These turn each plate from a v0.7 cross-section figure into a v0.8 one-stop page:

- **`source/exhibits/cross-sections/types.json`** — each Type gains a **`description`** (the authoritative regulatory paragraph rolled off the deleted prose); S-1/S-2 gain a **`note`** (shopfront cross-reference); every Type's **`standards`** block is filled out to the **uniform 14 rows** (adding Max. grade, Max. block length, Curb return radius, Sight distance "Per Table 3.2", Pavement "Per Table 3.3" / "Per MaineDOT" where each was previously absent); `attributes` rewritten as the scannable **Character** column, de-duplicated against the new description and standards.
- **`source/cross-section-plates.typ`** — renders the new `description` block and the optional colored-bar `note`; relabels the two reference columns **"Applies In" → "Target Districts"** and **"Key Attributes" → "Character"**; relabels the standards panel from "Design Standards — Table 3.1a/b" to **"Design Standards"**; tightens the illustration height cap (225 pt → 180 pt) to fit the rolled-on prose; updates the credit line off the retired tables.

## 9. What did NOT change

- **No regulatory standard added, removed, or altered.** Every ROW range, traveled-way width, lane count, parking provision, curb type, planting strip, sidewalk, street-tree rule, design speed, max grade, max block length, curb return radius, sight-distance reference, pavement spec, and surface is preserved — moved from the tables onto the per-Type pages verbatim. The R-3 passing pull-out rule moved from deleted prose into §3.C.5 intact.
- **Downstream pagination is identical.** Articles 1, 2, and 4–9 are untouched apart from the footer version stamp; Articles 4–9 open on exactly the printed pages they occupied in v0.7 (53 / 59 / 67 / 75 / 85 / 101). The internal rearrangement of Article 3 changed total length by zero pages.
- **The Driveway has no page.** Ten Type pages only, by design; the Driveway stays a short prose subsection (§2.D).
- **The plate generation pipeline is unchanged.** The Python compositor and the Streetmix CC BY-SA sprite provenance/attribution (`NOTICE.md`) are as shipped in v0.7.

## 10. Relationship to the baseline (no vs-baseline visual redline)

As with v0.5–v0.7, no page-by-page `diff-pdf` overlay against the original *Newcastle Core Zoning Code.pdf* is shipped: once the draft added a cover, an auto-derived TOC, native District spreads, and ten Type pages, a physical page-overlay against the baseline aligns nothing and reads as noise on every page. The substantive relationship to the baseline is unchanged from prior releases and is narrated across the Summaries: the standalone Road, Driveway & Entrance Ordinance is absorbed into a new form-based Article 3; Articles 3–8 are renumbered 4–9; and the cross-references are repointed. This release reorganizes *within* the already-drafted Article 3 and touches no baseline-derived content, so the baseline relationship is exactly as described in v0.4.x. The shipped **v0.8-vs-v0.7 redline** is the meaningful diff for this release — both documents are 111 pages with Articles 1–2 and 4–9 on identical pages, so the overlay isolates precisely the Article 3 reorganization.

## 11. Deliverables

- **`Newcastle CZC (Integrated Draft v0.8-draft).pdf`** — 111 pp (4 front matter + 107 body); Type pages at printed pp 35–44, inside §2.
- **`Newcastle CZC (Integrated Draft v0.8-draft).md`** — concatenated markdown; a pointer comment marks where the Type pages render (they have no markdown form).
- **`Article 3 Streets Roads & Driveways (Standalone v0.8-draft).pdf`** — 19 pp (opener + §1 + §2.A–C, then 10 Type pages at pp 3–12, then §2.D Driveway + §3 … §14).
- **`Article 3 Streets Roads & Driveways (Standalone v0.8-draft).md`** — Article 3 source (retains the `<!-- TYPE-PAGES -->` marker).
- **`Redline — Full CZC v0.8-draft vs v0.7-draft.pdf`** — `diff-pdf` overlay isolating the Article 3 reorganization.
- **`Summary of Changes v0.8-draft.md`** — this document.

## 12. Files changed

- **`source/article-03-streets-roads-driveways.md`** — removed §2.D–§2.M prose; inserted the `TYPE-PAGES` marker; renumbered §2.N → §2.D Driveway; retitled & reframed §3; deleted Tables 3.1a/3.1b; added §3.C.5 (R-3 pull-outs); repointed internal refs.
- **`source/exhibits/cross-sections/types.json`** — added `description` (all 10), `note` (S-1/S-2/R-4/R-5), filled `standards` to 14 rows, rewrote `attributes` as Character.
- **`source/cross-section-plates.typ`** — render description + note; renamed columns/panel; tightened height cap; updated credit line.
- **`style/czc-template.typ`** — added the `continuation` flag; gated the article opener on `not is_continuation`.
- **`build/split-article-03.py`** *(new)* — splits Article 3 at the marker; sets `continuation: true` on the resumed half.
- **`build/build-full-czc.sh`** — two-pass Article 3 render around the spliced plate block; combined-markdown pointer note.
- **`build/build-article-3.sh`** — standalone two-pass render around the plate block at even offsets.
- **`build/toc_entries.py`** — Article-bounded banner scans (`art_range`); Type-banner scan from `types.json`; page-only stable sort.
- **`build/build-redline.sh`** — write `diff-pdf` output to an ASCII temp path, then move into place (works around diff-pdf's double-encoding of non-ASCII output filenames; see §13).
- **`source/article-04-site-standards.md`**, **`source/article-09-definitions.md`**, **`memos/Right-of-Way Width Reduction — Justification Memo.md`** — cross-reference repointing (§7).
- **`releases/v0.8-draft/`** — Integrated (111 pp) `.md`/`.pdf`, Article 3 standalone (19 pp) `.md`/`.pdf`, the v0.8-vs-v0.7 redline, and this Summary.

## 13. Defect fixed along the way — redline filename encoding (`build/build-redline.sh`)

`diff-pdf` (a wxWidgets program) **double-encodes non-ASCII bytes** passed in `--output-diff`. The release filename contains an em-dash (`Redline — Full CZC …`), so diff-pdf wrote a valid 71 MB diff to a *mojibake* filename and the script's `[ -f "$OUTPUT" ]` guard — looking for the clean UTF-8 path — reported "did not produce an output file." Fixed by writing the diff to an ASCII-only `mktemp` path and then `mv`-ing it to the final destination through the shell (which handles UTF-8 filenames correctly). The redline now ships under its intended name.

## 14. Verification

- **Integrated PDF: 111 pp** = 4 front matter + 107 body. Article 3 opens at printed p 33; **Type pages at printed pp 35–44, inside §2**; §3 "Street & Road Standards" at printed p 45; Articles 4–9 at pp 53 / 59 / 67 / 75 / 85 / 101 — **identical to v0.7**.
- **All 10 Type pages render clean** — badge/banner chrome, context kicker, description paragraph, family-colored note bar (S-1/S-2 shopfront, R-4/R-5 MaineDOT), cross-section with width callouts and ROW bracket, CC BY-SA credit, 14-row Design Standards strip, Target Districts + Character columns. R-4/R-5 show the MaineDOT illustrative override.
- **Badge/running-head parity correct** — S-1 recto (badge right) through R-5 verso (badge left), alternating; running heads read "Street Types" (S-1…S-5) and "Road Types" (R-1…R-5); footers continuous across the 03a→plates→03b seams.
- **Standalone Article 3: 19 pp** — opener (p 1), §1 + §2.A–C (p 2), Type pages (pp 3–12), §2.D Driveway onward (pp 13–19); the big opener is **not** repeated after the plates (continuation flag verified).
- **Auto-TOC correct** — 10 Type pages nested under Article 3 in page order; R-4/R-5 resolve to their plate pages (43/44), not the Article 2 SD spreads; §3 before §4 on shared page 45.
- **No standard lost** — every Table 3.1a/3.1b value is present on the corresponding Type page; the R-3 pull-out rule is present in §3.C.5.
- **Build reproducibility** — `build-full-czc.sh` and `build-article-3.sh` reproduce the committed PDFs; `build-redline.sh` reproduces the redline under its UTF-8 name.

## 15. What's still off (carry forward)

1. **Comprehensive Plan citations** in §3.D remain to be re-verified against the adopted June 2018 plan text before public release (carried from v0.6/v0.7).
2. **The ROW Justification Memo** remains an unadopted discussion draft *by design* (carried from v0.6/v0.7); its table references are now updated to the per-Type pages.
3. **`article-02.typ` running-head lag** at the Core→Special district boundary (the same Typst mechanism fixed on the plates in v0.7) is still queued as a separate fix so it does not perturb Article 2's reviewed output.
4. **Existing-street inventory** (Article 3 §5 classification table + District-Map exhibit) remains a staff/Planning-Board field exercise, unchanged by this release.
