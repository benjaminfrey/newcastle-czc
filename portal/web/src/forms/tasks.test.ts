import { describe, expect, it } from "vitest";
import type { FormDef, FormField, FormSection } from "../applications";
import type { Current } from "./applicability";
import { stepModels } from "./steps";
import { canSend, cardsOf, firstCopySource, itemSummary, progressOf, TASK_HINTS, TASK_ICONS, taskStatus } from "./tasks";

const q = (id: string, extra: Partial<FormField> = {}): FormField => ({
  id, official_label: id, source: "question", from: null, may_correct: false, label: `${id}?`, help: null, why: null,
  type: "number", unit: null, min: null, max: null, required: true, allow_unknown: false, show_if: null, options: [],
  step: null, screen: null, ask_first: 0, control: null, step_size: null, default: null, autocomplete: null, ...extra,
});
const opts = (...v: string[]) => v.map((x) => ({ value: x, label: x, official: x }));
const sec = (id: string, step: string, fields: FormField[], extra: Partial<FormSection> = {}): FormSection =>
  ({ id, official_title: id, chapter: id, show_if: null, repeat: null, step, screens: [],
     fields: fields.map((f) => ({ ...f, step: f.step ?? step })), ...extra });
const BUILDING = { kind: "building", add_label: "Add a building", min: 1, max: 20 };

// Built like the real Small Project Plan's building (task-list brief §3): eight cards, two of them
// gathered across sections ("about": the name from one section, the homes from another).
const FORM: FormDef = {
  key: "small_project_plan", version: 1, ruleset_key: "adopted-v1.0", official_title: "Small Project Plan",
  steps: [{ id: "about_you", title: "About you" }, { id: "the_work", title: "The work" }, { id: "buildings", title: "Buildings" }],
  sections: [
    sec("applicant", "about_you", [q("applicant_name", { type: "text", screen: "contact" }), q("applicant_phone", { type: "text", screen: "contact" }),
                                   q("applicant_is_owner", { type: "yesno", control: "switch" })], { screens: [{ id: "contact", layout: null }] }),
    sec("owner", "about_you", [q("owner_name", { type: "text" })], { show_if: { eq: ["answers.applicant_is_owner", false] } }),
    sec("project", "the_work", [q("work_kinds", { type: "multichoice", control: "chips", options: opts("new_building", "site") }),
                                q("project_description", { type: "longtext" })]),
    sec("building", "buildings", [q("building_name", { type: "text", required: false, screen: "about" }),
                                  q("renovation_only", { type: "yesno", control: "switch", ask_first: 2, default: false })],
        { repeat: BUILDING, screens: [{ id: "about", layout: null }] }),
    sec("building_location", "buildings",
        ["setback_front", "setback_side_1", "setback_side_2", "setback_rear"].map((id) => q(id, { screen: "setbacks" })),
        { repeat: BUILDING, screens: [{ id: "setbacks", layout: "lot-diagram" }] }),
    sec("building_details", "buildings", [
      q("building_class", { type: "choice", control: "building-type", ask_first: 1, options: opts("residential", "residential_accessory") }),
      q("dwelling_units", { control: "stepper", screen: "about", required: false })], { repeat: BUILDING }),
    sec("building_mass", "buildings", [
      q("mass_width", { screen: "size" }), q("mass_depth", { screen: "size" }), q("stories", { screen: "size", control: "stepper" }),
      q("floor_area", { screen: "size" }),
      q("roof_style", { type: "choice", control: "tiles", screen: "roof", options: opts("gable", "flat") }),
      q("roof_slope", { type: "choice", control: "picker", screen: "roof", options: opts("flat", "8_12") }),
      q("exterior_finish", { type: "multichoice", control: "chips", screen: "outside", options: opts("clapboard", "other") })],
      { repeat: BUILDING, screens: [{ id: "size", layout: null }, { id: "roof", layout: null }, { id: "outside", layout: null }] }),
    sec("building_windows", "buildings", [
      q("front_facing", { type: "choice", control: "tiles", screen: "walls", options: opts("north", "east", "south", "west") }),
      ...["north", "east", "south", "west"].map((w) => q(`windows_${w}`, { control: "slider", screen: "walls" }))],
      { repeat: BUILDING, screens: [{ id: "walls", layout: "compass" }] }),
  ],
};
const B1 = { id: "b1", kind: "building", position: 0 };
const B2 = { id: "b2", kind: "building", position: 1 };
const cur = (answers: Current["answers"] = [], items: Current["items"] = [B1]): Current =>
  ({ answers, items, property: {}, account: {} });
