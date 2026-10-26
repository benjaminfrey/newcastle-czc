// Projects (projects brief §5.4): the forms and parts (public) and an applicant's projects (signed in).
//
// The cards speak of items: a building, an addition. The API speaks of parts, and every part
// is an item here (part_id ↔ item_id), so the card code reads a project as it read an application.
import type { Expr } from "./forms/expr";

export type Option = { value: string; label: string; official: string; icon?: string | null }; // icon: an outline icon (controls/Icon)
export type FormField = {
  id: string; official_label: string;
  source: "question" | "property" | "account" | "derived" | "at_submit" | "staff" | "parts";
  from: string | null; may_correct: boolean; label: string | null; help: string | null;
  why: { cite: string; text: string } | null;
  type: "text" | "longtext" | "number" | "choice" | "multichoice" | "yesno" | "date" | "uses" | "point" | "upload" | null;
  unit: string | null; min: number | null; max: number | null; required: boolean; allow_unknown: boolean;
  show_if: Expr | null; options: Option[];
  // The wizard's layer (forms/formdefs.py): the step it's asked in (resolved), the screen it shares
  // with others (deed book and page), whether it's asked before the rest of its item, the control
  // to draw, the slider increment, a starting value, address autofill.
  step?: string | null; screen?: string | null; ask_first?: number | boolean;
  /** @deprecated sheet pages, gone from the API; read only by the item sheet until it is removed. */
  page?: string | null;
  control?: "stepper" | "slider" | "switch" | "segmented" | "tiles" | "picker" | "chips"
    | "building-picker" | "street-picker" | "building-type" | null;
  step_size?: number | null; default?: unknown; autocomplete?: "name" | "tel" | "email" | "street-address" | null;
  copies?: boolean; // "Copy Building 1" brings this answer to the new building
  short?: string | null; // its name beside its field on a shared card ("Width")
};
export type Page = { id: string; title: string; layout: "compass" | "lot-diagram" | null };
export type AddOption = { label: string; preset: Record<string, unknown> };
export type ScreenGroup = { id: string; layout: "compass" | "lot-diagram" | null; title?: string | null; help?: string | null }; // a card: its drawing, its own question and help
export type FormSection = {
  id: string; official_title: string; chapter: string; show_if: Expr | null;
  repeat: { kind: string; add_label: string; min: number; max: number; add_options?: AddOption[] } | null;
  fields: FormField[];
  step?: string | null; screens?: ScreenGroup[];
  /** @deprecated see FormField.page. */
  pages?: Page[];
};
export type FormDef = {
  key: string; version: number; ruleset_key: string; official_title: string; sections: FormSection[];
  steps?: { id: string; title: string }[];
};

export type Item = { id: string; kind: string; position: number }; // a part of the project
export type Attachment = { id: string; field_id: string; item_id: string | null; filename: string; content_type: string; size_bytes: number };
export type Snapshot = {
  source: "lookup" | "manual"; parcel_id: number | null; map_lot: string; facts: Record<string, unknown>;
  parcels_as_of: string | null; verified: boolean; disputed: boolean; note: string;
};
export type Status = "draft" | "submitted" | "locked" | "decided";
export type Clock = { key: string; label: string; plain: string | null; days: number; basis: string; when: string | null;
  due?: string; approximate?: boolean; due_words?: string };
export type Fee = number | "varies" | { per_sf: number };
export type ReviewNeed = {
  review_key: string; use_key: string | null; part_id?: string; name: string; code_name: string; plain: string | null;
  reviewer: string | null; certainty: "needed" | "may_need"; in_portal: boolean; districts: string[];
  fee: Fee; fee_words: string; clocks: Clock[];
};
export type Permit = { key: string; name: string; application_fee: Fee | null; application_fee_words: string | null; reviews: ReviewNeed[] };
export type Needs = {
  permits: Permit[]; application_fees_total: number; application_fees_vary: boolean;
  notes: { kind: string; text: string; cite: string }[]; not_listed: { district: string; use: string; text: string }[];
  town_only: boolean;
} | { refused: string };
export type Missing = { field_id: string; item_id: string | null }[];
export type ProjectState = {
  id: string; title: string; status: Status; revision: number; ruleset_key: string; submitted_at: string | null;
  property: Snapshot; items: Item[]; forms: Record<string, number>; form: FormDef; needs: Needs | null;
  answers: { field_id: string; item_id: string | null; value: unknown; derived?: boolean }[];
  notes: { section_id: string; item_id: string | null; text: string }[];
  attachments: Attachment[];
  missing: Missing;
};
export type ProjectSummary = { id: string; title: string; status: Status; map_lot: string; updated_at: string;
  submitted_at: string | null; first_part: string | null; left: number };
