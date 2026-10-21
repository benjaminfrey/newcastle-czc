// Applications: the forms (public) and an applicant's drafts (signed in).
import type { Expr } from "./forms/expr";

export type Option = { value: string; label: string; official: string };
export type FormField = {
  id: string; official_label: string;
  source: "question" | "property" | "account" | "derived" | "at_submit" | "staff";
  from: string | null; may_correct: boolean; label: string | null; help: string | null;
  why: { cite: string; text: string } | null;
  type: "text" | "longtext" | "number" | "choice" | "multichoice" | "yesno" | "date" | "uses" | "point" | "upload" | null;
  unit: string | null; min: number | null; max: number | null; required: boolean; allow_unknown: boolean;
  show_if: Expr | null; options: Option[];
};
export type FormSection = {
  id: string; official_title: string; chapter: string; show_if: Expr | null;
  repeat: { kind: string; add_label: string; min: number; max: number } | null;
  fields: FormField[];
};
export type FormDef = { key: string; version: number; ruleset_key: string; official_title: string; sections: FormSection[] };

export type Item = { id: string; kind: string; position: number };
export type Attachment = { id: string; field_id: string; item_id: string | null; filename: string; content_type: string; size_bytes: number };
export type Snapshot = {
  source: "lookup" | "manual"; parcel_id: number | null; map_lot: string; facts: Record<string, unknown>;
  parcels_as_of: string | null; verified: boolean; disputed: boolean; note: string;
};
export type AppState = {
  id: string; form_key: string; form_version: number; ruleset_key: string; status: string; revision: number;
  property: Snapshot; items: Item[];
  answers: { field_id: string; item_id: string | null; value: unknown }[];
  notes: { section_id: string; item_id: string | null; text: string }[];
  attachments: Attachment[];
  missing: { field_id: string; item_id: string | null }[];
  newer_version: boolean;
};
export type AppSummary = { id: string; form_key: string; official_title: string; map_lot: string; status: string; updated_at: string };
export type NewApplication = {
  form_key: string;
  property: { source: "lookup"; parcel_id: number } | { source: "manual"; map_lot: string; district_code: string | null };
  disputed: boolean; note: string; use_key: string | null;
};
export type Change = { field_id: string; item_id: string | null; value: unknown };
export type Problem = { field_id: string; item_id: string | null; reason: string };

// "signed_out": the session ended; "not_approved": the form still has entries the chair
// hasn't approved; "unavailable": the server or the connection failed.
export type Refusal = "signed_out" | "not_approved" | "unavailable" | "not_found";
export type SaveResult = { revision: number; missing: AppState["missing"] } | { conflict: number } | { invalid: Problem[] } | Refusal;

const json = { "Content-Type": "application/json" };

async function call(input: string, init?: RequestInit): Promise<Response | null> {
  try {
    return await fetch(input, init);
  } catch {
    return null;
  }
}

async function detail(r: Response): Promise<unknown> {
  return ((await r.json().catch(() => ({}))) as { detail?: unknown }).detail;
}

async function refused(r: Response | null): Promise<Refusal | null> {
  if (!r || r.status >= 500) {
    if (r && r.status === 503 && (await detail(r.clone())) === "form_not_approved") return "not_approved";
    return "unavailable";
  }
  if (r.status === 401) return "signed_out";
  if (r.status === 404) return "not_found";
  return null;
}

export async function getForm(key: string, version?: number): Promise<FormDef | Refusal> {
  const r = await call(version ? `/api/forms/${key}/v/${version}` : `/api/forms/${key}`);
  return (await refused(r)) ?? ((await r!.json()) as FormDef);
}

export async function createApplication(body: NewApplication): Promise<{ id: string } | Refusal | "property_unavailable" | "invalid"> {
  const r = await call("/api/applications", { method: "POST", headers: json, body: JSON.stringify(body) });
  if (r && r.status === 503 && (await detail(r.clone())) === "property_unavailable") return "property_unavailable";
  const no = await refused(r);
  if (no) return no;
  if (r!.status === 422) return "invalid";
  return (await r!.json()) as { id: string };
}

export async function listApplications(): Promise<AppSummary[] | Refusal> {
  const r = await call("/api/applications");
  return (await refused(r)) ?? ((await r!.json()) as AppSummary[]);
}

export async function getApplication(id: string): Promise<AppState | Refusal> {
  const r = await call(`/api/applications/${id}`);
  return (await refused(r)) ?? ((await r!.json()) as AppState);
}

