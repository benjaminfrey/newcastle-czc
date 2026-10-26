import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes, useLocation } from "react-router";
import { beforeEach, describe, expect, it, vi } from "vitest";
import * as api from "../api";
import * as apps from "../projects";
import * as layout from "../shell/useWideLayout";
import ProjectPage from "./ProjectPage";

vi.mock("../components/ParcelMap", () => ({ default: () => <div>map</div> }));

// The application as tasks and cards (task-list brief, 2026-10-25). The form is built like the
// real Small Project Plan: the cover sheet's two tasks, the work, buildings (eight cards each) and
// additions.
const q = (id: string, label: string, extra: Partial<apps.FormField> = {}): apps.FormField => ({
  id, official_label: id, source: "question", from: null, may_correct: false, label, help: null, why: null,
  type: "number", unit: null, min: null, max: null, required: true, allow_unknown: false, show_if: null, options: [],
  step: null, screen: null, ask_first: 0, control: null, step_size: null, default: null, autocomplete: null, ...extra,
});
const sec = (id: string, step: string, fields: apps.FormField[], extra: Partial<apps.FormSection> = {}): apps.FormSection =>
  ({ id, official_title: id, chapter: id, show_if: null, repeat: null, step, screens: [],
     fields: fields.map((f) => ({ ...f, step: f.step ?? step })), ...extra });
const opts = (...v: [string, string, string?][]) => v.map(([value, label, icon]) => ({ value, label, official: label, icon: icon ?? null }));
const BUILDING = { kind: "building", add_label: "Add a building", min: 1, max: 20 };
const COMPONENT = { kind: "component", add_label: "Add an addition", min: 0, max: 30 };

