# Release deliverables and build machinery — scoping document

Town of Newcastle CZC. Written 2026-10-07, read-only against `main` at `11cf4cf`.
Input to an implementation plan. Nothing here is built.

Every factual claim carries `file:line`. Anything I did not read or reproduce is marked
**INFERRED** with the command that would confirm it. Section 7 lists these together.

---

## 0. DECISIONS MADE (2026-10-07)

Settled by Ben Frey, Planning Board chair, on the recommendations in §6. The §6 entries are kept
below for their reasoning and consequences; where they conflict with this section, this governs.

| # | Decision | Effect |
|---|---|---|
| D1 | A redline `.md` is **plain markdown**, additions `**bold**`, deletions `~~struck~~` | Readable in any viewer, diffable in git, and permanent — PDFs are gitignored, so this is the redline that survives |
| D2 | The Article 2 standalone **carries a generated data appendix** of all thirteen districts | The deliverable named "Article 2" must contain the thing that changed; a pointer note is the floor, not the target |
| D3 | The fifth status code **ships separately from Right to Farm**; combination with another code is **illegal and raises a build error** until the Board rules otherwise | It is the only item that alters binding Code data; fail-safe default, `DECISIONS-NEEDED.md` entry per the D-0033 precedent |
| D4 | **Fix the Article 2 chrome defect now**, in source | Every future edition is correct; the adopted v1.0 PDF is gitignored build output and its markdown body is unaffected — but this is a change to source an adopted instrument renders from, recorded deliberately |
| D5 | Adoption releases **do not ship standalones** | The integrated Code is what the Town adopts; extracts do not govern, and each one would multiply the gate surface on a legal instrument |
| D6 | Cover facts are **generated from the baseline**, not hand-fixed | The cover is wrong today for v1.1-draft; generation stops it recurring. The date line is scanned art pinned by a pixel test — re-measure if the mask moves |
| D7 | `inventory.json` substance = **type, name, termini, ownership, right-of-way and traveled widths**; addresses, geometry, present use and districts are derived | Otherwise every GIS refresh reads as an amendment to Article 3 — address counts changed on all 214 segments between v0.22 and v0.24 |
| D8 | A **retargeted cross-reference is always substantive** | Retargeting changes which standard applies; accepted cost is shipping more extracts |

**Deferred, not decided.** Which Code governs an application pending when the next version takes
effect (counsel; the permit-review app pins a ruleset per case, so either answer is implementable).
Whether `frozen-from.json` should pin the renderer as well as the source — today an adopted tag
re-renders with whatever `build/` and `style/` are current, and no gate would notice the difference.

**Correction carried from the scoping, because it reset the priorities.** Section-renumbering
suppression buys **zero rendered marks** for the Right-to-Farm release: headings are never marked in
`--source` mode, and all fifteen cross-references into Article 7's sections target §1.G, which sits
before the insertion point. It is worth building to protect future text and to stop a false headline
number reaching the packet, but it is not what makes the redline readable and must not become the
critical path.

---

## 1. RECOMMENDATION

**Build the capabilities as seams in the existing machinery, derive the section map per release
instead of committing it, and put one refusing gate in front of the release.** The four existing
build scripts keep their signatures and their defaults; `build-standalone.sh` gains the same
`SRC_DIR`/`OUT_DIR` seams `build-full-czc.sh` already has, so a per-Article redline stages marked
source and runs the real builder rather than forking it; the section map is derived from the two
git refs being compared and passed as an explicit argument, so `build/adoption-map.json` and
`build/baseline_selfcheck.py` are not touched at all; and one new `build-release.sh` computes the
deliverable set, builds it into a staging directory, and moves it into `releases/<ver>/` only after
every promised file is verified present and non-empty.

**The strongest argument against it.** A committed section map would get the self-comparison
invariant for free: `baseline_selfcheck.py:87` calls `changed_line_count(text, text, amap=amap)`
and refuses any map that marks a line, which is exactly the check a section map needs. A derived
map gets no such guard — "derived cannot be stale" is true about staleness and silent about
*wrongness*. A section renumbered *and* retitled in the same release is a title-match the deriver
can mis-pair, and a mis-pair suppresses a real amendment in a warrant packet, which
`normalize_for_diff.py:21-23` names as the one failure the module cannot recover from. **So this
design owes the derivation its own build-time self-comparison** — derive against the old ref, apply
it to the old side, assert the old tree versus itself marks zero lines, wired into
`build-release.sh` as a precondition the way `baseline_selfcheck.py` is wired at
`build-adoption.sh:79`. That gate is component **P6** below and is not optional. Without it this
design trades a tested guard for an untested derivation on a legal instrument.

**What I am giving up by not committing the map.** A second reviewable record of the shift, and
reuse of a guard that already exists and is already trusted. I accept that because the cost of the
committed map is concrete and recurring: `baseline_selfcheck.py:87` refuses a legitimately
populated map (reproduced below), so committing the map *requires* redesigning that guard — and
the guard exists because a half-done rollover once reported 308 phantom changes and exited 0
(`build/ADOPTION-SPEC.md:208-225`). A committed map also adds ~64 hand-authored entries per
amendment and a second manual rollover field of exactly the kind that already failed silently once.

**And a fact that should reset everyone's priorities on this.** Section suppression buys **zero
rendered marks** for the Right-to-Farm release. Headings are never marked in `--source` mode:
`redline-text.py:552-553` drops a deleted heading and `:560-561` emits the new one verbatim. Every
cross-reference into Article 7's sections is `Article 7 Section 1.G` — 15 occurrences, all inside
`source/article-07-use-standards.md` itself, and §1 sits *before* the §3 insertion point, so none
of them move. The entire deliverable of section suppression this release is the operator's
pre-freeze breakdown number and the legacy `--full` renderer. It is worth building — it protects
future text and stops a false headline number reaching the packet — but it is **not** the reason
the redline is readable, and it must not be allowed to become the critical path.

---

## 2. COMPONENTS

Ordering within each component: purpose, invocation, inputs/outputs, tests (negative control
named), files touched, must-not-break.

### P1 — `build-standalone.sh` seams

**Purpose.** The single blocking gap. `build-redline-full.sh:166-168` redirects the integrated
build with `SRC_DIR=`/`OUT_DIR=`; `build-standalone.sh:23` hard-codes `SOURCE_DIR="$REPO_ROOT/source"`
and `:48` hard-codes `RELEASE_DIR="$REPO_ROOT/releases/$VERSION"`. Without the seams a per-Article
redline must either fork the builder or mark files inside `source/`, which is a destructive edit to
the Code.

**Invocation.** Positional args unchanged: `build-standalone.sh <article-NN> <version> [date]`.
New optional environment, each defaulting to today's value:
`SRC_DIR` (mirrors `build-full-czc.sh:32`), `OUT_DIR` (mirrors `:45`), `OUT_NAME_OVERRIDE`, and
`STANDALONE_FRONT_NOTE` (a PDF prepended as front matter — the disclosure carrier for P8).

**The front-note parity rule — one reading, stated once.** `build-standalone.sh:150` renders the
Article opener with a literal offset `0`, and the template keys chrome off
`here().page() + page_offset` (`style/czc-template.typ:108`, `:122`), choosing verso/recto with
`calc.even(pn)`. So for a note of K pages prepended to `PARTS` but **not** added to `OFF`: the
opener still prints "1", and physical page = printed page + K. Verso/recto chrome is then correct
only if **K is even**. The alternative — add K to `OFF` and render the opener at offset K — is also
parity-correct for any K, but the Article's first page then prints "K+1", which changes the
extract's pagination convention that `build-standalone.sh:10-11` documents as its contract
("the standalone numbers pages 1..N from the Article opener"). **Recommendation: uncounted, K
forced even, and the script refuses an odd-length note.** Two of the three candidate architectures
asserted both rules at once; they are mutually exclusive and the plan must pick one in writing.

**Tests.** (a) Default preservation: Article 7 built with no environment set produces the same
`OUT_NAME` and the same per-page extracted text as before the change — text, not bytes, because
byte-identity across two Typst builds is **INFERRED** (confirm with `cmp` on two consecutive
identical builds before writing an equality assertion). (b) With `SRC_DIR` at a copied tree and
`OUT_DIR` at `tmp_path`, nothing is written under `releases/` — this also lets
`test_footer_modes.py:33-35` stop `shutil.rmtree`-ing the real release tree. (c) A failed build
leaves no `.pdf` in `OUT_DIR` (move `mkdir -p "$RELEASE_DIR"` at `:49` below input resolution).
**NEGATIVE CONTROL:** prepend a **one-page** note and assert a named test fails on verso/recto
inversion — the build still exits 0 today, so without this control an odd note silently reverses
the binding margins of the whole extract and nothing notices.

**Touches.** `build/build-standalone.sh` (`:23`, `:48-49`, `:83`, `:110-111` PARTS/OFF init,
`:150`/`:164`/`:170` render_seg offsets); `build/tests/test_footer_modes.py:25,33-35,41-43`.

**Must not break.** Draft-mode output for Articles 1, 2, 3 and 7 — the three splice codepaths plus
the fast path. `build-adoption.sh:149` calls this script; its behaviour there must be unchanged.

---

### P2 — `czc_standalone_name` in `adoption-name.sh`

**Purpose.** `build-standalone.sh:83` composes `Article $ANUM $ANAME (Standalone $VERSION)` inline
with no mode component, while `adoption-name.sh:16` already solved this for the integrated name
("the filename is chrome too"). Three consumers already disagree: `build-adoption.sh:150`
hard-codes `"Article 3 Thoroughfares (Standalone $VERSION).pdf"`, and
`test_footer_modes.py:41-43` finds the file with `glob(f"Article {article} *.pdf")` and `next()`,
which will match a standalone *and* its redline and pick arbitrarily.

**Invocation.** Sourced, pure, no globals — the contract of the file it joins:
`czc_standalone_name <draft|meeting|adopted> <article-num> <article-name> <version> [redline]`,
printing the basename without extension, returning 1 on an unknown mode as `czc_integrated_name`
does.

**Tests.** (a) Draft mode is character-identical to the shipped
`releases/v1.0/Article 3 Thoroughfares (Standalone v1.0).md` basename. (b) The redline form differs
from the plain form for the same article and version. (c) A release dir's `Article N *` matches
exactly the files the release plan names and no more. **NEGATIVE CONTROL:** build a standalone and
a standalone redline into one directory and assert `test_footer_modes.py`'s lookup resolves the
intended one. It cannot today, so the test must fail before the lookup is made specific.

**Touches.** `build/adoption-name.sh`; `build/build-standalone.sh:83`;
`build/build-adoption.sh:150,252`; `build/tests/test_footer_modes.py:41-43`.

**Must not break.** `czc_integrated_name`'s output in all three modes — it names the adopted
instrument and `adopted_residue.py` checks it.

---

### P3 — HTML comments are structure in `redline-text.py --source`

**Purpose.** Two of the three candidate architectures describe this hazard wrongly, so the plan must
carry the reproduced version. I ran both cases read-only in the scratchpad.

*Inserted or edited marker — survives, but leaves a Typst span.* Adding
`<!-- TYPE-PAGES -->` to the new side produced
`` `#text(fill: rgb("#cc0000"))[\<!-- TYPE-PAGES -->]`{=typst} ``, and
`split-article-03.py` exited **0** — `:38` is `if marker in ln`, a substring test the wrapper does
not break, and the matched line is then dropped at `:76` (`body[:m1], body[m1+1:]`). So the split
succeeds and the span never reaches the page. **It is not fatal and it is not a wrong layout.**

*Deleted marker — resurrected, and the layout is silently wrong.* This is the real defect. With the
marker deleted from the new source, `emit_deleted_src` (`redline-text.py:551-554`) **strikes**
rather than drops it (HTML comments are not masked — `prepare_source:535-538` keeps them intact),
output `~~<!-- TYPE-PAGES -->~~`, and the splitter then split at a marker the new source no longer
has, exit **0**. The redline would splice the Type plates at a position the real document does not
have.