async function write(url: string, method: string, body: unknown): Promise<SaveResult> {
  const r = await call(url, { method, headers: json, body: JSON.stringify(body) });
  const no = await refused(r);
  if (no) return no;
  if (r!.status === 409) return { conflict: ((await r!.json()) as { revision: number }).revision };
  if (r!.status === 422) {
    const d = await detail(r!);
    return { invalid: Array.isArray(d) ? (d as Problem[]) : [{ field_id: "", item_id: null, reason: String(d) }] };
  }
  const out = (await r!.json()) as { revision: number; missing?: AppState["missing"] };
  return { revision: out.revision, missing: out.missing ?? [] };
}

export function saveAnswers(id: string, baseRevision: number, changes: Change[]): Promise<SaveResult> {
  return write(`/api/applications/${id}/answers`, "PUT", { base_revision: baseRevision, changes });
}

export async function addItem(id: string, baseRevision: number, kind: string): Promise<SaveResult & { id?: string } | SaveResult> {
  const r = await call(`/api/applications/${id}/items`, { method: "POST", headers: json,
    body: JSON.stringify({ kind, base_revision: baseRevision }) });
  const no = await refused(r);
  if (no) return no;
  if (r!.status === 409) return { conflict: ((await r!.json()) as { revision: number }).revision };
  if (r!.status === 422) return { invalid: [{ field_id: "", item_id: null, reason: String(await detail(r!)) }] };
  const out = (await r!.json()) as { id: string; revision: number };
  return { revision: out.revision, missing: [], id: out.id };
}

export function removeItem(id: string, baseRevision: number, itemId: string): Promise<SaveResult> {
  return write(`/api/applications/${id}/items/${itemId}`, "DELETE", { base_revision: baseRevision });
}

export function saveNote(id: string, baseRevision: number, sectionId: string, itemId: string | null, text: string): Promise<SaveResult> {
  return write(`/api/applications/${id}/notes`, "PUT", { base_revision: baseRevision, section_id: sectionId, item_id: itemId, text });
}

export const UPLOAD_MESSAGES: Record<string, string> = {
  too_large: "That file is too big. Each file can be up to 25 MB.",
  unsupported_type: "We can only take PDF, JPEG, PNG or HEIC files. If it's something else, save it as a PDF first.",
  infected: "Our virus check flagged that file, so we didn't keep it. Please check the file and try another copy.",
  scanner_unavailable: "We can't check files for viruses right now, so we can't take uploads. Please try again later.",
  store_unavailable: "We couldn't save the file just now. Please try again in a few minutes.",
  too_many_uploads: "You've uploaded a lot of files in the last hour. Please wait a while and try again.",
  unavailable: "We couldn't reach the Town's server. Please check your connection and try again.",
};

export function uploadFile(id: string, fieldId: string, itemId: string | null, file: File,
                           onProgress?: (fraction: number) => void): Promise<Attachment | { refused: string }> {
  return new Promise((resolve) => {
    const body = new FormData();
    body.append("field_id", fieldId);
    if (itemId) body.append("item_id", itemId);
    body.append("file", file);
    const xhr = new XMLHttpRequest();
    xhr.open("POST", `/api/applications/${id}/attachments`);
    xhr.upload.onprogress = (e) => e.lengthComputable && onProgress?.(e.loaded / e.total);
    xhr.onerror = () => resolve({ refused: "unavailable" });
    xhr.onload = () => {
      let parsed: { detail?: string } & Partial<Attachment> = {};
      try {
        parsed = JSON.parse(xhr.responseText);
      } catch {
        // A proxy's HTML error page: fall through to the status.
      }
      if (xhr.status === 201) return resolve(parsed as Attachment);
      if (xhr.status === 413) return resolve({ refused: "too_large" });
      if (xhr.status === 415) return resolve({ refused: "unsupported_type" });
      if (xhr.status === 429) return resolve({ refused: "too_many_uploads" });
      resolve({ refused: typeof parsed.detail === "string" && parsed.detail in UPLOAD_MESSAGES ? parsed.detail : "unavailable" });
    };
    xhr.send(body);
  });
}

export async function removeAttachment(attachmentId: string): Promise<boolean> {
  const r = await call(`/api/attachments/${attachmentId}`, { method: "DELETE" });
  return !!r && r.status === 204;
}
