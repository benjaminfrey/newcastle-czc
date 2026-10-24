import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes, useLocation } from "react-router";
import { beforeEach, describe, expect, it, vi } from "vitest";
import * as api from "../api";
import * as apps from "../applications";
import * as layout from "../shell/useWideLayout";
import ApplicationPage from "./ApplicationPage";

vi.mock("../components/ParcelMap", () => ({ default: () => <div>map</div> }));

const q = (id: string, label: string, extra: Partial<apps.FormField> = {}): apps.FormField => ({
  id, official_label: id, source: "question", from: null, may_correct: false, label, help: null, why: null,
  type: "text", unit: null, min: null, max: null, required: true, allow_unknown: false, show_if: null, options: [],
  step: null, screen: null, ask_first: false, control: null, step_size: null, default: null, autocomplete: null, ...extra,
});
const sec = (id: string, step: string, fields: apps.FormField[], extra: Partial<apps.FormSection> = {}): apps.FormSection =>
  ({ id, official_title: id, chapter: id, show_if: null, repeat: null, step, screens: [],
     fields: fields.map((f) => ({ ...f, step: f.step ?? step })), ...extra });
const opts = (...v: [string, string][]) => v.map(([value, label]) => ({ value, label, official: label }));
const BUILDING = { kind: "building", add_label: "Add a building", min: 1, max: 20 };
const COMPONENT = { kind: "component", add_label: "Add an addition", min: 0, max: 30 };

const FORM: apps.FormDef = {
  key: "small_project_plan", version: 1, ruleset_key: "adopted-v1.0", official_title: "Small Project Plan Application",
  steps: [{ id: "lot", title: "Your lot" }, { id: "you", title: "About you" }, { id: "work", title: "The work" },
          { id: "buildings", title: "Buildings" }, { id: "additions", title: "Additions" }],
  sections: [
    sec("site", "lot", [
      q("lot_area", "How big is your lot, in acres?", { source: "property", from: "acres", may_correct: true, type: "number", unit: "acres" }),
      q("lot_width", "How wide is your lot, in feet?", { type: "number", unit: "ft", allow_unknown: true })]),
    sec("applicant", "you", [
      q("applicant_name", "What is your full name?"), q("applicant_phone", "What phone number should the Town use?"),
      q("applicant_is_owner", "Do you own this property?", { type: "yesno", control: "switch" })]),
    sec("owner", "you", [q("owner_name", "What is the property owner's full name?")],
        { show_if: { eq: ["answers.applicant_is_owner", false] } }),
    sec("project", "work", [q("sketch", "Add a sketch, if you have one", { type: "upload", required: false })]),
    sec("building_details", "buildings", [
      q("building_class", "Which best describes this building?", { type: "choice", control: "building-type", ask_first: true,
        options: opts(["home", "A home"], ["shed", "A shed"]) }),
      q("building_name", "What do you call this building?", { required: false })], { repeat: BUILDING }),
    sec("building_windows", "buildings", [
      q("front_facing", "Which way does the front of the building face?", { type: "choice", control: "tiles",
        options: opts(["north", "North"], ["east", "East"], ["south", "South"], ["west", "West"]) }),
      ...["north", "east", "south", "west"].map((w) => q(`windows_${w}`, `${w[0].toUpperCase()}${w.slice(1)} wall`,
        { type: "number", control: "slider", screen: "walls", min: 0, max: 100, step_size: 5, unit: "%" }))],
      { repeat: BUILDING, screens: [{ id: "walls", layout: "compass" }] }),
    sec("component", "additions", [q("component_kind", "What are you adding?", { type: "choice", control: "tiles",
      options: opts(["addition", "An addition"], ["deck", "A deck"]) })], { repeat: COMPONENT }),
  ],
};
const B1 = { id: "b1", kind: "building", position: 0 };
const B2 = { id: "b2", kind: "building", position: 1 };
const APP: apps.AppState = {
  id: "abc", form_key: "small_project_plan", form_version: 1, ruleset_key: "adopted-v1.0", status: "draft", revision: 3,
  property: { source: "lookup", parcel_id: null, map_lot: "004-036",
              facts: { acres: 2.73, streets: [{ name: "Sheepscot Road" }], location: "461 SHEEPSCOT RD" },
              parcels_as_of: null, verified: true, disputed: false, note: "" },
  items: [B1], answers: [], notes: [], attachments: [], missing: [], newer_version: false,
};
const a = (field_id: string, value: unknown, item_id: string | null = null) => ({ field_id, item_id, value });

