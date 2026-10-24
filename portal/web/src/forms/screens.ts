// The wizard's screens (brief 2026-10-24): a step's questions one per screen, in the form's order.
// Fields a form groups with `screen:` share one (deed book and page; the four setbacks). A building
// or an addition runs its screens in turn, ask-first questions leading, and the step ends with "Is
// there another?"; an empty additions step asks first whether there are any.
import type { FormDef, FormField } from "../applications";
import { controlFor } from "../controls/FieldControl";
import type { Current, Row } from "./applicability";
import type { StepModel } from "./steps";

export type ScreenKind = "choice" | "multi" | "picker" | "number" | "stepper" | "slider" | "text" | "long"
  | "set" | "confirm" | "setbacks" | "walls" | "facing" | "upload" | "point" | "uses" | "another" | "any";
export type Screen = {
  id: string;              // first field's id; "another:<kind>" or "any:<kind>" for loop questions
  step: string; itemId: string | null; kind: ScreenKind; rows: Row[];
  auto: boolean;           // moves on at a tap
  optional: boolean;       // shows "Skip for now"
  unknown: boolean;        // offers "I don't know yet"
};
export type Place = { step: string; screen: string; item?: string };

const TAP = new Set(["switch", "segmented", "tiles", "building-type", "building-picker", "street-picker"]);
const AUTO_KINDS = new Set<ScreenKind>(["choice", "facing", "another", "any"]);

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

function build(cur: Current, rows: Row[], step: string, itemId: string | null): Screen[] {
  const out: Screen[] = [];
  const groups = new Map<string, Screen>();
  for (const r of rows) {
    const g = r.field.screen;
    if (g) {
      const key = `${r.section.id}:${g}`;
      const open = groups.get(key);
      if (open) {
        open.rows.push(r);
        open.optional &&= !r.field.required;
        open.unknown &&= r.field.allow_unknown;
        continue;
      }
      const layout = r.section.screens?.find((x) => x.id === g)?.layout ?? null;
      const s = screen(step, itemId, layout === "lot-diagram" ? "setbacks" : layout === "compass" ? "walls" : "set", [r]);
      groups.set(key, s);
      out.push(s);
    } else {
      out.push(screen(step, itemId, kindOf(cur, r.field), [r]));
    }
  }
  return out;
}

export function screensOf(form: FormDef, cur: Current, step: StepModel): Screen[] {
  void form;
  if (step.kind !== "hub" || !step.hub) return build(cur, step.rows, step.id, null);
  const kind = step.hub.kind;
  const items = step.hub.items;
  if (items.length === 0) return [screen(step.id, null, "any", [], `any:${kind}`)];
  const out: Screen[] = [];
  for (const item of items) {
    const rows = step.rows.filter((r) => r.itemId === item.id);
    const ordered = [...rows.filter((r) => r.field.ask_first), ...rows.filter((r) => !r.field.ask_first)];
    out.push(...build(cur, ordered, step.id, item.id));
  }
  out.push(screen(step.id, items[items.length - 1].id, "another", [], `another:${kind}`));
  return out;
}

// The screens that share a trail and dots: the same step, and the same building or addition.
export function groupOf(screens: Screen[], s: Screen): Screen[] {
  return screens.filter((x) => x.step === s.step && x.itemId === s.itemId);
}

const place = (s: Screen): Place => ({ step: s.step, screen: s.id, ...(s.itemId ? { item: s.itemId } : {}) });

// Where Continue (or a tap) goes from `at`: the next screen in its step, else the next step's first,
// else review. A screen that stopped applying (an owner question after "I own it") is placed by the
// form's field order, so the applicant lands on the next question that still applies.
export function screenAfter(form: FormDef, cur: Current, models: StepModel[], at: Place): Place | { review: true } {
  const fieldOrder = new Map(form.sections.flatMap((s) => s.fields).map((f, i) => [f.id, i]));
  const stepOrder = (form.steps ?? []).map((s) => s.id);
  let m = models.findIndex((x) => x.id === at.step);
  if (m < 0) {
    // The step itself stopped applying (no building work any more): carry on from the next one.
    const next = models.findIndex((x) => stepOrder.indexOf(x.id) > stepOrder.indexOf(at.step));
    if (next < 0) return { review: true };
    m = next - 1;
  } else {
    const list = screensOf(form, cur, models[m]);
    const i = list.findIndex((s) => s.id === at.screen && (at.item === undefined || s.itemId === at.item));
    if (i >= 0 && i < list.length - 1) return place(list[i + 1]);
    if (i < 0) {
      const from = fieldOrder.get(at.screen) ?? Infinity;
      const later = list.find((s) => (at.item === undefined || s.itemId === at.item) && (fieldOrder.get(s.id) ?? -1) > from);
      if (later) return place(later);
    }
  }
  for (let n = m + 1; n < models.length; n++) {
    const list = screensOf(form, cur, models[n]);
    if (list.length) return place(list[0]);
  }
  return { review: true };
}
