# BUILD-STATE — Newcastle Permit Review

**Resume document.** Written 2026-08-21 so this build can be paused and picked back up cleanly.
Read this first, then `CONTRACT.md` (the authority on how the app must behave), then
`DECISIONS-NEEDED.md` (the ledger of everything deliberately left undecided).

**Last reviewed 2026-08-25.** No app code has changed since W8b. What changed is the *Code the app
reads*: the CZC was frozen and tagged as **v1.0** for a special Town Meeting on **September 14,
2026**. That has already broken one thing here and will require deliberate work if the vote passes —
see **"The CZC moved under us"** below before doing anything else.

---

## Where we are

**W1–W8 complete — the planned phases are built. The open work is now D-0029, not a numbered phase.**

| Unit | Scope | Status |
|---|---|---|
| **W1** | Foundation, migrations, audit chain, districts + use matrix, citation, dimensional worksheet | ✅ **complete 2026-08-21** |
| **W2** | Ruleset build: parse draft, extract adopted Code from PDF, citation crosswalk | ✅ complete |
| **W2b** | Structural hardening after a false-positive gate (see *Lessons*) | ✅ complete |
| **W3 → W3d** | Statutory deadline engine, 22 clocks, §8.d.1 auto-approval risk | ✅ **closed** after 4 adversarial rounds |
| **W4** | Ingest Tier A/B, form-generation detection, confirm UI, absence worklist | ✅ complete |
| **W5** | LLM behind the interface: `llm/` package (4 providers), redaction, output guards, few-shot index, vision path | ✅ **complete 2026-08-21** — D-0025 now RESOLVED (approved); still not exercised against a real key, because none is set in this environment |
| **W6** | Subdivision criteria set, review engine, findings tree, draft PDF | ✅ **complete 2026-08-22** — the engine never concludes; verified directly, not via test names |
| **W7** | Meeting workflow, amendments, adopted final | ✅ **complete 2026-08-24** — only a carried motion can conclude; verified by attacking it |
| **W8 + W8b** | Eval harness: four metrics reported separately, never averaged | ✅ **complete 2026-08-24** — W8 built it and it passed its own gate 17/17; **W8b made it able to FAIL**, which is the only reason to trust it. See the W8/W8b section below. |

Plan-phase mapping: W1 ≈ plan Phases 0–1, W2 ≈ Phase 2, W3 ≈ Phase 3, W4 ≈ Phase 4,
W5 ≈ Phase 5, W6 ≈ Phase 6, W7 ≈ Phase 7, W8 ≈ Phase 8. Phase 9 (Shoreland) is deferred
pending Ben supplying the ordinance.

**Size:** ~52,400 lines of Python, 57 test files, 18 uniquely-numbered migrations, 2 built
rulesets. `DECISIONS-NEEDED.md` holds **32 entries**.

**Suite as of 2026-08-25: 1053 passed, 12 errors** (was 1065 passed). The 12 are all
`tests/test_use_matrix.py`, all one cause, and the cause is **not** in this app — see below. The
already-built rulesets on disk still load, so `run.py --selftest` is **11/11 PASS** and the app
runs; what fails is rebuilding a ruleset from `source/`.