export type PartDef = { id: string; label: string; step: string; icon: string; repeats: boolean };
export type PropertyChoice = { source: "lookup"; parcel_id: number } | { source: "manual"; map_lot: string; district_code: string | null };
export type NewProject = { property: PropertyChoice; disputed: boolean; note: string; parts: string[]; title: string | null };
export type Change = { field_id: string; item_id: string | null; value: unknown };
export type Problem = { field_id: string; item_id: string | null; reason: string };

// "signed_out": the session ended; "not_approved": the form still has entries the chair
// hasn't approved; "busy": too many requests from this address in the last minute;
// "unavailable": the server or the connection failed; "locked": the Town has locked the project
// for review, so the applicant can't change it.
export type Refusal = "signed_out" | "not_approved" | "busy" | "unavailable" | "not_found" | "locked";
export type SaveResult = { revision: number; missing: Missing } | { conflict: number } | { invalid: Problem[] }
  | { incomplete: Missing } | Refusal;

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
  if (r.status === 429) return "busy";
  if (r.status === 401) return "signed_out";
  if (r.status === 404) return "not_found";
  if (r.status === 409 && (await detail(r.clone())) === "locked") return "locked";
  return null;
}

type WithPart = { part_id?: string | null };
function fromPart<T extends WithPart>(x: T): Omit<T, "part_id"> & { item_id: string | null } {
  const { part_id, ...rest } = x;
  return { ...rest, item_id: part_id ?? null };
}
const toPart = (c: Change) => ({ field_id: c.field_id, part_id: c.item_id, value: c.value });

// A form version never changes, so each is fetched once per page session. Refusals are not kept.
const formCache = new Map<string, FormDef>();

export function clearFormCache(): void {
  formCache.clear();
}

export async function getForm(key: string, version?: number): Promise<FormDef | Refusal> {
  const url = version ? `/api/forms/${key}/v/${version}` : `/api/forms/${key}`;
  const kept = formCache.get(url);
  if (kept) return kept;
  const r = await call(url);
  const no = await refused(r);
  if (no) return no;
  const form = (await r!.json()) as FormDef;
  if (version) formCache.set(url, form);
  return form;
}

export async function getParts(): Promise<PartDef[] | Refusal> {
  const r = await call("/api/parts");
  return (await refused(r)) ?? ((await r!.json()) as PartDef[]);
}

export async function createProject(body: NewProject): Promise<{ id: string } | Refusal | "property_unavailable" | "invalid"> {
  const r = await call("/api/projects", { method: "POST", headers: json, body: JSON.stringify(body) });
  if (r && r.status === 503 && (await detail(r.clone())) === "property_unavailable") return "property_unavailable";
  const no = await refused(r);
  if (no) return no;
  if (r!.status === 422) return "invalid";
  return (await r!.json()) as { id: string };
}

export async function listProjects(): Promise<ProjectSummary[] | Refusal> {
  const r = await call("/api/projects");
  return (await refused(r)) ?? ((await r!.json()) as ProjectSummary[]);
}

type ProjectBody = Omit<ProjectState, "items" | "answers" | "notes" | "attachments" | "missing"> & {
  parts: Item[]; answers: (ProjectState["answers"][number] & WithPart)[]; notes: WithPart[]; attachments: WithPart[];
  missing: WithPart[];
};

export async function getProject(id: string): Promise<ProjectState | Refusal> {
  const r = await call(`/api/projects/${id}`);
  const no = await refused(r);
  if (no) return no;
  const { parts, answers, notes, attachments, missing, ...rest } = (await r!.json()) as ProjectBody;
  return {
    ...rest, items: parts,
    answers: answers.map(fromPart) as ProjectState["answers"],
    notes: notes.map(fromPart) as ProjectState["notes"],
    attachments: attachments.map(fromPart) as Attachment[],
    missing: missing.map(fromPart) as Missing,
  };
}

