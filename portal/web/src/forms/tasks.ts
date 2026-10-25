// The application as a short list of tasks (task-list brief, 2026-10-25): each task is today's
// step, run as a few cards; a building or an addition is its own run of cards. A task's status
// shows as a pill on the task list, and "Check and send" opens once every task is done.
import type { FormDef } from "../applications";
import { answerOf, missing, type Current } from "./applicability";
import { buildCards, itemRows, type Screen } from "./screens";
import { itemLabel, statusOf, type StepModel } from "./steps";

export type TaskStatus = { kind: "done" } | { kind: "progress"; answered: number; total: number } | { kind: "todo" };

const empty = (v: unknown) => v === null || v === undefined || v === "" || (Array.isArray(v) && v.length === 0);

// A task's cards (a building's, when `itemId` is given; a whole hub's otherwise).
export function cardsOf(form: FormDef, cur: Current, step: StepModel, itemId?: string): Screen[] {
  if (step.kind !== "hub" || !step.hub) return buildCards(form, cur, step.rows, step.id, null);
  const items = itemId ? step.hub.items.filter((i) => i.id === itemId) : step.hub.items;
  return items.flatMap((i) => buildCards(form, cur, itemRows(step, i.id), step.id, i.id));
}

// A card is answered when each of its questions has a value (a form's default counts: it is shown
// chosen); a task has started once any answer differs from the form's default.
const answered = (cur: Current, s: Screen) =>
  s.rows.length > 0 && s.rows.every((r) => !empty(answerOf(cur, r.field.id, r.itemId)));
const touched = (cur: Current, step: StepModel) => step.rows.some((r) => {
  const v = answerOf(cur, r.field.id, r.itemId);
  return !empty(v) && v !== r.field.default;
});

export function taskStatus(form: FormDef, cur: Current, step: StepModel, visited: Set<string>): TaskStatus {
  if (statusOf(step, cur, visited).status === "done") return { kind: "done" };
  if (!touched(cur, step)) return { kind: "todo" };
  const cards = cardsOf(form, cur, step);
  return { kind: "progress", answered: cards.filter((s) => answered(cur, s)).length, total: cards.length };
}

export const canSend = (statuses: TaskStatus[]) => statuses.every((s) => s.kind === "done");

// The bar: one segment per card that applies now, and never fewer than are already answered, so
// reaching the end can't shrink it.
export function progressOf(cards: Screen[], at: Screen, answeredBefore: number): { count: number; at: number } {
  return { count: Math.max(cards.length, answeredBefore), at: Math.max(0, cards.indexOf(at)) };
}

const left = (form: FormDef, cur: Current, itemId: string) => missing(form, cur).filter(([, i]) => i === itemId).length;
const num = (cur: Current, itemId: string, re: RegExp) => {
  const id = cur.answers.find((x) => x.item_id === itemId && re.test(x.field_id) && typeof x.value === "number")?.field_id;
  return id ? (answerOf(cur, id, itemId) as number) : null;
};

// A building's line on the buildings list: "28 × 40 ft · 2 floors · 2,240 sq ft · front faces
// north", from what it has; "3 answers to go" while unfinished.
export function itemSummary(form: FormDef, cur: Current, itemId: string): string {
  const n = left(form, cur, itemId);
  if (n > 0) return `${n} ${n === 1 ? "answer" : "answers"} to go`;
  const w = num(cur, itemId, /(^mass|^component)_width$/), d = num(cur, itemId, /(^mass|^component)_depth$/);
  const floors = num(cur, itemId, /^stories$/), area = num(cur, itemId, /^floor_area$/);
  const facing = cur.answers.find((x) => x.item_id === itemId && /front_facing$/.test(x.field_id))?.value;
  return [
    w !== null && d !== null ? `${w} × ${d} ft` : null,
    floors !== null ? `${floors} ${floors === 1 ? "floor" : "floors"}` : null,
    area !== null ? `${area.toLocaleString("en-US")} sq ft` : null,
    typeof facing === "string" ? `front faces ${facing}` : null,
  ].filter(Boolean).join(" · ");
}

// "Copy Building 1": the first finished item of that kind, named by its number.
export function firstCopySource(form: FormDef, cur: Current, kind: string): { id: string; label: string } | null {
  const items = cur.items.filter((i) => i.kind === kind).sort((x, y) => x.position - y.position);
  const done = items.find((i) => left(form, cur, i.id) === 0 && cur.answers.some((x) => x.item_id === i.id));
  return done ? { id: done.id, label: itemLabel(form, cur, done.id).split(":")[0] } : null;
}

// The task list's icons and hints (task-list brief §4.2 and §5), by step id.
export const TASK_ICONS: Record<string, string> = {
  your_lot: "map-2", about_you: "user", the_work: "hammer", buildings: "building-cottage", additions: "stairs",
  driveway: "road", meets_road: "map-pin", safety: "eye", state_permit: "file-certificate",
  uses_today: "building-store", your_plan: "building-store", photos: "photo", review: "signature",
};
export const TASK_HINTS: Record<string, string> = {
  your_lot: "Size, frontage and what is there now",
  the_work: "What you are building, and a sketch",
  buildings: "One short set of questions for each",
};
