import { describe, expect, it } from "vitest";
import type { FormDef } from "../applications";
import type { Current } from "./applicability";
import fixtures from "./form-fixtures.json";
import { itemLabel, REVIEW_STEP, START_STEPS, statusOf, stepModels } from "./steps";

const form = fixtures.form as unknown as FormDef;
for (const s of form.sections) {
  s.show_if ??= null;
  s.repeat ??= null;
  s.pages ??= [];
  for (const f of s.fields) {
    f.may_correct ??= false; f.show_if ??= null; f.required ??= false; f.allow_unknown ??= false;
    f.options ??= []; f.from ??= null; f.step ??= s.step; f.page ??= null; f.control ??= null; f.default ??= null;
  }
}
const PROP = { map_lot: "004-036", acres: 2.1, districts: [], streets: [], on_state_highway: false };
const cur = (answers: Current["answers"] = [], items: Current["items"] = []): Current =>
  ({ answers, items, property: PROP, account: {} });
const B1 = { id: "x1", kind: "building", position: 0 };

describe("steps model", () => {
  it("the shared steps are fixed", () => {
    expect(START_STEPS.map((s) => s.title)).toEqual(["Your project", "Your property", "What you'll need"]);
    expect(REVIEW_STEP.title).toBe("Review and sign");
  });

  it("steps follow the form's order", () => {
    expect(stepModels(form, cur([], [B1])).map((s) => s.id)).toEqual(["lot", "you", "buildings"]);
  });

  it("a step with nothing applicable is left out", () => {
    // the owner group is the whole "About you" step's content besides is_owner, which is asked there too
    const only = { ...form, sections: form.sections.filter((s) => s.id !== "owner") };
    const noYou = { ...only, sections: only.sections.map((s) => ({ ...s, fields: s.fields.filter((f) => f.id !== "is_owner") })) };
    expect(stepModels(noYou, cur([], [B1])).map((s) => s.id)).toEqual(["lot", "buildings"]);
  });

  it("hub steps list items with their status", () => {
    const steps = stepModels(form, cur([{ field_id: "stories", item_id: "x1", value: 1 }], [B1, { id: "x2", kind: "building", position: 1 }]));
    const hub = steps.find((s) => s.id === "buildings")!;
    expect(hub.kind).toBe("hub");
    expect(hub.hub!.items.map((i) => [i.label, i.status])).toEqual([["Building 1", "done"], ["Building 2", "todo"]]);
  });

  it("step_status_needs_a_visit", () => {
    // "About you" holds only a defaulted switch and the hidden owner group: nothing is missing,
    // but the applicant hasn't seen it, so it isn't done.
    const answers = [{ field_id: "is_owner", item_id: null, value: true }];
    const you = stepModels(form, cur(answers, [B1])).find((s) => s.id === "you")!;
    expect(statusOf(you, cur(answers, [B1]), new Set()).status).toBe("todo");
    expect(statusOf(you, cur(answers, [B1]), new Set(["you"])).status).toBe("done");
  });

  it("a changed default counts as started", () => {
    const answers = [{ field_id: "is_owner", item_id: null, value: false }];
    const you = stepModels(form, cur(answers, [B1])).find((s) => s.id === "you")!;
    expect(statusOf(you, cur(answers, [B1]), new Set()).status).toBe("started");
    expect(statusOf(you, cur(answers, [B1]), new Set(["you"])).status).toBe("started"); // owner's name missing
  });

  it("unknowns are counted", () => {
    // Stories unknown keeps the second-floor question asked (unknown shows), so answer it too.
    const answers = [{ field_id: "stories", item_id: "x1", value: { unknown: true } },
                     { field_id: "height_2", item_id: "x1", value: { unknown: true } }];
    const hub = stepModels(form, cur(answers, [B1])).find((s) => s.id === "buildings")!;
    expect(statusOf(hub, cur(answers, [B1]), new Set(["buildings"]))).toEqual({ status: "done", unknowns: 2 });
  });

  it("items are labelled by type when unnamed", () => {
    expect(itemLabel(form, cur([], [B1]), "x1")).toBe("Building 1");
  });

  it("an item's kind is added in its own words, and not when it only repeats the noun", () => {
    const kinds = { ...form, sections: [{ ...form.sections[0], id: "component", repeat: { kind: "component" }, fields: [{
      ...form.sections[0].fields[0], id: "component_kind", type: "choice", show_if: null,
      options: [{ value: "addition", label: "An addition", official: "Addition" }, { value: "deck", label: "A deck", official: "Deck" }],
    }] }] } as unknown as FormDef;
    const C1 = { id: "c1", kind: "component", position: 0 };
    const kind = (v: string) => cur([{ field_id: "component_kind", item_id: "c1", value: v }], [C1]);
    expect(itemLabel(kinds, kind("addition"), "c1")).toBe("Addition 1");
    expect(itemLabel(kinds, kind("deck"), "c1")).toBe("Addition 1: Deck");
  });
});
