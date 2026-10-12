# Adoption Release — Specification

**Status:** implemented. Approved 2026-08-24; v1.0 was adopted at Town Meeting on September 14, 2026.
Revised 2026-10-11 to match the code (Wave 4b).
**Scope:** `build/build-adoption.sh`, `build/build-adopted.sh`, `build/normalize_for_diff.py`,
`build/adoption-map.json`, `build/build-release.sh`, `build/release_plan.py`, `build/release_gate.py`,
`build/section_map.py`, `build/structural_note.py`, `build/integrated_md.py`, and adoption-mode changes to `build/build-cover.py`,
`build/build-full-czc.sh`, `build/build-redline-full.sh`, and the exhibit banners.

Companion to `CLAUDE.md`'s "Build & release flow". This document is the authority on what an
adoption release must produce and what it must refuse to produce.

---

## 1. Why this exists

Drafting continues as it does today: edit `source/`, cut `vX.Y-draft`, collect changes. This spec
covers only what happens **when a draft is marked ready for Town Meeting**, and it exists because
three things are wrong or absent today.

### 1.1 A baseline redline is currently impossible, not merely noisy

`build-redline-full.sh` diffs each `source/article-*.md` against **the same path** at the old tag.
The article files were renamed when Article 3 was inserted:

| At `v0.1-baseline` | Now |
|---|---|
| `article-02-districts.md` | `article-02-prefatory.md` + `article-02.typ` |
| — | `article-03-streets-roads-driveways.md` *(new)* |
| `article-03-site-standards.md` | `article-04-site-standards.md` |
| `article-04-building-standards.md` | `article-05-building-standards.md` |
| `article-05-design-standards.md` | `article-06-design-standards.md` |
| `article-06-use-standards.md` | `article-07-use-standards.md` |
| `article-07-administration.md` | `article-08-administration.md` |
| `article-08-definitions.md` | `article-09-definitions.md` |

**Measured 2026-08-24: of nine article files, exactly one (`article-01-general.md`) would diff
correctly.** Seven would vanish and eight would render as 100% new. A redline run against the
adopted baseline today would show the entire Code as freshly written — in the document that goes
into a Town Meeting packet.

### 1.2 80% of the raw baseline diff is invisible formatting

Measured 2026-08-24 across the seven mappable article pairs:

| | Changed lines |
|---|---|
| Raw diff | **1,261** |
| After renumbering + heading-case normalisation | **243** |
| Formatting, not substance | **1,018 (80%)** |

Article 1 goes from 30 changed lines to **zero**. Article 7 Use Standards from 298 to **2**. The
cause is a source-formatting normalisation applied at some point (`### A.` → `### a.`) plus
paragraph re-wrapping — neither visible in the rendered PDF, because the Typst template styles
headings itself.

Without normalisation the redline buries 243 real changes under 1,018 cosmetic ones, and a reader
cannot tell which is which.

### 1.2b Article 2's content is no longer text-comparable

Found 2026-08-24 while implementing the normaliser. Article 2's district standards moved out of
markdown into a native-Typst unit between the baseline and now:

| | Lines |
|---|---|
| `article-02-districts.md` at `v0.1-baseline` | **2,444** |
| `article-02-prefatory.md` now | **125** |
| moved into `article-02.typ` + `article-02-data.json` | the remaining ~2,319 |

A text diff cannot see the `.typ`, so it would mark roughly 2,319 lines as **deleted** — which in a
Town Meeting packet reads as *the Town deleted all of its district standards*. This is the same
class of failure as §1.1: a structural change the text diff cannot see, surfacing as an enormous
false change.

Handled the same way the redline already handles every other native figure — **rendered at current
state, unmarked**, and described in the structural note (§4.3). `adoption-map.json` carries a
`not_text_comparable` entry naming the article and why.

### 1.3 A document must never claim it was adopted before the vote