async function write(url: string, method: string, body: unknown): Promise<SaveResult> {
  const r = await call(url, { method, headers: json, body: JSON.stringify(body) });
  const no = await refused(r);
  if (no) return no;
  if (r!.status === 409) return { conflict: ((await r!.json()) as { revision: number }).revision };
  if (r!.status === 422) {
    const body422 = (await r!.json().catch(() => ({}))) as { detail?: unknown; missing?: WithPart[] };
    if (body422.detail === "incomplete") return { incomplete: (body422.missing ?? []).map(fromPart) as Missing };
    const d = body422.detail;
    return { invalid: Array.isArray(d) ? (d as WithPart[]).map(fromPart) as Problem[]
      : [{ field_id: "", item_id: null, reason: String(d) }] };
  }
  const out = (await r!.json()) as { revision: number; missing?: WithPart[] };
  return { revision: out.revision, missing: (out.missing ?? []).map(fromPart) as Missing };
}

export function saveAnswers(id: string, baseRevision: number, changes: Change[]): Promise<SaveResult> {
  return write(`/api/projects/${id}/answers`, "PUT", { base_revision: baseRevision, changes: changes.map(toPart) });
}

// A new part; for a building or an addition with `copyFrom`, "Copy Building 1" (that part's copied answers come too).
export async function addPart(id: string, baseRevision: number, kind: string, copyFrom?: string): Promise<SaveResult & { id?: string } | SaveResult> {
  const r = await call(`/api/projects/${id}/parts`, { method: "POST", headers: json,
    body: JSON.stringify({ kind, base_revision: baseRevision, ...(copyFrom === undefined ? {} : { copy_from: copyFrom }) }) });
  const no = await refused(r);
  if (no) return no;
  if (r!.status === 409) return { conflict: ((await r!.json()) as { revision: number }).revision };
  if (r!.status === 422) return { invalid: [{ field_id: "", item_id: null, reason: String(await detail(r!)) }] };
  const out = (await r!.json()) as { id: string; revision: number };
  return { revision: out.revision, missing: [], id: out.id };
}

export function removePart(id: string, baseRevision: number, partId: string): Promise<SaveResult> {
  return write(`/api/projects/${id}/parts/${partId}`, "DELETE", { base_revision: baseRevision });
}

export function saveNote(id: string, baseRevision: number, sectionId: string, itemId: string | null, text: string): Promise<SaveResult> {
  return write(`/api/projects/${id}/notes`, "PUT", { base_revision: baseRevision, section_id: sectionId, part_id: itemId, text });
}

export function setTitle(id: string, baseRevision: number, title: string): Promise<SaveResult> {
  return write(`/api/projects/${id}/title`, "PUT", { base_revision: baseRevision, title });
}

export function submitProject(id: string, baseRevision: number): Promise<SaveResult> {
  return write(`/api/projects/${id}/submit`, "POST", { base_revision: baseRevision });
}

export const UPLOAD_MESSAGES: Record<string, string> = {
  too_large: "That file is too big. Each file can be up to 25 MB.",
  unsupported_type: "We can only take PDF, JPEG, PNG or HEIC files. If it's something else, save it as a PDF first.",
  infected: "Our virus check flagged that file, so we didn't keep it. Please check the file and try another copy.",
  scanner_unavailable: "We can't check files for viruses right now, so we can't take uploads. Please try again later.",
  store_unavailable: "We couldn't save the file just now. Please try again in a few minutes.",
  too_many_uploads: "You've uploaded a lot of files in the last hour. Please wait a while and try again.",
  unavailable: "We couldn't reach the Town's server. Please check your connection and try again.",
  locked: "The Town is reviewing this project, so files can't be added or removed now.",
};

export function uploadFile(id: string, fieldId: string, itemId: string | null, file: File,
                           onProgress?: (fraction: number) => void): Promise<Attachment | { refused: string }> {
  return new Promise((resolve) => {
    const body = new FormData();
    body.append("field_id", fieldId);
    if (itemId) body.append("part_id", itemId);
    body.append("file", file);
    const xhr = new XMLHttpRequest();
    xhr.open("POST", `/api/projects/${id}/attachments`);
    xhr.upload.onprogress = (e) => e.lengthComputable && onProgress?.(e.loaded / e.total);
    xhr.onerror = () => resolve({ refused: "unavailable" });
    xhr.onload = () => {
      let parsed: { detail?: string } & Partial<Attachment> = {};
      try {
        parsed = JSON.parse(xhr.responseText);
      } catch {
        // A proxy's HTML error page: fall through to the status.
      }
      if (xhr.status === 201) return resolve(fromPart(parsed as Attachment & { part_id: string | null }));
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