const a = (field_id: string, value: unknown, item_id: string | null = null) => ({ field_id, item_id, value });
const step = (c: Current, id: string) => stepModels(FORM, c).find((m) => m.id === id)!;

// Every required answer for one building.
const finished = (item: string) => [
  a("building_class", "residential", item), a("renovation_only", false, item),
  ...["setback_front", "setback_side_1", "setback_side_2", "setback_rear"].map((f) => a(f, 30, item)),
  a("mass_width", 28, item), a("mass_depth", 40, item), a("stories", 2, item), a("floor_area", 2240, item),
  a("roof_style", "gable", item), a("roof_slope", "8_12", item), a("exterior_finish", ["clapboard"], item),
  a("front_facing", "north", item), ...["north", "east", "south", "west"].map((w) => a(`windows_${w}`, 20, item)),
];

describe("cards", () => {
  it("a building is eight cards, type first, then renovation, then the cards gathered across sections", () => {
    const c = cur();
    expect(cardsOf(FORM, c, step(c, "buildings"), "b1").map((s) => s.id)).toEqual(
      ["building_class", "renovation_only", "building_name", "setback_front", "mass_width", "roof_style", "exterior_finish", "front_facing"]);
    const about = cardsOf(FORM, c, step(c, "buildings"), "b1")[2];
    expect(about.rows.map((r) => r.field.id)).toEqual(["building_name", "dwelling_units"]);
    expect(about.kind).toBe("set");
    expect(cardsOf(FORM, c, step(c, "buildings"), "b1")[7]).toMatchObject({ kind: "walls" });
  });

  it("a building's cards are its own, with no loop question", () => {
    const c = cur([], [B1, B2]);
    const cards = cardsOf(FORM, c, step(c, "buildings"), "b2");
    expect(cards.every((s) => s.itemId === "b2")).toBe(true);
    expect(cards.some((s) => s.id.startsWith("another:") || s.id.startsWith("any:"))).toBe(false);
  });

  it("a fields task's cards: a set gathers its questions", () => {
    const c = cur([a("applicant_is_owner", true)]);
    expect(cardsOf(FORM, c, step(c, "about_you")).map((s) => s.id)).toEqual(["applicant_name", "applicant_is_owner"]);
  });
});

describe("task status", () => {
  it("Not started, then n of m, then Done once visited with nothing missing", () => {
    const fresh = cur();
    expect(taskStatus(FORM, fresh, step(fresh, "the_work"), new Set())).toEqual({ kind: "todo" });
    const half = cur([a("work_kinds", ["new_building"])]);
    expect(taskStatus(FORM, half, step(half, "the_work"), new Set())).toEqual({ kind: "progress", answered: 1, total: 2 });
    const all = cur([a("work_kinds", ["new_building"]), a("project_description", "A house")]);
    expect(taskStatus(FORM, all, step(all, "the_work"), new Set(["the_work"]))).toEqual({ kind: "done" });
    expect(taskStatus(FORM, all, step(all, "the_work"), new Set())).toEqual({ kind: "progress", answered: 2, total: 2 });
  });

  it("a form's default alone isn't a start", () => {
    const c = cur([a("renovation_only", false, "b1")]);
    expect(taskStatus(FORM, c, step(c, "buildings"), new Set())).toEqual({ kind: "todo" });
  });

  it("Check and send opens when every task that applies is done", () => {
    const c = cur([a("applicant_name", "Ada"), a("applicant_phone", "207"), a("applicant_is_owner", true),
                   a("work_kinds", ["site"]), a("project_description", "Grading"), ...finished("b1")]);
    const models = stepModels(FORM, c);
    const visited = new Set(["about_you", "the_work", "buildings"]);
    expect(canSend(models.map((m) => taskStatus(FORM, c, m, visited)))).toBe(true);
    expect(canSend(models.map((m) => taskStatus(FORM, c, m, new Set(["about_you"]))))).toBe(false);
  });

  it("a task that stops applying doesn't hold up sending", () => {
    // Buildings hidden (as when the work is site-only): it isn't among the tasks at all.
    const site: FormDef = { ...FORM, sections: FORM.sections.map((s) => s.repeat ? { ...s, show_if: { eq: ["answers.work_kinds", "never"] } } : s) };
    const c = cur([a("applicant_name", "Ada"), a("applicant_phone", "207"), a("applicant_is_owner", true),
                   a("work_kinds", ["site"]), a("project_description", "Grading")]);
    const models = stepModels(site, c);
    expect(models.map((m) => m.id)).not.toContain("buildings");
    expect(canSend(models.map((m) => taskStatus(site, c, m, new Set(["about_you", "the_work"]))))).toBe(true);
  });
});