At freeze time the vote has not happened. Only the scheduled meeting date is known. A document
stamped "Adopted March 15, 2027" before March 15 is false, and would remain false if the meeting is
postponed or the article fails.

---

## 2. The lifecycle

Three states. Two commands move between them.

```
   DRAFT                    TOWN MEETING EDITION            ADOPTED
   vX.Y-draft   ──────►     vN.0                 ──────►    vN.0
                 freeze     (frozen, not yet              (voted, carries
                            adopted)                       adoption date)
                build-adoption.sh              build-adopted.sh
```

- **Draft.** Today's behaviour, unchanged. `vX.Y-draft`, `INTEGRATED DRAFT — NOT ADOPTED`.
- **Town Meeting edition.** Content frozen and tagged. Whole version number. Stamped with the
  meeting date and still clearly **not yet adopted**. This is what goes in the warrant packet.
- **Adopted.** Same content, different chrome: adoption date, draft language gone.

### 2.1 Version rules

- **A whole number means adopted law. A decimal means a draft.** This is enforced, not conventional
  (§6.1).
- The Meeting edition and the Adopted edition **share one number** (`v1.0`). The content is
  identical; only the stamp differs, so a different number would imply a change that did not occur.
- After adoption, drafting resumes on the decimal line: `v1.1-draft`, `v1.2-draft`, … and the next
  Town Meeting adoption is `v2.0`.
- **If the vote fails, is postponed, or the article is amended from the floor:** the `v1.0` Meeting
  edition tag stays as a permanent record of exactly what was put to the voters. Drafting resumes at
  `v0.25-draft` (or `v1.1-draft` after a successful adoption), and the next attempt re-cuts `v1.0`
  from the newer content. **A whole number is only ever spent on a document that was actually
  adopted.**

---

## 3. Components

### 3.1 `build/adoption-map.json`

The baseline→current article correspondence: file renames and the article-number map
(`{1:1, 2:2, 3:4, 4:5, 5:6, 6:7, 7:8, 8:9}`).

This knowledge currently exists in exactly one place — a hardcoded `RENUM` dict in
`extract/verso.py:18` — which the build cannot reach. Moving it to data makes it usable by the
redline, the normaliser, and any future baseline comparison, and gives it one place to be corrected.

The map must also mark `article-03-streets-roads-driveways.md` as **new at this adoption** (no
baseline counterpart) so the redline renders it as wholly new rather than as an unmatched file.
(That was the v0.1 map. Since the v1.0 rollover every field below is identity or empty.)

The map records `baseline_version` and, since Wave 4b, `baseline_amended_through` — the date the
baseline Code was last amended (September 14, 2026 for v1.0). The cover reads that date from here
(§7). `baseline_selfcheck.py` guards the rollover (§3.5).

**Section renumbering is not in this map.** When a section is inserted into an Article, later
headings and cross-references shift. `build/section_map.py` *derives* that map from title-identical
headings, in order, between the old ref and the new tree. It is never authored and never committed,
and never goes in `adoption-map.json`. The reason is the 308-phantom-line failure of §3.5: a hand
map that goes stale fails silently, and a derived map cannot go stale. It refuses below a 50%
similarity floor, on a bad ref, or when nothing was compared. Its `selfcheck` requires every entry to
pair title-identical headings and the map to equal a fresh derivation.

### 3.2 `build/normalize_for_diff.py`

Normalisation decides what counts as a difference. **When the result is rendered, it is applied to
the OLD side only** (`normalize_old_side`). The comparison form (`normalize`) also re-wraps
paragraphs; it must never reach a renderer, because it flattens the Code's lettered sub-clauses into
run-on prose (measured: Article 8 went from 211 indented lines to 4). Each rule is separately
testable and separately justifiable:

| Rule | Why it is not substantive |
|---|---|
| Heading letter case (`### A.` → `### a.`) | The Typst template styles headings; case in source never reaches the page |
| Cross-reference renumbering (via §3.1) | The renumbering is real, but is stated once as a structural change (§4.3) rather than marked 126 times (the count at the v1.0 adoption) |
| Paragraph re-wrapping (comparison only, never rendered) | Line breaks in markdown source do not survive rendering |
| Table renumbering (`TABLE 4.1` and its forms) | The leading number is an Article number, renumbered like a heading |
| Frontmatter `article-number` renumbering | Same map, same reason |
| Section renumbering (via the derived map, §3.1) | A pure renumbering of title-identical sections. Runs first; the map is keyed on baseline Article numbers |

**The conservatism requirement is the load-bearing part of this module.** A normaliser that is too
aggressive silently hides a real amendment — the worst failure this feature can produce, because an
omission from a redline is invisible to the reader.

Therefore:

- Every rule ships with a test proving it suppresses the cosmetic case **and** a test proving a real
  change of the same shape still appears. Deleting a sentence, changing a number, or reversing
  "shall"/"may" must survive normalisation in every case.
- Normalisation **never** touches: numerals, defined terms, `shall`/`may`/`must`, section content,
  or any word not covered by a listed rule.
- The module reports what each rule suppressed, by count, so the effect is visible rather than
  assumed.
- **The section rule is the most conservative.** A bare or plural reference is rewritten only when
  nothing qualifies it. It leaves raw anything it cannot prove internal: statute tokens, any
  `<word> <number>` or `<name>,` before it, any `of …` after it (except "of this Article"), any
  paragraph naming another Article, Ordinance or statute, and any range whose span changed. An
  explicit `Article N Section M` resolves against Article N. With no map, nothing changes.

### 3.3 `build/build-adoption.sh <version> <meeting-date>`

The freeze. It checks its own gates (§6.1), then runs the release driver `build/build-release.sh`
in meeting mode (`ADOPTION_MODE=meeting`), against the previously adopted Code. The driver plans
the packet from the change determination (`czc_diff.py`, `release_plan.py`) and builds it into
`releases/<version>/`. The packet is whatever the plan lists; the kinds it can list are:

<!-- PACKET-KINDS -->
- `integrated` — the Town Meeting edition: integrated CZC, PDF + md, meeting-mode chrome (§4).
- `integrated-redline` — the integrated redline vs the previously adopted Code, PDF + md: full
  publication layout, prose marked inline, normalised per §3.2, mapped per §3.1.
- `standalone` — one per Article that changed **in substance**, PDF + md.
- `standalone-redline` — the matching per-Article redline, PDF + md.
- `use-table-changes` — the Use Table Changes memo, md + PDF; present only when district data moved.
- `summary` — the Summary of Changes. The driver generates a skeleton; a person finishes it by
  hand (plain language, no file/path/script references). `--render-summary` renders its PDF.
- `record` — `release-plan.json` and `ships.json`: what was planned and what shipped.
<!-- /PACKET-KINDS -->

`build-adoption.sh` then writes `frozen-from.json` (the source tree the packet was built from; §6.1).
An Article touched only by renumbering or cross-references ships no standalone; the Summary names it.

**The driver run directly is a proof, not a freeze.** `build-release.sh` in meeting mode has no
dirty-source check and writes no `frozen-from.json`, so `build-adopted.sh` cannot adopt what it
produced.

Nothing here forks the builder: the leaves reuse `build-full-czc.sh` and `build-standalone.sh`
through their `SRC_DIR`/`OUT_DIR` seams.

**It prints the substantive-change breakdown by article before it finishes**, so the changes going
into the packet can be reviewed before the packet exists rather than at the meeting.

### 3.4 `build/build-adopted.sh <version> <adoption-date>`

After the vote.

**It renders from the tagged Meeting-edition source, not the working tree.** This is the central
safety property: the adopted document structurally cannot contain anything the voters did not see.
The working tree may have moved on; it is not consulted.

It then asserts the rendered body is **byte-identical** to the Meeting edition, differing only in
chrome (§6.2).

### 3.5 Previously adopted version