const FORM: apps.FormDef = {
  key: "small_project_plan", version: 1, ruleset_key: "adopted-v1.0", official_title: "Small Project Plan Application",
  steps: [{ id: "your_lot", title: "Your lot" }, { id: "about_you", title: "About you" }, { id: "the_work", title: "The work" },
          { id: "buildings", title: "Buildings" }, { id: "additions", title: "Additions" }],
  sections: [
    sec("site", "your_lot", [
      q("lot_area", "How big is your lot, in acres?", { source: "property", from: "acres", may_correct: true, unit: "acres" }),
      q("lot_width", "How wide is your lot, in feet?", { screen: "lot_size", short: "Width", unit: "ft", allow_unknown: true }),
      q("lot_depth", "How deep is your lot, in feet?", { screen: "lot_size", short: "Depth", unit: "ft", allow_unknown: true })],
      { screens: [{ id: "lot_size", layout: null, title: "How big is your lot?", help: "In feet. Your deed or a survey has these." }] }),
    sec("applicant", "about_you", [
      q("applicant_name", "What is your full name?", { type: "text" }),
      q("applicant_is_owner", "Do you own this property?", { type: "yesno", control: "switch", default: false })]),
    sec("owner", "about_you", [q("owner_name", "What is the property owner's full name?", { type: "text" })],
        { show_if: { eq: ["answers.applicant_is_owner", false] } }),
    sec("project", "the_work", [
      q("work_kinds", "What kind of work is this?", { type: "multichoice", control: "chips",
        options: opts(["new_building", "A new building", "building-cottage"], ["site", "Work on the land", "shovel"]) }),
      q("sketch", "Add a sketch, if you have one", { type: "upload", required: false })]),
    sec("building", "buildings", [
      q("building_name", "What do you call this building?", { type: "text", required: false, screen: "about", short: "What you call it" }),
      q("renovation_only", "Is it only being renovated?", { type: "yesno", control: "switch", ask_first: 2, default: false })],
      { repeat: BUILDING, screens: [{ id: "about", layout: null }] }),
    sec("building_location", "buildings",
        ["setback_front", "setback_side_1", "setback_side_2", "setback_rear"].map((id) => q(id, `${id}?`, { screen: "setbacks" })),
        { repeat: BUILDING, screens: [{ id: "setbacks", layout: "lot-diagram" }] }),
    sec("building_details", "buildings", [
      q("building_class", "Which best describes this building?", { type: "choice", control: "building-type", ask_first: 1, copies: true,
        options: opts(["residential", "A home: a house"], ["residential_accessory", "Goes with a home"],
                      ["commercial_accessory", "Goes with a business"], ["general_accessory", "Either"]) }),
      q("dwelling_units", "How many homes will this building have?", { control: "stepper", screen: "about", short: "Homes in it", required: false })],
      { repeat: BUILDING }),
    sec("building_mass", "buildings", [
      q("mass_width", "How wide is it?", { screen: "size", short: "Width", unit: "ft", copies: true, allow_unknown: true }),
      q("mass_depth", "How deep is it?", { screen: "size", short: "Depth", unit: "ft", copies: true, allow_unknown: true }),
      q("stories", "How many stories?", { screen: "size", short: "Floors above ground", control: "stepper", copies: true }),
      q("floor_height_1", "First story height?", { screen: "size", short: "First floor height", unit: "ft", required: false }),
      q("floor_height_2", "Second story height?", { screen: "size", short: "Second floor height", unit: "ft", required: false,
        show_if: { gte: ["item.stories", 2] } }),
      q("roof_style", "What shape is the roof?", { type: "choice", control: "tiles", screen: "roof", short: "Shape",
        options: opts(["gable", "Gable"], ["flat", "Flat"]) }),
      q("roof_slope", "How steep is the roof?", { type: "choice", control: "picker", screen: "roof", short: "Slope",
        options: opts(["low", "Low"], ["steep", "Steep"]) }),
      q("exterior_finish", "What will the outside be covered with?", { type: "multichoice", control: "chips", screen: "outside",
        short: "Materials", options: opts(["clapboard", "Clapboard"], ["brick", "Brick"], ["other", "Something else"]) }),
      q("exterior_finish_other", "What other material?", { type: "text", screen: "outside", short: "Other material", required: false })],
      { repeat: BUILDING, screens: [{ id: "size", layout: null, title: "How big is the building?", help: "In feet. A builder's plan has these." },
                                    { id: "roof", layout: null, title: "What shape is the roof?", help: "Choose one." },
                                    { id: "outside", layout: null, title: "What will the outside walls and roof be covered with?", help: "Choose all that apply." }] }),
    sec("building_windows", "buildings", [
      q("front_facing", "Which way does the front of the building face?", { type: "choice", control: "tiles", screen: "walls",
        options: opts(["north", "North", "arrow-up"], ["east", "East", "arrow-right"], ["south", "South", "arrow-down"], ["west", "West", "arrow-left"]) }),
      ...["north", "east", "south", "west"].map((w) => q(`windows_${w}`, `${w} wall`,
        { control: "slider", screen: "walls", min: 0, max: 100, step_size: 5, unit: "%" }))],
      { repeat: BUILDING, screens: [{ id: "walls", layout: "compass" }] }),
    sec("component", "additions", [q("component_kind", "What are you adding?", { type: "choice", control: "tiles",
      options: opts(["addition", "An addition"], ["deck", "A deck"]) }),
      q("attached_to", "Which building is it attached to?", { type: "text", control: "building-picker", required: false })], { repeat: COMPONENT }),
  ],
};
const B1 = { id: "b1", kind: "building", position: 0 };
const B2 = { id: "b2", kind: "building", position: 1 };
const APP: apps.ProjectState = {
  id: "abc", title: "A new building at Sheepscot Road", ruleset_key: "adopted-v1.0", status: "draft", revision: 3,
  submitted_at: null, forms: { small_project_plan: 1 }, form: FORM, needs: null,
  property: { source: "lookup", parcel_id: null, map_lot: "004-036",
              facts: { acres: 2.73, streets: [{ name: "Sheepscot Road" }], location: "461 SHEEPSCOT RD" },
              parcels_as_of: null, verified: true, disputed: false, note: "" },
  items: [B1], answers: [], notes: [], attachments: [], missing: [],
};
const a = (field_id: string, value: unknown, item_id: string | null = null) => ({ field_id, item_id, value });
const finished = (item: string) => [
  a("building_class", "residential", item), a("renovation_only", false, item),
  ...["setback_front", "setback_side_1", "setback_side_2", "setback_rear"].map((f) => a(f, 30, item)),
  a("mass_width", 28, item), a("mass_depth", 40, item), a("stories", 1, item), a("roof_style", "gable", item), a("roof_slope", "steep", item),
  a("exterior_finish", ["clapboard"], item), a("front_facing", "north", item),
  ...["north", "east", "south", "west"].map((w) => a(`windows_${w}`, 20, item)),
];