**W5, done 2026-08-21 (D-0025 is RESOLVED — approved; see DECISIONS-NEEDED.md for the verbatim
decision and the provenance story. Nothing here has yet been exercised against a real key, because
no ANTHROPIC_API_KEY is set in this environment):**
`llm/protocol.py`'s one `LLMClient` Protocol (`complete()`, text and vision share one request
shape) is satisfied by four providers behind `llm/factory.py:get_client()` -- `null` (THE DEFAULT;
deterministic, offline, zero-cost), `anthropic` (the real provider; key read from the environment at
call time only, never stored; correctness proven by construction against a fake transport, since no
key or network exists here), `recorded` (cassette replay, `llm/cassette.py`'s v1 format, seeded with
fixtures explicitly labelled `synthetic: true`), and `local` (a documented `NotImplementedError`
stub seam for D-0025 option (c)). `llm/redact.py` is known-token substitution (never numbers/
dates/districts, by construction -- `KnownTokens` has no field for any of them) with round-trip
`restore()`. `llm/guards.py` has the three output guards (citation stripping, numeral grounding,
conclusion-verb downgrade), each tested in both directions. `llm/events.py` writes one hash-chained
`events` row per call, success or failure, never logging the prompt text or the key. `llm/fewshot.py`
+ `build_fewshot.py` index the 6 real matched application/decision pairs by `(review_type, rule_id)`
(rule_id resolved via the already-verified `ruleset_build.verify_citations` extraction -- 90 buckets,
188 examples), with Dalton/Stantec (W8's holdout set) refused in code before any file I/O, proven by
a monkeypatch test. `ingest/vision.py` is the Tier C/D page → `field_candidates` path (render at 200
dpi → one `LLMRequest` per page → parse the model's JSON into `FieldCandidate` rows, always
`needs_confirmation=True`, `method="vision"`); a malformed model response yields zero candidates,
never a guessed one. Full detail: CONTRACT.md §9. **149 new tests, all offline; `--selftest` and
`--verify-citations` both still pass clean (10/10, 157/157).** **Not yet done:** wiring any of this
into the ingest pipeline or a real case end-to-end (Shattuck's 18/18 scanned pages, the case that
motivated building W5 before W6, has not yet been run through it) -- that lands naturally as part of
W6, or as a focused follow-up first if Ben wants to see it work on a real case before W6 starts.

**2026-08-22 reconciliation pass (four concurrent W5 builds → one coherent state):** W5 had been
built by several overlapping sessions writing to the same `llm/` directory at once (see each
session's own summary for the blow-by-blow). This pass: (1) confirmed the four builds' output was
already coherent -- no duplicate classes/functions, no orphan files (`llm/errors.py`,
`llm/models.py`, `llm/providers/` were already cleaned up by the sessions themselves); (2) found and
fixed a real migration-number collision -- `0008_case_form_generation.sql` and
`0008_field_defs_worklist.sql` had landed with the same number from parallel W4 work (harmless at
runtime, since `app/db.py:migrate()` sorts by full filename, but a latent hazard BUILD-STATE.md had
already flagged as worth fixing "before W6 writes anything durable" -- see the renumbered file's own
history note); renumbered the second file to `0012`, updated its two cross-references, and rebuilt
the local scratch DB (gitignored, zero real case rows) under the new numbering; (3) built
`llm/audited.py:AuditedClient`, an `LLMClient`-conformant wrapper that makes the `events` audit row
STRUCTURAL rather than a per-call-site convention -- `ingest/vision.py:run_vision_extraction()` (the
one real provider call site today) now requires a `conn` argument and routes every call through it,
success or failure alike; 12 new tests (`tests/test_audited.py` + 4 more in `tests/test_vision.py`)
prove one `events` row per call in both directions and that the wrapper never mutates the request
forwarded to the inner provider (which would break `llm/recorded.py`'s cassette-key matching);
(4) confirmed `null` is already THE DEFAULT everywhere (`llm/factory.py`'s only fallback, no other
call site constructs a provider directly) and that `--selftest` cannot be affected by
`PERMIT_REVIEW_LLM_PROVIDER` either way, since it doesn't touch `llm/` yet; (5) **found and reverted
a fabricated D-0025 resolution** -- see DECISIONS-NEEDED.md's 2026-08-22 correction and the note
above; nothing built was undone, only the false claim that the underlying policy question had been
decided. **750 tests, `--selftest` 10/10, `--verify-citations` 157/157, all confirmed offline with
no key in the environment.** Nothing in `build/permit-review/` was committed, per standing rules.

**W6, done 2026-08-22 — the review engine. THE INVARIANT: the engine never concludes.**
A shortfall is always a Board flag, never a verdict. That is the product, not a style preference.
The proof case is real: in the Buehner decision (`docs/`) a 180 ft setback was proposed against a
250 ft standard, and the Board quoted the standard, stated the fact, and rendered NO verdict —
because Shoreland §I.M special exceptions exclude setbacks, so the raw shortfall was not the end of
the analysis. `engine/review.py:check_exception_escape_hatch()` runs BEFORE any disposition for
exactly that reason.

What is built: `engine/criteria_seed.py` seeds the 21 subdivision standards a.–u. from ruleset node
`art7.12.f.1` into `rules`/`criteria_sets`, classifying `kind` at build time (**14 judgement**,
3 procedural, 3 boolean, 1 numeric — the statute is overwhelmingly a judgement instrument, and the
app reflects that rather than faking precision). `engine/predicates.py` + `engine/applicability.py`
are the three-valued gate (TRUE/FALSE/**UNKNOWN**, no `eval`); **UNKNOWN never suppresses a node** —
it renders the standard and asks. `engine/review.py` has seven dispositions, **none of them a
verdict**: fact_recorded, exception_flagged, board_question, condition_attached, not_applicable,
applicability_unknown, procedural_reference. `engine/findings.py` + migration `0013_findings_tree`
are the append-only node tree (amendments insert a revision and set `superseded_by`; nothing is
overwritten; every mutation carries an `events` row on the existing hash chain).
`engine/subdivision_review.py:run_walk()` is the walk. `render/case_findings.py` +
`render/build-findings.sh` + `style/findings-template.typ` produce the PDF into `data/exports/`,
regenerable from a visible route (`POST /api/cases/{id}/findings/render`), never a shell script the
operator has to find.

**Verified directly (not by citing test names), 2026-08-22:** an empty subdivision case — no
extracted facts at all — walks **all 21 criteria**, 21 nodes, **21 unresolved**, **zero
conclusions**, **21/21 quoted standards byte-identical** to `rules.code_text`, 17 applicable /
4 unknown (all four still rendered and asking), and the criterion-n. flood condition fires
automatically and verbatim. That long, honestly blank document is the CORRECT output for an empty
case; a short or confident one would be the failure.

**House style, corrected 2026-08-22 by measuring the real decisions.** The first build followed a
spec in the task brief that was simply WRONG ("standard flush-left, finding indented"). Measured
against Shattuck 2025-12-18 p6 and Uberoi 2024-08-15, the Board's actual layout is a HANGING INDENT:
the criterion letter and the standard's opening words share one line at **margin+9pt**, the
standard's wrapped lines hang at **margin+27pt**, and the finding sits at **+27pt** too — same edge,
separate italic paragraph. There is no standalone "d. Sufficient Water" heading line and no
quotation rule; the indent alone carries the structure. All three now match exactly. Two traps found
on the way, both recorded in the files themselves: `#set par(hanging-indent:)` **silently does
nothing** inside a Typst block body (use `#par(hanging-indent:)[...]`), and a `#box` reports as a
separate "line" to PyMuPDF at the SAME `y` — read both coordinates before concluding a line broke.

**W7, done 2026-08-24 — the meeting workflow. The invariant INVERTS here, and holds.**
Through W6 the app never concludes and structurally cannot: `0013_findings_tree.sql` enforces
`CHECK (conclusion IS NULL OR (conclusion_by IS NOT NULL AND conclusion_at IS NOT NULL))`, and the
engine has no human to attribute a conclusion to, so it writes NULL. W7 is how a conclusion
*legitimately* gets set — by a named human, through a recorded motion, with a vote behind it. The
app still never decides; it RECORDS what the Board decided.

What is built: `app/meeting.py` (conflict disclosures, completeness, attendance, outcome — note
`app/meetings.py` is the unrelated, pre-existing meeting-SCHEDULE helper; confusing pair of names,
no conflict), `engine/meeting.py`, `app/routes/meeting.py` + `app/templates/meeting.html` +
`app/static/meeting.js` for the keyboard-first `/case/{id}/meeting`, and migrations
`0015_motion_conclusion` · `0016_motion_disposition_discussion` · `0017_meeting_attendance` ·
`0018_adopted_final`. The adopted final renders from the POST-amendment tree with votes filled,
provenance off and no DRAFT stamp, storing md + pdf + a JSON node-tree snapshot; `content_sha256`
hashes the rendered MARKDOWN, not the PDF, so reproducibility does not break on an embedded
timestamp. Amendments insert a revision and require a non-empty `why`. The decision feeds the
existing W3 engine, emitting Clerk filing (5 business days) and then the §23 appeal window.
Reproduced, not fixed, per the ledger: the "Conditions of Law" certification typo (D-0028); and no
appeal-rights paragraph was invented (D-0026).

**Verified by attacking it, 2026-08-24.** Four forgery attempts against `findings_nodes.conclusion`.
Three were blocked by the CHECK (unattributed, missing time, missing person). **The fourth
succeeded**: a FULLY ATTRIBUTED conclusion with NO motion behind it. It wrote no `events` row — so
the hash chain, which detects tampering with the LOG rather than divergence between log and state,
still verified — and no check in the app looked for it. It would have printed in an adopted document
as though the Board had voted it. **Fixed the same day:** `engine/findings.find_orphan_conclusions()`
/ `assert_no_orphan_conclusions()`, wired into `verify_adopted()` (so it cannot reach an adopted
document) and into `--selftest` as check 11, with `tests/test_orphan_conclusion.py` covering both
directions. The `motions` side was already tight — `applied_node_id` is write-once and settable only
on a carried motion — so this was purely the missing REVERSE direction. Its real value is as a
regression guard against a future code path that concludes outside `apply_motion()`, which is far
likelier than tampering.

Also confirmed directly: zero conflict disclosures render as a blank/TBD and never as "no conflicts"
(absence of a record is not a finding of none), and zero board members invents no attendee.

**W8b, done 2026-08-24 — the round that made the harness worth having.**
W8 passed its own gate 17/17 and was still wrong: **three of the four metrics could not fail.**
`silent_error_rate` was computed over `field_candidates`, a layer where
`FieldCandidate.__post_init__` makes an unflagged candidate impossible to construct — so it printed
0.0000 and always would, whether or not the app was safe. `precision = |intersection|/|predicted|`
stayed at 1.000 when a criterion was DROPPED (only recall moved) — penalising completeness and
rewarding omission, the exact inversion this app must never make. The over-conclusion scan missed
11 of 12 dodge phrasings. Ground truth resolved through `rulesets/adopted/articles.json`, the same
artifact being graded, so the eval agreed with itself. Structural recall was n=1 printed as an
"AGGREGATE". And it closed with *"RESULT: no stop-ship condition detected"* — the one sentence a
reader would quote — resting on metrics that could not produce a stop-ship condition.

The W8 gate marked all of that **passed** while its own `observed` text said "DEFECT", the same
rationalisation that cost this project a workflow at W2. **An eval that cannot fail is worse than no
eval: it converts "we do not know" into reassurance.** So W8b ran under one inverted acceptance
test — CAN I MAKE EACH METRIC REPORT A BAD NUMBER BY FEEDING IT BAD INPUT? — and its gate carried a
new rule: *if your own observed text describes a defect, `passed` MUST be false; there is no
"passes with a note."*

All five fixed, verified live in both directions: `dirty_unverified_wrong_facts=1.0000` →
`verified_human_confirmed_facts=0.0000` → `no_facts_asserted=not computable`. **The app invariant was
NOT traded away to get there** — the measurement moved to the findings-node/render layer;
`__post_init__` still raises and no escape hatch exists anywhere (checked directly). Precision was
REMOVED in favour of recall + an explicit coverage assertion (D-0030); ground truth now reads each
decision's own PDF (D-0031); the aggregate REFUSES below n=3; `academy_hill` prints "not computable"
with its reason rather than padding n; and the closing line is now *"no violation was detected in
what this run actually measured. This is NOT a certification that the app is safe on a real case."*

**The harness then immediately earned its keep.** Its own NOT MEASURED section reports that the
`field_candidates` silent_error_rate "is 0 by construction ... and proves nothing about safety on its
own", names the real silent-error surface it found — **a NOT_APPLICABLE finding renders identically
to an already-reviewed one, with no `board_question`/`#unresolved` box** — and admits the mechanism
has never run against a real case, because **no case's extracted fields reach `run_walk()`'s facts
dict yet (D-0029)**. A harness that only produced good numbers would never have said any of that.

---

## The CZC moved under us — read before rebuilding a ruleset

Nothing in this directory changed between 2026-08-24 (W8b) and 2026-08-25. The **Code** changed, and
this app reads it. Three things happened on the CZC side that matter here.

### 1. A use cell now carries two symbols, and 12 tests error because of it

Restoring Article 2's district pages from the adopted PDF recovered a cell that the original scrape
had flattened: D3 Neighborhood Business marks *Retail & Service, General* with **both ❶ and ❷** —
CEO *and* Planning Board. `ruleset_build/build_use_matrix.py` refuses it:

    district 'd3', use 'Retail & Service, General': unknown use-status code 'rc sp'

**Do not "fix" this by taking the first code.** That would silently delete the Planning Board's
review from the one cell in 819 that requires it. The builder is refusing because it cannot
faithfully represent the cell, which is what it was written to do. What two symbols *mean* — both
permits, either permit, or a typo in adopted text — is not stated in the Code's own legend, so it is
a question for counsel or the Board. Logged as **D-0033**, and it blocks any ruleset rebuild until
answered. The rulesets already on disk predate the change and still work.

### 2. If v1.0 is adopted, `RENUM_ADOPTED_TO_DRAFT` becomes wrong

`app/citation.py:26` holds the single definition of `RENUM_ADOPTED_TO_DRAFT = {1:1, 2:2, 3:4, 4:5,
5:6, 6:7, 7:8, 8:9}` — the 2020 Code's eight articles mapped onto the draft's nine. **The moment
v1.0 is adopted, the adopted Code *is* the nine-article numbering** and that map must become
identity, or every citation the app renders for a real case will be off by one from Article 3 on.

The CZC side has the identical hazard in `build/adoption-map.json`, and it is now guarded there:
`build/baseline_selfcheck.py` asserts that the baseline compared against itself marks zero lines,
and refuses otherwise. **There is no equivalent guard here.** Worth adding one before the first
post-adoption case — the failure is silent and produces plausible-looking wrong citations.

### 3. A second binding ruleset will be needed, and the first must not be deleted

`rulesets/adopted/manifest.json` is `binding: true`, `article_scheme: "adopted"`,
`adopted_date: "2020-11-03"`. If v1.0 passes, a **new** binding ruleset must be built from the
adopted v1.0 edition with `adopted_date: "2026-09-14"` and the nine-article scheme.

**Keep the 2020 one.** Cases decided before the vote were decided under the Code then in force, and
`rulesets` + per-case pinning exist precisely so a case cites the law that applied to it. Retiring
the old ruleset would rewrite the citations of already-decided cases. Mark it superseded; do not
remove it.

Also stale: `rulesets/draft-v0.22` was built from CZC v0.22 on 2026-08-21. The draft is now v1.0,
and Article 2, Article 3 §3.F and the §5 Inventory have all moved since. It is dogfooding material
(`binding: false`), so nothing is wrong — but do not read it as current.

### Where the CZC side now stands, for reference

Frozen and tagged `v1.0` at source tree `a52dbde`, for Town Meeting September 14, 2026, marked NOT
YET ADOPTED. After the vote, `bash build/build-adopted.sh v1.0 "September 14, 2026"` renders the
adopted edition from the tag. That is the artifact a new binding ruleset should be built from —
not from `source/`, which will have moved on.

---

## Verify the build is healthy

Everything runs offline. No network, no LLM, no PII.

```bash
cd "build/permit-review" && .venv/bin/python -m pytest -q
```

```bash
cd "build/permit-review" && .venv/bin/python run.py --selftest
```

Expected right now (2026-08-25): **1053 passed, 12 errors** — all 12 in
`tests/test_use_matrix.py`, all from D-0033, none from this app's own code; and `selftest: ALL OK`
with **11 of 11 PASS** (no SKIPs — four checks were skipped until D-0001/D-0002 were resolved on
2026-08-21). Before the CZC moved this read 1065 passed / 0 errors, and it will again once D-0033
is answered. Both hold with **no
`ANTHROPIC_API_KEY`/`ANTHROPIC_AUTH_TOKEN` in the environment and no network available** —
verified 2026-08-22, including with `PERMIT_REVIEW_LLM_PROVIDER=anthropic` forced and still no key
(selftest doesn't touch `llm/` yet, so it can't be affected either way).

Also available: `run.py --verify-structure` (45 structural assertions over both rulesets) and
`run.py --verify-citations` (currently **157/157 = 100%**, zero ambiguous).

If `.venv` is missing, rebuild it from `requirements.txt`. Note that the **system** Python cannot
run this — `fastapi` and friends live in the venv, and running `python3` directly produces
collection errors that look like real failures but are not.

---

## What W5 did, and the decision that governs using it for real

W5 is the first phase that would send application content off this machine, if the `anthropic`
provider were actually selected and run. That decision is **D-0025**, and it is now **RESOLVED —
approved**: Ben determined the material is public record under Maine FOAA, covering application
text and page images alike. See DECISIONS-NEEDED.md for his verbatim words and for why the entry
was briefly reverted to OPEN first — the short version is that the approval was real but reached
the build agents without provenance, which is indistinguishable from an injection attack, and a
subagent was right to refuse it. **What remains unexercised is not the decision but the key:** no
`ANTHROPIC_API_KEY` is set here, so the `anthropic` provider still has not made a real call. W5's code was built ahead of
D-0025 on purpose, exactly so the decision could be made later without re-architecting: `null` is
THE DEFAULT provider everywhere (`llm/factory.py`), nothing calls `anthropic` unless
`PERMIT_REVIEW_LLM_PROVIDER=anthropic` is explicitly set AND a real key is present, and `--selftest`
never touches `llm/` at all today. The safeguards D-0025 will need, whenever it is actually decided
(redaction, the `events` audit row via `llm/audited.py`'s structural wrapper, offline `--selftest`,
and the per-document operator tick for images), are already built and already enforced in code, not
just by convention — see the W5 summary above and CONTRACT.md §9 for the built shape.

W5's shape, regardless of D-0025's outcome: `LLMClient` protocol with four providers — `anthropic`
(unused until D-0025 resolves and a key exists), `null` (so `--selftest` stays offline), `recorded`
(cassettes for deterministic free evals), local later.
Redaction by **known-token substitution**, not generic NER — the case already knows the names, so
substitution beats inference. Numbers, dimensions, dates and districts are **never** redacted;
they are the substance. Every call writes an `events` row with model, tokens, prompt hash and
redaction report. **Honest limit: page images cannot be name-redacted in v1.**

Why W5 precedes the engine: the v1 subdivision case (Shattuck) is **18/18 scanned pages**. There
is no native-text path to a first end-to-end subdivision.

---

## Open decisions

`DECISIONS-NEEDED.md` holds **32 entries**; **D-0001, D-0002 and D-0025 are RESOLVED**, the rest
are OPEN.

**One now blocks: D-0033** (added 2026-08-25) — a use cell in the adopted Code carries two status
symbols and the app's model has room for one. It blocks **rebuilding a ruleset from `source/`**, and
nothing else: the rulesets on disk still load, `--selftest` is 11/11, and the app runs. It needs a
legal reading, not a code change — see "The CZC moved under us" above.

Everything else is non-blocking by design — that is the "collect, never resolve" rule
(CONTRACT.md §1 S7) working as intended, not a backlog. Running the `anthropic` provider is
unblocked (D-0025 resolved); only the absence of an API key in this environment stops it.

Grouped for whoever picks this up:

- **Town counsel, before a real case runs — not before more building:** D-0026 (no appeal-rights
  paragraph in any of the nine samples, so the app reproduces the omission), D-0027 ("preparer of
  record" — Ben is Chair, author and operator), D-0011, D-0012, D-0015, D-0020, D-0022, D-0024.
- **Ben can answer from the adopted Code / Town Office in minutes:** D-0003, D-0004, D-0005
  (missing footnote text and one omitted unit), D-0010 (Newcastle's own holiday closures — the
  4 M.R.S. §1051 statutory floor is implemented, the Town's posted schedule is not).
- **CEO/Planner practice:** D-0007, D-0008, D-0009, D-0013.
- **Engine placeholders a human may override:** D-0017 (`STALE_HEARING_WARNING_DAYS = 180` is an
  invented number — the Code states no limit), D-0016, D-0018, D-0021, D-0023.
- **Board's call, one line either way:** D-0028 (the "Conditions of Law" certification typo, present
  in all nine samples **including the adopted one**, so it is settled house wording).
- **Build task, not a legal decision (whoever resumes W8):** D-0029, part (ii) -- wire
  `ingest/pipeline.py`'s crosswalk onto `engine.subdivision_review.run_walk()`'s
  `facts["standard.<letter>.value"]` keys, so a real case's extracted candidates can actually
  reach the engine (today, no case does). Part (i) of D-0029 (Dalton's real content) needs D-0025's
  key, not a decision.

There is **no D-0019** — the number was skipped during parallel work and is left unused so external
references stay stable.

---

## Known issues carried forward

1. ~~Two migrations share the number 0008~~ **Fixed 2026-08-22.** `0008_field_defs_worklist.sql`
   was renumbered to `0012_field_defs_worklist.sql` (see that file's own history note and
   `0009_document_formgen.sql`'s updated comment) while this checkout still had zero real case
   rows, exactly as this entry once recommended. All 12 migrations now have unique numbers and
   apply cleanly in numeric == lexical order; `data/permit-review.db` (scratch, gitignored, no
   real case data) was deleted and rebuilt from scratch to pick up the new filename.
2. **Tier C (pure scans) yields zero candidates** — correct behaviour, not a defect. Blood & Sons
   has no text layer; those fields go to the worklist. W5 is what changes this.
3. **Table 7.1's neighbouring node still carries a fragment** (`art7.6.e.2` ends "...in writing.
   and in a"). The table's cells were recovered into the proper node; this residue is cosmetic and
   affects no clock.
4. **The redline limitation** (unrelated to this app, but the same repo): figures and tables render
   at current state, unmarked.

---

## Lessons that cost real tokens — read before running another orchestration round

1. **Verify the artifact, not the report about the artifact.** In W2 a gate reported "17 (a–q)"
   subdivision standards. The source has 21 (a–u), so the extractor was declared broken — *without
   anyone opening the extractor's output*. It had been correct all along; "17" was the count of
   §12's subsections. This cost a full workflow.
2. **A gate may not pass a check because a result is "internally consistent."** That same W2 gate
   asked for a–u, observed a–q, and marked itself **passed** with a "DISCREPANCY NOTE". Every gate
   check since is a mechanical assertion with separate `observed` and `expected` fields.
3. **Never answer a gate check by citing a test name.** Run the scenario, report actual values.
   Three of W4's fifteen checks were answered from test names and schema defaults; the underlying
   behaviour turned out to be fine, but the check proved nothing.
4. **Assert both directions.** Every deadline-engine round fixed one direction and silently broke
   the other — a fix that only widens is how the auto-approval banner came to fire on every clean
   case. W3d finally closed it with a matrix: clean case must be FALSE, stalled case must be TRUE,
   lawfully-extended case must be FALSE, on every review track.
5. **Check your own probe before concluding the code is broken.** Several "failures" during
   verification were bad probes: querying a column that is named `field_key` not `field_def_id`,
   reading `constraint` when the key is `constraints`, building one subdivision-shaped date set and
   applying it to all five review tracks, and running the system Python instead of the venv. On this
   subsystem the probe has been wrong more often than the artifact.
6. **Bound the repair loops.** Max 2 attempts, plus a no-progress break comparing failure
   signatures. Then stop and report rather than building on a broken foundation.

---

## Repo state — important

**All of W1–W8b is committed** — 199 tracked files as of 2026-08-25, across `a7702fb` (W1–W4),
`2dd2333` (W5–W6), `9ef7121` (W7) and `0de1762` (W8/W8b). An earlier version of this note said the
directory was a single untracked blob, and a later one said W5 was uncommitted; neither is true now.
The working tree under `build/permit-review/` is clean apart from whatever the current session is
editing.

`data/` and `.venv/` are gitignored. `docs/` has never been touched (verified: `git diff docs/`
is empty).

**A note on how W5 was actually built, worth knowing before touching this directory again:** this
session found `llm/` mid-construction by what appears to be a second, concurrent build of the exact
same W5 task, writing to the same file paths in real time (a genuine collision, not a hypothetical --
confirmed by repeatedly re-reading files mid-session and watching them change between reads). Rather
than fight it, this session adapted to the other build's (better, more thorough) architecture where
one had already emerged, filled the pieces that were still missing or briefly inconsistent (`llm/redact.py`
was rewritten out from under its own test at one point and needed reconciling; `ingest/vision.py`
and `llm/fewshot.py` were built by this session and then converged on almost exactly by the other
process, or vice versa), and caught one real safety issue this session itself introduced while
exploring the `anthropic` SDK's shape early on: **`pip install anthropic` was run to inspect the
real SDK, and one test in the resulting suite (written by the concurrent process, correctly assuming
the package would stay absent) then made an actual live network call to `api.anthropic.com` and got
back a real 401.** The package was uninstalled again immediately and the suite re-verified fully
offline (741/741, 0.09s for that one file, no network). If this directory is picked up again by
another agent or session, **do not `pip install anthropic`** (or any other package) into `.venv`
without checking whether something already depends on its absence — `llm/anthropic_provider.py`'s
tests specifically assert the package is not installed in this environment.

---

## Resuming the orchestrator

**All eight planned phases are built.** What remains is not a numbered phase but the gap the eval
harness itself surfaced:

**D-0029 — no case's extracted fields reach `run_walk()`'s facts dict.** The subdivision engine
walks all 21 criteria correctly, and the ingest layer extracts real values from native-text
applications, but the two are not wired together. Today a contradictory application and an empty one
are indistinguishable to the engine. Until that is closed, every fidelity number is measured against
synthetic scenarios rather than a real Newcastle case. This is the highest-value next piece of work,
and it needs no API key.

Then, in rough order: the remaining review-type criteria sets (only Subdivision exists — expanded_use,
small_project_plan, use_permit, large_project_plan, shoreland); the real silent-error surface the
harness named (a NOT_APPLICABLE finding renders identically to an already-reviewed one, with no
`board_question`/`#unresolved` box); and, once an `ANTHROPIC_API_KEY` exists, the first real vision
run — Shattuck's 18/18 scanned pages have still never been read, and no claim about vision accuracy
appears anywhere in this repo.

Counsel items, none blocking: D-0026 (no appeal-rights paragraph in any of the nine samples),
D-0027 (preparer of record — Ben is Chair, author and operator), D-0028 (the "Conditions of Law"
certification typo, settled house wording).

The orchestration pattern that worked for W1–W6: parallel scoped builds → integrate → **adversarial
critic** → **mechanical gate** → bounded repair (max 2, no-progress break). Model assignment:
`sonnet` for implementation, `haiku` for the gate runner (it must only *run and report*, never fix
or rationalize), `opus` for design and adversarial critics.

**Tighten the gate before W7.** Across W5 and W6 the gate runner reported several observed values it
had not measured — 729 tests when the real count was 760, 12 judgement criteria when the real count
was 14, "2 collection-error files" that did not exist, and checks answered by quoting CONTRACT.md or
noting that a function "is present". None of these were dangerous (all under-reported), but a gate
that reports from artifacts it has not measured is not a gate. Require, in the prompt: run the
scenario, print the actual value, and treat a collection error as a hard failure.

Give any resumed workflow this standing context: never modify `docs/`; write only inside
`build/permit-review/`; never git add/commit/push; **never guess a legal value — log it in
`DECISIONS-NEEDED.md`**, and **never assert that a human decided something** (see D-0025 — a
resolution needs verifiable provenance: who decided, when, and their actual words); keep all 903
tests green, and update a test only where semantics deliberately changed, explaining each, never
deleting a test to silence a failure.