**Invocation.** No CLI change. Add `is_unmarkable_structure(ln)` beside `is_heading` (`:542`),
true for a line that is wholly an HTML comment; `emit_inserted_src` returns it verbatim,
`emit_deleted_src` returns `''` as it already does for headings, `_markable` excludes it. Separately
fix the integrated build's silent fallback: `build-full-czc.sh:155-158` appends the plates *after*
the prose when the marker is missing, where `build-standalone.sh:146-148` exits 1 — the same damaged
marker gives a fatal standalone and a quietly wrong integrated PDF. Make it refuse, naming the
marker.

**Tests.** A newly added marker survives bare and the split yields three non-empty segments; an
edited marker survives; a deleted comment produces no `~~<!--`; narrowness — a prose line containing
the text `TYPE-PAGES` without comment syntax is still marked. **NEGATIVE CONTROL (the one that
matters):** with the marker deleted from the new side, assert the marked file does **not** split —
this is the reproduced failure, and a test written against the "exit 2" premise would pass against
the real bug. Second control: damage the marker and assert `build-full-czc.sh` now exits non-zero.

**Touches.** `build/redline-text.py:542-562`; `build/build-full-czc.sh:155-158`;
`build/split-article-03.py` (message only).

**Must not break.** `--source` output for an unchanged marker line, and the TOC derivation —
headings stay unmarked (`:560-561`) because `toc_entries.py` and `toc_links.py` scan the built body.

---

### P4 — `redline-text.py --plain`

**Purpose.** The rule requires every redline in both `.pdf` and `.md`, and **no redline `.md` has
ever existed for anything.** `build-redline-full.sh:67-68` writes the combined markdown into a
`mktemp -d` deleted by the `trap`, and its content is full of
`` `#text(fill: rgb("#cc0000"))[...]`{=typst} `` spans (`:215`, `wrap_red` at `:233`) — pandoc+Typst
source, not readable markdown. `ls releases/v1.0 releases/v0.24-draft` shows only `— Redline.pdf`.
Since `releases/**/*.pdf` is gitignored, **the markdown redline is also the only form of a redline
that will exist in the repository a year from now**, which makes the format a provenance decision
(see Open Decision D1).

**Invocation.** One new flag on the existing parser, which already reads flags as a set
(`:601-602`). With `--plain`, rebind the wrappers before diffing: additions `**bold**`, deletions
`~~struck~~`, no Typst. A raw-Typst or fenced block emits the NEW block preceded by an explicit
`<!-- unmarked: regenerated figure -->` line, so the limitation is visible in the text rather than
inferred from its absence. Composes with `--source`, `--full`, `--digest`. Without the flag the
output is byte-identical to today.

**Tests.** (a) A fixture pair with and without the flag: the non-plain output is byte-identical to
the pre-change output; the plain output contains zero `{=typst}` and zero `rgb(`. (b) The plain
output round-trips through `pandoc -t gfm` without error. (c) The stderr tally (`:621`) is identical
under both flags — the flag changes rendering, never what counts as a change.
**NEGATIVE CONTROL:** assert no `{=typst}` substring in any shipped `.md` deliverable; with the flag
ignored this fails loudly instead of shipping Typst source to voters as markdown.

**Touches.** `build/redline-text.py` (`:207-215` raw-Typst inline, `:233` `wrap_red`, `:600-620`
main).

**Must not break.** The PDF path. Every existing call site passes no `--plain`.

---

### P5 — `redline-stage.sh`, the shared old-side loop

**Purpose.** `build-redline-full.sh:104-134` is the only place that knows the rc-3/rc-4 contract of
`redline_resolve.py` — rc 3 means an empty old side so the whole body marks as added, rc 4 means
old copied from new so the Article renders unmarked, anything else refuses
(`redline_resolve.py:8-19`). Those three mappings are the difference between a correct redline and
one reporting the whole Code as newly written; `adoption_map.py:6-9` records that exact measured
failure. Copied into a second script they will drift, and the drift is silent in the direction that
misleads.

**Invocation.** Sourced lib beside `adoption-footer.sh`:
`czc_redline_stage <src-dir> <stage-dir> <old-ver> <baseline-flag> <plain-flag> [basename ...]`.
Copies `src-dir` verbatim with the proven `cp -R "$SRC/." "$STAGE/"` pattern (`:69`) so native
`.typ`/JSON/SVG render at current state, then for each basename (default: every `article-*.md`)
resolves the old side and marks in place. Prints the per-file rc notices unchanged.

**Tests.** (a) `build-redline-full.sh` after the extraction produces the same page and blank count
on a known pair and the same `Marked N article markdown file(s)` line. (b) Called with one basename,
only that file is marked and the other eight are byte-identical to `source/`. (c) rc 3 and rc 4 each
exercised with a synthetic map. **NEGATIVE CONTROL:** a basename whose old side cannot be resolved
must exit non-zero and leave the stage byte-identical — no half-marked tree.
`redline_resolve.py:86-88` already refuses; the extraction must not swallow it.

**Touches.** `build/build-redline-full.sh:100-134` (replaced by a call); new `build/redline-stage.sh`.

**Must not break.** The integrated redline on the `v1.0` → working-tree pair, and the
`ADOPTION_BASELINE=1` path.

---

### P6 — `section_map.py`: derived, ref-scoped, never committed — **plus the self-comparison gate**

**Purpose.** Section suppression needs a map, and the obvious home is the worst one. I reproduced
the conflict read-only: with a scratch map populated `7→8, 8→9, 9→10` selected through the
`ADOPTION_MAP` env seam, `baseline_selfcheck.py` printed
`adoption-map.json has not been rolled over for v1.0:` and listed 7 articles (Article 7 = 34 phantom
lines) and exited **1**. The shipped identity map exits 0 with `0 marked lines`.
`build-adoption.sh:79` runs the check *before* the `:92` dry-run exit, so a map legitimately
populated for the next amendment is refused as "not rolled over". A derived map avoids this
entirely: `adoption-map.json`, `adoption_map.py` and `baseline_selfcheck.py` are **not touched**.

**Invocation.** `section_map.py derive <old-ref> [--new-dir DIR] --out PATH` and
`section_map.py check <PATH> --old-ref R`. Derivation reads each Article's headings at `<old-ref>`
via `git show` and in `--new-dir` (default `source/`), matches on **normalised heading title** —
not a regex over numbers, which is what makes it conservative — and maps old→new **only** for a
pure renumbering: identical title, different number, unchanged relative order. A retitled, added,
deleted or reordered section is **not** mapped; it is reported and stays fully visible as a real
change, and below a similarity floor the command exits non-zero and demands a hand entry. The map
records `for_old_ref`, `for_new_tree` and per-article `{old: new}`; `check` refuses a map whose
`for_old_ref` differs from the ref it is applied to — closing the real hazard that nothing today
validates `OLD_V` against `adoption-map.json`'s `baseline_version`, which is used only in a message
at `redline_resolve.py:70`.

**`section_map.py selfcheck <PATH> --old-ref R` is the gate this architecture owes.** It applies the
derived map to the old side and asserts the old tree compared against **itself** marks zero lines —
the same invariant `baseline_selfcheck.py:87` enforces for the article map, run at build time, not
only in pytest. `build-release.sh` (P13) runs it as a precondition and refuses on non-zero.

**Inputs/outputs.** Inputs: two git refs (or a ref and a directory). Output: one JSON file in the
release's staging dir, never under version control.

**Tests.** (a) Derived against `v1.0` with an unmodified tree: empty for all nine Articles.
(b) A synthetic Article 7 with one section inserted at §3 derives exactly **64** entries,
3→4 … 66→67 — `source/article-07-use-standards.md` has 66 `## N.` headings (verified by count), so
an insertion at §3 shifts §3–§66 = 64. The brief's "63" is the use-matrix row count, a different
quantity. (c) A renamed section at a shifted number is reported as unmapped, not mapped.
(d) `check` with a mismatched `for_old_ref` exits non-zero. (e) `selfcheck` on the real `v1.0` tree
reports zero. **NEGATIVE CONTROL:** a section whose number is unchanged but whose *text* changed must
not appear in the map; a second control where a section is deleted must leave the surrounding
numbers unmapped rather than guessing a shift. Remove the title-match requirement and both fail.
**Third control:** hand `selfcheck` a deliberately wrong map (an off-by-one shift) and assert it
exits non-zero — the gate must be able to fail, or it is decoration.

**Touches.** New `build/section_map.py` (imports `redline_resolve.git_show:37-40`, adding no new git
plumbing). **Nothing else.**

**Must not break.** `build/adoption-map.json`, `build/adoption_map.py`,
`build/baseline_selfcheck.py` — all three untouched by design, and the plan should state that as an
invariant so a later step does not quietly reach into them.

---

### P7 — the section rule in `normalize_for_diff.py`

**Purpose.** Suppress within-article section renumbering on the old side only, protecting the
operator's pre-freeze number and future cross-reference text. Built strictly to the module's own
doctrine (`:21-30`: narrow, separately tested in both directions, never semantic).

**Correct the premise.** Headings are never marked in `--source`
(`redline-text.py:552-553,560-561`), so 64 renumbered headings produce **no rendered marks**. The
damage is in `changed_line_count`, which at `:223-226` counts every `+`/`-` line of a raw
`unified_diff(..., n=0)` including headings, blanks, HTML comments and frontmatter — so a simulated
Article 7 insertion inflates the packet's headline number by roughly 128 phantom lines.

**Invocation.** `_renumber_sections(text, smap, article)` applied inside **both** `normalize()`
(the `is_baseline_side` branch, `:170-173`) and `normalize_old_side()` (`:195-197`) — both, because
`test_breakdown_and_render_paths_agree_on_the_real_corpus` pins their agreement and a rule in only
one breaks it. Signatures become `normalize(…, *, amap, is_baseline_side, smap=None)`,
`normalize_old_side(…, *, amap, smap=None)`, `changed_line_count(…, *, amap, smap=None)` —
**keyword-only with a `None` default, so every existing call site and every existing test is
unchanged, `baseline_selfcheck.py:87` keeps passing `amap` alone, and the draft path stays raw
unless a map is handed in.** `redline_resolve.py` gains `--section-map PATH --article N`, likewise
opt-in.

**Grammars, each separately tested.** `Section N`, `Section N.X`, `Section N.X.n`,
`Sections N, M, and K` (the list form is live at `source/article-03-streets-roads-driveways.md:26`
`(Sections 6, 7.F, and 14)`), `§N`, `Article N Section M`, `Article N §M`.

**Two hard guards.** A bare `Section N` resolves against the **containing** Article's sub-map — a
global regex is wrong here in a way `amap.renumber`'s `\bArticle (\d+)\b` (`adoption_map.py:67`) is
not, because "Article N" is globally unambiguous and "Section N" is not. And no rewrite after
`MRSA`, `M.R.S.`, `M.R.S.A.` or `Title`: the corpus carries
`source/article-08-administration.md:452` "Title 38, Section 480-B" and
`source/article-01-general.md:102` "30-A MRSA Section 4358". **Ordering:** the section rule runs
*before* `amap.renumber`, keyed on baseline article numbers, or `Article 7 Section 3` has its
article rewritten out from under the lookup.

Also wire `report()` (`:229-250`) into the build with a `sections` count. It is called today by
exactly one test (`test_normalize_for_diff.py:247`) and by no production code, while
`ADOPTION-SPEC.md:155` claims the module reports what it suppressed. A suppressed mark is honest
only if the reader can be shown the count.

