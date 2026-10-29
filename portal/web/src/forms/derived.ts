// The answers worked out from a project's parts, never typed: the twin of
// portal_api/forms/parts.py `derived`. "Type of project" prints from the parts (projects brief
// §4), and the homes in the new buildings decide whether the five-year homes question is asked.
import type { Answer, Current } from "./applicability";

// parts.yaml's work_kind for each part.
const WORK_KIND: Record<string, string> = { building: "new_building", addition: "addition", renovation: "renovation", site: "site" };
const ORDER = ["building", "addition", "renovation", "site"];
export const DERIVED = ["work_kinds", "new_homes_total"];

export function derived(items: Current["items"], answers: Answer[]): Answer[] {
  const kinds = new Set(items.map((i) => i.kind));
  const work = ORDER.filter((k) => kinds.has(k)).map((k) => WORK_KIND[k]);
  let homes = 0;
  for (const i of items) {
    if (i.kind !== "building") continue;
    const v = answers.find((a) => a.field_id === "dwelling_units" && a.item_id === i.id)?.value;
    if (typeof v === "number") homes += v;
  }
  return [{ field_id: "work_kinds", item_id: null, value: work }, { field_id: "new_homes_total", item_id: null, value: homes }];
}

// The answers with the worked-out ones brought up to date.
export const withDerived = (items: Current["items"], answers: Answer[]): Answer[] => {
  const typed = answers.filter((a) => !(a.item_id === null && DERIVED.includes(a.field_id)));
  return [...typed, ...derived(items, typed)];
};
