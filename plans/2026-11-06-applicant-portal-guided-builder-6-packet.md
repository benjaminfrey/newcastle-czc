# Guided builder, plan 6 of 6: the applicant's packet — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** The resident can open their project's packet: the same summary, back-and-forth,
checklist (judgment first) and lot drawing the Town will read. It is shown as it stands before
sending, and as sent afterwards, and it prints cleanly.

**Architecture:**
- **API.** A new `portal_api/guide/packet.py` assembles the packet from what is already stored:
  the replayed conversation, its checks and ending, the notes, the snapshot, the project's needs and
  the drawing.
  - `GET /api/projects/{id}/packet` returns it.
  - Sending stores the packet as it was at that moment, in a new `guide_packet` table, so "as
    sent" never changes.
  - The staff view (design 4) will call the same `build`.
- **Web.** A new `src/guide/packet/` folder: `PacketPage` and its four parts. It reuses plan 3's
  words, plan 4's `LotDrawing` and `DrawingList`, and plan 5's `entryCard`. A print stylesheet
  lays it out on letter paper. Links lead to it from Check and send, the ending page and the
  project page.
- Everything stays behind `VITE_GUIDE_PREVIEW=1`.

**Tech Stack:**
- API: Python 3.14, FastAPI, SQLAlchemy `text()`, Alembic, pytest.
- Web: React 19.3, TypeScript 5.9, MUI 9.5.0, Vitest 5, Testing Library, Playwright 1.64 with axe.
- **No new packages.**

**Spec:** `specs/2026-11-06-applicant-portal-guided-builder-packet.md` (approved by the chair
2026-11-06), under `specs/2026-10-30-applicant-portal-guided-builder.md` §7 and decision 8.

**Branch:** `portal-guided-6-packet`, cut from `portal-guided-5-pictures` (PR #27 is not merged
yet). Merge `main` in if the stack below merges first. Never rebase a pushed branch.

## Global Constraints

- **One packet for both sides.** Everything the page shows comes from `GET /packet`. The web
  computes nothing about fits, judgment or who decides.
- **Their own words, unedited.** Notes are shown exactly as stored. They are never trimmed,
  summarised or corrected.
- **Never a decision** (§10.3). Reuse the approved words wherever they exist:
  - `settled_heading` "What we could settle", `unsettled_heading` "What goes to the Town";
  - `fits_mark` "Fits", `for_the_town` "For the Town";
  - `WORDS.unsettled.*`, the `drawing.*` rows, and the reviews' decision sentences.

  New words start as drafts in `words.ts`, which turns `WORD_STATUS` back to `"draft"`. The banned
  list (approved, denied, granted, rejected, permit issued, compliant, violates) never appears.
- **Never guess a legal value.** Limits and decision sentences come from the rulesets and
  `applications.yaml` through the API.
- **Draft gate.** `GET /packet` refuses with 503 `guide_not_approved` when the packet would show
  draft content and `allow_draft_rules` is off, as the guide's routes do.
- **Accessibility:**
  - one `h2` per part;
  - a highlight always carries a text tag, never colour alone;
  - the folded passes sit behind a real `<button aria-expanded>`;
  - the drawing keeps its list;
  - axe runs on the packet journey.
- **Old projects still work.** A project with no conversation gets 404 `not_started`, and no link
  to its packet is shown. A snapshot with no outline gets a packet with no drawing.
- **Tests run on the VM.** Journeys run from the Mac against the LAN copy, at no more than 20
  sign-ins an hour; the guide spec already uses 18, so the packet journey adds at most 2.

## Review Focus

1. **A project sent, then changed before staff lock it.** Expect "as sent" to show the packet
   from the moment of sending, unchanged by later answers. Sending again replaces it. Test:
   `test_the_sent_packet_does_not_follow_later_changes` (Task 2).
2. **A note with line breaks, quotes or markup.** Expect it shown exactly as typed, as text, never
   as HTML. Test: `own words are shown exactly as written` (Task 4).
3. **A conversation still in progress** (no ending yet). Expect the checklist to come from the
   checks so far, and a line saying the conversation isn't finished. Test:
   `test_a_packet_mid_conversation_lists_the_checks_so_far` (Task 1).
4. **A project that needs two reviews** (a Large Project Plan). Expect every decision sentence, in
   the order the reviews run. Test: `test_every_decision_sentence_in_review_order` (Task 1).
