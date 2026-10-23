// Which questions apply — the browser's copy of the rules in
// portal_api/forms/expr.py (shown) and answers.py, checked against
// applicability-fixtures.json on both sides.
import type { FormDef, FormField, FormSection } from "../applications";
import { evaluate, type Expr } from "./expr";

// A question is asked unless its condition is known to be false: an answer still
// missing, or a property fact nobody knows, keeps the question in.
export function shown(showIf: Expr | null | undefined, data: Record<string, unknown>): boolean {
  return !showIf || evaluate(showIf, data) !== false;
}

// ---- What applies, what's missing, what prints (twin of answers.py) ----


export type Answer = { field_id: string; item_id: string | null; value: unknown };
export type Current = {
  answers: Answer[];
  items: { id: string; kind: string; position: number }[];
  property: Record<string, unknown>;
  account: Record<string, unknown>;
};
export type Row = { section: FormSection; field: FormField; itemId: string | null };
export type Block = { section: FormSection; itemId: string | null; rows: { field: FormField; value: unknown }[] };

export const isQuestion = (f: FormField) => f.source === "question" || f.may_correct;

export function answerOf(cur: Current, fieldId: string, itemId: string | null): unknown {
  return cur.answers.find((a) => a.field_id === fieldId && a.item_id === itemId)?.value ?? null;
}

export function scope(cur: Current, itemId: string | null): Record<string, unknown> {
  const answers: Record<string, unknown> = {};
  const item: Record<string, unknown> = {};
  for (const a of cur.answers) {
    if (a.item_id === null) answers[a.field_id] = a.value;
    else if (itemId !== null && a.item_id === itemId) item[a.field_id] = a.value;
  }
  return { answers, item, property: cur.property };
}

function liveItems(cur: Current, kind: string): string[] {
  return cur.items.filter((i) => i.kind === kind).sort((a, b) => a.position - b.position).map((i) => i.id);
}

// (section, item) in form order; a run of sections repeating the same kind is walked
// item by item, so each building gets all of its sections in turn.
export function blocks(form: FormDef, cur: Current): { section: FormSection; itemId: string | null }[] {
  const out: { section: FormSection; itemId: string | null }[] = [];
  const ss = form.sections;
  for (let i = 0; i < ss.length;) {
    const s = ss[i];
    if (!s.repeat) {
      out.push({ section: s, itemId: null });
      i += 1;
      continue;
    }
    const run = [s];
    while (i + run.length < ss.length && ss[i + run.length].repeat?.kind === s.repeat.kind) run.push(ss[i + run.length]);
    for (const itemId of liveItems(cur, s.repeat.kind)) for (const r of run) out.push({ section: r, itemId });
    i += run.length;
  }
  return out;
}

function shownBlocks(form: FormDef, cur: Current) {
  return blocks(form, cur)
    .map((b) => ({ ...b, data: scope(cur, b.itemId) }))
    .filter((b) => shown(b.section.show_if, b.data));
}

export function applicable(form: FormDef, cur: Current): Row[] {
  return shownBlocks(form, cur).flatMap((b) =>
    b.section.fields.filter((f) => isQuestion(f) && shown(f.show_if, b.data))
      .map((field) => ({ section: b.section, field, itemId: b.itemId })));
}

function propertyValue(key: string | null, prop: Record<string, unknown>, prefill: boolean): unknown {
  if (!key) return null;
  const v = prop[key];
  if (key === "districts") {
    const names = ((v as { name?: string | null; code?: string }[]) ?? []).map((d) => d.name || d.code).filter(Boolean);
    return names.length ? names.join("; ") : null;
  }
  if (key === "streets") {
    const streets = (v as { name: string; type_name?: string | null; frontage_ft?: number | null }[]) ?? [];
    if (streets.length === 0) return null;
    if (prefill) return streets.reduce((n, s) => n + (s.frontage_ft ?? 0), 0);
    return streets.map((s) => s.name + (s.type_name ? ` (${s.type_name})` : "")
      + (s.frontage_ft != null ? `, about ${s.frontage_ft} ft` : "")).join("; ");
  }
  return v ?? null;
}

export function valueOf(form: FormDef, f: FormField, itemId: string | null, cur: Current, depth = 0): unknown {
  if (isQuestion(f)) {
    const v = answerOf(cur, f.id, itemId);
    return v === null && f.may_correct ? propertyValue(f.from, cur.property, true) : v;
  }
  if (f.source === "property") return propertyValue(f.from, cur.property, false);
  if (f.source === "account") return cur.account[f.from ?? ""] ?? null;
  if (f.source === "derived" && depth < 5) {
    const src = form.sections.flatMap((s) => s.fields).find((x) => x.id === f.from);
    return src ? valueOf(form, src, null, cur, depth + 1) : propertyValue(f.from, cur.property, false);
  }
  return null;
}

const empty = (v: unknown) => v === null || v === undefined || v === "" || (Array.isArray(v) && v.length === 0);

export function missing(form: FormDef, cur: Current): [string, string | null][] {
  return applicable(form, cur)
    .filter((r) => r.field.required && r.field.type !== "upload" && empty(valueOf(form, r.field, r.itemId, cur)))
    .map((r) => [r.field.id, r.itemId]);
}

export function printed(form: FormDef, cur: Current): Block[] {
  return shownBlocks(form, cur).map((b) => ({
    section: b.section, itemId: b.itemId,
    rows: b.section.fields.filter((f) => !isQuestion(f) || shown(f.show_if, b.data))
      .map((field) => ({ field, value: valueOf(form, field, b.itemId, cur) })),
  }));
}