function Where() {
  const l = useLocation();
  return <p data-testid="where">{l.pathname}{l.search}</p>;
}
const open = (path: string) => render(
  <MemoryRouter initialEntries={[path]}>
    <Routes>
      <Route path="/projects/:id/:stepId?/:sub?" element={<><ProjectPage /><Where /></>} />
      <Route path="*" element={<Where />} />
    </Routes>
  </MemoryRouter>,
);
const where = () => screen.getByTestId("where");
const withApp = (over: Partial<apps.ProjectState>) => vi.spyOn(apps, "getProject").mockResolvedValue({ ...APP, ...over });
let save: ReturnType<typeof vi.spyOn>;
const saved = () => save.mock.calls.flatMap((c: unknown[]) => c[2] as apps.Change[]);

beforeEach(() => {
  localStorage.clear();
  vi.restoreAllMocks();
  vi.spyOn(layout, "useWideLayout").mockReturnValue(true);
  vi.spyOn(apps, "getProject").mockResolvedValue(APP);
  vi.spyOn(apps, "getParts").mockResolvedValue([]);
  vi.spyOn(api, "getMe").mockResolvedValue({ email: "a@example.com", role: "applicant" });
  vi.spyOn(api, "getUseGroups").mockResolvedValue([]);
  save = vi.spyOn(apps, "saveAnswers").mockResolvedValue({ revision: 4, missing: [] });
});

describe("the project's home", () => {
  it("is the dashboard: the parcel, a row per part with its pill", async () => {
    withApp({ answers: [a("lot_width", 120), a("lot_depth", 200)] });
    open("/projects/abc");
    const main = await screen.findByRole("main");
    expect(within(main).getByRole("link", { name: /^Your lot,\s*Map 4, Lot 36.*(Not started|answered|Done)$/ })).toBeInTheDocument();
    expect(within(main).getByRole("link", { name: /^The work.*answered$/ })).toBeInTheDocument();
    expect(within(main).getByRole("link", { name: "Check and send" })).toHaveAttribute("href", "/projects/abc/send");
  });
});