**Tests.** Both directions for every grammar, following the existing
`test_renumbering_is_suppressed_on_the_baseline_side_only` /
`test_the_new_side_is_never_renumbered` convention: `Section 7.4.b` suppressed when the map says
3→4; `Title 38, Section 480` untouched; a bare `Section 12` in Article 3 resolves against Article
3's map and is not shifted by Article 7's; each element of `Sections 6, 7.F, and 14` mapped
independently; `changed_line_count` on the synthetic 64-section insertion drops to the real figure
while the rendered mark count is unchanged. **NEGATIVE CONTROL (the most important in this design):**
a real amendment to a section's *text* at a renumbered position — `shall`→`may` on the line
immediately after a renumbered heading — must still appear as a mark. Widen any grammar's anchor or
drop P6's title-match and this fails. **Second control:** `baseline_selfcheck.py` must still report
0 with the shipped map and no section map — proof the guard was left intact.

**Touches.** `build/normalize_for_diff.py:150-198,201-226,229-250`;
`build/redline_resolve.py:48-58,90-94`; `build/tests/test_normalize_for_diff.py`;
`build/tests/test_redline_resolve.py`.

**Must not break.** `changed_line_count` with no section map, the breakdown/render agreement test,
and the draft-to-draft raw path that `redline_resolve.py:18-19` guarantees and
`test_redline_resolve.py::test_without_baseline_flag_it_uses_the_same_filename` pins.

---

### P8 — `structural_note.py`: data-generated, and scoped to one Article

**Purpose.** Two jobs. (1) A standalone redline has nowhere to put its disclosure —
`build-standalone.sh:10-11` states there is no cover, and `REDLINE_CAVEAT` reaches the page only
through `build-cover.py` (`build-full-czc.sh:292`). For Articles 2 and 3, whose spreads, plates and
exhibits render unmarked, an undisclosed unmarked figure reads as "unchanged". (2) The existing note
hard-codes v1.0-era claims that become **false** at v2.0: `structural_note.py:93-96` asserts
"Article 3, Thoroughfares, is new"; `:98` heads a section "The articles after Article 2 were
renumbered" while `article_shift_sentence` at `:68` may say none were; `:102-106` asserts "Article
2 therefore carries NO marks". A v2.0 packet built unchanged asserts false facts about a legal
instrument.

**Invocation.** `structural_note.py OUT_PDF [--map PATH] [--old-label L] [--scope code|article:N]
[--section-map PATH] [--pad-to-even]`. `--scope code` is today's behaviour and today's output.
`--scope article:N` renders the per-Article note: which of that Article's units render unmarked
(read from `article-manifest.json`, not hardcoded), how many section renumbers were suppressed for
it (from P6's map and P7's `report()`), and a pointer to the Use Table Changes artifact when Article
2 is in scope. **Every sentence that names an article, a count or a "new" status is generated from
the map/manifest; the only literals left are grammar.** `--pad-to-even` appends a blank so P1's
even-length rule holds. The one-page ceiling (`:164-168`) stays for `--scope code` and becomes a
per-scope budget.

**Tests.** (a) `--scope code` with the pre-rollover fixture map produces the same page and the same
three disclosures `test_structural_note.py:52` already asserts. (b) With the **shipped identity
map** (baseline v1.0, nothing new, nothing non-comparable) the page must **not** say any article is
new and must **not** say any article is unmarked for being non-comparable. (c) `--scope article:2`
names the district spreads and the Use Table Changes artifact and renders an even page count.
**NEGATIVE CONTROL:** build the note from an identity map and assert the string `"is new"` is
absent. That string is unconditional today, so this test fails before the change — which is the
point: it is the test that stops a v2.0 packet telling voters Article 3 was just inserted.
**Second control:** build an Article 2 standalone redline with the disclosure suppressed and assert
a named test fails — an Article 2 redline with zero marks and no note is the single most
misleading artifact this design can produce.

**Touches.** `build/structural_note.py:60-200`; `build/build-redline-full.sh:152-160` (the caveat
likewise hard-codes "the Core Zoning Code adopted November 3, 2020 and amended through March 24,
2025" at `:156`); `build/tests/test_structural_note.py`.

**Must not break.** The integrated baseline note's position (the verso facing the cover, replacing
the front-matter blank so parity holds) and its page count, which
`test_structural_note.py:46,108,118` pins.

---

### P9 — ownership map in `article-manifest.json` + `manifest.py` readers

**Purpose.** The substantive-change determination has to know which files carry an Article's
standards, and nothing records that. The manifest's `data` field is the `--input data=` value for a
Typst unit, not an ownership declaration, and it is set for exactly one unit. Meanwhile
`source/article-02.typ:360` reads `article-02-data.json` and
`source/cross-section-plates.typ:275` reads `exhibits/cross-sections/types.json` — both carrying
binding content that neither the manifest nor any diff knows about. Without an ownership map a new
data file is silently uncounted, which is precisely the failure that already shipped (P10).

**Invocation.** Every Article 1–9 gets an entry (4–9 as `{prose, units: [], data_sources: []}`),
plus top-level `shared` and `ignored` lists. Each `data_sources` entry is `{path, compare}` where
`compare` is `json-keyed` (keyed leaf diff with a key spec), `binary-hash` (images — report
"changed (binary)" and require a recorded human call) or `generated-from` (naming the file it
derives from, so the ten cross-section SVGs count only through `types.json`, and an SVG change with
an unchanged `types.json` is flagged as an *anomaly*). `manifest.py` gains `data <NN>`, `articles`
and `owner <path>`; the four existing subcommands keep their output byte-identical.

**Format constraint, load-bearing.** `manifest.py:46-49` emits units as six pipe-delimited fields
and `build-standalone.sh:118` splits on `|`, while `markers` is read as exactly two words at
`:144` — so a field containing a pipe breaks the bash reader silently. `data_sources` gets its own
JSON-out subcommand rather than widening that line.

**Tests.** (a) `has`, `prose`, `markers`, `units` produce byte-identical output for all nine
Articles before and after. In particular `has 7` must still exit 1 — it tests
`entry.get("units")`, not `entry` (`manifest.py:34`), so adding an entry for Article 7 with an
empty `units` list keeps the pure-prose fast path. (b) `units 3` still emits exactly three
pipe-delimited lines in the same order. **NEGATIVE CONTROL:** a coverage test asserting every file
under `source/` is claimed by exactly one Article or named in `shared`/`ignored`. Drop a new
`source/foo.json` into a fixture tree and it must fail — this is the test that makes "silently
uncounted" impossible rather than unlikely.

**Touches.** `build/article-manifest.json`; `build/manifest.py:27-51`;
`build/build-standalone.sh` (reads only, unchanged).

**Must not break.** `build-standalone.sh`'s three codepath selections, especially the
`has`-exits-1 fast path for Articles 4–9.

---

### P10 — `czc_diff.py`: the substantive-change determination

**Purpose.** The rule turns on "changes to that Article's own standards, definitions or data", and
the only instrument today — `adoption_breakdown.py:84` via `changed_line_count` — is markdown-only,
driven by the nine `.md` files in `adoption-map.json`, and blind to the native data.

**The false zero is not hypothetical; it already shipped.** `git diff --numstat v0.24-draft v1.0 --
source/` shows `article-02-data.json` at **294 added / 24 removed** while
`article-02-prefatory.md` **does not appear in the diff at all**. So the breakdown reports Article 2
at zero lines across a release whose Article 2 data changed substantially, including one use cell.
Commit `13b2a50`'s own message records the consequence. On a Right-to-Farm release, which edits all
thirteen district use tables, a text-only count would call Article 2 unchanged.

**Invocation.** `czc_diff.py --old <ref> [--new-ref REF] [--section-map PATH] [--article N]
[--json PATH]`. Per Article, four independent counts and a proposed verdict:
- `prose` — normalised markdown lines after stripping blanks, HTML comments and frontmatter (a new
  `substantive_line_count`, leaving `changed_line_count` untouched so its agreement test stays
  valid).
- `heading` — added, deleted or retitled sections, reported here **precisely because the redline can
  never mark them** (`redline-text.py:552-553,560-561`).
- `table` — changed raw-Typst table blocks, which render unmarked (`emit_inserted_src:559`).
- `data` — changed leaves per `data_sources`, keyed.

**The Article 2 key, verified by reproduction.** `source/article-02-data.json` is a 13-record list
whose `code` field is **not** unique — seven records all read `SD`, so the key must be
`code + name`. Use cells live under `use_col1`/`use_col2` → `entries` as `[label, code]` pairs. I
built that keyed index read-only: **819 cells**, status counts
`{'': 450, 'u': 218, 'sp': 58, 'rc': 52, 'ex': 40, 'rc sp': 1}`, and the keyed diff
v0.24-draft → working tree returns **exactly one changed cell**:
`(('D3','NEIGHBORHOOD BUSINESS'), 'COMMERCIAL GOODS', 'Retail & Service, General')` `rc` → `rc sp`,
with nothing added or removed. That matches commit `13b2a50` and is the calibrated positive control.
`matrix` is **null** for CONSERVATION, CAMPUS and MARINE, so a positional differ crashes on them.

**It proposes; it never finalises.** Verdict is `SUBSTANTIVE` if any of the four counts is nonzero,
else `RENUMBER-ONLY` with the suppressed-reference count, else `UNCHANGED`. P13 writes
`releases/<ver>/ships.json` from it; an operator may add a per-Article
`{"override": {"verdict": …, "reason": …, "by": …}}`, and the driver **refuses an override with an
empty reason** and prints every override it honoured. Nothing moves an Article between the lists
silently in either direction.

**Tests.** Positive controls on real tag pairs, the only way to know the instrument works:
v0.24-draft → v1.0 must report Article 2 `data` nonzero including that one cell (it is zero today),
and Article 3's inventory type changes; `v1.0` vs `v1.0` must report all four counts zero for all
nine Articles for every comparator. A blank-line-only edit scores 0 where `changed_line_count`
scores 1. A table-only edit scores `table` 1 and `prose` 0 and must still come out `SUBSTANTIVE`
even though the redline will show no marks. **NEGATIVE CONTROL:** flip one use status in a fixture
copy of `article-02-data.json` and assert exactly that one cell is reported. **Second control:**
remove the `data_sources` wiring and assert the Article reports 0 and a named test fails — "Article
2 reports zero" is the exact shape of the failure that already shipped.

**Touches.** New `build/czc_diff.py` (imports `manifest.py`, `normalize_for_diff.py`,
`redline_resolve.git_show`); `build/adoption_breakdown.py` left intact in this step and later
re-expressed as a thin caller.

**Must not break.** `adoption_breakdown.py`'s exit-code contract and its "fix the map" messages —
`build-adoption.sh:89` depends on them.

---

### P11 — `use_table_changes.py`: the Use Table Changes artifact

**Purpose.** Article 2's district standards and use tables live in `article-02-data.json`, read at
`article-02.typ:360`. No redline path can see them: `build-redline-full.sh:69` copies `source/`
verbatim and only `article-*.md` is rewritten, so the spreads render at current state, unmarked —
and in baseline mode Article 2 is forced unmarked via rc 4 (`:121`). The Summary says in prose what
moved, which is how a single changed use cell reached an adopted Code with no reader able to catch
it.

**Invocation.** `use_table_changes.py <old-ref> <out.md> [--new-ref REF] [--json PATH]`, rendered to
PDF with the existing `build-memo.sh <md> <pdf> "<running head>" "<footer>"` — a memo, not an
Article, so no parity handling is involved and long tables already flow across pages. Exit 2 when
there is nothing to report, so P13 can skip it without a special case.

**Content, in this order.** (1) The **legend delta first**, because a changed meaning for an
existing code moves all 819 cells with no cell diff at all — and the legend lives in
`article-02.typ:224` (`#let glyphs = (u: "●", rc: "❶", sp: "❷", ex: "✪")`) and `:339` (the Note),
not in the data. (2) Per district, the count of changed use cells then
`Use (category): old label → new label`, with the empty code rendered as **"Not allowed"** never
blank — 450 of 819 cells carry it — and the issuing authority named. (3) Added and removed uses and
districts as event types **distinct** from a status change: `build_edition.py:333-338` iterates only
the new keys and so can never report a removal, which is the limit to design around. (4) Permitted
Buildings matrix changes by district/row/column, noting the three null matrices. (5) District
use-standards prose changes. (6) Totals that reconcile with P10's Article 2 `data` count.