function Where() {
  const l = useLocation();
  return <p data-testid="where">{l.pathname}{l.search}</p>;
}
const open = (path: string) => render(
  <MemoryRouter initialEntries={[path]}>
    <Routes>
      <Route path="/applications/:id/:stepId?" element={<><ApplicationPage /><Where /></>} />
      <Route path="*" element={<Where />} />
    </Routes>
  </MemoryRouter>,
);
const where = () => screen.getByTestId("where");
const withApp = (over: Partial<apps.AppState>) => vi.spyOn(apps, "getApplication").mockResolvedValue({ ...APP, ...over });
let save: ReturnType<typeof vi.spyOn>;

beforeEach(() => {
  localStorage.clear();
  vi.restoreAllMocks();
  vi.spyOn(layout, "useWideLayout").mockReturnValue(true);
  vi.spyOn(apps, "getApplication").mockResolvedValue(APP);
  vi.spyOn(apps, "getForm").mockResolvedValue(FORM);
  vi.spyOn(api, "getMe").mockResolvedValue({ email: "a@example.com", role: "applicant" });
  vi.spyOn(api, "getUseGroups").mockResolvedValue([]);
  save = vi.spyOn(apps, "saveAnswers").mockResolvedValue({ revision: 4, missing: [] });
});
const saved = () => save.mock.calls.flatMap((c: unknown[]) => c[2] as apps.Change[]);

