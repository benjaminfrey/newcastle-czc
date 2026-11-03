// The guided conversation's calls (guided plans 2 and 3). The screens only show what these
// return: every limit, check and ending is worked out by the API (spec §5).
import type { Refusal } from "../projects";

export type Step = { n: number; of: number; label: string };
export type Entry = { id: string; overline: string; answer: string; detail: string; why: string | null;
  cites: string[]; version: number; governs: string };
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
  drafts: string[];
};
export type Opening = { id: string; label: string; part: string };
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
