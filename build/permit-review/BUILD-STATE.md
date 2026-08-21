# BUILD-STATE — Newcastle Permit Review

**Resume document.** Written 2026-08-21 so this build can be paused and picked back up cleanly.
Read this first, then `CONTRACT.md` (the authority on how the app must behave), then
`DECISIONS-NEEDED.md` (the ledger of everything deliberately left undecided).

---

## Where we are

**W1–W4 complete. W5 is next and is gated on one human decision (D-0025).**

| Unit | Scope | Status |
|---|---|---|
| **W1** | Foundation, migrations, audit chain, districts + use matrix, citation, dimensional worksheet | ✅ **complete 2026-08-21** |
| **W2** | Ruleset build: parse draft, extract adopted Code from PDF, citation crosswalk | ✅ complete |
| **W2b** | Structural hardening after a false-positive gate (see *Lessons*) | ✅ complete |
| **W3 → W3d** | Statutory deadline engine, 22 clocks, §8.d.1 auto-approval risk | ✅ **closed** after 4 adversarial rounds |
| **W4** | Ingest Tier A/B, form-generation detection, confirm UI, absence worklist | ✅ complete |
| **W5** | LLM behind the interface: vision reads + redaction | ⛔ **next — gated on D-0025** |
| **W6** | Subdivision criteria set, review engine, findings tree, draft PDF | not started |
| **W7** | Meeting workflow, amendments, adopted final | not started |
| **W8** | Eval harness + held-out run (Dalton, Stantec) | not started (`eval/` is empty) |

Plan-phase mapping: W1 ≈ plan Phases 0–1, W2 ≈ Phase 2, W3 ≈ Phase 3, W4 ≈ Phase 4,
W5 ≈ Phase 5, W6 ≈ Phase 6, W7 ≈ Phase 7, W8 ≈ Phase 8. Phase 9 (Shoreland) is deferred
pending Ben supplying the ordinance.

**Size:** ~31,000 lines of Python, 27 test files, **592 tests**, 12 migrations, 2 built rulesets.

---

## Verify the build is healthy

Everything runs offline. No network, no LLM, no PII.

```bash
cd "build/permit-review" && .venv/bin/python -m pytest -q
```

```bash
cd "build/permit-review" && .venv/bin/python run.py --selftest
```

Expected right now: **592 passed**, and `selftest: ALL OK` with **10 of 10 PASS** (no SKIPs —
four checks were skipped until D-0001/D-0002 were resolved on 2026-08-21).

Also available: `run.py --verify-structure` (45 structural assertions over both rulesets) and
`run.py --verify-citations` (currently **157/157 = 100%**, zero ambiguous).

If `.venv` is missing, rebuild it from `requirements.txt`. Note that the **system** Python cannot
run this — `fastapi` and friends live in the venv, and running `python3` directly produces
collection errors that look like real failures but are not.

---

## What W5 must do, and why it is blocked

W5 is the first phase that sends application content off this machine. That is **D-0025**, and it
is Ben's call:

> May application material — names, addresses, phone numbers, deed references, and **page images of
> scanned applications** — be sent to Anthropic's API?

It cuts both ways: a permit application filed with the Town may already be a **public record under
Maine FOAA**, which would shrink the exposure considerably. That is a legal question, to be
**confirmed, not assumed**.

Options recorded in D-0025: (a) approve, page images only for documents an operator ticks;
(b) text only, no page images; (c) local vision model instead (the `LLMClient` protocol already
allows it, at an accuracy cost); (d) confirm FOAA first, then choose.

**Do not start W5 without an answer.** Everything else in the app is offline by construction, and
that property should not be given up implicitly.

W5's shape, once unblocked: `LLMClient` protocol with four providers — `anthropic`, `null` (so
`--selftest` stays offline), `recorded` (cassettes for deterministic free evals), local later.
Redaction by **known-token substitution**, not generic NER — the case already knows the names, so
substitution beats inference. Numbers, dimensions, dates and districts are **never** redacted;
they are the substance. Every call writes an `events` row with model, tokens, prompt hash and
redaction report. **Honest limit: page images cannot be name-redacted in v1.**

Why W5 precedes the engine: the v1 subdivision case (Shattuck) is **18/18 scanned pages**. There
is no native-text path to a first end-to-end subdivision.

---

## Open decisions

`DECISIONS-NEEDED.md` holds **27 entries**; D-0001 and D-0002 are RESOLVED, the rest are OPEN.
**Only D-0025 blocks anything.** Everything else is non-blocking by design — that is the
"collect, never resolve" rule (CONTRACT.md §1 S7) working as intended, not a backlog.

Grouped for whoever picks this up:

- **Blocks W5:** D-0025 (third-party API / FOAA).
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

There is **no D-0019** — the number was skipped during parallel work and is left unused so external
references stay stable.

---

## Known issues carried forward

1. **Two migrations share the number 0008** (`0008_case_form_generation.sql`,
   `0008_field_defs_worklist.sql`), from parallel W4 work. Not a bug today: the runner applies
   `sorted(glob("*.sql"))`, so `case_form` < `field_defs` deterministically. It is a latent hazard —
   ordering depends on the descriptive suffix rather than the number. **Renumbering is free right
   now and expensive later:** the runner keys `schema_migrations` on filename and verifies a sha,
   so after real case data exists a rename reads as one missing migration plus one new one. This
   checkout has zero real case rows. Decide before W6 writes anything durable.
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

**Nothing in `build/permit-review/` has ever been committed.** `git status` shows the whole
directory as a single untracked entry, and HEAD is still `e956296` ("memo: one-page public-hearing
handout for Article 3"), unchanged throughout the build.

This is deliberate — the project's standing rule is to never commit without an explicit request —
but it means **~31,000 lines of work exist only in the working tree**, with no recovery point if
the directory is lost. Worth a decision before the next stretch of work.

`data/` and `.venv/` are gitignored. `docs/` has never been touched (verified: `git diff docs/`
is empty).

---

## Resuming the orchestrator

The next unit is **W5**, and it should not launch until D-0025 is answered. When it is, the
orchestration pattern that worked is: parallel scoped fixes → integrate → **mechanical gate** →
bounded repair (max 2, no-progress break). Model assignment that worked: `sonnet` for
implementation, `haiku` for the gate runner (it must only *run and report*, never fix or
rationalize), `opus` for design and adversarial critics.

Give any resumed workflow this standing context: never modify `docs/`; write only inside
`build/permit-review/`; never git add/commit/push; **never guess a legal value — log it in
`DECISIONS-NEEDED.md`**; keep all 592 tests green, and update a test only where semantics
deliberately changed, explaining each, never deleting a test to silence a failure.