5. **Printing.** Expect the folded passes printed open, the app bar and buttons hidden, and the
   parts in §7's order. Test: the print journey (Task 6), which emulates `print` media and checks
   that the passes are visible and the buttons hidden.

---

### Task 1: The API assembles the packet

**Files:**
- Create: `portal/api/portal_api/guide/packet.py`
- Modify: `portal/api/portal_api/routes/guide.py` (the new route)
- Test: `portal/api/tests/test_guide_packet.py`

**Interfaces:**
- Produces: `build(conn, row, request_settings) -> dict`, returning:

```
{ "state": "now" | "sent", "sent_at": iso | null, "finished": bool,
  "summary": { "own_words": [{"body", "at"}], "reading": str | null,
               "deciders": [str], "corrections": {"lot_disputed": bool, "note": str | null} },
  "history": [{ "turn_id", "ask", "answer", "marks": ["confirmed" | "unsure" | "took_suggestion" | "kept"] }],
  "checklist": { "town": [{ "turn_id", "ask", "reason", "check": Check | null, "why": Entry | null }],
                 "fits": [{ "turn_id", "ask", "check": Check, "why": Entry | null }] },
  "drawing": <the /guide/drawing payload> | null,
  "drafts": [str] }
```

- `GET /api/projects/{id}/packet` returns `build(...)` or a refusal:
  - 404 `not_found` for someone else's project;
  - 404 `not_started` when there is no conversation;
  - 503 `guide_not_approved` when there are drafts and drafts aren't allowed.

**How each part is made** (from code that already exists):
- `own_words`: `store.notes(conn, project_id)`, verbatim.
- `reading`: the `confirm` turn's `ask` from the history, if it was answered `yes`.
- `deciders`: the `plain` text of every clock whose key contains `decision`, in each needed
  permit's `clocks` (`Loaded(conn, row).needs(...)["permits"]`), in permit order. Empty when no
  review is settled.
- `corrections.lot_disputed`: `lot.disputed` or the fact `lot.confirmed is False`.
  `corrections.note` is the snapshot's `note`, or null.
- `history`: one row per `(shown, value)`:
  - `answer` is the chosen answer's label, or the number with its unit;
  - marks: `confirmed` for `confirm` = yes; `unsure` for the value `unsure`; `took_suggestion`
    for a `doesnt_fit:` turn answered `nearest`; `kept` for one answered `keep_mine`.
- `checklist`:
  - If there is an ending, `town` comes from its `unsettled` (reason as given) and `fits` from its
    `settled`.
  - If not, `town` is every check that isn't `fits` plus every unsure turn, and `fits` is every
    `fits` check.
  - `why` is that turn's explanation entry, serialized as the engine does today.
  - `finished` is whether there is an ending.
- `drawing`: the same function the `/guide/drawing` route uses (extract it into a helper both call).

- [ ] **Step 1: Write the failing tests.** Use the route fixtures from `test_guide_routes.py`:
  - `test_the_packet_carries_their_words_exactly`: a note `"Line one\n<b>Two</b> \"quoted\""`
    comes back byte for byte.
  - `test_the_reading_and_who_decides`: a new house walked to `ready` has
    `reading.startswith("So you'd like to build a new house")`, and `deciders` contains "The Code
    Enforcement Officer decides within 10 days of accepting your project."
  - `test_every_decision_sentence_in_review_order`: unit-test `deciders_from(needs)` with a
    two-permit needs dict (CEO, then Board); both sentences are returned, in that order.
  - `test_history_marks_the_moments_that_matter`: a walk with confirm yes, one "unsure", and a
    `doesnt_fit` answered `nearest` carries the marks `confirmed`, `unsure` and
    `took_suggestion`, on the right rows.
  - `test_judgment_comes_first`: on a `town_judgment` ending, `checklist.town` holds the
    `unsettled` turns and `fits` the settled ones; no turn is in both.
  - `test_a_packet_mid_conversation_lists_the_checks_so_far`: after the front setback,
    `finished is False` and `fits` has `setback_front`.
  - `test_a_disputed_lot_is_flagged`: answering "That's not right" sets
    `corrections.lot_disputed`.
  - `test_no_conversation_is_not_started` and `test_someone_elses_packet_is_404`.
  - `test_the_packet_is_refused_while_its_words_are_drafts`: the `all_draft` pattern from
    plan 5's route tests.
- [ ] **Step 2: Run them on the VM.** Expected: FAIL (no route).
- [ ] **Step 3: Implement** `packet.py`, with `deciders_from(needs: dict) -> list[str]` as its own
  function, and the route.
