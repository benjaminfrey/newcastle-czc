# Adoption Release — Specification

**Status:** design, approved 2026-08-24. Not yet implemented.
**Scope:** `build/build-adoption.sh`, `build/build-adopted.sh`, `build/normalize_for_diff.py`,
`build/adoption-map.json`, and adoption-mode changes to `build/build-cover.py`,
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

### 3.2 `build/normalize_for_diff.py`

Normalisation applied to **both sides** before diffing. Each rule is separately testable and
separately justifiable:

| Rule | Why it is not substantive |
|---|---|
| Heading letter case (`### A.` → `### a.`) | The Typst template styles headings; case in source never reaches the page |
| Cross-reference renumbering (via §3.1) | The renumbering is real, but is stated once as a structural change (§4.3) rather than marked 126 times |
| Paragraph re-wrapping | Line breaks in markdown source do not survive rendering |

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

### 3.3 `build/build-adoption.sh <version> <meeting-date>`

The freeze. Produces, into `releases/<version>/`:

1. **Town Meeting edition** — integrated CZC, PDF + md, adoption-mode chrome (§4).
2. **Redline vs the previously adopted Code** — full publication layout, prose marked inline,
   normalised per §3.2, mapped per §3.1.
3. **Summary of Changes vs the previously adopted Code** — hand-written, per the existing house
   rule: plain language, no file/path/script references.
4. **Standalone Article 3** — PDF + md, as every release ships today.

It reuses `build-full-czc.sh` through the existing `SRC_DIR`/`OUT_DIR` seams. It does not fork the
builder.

**It prints the substantive-change breakdown by article before it finishes** (§1.2's 243 lines, by
file), so the changes going into the packet can be reviewed before the packet exists rather than at
the meeting.

### 3.4 `build/build-adopted.sh <version> <adoption-date>`

After the vote.

**It renders from the tagged Meeting-edition source, not the working tree.** This is the central
safety property: the adopted document structurally cannot contain anything the voters did not see.
The working tree may have moved on; it is not consulted.

It then asserts the rendered body is **byte-identical** to the Meeting edition, differing only in
chrome (§6.2).

### 3.5 Previously adopted version

For this adoption, the previously adopted version is **`v0.1-baseline`** — the transcription of the
Code adopted November 3, 2020 and amended through March 24, 2025. That tag exists for exactly this
purpose; its own Summary states: *"All subsequent drafts diff against this v0.1-baseline rather than
against the PDF, giving cleaner redlines and clearer change tracking."*

After `v1.0` is adopted, **`v1.0` becomes the previously adopted version** for the next cycle. The
map in §3.1 is then reset to identity (no renames pending), and re-populated only if a future
amendment renumbers articles again.

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
told the fact once, plainly, instead of encountering it 126 times.

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

### 6.1 Version-state gates

- `build-adopted.sh` refuses a decimal version.
- `build-adoption.sh` refuses a version that is not `vN.0`.
- `build-full-czc.sh` refuses to stamp a whole number with draft chrome.

Together these make "whole numbers are adopted law" unfakeable rather than conventional.

### 6.2 Content-identity gate

The adopted edition's body must be **byte-identical** to the Meeting edition's, chrome excepted.
Asserted by comparing the rendered markdown (not the PDF, which carries timestamps) — the same
reasoning that made `content_sha256` hash markdown in the permit-review app.

**"Body" means the combined markdown with YAML frontmatter blocks stripped.** This is not a
technicality: the combined `.md` carries a per-article `footer-date:` line, which is chrome and
differs by state by design. Comparing the raw file would fail on every run for the one reason that
does not matter. Verified 2026-08-24 — the v0.24 combined markdown carries three such lines.

### 6.3 Draft-residue gate

**No draft CHROME survives anywhere in the adopted PDF** — checked by extracting text from the
rendered document, not by asserting the substitution ran.

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

Parity holds (logical page == physical page, one constant offset); page counts and blank counts
recorded for each artifact.

---

## 7. Open items

- **The 243 substantive lines have not been reviewed.** They accumulated across 24 drafts and are
  concentrated in Article 9 Definitions (115 lines — the v0.21 alphabetical merge of 25 Article-3
  terms) with the remainder scattered across Articles 4–8. They should be read before the packet is
  assembled, and `build-adoption.sh` printing the breakdown is what makes that possible.
- **The stale `footer-date` in Article 3's frontmatter** (§4.1).
- **Typos inherited from the adopted Code.** `designnee` (×2) and `extentions` (×1) appear in the
  baseline Administration article and have been carried faithfully through 24 drafts. Adoption is
  the moment at which correcting them would be legitimate, since the Board is voting on the text.
  Handled exactly as the "Conditions of Law" question in the permit-review app: **surfaced, never
  silently fixed.** Correcting the Town's own adopted wording is the Board's decision.
- **Whether the adopted edition ships a standalone Article 3 at all.** Once adopted, Article 3 is
  simply part of the Code; a standalone excerpt may be a convenience or may be a confusion. Not
  decided.
