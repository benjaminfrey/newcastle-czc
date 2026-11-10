// The explanation library's review page (design 2, §7), for Town staff. These are drafts for the
// chair: the page is staff-only, but every word in the portal is approved before it ships.
export const LIBRARY_WORD_STATUS = "draft" as "draft" | "approved";

export const LW = {
  title: "Explanation library",
  staff_only: "This page is for Town staff.",
  unavailable: "The library couldn't be loaded. Try again in a moment.",
  loading: "Loading the library…",
  all_batches: "all batches",
  counts: "{total} entries · {draft} drafts · {approved} approved · {ratified} ratified · {pulled} pulled",
  pending_count: "{n} waiting to be recorded",
  questions_heading: "Questions for the chair",
  district: "District",
  building: "Building",
  not_for_district: "This entry doesn't apply here: the Code gives no value, so the standard goes to the Town.",
  code_heading: "What the Code says",
  flags_heading: "Checks",
  status: { draft: "Draft", approved: "Approved by the chair", ratified: "Ratified by the Board", pulled: "Pulled" },
  pending: "Pending: {action}, not yet recorded",
  actions: { approve: "approved", edit: "edited", send_back: "sent back" },
  pulled_now: "Pulled on the site: {why}",
  sent_back_note: "Sent back: {note}",
  approve: "Approve",
  edit: "Edit",
  save_edit: "Save edit",
  cancel: "Cancel",
  send_back: "Send back",
  pull: "Pull",
  note_label: "Note for the record",
  why_label: "Why pull it?",
  fields: { overline: "Heading", answer: "Answer", detail: "Detail", why: "Why the rule exists" },
  confirm_pull: "Pull this entry now?",
  confirm_pull_body: "Residents stop seeing it at once. Its standard goes to the Town until a fixed version is approved and ratified.",
  confirm_pull_yes: "Pull it",
  pending_edit: "The edited text, waiting for approval",
  saved: "Saved. It is recorded when the library's files are next committed.",
} as const;

export const libraryDraft = () => LIBRARY_WORD_STATUS === "draft";