**The legend reader.** Parse it with a small extractor in this module rather than importing
`build/permit-review/ruleset_build/legend.py`. The build produces the legal instrument and the app
consumes it; inverting that dependency would make a packet build fail because an app assertion
drifted. The cost is two readers of one legend block, paid for by an agreement test — and if that
test is ever skipped or xfailed the drift is silent.

**Tests.** (a) v0.24-draft → v1.0 reproduces exactly the one D3 cell above and nothing else.
(b) `v1.0` vs `v1.0` exits 2 and writes nothing. (c) Agreement test: this extractor and
`ruleset_build.legend.parse_legend` return the same codes, labels, authorities and glyphs for the
current `article-02.typ`. (d) The three null-matrix districts are reported as "no Permitted
Buildings matrix", not skipped. **NEGATIVE CONTROL:** change only the legend's wording for an
existing code, leaving all 819 cells untouched, and assert the artifact reports it. A
cell-diff-only implementation reports nothing and the test fails — and that is exactly what P14
does to the legend.

**Touches.** New `build/use_table_changes.py`; `build/build-memo.sh` (consumer, unchanged);
`build/ADOPTION-SPEC.md` §3.3.

---

### P12 — `czc_md.py`: the standalone markdown deliverable

**Purpose.** Make the standalone `.md` an honest document. Today it is `cp "$PROSE"`
(`build-standalone.sh:175`), so for Article 2 it is `article-02-prefatory.md` alone — **the
thirteen district use tables Right to Farm edits would be entirely absent from the deliverable most
likely to be read as "Article 2" by someone who was told Article 2 changed.** The integrated `.md`
at least injects a pointer note (`build-full-czc.sh:358-360`); the standalone injects nothing. It
also carries source frontmatter verbatim, including `footer-date: "Draft v0.2-draft"` at
`source/article-03-streets-roads-driveways.md:4`, which is why that string sits in the shipped
`releases/v1.0-adopted/Newcastle CZC (Adopted v1.0).md:258` where
`adopted_residue.py:52` never looks (it receives the `.md` only as a basename).

**This is the component that is larger than it looks.** An Article 2 data appendix is a *second
renderer* for the district tables, and a second thing to drift from `article-02.typ`. Scope it
deliberately (see Open Decision D2): the honest minimum is a generated pointer note naming exactly
what is absent and where it is authoritative, declared per Article as `md_completeness`
(`complete` | `prose-only` | `prose-plus-appendix`) in P9's manifest so the gap is a declared fact
rather than a silent one. Build the Article 2 appendix only if Ben wants it, and reuse P11's
renderer rather than writing a third one.

**Invocation.** `czc_md.py <article-NN> <out.md> [--src-dir DIR] [--mode MODE] [--version V]`,
called from `build-standalone.sh:175` in place of `cp`.

**Tests.** No `Draft v` string survives in any mode's output; Article 1's output carries the
pointer note naming the district maps; Article 3's marker comments do not appear as raw comments;
if an appendix is built, Article 2's contains all 13 districts and 819 cells and matches what
`article-02.typ` renders from the same data. **NEGATIVE CONTROL:** declare Article 2
`md_completeness: complete` while the appendix generator is stubbed out and assert a named test
fails — the control that stops `prose-only` being quietly claimed as complete. **Residue control:**
assert an adopted-mode `.md` contains no draft chrome.

**Touches.** `build/build-standalone.sh:175`; new `build/czc_md.py`;
`build/article-manifest.json` (`md_completeness`, per P9); `build/adopted_residue.py:52` (extend to
scan `.md` bytes, or record why not).

**Separate commit, separately summarised.** The one-line fix to
`source/article-03-streets-roads-driveways.md:4` is live, propagates to v2.0 and to every standalone
`.md`, and bundling it into a machinery change would hide it. And widening the residue scan must
**not** widen the pattern to the bare word "draft": `adopted_residue.py:29` pins
`MUST_SURVIVE = ("drafts the official map",)` — the Code's own adopted text — while `"Draft v"` is
already in `CHROME`.

---

### P13 — `build-release.sh`: one command, and the gate that makes it trustworthy

**Purpose.** Release deliverables are produced in three disconnected places today —
`build-adoption.sh:137-150` for adoption, hand-run commands in `CLAUDE.md` for drafts, and test
helpers — and nothing knows what a release must contain. Adding three deliverable types by hand
means three more hand-run steps and three more hard-coded lines like
`build-adoption.sh:150`'s literal Article 3 filename.

**Invocation.** `build-release.sh <version> [date] --old-ver=<ref> [--plan-only] [--out-dir DIR]`.
`--old-ver` is **required**, not auto-detected: I ran
`git describe --tags --abbrev=0 v1.1-draft^` and it returns
`fatal: Not a valid object name v1.1-draft^`, so `build-redline-full.sh:55`'s auto-detect provably
cannot work for an unreleased draft. Falling back to "newest tag reachable from HEAD" would silently
pick the wrong baseline in a repo that moves tags habitually. Refuse rather than guess.

**Sequence.** Derive the section map (P6) → **run `section_map.py selfcheck` and refuse on non-zero**
→ run `czc_diff.py` and write `ships.json` → apply overrides, refusing any without a reason →
write `release-plan.json` and stop if `--plan-only` (this is the operator's review surface, and what
makes the judgement auditable rather than implicit) → integrated `.pdf` + `.md` → integrated
redline `.pdf` + `.md` (the `.md` is the `--plain` stage concatenated; today it is discarded with the
tmpdir) → for each `SUBSTANTIVE` Article, `build-standalone.sh N` and `build-redline-standalone.sh N`
→ `use_table_changes.py` + `build-memo.sh` when Article 2's data moved → a Summary skeleton
**generated from the plan**, naming the `RENUMBER-ONLY` Articles → the gate → `pdf_recap.py`.

**The Summary skeleton must be generated, not copied.** `build-adoption.sh:197-198` hard-codes
"adopted November 3, 2020 and amended through March 24, 2025" and `:210` "Article renumbering (old
3-8 become 4-9)" — a four-point list keyed to the v0.1-baseline situation and **false for any later
cycle**. The baseline sentence comes from `adoption-map.json`; the cannot-show list from P10's own
`heading`/`table`/`data` counts and P6's suppression counts; and the named `RENUMBER-ONLY` list is
what the new rule actually requires the Summary to carry. The prose stays hand-written, and the
driver never overwrites an existing Summary.

**The gate.** Assert every file the plan promises exists, is non-empty, and for each PDF that its
footer page numbers run consecutively. Build everything into `releases/<ver>/.staging/` and move it
into place **only after the gate passes**, so a failure cannot leave a shipped-looking directory —
today `mkdir -p "$RELEASE_DIR"` runs before any render (`build-full-czc.sh:46`,
`build-standalone.sh:49`), pandoc stdout is discarded (`build-full-czc.sh:243,248`), and only
`toc_links.py:44-47` writes atomically, so a leaf's exit 0 does not prove its file was written.
**The gate refuses; it does not report.** `pdf_recap.py`'s `main()` prints and returns 0 while
`ADOPTION-SPEC.md:301` says "Each gate refuses; none warns" — §6.5 is already report-only, and that
is the miniature of the failure this component must not repeat.

**Mode decision, recorded here.** Standalones ship in **draft and meeting mode only, never
adopted**. The integrated Code is the document the Town adopts and standalones are extracts that do
not govern, so adopted-mode standalones would need their own render path, their own identity gate
and their own residue gate in `build-adopted.sh` to protect documents with no legal effect. This
closes the open item at `ADOPTION-SPEC.md:380-382` by decision. `build-adopted.sh` and
`adopted_residue.py` stay unextended. Ben can overrule it; the cost of overruling is one render path
and one residue gate per artifact (Open Decision D5).

**`build-adoption.sh` calls this driver in meeting mode**, keeping its own gates — version state,
`baseline_selfcheck`, the dirty-`source/` refusal, `frozen-from.json` — and its own argv unchanged.

**Tests.** (a) On a tree with no changes: integrated Code and redline, no standalones, a Summary
skeleton naming nothing, exit 0. (b) With a single Article 7 prose edit, exactly Article 7's four
files appear. (c) With a single `article-02-data.json` edit, Article 2's four files **and** the Use
Table Changes artifact appear, and Article 2's standalone redline carries the unmarked-figure
disclosure. (d) An override with an empty reason is refused. (e) `--plan-only` writes no artifacts.
**NEGATIVE CONTROL:** stub one leaf script to exit 0 without writing its PDF and assert the gate
catches the missing deliverable and leaves `releases/<ver>/` absent. Without that control the driver
reports a complete release that is missing a file, which is worse than a crash because someone reads
"Done" and commits.

**Touches.** New `build/build-release.sh`; new `build/combined_md.py` (extracting the Article 2
pointer-note injection from `build-full-czc.sh:358-360` so the standalone `.md` for native Articles
stops silently omitting the district tables, rather than copying that text a second time);
`build/build-adoption.sh:130-252`; `build/build-redline-full.sh` (the `.md` copy);
`build/pdf_recap.py` (counts become assertions; the printing stays).

---

### P14 — `build-redline-standalone.sh`

**Purpose.** The per-Article redline the rule requires and `CLAUDE.md` lists as deferred. With P1,
P4, P5 and P8 in place this is a thin composition, not a new build.

**Invocation.** `build-redline-standalone.sh <article-NN> <new-ver> <old-ver> [date]` —
deliberately not auto-detecting `old-ver` (see P13). Stages `source/`, calls P5 for that one
Article's prose so no other file is touched, renders P8's even-page note, then invokes
`build-standalone.sh` with `SRC_DIR`/`OUT_DIR`/`OUT_NAME_OVERRIDE`/`STANDALONE_FRONT_NOTE`.
Honours `ADOPTION_MODE`/`ADOPTION_EVENT_DATE` by sourcing `adoption-footer.sh` through
`build-standalone.sh` unchanged, so the version-state gate (`adoption-footer.sh:37-41`) applies in
both directions. `REDLINE_OUT=<path>` for a dry run that cannot touch a release, matching
`build-redline-full.sh:181`. Emits both `.pdf` and the `--plain` `.md`.

**Tests.** (a) Article 7 `v1.0` → working tree: page count, blank count, and **every footer's
printed number equals its physical page** — the parity predicate, asserted on the *marked*
document, which is longer than the unmarked one. (b) Article 2: D1's first spread page still lands
on a **verso**, i.e. the pad-to-odd-before guard (`build-standalone.sh:124-126`) survived the note.
(c) Article 3 with an edited `<!-- TYPE-PAGES -->` line: assert the plates' *physical positions*,
not just exit 0 (the P3 interaction). (d) `REDLINE_OUT=/tmp/...` leaves `releases/` untouched.
**NEGATIVE CONTROL:** an Article whose only change is inside a raw-Typst table must produce a
redline with **zero** red marks **and** a disclosure page saying so — asserted, because a reader
seeing no marks concludes nothing changed. Remove the disclosure and the test fails. **Second
control:** insert an uncounted page into `PARTS` and assert the parity test fails — proof the test
can see a parity break rather than merely passing.

**Touches.** New `build/build-redline-standalone.sh`. Consumes P1, P2, P4, P5, P8.

---

### P15 — the fifth use-table status code, end to end

**Purpose.** "Permitted without a permit" has to land in five places, and one fails **silently in
the permissive direction a resident would act on.**

