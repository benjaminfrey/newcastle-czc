# Summary of Changes — v0.20-draft

**Release type: Legal-drafting / editorial — define "Character" and remove it from the
binding standards.** The word *character* is a conclusory term with no measurable
referent, which makes any provision that *relies* on it a target for a "void for
vagueness" challenge. This release does two things: (1) adds an Article 9 definition that
anchors "Character" to measurable physical attributes (and expressly excludes ownership,
occupancy, and socioeconomic factors), and (2) replaces the word in the places where it
was doing **operative** work — classification tests and approval criteria — with the
concrete form-based terms the Code already uses ("built form," "development pattern,"
"nature"). Aspirational *purpose* statements keep the word, now anchored by the
definition.

No change to any dimensional standard, Type, district, or the classification data.

**Compares against:** [v0.19-draft](../v0.19-draft/) (immediate prior) and
[v0.1-baseline](../v0.1-baseline/) (cumulative). The vs-v0.19 redline is 8 passages.

## 1. New defined term (Article 9)

> **Character.** The combined effect of the physical and design attributes of an area —
> including the form, scale, massing, and placement of buildings; the pattern of lots,
> blocks, and streets; the relationship of buildings to the street and to one another;
> and the streetscape and landscape — that distinguishes the area and that the form-based
> standards of this Code are intended to express. As used in this Code, character refers
> to these physical and design attributes; it does not refer to the ownership or
> occupancy of property, the identity of property owners or occupants, or the
> socioeconomic composition of an area.

The exclusion clause is deliberate: it forecloses reading "character" as a proxy for who
owns or occupies property (a fair-housing safeguard) and ties the term to the Code's own
measurable form standards.

## 2. Operative uses replaced (8 passages)

Where "character" carried binding weight, it is replaced with the concrete term:

| Location | Before → After |
|---|---|
| Art. 3 §5.D.1.b (Classification Rubric) | "**Built character test**" → "**Built-form test**"; sentence reworded to *built form* / *form* |
| Art. 3 §5.D.1.e (Tie-breaker) | "long-term **character** intent" → "intended long-term **development pattern**" |
| Art. 3 §5.E.1.b (Reclassification) | "built **character** has demonstrably changed" → "built **form** …" |
| Art. 3 §6.C.2 (Type assignment) | "intended built **character**" → "intended built **form**" |
| Art. 3 §6.D.1.c (Components & widths) | "the **character** of the abutting District" → "the built **form** of the abutting District" |
| Art. 3 §14.E.1 (Reclassify to resolve nonconformity) | "current and likely future **character**" → "… future built **form**" |
| Art. 8 (Written interpretations) | "**character** of the development proposal" → "**nature** of the development proposal" |
| Art. 8 (Special-permit criteria) | "of a **character** that does not produce…" → "of a **nature** that does not produce…" |

## 3. Deliberately kept (now anchored by the definition)

- **Purpose / intent statements** throughout (Articles 1–7) — non-binding goals, so the
  vagueness concern doesn't bite; the definition supplies meaning if ever read as operative.
- **"form and character of a thoroughfare"** — the form-based-code pairing (Art. 3 §1, §4,
  §5, and the Thoroughfare Type definition; the "Character" panel on each Type plate).
- **"rural character"** — a policy term of art tied to the Comprehensive Plan; retained in
  the District purposes, the Type pages, and the §6.D.1.4 balancing factor.

## 4. ⛔ Deliberately NOT changed — flagged for town counsel

- **Variance standards (Art. 8).** "will not alter the **essential character of the
  locality**" and "undesirable change in the **character of the neighborhood**" appear to
  track **30-A M.R.S. §4353(4)** (the statutory variance test). An ordinance must mirror
  the enabling act, so these are left verbatim — **confirm with counsel before any change.**
- **Human-services-facility criterion (Art. 7).** "will not alter the essential nature
  and **character of the community**" — left as-is pending counsel, because rewording
  approval criteria for this use class can implicate the Fair Housing Act.

## 5. Out of scope (no change)

- **"characteristic(s)"** and **"characterized by"** (e.g., "site characteristics,"
  "the D2 district is characterized by…") — a different, concrete word; left alone.
- The **typographic** "character" in the Sign definition (a glyph) — left alone.
- `source/legacy/article-02-districts.md` — superseded, not in the build; not touched.

## 6. Deliverables

- `Newcastle CZC (Integrated Draft v0.20-draft).pdf` / `.md` — 118 pp, clickable TOC.
- `Article 3 Thoroughfares (Standalone v0.20-draft).pdf` / `.md` — 27 pp.
- `Redline — Full CZC v0.20-draft vs v0.19-draft.pdf` — the 8 passages above.
- `Redline — Full CZC v0.20-draft vs v0.1-baseline.pdf` — cumulative.

## 7. Verification

- Integrated **118 pp / 3 blank**; standalone **27 pp / 0 blank** — **identical to v0.19**
  (text-only change; no build, layout, or `.typ` code touched). TOC re-derives; **188**
  GoTo links.
- Direct `v0.19 → v0.20` markdown diff = exactly the 9 intended edits (8 replacements +
  the new definition), no collateral changes.
- The two variance lines and the human-services criterion confirmed **unchanged**.