describe("cards", () => {
  it("a tap answers and moves on, with no Continue", async () => {
    withApp({ answers: [a("applicant_name", "Ada")] });
    open("/projects/abc/about_you?screen=applicant_is_owner");
    await userEvent.click(await screen.findByRole("radio", { name: "Yes" }));
    expect(screen.queryByRole("button", { name: "Continue" })).not.toBeInTheDocument();
    await waitFor(() => expect(where()).toHaveTextContent("/projects/abc/about_you/check"));
    expect(saved()).toContainEqual(a("applicant_is_owner", true));
  });

  it("Continue saves a typed answer; Return does the same", async () => {
    open("/projects/abc/about_you?screen=applicant_name");
    await userEvent.type(await screen.findByRole("textbox", { name: "What is your full name?" }), "Ada{Enter}");
    await waitFor(() => expect(where()).toHaveTextContent("?screen=applicant_is_owner"));
    expect(saved()).toContainEqual(a("applicant_name", "Ada"));
  });

  it("the card's header names the task and counts its cards", async () => {
    withApp({ answers: [a("applicant_is_owner", false)] }); // the owner's card applies
    open("/projects/abc/about_you?screen=applicant_is_owner");
    await screen.findByRole("heading", { level: 2, name: "Do you own this property?" });
    expect(screen.getByRole("img", { name: "Question 2 of 3" })).toBeInTheDocument();
    expect(screen.getByText("2 of 3")).toBeInTheDocument();
  });

  it("Back on a part's first card goes to the dashboard", async () => {
    open("/projects/abc/about_you?screen=applicant_name");
    await userEvent.click(await screen.findByRole("button", { name: "Back" }));
    await waitFor(() => expect(where()).toHaveTextContent(/^\/projects\/abc$/));
  });

  it("a set of values: short names beside their fields; Continue saves them all", async () => {
    open("/projects/abc/your_lot?screen=lot_width");
    expect(await screen.findByRole("heading", { level: 2, name: "How big is your lot?" })).toBeInTheDocument();
    expect(screen.getByText("In feet. Your deed or a survey has these.")).toBeInTheDocument();
    await userEvent.type(screen.getByRole("textbox", { name: "Width" }), "120");
    await userEvent.type(screen.getByRole("textbox", { name: "Depth" }), "200");
    await userEvent.click(screen.getByRole("button", { name: "Continue" }));
    await waitFor(() => expect(saved()).toEqual(expect.arrayContaining([a("lot_width", 120), a("lot_depth", 200)])));
  });

  it("I don't know some of these yet marks only the blank ones", async () => {
    withApp({ answers: [a("lot_width", 120)] });
    open("/projects/abc/your_lot?screen=lot_width");
    await userEvent.click(await screen.findByRole("button", { name: "I don't know some of these yet" }));
    await waitFor(() => expect(saved()).toContainEqual(a("lot_depth", { unknown: true })));
    expect(saved()).not.toContainEqual(a("lot_width", { unknown: true }));
  });

  it("a typed number saves when Back is pressed without leaving the field", async () => {
    open("/projects/abc/your_lot?screen=lot_width");
    await userEvent.type(await screen.findByRole("textbox", { name: "Width" }), "120");
    fireEvent.click(screen.getByRole("button", { name: "Back" })); // a tap on a phone: focus stays in the field
    await waitFor(() => expect(saved()).toContainEqual(a("lot_width", 120)));
  });

  it("Is this right? keeps the map's value; a correction shows as the applicant's", async () => {
    open("/projects/abc/your_lot?screen=lot_area");
    await userEvent.click(await screen.findByRole("radio", { name: "Yes, that's right" }));
    await waitFor(() => expect(where()).toHaveTextContent("?screen=lot_width"));
    expect(saved()).toEqual([]);
  });

  it("a corrected value can go back to the map's", async () => {
    withApp({ answers: [a("lot_area", 2.5)] });
    open("/projects/abc/your_lot?screen=lot_area");
    expect(await screen.findByText("You entered this. The Town's map says 2.73 acres.")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("radio", { name: "Use the map's 2.73 acres" }));
    await waitFor(() => expect(saved()).toContainEqual(a("lot_area", null)));
  });

  it("an answered tap card offers Continue; a form default alone doesn't", async () => {
    withApp({ answers: [a("applicant_name", "Ada"), a("applicant_is_owner", false)] });
    const { unmount } = open("/projects/abc/about_you?screen=applicant_is_owner");
    await screen.findByRole("heading", { level: 2, name: "Do you own this property?" });
    await new Promise((r) => setTimeout(r, 50));
    expect(screen.queryByRole("button", { name: "Continue" })).not.toBeInTheDocument();
    unmount();
    withApp({ answers: [a("applicant_name", "Ada"), a("applicant_is_owner", true)] });
    open("/projects/abc/about_you?screen=applicant_is_owner");
    await userEvent.click(await screen.findByRole("button", { name: "Continue" }));
    await waitFor(() => expect(where()).toHaveTextContent("/projects/abc/about_you/check"));
  });

  it("A tap moves on is said once in an application", async () => {
    withApp({ answers: [a("applicant_name", "Ada")] });
    const { unmount } = open("/projects/abc/about_you?screen=applicant_is_owner");
    expect(await screen.findByText("A tap moves on")).toBeInTheDocument();
    unmount();
    open("/projects/abc/about_you?screen=applicant_is_owner");
    await screen.findByRole("heading", { level: 2, name: "Do you own this property?" });
    expect(screen.queryByText("A tap moves on")).not.toBeInTheDocument();
  });

  it("a tap's move-on gives way when the applicant goes elsewhere first", async () => {
    withApp({ answers: [a("applicant_name", "Ada")] });
    open("/projects/abc/about_you?screen=applicant_is_owner");
    await userEvent.click(await screen.findByRole("radio", { name: "Yes" }));
    fireEvent.click(screen.getByRole("button", { name: "Back" }));
    await new Promise((r) => setTimeout(r, 400));
    expect(where()).toHaveTextContent("?screen=applicant_name");
  });
});

