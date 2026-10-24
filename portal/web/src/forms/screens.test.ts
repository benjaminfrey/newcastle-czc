import { describe, expect, it } from "vitest";
import type { FormDef, FormField, FormSection } from "../applications";
import type { Current } from "./applicability";
import { groupOf, screenAfter, screensOf } from "./screens";
import { stepModels } from "./steps";

const q = (id: string, extra: Partial<FormField> = {}): FormField => ({
  id, official_label: id, source: "question", from: null, may_correct: false, label: `${id}?`, help: null, why: null,
  type: "text", unit: null, min: null, max: null, required: true, allow_unknown: false, show_if: null, options: [],
  step: null, screen: null, ask_first: false, control: null, step_size: null, default: null, autocomplete: null, ...extra,
});
const opts = (...v: string[]) => v.map((x) => ({ value: x, label: x, official: x }));
const sec = (id: string, step: string, fields: FormField[], extra: Partial<FormSection> = {}): FormSection =>
  ({ id, official_title: id, chapter: id, show_if: null, repeat: null, step, screens: [],
     fields: fields.map((f) => ({ ...f, step: f.step ?? step })), ...extra });
const BUILDING = { kind: "building", add_label: "Add a building", min: 1, max: 20 };
const COMPONENT = { kind: "component", add_label: "Add an addition", min: 0, max: 30 };

const FORM: FormDef = {
  key: "small_project_plan", version: 1, ruleset_key: "adopted-v1.0", official_title: "Small Project Plan",
  steps: [{ id: "lot", title: "Your lot" }, { id: "you", title: "About you" }, { id: "work", title: "The work" },
          { id: "buildings", title: "Buildings" }, { id: "additions", title: "Additions" }],
  sections: [
    sec("location", "lot", [
      q("street_address", { source: "property", from: "location", may_correct: true }),
      q("deed_book", { screen: "deed", allow_unknown: true }), q("deed_page", { screen: "deed", allow_unknown: true })],
      { screens: [{ id: "deed", layout: null }] }),
    sec("site", "lot", [q("lot_area", { source: "property", from: "acres", may_correct: true, type: "number", unit: "acres" }),
                        q("lot_width", { type: "number", unit: "ft", allow_unknown: true })]),
    sec("applicant", "you", [q("applicant_name"), q("applicant_phone"), q("applicant_address"),
                             q("applicant_is_owner", { type: "yesno", control: "switch" }), q("has_agent", { type: "yesno", control: "switch" })]),
    sec("owner", "you", [q("owner_name"), q("owner_email"), q("owner_phone"), q("owner_address")],
        { show_if: { eq: ["answers.applicant_is_owner", false] } }),
    sec("project", "work", [q("work_kinds", { type: "multichoice", control: "chips", options: opts("new_building", "site") })]),
    sec("building", "buildings", [q("building_name", { required: false }), q("renovation_only", { type: "yesno", control: "switch" })],
        { repeat: BUILDING }),
    sec("building_location", "buildings",
        ["setback_front", "setback_side_1", "setback_side_2", "setback_rear"].map((id) => q(id, { type: "number", screen: "setbacks" })),
        { repeat: BUILDING, screens: [{ id: "setbacks", layout: "lot-diagram" }] }),
    sec("building_details", "buildings", [
      q("building_class", { type: "choice", control: "building-type", ask_first: true, options: opts("home", "shed") })],
      { repeat: BUILDING }),
    sec("building_mass", "buildings", [q("roof_slope", { type: "choice", control: "picker", options: opts("flat", "8_12") })],
        { repeat: BUILDING }),
    sec("building_windows", "buildings", [
      q("front_facing", { type: "choice", control: "tiles", options: opts("north", "east", "south", "west") }),
      ...["north", "east", "south", "west"].map((w) => q(`windows_${w}`, { type: "number", control: "slider", screen: "walls" }))],
      { repeat: BUILDING, screens: [{ id: "walls", layout: "compass" }] }),
    sec("component", "additions", [q("component_kind", { type: "choice", control: "tiles", options: opts("addition", "deck") })],
        { repeat: COMPONENT }),
  ],
};
const B1 = { id: "b1", kind: "building", position: 0 };
const B2 = { id: "b2", kind: "building", position: 1 };
const cur = (answers: Current["answers"] = [], items: Current["items"] = [B1], property: Record<string, unknown> = {}): Current =>
  ({ answers, items, property: { location: "461 SHEEPSCOT RD", acres: 2.73, ...property }, account: {} });