describe("the wizard", () => {
  it("a single choice moves on at a tap", async () => {
    withApp({ answers: [a("applicant_name", "Ada"), a("applicant_phone", "207")] });
    open("/applications/abc/you?screen=applicant_is_owner");
    await userEvent.click(await screen.findByRole("radio", { name: "Yes" }));
    expect(screen.queryByRole("button", { name: "Continue" })).not.toBeInTheDocument();
    await waitFor(() => expect(where()).toHaveTextContent("/applications/abc/work?screen=sketch"));
    expect(saved()).toContainEqual(a("applicant_is_owner", true));
  });

  it("Continue saves a typed answer and moves on; Return does the same", async () => {
    open("/applications/abc/you?screen=applicant_name");
    await userEvent.type(await screen.findByRole("textbox", { name: "What is your full name?" }), "Ada");
    await userEvent.click(screen.getByRole("button", { name: "Continue" }));
    await waitFor(() => expect(where()).toHaveTextContent("?screen=applicant_phone"));
    expect(saved()).toContainEqual(a("applicant_name", "Ada"));
    await userEvent.type(await screen.findByRole("textbox", { name: "What phone number should the Town use?" }), "207{Enter}");
    await waitFor(() => expect(where()).toHaveTextContent("?screen=applicant_is_owner"));
    expect(saved()).toContainEqual(a("applicant_phone", "207"));
  });

  it("Back goes to the previous screen, across steps", async () => {
    open("/applications/abc/you?screen=applicant_name");
    await userEvent.click(await screen.findByRole("button", { name: "Back" }));
    await waitFor(() => expect(where()).toHaveTextContent("/applications/abc/lot?screen=lot_width"));
  });

  it("Back from a new building's first screen goes to the previous building's last screen", async () => {
    withApp({ items: [B1, B2] });
    open("/applications/abc/buildings?screen=building_class&item=b2");
    await userEvent.click(await screen.findByRole("button", { name: "Back" }));
    await waitFor(() => expect(where()).toHaveTextContent("/applications/abc/buildings?screen=windows_north&item=b1"));
  });

  it("chips go back to their question", async () => {
    withApp({ answers: [a("applicant_name", "Ada")] });
    open("/applications/abc/you?screen=applicant_phone");
    await userEvent.click(await screen.findByRole("button", { name: /^Ada/ }));
    await waitFor(() => expect(where()).toHaveTextContent("?screen=applicant_name"));
  });

  it("a chip saves the typed answer first", async () => {
    withApp({ answers: [a("applicant_name", "Ada")] });
    open("/applications/abc/you?screen=applicant_phone");
    await userEvent.type(await screen.findByRole("textbox", { name: "What phone number should the Town use?" }), "207");
    await userEvent.click(screen.getByRole("button", { name: /^Ada/ }));
    await waitFor(() => expect(saved()).toContainEqual(a("applicant_phone", "207")));
  });

  it("the trail drops answers whose screens stopped applying", async () => {
    withApp({ answers: [a("applicant_name", "Ada"), a("applicant_phone", "207"), a("applicant_is_owner", true), a("owner_name", "Bob")] });
    open("/applications/abc/you?screen=applicant_is_owner");
    await screen.findByRole("heading", { level: 2, name: "Do you own this property?" });
    const trail = screen.getByRole("group", { name: "Your answers" });
    expect(within(trail).getByRole("button", { name: /^Ada/ })).toBeInTheDocument();
    expect(within(trail).queryByRole("button", { name: /^Bob/ })).not.toBeInTheDocument();
  });

  it("Is this right? Yes moves on and saves nothing; I'll correct it saves the typed value", async () => {
    open("/applications/abc/lot?screen=lot_area");
    expect(await screen.findByText(/2\.73/)).toBeInTheDocument();
    await userEvent.click(screen.getByRole("radio", { name: "Yes, that's right" }));
    await waitFor(() => expect(where()).toHaveTextContent("?screen=lot_width"));
    expect(saved()).toEqual([]);
  });

  it("I'll correct it opens the field and saves what is typed", async () => {
    open("/applications/abc/lot?screen=lot_area");
    await userEvent.click(await screen.findByRole("radio", { name: "No, I'll correct it" }));
    const box = await screen.findByRole("textbox", { name: "How big is your lot, in acres?" });
    await userEvent.clear(box);
    await userEvent.type(box, "2.5");
    await userEvent.click(screen.getByRole("button", { name: "Continue" }));
    await waitFor(() => expect(saved()).toContainEqual(a("lot_area", 2.5)));
  });

  it("another building adds exactly one", async () => {
    let finish!: (v: { id: string; revision: number }) => void;
    const add = vi.spyOn(apps, "addItem").mockReturnValue(new Promise((r) => { finish = r; }) as never);
    open("/applications/abc/buildings?screen=another:building");
    const yes = await screen.findByRole("radio", { name: "Yes, add another building" });
    await userEvent.click(yes);
    await userEvent.click(yes);
    expect(add).toHaveBeenCalledTimes(1);
    withApp({ items: [B1, B2] });
    finish({ id: "b2", revision: 4 });
    await waitFor(() => expect(where()).toHaveTextContent("/applications/abc/buildings?screen=building_class&item=b2"));
  });

  it("No, that's all goes to the next step", async () => {
    open("/applications/abc/buildings?screen=another:building");
    await userEvent.click(await screen.findByRole("radio", { name: "No, that's all" }));
    await waitFor(() => expect(where()).toHaveTextContent("/applications/abc/additions?screen=any:component"));
  });

  it("an empty additions step asks first; No moves on and marks the step visited", async () => {
    open("/applications/abc/additions?screen=any:component");
    await userEvent.click(await screen.findByRole("radio", { name: "No" }));
    await waitFor(() => expect(where()).toHaveTextContent("/applications/abc/review"));
    expect(JSON.parse(localStorage.getItem("portal.visited.abc")!)).toContain("additions");
  });

  it("Change from review returns to review, unless new screens now apply", async () => {
    withApp({ answers: [a("applicant_name", "Ada"), a("applicant_phone", "207"), a("applicant_is_owner", true)] });
    open("/applications/abc/you?screen=applicant_is_owner&return=review");
    await userEvent.click(await screen.findByRole("radio", { name: "No" }));
    await waitFor(() => expect(where()).toHaveTextContent("?screen=owner_name&return=review"));
    await userEvent.type(await screen.findByRole("textbox", { name: "What is the property owner's full name?" }), "Bob");
    await userEvent.click(screen.getByRole("button", { name: "Continue" }));
    await waitFor(() => expect(where()).toHaveTextContent("/applications/abc/review"));
  });

  it("Change from review finds new questions even past an answered one", async () => {
    // As on the real cover sheet: "Is someone helping?" (answered) sits between the owner question and the owner's details.
    const helper = { ...FORM, sections: FORM.sections.map((sec) => sec.id === "applicant"
      ? { ...sec, fields: [...sec.fields, { ...sec.fields[0], id: "has_agent", label: "Is someone helping?", type: "yesno" as const, control: "switch" as const }] }
      : sec) };
    vi.spyOn(apps, "getForm").mockResolvedValue(helper);
    withApp({ answers: [a("applicant_name", "Ada"), a("applicant_phone", "207"), a("applicant_is_owner", true), a("has_agent", false)] });
    open("/applications/abc/you?screen=applicant_is_owner&return=review");
    await userEvent.click(await screen.findByRole("radio", { name: "No" }));
    await waitFor(() => expect(where()).toHaveTextContent("?screen=owner_name&return=review"));
  });

  it("the walls name the front", async () => {
    withApp({ answers: [a("front_facing", "north", "b1")] });
    open("/applications/abc/buildings?screen=windows_north&item=b1");
    expect(await screen.findByRole("slider", { name: "Front (north, faces Sheepscot Road)" })).toBeInTheDocument();
    expect(screen.getByRole("slider", { name: "Back (south)" })).toBeInTheDocument();
    expect(screen.getByRole("slider", { name: "Side (east)" })).toBeInTheDocument();
  });

  it("I don't know yet answers as unknown and moves on", async () => {
    open("/applications/abc/lot?screen=lot_width");
    await userEvent.click(await screen.findByRole("button", { name: "I don't know yet" }));
    await waitFor(() => expect(where()).toHaveTextContent("/applications/abc/you?screen=applicant_name"));
    expect(saved()).toContainEqual(a("lot_width", { unknown: true }));
  });

  it("Skip for now leaves an optional upload empty and moves on", async () => {
    open("/applications/abc/work?screen=sketch");
    await userEvent.click(await screen.findByRole("button", { name: "Skip for now" }));
    await waitFor(() => expect(where()).toHaveTextContent("/applications/abc/buildings?screen=building_class&item=b1"));
  });

  it("the dots count the group, and no Why we ask", async () => {
    withApp({ answers: [a("applicant_name", "Ada")] });
    open("/applications/abc/you?screen=applicant_phone");
    // The owner's question counts until "Do you own this property?" is answered Yes.
    expect(await screen.findByRole("img", { name: "Question 2 of 4" })).toBeInTheDocument();
    expect(screen.queryByText("Why we ask")).not.toBeInTheDocument();
  });

  it("⌘↓ from a text field saves the answer", async () => {
    open("/applications/abc/you?screen=applicant_name");
    await userEvent.type(await screen.findByRole("textbox", { name: "What is your full name?" }), "Ada");
    await userEvent.keyboard("{Meta>}{ArrowDown}{/Meta}");
    await waitFor(() => expect(saved()).toContainEqual(a("applicant_name", "Ada")));
  });

  it("site-only work has no Buildings step", async () => {
    const site: apps.FormDef = { ...FORM, sections: FORM.sections.map((s) => s.repeat?.kind === "building"
      ? { ...s, show_if: { eq: ["answers.applicant_is_owner", "never"] } } : s) };
    vi.spyOn(apps, "getForm").mockResolvedValue(site);
    withApp({ answers: [a("applicant_is_owner", true)] });
    open("/applications/abc/work?screen=sketch");
    const nav = await screen.findByRole("navigation", { name: "Steps" });
    expect(within(nav).queryByRole("link", { name: /^Buildings/ })).not.toBeInTheDocument();
  });
});
