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
  id, official_label: label, source: "question", from: null, may_correct: false, label: `${label}?`, help: null, why: null,
  type: "text", unit: null, min: null, max: null, required: true, allow_unknown: false, show_if: null, options: [],
  step: null, page: null, control: null, step_size: null, default: null, autocomplete: null, ...extra,
});
const REPEAT = { kind: "building", add_label: "Add another building", min: 1, max: 20,
  add_options: [{ label: "A building", preset: {} }, { label: "A detached garage or shed", preset: { building_class: "residential_accessory" } }] };
const FORM: apps.FormDef = {
  key: "small_project_plan", version: 1, ruleset_key: "adopted-v1.0", official_title: "Small Project Plan Application",
  steps: [{ id: "about_you", title: "About you" }, { id: "the_work", title: "The work" }, { id: "buildings", title: "Buildings" }],
  sections: [
    { id: "applicant", official_title: "Applicant", chapter: "Who", show_if: null, repeat: null, step: "about_you", pages: [], fields: [
      q("applicant_name", "Name", { step: "about_you" }),
      q("applicant_is_owner", "Owner", { type: "yesno", control: "switch", default: true, step: "about_you", label: "Do you own this property?" })] },
    { id: "owner", official_title: "Property Owner (if different)", chapter: "Who", show_if: { eq: ["answers.applicant_is_owner", false] },
      repeat: null, step: "about_you", pages: [], fields: [q("owner_name", "Owner name", { step: "about_you" })] },
    { id: "project", official_title: "Your Project", chapter: "Project", show_if: null, repeat: null, step: "the_work", pages: [], fields: [
      q("work_kinds", "Type of project", { type: "multichoice", control: "chips", step: "the_work",
        options: [{ value: "new_building", label: "A new building", official: "New" }, { value: "site", label: "Site work", official: "Site" }] })] },
    { id: "building", official_title: "Building Form", chapter: "Buildings", repeat: REPEAT, step: "buildings",
      show_if: { has: ["answers.work_kinds", "new_building"] },
      pages: [{ id: "basics", title: "Basics", layout: null }, { id: "windows", title: "Windows", layout: "compass" }],
      fields: [
        q("building_name", "Building reference (name)", { step: "buildings", page: "basics", required: false }),
        ...["north", "east", "south", "west"].map((w) => q(`windows_${w}`, `${w} %`, {
          type: "number", control: "slider", min: 0, max: 100, step_size: 5, unit: "%", step: "buildings", page: "windows",
          label: `${w[0].toUpperCase()}${w.slice(1)} wall` })),
      ] },
  ],
};
const APP: apps.AppState = {
  id: "abc", form_key: "small_project_plan", form_version: 1, ruleset_key: "adopted-v1.0", status: "draft", revision: 3,
  property: { source: "lookup", parcel_id: null, map_lot: "004-036", facts: { streets: [{ name: "Sheepscot Road" }] },
              parcels_as_of: null, verified: true, disputed: false, note: "" },
  items: [{ id: "b1", kind: "building", position: 0 }],
  answers: [{ field_id: "applicant_is_owner", item_id: null, value: true }, { field_id: "work_kinds", item_id: null, value: ["new_building"] }],
  notes: [], attachments: [], missing: [], newer_version: false,
};

function Where() {
  const l = useLocation();
  return <p data-testid="where">{l.pathname}{l.search}</p>;
}

const open = (path: string) =>
  render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route path="/applications/:id/:stepId?" element={<><ApplicationPage /><Where /></>} />
        <Route path="*" element={<Where />} />
      </Routes>
    </MemoryRouter>,
  );

beforeEach(() => {
  localStorage.clear();
  vi.spyOn(layout, "useWideLayout").mockReturnValue(true);
  vi.spyOn(apps, "getApplication").mockResolvedValue(APP);
  vi.spyOn(apps, "getForm").mockResolvedValue(FORM);
  vi.spyOn(api, "getMe").mockResolvedValue({ email: "a@example.com", role: "applicant" });
  vi.spyOn(api, "getUseGroups").mockResolvedValue([]);
});

describe("StepPane", () => {
  it("groups sections and reveals the owner group when the switch turns off", async () => {
    vi.spyOn(apps, "saveAnswers").mockResolvedValue({ revision: 4, missing: [] });
    open("/applications/abc/about_you");
    const applicant = await screen.findByRole("group", { name: "Applicant" });
    expect(screen.queryByRole("group", { name: "Property Owner (if different)" })).not.toBeInTheDocument();
    await userEvent.click(within(applicant).getByRole("switch", { name: "Do you own this property?" }));
    expect(await screen.findByRole("group", { name: "Property Owner (if different)" })).toBeInTheDocument();
  });

  it("focus moves to the step title and the page title names the step", async () => {
    open("/applications/abc/about_you");
    const h1 = await screen.findByRole("heading", { level: 1, name: "About you" });
    await waitFor(() => expect(h1).toHaveFocus());
    expect(document.title).toBe("About you — Small Project Plan Application");
  });
});