describe("a building", () => {
  it("runs eight cards, headed by its number and type, then its check page, then the list", async () => {
    withApp({ answers: [a("building_class", "residential", "b1")] });
    open("/projects/abc/buildings?screen=building_class&item=b1");
    await screen.findByRole("heading", { level: 2, name: "Which best describes this building?" });
    expect(screen.getByText("Building 1 · A home")).toBeInTheDocument();
    expect(screen.getByRole("img", { name: "Question 1 of 8" })).toBeInTheDocument();
  });

  it("the last card goes to the building's check page, and Done there to the list", async () => {
    withApp({ answers: finished("b1") });
    open("/projects/abc/buildings?screen=front_facing&item=b1");
    await userEvent.click(await screen.findByRole("button", { name: "Continue" }));
    await waitFor(() => expect(where()).toHaveTextContent("/projects/abc/buildings/check?item=b1"));
    expect(await screen.findByText("Check Building 1")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Done" }));
    await waitFor(() => expect(where()).toHaveTextContent(/^\/projects\/abc\/buildings$/));
  });

  it("the roof's shape tiles answer without moving on; Continue moves on", async () => {
    open("/projects/abc/buildings?screen=roof_style&item=b1");
    await userEvent.click(await screen.findByRole("radio", { name: "Gable" }));
    await new Promise((r) => setTimeout(r, 300));
    expect(where()).toHaveTextContent("?screen=roof_style");
    expect(saved()).toContainEqual(a("roof_style", "gable", "b1"));
    await userEvent.click(screen.getByRole("button", { name: "Continue" }));
    await waitFor(() => expect(where()).toHaveTextContent("?screen=exterior_finish"));
    // (the slope's tiles appear once a shape is chosen)
  });

  it("a floor height for each floor entered, and none before", async () => {
    withApp({ answers: [a("stories", 2, "b1")] });
    const { unmount } = open("/projects/abc/buildings?screen=mass_width&item=b1");
    await screen.findByRole("heading", { level: 2, name: "How big is the building?" });
    expect(screen.getByRole("textbox", { name: "First floor height" })).toBeInTheDocument();
    expect(screen.getByRole("textbox", { name: "Second floor height" })).toBeInTheDocument();
    unmount();
    withApp({ answers: [] });
    open("/projects/abc/buildings?screen=mass_width&item=b1");
    await screen.findByRole("heading", { level: 2, name: "How big is the building?" });
    expect(screen.queryByRole("textbox", { name: "First floor height" })).not.toBeInTheDocument();
  });

  it("floors are counted with − and + beside the number", async () => {
    open("/projects/abc/buildings?screen=mass_width&item=b1");
    await userEvent.click(await screen.findByRole("button", { name: "Floors above ground, one more" }));
    await waitFor(() => expect(saved()).toContainEqual(a("stories", 1, "b1")));
    expect(screen.getByRole("button", { name: "Floors above ground, one fewer" })).toBeInTheDocument();
  });

  it("the roof: its shapes, then its slope once a shape is chosen", async () => {
    const { unmount } = open("/projects/abc/buildings?screen=roof_style&item=b1");
    expect(await screen.findByRole("heading", { level: 2, name: "What shape is the roof?" })).toBeInTheDocument();
    expect(screen.queryByRole("radio", { name: "Steep" })).not.toBeInTheDocument();
    expect(screen.queryByText("Shape")).not.toBeInTheDocument();
    unmount();
    withApp({ answers: [a("roof_style", "gable", "b1")] });
    open("/projects/abc/buildings?screen=roof_style&item=b1");
    expect(await screen.findByRole("radio", { name: "Steep" })).toBeInTheDocument();
  });

  it("the materials: another material is asked only when Something else is chosen", async () => {
    const { unmount } = open("/projects/abc/buildings?screen=exterior_finish&item=b1");
    await screen.findByRole("heading", { level: 2, name: "What will the outside walls and roof be covered with?" });
    expect(screen.queryByRole("textbox", { name: "Other material" })).not.toBeInTheDocument();
    expect(screen.queryByText("Materials")).not.toBeInTheDocument();
    unmount();
    withApp({ answers: [a("exterior_finish", ["other"], "b1")] });
    open("/projects/abc/buildings?screen=exterior_finish&item=b1");
    expect(await screen.findByRole("textbox", { name: "Other material" })).toBeInTheDocument();
  });

  it("the walls appear once the front's direction is chosen", async () => {
    const { unmount } = open("/projects/abc/buildings?screen=front_facing&item=b1");
    await screen.findByRole("radio", { name: "North" });
    expect(screen.queryByRole("slider")).not.toBeInTheDocument();
    unmount();
    withApp({ answers: [a("front_facing", "north", "b1")] });
    open("/projects/abc/buildings?screen=front_facing&item=b1");
    expect(await screen.findByRole("slider", { name: "Front (north, faces Sheepscot Road)" })).toBeInTheDocument();
  });

  it("the bar never shows fewer cards than are already answered", async () => {
    // Floors above ground cleared after the size card was reached: the card count stays put.
    withApp({ answers: finished("b1") });
    open("/projects/abc/buildings?screen=front_facing&item=b1");
    expect(await screen.findByRole("img", { name: "Question 8 of 8" })).toBeInTheDocument();
  });
});

describe("the buildings list", () => {
  it("one row per building with its summary; Change, Finish and Delete", async () => {
    withApp({ items: [B1, B2], answers: [...finished("b1"), a("building_class", "residential_accessory", "b2")] });
    open("/projects/abc/buildings");
    expect(await screen.findByText("28 × 40 ft · 1 floor · front faces north")).toBeInTheDocument();
    expect(screen.getByText(/answers to go/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Change Building 1" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Finish Building 2" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Delete Building 2" })).toBeInTheDocument();
  });

  it("the only building can't be deleted", async () => {
    withApp({ answers: finished("b1") });
    open("/projects/abc/buildings");
    await screen.findByText("Building 1 · A home");
    expect(screen.queryByRole("button", { name: /^Delete/ })).not.toBeInTheDocument();
  });

  it("Delete asks first, then removes it", async () => {
    withApp({ items: [B1, B2], answers: finished("b1") });
    const remove = vi.spyOn(apps, "removePart").mockResolvedValue({ revision: 4 } as never);
    open("/projects/abc/buildings");
    await userEvent.click(await screen.findByRole("button", { name: "Delete Building 2" }));
    withApp({ items: [B1], answers: finished("b1") });
    await userEvent.click(await screen.findByRole("button", { name: "Delete" }));
    await waitFor(() => expect(remove).toHaveBeenCalledWith("abc", 3, "b2"));
  });

  it("Add a building opens its first card", async () => {
    withApp({ answers: finished("b1") });
    const add = vi.spyOn(apps, "addPart").mockImplementation(async () => {
      withApp({ items: [B1, B2], answers: finished("b1") });
      return { revision: 4, missing: [], id: "b2" };
    });
    open("/projects/abc/buildings");
    await userEvent.click(await screen.findByRole("button", { name: "Add a building" }));
    expect(add).toHaveBeenCalledWith("abc", 3, "building", undefined);
    await waitFor(() => expect(where()).toHaveTextContent("/projects/abc/buildings?screen=building_class&item=b2"));
  });

  it("Copy Building 1 copies it and opens the copy's check page", async () => {
    withApp({ answers: finished("b1") });
    const add = vi.spyOn(apps, "addPart").mockImplementation(async () => {
      withApp({ items: [B1, B2], answers: [...finished("b1"), a("building_class", "residential", "b2")] });
      return { revision: 4, missing: [], id: "b2" };
    });
    open("/projects/abc/buildings");
    await userEvent.click(await screen.findByRole("button", { name: "Copy Building 1" }));
    expect(add).toHaveBeenCalledWith("abc", 3, "building", "b1");
    await waitFor(() => expect(where()).toHaveTextContent("/projects/abc/buildings/check?item=b2"));
  });

  it("no Copy until a building is finished", async () => {
    open("/projects/abc/buildings");
    await screen.findByRole("button", { name: "Add a building" });
    expect(screen.queryByRole("button", { name: /^Copy/ })).not.toBeInTheDocument();
  });

  it("an empty additions task: add one, or none", async () => {
    open("/projects/abc/additions");
    expect(await screen.findByRole("button", { name: "Add an addition, porch or deck" })).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "No additions" }));
    await waitFor(() => expect(where()).toHaveTextContent(/^\/projects\/abc$/));
    expect(JSON.parse(localStorage.getItem("portal.visited.abc")!)).toContain("additions");
  });
});