For the first adoption (v1.0), the previously adopted version was **`v0.1-baseline`** — the transcription of the
Code adopted November 3, 2020 and amended through March 24, 2025. That tag exists for exactly this
purpose; its own Summary states: *"All subsequent drafts diff against this v0.1-baseline rather than
against the PDF, giving cleaner redlines and clearer change tracking."*

After `v1.0` is adopted, **`v1.0` becomes the previously adopted version** for the next cycle. The
map in §3.1 is then reset to identity (no renames pending), and re-populated only if a future
amendment renumbers articles again. Concretely, five fields change: `baseline_version` to the new
adoption, `article_numbers` and `files` to identity, and `new_at_this_adoption` and
`not_text_comparable` emptied.

**Performed September 14, 2026**, the night Town Meeting adopted v1.0: `baseline_version` is now
`v1.0`, every map is identity, and `baseline_selfcheck.py` reports **0 marked lines** comparing v1.0
against itself. The pre-rollover map is kept as `build/tests/fixtures/adoption-map-v0.1-baseline.json`;
the baseline-redline tests (renumbering, renamed files, not-text-comparable articles, the 151-line
breakdown) pin it through the `ADOPTION_MAP` environment variable — a test seam in
`build/adoption_map.py` that no build sets — so that machinery stays covered while the shipped map
exercises none of it.

**Nothing performs that edit — it is done by hand, once, possibly years later.** So it is guarded
instead. `build/baseline_selfcheck.py` asserts the invariant that makes the map checkable at all:
**the baseline compared against ITSELF must mark zero lines.** `build-adoption.sh` runs it as a
precondition, before anything is built.

The guard exists because the halves fail differently. A stale `files` map already failed loudly —
`adoption_breakdown.py` refuses with "does not exist at v1.0". A stale `article_numbers` fails
**silently**: measured 2026-08-25 against the real `v1.0` tree, resetting `baseline_version` and
`files` but leaving the renumbering at 3→4…8→9 reports **308 substantive changed lines comparing
v1.0 to itself, and exits 0** — the old side's "Article 4" rewritten to "Article 5" against a new
side that says "Article 4". That is a warrant packet full of changes nobody made. A stale
`not_text_comparable` and a leftover null in `files` fail the same quiet way: Article 2 would render
unmarked at every future meeting, and Article 3 would be marked "NEW at this adoption" forever.

The check is **dormant while the baseline is not an adoption version**. `v0.1-baseline` is
deliberately not one (§6.1): it is the 2020 Code in its own formatting conventions, so normalising
it legitimately changes it and a self-comparison there is meaningless. The guard therefore arms
itself at the rollover — exactly when the mistake becomes possible.

---

## 4. Chrome, in three modes

Every element that currently says "draft" and what it becomes.

| Element | Draft | Town Meeting edition | Adopted |
|---|---|---|---|
| Cover bar | `INTEGRATED DRAFT — NOT ADOPTED` | `TOWN MEETING EDITION — NOT YET ADOPTED` | *(bar removed)* |
| Cover line 2 | `vX.Y-draft · includes proposed Article 3: Thoroughfares` | `v1.0 · for adoption at Town Meeting, <meeting-date>` | `v1.0 · Adopted <adoption-date>` |
| Cover line 3 | `Generated <date> … For review only — not a certified copy.` | `Frozen <date>. The text put before the voters. Not a certified copy.` | `Adopted <adoption-date>, amending the Code adopted November 3, 2020.` |
| Page footer | `Draft vX.Y-draft` | `Town Meeting Edition v1.0` | `Adopted: <adoption-date>` |
| Exhibit 3.1 / 3.2 banner | `DRAFT — Types auto-derived from an approximate trace of the District Map; not yet reviewed or adopted.` | Provenance note **plus** a not-yet-adopted marker (§4.2) | Provenance note only, draft language dropped (§4.2) |

Exact wording of cover lines is a drafting matter and may be revised; the **states** and what each
must not claim are normative.