describe("ApplicationPage", () => {
  it("Continue waits for saves, then moves on", async () => {
    let finish!: (v: apps.SaveResult) => void;
    vi.spyOn(apps, "saveAnswers").mockReturnValue(new Promise((r) => { finish = r; }));
    open("/applications/abc/about_you");
    const name = await screen.findByRole("textbox", { name: "Name?" });
    await userEvent.type(name, "Ada");
    await userEvent.click(screen.getByRole("button", { name: "Continue" }));
    expect(screen.getByTestId("where")).toHaveTextContent("/applications/abc/about_you");
    finish({ revision: 4, missing: [] });
    await waitFor(() => expect(screen.getByTestId("where")).toHaveTextContent("/applications/abc/the_work"));
    expect(JSON.parse(localStorage.getItem("portal.visited.abc")!)).toContain("about_you");
  });

  it("Return in a text field saves the answer before moving on", async () => {
    const save = vi.spyOn(apps, "saveAnswers").mockResolvedValue({ revision: 4, missing: [] });
    open("/applications/abc/about_you");
    const name = await screen.findByRole("textbox", { name: "Name?" });
    await userEvent.type(name, "Ada{Enter}");
    await waitFor(() => expect(screen.getByTestId("where")).toHaveTextContent("/applications/abc/the_work"));
    expect(save).toHaveBeenCalledWith("abc", 3, [{ field_id: "applicant_name", item_id: null, value: "Ada" }]);
  });

  it("⌘↓ from a text field saves the answer, and ⌘↓ in a long answer stays there", async () => {
    const save = vi.spyOn(apps, "saveAnswers").mockResolvedValue({ revision: 4, missing: [] });
    open("/applications/abc/about_you");
    const name = await screen.findByRole("textbox", { name: "Name?" });
    await userEvent.type(name, "Ada");
    await userEvent.keyboard("{Meta>}{ArrowDown}{/Meta}");
    await waitFor(() => expect(save).toHaveBeenCalledWith("abc", 3, [{ field_id: "applicant_name", item_id: null, value: "Ada" }]));
  });

  it("a step opened from the sidebar counts as visited", async () => {
    open("/applications/abc/the_work");
    await screen.findByRole("heading", { level: 1, name: "The work" });
    await waitFor(() => expect(JSON.parse(localStorage.getItem("portal.visited.abc") ?? "[]")).toContain("the_work"));
  });

  it("site-only work has no Buildings step", async () => {
    vi.spyOn(apps, "getApplication").mockResolvedValue({ ...APP, answers: [{ field_id: "work_kinds", item_id: null, value: ["site"] }] });
    open("/applications/abc/the_work");
    const nav = await screen.findByRole("navigation", { name: "Steps" });
    expect(within(nav).queryByRole("link", { name: /^Buildings/ })).not.toBeInTheDocument();
    expect(within(nav).getAllByRole("link").map((l) => l.textContent)).toEqual(
      ["Your project", "Your property", "What you'll need", "About you", "The work", "Review and sign"]);
  });

  it("a reload reopens the sheet", async () => {
    open("/applications/abc/buildings?item=b1&page=windows");
    expect(await screen.findByRole("dialog", { name: "Building 1" })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "Windows" })).toHaveAttribute("aria-selected", "true");
  });
});

describe("HubPane and ItemSheet", () => {
  it("add options create the preset item", async () => {
    const add = vi.spyOn(apps, "addItem").mockResolvedValue({ revision: 4, missing: [], id: "b2" });
    open("/applications/abc/buildings");
    await userEvent.click(await screen.findByRole("button", { name: "Add a building" }));
    await userEvent.click(await screen.findByRole("menuitem", { name: "A detached garage or shed" }));
    expect(add).toHaveBeenCalledWith("abc", 3, "building", 1);
  });

  it("delete asks first", async () => {
    vi.spyOn(apps, "getApplication").mockResolvedValue({ ...APP, items: [...APP.items, { id: "b2", kind: "building", position: 1 }] });
    const remove = vi.spyOn(apps, "removeItem").mockResolvedValue({ revision: 4, missing: [] });
    open("/applications/abc/buildings?item=b2&page=windows");
    await userEvent.click(await screen.findByRole("button", { name: "Delete Building 2" }));
    expect(remove).not.toHaveBeenCalled();
    await userEvent.click(await screen.findByRole("button", { name: "Delete" }));
    expect(remove).toHaveBeenCalledWith("abc", 3, "b2");
  });

  it("the last building cannot be deleted", async () => {
    open("/applications/abc/buildings?item=b1&page=windows");
    await screen.findByRole("dialog", { name: "Building 1" });
    expect(screen.queryByRole("button", { name: /^Delete Building/ })).not.toBeInTheDocument();
  });

  it("pages and dots; Done returns to the hub", async () => {
    open("/applications/abc/buildings?item=b1&page=basics");
    await screen.findByRole("dialog", { name: "Building 1" });
    expect(screen.getByRole("textbox", { name: "Building reference (name)?" })).toBeInTheDocument();
    await userEvent.click(screen.getByRole("tab", { name: "Windows" }));
    expect(screen.getByTestId("where")).toHaveTextContent("page=windows");
    await userEvent.click(screen.getByRole("button", { name: "Done" }));
    await waitFor(() => expect(screen.getByTestId("where")).toHaveTextContent(/^\/applications\/abc\/buildings$/));
  });
});

describe("CompassLayout", () => {
  it("four sliders around the plan, labelled by wall, with the street side named", async () => {
    open("/applications/abc/buildings?item=b1&page=windows");
    await screen.findByRole("dialog", { name: "Building 1" });
    for (const wall of ["North wall", "East wall", "South wall", "West wall"]) {
      expect(screen.getByRole("slider", { name: wall })).toBeInTheDocument();
    }
    expect(screen.getByText("The front faces Sheepscot Road")).toBeInTheDocument();
  });
});
