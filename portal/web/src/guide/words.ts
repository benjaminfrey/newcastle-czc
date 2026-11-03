// Every word the guide's screens say on their own (spec §11: every word an applicant reads is
// approved before the public sees it). Turn, answer, entry and ending words come from the API's
// content files; these are the rest. All are draft until the chair approves them, which is why
// every guide screen carries the "Draft wording" chip. Nothing else in src/guide/ writes words.
export const WORD_STATUS = "draft";

export const WORDS = {
  // The app bar and the page around the conversation.
  back_to_project: "your project",           // "Back to your project", on the first turn
  back_a_turn: "the last question",          // "Back to the last question"
  your_project: "Your project",              // the summary's heading, and its button on a phone
  close: "Close",
  loading: "Loading your project…",
  pick_opening: "What would you like to do?", // before the guide starts

  // The lot as the Town knows it (spec §4.1).
  lot_map_lot: "Map-lot",
  lot_districts: "District",
  lot_acres: "Lot size",
  lot_frontage: "Road frontage",
  approximate: "approximate, from the tax maps",
  unknown: "The Town doesn't know this yet",
  acres: "acres",
  ft: "ft",

  // Numbers (spec §4.4).
  next: "Next",
  unsure: "I'm not sure yet",
  less: "Less",
  more: "More",
  not_a_number: "Please enter a number, like 25 or 1,800.",
  out_of_range: "That number is outside what this question takes.",
  room_left: "Within the limit · {room} {unit} to spare",
  at_limit: "Within the limit, right at it",
  past_limit_over: "{gap} {unit} over the limit here",
  past_limit_short: "{gap} {unit} short of the limit here",
  town_decides: "The Town will look at this one",
  limit_mark: "Limit",

  // The conversation.
  reply_placeholder: "Anything else the Town should know?",
  notes_kept: "The Town Office will read this. The guide's questions don't change because of it.",

  // Notices.
  notices: {
    changed_elsewhere: "This project changed in another window, so we've brought this page up to date.",
    try_again: "That answer didn't go through. Please try again.",
  },
  locked: "The Town is reviewing this project, so it can't be changed now.",

  // Your project (spec §4.4, §4.7).
  change: "Change",
  fits_mark: "Fits",
  for_the_town: "For the Town",

  // The endings (spec §4.6).
  settled_heading: "What we could settle",
  unsettled_heading: "What goes to the Town",
  reviews_heading: "What your project needs",
  fees_heading: "Fees",
  application_fees: "Application fees, due when you send",
  permit_fees: "Permit fees, due later",
  fee_varies: "Set by the Town Office",
  fees_unknown: "Your fees show here once the Town's rules for them are ready.",
  check_and_send: "Check and send",
  no_permit_keep: "Keep to what you told us. If anything changes, ask the Town Office before you start.",
  allowed_heading: "What {district} allows",
  talk_to_town: "You can talk this through with the Town Office. Your project and this conversation are saved.",
  unsettled: {
    not_listed: "Whether this use is listed for your lot",
    not_listed_in_one_district: "Your lot is in two districts, and this use is listed in only one",
    unsure: "An answer you weren't sure of yet",
    kept_past_the_limit: "A number you kept past its limit",
    talk_to_town: "A number you'd like to talk over with the Town",
    lot_disputed: "The Town's facts about your lot, which you said aren't right",
    no_district: "Which district rules apply to your lot",
    not_checkable: "A limit the guide can't check yet",
    two_districts: "Your lot is in two districts with different limits",
    unknown_input: "A number that rests on an answer you weren't sure of",
    board_decides: "A number the Planning Board can allow",
    town_only: "Work only the Town Office can review",
    contact_town: "Something the Town Office needs to look at",
  },

  // Check and send (spec §4.7).
  check_heading: "Check your project",
  send: "Send to the Town",
  sending: "Sending…",
  sent: "Sent. The Town has your project.",
  to_project: "Go to your project",
  still_needs: "Before you send, the Town's form still needs:",
  finish_on_form: "Fill these in on your project's form",
  refusals: {
    signed_out: "You've been signed out. Please sign in again.",
    not_found: "We couldn't find this project.",
    not_approved: "The guide isn't open yet. Please contact the Town Office.",
    busy: "Too many requests just now. Please wait a minute and try again.",
    unavailable: "We couldn't reach the Town's server. Please check your connection and try again.",
    locked: "The Town is reviewing this project, so it can't be changed now.",
  },

  // The HeroUI dashboard's link in (LAN copy only).
  try_guide: "Try the guided version (preview)",
} as const;

// "{room} {unit} to spare" → the words with their slots filled.
export function fill(words: string, slots: Record<string, string | number>): string {
  return words.replace(/\{(\w+)\}/g, (_, k: string) => String(slots[k] ?? ""));
}
