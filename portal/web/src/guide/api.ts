// The guided conversation's calls (guided plans 2 and 3). The screens only show what these
// return: every limit, check and ending is worked out by the API (spec §5).
import type { Refusal } from "../projects";

export type Step = { n: number; of: number; label: string };
export type Entry = { id: string; overline: string; answer: string; detail: string; why: string | null;
  cites: string[]; version: number; governs: string; picture?: string | null; picture_alt?: string | null;
  // The chair's recorded readings behind its numbers, shown as the Town's interpretation (design 2, decision 16).
  interpretations?: string[];
  mark?: string | null };   // the guide's own words for that mark, sent with them
export type Check = {
  result: "fits" | "outside" | "cannot_check"; value: number | null; min: number | null; max: number | null;
  unit: string | null; room: number | null; gap: number | null; direction: "over" | "short" | null;
  reason: string | null; standard_keys: string[]; nearest: { id: string; value: number }[];
};
export type Approx = { value: number | null; approximate: boolean };
export type LotFacts = { map_lot: string | null; districts: { code: string; name: string }[];
  acres: Approx; frontage_ft: Approx };
export type TurnAnswer = { id: string; label: string; hint: string | null };
export type Shown = {
  turn_id: string; kind: "lot" | "confirm" | "choice" | "number"; step: Step; ask: string; help: string | null;
  answers: TurnAnswer[]; input: { unit: string | null; min: number; max: number } | null; why: Entry | null;
  defines: Entry[]; check: Check | null; facts_shown: LotFacts | null;
  drawing?: "front" | "front_setback" | "side_1" | "side_2" | "secondary" | "rear" | null;   // plan 4
};
export type Unsettled = { turn_id: string | null; reason: string; district?: string; standard_keys?: string[] };
export type Ending = {
  kind: "not_here" | "town_judgment" | "ready" | "no_permit"; title: string; body: string; entry: Entry | null;
  settled: { turn_id: string; check: Check }[]; unsettled: Unsettled[]; reviews: unknown[];
  allowed_uses: { district: string; uses: { use_key: string; code_name: string }[] }[];
  not_listed: unknown[]; notes: unknown[];
};
export type Note = { body: string; at: string };
export type Guide = {
  revision: number; opening: string; current: Shown | null; history: { shown: Shown; value: unknown }[];
  ending: Ending | null; step: Step | null; unsure: string[]; checks: Record<string, Check>; notes: Note[];
  reopened: { turn_id: string; ask: string }[];   // the later questions the last Change reopened
  drafts: string[];
};
// A place to tap in the opening scene (guided plan 5): `picture` is its spot, `guided` whether the
// guide can walk through it yet, `in_project` whether the project already has its part.
export type Opening = { id: string; label: string; part: string | null; picture: string; guided: boolean; in_project: boolean };

// The lot drawing (guided plan 4): the tax-map outline in feet, and what the API says each line is.
export type Pt = [number, number];
export type LotLine = { id: string; points: Pt[]; length_ft: number; street: { name: string; type: string | null } | null };
export type Outline = { units: "ft"; approximate: true; parts: Pt[][]; lines: LotLine[]; streets: { name: string; points: Pt[] }[] };
export type Role = "front" | "side" | "rear" | "frontage" | "secondary";
export type Limit = { min: number | null; max: number | null; unit: string | null; reason: string | null; standard_keys: string[] };
export type Drawing = {
  outline: Outline | null; front: string | null; roles: Record<string, Role> | null;
  limits: Record<"front" | "side" | "rear" | "secondary", Limit | null>;
};
export type GuideRefusal = Refusal | "not_started" | "not_approved" | { conflict: true } | { rejected: string };

const json = { "Content-Type": "application/json" };

async function call(input: string, init?: RequestInit): Promise<Response | null> {
  try {
    return await fetch(input, { credentials: "include", ...init });
  } catch {
    return null;
  }
}

async function read<T>(r: Response | null): Promise<T | GuideRefusal> {
  if (!r) return "unavailable";
  const body = (await r.json().catch(() => ({}))) as { detail?: unknown };
  if (r.ok) return body as T;
  const d = body.detail;
  if (r.status === 401) return "signed_out";
  if (r.status === 429) return "busy";
  if (r.status === 404) return d === "not_started" ? "not_started" : "not_found";
  if (r.status === 409) return d === "locked" ? "locked" : { conflict: true };
  if (r.status === 422) return { rejected: typeof d === "string" ? d : "invalid" };
  if (r.status === 503 && d === "guide_not_approved") return "not_approved";
  return "unavailable";
}

const base = (id: string) => `/api/projects/${encodeURIComponent(id)}/guide`;
const post = <T>(url: string, body: unknown, signal?: AbortSignal) =>
  call(url, { method: "POST", headers: json, body: JSON.stringify(body), signal }).then((r) => read<T>(r));

export const getGuide = (id: string) => call(base(id)).then((r) => read<Guide>(r));

export async function getOpenings(id: string): Promise<Opening[] | GuideRefusal> {
  const out = await call(`${base(id)}/openings`).then((r) => read<{ openings: Opening[] }>(r));
  return typeof out === "object" && "openings" in out ? out.openings : out as GuideRefusal;
}

// The packet (guided plan 6; spec §7): what the Town reads, as the API assembles it once for both sides.
export type PacketMark = "confirmed" | "unsure" | "took_suggestion" | "kept";
export type PacketRow = { turn_id: string | null; ask: string | null; reason?: string; check: Check | null; why: Entry | null };
export type Packet = {
  state: "now" | "sent"; sent_at: string | null; changed: boolean; finished: boolean;
  ending: { kind: string; title: string | null } | null;
  summary: { own_words: { body: string; at: string }[]; reading: string | null;
    deciders: { review: string | null; reviewer: string | null; sentence: string | null }[];
    corrections: { lot_disputed: boolean; note: string | null } };
  history: { turn_id: string; ask: string; answer: string | null; value: unknown; marks: PacketMark[] }[];
  checks: Record<string, Check>;
  checklist: { town: PacketRow[]; fits: PacketRow[] };
  drawing: Drawing | null; drafts: string[];
};

export const getPacket = (id: string) =>
  call(`/api/projects/${encodeURIComponent(id)}/packet`).then((r) => read<Packet>(r));

export async function getDrawing(id: string): Promise<Drawing | GuideRefusal> {
  return call(`${base(id)}/drawing`).then((r) => read<Drawing>(r));
}

export const startGuide = (id: string, opening: string, rev: number) =>
  post<Guide>(base(id), { opening, base_revision: rev });
export const answerTurn = (id: string, turnId: string, value: unknown, rev: number) =>
  post<Guide>(`${base(id)}/answers`, { turn_id: turnId, value, base_revision: rev });
export const goBack = (id: string, rev: number) => post<Guide>(`${base(id)}/back`, { base_revision: rev });
export const revisit = (id: string, turnId: string, rev: number) =>
  post<Guide>(`${base(id)}/revisit`, { turn_id: turnId, base_revision: rev });
export const addNote = (id: string, body: string, rev: number) =>
  post<Guide>(`${base(id)}/notes`, { body, base_revision: rev });

// The check for a value not yet given (spec §4.4): saves nothing.
export const checkValue = (id: string, turnId: string, value: number | "unsure", signal?: AbortSignal) =>
  post<Check | { result: null }>(`${base(id)}/check`, { turn_id: turnId, value }, signal);

export function isRefusal(x: unknown): x is GuideRefusal {
  return typeof x === "string" || (typeof x === "object" && x !== null && ("conflict" in x || "rejected" in x));
}
