// The review page's calls (design 2, §7). Staff only: a resident gets "staff_only".
import type { Entry } from "../guide/api";

export type Refusal = "signed_out" | "staff_only" | "not_found" | "stale" | "unavailable" | { rejected: string };
export type BatchCount = { batch: string; total: number; draft: number; approved: number; ratified: number;
  pulled: number; pending: number; open_questions: number };
export type LibraryEntry = { id: string; kind: string; overline: string; answer: string; detail: string; why: string;
  cites: string[]; version: number; status: "draft" | "approved" | "ratified" | "pulled"; standards: string[];
  review_note: string | null; [k: string]: unknown };
export type Decision = { id: number; entry_id: string; version: number; action: "approve" | "edit" | "send_back";
  body: Record<string, string> | null; note: string | null; decided_at: string; decided_by_email: string };
export type Pull = { entry_id: string; version: number; why: string; pulled_at: string; pulled_by_email: string };
export type ReviewItem = { entry: LibraryEntry; flags: string[]; code: { cite: string; text: string }[];
  pending: Decision | null; pulled: Pull | null };
export type District = { key: string; code: string; name: string; buildings: string[] };
export type Batch = { batch: string; open_questions: string[]; entries: ReviewItem[]; districts: District[] };
export type Texts = { overline: string; answer: string; detail: string; why: string };

async function call<T>(input: string, init?: RequestInit): Promise<T | Refusal> {
  let r: Response;
  try {
    r = await fetch(input, { credentials: "include", ...init });
  } catch {
    return "unavailable";
  }
  const body = (await r.json().catch(() => ({}))) as { detail?: unknown };
  if (r.ok) return body as T;
  if (r.status === 401) return "signed_out";
  if (r.status === 403) return "staff_only";
  if (r.status === 404) return "not_found";
  if (r.status === 409) return "stale";
  if (r.status === 422) return { rejected: typeof body.detail === "string" ? body.detail : "invalid" };
  return "unavailable";
}

const post = <T>(url: string, body: unknown) =>
  call<T>(url, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
const entry = (id: string) => `/api/library/entries/${encodeURIComponent(id)}`;

export const getBatches = () => call<BatchCount[]>("/api/library/batches");
export const getBatch = (b: string) => call<Batch>(`/api/library/batches/${encodeURIComponent(b)}`);
export const getPreview = (id: string, district: string, building: string | null) =>
  call<Entry>(`${entry(id)}/preview?district=${encodeURIComponent(district)}` +
    (building ? `&building=${encodeURIComponent(building)}` : ""));
export const decide = (id: string, version: number, action: Decision["action"], extra: { body?: Texts; note?: string } = {}) =>
  post<{ id: number }>(`${entry(id)}/decision`, { version, action, ...extra });
export const pullEntry = (id: string, version: number, why: string) => post<{ entry_id: string }>(`${entry(id)}/pull`, { version, why });

export function isRefusal(x: unknown): x is Refusal {
  return typeof x === "string" || (typeof x === "object" && x !== null && "rejected" in x);
}
