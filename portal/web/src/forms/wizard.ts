// The wizard's screens: one question each, in form order, only those that apply,
// with an "Add another…?" screen after each repeating part (buildings, components).
import type { FormDef, FormField, FormSection } from "../applications";
import { answerOf, applicable, blocks, scope, shown, type Current } from "./applicability";

export type QuestionScreen = {
  kind: "question"; key: string; chapter: string; section: FormSection; field: FormField;
  itemId: string | null; itemLabel: string | null;
};
export type AddScreen = {
  kind: "add"; key: string; chapter: string; repeat: NonNullable<FormSection["repeat"]>; count: number;
};
export type Screen = QuestionScreen | AddScreen;

const NOUNS: Record<string, string> = { building: "Building", component: "Addition, porch or deck" };

export function screenKey(sectionId: string, fieldId: string, itemId: string | null): string {
  return `${sectionId}.${fieldId}${itemId ? `.${itemId}` : ""}`;
}

// "Building 2: barn", from the item's own name answer when it has one.
export function itemLabel(form: FormDef, cur: Current, itemId: string): string {
  const item = cur.items.find((i) => i.id === itemId);
  if (!item) return "";
  const n = cur.items.filter((i) => i.kind === item.kind && i.position <= item.position).length;
  const base = `${NOUNS[item.kind] ?? item.kind} ${n}`;
  for (const s of form.sections.filter((s) => s.repeat?.kind === item.kind)) {
    for (const f of s.fields) {
      const v = answerOf(cur, f.id, itemId);
      if (typeof v === "string" && f.type === "text" && v) return `${base}: ${v}`;
      if (typeof v === "string" && f.type === "choice") {
        const o = f.options.find((x) => x.value === v);
        if (o) return `${NOUNS[item.kind] ? `${NOUNS[item.kind].split(",")[0]} ${n}` : base}: ${o.official.toLowerCase()}`;
      }
    }
  }
  return base;
}

export function screens(form: FormDef, cur: Current): Screen[] {
  const rows = applicable(form, cur);
  const out: Screen[] = [];
  const seenRuns = new Set<string>();
  const order = blocks(form, cur);
  const sections = form.sections;
  for (let i = 0; i < sections.length; i += 1) {
    const s = sections[i];
    if (s.repeat && seenRuns.has(`${i}`)) continue;
    const run = [s];
    if (s.repeat) {
      while (i + run.length < sections.length && sections[i + run.length].repeat?.kind === s.repeat.kind) {
        seenRuns.add(`${i + run.length}`);
        run.push(sections[i + run.length]);
      }
    }
    const ids = new Set(run.map((r) => r.id));
    for (const b of order.filter((b) => ids.has(b.section.id))) {
      for (const r of rows.filter((r) => r.section.id === b.section.id && r.itemId === b.itemId)) {
        out.push({ kind: "question", key: screenKey(r.section.id, r.field.id, r.itemId), chapter: r.section.chapter,
                   section: r.section, field: r.field, itemId: r.itemId,
                   itemLabel: r.itemId ? itemLabel(form, cur, r.itemId) : null });
      }
    }
    // Offer another only while the repeating part applies at all (a site-only project
    // has no buildings to add).
    if (s.repeat && shown(s.show_if, scope(cur, null))) {
      const count = cur.items.filter((it) => it.kind === s.repeat!.kind).length;
      if (count < s.repeat.max) out.push({ kind: "add", key: `add.${s.repeat.kind}`, chapter: s.chapter, repeat: s.repeat, count });
    }
  }
  return out;
}
