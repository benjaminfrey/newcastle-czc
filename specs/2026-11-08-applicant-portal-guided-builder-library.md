# Guided builder: the explanation library (design 2 of 5) — design

**Status:** approved by the chair (Ben Frey) on 2026-11-08, as written, including every
*builder's call*. Written from his interview of 2026-11-07/08, then checked by a
fresh builder, whose two questions he answered (decisions 15–16). Items marked *builder's call*
are the writer's, for him to check.

**Builds on:** `specs/2026-10-30-applicant-portal-guided-builder.md` (the experience design),
§6 "The explanation library", §11 (every word approved), §12 item 4 (who approves entries).
Design 1, the experience, is built and merged (plans 1–6, PRs #22–#28). The first slice of the
library is already in use: four approved entries in
`portal/api/portal_api/guide/definitions/entries.yaml`, carrying version, status, approver and
date.

## 1. Why

The guided builder promises **absolute consistency**: two residents with the same project read
the same words, and those words are the Town's, approved before anyone sees them (§3 decision 5).
The AI chooses entries and never writes them. Launch covers every standard in the Code (decision
7), so the library has to hold an approved explanation for every standard the guide can meet.
The portal opens to the public only when it does (decision 13).

Drafting and approving that library is the largest single piece of work in the project. This
design settles how entries are shaped, drafted, approved, put on the Town's record, kept in step
with amendments, and corrected.

## 2. Goals, non-goals, anti-goals

**Goals**
1. One library, in the repo, holding every word a resident reads that explains the Code. That
   means standard explanations, interpretations, the "So you mean…" templates, and (folded in)
   the words already approved.
2. An entry's numbers can never differ from the Code's tables, because they come from the
   ruleset and are never typed.
3. You can approve a whole Article's entries efficiently, seeing each one as a resident will.
4. Every entry a resident sees has been approved by the chair and ratified by the Board, and the
   record of both is in git.
5. An amendment can never leave a stale entry showing.
6. A wrong entry can be taken down at once.

**Non-goals**
- The bounded AI (design 3). This design gives it a library to choose from; it doesn't decide
  how it chooses.
- The CEO inbox and how new answers arrive (design 4). This design gives those answers a place
  and a path to approval.
- Rewriting the Code. Entries explain the adopted Code. Where the Code is unclear, the entry
  waits and the question goes to the chair (CLAUDE.md rule 6).

**Anti-goals** (a failure even if it works)
- A resident sees words nobody approved, or numbers that drift from the Code.
- An entry reads as the Town's decision. The never-used words (spec §10.3) stay banned.
- An entry claims more than the Code says, or stands in for it. Every entry carries "The adopted
  Code governs if anything here differs from it."
- Approval turns into rubber-stamping because the batches are unreadable.

## 3. The chair's decisions (interview, 2026-11-07/08)

1. **Approval:** the chair approves each entry. The Planning Board ratifies each Article's set.
2. **Going live:** an entry reaches residents only after the Board ratifies it.
3. **Drafting:** AI-drafted from the adopted Code, one Article at a time.
4. **Review:** on a review page in the portal (the LAN copy), showing each entry as a resident
   will see it. The chair approves, edits or sends back each one.
5. **For the Board:** a memo PDF per Article, built from the approved files, for the meeting
   packet.
6. **Storage:** in the repo, as files. The review page records decisions, and the builder turns
   them into a commit for the chair's OK. Git is the Town's record.
7. **Granularity:** one entry per standard. Each district's number is filled in from the ruleset.
8. **Pictures:** only spatial rules (setbacks, height, stories and attics, frontage, lot coverage,
   placement), drawn in plan 5's house style.
9. **Interpretations:** seeded from rulings already made, listed by the chair and the CEO. Each
   one is marked as an interpretation, with its date and who decided.
10. **"So you mean…":** approved as templates with slots. Slots are filled only from approved
    terms.
11. **Amendments:** a release flags every entry that cites a changed section. Flagged entries come
    off the public site until they're re-approved and re-ratified.
12. **No entry:** a standard with no live entry goes to the Town's judgment, with the approved
    "The Town will look at this one" words. Nothing unapproved is shown.
13. **Corrections:** the chair or the CEO can pull an entry at once. The fix goes through approval
    and ratification again.
14. **Reading level:** about grade 8, checked on every draft. The Code's defined terms are
    allowed and link to their definitions.
15. **Existing words:** the form entries and design 1's words are folded in with their original
    approvals. Nothing is re-approved, and they don't need the Board: they are live as they stand
    (the chair, 2026-11-08, after the builder check).
16. **The chair's recorded answers** where the Code is silent (`standards_overrides.json`): an
    entry may show those numbers, marked as the Town's interpretation and citing the chair's
    decision, like an interpretation entry. They go through ratification (2026-11-08).

## 4. The entry

An entry extends today's `entries.yaml` shape (spec §6). Fields:

| Field | What it holds |
|---|---|
| `id` | Stable, never reused. |
| `standard` | For `standard` entries: the standard it explains, by the key the checks use (`standards.py`). This is how the guide finds the entry, how "no live entry" is known (decision 12), and how coverage is counted. |
| `kind` | `standard` · `interpretation` · `template` · `word`. |
| `overline`, `answer`, `detail`, `why` | As today. The answer comes first, each condition is one short sentence with one number, and the detail is one tap away. |
| `slots` | Named values the entry reads from the standards (`standards.py`: the ruleset merged with the chair's recorded answers), e.g. `{side: districts.<d>.setback.side}`. The text uses `{side}`. The loader refuses a slot the standards can't supply. A value that comes from a recorded answer is shown with the Town's-interpretation mark and the decision's citation (decision 16). |
| `cites` | Real Code sections, checked against the pinned ruleset as today. |
| `terms` | Defined terms (Article 9) used in the text. Each links to its definition and is left out of the reading-level count. |
| `picture`, `picture_alt` | Spatial rules only (decision 8). |
| `decided_by`, `decided_on`, `source` | Interpretations only: who ruled, when, and where it's recorded (a meeting or a CEO determination). Never a resident's name or address. |
| `ruleset` | The ruleset the entry was approved against, e.g. `adopted-v1.0`. |
| `version`, `status`, `approved_by`, `approved_on` | As today. |
| `ratified_on`, `ratified_by` | The Board meeting date and "Planning Board". |
| `pulled_on`, `pulled_by`, `pulled_why` | Set when an entry is taken down (§8). |

**One entry per standard** (decision 7). A standard is one row label of the district pages'
dimension panels or the Permitted Buildings tables (for example "Total Stories"), whatever the
district or building type (*builder's call*). For example, "the side setback" is written once, and
`{side}` comes from the resident's district. Where a district differs *in kind* and not just in
number, the entry may carry a `district_notes` map. Each note is approved like the entry
(*builder's call*, since the chair chose one entry per standard). A district whose value is "not
established" in the ruleset gets no number. The standard goes to the Town (decision 12), as the
coverage audit already does.

**Templates** (decision 10) are entries of kind `template`. Their slots are listed, and each slot
is filled only from an approved list: use names from the Use Table, districts, Thoroughfare Types,
or a number with its unit. The engine's `TEMPLATE_SLOTS` check stays, extended to the new slots.

**Words** (decision 15): the readable strings of the form definitions (`forms/definitions/*.yaml`:
labels, help, clock sentences), of `guide/definitions/*.yaml` and of the web's `words.ts` keep
their text and approvals and become `kind: word` entries in one source. Only the strings move.
Conditions, fees, clocks and form versions stay where they are and point to their words by id
(*builder's call*). `words.ts` records approvals by group in its header, not per word, so each word
takes its group's date from the approval memos. *Builder's call:* the web's words are generated from, or served from, the library, so
there is one source and not two copies. The existing draft gate (`WORD_STATUS`, `draftWording`)
reads the library's statuses.

## 5. Status, from draft to live

```
draft ──chair approves──▶ approved ──Board ratifies──▶ ratified (live)
  ▲                          │                            │
  └──── chair sends back ────┘          chair or CEO pulls / amendment flags
                                                          ▼
                                                        pulled ──re-approve, re-ratify──▶ ratified
```

- **Live** means `ratified` and not pulled. The one exception is the words approved before this
  design (decision 15): `approved` is live for them. *Builder's call, for the chair to check:* new
  screen words (`kind: word`: questions, buttons, headings) follow the same rule as the old ones
  and need only the chair. Anything that explains the Code (`standard`, `interpretation`,
  `template`) needs the Board. The guide shows only live entries to the public.
- **The LAN copy** may show `approved` entries, so the chair and Board can see them in place. When
  it does, the existing draft chip marks them (*builder's call*). The public build refuses to
  start if any entry it would show is not live. The guard works like `build/version_state.py`:
  the state is in the data. Unlike today's draft gate, which `PORTAL_ALLOW_DRAFT_RULES` can switch
  off, no setting reaches it in the public build.
- **Edits** made on the review page create a new version. The chair approves the edited text,
  never the text before the edit.

## 6. Drafting

- **By Article** (decision 3), Article 2's district standards first, because the guide already
  checks them. Then the Articles in order, each sized at the start of its batch (*builder's call*
  on order after Article 2).
- **From the adopted Code's text**, citing the sections each sentence rests on. A draft never
  supplies a value the Code doesn't state (rule 6). Where the Code is unclear or silent, the draft
  stops, and the question goes on the batch's open-questions list for the chair.
- **Checked on load:** citations exist, slots resolve, the never-used words are absent, the
  governs line is present, defined terms are linked, and the reading level is about grade 8 or
  lower. *Builder's call:* Flesch–Kincaid grade, with defined terms and numbers excluded; above 8
  flags the draft and doesn't refuse it, and the review page shows the grade.
- **Interpretations** are drafted from the list the chair and the CEO supply (decision 9). That
  list is an input the builder can't produce, so the plan asks for it when the first
  interpretation batch begins.

## 7. The review page and the record

**The page** is part of the same portal and database residents use, not a separate copy. Until
launch, that is the LAN copy; at launch, the same staff-only page on the public site, so a pull
reaches residents at once (*builder's call*). It is for the `staff` and `admin` roles that already exist in the
`applicant` table. The chair and the CEO need those roles; residents never see the page. For each
entry in a batch it shows:
- the entry exactly as a resident will see it, using the guide's own card, with a district picker
  for the slots;
- the cited Code text beside it, from the pinned ruleset;
- the reading grade and any load-check flags;
- **Approve**, **Edit** (approving after editing makes a new version) and **Send back** (with a
  note);
- for an amendment batch, the old and new wording.

**The record.** The page stores decisions as pending. The builder exports them into the library
files as one commit per batch: who, what and when, with the chair's OK as usual (CLAUDE.md rule 1).
The running portal reads the library from the deployed files, so a decision reaches residents
only through a commit and a deploy. *Builder's call:* until that commit, the page shows a
decision as pending, so nobody mistakes it for the record.

**Ratification.** When an Article's set is approved, the builder renders a memo PDF with
`build/build-memo.sh`, generated from the approved files. It shows every entry as a resident sees
it (with each district's numbers filled in), its citations, its approval date and the batch's
open questions, if any remain. After the vote, the chair gives the meeting date, and the commit
records `ratified_on` for the set.

## 8. Pulling an entry

- The chair or the CEO presses **Pull** on the review page, with a reason. It takes effect at once
  on the running portal, before any commit. It is the one decision that does. The entry's
  standard falls back to the Town's judgment (decision 12).
- The pull is recorded in the library at the next commit (`pulled_on`, `pulled_by`, `pulled_why`).
- The fix is a new version that goes through approval and ratification again.
- *Builder's call:* a pull is kept in the database as an overlay that the API reads on every
  request, so it survives a restart and needs no deploy.

## 9. Versions and the packet

A sent packet already keeps what its resident saw: `packet.as_sent` stores the whole rendered body
at sending. That stays. The packet also records each entry it showed by `id` and `version`, so
staff can tell when an entry has changed since (*builder's call*). Earlier versions live in git; no
history is kept in the files. A packet that is sent again shows the versions live at that moment.

## 10. Amendments

- Each entry records the `ruleset` it was approved against. When a new ruleset is vendored for an
  adopted amendment, a check lists every entry whose `cites` include a section that changed
  between the two. It uses the same section-level change list the release's redline builds.
- **At adoption** (when the new ruleset is pinned), the flagged entries are pulled until they're
  re-approved and re-ratified (decision 11). While the amendment is only a draft, entries stay as
  they are. The Code they explain is still the one in force (the chair's call, 2026-11-07).
- An entry whose numbers come from slots updates with the ruleset by itself. It is still flagged
  if its cited sections changed, because its words may no longer fit.
- A test fails if a live entry cites a section that changed after its `ruleset`.

## 11. Scale and order

The coverage audit (`memos/2026-10-30-guided-builder-rules-coverage.md`) counts 452 district
standards across 13 districts. With one entry per standard, Article 2 comes down to a few dozen
entries. The standards in Articles 3–9 aren't yet counted. Sizing them is the first task of each
Article's batch. The plan ships the format, the checks, the review page, the record and the memo
first, proves them on Article 2's batch, and then runs the other Articles as batches using the
same tools.

## 12. What's left to the builder

File layout (one file per Article, or per kind); the slot path syntax; how the web gets its words
from the library; the readability library; the review page's look (the guide's theme, Material);
the export format; how the change list between rulesets is computed.

## 13. Open questions

**For the chair or the Board**
1. How the Board ratifies: a vote on a motion naming the Article's set and the memo's date, or
   another form the Board's procedures need.
2. Who the CEO is in the portal: which account gets the `staff` role, and whether anyone else may
   pull.

**For counsel** (from the experience design §12, now touching the library)
3. Whether the governs line, "The adopted Code governs if anything here differs from it.", is
   enough given how Maine treats reliance (§12 item 1).
4. Whether a published interpretation needs anything beyond its date, who decided and its source,
   and whether naming a case, even without a resident's name, raises a records question
   (§12 item 3).

**Inputs only the Town can give**
5. The list of rulings already made (decision 9), for the first interpretation batch.