const a = (field_id: string, value: unknown, item_id: string | null = null) => ({ field_id, item_id, value });
const screens = (c: Current, step: string) => screensOf(FORM, c, stepModels(FORM, c).find((m) => m.id === step)!);

describe("screens", () => {
  it("one screen per question", () => {
    expect(screens(cur([a("applicant_is_owner", true)]), "you").map((s) => s.id))
      .toEqual(["applicant_name", "applicant_phone", "applicant_address", "applicant_is_owner", "has_agent"]);
  });

  it("owner questions slot in after the owner question", () => {
    expect(screens(cur([a("applicant_is_owner", false)]), "you").map((s) => s.id)).toEqual(
      ["applicant_name", "applicant_phone", "applicant_address", "applicant_is_owner", "has_agent",
       "owner_name", "owner_email", "owner_phone", "owner_address"]);
  });

  it("a screen group is one screen", () => {
    const lot = screens(cur(), "lot");
    const deed = lot.find((s) => s.id === "deed_book")!;
    expect(deed.kind).toBe("set");
    expect(deed.rows.map((r) => r.field.id)).toEqual(["deed_book", "deed_page"]);
    const setbacks = screens(cur(), "buildings").find((s) => s.id === "setback_front")!;
    expect(setbacks.kind).toBe("setbacks");
    expect(setbacks.rows).toHaveLength(4);
    expect(screens(cur(), "buildings").find((s) => s.id === "windows_north")!.kind).toBe("walls");
  });

  it("single choices move on at a tap; the rest wait for Continue", () => {
    const you = screens(cur(), "you");
    expect(you.find((s) => s.id === "applicant_is_owner")!).toMatchObject({ kind: "choice", auto: true });
    expect(screens(cur(), "work")[0]).toMatchObject({ kind: "multi", auto: false });
    const b = screens(cur(), "buildings");
    expect(b.find((s) => s.id === "roof_slope")!).toMatchObject({ kind: "picker", auto: false });
    expect(b.find((s) => s.id === "front_facing")!).toMatchObject({ kind: "facing", auto: true });
  });

  it("a value from the Town's map asks Is this right?", () => {
    expect(screens(cur(), "lot").find((s) => s.id === "lot_area")!.kind).toBe("confirm");
    expect(screens(cur([], [B1], { acres: null }), "lot").find((s) => s.id === "lot_area")!.kind).toBe("number");
  });

  it("an item's ask-first questions come first, and optional and unknown are carried", () => {
    const b = screens(cur(), "buildings").filter((s) => s.itemId === "b1");
    expect(b[0].id).toBe("building_class");
    expect(b.find((s) => s.id === "building_name")!.optional).toBe(true);
    expect(screens(cur(), "lot").find((s) => s.id === "deed_book")!.unknown).toBe(true);
  });

  it("buildings loop: each building's screens, then Is there another?", () => {
    const b = screens(cur([], [B1, B2]), "buildings");
    const ids = b.map((s) => `${s.itemId}:${s.id}`);
    expect(ids.indexOf("b2:building_class")).toBeGreaterThan(ids.indexOf("b1:windows_north"));
    const last = b[b.length - 1];
    expect(last).toMatchObject({ id: "another:building", kind: "another", auto: true });
    expect(groupOf(b, last).every((s) => s.itemId === "b2")).toBe(true);
    expect(groupOf(b, last)).toContain(last);
  });

  it("an empty additions step asks first", () => {
    const add = screens(cur(), "additions");
    expect(add.map((s) => [s.id, s.kind])).toEqual([["any:component", "any"]]);
    const one = screens(cur([], [B1, { id: "c1", kind: "component", position: 0 }]), "additions");
    expect(one.map((s) => s.id)).toEqual(["component_kind", "another:component"]);
  });

  it("screenAfter crosses steps and ends at review", () => {
    const c = cur([a("applicant_is_owner", true)]);
    const models = stepModels(FORM, c);
    expect(screenAfter(FORM, c, models, { step: "you", screen: "has_agent" })).toEqual({ step: "work", screen: "work_kinds" });
    expect(screenAfter(FORM, c, models, { step: "additions", screen: "any:component" })).toEqual({ review: true });
    expect(screenAfter(FORM, c, models, { step: "lot", screen: "street_address" })).toEqual({ step: "lot", screen: "deed_book" });
  });

  it("screenAfter skips screens that stopped applying", () => {
    // On the owner's name when the owner question was just turned to Yes: the next screen still asked.
    const c = cur([a("applicant_is_owner", true)]);
    expect(screenAfter(FORM, c, stepModels(FORM, c), { step: "you", screen: "owner_name" })).toEqual({ step: "work", screen: "work_kinds" });
  });
});
