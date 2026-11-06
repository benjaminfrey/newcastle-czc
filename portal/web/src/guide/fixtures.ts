import type { Guide, Shown } from "./api";
import { shown } from "./turns/fixtures";

export const LOT_FACTS = { map_lot: "012-034", districts: [{ code: "D1", name: "Rural" }],
  acres: { value: 2, approximate: true }, frontage_ft: { value: 200, approximate: true } };

const yesNo = [{ id: "yes", label: "Yes", hint: null }, { id: "not_right", label: "That's not right", hint: null },
               { id: "unsure", label: "I'm not sure yet", hint: null }];
export const LOT: Shown = shown({ turn_id: "lot", kind: "lot", ask: "Is this your lot?", answers: yesNo,
  step: { n: 1, of: 4, label: "Your lot" }, facts_shown: LOT_FACTS });
export const SIDE: Shown = shown({ turn_id: "setback_side_1", kind: "number", ask: "How far from the side line?",
  step: { n: 4, of: 4, label: "Where it sits" }, input: { unit: "ft", min: 0, max: 50000 }, answers: [] });
export const FLOOR: Shown = shown({ turn_id: "floor_area", kind: "number", ask: "What is the floor area?",
  step: { n: 3, of: 4, label: "The building" }, input: { unit: "sq ft", min: 1, max: 1000000 }, answers: [] });

export const guide = (over: Partial<Guide> = {}): Guide => ({
  revision: 4, opening: "new_house", current: FLOOR, history: [{ shown: LOT, value: "yes" }], ending: null,
  step: FLOOR.step, unsure: [], checks: {}, notes: [], reopened: [], drafts: ["turns.yaml: lot"], ...over,
});