**The reproduced defect.** `app/citation.py:475` is
`if not cell.get("allowed") or not cell.get("permit"): return []` — the same result for a prohibited
cell and a permit-free one. I ran it read-only on
`{'code':'p','permit':None,'authority':None,'allowed':True}` and `cell_reviews` returned `[]`. The
sentence builder at `:536` branches on the identical test `if not allowed or not permit:` and at
`:538` emits
`f"{art} {use_label} use is not allowed in the {district_label} District."` — so a use the Code
permits outright prints as **prohibited**, confidently, with no error. Three further sites read a
null permit as prohibition: `app/main.py:372` and `render/worksheet.py:124` both
`row["permit"] or "(none — prohibited)"`, and `app/templates/worksheet.html:63`
`{{ 'row-prohibited' if not row.permit else '' }}`. **Nothing in the 1099-test suite catches this.**

**Five coordinated edits, branch fix first.**
1. `app/citation.py`: split `:475`/`:536` so the order is `not allowed` → prohibition;
   `allowed and no reviews` → a new permit-free sentence form; else the existing sentence. The
   discriminator must be an explicit `status` (`permitted` | `permit_required` | `prohibited`),
   **never `permit is None`** — `cell_reviews` legitimately returns `[]` because no review *is*
   required.
2. `source/article-02.typ`: the new code in `glyphs` (`:224`), a fifth legend row, and the Note at
   `:339` rewritten to name five codes. `status()` at `:229-233` already splits on spaces and looks
   the code up in `glyphs`, so no renderer logic changes.
3. `ruleset_build/legend.py`: `_REQUIRED_CODES` (`:68`); the `' Required'` and `' Permit'` suffix
   assertions at `:128-137`, which a permit-free row satisfies **neither** of; `EXPECTED_LEGEND`
   (`:19-66`); and **remove the early `break` at `:150-151`** — `if len(seen_codes) ==
   len(_REQUIRED_CODES): break` means a fifth legend row added to the `.typ` alone is **silently
   ignored rather than rejected**. The Note's wording is asserted verbatim, so that half fails
   loudly; the row is the silent half.
4. `ruleset_build/build_use_matrix.py`: the counter at `:219` is a literal
   `{"u":0,"rc":0,"sp":0,"ex":0,"":0}` and the multi-status path at `:228` does
   `by_code_counts[part] += 1` — a **bare subscript**, so a new code inside a combined cell raises a
   raw `KeyError` instead of `UseMatrixBuildError`, while the single path at `:238` uses `.get`.
   Seed the counter from the legend. The literal `63` at `:210` and `:252` (and
   `app/main.py:1502`) becomes a per-edition declared count, keeping the cross-district
   identical-set guard.
5. `app/main.py:372`, `render/worksheet.py:124`, `app/templates/worksheet.html:63`,
   `app/reviews.py` (row shape), `ingest/formgen.py` (`cross_check_review_type`).

Schema to 1.2.0 with every existing cell byte-identical, following the D-0033 precedent — except
D-0033's "null permit means print nothing" is the **opposite** of fail-safe here.

**Ordering, and it is not optional.** P15 must land **after P11**. Introducing a fifth code changes
what the Note at `:339` asserts about every cell carrying none of the four — 450 of 819 cells —
**with no cell diff at all.** If P11 cannot yet report a legend delta, the code's introduction is
itself an undisclosed 819-cell move. One of the three candidate architectures placed P15 in parallel
with everything and called it independent; it is not.

**Tests.** (a) A fixture cell with the new code yields the permit-free sentence, and the prohibited
cell's sentence is unchanged character for character. (b) The new code combined with another in one
cell either builds correctly or raises `UseMatrixBuildError` — **never `KeyError`**; Ben decides
which, and until he does the builder raises (Open Decision D3). (c) Every existing cell in
`rulesets/adopted-v1.0/use-matrix.json` is byte-identical under 1.2.0. (d) A fifth legend row the
parser does not recognise must **raise**, not be ignored — delete the `:150` fix and this fails.
**NEGATIVE CONTROL, the single most important test in this design:** revert the `citation.py` split
and assert a **named** test fails on a permit-free cell rendering as "is not allowed". The output is
reproduced above, so this control is known to fire. Without it the whole feature can ship green and
tell residents a permitted use is prohibited.

**Before adoption there is no binding ruleset that can carry the code** — `rulesets/draft-v0.22` has
no `use-matrix.json` and `app/rulesets.py:_build_ruleset` raises without it — so the only pre-vote
exercise is a fixture ruleset built to a temp dir. Plan for that fixture.

**Touches.** `source/article-02.typ:224,335-342`;
`build/permit-review/ruleset_build/legend.py:19-66,68,110,125-155`;
`.../build_use_matrix.py:210,219,228,252`; `app/citation.py:475,536`; `app/main.py:372,1502`;
`render/worksheet.py:124`; `app/templates/worksheet.html:63`; `app/reviews.py`;
`ingest/formgen.py`; `build/permit-review/CONTRACT.md` §4.3, §4.4, §6.2; a `DECISIONS-NEEDED.md`
entry.

---

### P16 — Article 2's missing first-page chrome (prerequisite, pre-existing)

**Purpose.** `source/article-02.typ:95`, `:119` and `:143` each return early on
`here().page() == 1`, guards written for a leading parity blank that `:365-372` records as
**removed**. I measured the shipped artifact with PyMuPDF: in
`releases/v1.0/Newcastle CZC (Town Meeting Edition v1.0).pdf` (117 pages), **physical page 12 —
D1's first page — contains no `Newcastle Core Zoning Code` footer, while pages 11, 13 and 14 all do.
It is in the adopted v1.0 edition too, since that renders from the same source.** Fix it before
Article 2 ships a standalone and a standalone redline, or it ships three more times per release.

**Invocation.** No interface change. Remove the three guards and let the chrome key off
`page_offset` as every other unit does. While in the file, delete the two comments at
`build-full-czc.sh:87-89` and `:137` that describe parity padding the code does not perform — the
written model of parity must match the build, since the next person to touch it reads the comment.

**Tests.** (a) Render `article-02.typ` alone at a known offset and assert page 1 carries the footer,
the running head and the tab — do this *before* the fix to confirm the defect is in the unit and not
in assembly (**INFERRED** until run; the measurement above is of the assembled PDF). (b) The
integrated build's page and blank counts are unchanged — chrome does not change pagination.
(c) The Article 2 standalone's D1 page carries chrome and is a verso.
**NEGATIVE CONTROL:** restore one guard and assert a named test fails on the missing footer.
Nothing asserts chrome on any unit's first page today, which is why this survived into an adopted
ordinance.

**Touches.** `source/article-02.typ:95,119,143`; `build/build-full-czc.sh:87-89,137` (comments only);
`build/tests/test_footer_modes.py`.

**Needs a ruling.** It changes source that an adopted edition renders from (Open Decision D4).

---

### P17 — de-pin the tests that track the live tree

**Purpose.** Several tests assert numbers computed from the working tree and go red the moment
Right-to-Farm source lands, independently of anything in this design:
`test_build_adoption.py:28 EXPECTED_TOTAL = 151` (the breakdown compares working-tree `source/`
against the baseline, and the file says so at `:11-17`), and `test_structural_note.py:108`
`page_count == 117` and `:118` `"113" in last`. On the app side,
`test_use_matrix.py` (819/63/`by_code`), `test_parse_definitions.py:49,104,117`
(272 terms, 64 uses, RESIDENCE at section "53" → 54) and `test_edition_rollover.py:73` all move.
**If they are re-pinned reflexively, or loosened, the suite stops being evidence at exactly the
release where the evidence matters.**

**Invocation.** Convert each to fixture-driven or invariant-driven: the breakdown total is asserted
against a committed fixture source tree, not `REPO/source`; page and blank counts are asserted as
**invariants** (front matter even, exactly one structural blank, every footer number equals its
physical page) rather than as literals. Where a literal is genuinely the point, move it into a
fixture file with a comment naming the release it was measured on. Add the fixture coverage the new
rules need: a section map with a within-article shift, and a `v1.0`-as-baseline pair — today every
baseline test pins the pre-rollover 2020 map through the `ADOPTION_MAP` env seam
(`adoption_map.py:27`), so none of the machinery is exercised against the shipped identity map.

**Tests.** The suite passes on current `main` with identical results, and passes unchanged when a
fixture Article gains a section. **NEGATIVE CONTROL:** introduce a real parity break (an uncounted
inserted page) in a fixture build and assert the invariant tests fail. A page-count literal would
also fail, but for the wrong reason and with no diagnosis, which is how a loosened assertion gets
written.

**Touches.** `build/tests/test_build_adoption.py:11-17,28`; `build/tests/test_structural_note.py`;
`build/tests/test_footer_modes.py:25,33-35`; `build/tests/fixtures/` (new);
`build/permit-review/tests/` per P15.

---

### P18 — `ADOPTION-SPEC.md` and `CLAUDE.md`

**Purpose.** Keep the declared authority for a legal instrument true. **The spec and the code
already disagree before this work starts**, so new capabilities must not be shipped against it
unrevised:
- `ADOPTION-SPEC.md:3` still reads "**Status:** design, approved 2026-08-24. Not yet implemented."
  for machinery that shipped an adopted ordinance.
- `:135` says normalisation is "applied to **both sides**" and tabulates **three** rules, while
  `normalize_for_diff.py:166-167` applies renumbering to the **old side only** and the module has
  **five** (`_heading_case`, `amap.renumber`, `_renumber_tables`, `_renumber_frontmatter`,
  `_rewrap`).
- `:301` says "Each gate **refuses**; none warns" while §6.5's layout check is `pdf_recap.py`,
  which prints and returns 0.
- `:380-382` leaves the standalone-in-adopted question open; P13 closes it.
- §3.3's packet list has four items and omits `frozen-from.json`.

**Scope of revision.** §3.1 (the derived section map is *not* in `adoption-map.json`, and why);
§3.2 (which side is normalised, the real rule count, the section rule and its conservatism tests);
§3.3 (packet list: per-Article standalones and standalone redlines in both formats, the Use Table
Changes artifact, `ships.json`, `frozen-from.json`); §4.3 (the structural note stops being fixed to
Articles 2 and 3); §6.1 (add the `baseline_selfcheck`, dirty-tree and section-map-selfcheck gates);
§6.2 (correct the identity gate's premise — `cmp` shows the v1.0 meeting and adopted `.md` are
byte-identical, because `build-full-czc.sh:398` is a plain `cat`, so the frontmatter strip is
harmless but the stated rationale is wrong); §6.3 (residue scope over `.md` bytes, or record why
not); §6.5 (layout stops being report-only); §7 (the stale `footer-date`).
`CLAUDE.md`'s "Build & release flow" becomes `build-release.sh`; the deferred per-Article redline
moves to done.

**Spec revisions ship in the same commits as the code they describe, not as a follow-up.**

**Tests.** Documentation, so the test is a reviewed read. Two mechanical checks are worth having:
the spec's packet list and the release plan's artifact kinds must agree, asserted over a fixture
plan; and every gate §6.1 claims must be reachable by name from `build-adoption.sh` or
`build-release.sh`. **NEGATIVE CONTROL** for the first: add an artifact kind the spec does not list
and assert the agreement test fails — the control that keeps the spec from drifting behind the code
the way §3.2 and §6.2 already have.

---

## 3. BUILD ORDER

Five waves. Dependencies are real, not stylistic.

**Wave 0 — prerequisites, independent of the rule. Parallel.**
- **P16** (Article 2 chrome) — before Article 2 ships extracts, or the defect ships three more
  times per release.
- **P17** (de-pin tests) — before adding tests, or every later wave fights red baselines it did not
  cause.
- **Also in this wave, outside the rule but live and dangerous:** `ruleset_build/build_ruleset.py:153`
  calls `_lift_use_matrix.main([])`, and `lift_use_matrix.py:40-41` defaults to
  `DEFAULT_RULESET_KEY = "adopted"` and `DEFAULT_SRC = source/article-02-data.json` — so re-running
  the orchestrator **rebuilds the SUPERSEDED 2020 use matrix from the working tree.** Nine decided
  cases cite that record. Guard it (hash check against the manifest, or remove the step from the
  orchestrator) before anyone re-runs the builder for P15. This is live today and not caused by
  Right to Farm.