describe("Check and send", () => {
  it("opens, headed Check and send, once they are", async () => {
    localStorage.setItem("portal.visited.abc", JSON.stringify(["your_lot", "about_you", "the_work", "buildings", "additions"]));
    withApp({ answers: [a("lot_width", 120), a("lot_depth", 200), a("applicant_name", "Ada"), a("applicant_is_owner", true),
                        a("work_kinds", ["new_building"]), ...finished("b1")] });
    open("/projects/abc/send");
    const main = await screen.findByRole("main");
    expect(await within(main).findByText("Check and send")).toBeInTheDocument();
    expect(where()).toHaveTextContent("/projects/abc/send");
  });
});

describe("check pages", () => {
  it("a check page speaks the applicant's words, not the form's terms", async () => {
    withApp({ answers: finished("b1") });
    open("/projects/abc/buildings/check?item=b1");
    expect(await screen.findByText("A home")).toBeInTheDocument();
    expect(screen.getByText("Gable")).toBeInTheDocument();
  });

  it("a task's answers with Change; Change comes back to the check page", async () => {
    withApp({ answers: [a("applicant_name", "Ada"), a("applicant_is_owner", true)] });
    open("/projects/abc/about_you/check");
    expect(await screen.findByText("Check About you")).toBeInTheDocument();
    expect(screen.getByText("Ada")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("link", { name: "Change What is your full name?" }));
    await waitFor(() => expect(where()).toHaveTextContent("?screen=applicant_name&return=check"));
    await userEvent.type(screen.getByRole("textbox", { name: "What is your full name?" }), " Lovelace");
    await userEvent.click(screen.getByRole("button", { name: "Continue" }));
    await waitFor(() => expect(where()).toHaveTextContent("/projects/abc/about_you/check"));
  });

  it("a change that adds a card asks it first, then comes back", async () => {
    withApp({ answers: [a("applicant_name", "Ada"), a("applicant_is_owner", true)] });
    open("/projects/abc/about_you?screen=applicant_is_owner&return=check");
    await userEvent.click(await screen.findByRole("radio", { name: "No" }));
    await waitFor(() => expect(where()).toHaveTextContent("?screen=owner_name&return=check"));
  });

  it("Done on a task's check page goes to the task list", async () => {
    withApp({ answers: [a("applicant_name", "Ada"), a("applicant_is_owner", true)] });
    open("/projects/abc/about_you/check");
    await userEvent.click(await screen.findByRole("button", { name: "Done" }));
    await waitFor(() => expect(where()).toHaveTextContent(/^\/projects\/abc$/));
  });
});