### 4.1 Footer mechanics

`build-full-czc.sh` currently overrides every article's `footer-date` with `Draft $VERSION`
(lines 210/223/229). Adoption mode changes only that string. Per-article frontmatter
`footer-date` values are untouched.

**Note a latent inconsistency:** `article-03-streets-roads-driveways.md`'s own frontmatter still
reads `"Draft v0.2-draft"`. It is always overridden by both the integrated and standalone builders,
so it never reaches a page — but it is stale and should be corrected while this work is open.

### 4.2 Exhibit banners

`inventory.json`'s `_meta.banner` drives both exhibits. At adoption the draft language goes and a
provenance note remains: the classification's derivation and the fact that recorded field values are
approximate.

**The Meeting edition's exhibits keep a not-yet-adopted marker of their own**, rather than relying
on the cover. Exhibit 3.1 runs to five pages and Exhibit 3.2 is a full-page map; these are precisely
the pages someone photocopies or projects on their own, detached from the cover that carries the
status. A page that can be separated from its context must carry its own.

The provenance note is accurate and must stay: the district geometry is still a ~0.77-IoU
approximation pending the contractor's shapefile. §5.C.2 makes the Type column binding regardless, and §5.C.3 already permits
the Town to update reference information without amendment — so a note about basis creates no
conflict with adopted status.

### 4.3 The structural-changes note

The Meeting-edition redline opens with a stated structural summary, before any marked text:

- Article 3 *Thoroughfares* is new.
- Every Article after 2 shifts up by one (old 3→4, 4→5, 5→6, 6→7, 7→8, 8→9).
- Cross-references throughout were renumbered accordingly and are **not** individually marked.
- **Article 2's district standards are now rendered as full-page spreads** rather than prose. Their
  text is unchanged in substance but is not markdown any more, so it is shown at current state and
  **not** marked — the same treatment every figure in this redline receives (§1.2b). A reader must
  not infer from the absence of marks that Article 2 was untouched, nor from a text diff that it
  was deleted.

This is what makes suppressing 126 renumbering marks honest rather than concealing: the reader is
told the fact once, plainly, instead of encountering it 126 times (the count at the v1.0 adoption).

`build/structural_note.py` writes the note in two scopes.

- **Code scope** (the integrated redline): one page on the verso facing the cover. Every sentence
  that names an Article, a count or a "new" status is generated from the adoption map, so under the
  identity map it claims nothing is new, unmarked or renumbered. It names every data-generated page
  (district pages, Type plates, Exhibits 3.1 and 3.2, District Maps) as shown unmarked. It refuses
  rather than spill onto a second page.
- **Article scope** (a standalone redline, `--scope article:N`): written from the change
  determination. It names the kinds of change, never line counts, and each heading and table by
  name. Markdown wording is used for the `.md`.

The notes are truthful by construction: they say only what the determination and the map show.

---

## 5. What this does not do

- **No warrant article text, certificate of adoption, or attestation page.** Those have statutory
  form requirements this project has not established. If they are needed, they are a separate
  decision for town counsel and get their own spec.
- **No change to drafting.** `build-full-czc.sh`, `build-standalone.sh`, and the per-version
  redline behave exactly as they do today for decimal versions.
- **No automatic adoption.** `build-adopted.sh` is run by a human after a vote, with the real date.

---

## 6. Gates

This produces a legal instrument. Each gate **refuses**; none warns.

### 6.1 Gates

Each bullet names the script that runs the gate and a literal line from it: the refusal message,
or the step that makes the refusal. A test finds each line in that one script, outside comments.

<!-- GATES -->
- `build-adopted.sh` — `build/version_state.py" --require adoption "$VERSION"` — version state, both
  directions. A decimal is refused where adoption is required, and a whole number where draft is
  required (`build-adoption.sh` refuses anything but `vN.0`; `build-release.sh` refuses a whole
  number in draft mode and a decimal in meeting mode). Whole numbers are adopted law, unfakeably.
