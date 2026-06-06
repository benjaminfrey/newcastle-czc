# Summary of Changes — v0.19-draft

**Release type: Integrated-PDF output improvements — fewer blank pages + a clickable
Table of Contents.** No content or regulatory change: the integrated markdown is
byte-identical to v0.18, and the standalone Article 3 is unchanged (it already flowed
continuously and has no TOC). Both are rebuilt under the v0.19 label.

**Compares against:** [v0.18-draft](../v0.18-draft/). The vs-v0.18 redline is empty —
these changes are in the PDF structure (page assembly + link annotations), not the text.

## 1. Blank pages removed (10 → 3)

`build-full-czc.sh` previously padded every odd-length Article with a trailing blank so
the next Article opened on a recto (the bound-book convention). The build now **threads
the true running page offset** instead, so the body flows continuously and the seven
inter-article blank pages are gone. The integrated PDF went **125 → 118 pages**.

**Three structural blanks remain**, by design:
- **Article 2 (×2):** the 13 district pages are 2-page spreads that start on a verso (an
  internal `pagebreak(to:"even")` lands them there); a parity pad keeps that alignment.
- **Front matter (×1):** the blank between the cover and the TOC keeps the TOC's margins
  correct and the body numbered from a recto.

Side effect: those two body blanks occupy page-number slots without printing them, so the
printed numbering skips a couple of values around Article 2 (internally consistent — the
TOC matches). Removing the last three would require reworking the district-spread layout;
deferred by choice.

## 2. Clickable Table of Contents

New `build/toc_links.py` (run at the end of the integrated build) adds an internal GoTo
link from every TOC row to its page — **188 links**. It re-derives everything from the
rendered PDF (each row's "NAME … <page>" + the front-matter page count), so it is robust
to layout changes. Spot-checked: each Article → its opener, the ten Type plates → their
own pages (S1 → the S1 plate, R3 → the R3 plate, …), Definitions → Article 9.

## 3. Deliverables

- `Newcastle CZC (Integrated Draft v0.19-draft).pdf` / `.md` — 118 pp, clickable TOC.
- `Article 3 Thoroughfares (Standalone v0.19-draft).pdf` / `.md` — unchanged from v0.18.
- `Redline — Full CZC v0.19-draft vs v0.18-draft.pdf` — empty (PDF-structure only).
- `Redline — Full CZC v0.19-draft vs v0.1-baseline.pdf` — cumulative (unchanged counts).

## 4. Verification

- Integrated: 118 pages, **3 blank pages** (was 10), **188 TOC GoTo links**.
- Links resolve to the correct pages (exact-row spot-checks across articles, plates, and
  sub-sections).
- Body chrome stays correct (page numbers / verso-recto margins track the physical page,
  logical == physical); Article 2's district spreads keep their verso alignment.