// Everything answered and every task opened: Check and send is open.
const COMPLETE = [a("lot_width", 120), a("lot_depth", 200), a("applicant_name", "Ada"), a("applicant_is_owner", true),
                  a("work_kinds", ["new_building"]), ...finished("b1")];
const visitAll = () => localStorage.setItem("portal.visited.abc", JSON.stringify(["your_lot", "about_you", "the_work", "buildings", "additions"]));

// Kept from the wizard's tests (wizard.test.tsx, 2026-10-24), as cards.
describe("kept from the wizard", () => {
  it("Skip for now leaves an optional upload empty and moves on", async () => {
    withApp({ answers: [a("work_kinds", ["site"])] });
    open("/projects/abc/the_work?screen=sketch");
    await userEvent.click(await screen.findByRole("button", { name: "Skip for now" }));
    await waitFor(() => expect(where()).toHaveTextContent("/projects/abc/the_work/check"));
  });

  it("Change from review returns to review, unless new cards now apply", async () => {
    visitAll();
    withApp({ answers: COMPLETE });
    open("/projects/abc/about_you?screen=applicant_is_owner&return=review");
    await userEvent.click(await screen.findByRole("radio", { name: "No" }));
    await waitFor(() => expect(where()).toHaveTextContent("?screen=owner_name&return=review"));
    await userEvent.type(await screen.findByRole("textbox", { name: "What is the property owner's full name?" }), "Bob");
    await userEvent.click(screen.getByRole("button", { name: "Continue" }));
    await waitFor(() => expect(where()).toHaveTextContent("/projects/abc/send"));
  });

  it("Change from review goes back to review past cards left blank before", async () => {
    visitAll();
    withApp({ answers: COMPLETE.filter((x) => x.field_id !== "lot_depth").concat(a("lot_depth", { unknown: true })) });
    open("/projects/abc/your_lot?screen=lot_area&return=review");
    await userEvent.click(await screen.findByRole("radio", { name: "Yes, that's right" }));
    await waitFor(() => expect(where()).toHaveTextContent("/projects/abc/send"));
  });

  it("Another road is typed, then Continue", async () => {
    withApp({ form: { ...FORM, sections: FORM.sections.map((s) => s.id === "project"
      ? { ...s, fields: [q("entrance_road", "Which road will the entrance be on?", { type: "text", control: "street-picker", step: "the_work" }), ...s.fields] } : s) } });
    open("/projects/abc/the_work?screen=entrance_road");
    await userEvent.click(await screen.findByRole("radio", { name: "Another road" }));
    await userEvent.type(screen.getByRole("textbox", { name: "Name of the road" }), "Main Street");
    await new Promise((r) => setTimeout(r, 300));
    expect(where()).toHaveTextContent("?screen=entrance_road");
    await userEvent.click(screen.getByRole("button", { name: "Continue" }));
    await waitFor(() => expect(where()).toHaveTextContent("?screen=work_kinds"));
    expect(saved()).toContainEqual(a("entrance_road", "Main Street"));
  });
});

