import { describe, expect, it } from "vitest";
import type { FormDef } from "../applications";
import type { Current } from "./applicability";
import fixtures from "./form-fixtures.json";
import { screens } from "./wizard";

const form = fixtures.form as unknown as FormDef;
for (const s of form.sections) {
  s.show_if ??= null;
  s.repeat ??= null;
  for (const f of s.fields) {
    f.may_correct ??= false; f.show_if ??= null; f.required ??= false; f.allow_unknown ??= false; f.options ??= []; f.from ??= null;
  }
}
const PROP = { map_lot: "004-036", acres: 2, districts: [], streets: [], on_state_highway: false };
const cur = (answers: Current["answers"], items: Current["items"] = [], property: Record<string, unknown> = PROP): Current =>
  ({ answers, items, property, account: {} });

describe("wizard screens", () => {
  it("one screen per applicable question", () => {
    const ss = screens(form, cur([{ field_id: "is_owner", item_id: null, value: true }], [{ id: "x1", kind: "building", position: 0 }]));
    expect(ss.map((s) => s.key)).toEqual(["site.lot_area", "site.frontage", "site.is_owner", "b.stories.x1", "b2.height_2.x1", "add.building"]);
  });

  it("owner questions appear only when not the owner", () => {
    const owner = screens(form, cur([{ field_id: "is_owner", item_id: null, value: true }]));
    expect(owner.some((s) => s.key === "owner.owner_name")).toBe(false);
    const notOwner = screens(form, cur([{ field_id: "is_owner", item_id: null, value: false }]));
    expect(notOwner.some((s) => s.key === "owner.owner_name")).toBe(true);
  });

  it("repeat offers to add another, with each item's questions together", () => {
    const items = [{ id: "x1", kind: "building", position: 0 }, { id: "x2", kind: "building", position: 1 }];
    const ss = screens(form, cur([{ field_id: "stories", item_id: "x1", value: 2 }], items));
    expect(ss.map((s) => s.key).slice(-5)).toEqual(["b.stories.x1", "b2.height_2.x1", "b.stories.x2", "b2.height_2.x2", "add.building"]);
    const first = ss.find((s) => s.key === "b.stories.x2");
    expect(first && first.kind === "question" && first.itemLabel).toBe("Building 2");
  });

  it("uses the shared shown rule: an unknown road asks the MaineDOT question", () => {
    const ss = screens(form, cur([], [], { ...PROP, on_state_highway: null }));
    expect(ss.some((s) => s.key === "site.highway")).toBe(true);
    expect(screens(form, cur([])).some((s) => s.key === "site.highway")).toBe(false);
  });

  it("stops offering more once the limit is reached", () => {
    const items = Array.from({ length: 5 }, (_, i) => ({ id: `x${i}`, kind: "building", position: i }));
    expect(screens(form, cur([], items)).some((s) => s.kind === "add")).toBe(false);
  });
});