**Wave 1 — seams. Parallel; all four default-preserving and independently testable.**
- **P1** (standalone seams), **P2** (naming), **P3** (marker safety), **P4** (`--plain`), **P9**
  (manifest ownership).
- **P5** (redline-stage extraction) lands at the *end* of this wave: it is a pure refactor whose
  test is "the integrated redline is unchanged", and it should not be in flight while P4 changes
  the wrappers it calls.
- **P3 gates** any redline of a marker-bearing Article, so it must precede P14.

**Wave 2 — the diff core. Strictly sequential.**
- **P6** (`section_map.py` + the selfcheck gate) then **P7** (the normaliser rule).
  P7's grammars consume P6's map shape, and P7's conservatism tests need P6's derivation to produce
  a real 64-entry map. **P7 must not start before P6's negative controls pass**, because a
  hand-authored map is the 308-phantom-line failure and the whole reason the map is derived.
- Neither touches `adoption-map.json` or `baseline_selfcheck.py`. That is the point of the choice
  and should be asserted, not assumed.

**Wave 3 — determination and artifacts. Parallel after P9 and P7.**
- **P10** (`czc_diff`) needs P9's ownership map and P7's suppression to classify renumber-only
  Articles. **P11** (`use_table_changes`) needs P9 only, and shares the keyed JSON differ with P10 —
  **build the differ inside P10 and have P11 import it**, not the reverse, so there is one keyed
  comparator.
- **P8** (notes) needs P7 (it must state the suppression count) and P9 (it reads which units render
  unmarked). **P12** (`czc_md`) needs P9 and, if an Article 2 appendix is in scope, P11's renderer.
- **P14** (`build-redline-standalone`) needs P1, P2, P3, P4, P5 from Wave 1 and P8 for its
  disclosure, so P8 lands first within this wave.

**Wave 4 — composition and the code.**
- **P13** (`build-release.sh` + the gate) last among the build work, because it is the only
  component testable end to end and its gate is what proves the others produced files.
- **P15** (fifth status code) **after P11**, for the reason given in its entry. It is otherwise
  independent of the release machinery — it touches the data and the app — so it can run in
  parallel with P13.
- **P18** (spec + CLAUDE.md) committed alongside each code change it describes, finalised last.

### What Right to Farm actually blocks on

**Blocking** — the amendment cannot ship a conforming release without these:
P1, P2, P3, P4, P5 (the standalone redline's whole substrate), P14, P9, P10 (the determination the
rule turns on), P11 (Article 2's tables moved), P12 (or at minimum its pointer note, or the Article
2 `.md` ships without the tables that changed), P13, P8, P16.

**Can follow the amendment:**
- **P6 + P7.** Section suppression buys **zero rendered marks** for this release (Section 1). It
  protects the operator's headline number and future text. If the schedule tightens, ship Right to
  Farm with the inflated breakdown number *explained in the Summary* and land P6/P7 in the next
  cycle. It must not be the critical path.
- **P15.** Only if the fifth status code is actually part of the Right-to-Farm amendment — which is
  Open Decision D3. If it is, it is blocking and it is the highest-risk item here.
- **P17** can land before or during, but not after Wave 1.
- **P18** tracks whatever ships.

---

## 4. CHANGES TO EXISTING MACHINERY

Every existing file that changes, with what changes in it.

| File | What changes |
|---|---|
| `build/build-standalone.sh` | `:23` `SOURCE_DIR` → `${SRC_DIR:-…}`; `:48-49` `RELEASE_DIR` → `${OUT_DIR:-…}` and `mkdir -p` moved below input resolution; `:83` `OUT_NAME` from `czc_standalone_name` with an override; `:110-111`/`:150`/`:164`/`:170` front-note pages into `PARTS` with the even-length rule; `:175` `cp "$PROSE"` → `czc_md.py` (P1, P2, P12) |
| `build/adoption-name.sh` | Gains `czc_standalone_name`; `czc_integrated_name` unchanged (P2) |
| `build/redline-text.py` | `:207-215`/`:233` `--plain` wrappers; `:542-562` `is_unmarkable_structure` in the `--source` emitters; `:600-620` flag handling; the stderr tally becomes machine-readable (P3, P4) |
| `build/build-full-czc.sh` | `:155-158` the silent marker fallback becomes a refusal; `:87-89` and `:137` stale parity comments deleted; `:358-360` Article 2 pointer-note injection extracted to `combined_md.py`; the redline `.md` is kept rather than discarded (P3, P13) |
| `build/build-redline-full.sh` | `:100-134` old-side loop replaced by a `redline-stage.sh` call; `:152-160` caveat and `--old-label` generated rather than hard-coding "November 3, 2020 … March 24, 2025"; gains the `--plain` `.md` output (P5, P8, P13) |
| `build/normalize_for_diff.py` | `:150-198` section rule in **both** normalisers behind `smap=None`; `:201-226` `changed_line_count` gains `smap=None` and a new `substantive_line_count` beside it; `:229-250` `report()` gains `sections` and is wired into the build (P7, P10) |
| `build/redline_resolve.py` | `:48-58`/`:90-94` `--section-map` and `--article`, opt-in; `git_show:37-40` promoted to a shared helper, behaviour unchanged (P6, P7, P11) |
| `build/structural_note.py` | `:60-200` the hard-coded "Article 3 … is new", "articles after Article 2 were renumbered", "Article 2 … NO marks" blocks become data-generated; `--scope`, `--section-map`, `--pad-to-even`; `:164-168` one-page ceiling becomes a per-scope budget (P8) |
| `build/article-manifest.json` | Entries for Articles 4–9 (empty `units`), `data_sources`, `md_completeness`, top-level `shared`/`ignored` (P9, P12) |
| `build/manifest.py` | `:27-51` new `data`, `articles`, `owner` subcommands as JSON-out; the four existing subcommands byte-identical, `has` still exiting 1 for 4–9 (P9) |
| `build/adoption_breakdown.py` | Left intact in Wave 3; later a thin caller over `czc_diff.py` so draft and adoption read one instrument (P10) |
| `build/build-adoption.sh` | `:137-150` the three hard-coded builds and `:150`'s literal Article 3 filename become a `build-release.sh` call; `:197-215` the Summary skeleton's 2020-baseline sentence and four-point list become generated slots; `:245-252` recap labels from the plan. Its own gates and argv unchanged (P13) |
| `build/pdf_recap.py` | Counts become assertions the gate can fail on; printing stays (P13) |
| `build/adopted_residue.py` | `:52` extended to scan `.md` bytes, or the refusal recorded. **The pattern must not widen to the bare word "draft"** — `:29` pins the Code's own "drafts the official map" (P12) |
| `source/article-02.typ` | `:95`, `:119`, `:143` the `here().page() == 1` guards removed; `:224` `glyphs` and `:335-342` the legend row and Note for the fifth code (P16, P15) |
| `source/article-03-streets-roads-driveways.md` | `:4` `footer-date: "Draft v0.2-draft"` — **its own commit, its own Summary line** (P12) |
| `build/permit-review/ruleset_build/legend.py` | `:19-66` `EXPECTED_LEGEND`; `:68` `_REQUIRED_CODES`; `:125-137` the `' Required'`/`' Permit'` row grammar; `:150-151` the early `break` removed so an unknown fifth row **raises** (P15) |
| `build/permit-review/ruleset_build/build_use_matrix.py` | `:210`/`:252` the literal `63` → per-edition declared count; `:219` counter seeded from the legend; `:228` bare subscript → the module's own error; schema 1.2.0 (P15) |
| `build/permit-review/ruleset_build/build_ruleset.py` | `:153` guarded so the orchestrator cannot rebuild the superseded 2020 matrix from the working tree (Wave 0) |
| `build/permit-review/app/citation.py` | `:475` `cell_reviews` and `:536` the sentence branch split on an explicit `status`, never on `permit is None` (P15) |
| `build/permit-review/app/main.py`, `render/worksheet.py`, `app/templates/worksheet.html`, `app/reviews.py`, `ingest/formgen.py` | `main.py:372`, `worksheet.py:124`, `worksheet.html:63` stop reading a null permit as prohibition; row shape gains `status`; `cross_check_review_type` handles it; `main.py:1502` per-edition counts (P15) |
| `build/permit-review/CONTRACT.md` | §4.3, §4.4, §6.2 (63/819/four-code/legend-note facts); and **five** sites asserting "Section numbers are preserved; only article numbers shift" — `:753`, `:734`, `app/citation.py:75`, `app/citation.py:211`, and `ruleset_build/crosswalk.py:247`, which writes it **into a generated artifact** (`rulesets/article-map.json`) (P15, P18) |
| `build/ADOPTION-SPEC.md` | `:3` status; §3.1, §3.2, §3.3, §3.5, §4.3, §6.1, §6.2, §6.3, §6.5, §7 (P18) |
| `CLAUDE.md` | Build & release flow → `build-release.sh`; the deferred per-Article redline → done; the rollover bullet unchanged, since the section map is not in `adoption-map.json` (P18) |
| `build/tests/` | `test_build_adoption.py:11-17,28`; `test_structural_note.py:46,108,118`; `test_footer_modes.py:25,33-35,41-43`; `test_normalize_for_diff.py`; `test_redline_resolve.py`; new fixtures (P17) |

**Explicitly unchanged, as an invariant of this architecture:** `build/adoption-map.json`,
`build/adoption_map.py`, `build/baseline_selfcheck.py`, `build/build-adopted.sh`,
`build/version_state.py`, `build/toc_links.py`, `build/toc_entries.py`,
`build/split-article-03.py` (message only), `build/build-memo.sh`, `build/build-article.sh`,
`style/czc-template.typ`.

---

## 5. RISKS AND FAILURE MODES

### Breaks silently (the dangerous set)

**R1. The section rule suppresses a real amendment.** The worst failure available — an omission from
a redline is invisible to the reader, and this is a warrant packet.
`normalize_for_diff.py:21-23` names it. Mitigated **structurally**, not by care: the map is derived
from heading-title matches and holds only pure renumberings, so a retitled or moved-and-edited
section is never mapped; the deriver refuses below a similarity floor; every grammar is tested in
both directions; the statute guard is explicit; `report()` is wired in so the suppressed count is
shown rather than assumed; and P6's build-time `selfcheck` runs before any release.
**Residual risk accepted deliberately:** a cross-reference form not enumerated. An unsuppressed
reference is a recoverable false "still differs"; a suppressed amendment is not.
**Negative controls:** `shall`→`may` next to a renumbered heading still marks; a deleted section
leaves neighbours unmapped; a deliberately wrong map fails `selfcheck`.

**R2. The permit-free status ships green and wrong.** Reproduced above: `cell_reviews` returns `[]`
and `citation.py:536` builds "is not allowed" for a permitted use. Permissive-direction, user-facing,
and invisible to 1099 tests. **The named negative control is the single most important test in this
design.** Related and *not* fixed by this work: `build_edition.py:148` matches citations on the
superseded ruleset's key while `build_subdivision_criteria.py:529-530` writes the literal
`"adopted"`, so at the **next** adoption the criteria citations silently fail to re-point —
harmless for Right to Farm because Article 8 is untouched, fatal whenever Article 8 moves. Flag it;
do not absorb it.

**R3. `ships.json` becomes a rubber stamp.** The determination is computed, but "substantive" is
ultimately a legal judgement, and an operator under time pressure will downgrade an Article rather
than review it. The reason-required gate is a speed bump, not a guarantee. The real mitigation is
that `czc_diff.py` reports **four independent counts**, so a downgrade has to argue with a specific
number, and `release-plan.json` records who ruled and why.