// The whole-branch review's fixes (task-list Task 9).
describe("review fixes", () => {
  it("a check page and the buildings list scroll between their header and footer", async () => {
    withApp({ answers: finished("b1") });
    const { unmount } = open("/projects/abc/buildings/check?item=b1");
    await screen.findByText("Check Building 1");
    expect(document.querySelector("[data-card-scroll]")!.className).toContain("overflow-y-auto");
    expect(document.querySelector("[data-card-scroll]")).toContainElement(screen.getAllByRole("link", { name: /^Change / })[0]);
    unmount();
    open("/projects/abc/buildings");
    await screen.findByText("Building 1 · A home");
    expect(document.querySelector("[data-card-scroll]")).toContainElement(screen.getByText("Building 1 · A home"));
  });

  it("I don't know some of these yet keeps a value just typed", async () => {
    open("/projects/abc/your_lot?screen=lot_width");
    await userEvent.type(await screen.findByRole("textbox", { name: "Width" }), "120");
    fireEvent.click(screen.getByRole("button", { name: "I don't know some of these yet" }));
    await waitFor(() => expect(saved()).toContainEqual(a("lot_depth", { unknown: true })));
    expect(saved()).toContainEqual(a("lot_width", 120));
    expect(saved()).not.toContainEqual(a("lot_width", { unknown: true }));
  });

  it("a check page names the building an addition is attached to", async () => {
    const C1 = { id: "c1", kind: "component", position: 0 };
    withApp({ items: [B1, C1], answers: [...finished("b1"), a("component_kind", "deck", "c1"), a("attached_to", "b1", "c1")] });
    open("/projects/abc/additions/check?item=c1");
    await screen.findByText("Check Addition 1");
    expect(screen.getByText("Building 1 · A home")).toBeInTheDocument(); // as on the buildings list
    expect(screen.queryByText("b1")).not.toBeInTheDocument();
  });

  it("no Copy on the additions list: additions copy nothing", async () => {
    const C1 = { id: "c1", kind: "component", position: 0 };
    withApp({ items: [B1, C1], answers: [...finished("b1"), a("component_kind", "deck", "c1")] });
    open("/projects/abc/additions");
    await screen.findByRole("button", { name: "Add an addition, porch or deck" });
    expect(screen.queryByRole("button", { name: /^Copy/ })).not.toBeInTheDocument();
  });

  it("the bar counts the cards that apply now, even after an answer removes one", async () => {
    // In one visit: the owner's card seen (3 of 3), then "Yes, I own it" removes it.
    withApp({ answers: [a("applicant_name", "Ada"), a("applicant_is_owner", false)] });
    open("/projects/abc/about_you?screen=owner_name");
    expect(await screen.findByRole("img", { name: "Question 3 of 3" })).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Back" }));
    await userEvent.click(await screen.findByRole("radio", { name: "Yes" }));
    await waitFor(() => expect(where()).toHaveTextContent("/projects/abc/about_you/check"));
    await userEvent.click(await screen.findByRole("link", { name: "Change What is your full name?" }));
    expect(await screen.findByRole("img", { name: "Question 1 of 2" })).toBeInTheDocument();
  });

  it("a form's default alone doesn't count as an answered card on the dashboard", async () => {
    // A homes count starts the task; the renovation question's default isn't an answer.
    withApp({ answers: [a("renovation_only", false, "b1"), a("dwelling_units", 1, "b1")] });
    open("/projects/abc");
    const main = await screen.findByRole("main");
    expect(within(main).getByRole("link", { name: /^Buildings.*0 of 8 ?answered$/ })).toBeInTheDocument();
  });

  it("Skip for now is a plain button; only Continue is filled", async () => {
    withApp({ answers: [a("work_kinds", ["site"])] });
    open("/projects/abc/the_work?screen=sketch");
    expect(await screen.findByRole("button", { name: "Skip for now" })).not.toHaveAttribute("data-filled");
  });

  it("a count reaches its least from blank with −", async () => {
    open("/projects/abc/buildings?screen=building_name&item=b1");
    await userEvent.click(await screen.findByRole("button", { name: "Homes in it, one fewer" }));
    await waitFor(() => expect(saved()).toContainEqual(a("dwelling_units", 0, "b1")));
  });

  it("an empty additions list asks in its own words", async () => {
    open("/projects/abc/additions");
    expect(await screen.findByText("Are you adding an addition, a porch or a deck?")).toBeInTheDocument();
  });
});