- [ ] **Step 4: Run the whole API suite on the VM.** Expected: all pass.
- [ ] **Step 5: Commit.**

### Task 2: "As sent" is kept

**Files:**
- Create: `portal/api/migrations/versions/0011_guide_packet.py`
- Modify: `portal/api/portal_api/guide/store.py` (`save_packet`, `sent_packet`), `portal/api/portal_api/routes/projects.py` (`submit`), `packet.py` (the route serves the sent one)
- Test: `portal/api/tests/test_guide_packet.py`

**Interfaces:**
- Table `guide_packet(project_id uuid primary key references project(id) on delete cascade,
  sent_at timestamptz not null, body jsonb not null)`.
- `store.save_packet(conn, project_id, body: dict) -> None` upserts.
  `store.sent_packet(conn, project_id) -> tuple[datetime, dict] | None`.
- `submit` saves `packet.build(...)` (with `state: "sent"` and `sent_at` set) when the project has a
  conversation, in the same transaction as the status change.
- `GET /packet` returns the saved packet when the project's status isn't `draft` and one is saved;
  otherwise it builds one now.

- [ ] **Step 1: Write the failing tests:**
  - `test_sending_keeps_the_packet_as_sent`: after submit, `GET /packet` has `state == "sent"`
    and a `sent_at`.
  - `test_the_sent_packet_does_not_follow_later_changes`: send, then add a note. The packet's
    `own_words` don't include the new note.
  - `test_sending_again_replaces_it`.
  - `test_a_project_sent_without_a_conversation_saves_nothing`.
- [ ] **Step 2: Run them on the VM.** Expected: FAIL.
- [ ] **Step 3: Implement**, including the migration's `downgrade`.
- [ ] **Step 4: Run the whole API suite on the VM.** Expected: all pass.
- [ ] **Step 5: Commit.**

### Task 3: The packet page

**Files:**
- Create: `portal/web/src/guide/packet/PacketPage.tsx`, `PacketSummary.tsx`, `PacketHistory.tsx`, `PacketChecklist.tsx`, `packet.css` (print)
- Modify: `portal/web/src/guide/api.ts` (`Packet`, `getPacket`), `words.ts`, the app's routes (`/projects/:id/packet`, lazy, in the guide's chunk)
- Test: `portal/web/src/guide/packet/PacketPage.test.tsx`, `words.test.ts`

**Interfaces:**
- Consumes: Task 1's JSON as the `Packet` type; plan 4's `LotDrawing` (with `asking={null}`) and
  `DrawingList`; plan 5's `entryCard`.
- Produces: `getPacket(id): Promise<Packet | GuideRefusal>` and the route `/projects/:id/packet`.

**Words (drafts, `words.packet`):**
- `title`: "Your packet"
- `intro`: "This is what the Town will read about your project. Staff see the same, with their own notes."
- `now`: "As it stands now"
- `sent`: "As sent on {date}"
- `not_finished`: "The conversation isn't finished, so this shows what's settled so far."
- `own_words`: "In your own words"
- `no_words`: "You haven't written anything for the Town."
- `reading`: "Your project in the Code's terms"
- `deciders`: "Who decides"
- `no_deciders`: "The Town decides which review your project needs."
- `lot_flag`: reuses `WORDS.unsettled.lot_disputed`
- `history`: "The questions and your answers"
- `mark_confirmed`: "You confirmed this"
- `mark_unsure`: reuses `WORDS.unsure`
- `mark_took_suggestion`: "You took the suggestion"
- `mark_kept`: "You kept your number"
- `checklist`: "The checklist"
- `show_fits`: "Show what fits ({n})"
- `hide_fits`: "Hide what fits"
- `required`: "Required"
- `drawing`: "Your lot"
- `no_drawing`: "The Town's tax map has no outline for this lot, so there is no drawing."
- `print`: "Print"
- `open_packet`: "Your packet"

The checklist's headings reuse `unsettled_heading` and `settled_heading`; its rows reuse
`for_the_town`, `fits_mark`, `drawing.at_least`, `drawing.yours` and `WORDS.unsettled[reason]`.

