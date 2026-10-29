import { valueOf, type Current } from "../forms/applicability";
import type { StepModel } from "../forms/steps";
import { cardsOf } from "../forms/tasks";
import type { FormDef } from "../projects";

const empty = (v: unknown) => v === null || v === undefined || v === "" || (Array.isArray(v) && v.length === 0);

// Each row (a part, About you, Your lot) with something required still blank, and its first such
// card: Check and send's "things to finish first", and the dashboard's Continue button.
export function todoRows(form: FormDef, cur: Current, models: StepModel[], base: string): { id: string; title: string; href: string }[] {
  return models.flatMap((m) => {
    const card = cardsOf(form, cur, m).find((s) => s.rows.some((r) => r.field.required && r.field.type !== "upload"
      && empty(valueOf(form, r.field, r.itemId, cur))));
    if (!card) return [];
    const q = new URLSearchParams({ screen: card.id, ...(card.itemId ? { item: card.itemId } : {}) });
    return [{ id: m.id, title: m.title, href: `${base}/${m.id}?${q.toString()}` }];
  });
}
