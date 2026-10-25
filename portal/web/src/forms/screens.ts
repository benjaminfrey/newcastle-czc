// The cards (task-list brief, 2026-10-25): a step's questions one to a card, in the form's order;
// questions a form gathers with `screen:` share one (deed book and page; a building's size; the
// four setbacks). A building's or an addition's cards run with its ask-first questions leading.
// Which cards a task has, and where its run goes, is forms/tasks.ts.
import type { FormDef, FormField } from "../applications";
import { controlFor } from "../controls/FieldControl";
import type { Current, Row } from "./applicability";
import type { StepModel } from "./steps";

export type ScreenKind = "choice" | "multi" | "picker" | "number" | "stepper" | "slider" | "text" | "long"
  | "set" | "confirm" | "setbacks" | "walls" | "facing" | "upload" | "point" | "uses";
export type Screen = {
  id: string;              // its first question's id
  step: string; itemId: string | null; kind: ScreenKind; rows: Row[];
  auto: boolean;           // moves on at a tap
  optional: boolean;       // shows "Skip for now"
  unknown: boolean;        // offers "I don't know yet"
  title?: string | null;   // a card that gathers several asks its own question ("How big is the building?")
  help?: string | null;
};

const TAP = new Set(["switch", "segmented", "tiles", "building-type", "building-picker", "street-picker"]);
const AUTO_KINDS = new Set<ScreenKind>(["choice", "facing"]);

// The Town's map knows this value (an address, the lot's acres, its roads).
function mapHas(cur: Current, from: string | null): boolean {
  const v = from ? (cur.property as Record<string, unknown>)[from] : null;
  return Array.isArray(v) ? v.length > 0 : v !== null && v !== undefined && v !== "";
}

function kindOf(cur: Current, f: FormField): ScreenKind {
  if (f.source === "property" && f.may_correct && mapHas(cur, f.from)) return "confirm";
  if (f.id.endsWith("front_facing")) return "facing";
  const c = controlFor(f);
  if (TAP.has(c)) return "choice";
  switch (c) {
    case "picker": return "picker";
    case "chips": return "multi";
    case "stepper": return "stepper";
    case "slider": return "slider";
    case "number": return "number";
    case "longtext": return "long";
    case "upload": return "upload";
    case "point": return "point";
    case "uses": return "uses";
    default: return "text";
  }
}

function screen(step: string, itemId: string | null, kind: ScreenKind, rows: Row[], id = rows[0].field.id): Screen {
  return { id, step, itemId, kind, rows, auto: AUTO_KINDS.has(kind),
           optional: rows.length > 0 && rows.every((r) => !r.field.required),
           unknown: rows.length > 0 && rows.every((r) => r.field.allow_unknown) };
}

// A card's declaration (its drawing, its own question): any section of its repeat may declare it.
function declOf(form: FormDef, row: Row, g: string) {
  const kind = row.section.repeat?.kind ?? null;
  for (const s of form.sections) {
    if ((s.repeat?.kind ?? null) !== kind) continue;
    const found = s.screens?.find((x) => x.id === g);
    if (found) return found;
  }
  return null;
}

// A step's (or one item's) questions as cards: a question alone, or the questions that share a
// `screen` — gathered across sections (a building's name and its homes) — placed where the first
// of them is asked.
export function buildCards(form: FormDef, cur: Current, rows: Row[], step: string, itemId: string | null): Screen[] {
  const out: Screen[] = [];
  const groups = new Map<string, Screen>();
  for (const r of rows) {
    const g = r.field.screen;
    if (g) {
      const key = g;
      const open = groups.get(key);
      if (open) {
        open.rows.push(r);
        open.optional &&= !r.field.required;
        open.unknown &&= r.field.allow_unknown;
        continue;
      }
      const decl = declOf(form, r, g);
      const layout = decl?.layout ?? null;
      const s = { ...screen(step, itemId, layout === "lot-diagram" ? "setbacks" : layout === "compass" ? "walls" : "set", [r]),
                  title: decl?.title ?? null, help: decl?.help ?? null };
      groups.set(key, s);
      out.push(s);
    } else {
      out.push(screen(step, itemId, kindOf(cur, r.field), [r]));
    }
  }
  return out;
}

// An item's questions in asking order: ask-first ones by rank (the building's type, then whether
// it's only being renovated), then the rest in the form's order.
const rank = (r: Row) => Number(r.field.ask_first ?? 0);
// Ranked questions first, by rank (the form's order among equals), then the rest in the form's order.
export function ranked(rows: Row[]): Row[] {
  return [...rows.filter((r) => rank(r) > 0).sort((x, y) => rank(x) - rank(y)), ...rows.filter((r) => rank(r) === 0)];
}
export function itemRows(step: StepModel, itemId: string): Row[] {
  return ranked(step.rows.filter((r) => r.itemId === itemId));
}