- [ ] **Step 1: Write the failing tests** in `PacketPage.test.tsx`, with `getPacket` mocked:
  - `the four parts come in the spec's order`: the h2s read, in order, "In your own words" … "Your
    lot".
  - `own words are shown exactly as written`: a body with `<b>` and a line break renders as text,
    and the line break is kept (`white-space: pre-wrap`).
  - `judgment comes first and the passes are folded`: the town rows show; "Show what fits (2)" is a
    button with `aria-expanded="false"`; clicking it shows the two rows.
  - `every highlight carries its words`: a history row marked `took_suggestion` shows "You took
    the suggestion".
  - `as sent says when`: `state: "sent"` shows "As sent on …".
  - `a lot corrected by the person is flagged in the summary`.
  - `no outline, no drawing, and it says why`.
  - `not started shows nothing to read`: the refusal `not_started` leads back to the project.
  - In `words.test.ts`: `WORD_STATUS` is `"draft"`, and the new words pass the banned-words check.
- [ ] **Step 2: Run them.** Expected: FAIL.
- [ ] **Step 3: Implement.** Layout: with `useWideLayout()` true the drawing sits beside the
  checklist; otherwise everything is one column in §7's order. In `packet.css`, under
  `@media print`:
  - the folded passes are shown (`[data-fits] { display: block !important }`);
  - `header`, `nav` and `button` are hidden;
  - each `section` gets `break-inside: avoid-page` where it fits.
- [ ] **Step 4: Run the web suite, tsc and the build.** Expected: all pass.
- [ ] **Step 5: Commit.**

### Task 4: The ways in

**Files:**
- Modify: `portal/web/src/guide/CheckAndSend.tsx`, `EndingView.tsx`, `app/Dashboard.tsx`; `portal/api/portal_api/routes/projects.py` (the project's GET gains `has_conversation: bool`)
- Test: `CheckAndSend.test.tsx`, `EndingView.test.tsx`, `app/Dashboard.test.tsx`, `portal/api/tests/test_guide_packet.py`

- [ ] **Step 1: Write the failing tests:**
  - Check and send and every ending show a "Your packet" link to `/projects/{id}/packet`.
  - The dashboard shows it only when `has_conversation` is true (preview builds only).
  - `test_the_project_says_whether_it_has_a_conversation`.
- [ ] **Step 2: Run them.** Expected: FAIL.
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run the full API and web suites.** Expected: all pass.
- [ ] **Step 5: Commit.**

### Task 5: The four old looks findings, rechecked

The old cards' findings, closed as superseded (`OPEN_ITEMS.md`), are rechecked on the new screens
as journey assertions in `portal/web/e2e/guide.spec.ts`:
1. **One task list:** on a desktop guide page only one "Your project" panel is visible, and on a
   phone the sheet is closed until asked for.
2. **Field heights:** every text field on the number turn and on Check and send has the same height,
   at least 48 px.
3. **The lot card's spacing:** `LotFacts` rows have equal gaps (measured from their boxes, within
   1 px).
4. **"No password" once:** the sign-in page shows "No password" exactly once.

- [ ] **Step 1: Write the assertions** into the existing journeys, so no new sign-ins are needed.
- [ ] **Step 2: Rebuild the LAN copy and run `guide.spec`.** Each assertion that fails is a finding
  to fix in the screen it names. Fix it with a unit test that fails first, then run again.
- [ ] **Step 3: Commit.** Record each finding's result in the ledger.

### Task 6: The packet journey, and the words to the chair

**Files:**
- Create: `portal/web/e2e/packet.spec.ts`
- Create: `memos/2026-11-xx-guided-builder-packet-for-approval.md` (the date it is written)
- Modify: `OPEN_ITEMS.md`

- [ ] **Step 1: The journey** (desktop and phone, one sign-in each):
  - walk a new house to `ready`, open "Your packet", run axe;
  - check the four headings in order, and that "Show what fits" opens the passes;
  - emulate `print` media: the passes are visible and no button is visible;
  - send (or, if the form still has gaps, check that the packet says "As it stands now").
- [ ] **Step 2: Rebuild the LAN copy and run `packet.spec` and `guide.spec`.** Mind the sign-in
  limit. Expected: all pass, with the guide's two device-specific skips.
- [ ] **Step 3: The memo.** It lists the new words, with a screenshot of the packet at a
  computer's width and on a phone, for the chair's approval (§8 of the design).
- [ ] **Step 4: `OPEN_ITEMS.md`.** Plan 6 is on its branch, and its words are with the chair. The
  looks findings are closed or fixed, as Task 5 found them.
- [ ] **Step 5: Commit.** Then the whole-branch review (one fresh reviewer, the most capable
  model).