- `build-adoption.sh` — `build/baseline_selfcheck.py" || exit 1` — the baseline compared against
  itself must mark zero lines (§3.5). Run before anything is built.
- `build-adoption.sh` — `Refusing to freeze: source/ has uncommitted or untracked changes.` — the
  dirty-source refusal.
- `build-adoption.sh` — `Refusing to freeze: $V is set in the environment.` — an inherited build
  override is refused, never dropped. The freeze records the tree of `source/`.
- `build-release.sh` — `it would change what the leaves build. Unset it.` — the same refusal in the
  driver. It also refuses `ADOPTION_BASELINE` and `ADOPTION_EVENT_DATE` in draft mode.
- `build-release.sh` — `the derived section map failed its selfcheck.` — the derived section map
  must pass `section_map.py selfcheck` before it is used.
- `build-release.sh` — `the release gate refused; nothing was released.` — `release_gate.py` refuses
  a missing, empty or unplanned artifact, and a pagination fault (§6.5).
- `build-adopted.sh` — `THE '$VERSION' TAG NO LONGER POINTS AT THE FROZEN SOURCE.` — the provenance
  gate: the tag's `source/` tree must equal the tree recorded in `frozen-from.json`.
- `build-adopted.sh` — `ADOPTED BODY DIFFERS FROM THE TOWN MEETING EDITION.` — the content-identity
  gate (§6.2).
- `build-adopted.sh` — `adopted: draft chrome found in the adopted MARKDOWN` — the draft-residue
  gate on the `.md` (§6.3); `adopted_residue.py` also scans the PDF text and file names.
- `build-adopted.sh` — `build/pdf_recap.py" "Adopted edition=` — fails on an unreadable or
  zero-page PDF (§6.5).
<!-- /GATES -->

### 6.2 Content-identity gate

The adopted edition's body must be **byte-identical** to the Meeting edition's, chrome excepted.
Asserted by comparing the rendered markdown (not the PDF, which carries timestamps) — the same
reasoning that made `content_sha256` hash markdown in the permit-review app.

**"Body" means the combined markdown with YAML frontmatter blocks stripped.** This is not a
technicality: each Article's frontmatter carries a `footer-date:` line, which is chrome and differs
by state by design. Comparing the raw file would fail on every run for the one reason that does not
matter. The integrated markdown carries **nine** frontmatter blocks, one per Article.

Since Wave 4b the body is **mode-independent by construction**: `build/integrated_md.py` writes it
with no title, provenance or mode line, and no build comments or raw Typst, so the meeting and
adopted editions' bodies are the same bytes. The gate confirms it; it no longer relies on a lucky
match.

### 6.3 Draft-residue gate

**No draft CHROME survives anywhere in the adopted PDF or the adopted `.md`** — checked by
extracting text from the rendered document and reading the markdown bytes, not by asserting the
substitution ran. The `.md` is scanned for chrome only; the damage check below stays on the PDF text.

**The gate must target the chrome strings, not the bare word.** The Code's own adopted text uses
"draft" substantively: Article 8 §979 reads *"The Planning Board, or its designnee, drafts the
official map of the Town of Newcastle."* A blanket search for "draft" would fail on the Town's own
words, and the natural fix under time pressure — deleting the gate — is worse than never having it.

So the gate checks for the specific chrome phrases (`INTEGRATED DRAFT`, `TOWN MEETING EDITION`,
`NOT ADOPTED`, `NOT YET ADOPTED`, `For review only`, `Draft v`) and the footer pattern, and asserts
the substantive occurrences are **still present and unchanged** — a substitution that damaged the
Code's own text would be a far worse failure than one that left a banner behind.

### 6.4 Redline gates

- The number of marked substantive changes is **reported**, per article and in total.
- Every article file in the map resolves on both sides; an unmatched file is an error, never a
  silent 100%-new rendering.
- The normaliser's conservatism tests pass (§3.2).

### 6.5 Layout gates