describe("progress", () => {
  it("counts the cards, and never fewer than are already answered", () => {
    const c = cur();
    const cards = cardsOf(FORM, c, step(c, "buildings"), "b1");
    expect(progressOf(cards, cards[2], 0)).toEqual({ count: 8, at: 2 });
    expect(progressOf(cards.slice(0, 5), cards[2], 6)).toEqual({ count: 6, at: 2 });
  });
});

describe("items", () => {
  it("a finished building's summary", () => {
    const c = cur(finished("b1"));
    expect(itemSummary(FORM, c, "b1")).toBe("28 × 40 ft · 2 floors · 2,240 sq ft · front faces north");
  });

  it("an unfinished building says how many answers are left", () => {
    const c = cur(finished("b1").filter((x) => !["mass_width", "mass_depth", "stories"].includes(x.field_id)));
    expect(itemSummary(FORM, c, "b1")).toBe("3 answers to go");
    const one = cur(finished("b1").filter((x) => x.field_id !== "stories"));
    expect(itemSummary(FORM, one, "b1")).toBe("1 answer to go");
  });

  it("copies from the first finished building, by number", () => {
    expect(firstCopySource(FORM, cur([], [B1, B2]), "building")).toBeNull();
    expect(firstCopySource(FORM, cur(finished("b2"), [B1, B2]), "building")).toEqual({ id: "b2", label: "Building 2" });
    expect(firstCopySource(FORM, cur([...finished("b1"), a("building_name", "Garage", "b1")], [B1, B2]), "building"))
      .toEqual({ id: "b1", label: "Building 1" });
  });
});

describe("the task list's words", () => {
  it("every task has an icon, and the brief's hints", () => {
    for (const id of ["your_lot", "about_you", "the_work", "buildings", "additions", "driveway", "meets_road", "safety",
                      "state_permit", "uses_today", "your_plan", "photos", "review"]) expect(TASK_ICONS[id], id).toBeTruthy();
    expect(TASK_HINTS.your_lot).toBe("Size, frontage and what is there now");
    expect(TASK_HINTS.the_work).toBe("What you are building, and a sketch");
    expect(TASK_HINTS.buildings).toBe("One short set of questions for each");
  });
});

describe("asking order outside a building", () => {
  it("ranked questions lead a task: the owner's card follows its question, before \"Is someone helping?\"", () => {
    const form: FormDef = { ...FORM, sections: [
      sec("applicant", "about_you", [q("applicant_name", { type: "text", ask_first: 1 }), q("applicant_is_owner", { type: "yesno", ask_first: 2 }),
                                     q("has_agent", { type: "yesno" })]),
      sec("owner", "about_you", [q("owner_name", { type: "text", ask_first: 3 })], { show_if: { eq: ["answers.applicant_is_owner", false] } }),
      ...FORM.sections.filter((s) => s.step !== "about_you")] };
    const c = cur([a("applicant_is_owner", false)]);
    expect(cardsOf(form, c, stepModels(form, c).find((m) => m.id === "about_you")!).map((s) => s.id))
      .toEqual(["applicant_name", "applicant_is_owner", "owner_name", "has_agent"]);
  });
});
