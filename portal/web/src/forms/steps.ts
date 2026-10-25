// The application's steps (the redesign): the three shared start steps, the form's own steps
// (declared in its YAML), and Check and send. A step is a list of rows (questions that apply)
// or a hub of items (buildings, additions) whose questions sit on sheet pages.
import type { FormDef, FormSection, Page } from "../applications";
import type { StepStatus } from "../shell/types";
import { answerOf, applicable, missing, scope, shown, type Current, type Row } from "./applicability";

export const START_STEPS = [
  { id: "project", title: "Your project" },
  { id: "property", title: "Your property" },
  { id: "needs", title: "What you'll need" },
] as const;
export const REVIEW_STEP = { id: "review", title: "Check and send" } as const;

export type HubItem = { id: string; label: string; status: StepStatus; unknowns: number };
export type StepModel = {
  id: string; title: string; kind: "fields" | "hub";
  rows: Row[]; sections: FormSection[];
  hub?: { kind: string; repeat: NonNullable<FormSection["repeat"]>; pages: Page[]; items: HubItem[] };
};

const NOUNS: Record<string, string> = { building: "Building", component: "Addition" };

const stepOf = (r: Row) => r.field.step ?? r.section.step ?? null;
const isUnknown = (v: unknown) => typeof v === "object" && v !== null && (v as { unknown?: unknown }).unknown === true;
const empty = (v: unknown) => v === null || v === undefined || v === "" || (Array.isArray(v) && v.length === 0);

// "Building 2: Garage", from the item's name or kind when it has one.
export function itemLabel(form: FormDef, cur: Current, itemId: string): string {
  const item = cur.items.find((i) => i.id === itemId);
  if (!item) return "";
  const n = cur.items.filter((i) => i.kind === item.kind && i.position <= item.position).length;
  const base = `${NOUNS[item.kind] ?? item.kind} ${n}`;
  for (const s of form.sections.filter((x) => x.repeat?.kind === item.kind)) {
    for (const f of s.fields) {
      const v = answerOf(cur, f.id, itemId);
      if (typeof v === "string" && v && f.type === "text" && f.id.endsWith("_name")) return `${base}: ${v}`;
      if (typeof v === "string" && f.type === "choice" && (f.id.endsWith("_kind") || f.id.endsWith("_class"))) {
        const o = f.options.find((x) => x.value === v);
        // "Addition 1: Deck", but "Addition 1" rather than "Addition 1: addition".
        if (o) return o.official.toLowerCase() === (NOUNS[item.kind] ?? "").toLowerCase() ? base : `${base}: ${o.official}`;
      }
    }
  }
  return base;
}

function itemStatus(rows: Row[], gaps: Set<string>, cur: Current): { status: StepStatus; unknowns: number } {
  const answered = rows.filter((r) => !empty(answerOf(cur, r.field.id, r.itemId)) && answerOf(cur, r.field.id, r.itemId) !== r.field.default);
  const unknowns = rows.filter((r) => isUnknown(answerOf(cur, r.field.id, r.itemId))).length;
  const open = rows.some((r) => gaps.has(`${r.field.id}|${r.itemId ?? ""}`));
  return { status: !open && answered.length > 0 ? "done" : answered.length > 0 ? "started" : "todo", unknowns };
}

export function stepModels(form: FormDef, cur: Current): StepModel[] {
  const rows = applicable(form, cur);
  const gaps = new Set(missing(form, cur).map(([f, i]) => `${f}|${i ?? ""}`));
  const out: StepModel[] = [];
  for (const st of form.steps ?? []) {
    const sections = form.sections.filter((s) => s.step === st.id || s.fields.some((f) => f.step === st.id));
    const mine = rows.filter((r) => stepOf(r) === st.id);
    const repeat = sections.find((s) => s.repeat)?.repeat;
    if (repeat) {
      const first = sections.find((s) => s.repeat)!;
      if (!shown(first.show_if, scope(cur, null))) continue;
      const items = cur.items.filter((i) => i.kind === repeat.kind).sort((a, b) => a.position - b.position)
        .map((i) => ({ id: i.id, label: itemLabel(form, cur, i.id), ...itemStatus(mine.filter((r) => r.itemId === i.id), gaps, cur) }));
      const pages = sections.flatMap((s) => s.pages ?? []).filter((p, k, all) => all.findIndex((x) => x.id === p.id) === k);
      out.push({ id: st.id, title: st.title, kind: "hub", rows: mine, sections, hub: { kind: repeat.kind, repeat, pages, items } });
    } else if (mine.length > 0) {
      out.push({ id: st.id, title: st.title, kind: "fields", rows: mine, sections });
    }
  }
  return out;
}

// Done only once the applicant has opened the step (a switch already set by the form isn't an
// answer they've seen) and nothing required in it is missing.
export function statusOf(step: StepModel, cur: Current, visited: Set<string>): { status: StepStatus; unknowns: number } {
  const gaps = new Set(missing({ sections: step.sections } as FormDef, cur).map(([f, i]) => `${f}|${i ?? ""}`));
  const mineGaps = step.rows.some((r) => gaps.has(`${r.field.id}|${r.itemId ?? ""}`));
  const unknowns = step.rows.filter((r) => isUnknown(answerOf(cur, r.field.id, r.itemId))).length;
  const touched = step.rows.some((r) => {
    const v = answerOf(cur, r.field.id, r.itemId);
    return !empty(v) && v !== r.field.default;
  });
  const tooFew = step.hub ? step.hub.items.length < step.hub.repeat.min : false;
  if (visited.has(step.id) && !mineGaps && !tooFew) return { status: "done", unknowns };
  return { status: visited.has(step.id) || touched ? "started" : "todo", unknowns };
}