**R4. Parity, in exactly one place.** The offset model is data-driven and safe by construction as
long as every inserted page is counted (`build-standalone.sh:134`). The narrow exposure is the
standalone's front note, which has no TOC padding to absorb an odd run — an odd note flips
verso/recto for the whole extract and the build still exits 0. Covered by P1's named negative
control. The integrated build is unaffected: `build-full-czc.sh:337-341` already pads `PRE_TOC_COUNT`
to even.

**R5. A v2.0 packet asserting false facts.** `structural_note.py:93-106` and
`build-redline-full.sh:156` hard-code "Article 3 is new", "Article 2 carries NO marks" and the 2020
old-label. P8 fixes the note. **Not fixed here and already false:** `build-cover.py:137-139`'s
"includes proposed Article 3: Thoroughfares" and "amended through March 24, 2025" — the Code was
amended **September 14, 2026**, so the draft cover for `v1.1-draft` is wrong today. The baseline
cover's date line is scanned art with no text layer, masked only in adopted mode and pinned by
`test_cover_modes.py`, so a text assertion cannot see it. This needs its own ruling (D6).

**R6. Two readers of one legend block** (P11's extractor and `ruleset_build/legend.py`), chosen over
making the packet build depend on the app. The agreement test is the whole mitigation; if it is
skipped or xfailed the drift is silent.

**R7. The crosswalk silently mis-pairs after the renumbering.** `crosswalk.py` matches
adopted-to-draft on section-**number** identity (`:19`, `:247`), so after an insertion it pairs 64
wrong sections at confidence 1.0, with a note saying the numbers line up —and the existing test,
which asserts only that matched numbers are equal, still passes. Nothing at runtime reads
`crosswalk.json`, so the damage is to a record, not to a decided case. **Out of scope here; state it
in the plan rather than fixing it**, and note that any fix needs P6's map first.

### Breaks loudly (acceptable)

- The legend **Note**'s wording is asserted verbatim by `legend.py`, so a stale Note fails hard. The
  legend **row** is the silent half (`:150-151`) — P15 closes it.
- `build_use_matrix.py:210,252` hard-fail on a use count other than 63.
- `redline_resolve.py:86-88` refuses an unresolvable old side; `build-redline-full.sh:123-124`
  propagates it.
- `adoption-footer.sh:37-41` refuses a version/mode mismatch in both directions.
- `structural_note.py:164-168` raises when a block overflows the page.
- P17's re-pinned tests go red by design when Right-to-Farm source lands. **That is correct
  behaviour, and re-pinning them reflexively instead of converting them to invariants is itself a
  risk.**

### Cost risks

**R8. Review attention, which the brief names as a constraint.** A Right-to-Farm release under this
design ships the integrated Code and redline, standalones and standalone redlines for each
substantive Article, a Use Table Changes artifact and a Summary — roughly 18 files where v1.0
shipped 8. The mitigations are the rule's own carve-out (enforced by P10: Articles touched only by
renumbering are **named, not shipped**) and `--plan-only`, which is the signal to read *before*
building. **If the computed verdict comes back `SUBSTANTIVE` for seven Articles, the right response
is to question the comparator's thresholds before the release, not to ship fourteen extracts.**
`build-release.sh` should print the artifact count and require confirmation above a threshold.

**R9. Build time.** The suite is ~2.5 minutes because it builds real PDFs, and this design adds a
standalone redline per substantive Article. P1's `OUT_DIR` seam lets the new tests build into
`tmp_path` instead of the real release tree, which is a correctness win; it does not make them
fast. P13's tests should use `--plan-only` and single-Article `tmp_path` builds, not full releases.

**R10. A `build-adoption.sh` re-run over an already-frozen release.** `CLAUDE.md` and
`build-adoption.sh:258-261` document re-running the freeze to render the Summary PDF. Under the new
rule that re-run rebuilds ~18 artifacts into a directory that may already be committed and tagged,
and the driver stages-then-moves. **Nothing gates "this release is already frozen — render only the
Summary, or refuse."** `version_state.py --require adoption v1.0` exits 0 for an already-adopted
version (I ran it), and `build-adoption.sh:130` is a bare `mkdir -p "$OUT"` with no existing-tag
check. P13 should carry a gate that the new version exceeds `baseline_version` and that neither the
tag nor the release dir already exists, with an explicit "Summary-only" re-run mode.

### Larger than it looks — say so now, not at implementation time

- **P12's Article 2 appendix** is a second renderer for the district tables. If it is in scope it is
  one of the two biggest items here. The pointer-note version is small; the appendix version is not.
- **P7's grammars** are seven forms × two directions × article-context resolution × the statute
  guard. Not a regex.
- **P15** touches twelve-plus files across the build and the app, bumps a schema, and re-pins six
  test families.
- **P13** is the only end-to-end component and will absorb every ambiguity the others leave.
- **P17** is unglamorous and will be the first thing cut under pressure, which is exactly when it
  matters most.

---

## 6. OPEN DECISIONS

These are Ben's, the Board's, or the chair's. None can be settled by this process.

**D1 — What *is* a redline `.md`?** No redline markdown has ever shipped. Because
`releases/**/*.pdf` is gitignored and `releases/v1.0` tracks only `.md` files plus
`frozen-from.json`, **the markdown redline is the only form of a redline that will exist in the
repository a year from now** — so the format is a permanent provenance decision, not a convenience.
*Options:* (a) plain markdown, `**added**` / `~~deleted~~`, readable in any viewer and diffable in
git — P4's proposal; (b) CriticMarkup; (c) define the `.md` as the marked Typst staging source.
*Consequences:* (a) is readable and permanent but is a new published format the Town must stand
behind; (c) is free but ships pandoc+Typst source to voters as "markdown". Applies to the integrated
redline too.

**D2 — Does the standalone Article 2 `.md` carry the district tables?** Today it would be
`article-02-prefatory.md` alone — prose, no use tables. *Options:* (a) a generated data appendix
(all 13 districts, 819 cells) — honest and complete, but a second renderer for the same data and a
second thing to drift; (b) a mandatory generated pointer note naming exactly what is absent and
where it is authoritative — small, honest about the gap, incomplete as a document; (c) ship prose
only. *Consequences:* (c) means the deliverable named "Article 2" omits the thing that changed, and
should not be chosen. (b) is the floor. (a) is real work and should be scoped as such.

**D3 — The fifth status code's semantics, and whether it is in Right to Farm at all.** Needs: the
code, the glyph, the legend row's wording, the rewritten Note, and **whether it may co-occur with
another code in one cell.** D-0033's `all_required` rule has no meaning for a permit-free status.
*Options:* (a) combination is illegal and the builder raises `UseMatrixBuildError`; (b) combination
is legal with a defined precedence. *Consequences:* (a) is fail-safe and is the default until ruled
otherwise; (b) needs a precedence rule written into `CONTRACT.md` and a citation sentence for the
combined case. D-0033 was resolved by the Planning Board Chair, so a `DECISIONS-NEEDED.md` entry is
the precedent. **Also decide whether this ships with Right to Farm or separately** — it is the
highest-risk item here and the only one that alters binding Code data.