Parity holds (logical page == physical page, one constant offset). `release_gate.py` **refuses**
pagination that is not consistent: the printed-minus-physical page offset must be even and the same
throughout. `pdf_recap.py` fails on an unreadable or zero-page PDF. Page counts and blank counts are
a **report**, not a gate.

---

## 7. Open items

- **At the v1.0 adoption, the 243 substantive lines had not been reviewed.** They accumulated across 24 drafts and are
  concentrated in Article 9 Definitions (115 lines — the v0.21 alphabetical merge of 25 Article-3
  terms) with the remainder scattered across Articles 4–8. They should be read before the packet is
  assembled, and `build-adoption.sh` printing the breakdown is what makes that possible.
- ~~**The stale `footer-date` in Article 3's frontmatter** (§4.1).~~ **FIXED** (commit `07e82db`).
- **Typos inherited from the adopted Code.** `designnee` (×2) and `extentions` (×1) appear in the
  baseline Administration article and have been carried faithfully through 24 drafts. Adoption is
  the moment at which correcting them would be legitimate, since the Board is voting on the text.
  Handled exactly as the "Conditions of Law" question in the permit-review app: **surfaced, never
  silently fixed.** Correcting the Town's own adopted wording is the Board's decision.
- ~~**The adopted cover contradicts itself on dates.**~~ **RESOLVED 2026-08-25 — Ben chose (b),
  overprint, scoped to `adopted` mode only.** The cover reuses the baseline scan art, whose lower
  block reads "AMENDED THROUGH: MARCH 24, 2025", while the `adopted` banner above it reads "Adopted
  <date>, amending the Core Zoning Code adopted November 3, 2020" — two competing claims about
  currency on the cover of a legal instrument. `build-cover.py` now masks that one line and reprints
  it as **"AMENDED THROUGH: <adoption date>"** in adopted mode. *Revised Wave 4b:* in **every** mode
  the line is now generated from `baseline_amended_through` in the adoption map, so draft and meeting
  covers state the baseline's amended-through date (September 14, 2026 under the v1.0 map) rather than
  the scanned March 24, 2025. The two lines above it (EFFECTIVE / ADOPTED) stay as they are in every mode — the Code
  really was adopted November 3, 2020, and this edition amends it rather than replacing it.
  Implementation notes: the line is scanned art with **no text layer**, so a text-only assertion
  cannot see the stale line and would pass with the mask deleted — the gate is a **pixel** test that
  renders with a short adoption date (leaving the stale line's left end uncovered by the
  replacement) and asserts zero ink there, with meeting mode as the positive control. Verified by
  mutation: both deleting the mask and mis-positioning it fail the test. Geometry was measured off
  the baseline at 600 dpi (ink x 388.8–563.9, cap-top 722.9, baseline 731.9); the replacement is
  Barlow Condensed at 12.86 pt with +0.777 pt tracking, matching the scanned line's cap height and
  letterspacing, in the sampled scan ink (96,100,101).
- ~~**Whether the adopted edition ships a standalone Article 3 at all.**~~ **DECIDED (D5): adopted
  releases ship no standalones.** Only the integrated Code is adopted; `build-release.sh` refuses
  adopted mode, and `build-adopted.sh` builds the integrated edition alone.
- **v1.0 cannot be re-adopted.** Re-adopting v1.0 is impossible (Wave 4b, ruling 10), and no code
  works around it. `build-adopted.sh` renders the v1.0 tag's `source/` with *today's* builders and
  compares the result with the committed `releases/v1.0` Town Meeting `.md`. The old assembler
  wrote that file (raw Typst blocks, HTML comments, "See the Integrated Draft PDF"); today's
  integrated `.md` body differs, so the identity gate refuses. The tag's Article 3 frontmatter also
  still reads `footer-date: "Draft v0.2-draft"`, which the residue scan of the adopted `.md`
  refuses. v1.0's adopted edition already exists (`releases/v1.0-adopted`).