**D4 — Is the Article 2 chrome defect fixed, or carried?** The missing footer on D1's first page is
in the **shipped and adopted** v1.0 edition (measured: page 12 of the Town Meeting edition).
*Options:* (a) fix the source now, so every future edition is correct and the adopted v1.0 PDF
differs from the one the Town voted on if ever re-rendered; (b) fix it and re-render
`v1.0-adopted` (which `build-adopted.sh`'s identity gate would then flag); (c) carry it
deliberately and record why. *Consequences:* (a) is my recommendation and is safe because the
adopted PDF is gitignored build output and the `.md` body is unaffected — but it is a change to
source that an adopted instrument renders from, and it needs saying out loud.

**D5 — Do adopted releases ship standalones?** `ADOPTION-SPEC.md:380-382` leaves it open. P13
closes it as **no** (the integrated Code is what the Town adopts; standalones are extracts that do
not govern). *Consequence of overruling:* one render path and one residue gate per artifact inside
`build-adopted.sh`, multiplying the gate surface of a legal instrument for documents with no legal
effect.

**D6 — The stale cover facts.** `build-cover.py:137-139` says "includes proposed Article 3:
Thoroughfares" and "amended through March 24, 2025"; the Code was amended **September 14, 2026**.
The draft cover for `v1.1-draft` is wrong today. *Options:* (a) generate both from
`adoption-map.json` and the baseline; (b) fix the strings for this cycle. *Consequence:* the
baseline cover's date line is scanned art with no text layer, masked only in adopted mode and pinned
by a pixel test — so (a) needs the pixel geometry re-measured if the mask moves.

**D7 — Which `inventory.json` fields are substance versus derived?** P9's whitelist decides whether
every GIS refresh looks like an amendment. Across v0.22 → v0.24, `addresses` changed on all 214
segments. *Options:* (a) whitelist `type`, `name`, `termini`, `ownership`, ROW/traveled widths as
substance and exclude `addresses`, `geometry`, `present_use`, `districts` as derived; (b) count
everything. *Consequence:* (b) makes the Type Map's own regeneration a substantive change to Article
3 at every release.

**D8 — Can a retargeted cross-reference ever be "renumber-only"?** The rule's carve-out says
Articles touched only by renumbering or cross-reference updates are named, not shipped. But
retargeting a reference changes **which standard applies**. *Options:* (a) a retarget is always
substantive; (b) a pure renumber-shift of an existing target is not. *Consequence:* (a) is
conservative and will ship more extracts; (b) needs the distinction to be machine-decidable, which
P7's map makes possible only for pure shifts.

**D9 — Which Code governs an application pending when the next version takes effect?** The
permit-review app pins a ruleset per case, so either answer is implementable; the code cannot
choose. Outside the build machinery but surfaced by it.

**D10 — Should `frozen-from.json` pin the renderer?** `build-adopted.sh:110` archives the tag's
`source/` and renders it with **today's** `build/` and `style/`; the dirty check at `:115` is
`-- source` only, and `frozen-from.json` records only `frozen_source_tree`. Every component here
adds producers the provenance gate cannot see. *Options:* (a) record the `build/` and `style/` tree
hashes too; (b) leave it. *Consequence:* (b) means a future render of an adopted tag can differ from
what the Town voted on with no gate noticing. Worth a decision, not a task in this scope.

---

## 7. FACTS RELIED ON

All paths relative to `/Users/ben/Developer/Claude/Projects/Newcastle Core Zoning Code`.
Read-only throughout: no file changed, no writing git command run. Probes used toy files in the
scratchpad.

### Reproduced by running (read-only)

| Fact | How |
|---|---|
| An **inserted** splice marker survives marking and the split still succeeds | Marked a toy pair with `redline-text.py --source`: output `` `#text(fill: rgb("#cc0000"))[\<!-- TYPE-PAGES -->]`{=typst} ``; `split-article-03.py` exit **0**. Mechanism: `split-article-03.py:38` `if marker in ln` (substring) and `:76` drops the matched line |
| A **deleted** marker is **resurrected** and the split happens at a marker the new source lacks | Same probe, marker removed from the new side: output `~~<!-- TYPE-PAGES -->~~`, split exit **0**, segment A ended at the resurrected marker. Cause: `emit_deleted_src` (`redline-text.py:551-554`) strikes rather than drops; `prepare_source:535-538` keeps HTML comments intact |
| A permit-free cell yields no reviews | `citation.cell_reviews({'code':'p','permit':None,'authority':None,'allowed':True})` → `[]` |
| Article 2's first page has no footer in the **shipped** v1.0 Town Meeting edition | PyMuPDF over `releases/v1.0/Newcastle CZC (Town Meeting Edition v1.0).pdf` (117 pp): page 12 starts "D1", `'Newcastle Core Zoning Code' in text` → **False**; pages 11, 13, 14 → True |
| `article-02-data.json` has 819 use cells keyed on `(code+name, block title, label)`; `code` alone collides | Built the index read-only: 13 records, `Counter(code)` = `{'SD': 7, 'D1': 1, …}`; 819 cells; statuses `{'': 450, 'u': 218, 'sp': 58, 'rc': 52, 'ex': 40, 'rc sp': 1}`; `matrix` null for CONSERVATION, CAMPUS, MARINE |
| The keyed diff v0.24-draft → working tree returns **exactly one** changed cell | `(('D3','NEIGHBORHOOD BUSINESS'), 'COMMERCIAL GOODS', 'Retail & Service, General')` `rc`→`rc sp`; nothing added or removed. Matches commit `13b2a50` |
| Article 2's false zero in the breakdown | `git diff --numstat v0.24-draft v1.0 -- source/`: `294 24 source/article-02-data.json`, `6 1 source/article-02.typ`, and **`article-02-prefatory.md` absent from the diff entirely**, while `adoption_breakdown.py:52` loops over `m.files.items()` (nine `.md` files) |
| `baseline_selfcheck.py` refuses a legitimately populated map | Scratch map `7→8, 8→9, 9→10` via the `ADOPTION_MAP` seam → `adoption-map.json has not been rolled over for v1.0:`, 7 articles listed (Article 7 = 34 phantom lines), exit **1**. Shipped identity map → `0 marked lines`, exit 0 |
| The old-version auto-detect cannot work for an unreleased draft | `git describe --tags --abbrev=0 v1.1-draft^` → `fatal: Not a valid object name v1.1-draft^` |
| `version_state.py --require adoption v1.0` exits 0 for an already-adopted version | Ran it |
| Article 7 has **66** `## N.` headings, so an insertion at §3 shifts **64** sections | `grep -cE '^## [0-9]+\.' source/article-07-use-standards.md` → 66. The brief's "63" is the use-matrix row count, a different quantity |
| Only 15 cross-references reach Article 7's sections, all internal, all `Section 1.G` | `grep -rn "Article 7 Section\|Article 7 §" source/*.md` → 15 hits, only in `source/article-07-use-standards.md` |
| The statute-citation collision is real | `source/article-01-general.md:102` "30-A MRSA Section 4358"; `source/article-08-administration.md:452` "Title 38, Section 480-B" |
| `adoption-map.json` is rolled over to v1.0 identity | Loaded it: `baseline_version: v1.0`, `article_numbers` 1..9 identity, `files` identity, `new_at_this_adoption: []`, `not_text_comparable: {}` |

### Read and quoted (not run)

- **Standalone seams absent:** `build-standalone.sh:23`, `:48`; vs `build-full-czc.sh:32`, `:45`.
  The gap is documented in the tests' own words at `test_footer_modes.py:25`.
- **Parity mechanism:** `style/czc-template.typ:108` and `:122` `let pn = here().page() + page_offset`,
  with `calc.even(pn)` choosing verso/recto; `build-standalone.sh:134`
  `PARTS+=("$out"); OFF=$((OFF + $(pagecount "$out")))`; the opener rendered at literal `0` at
  `:150`; integrated front matter padded to even at `build-full-czc.sh:337-346`; Article 2
  pad-to-odd at `build-standalone.sh:124-126`.
- **Headings never marked in `--source`:** `redline-text.py:552-553` (deleted heading dropped),
  `:560-561` (new heading verbatim), `:546-548` `_markable`.
- **`changed_line_count` counts raw diff lines:** `normalize_for_diff.py:223-226`
  `difflib.unified_diff(o, n, n=0)` over `normalize_old_side(old)` vs verbatim `new`.
- **Five normaliser rules, old side only:** `_heading_case`, `amap.renumber`, `_renumber_tables`,
  `_renumber_frontmatter`, `_rewrap`; `normalize():170-173` gates three on `is_baseline_side`;
  `normalize_old_side():195-198` omits `_rewrap`. `amap.renumber` is `adoption_map.py:64-70`,
  `r"\bArticle (\d+)\b"`.
- **`report()` is dead code:** `normalize_for_diff.py:229-250`, three keys, no `sections`; its only
  caller is `build/tests/test_normalize_for_diff.py:247`, while `ADOPTION-SPEC.md:155` claims the
  module reports what it suppressed.
- **Draft path is unnormalised:** `redline_resolve.py:18-19` ("keep the historical behaviour
  exactly: same filename at the old tag, no map, no normalisation"), `:52-58`.
- **`baseline_selfcheck` mechanism:** `:87` `n = nz.changed_line_count(text, text, amap=amap)`;
  run as a precondition at `build-adoption.sh:79`, before the `:92` dry-run exit.
- **rc-3/rc-4 contract:** `redline_resolve.py:8-19`; the only reader is
  `build-redline-full.sh:104-134`; `adoption_map.py:6-9` records the measured eight-of-nine
  empty-old-side failure.
- **No redline `.md`:** `build-redline-full.sh:67-68` (`mktemp -d` + `trap`), `:181-189` (PDF only);
  `redline-text.py:207-215` and `:233` emit `{=typst}` spans; `ls releases/v1.0
  releases/v0.24-draft` shows only `— Redline.pdf`.
- **No disclosure surface on a standalone:** `build-standalone.sh:10-11` (no cover/TOC);
  `REDLINE_CAVEAT` reaches the page only via `build-cover.py` (`build-full-czc.sh:292`);
  `FRONT_NOTE_PDF` handling is `build-full-czc.sh:311-346`.
- **Structural-note hardcodes:** `structural_note.py:93-96`, `:98` vs `:68`, `:102-106`, `:164-168`;
  `build-redline-full.sh:156` the 2020 old-label.
- **Manifest has no ownership:** `article-manifest.json` carries only `typ`/`splice`/`data`/
  `conditional_on`/`parity`/`pad_to`; `manifest.py:34` `has` tests `entry.get("units")`;
  `:46-49` the six pipe-delimited fields; `build-standalone.sh:144` reads `markers` as exactly two
  words. Unregistered data reads: `source/article-02.typ:360`
  `json("article-02-data.json")`, `source/cross-section-plates.typ:275`
  `json("exhibits/cross-sections/types.json")`.
- **Two sources of truth for splices:** `grep -c manifest build/build-full-czc.sh` → **0**; splices
  hardcoded at `:90`, `:114-117`.
- **Divergent split-failure handling:** `build-full-czc.sh:155-158` (silent fallback, plates to the
  end) vs `build-standalone.sh:146-148` (`exit 1`).
- **Hardcoded adoption artifacts:** `build-adoption.sh:150` the Article 3 literal filename;
  `:197-215` the Summary skeleton's 2020 baseline sentence and four-point list; `:245-252` recap
  labels; `:258-261` the `--freeze-date` re-run warning; `:130` bare `mkdir -p "$OUT"`.
- **Non-atomic output:** `build-full-czc.sh:46` `mkdir -p` before any render, `:243,248` pandoc
  stdout discarded; `build-standalone.sh:49`; only `toc_links.py:44-47` uses `os.replace`.
- **Fifth-code blockers:** `source/article-02.typ:224` `glyphs`, `:339` the four-code Note;
  `legend.py:68` `_REQUIRED_CODES`, `:128-137` the `' Required'`/`' Permit'` grammar, `:150-151`
  the early `break`; `build_use_matrix.py:210,252` the literal 63, `:219` the seeded counter,
  `:228` the bare subscript vs `:238`'s `.get`; `citation.py:475,536`; `app/main.py:372,1502`;
  `render/worksheet.py:124`; `app/templates/worksheet.html:63`.
- **Superseded-ruleset hazard:** `lift_use_matrix.py:40-41` defaults
  (`DEFAULT_RULESET_KEY = "adopted"`, `DEFAULT_SRC = source/article-02-data.json`);
  `build_ruleset.py:153` `rc = _lift_use_matrix.main([])`.
- **Next-adoption citation drift:** `build_edition.py:148` matches on `old_key` +
  `SUPERSEDED_SCHEME` (`:70` = `"adopted"`); `build_subdivision_criteria.py:529-530` writes the
  literal `"adopted"`.
- **Crosswalk matches on section number:** `crosswalk.py:19`, `:247` (the claim is written into
  `rulesets/article-map.json`).
- **Contract's section claim, five sites:** `CONTRACT.md:753`, `:734`, `app/citation.py:75`,
  `app/citation.py:211`, `crosswalk.py:247`.
- **Spec drift:** `ADOPTION-SPEC.md:3` (status), `:135` ("both sides", three rules), `:301` ("Each
  gate refuses; none warns") vs `pdf_recap.py`'s `main()` printing and returning 0, `:380-382` (the
  open standalone question).
- **Stale frontmatter ships inside the adopted `.md`:**
  `source/article-03-streets-roads-driveways.md:4` `footer-date: "Draft v0.2-draft"`, carried into
  `releases/v1.0-adopted/Newcastle CZC (Adopted v1.0).md:258`;
  `adopted_residue.py:52` receives the `.md` as a basename only; `:29`
  `MUST_SURVIVE = ("drafts the official map",)`.
- **Test pins:** `test_build_adoption.py:28` `EXPECTED_TOTAL = 151` (with `:11-17` saying to re-pin
  by hand); `test_structural_note.py:46,108,118`; `test_footer_modes.py:25,33-35,41-43`;
  `adoption_map.py:27` `ENV_OVERRIDE = "ADOPTION_MAP"`.
- **Identity-gate premise:** `build-full-czc.sh:398` is a plain `cat`, so the combined `.md` carries
  no mode-varying chrome; `ADOPTION-SPEC.md:319-320` claims it does.

### INFERRED or unverified — resolve before relying on these

1. **Byte-identity of two Typst builds of the same source.** P1's default-preservation test is
   specified against *extracted text* for this reason. **Confirm:** build Article 7 standalone
   twice into throwaway versions and `cmp` the PDFs. If they differ, no byte-equality assertion
   anywhere in this plan is valid.
2. **That `build-standalone.sh` actually builds Articles 1, 2 and 4–9 today.** Mechanically sound —
   all nine have a prose source and all three codepaths are reachable — but **no test builds a
   standalone for any Article other than 3** (`test_footer_modes.py:144,150,159` all pass `"3"`).
   The CLAUDE.md note that Articles 1, 2 and 7 were verified is a 2026-06-21 manual observation.
   I did not run them, because the missing `OUT_DIR` seam would have written into `releases/`.
   **Confirm:** `bash build/build-standalone.sh N v9.98-draft` for N in 1,2,4..9, then
   `rm -rf releases/v9.98-draft`.
3. **Whether the Article 2 chrome defect is in the unit or in assembly.** I measured the assembled
   PDF only. **Confirm:** render `source/article-02.typ` alone at a known offset and read page 1's
   text.
4. **Whether `build-adoption.sh` would overwrite an already-frozen `releases/v1.0`.** `:130` is a
   bare `mkdir -p` and `version_state.py --require adoption v1.0` exits 0, but I did not trace every
   branch. **Confirm:** `bash build/build-adoption.sh v1.0 "X" --dry-run` and read the path.
5. **The shape of Right to Farm's new Article 7 §3.** The branch is not in this tree, so whether
   `parse_articles.py` counts it as a 65th use turns on whether it carries a `DEFINITION`
   subsection (`parse_articles.py` keys on exactly that). **Confirm:** `parse_articles.py --verify`
   against the `right-to-farm` branch.
6. **The exact count of changed `inventory.json` leaves across recent tags,** and the discrepancy
   between CLAUDE.md's "42 Type corrections" for v0.22 and the ~32 `type` changes plus one removal
   visible in the tag diff. **Confirm:** run P10's keyed differ on `v0.21-draft..v0.22-draft` before
   trusting either number as a positive control.
7. **Whether Right to Farm includes the fifth status code at all** (Open Decision D3). The brief
   lists it; the spec is on another branch. Everything in P15's ordering depends on the answer.
