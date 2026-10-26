import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes, useLocation } from "react-router";
import { beforeEach, describe, expect, it, vi } from "vitest";
import * as api from "../api";
import * as apps from "../projects";
import * as layout from "../shell/useWideLayout";
import ProjectPage from "./ProjectPage";

vi.mock("../components/ParcelMap", () => ({ default: () => <div>map</div> }));

// A project's merged form, as the API builds it: the cover sheet's two rows, then a row per part.
const q = (id: string, label: string, extra: Partial<apps.FormField> = {}): apps.FormField => ({
  id, official_label: id, source: "question", from: null, may_correct: false, label, help: null, why: null,
  type: "text", unit: null, min: null, max: null, required: true, allow_unknown: false, show_if: null, options: [],
  step: null, screen: null, ask_first: 0, control: null, step_size: null, default: null, autocomplete: null, ...extra,
});
const sec = (id: string, step: string, fields: apps.FormField[], extra: Partial<apps.FormSection> = {}): apps.FormSection =>
  ({ id, official_title: id, chapter: id, show_if: null, repeat: null, step, screens: [], fields, ...extra });
const FORM: apps.FormDef = {
  key: "project", version: 1, ruleset_key: "adopted-v1.0", official_title: "Project",
  steps: [{ id: "your_lot", title: "Your lot" }, { id: "about_you", title: "About you" },
          { id: "building", title: "New buildings" }, { id: "driveway", title: "Driveway" }],
  sections: [
    sec("location", "your_lot", [q("deed_book", "What is the deed book?", { required: false })]),
    sec("applicant", "about_you", [q("applicant_is_owner", "Do you own this property?", { type: "yesno" })]),
    sec("building", "building", [q("building_name", "What do you call this building?"), q("stories", "How many stories?", { type: "number" })],
        { repeat: { kind: "building", add_label: "Add a building", min: 1, max: 20 } }),
    sec("entrance", "driveway", [q("driveway_width", "How wide is the driveway?", { type: "number" })]),
  ],
};
const NEEDS: apps.Needs = {
  permits: [{ key: "building_permit", name: "Building Permit", application_fee: 30, application_fee_words: "$30", reviews: [
    { review_key: "small_project_plan", use_key: null, name: "Small Project Plan", code_name: "Small Project Plan", plain: null,
      reviewer: "Code Enforcement Officer", certainty: "needed", in_portal: true, districts: [], fee: 0, fee_words: "No permit fee",
      clocks: [{ key: "small_project_decision", label: "x", plain: "The Code Enforcement Officer decides within 10 days of accepting your project.",
                 days: 10, basis: "calendar", when: null }] },
    { review_key: "large_project_plan", use_key: null, name: "Large Project Plan", code_name: "Large Project Plan", plain: null,
      reviewer: "Code Enforcement Officer", certainty: "may_need", in_portal: false, districts: [], fee: 240, fee_words: "$240", clocks: [] },
    { review_key: "structure", use_key: null, part_id: "b1", name: "Structure", code_name: "Structure", plain: null, reviewer: null,
      certainty: "needed", in_portal: true, districts: [], fee: 30, fee_words: "$30", clocks: [] },
    { review_key: "entrance_permit", use_key: null, name: "Entrances", code_name: "Driveway and Entrance Permit", plain: null,
      reviewer: "Code Enforcement Officer", certainty: "needed", in_portal: true, districts: [], fee: 0, fee_words: "No permit fee", clocks: [] },
  ] }],
  application_fees_total: 30, application_fees_vary: false, notes: [], not_listed: [], town_only: false,
};
const PROJECT: apps.ProjectState = {
  id: "p1", title: "A new building and a driveway at Sheepscot Road", status: "draft", revision: 3, ruleset_key: "adopted-v1.0",
  submitted_at: null, forms: {}, form: FORM, needs: NEEDS,
  property: { source: "lookup", parcel_id: 229, map_lot: "004-036", verified: true, disputed: false, note: "", parcels_as_of: "2012-04-01",
              facts: { location: "SHEEPSCOT ROAD", acres: 2.73, districts: [{ code: "D1", name: "Rural (D1)" }],
                       streets: [{ name: "Sheepscot Road", frontage_ft: 675 }] } },
  items: [{ id: "b1", kind: "building", position: 0 }, { id: "d1", kind: "driveway", position: 0 }],
  answers: [], notes: [], attachments: [], missing: [],
};
const PARTS: apps.PartDef[] = [
  { id: "building", label: "A new building", step: "New buildings", icon: "building-cottage", repeats: true },
  { id: "driveway", label: "A driveway", step: "Driveway", icon: "road", repeats: false },
  { id: "use", label: "Start or change a use", step: "Uses", icon: "building-store", repeats: false },
];

function Where() {
  const l = useLocation();
  return <p data-testid="where">{l.pathname}{l.search}</p>;
}
const open = () => render(<MemoryRouter initialEntries={["/projects/p1"]}><Routes>
  <Route path="/projects/:id/:stepId?/:sub?" element={<><ProjectPage /><Where /></>} />
</Routes></MemoryRouter>);

beforeEach(() => {
  localStorage.clear();
  vi.spyOn(layout, "useWideLayout").mockReturnValue(true);
  vi.spyOn(apps, "getProject").mockResolvedValue(PROJECT);
  vi.spyOn(apps, "getParts").mockResolvedValue(PARTS);
  vi.spyOn(api, "getMe").mockResolvedValue({ email: "a@example.com", role: "applicant", name: "Ada Lovelace", phone: "207", mailing_address: "PO Box 1" });
  vi.spyOn(api, "getUseGroups").mockResolvedValue([]);
});

describe("the dashboard", () => {
  it("shows the title, the parcel, a row per part and the parts still to add", async () => {
    open();
    expect(await screen.findByRole("heading", { level: 2, name: "A new building and a driveway at Sheepscot Road" })).toBeInTheDocument();
    const lot = screen.getByRole("link", { name: /^Your lot, Map 4, Lot 36.*(Not started|answered|Done)$/ });
    expect(lot).toHaveTextContent("Sheepscot Road · Rural (D1)");
    expect(lot).toHaveTextContent("2.73 acres · 675 ft on Sheepscot Road");
    const parts = screen.getByRole("list", { name: "Your project" });
    expect(within(parts).getAllByRole("link").map((l) => l.getAttribute("href"))).toEqual(["/projects/p1/building", "/projects/p1/driveway"]);
    expect(within(parts).getByRole("link", { name: /^New buildings.*Not started$/ })).toBeInTheDocument();
    const add = await screen.findByRole("region", { name: "Add to your project" });
    expect(within(add).getAllByRole("button").map((b) => b.textContent)).toEqual(["Start or change a use, add"]);
  });

  it("counts the rows with something still to answer", async () => {
    open();
    expect(await screen.findByText(/3 things left/)).toBeInTheDocument(); // About you, the building, the driveway
  });

  it("says Ready to send once nothing is left", async () => {
    vi.spyOn(apps, "getProject").mockResolvedValue({ ...PROJECT, answers: [
      { field_id: "applicant_is_owner", item_id: null, value: true }, { field_id: "building_name", item_id: "b1", value: "House" },
      { field_id: "stories", item_id: "b1", value: 2 }, { field_id: "driveway_width", item_id: null, value: 12 }] });
    open();
    expect(await screen.findByText("Ready to send")).toBeInTheDocument();
  });

  it("reads what the project needs in words", async () => {
    open();
    const needs = await screen.findByRole("region", { name: "Building Permit" });
    expect(within(needs).getByRole("heading", { level: 3 })).toHaveTextContent("Building Permit · $30 when you send");
    expect(needs).toHaveTextContent("Small Project PlanNo permit fee");
    expect(needs).toHaveTextContent("The Code Enforcement Officer decides within 10 days of accepting your project.");
    expect(needs).toHaveTextContent("May be needed — the Code Enforcement Officer confirms");
    expect(needs).toHaveTextContent("Not in the portal yet — the Town Office takes this one");
    expect(needs).toHaveTextContent("Structure$30");
    expect(needs).toHaveTextContent("EntrancesNo permit fee");
    expect(screen.getByText(/\$30 in application fees when you send/)).toBeInTheDocument();
  });

  it("adding a part opens its first card", async () => {
    const add = vi.spyOn(apps, "addPart").mockResolvedValue({ revision: 4, missing: [], id: "u1" });
    vi.spyOn(apps, "getProject").mockResolvedValueOnce(PROJECT).mockResolvedValue({ ...PROJECT,
      form: { ...FORM, steps: [...FORM.steps!, { id: "use", title: "Uses" }],
              sections: [...FORM.sections, sec("proposed", "use", [q("proposed_description", "What will happen there?")])] },
      items: [...PROJECT.items, { id: "u1", kind: "use", position: 0 }] });
    open();
    await userEvent.click(await screen.findByRole("button", { name: "Start or change a use, add" }));
    expect(add).toHaveBeenCalledWith("p1", 3, "use", undefined);
    await waitFor(() => expect(screen.getByTestId("where")).toHaveTextContent("/projects/p1/use?screen=proposed_description"));
  });

  it("renames the project", async () => {
    const title = vi.spyOn(apps, "setTitle").mockResolvedValue({ revision: 4, missing: [] });
    open();
    await userEvent.click(await screen.findByRole("button", { name: "Rename the project" }));
    const box = screen.getByRole("textbox", { name: "The project's name" });
    await userEvent.clear(box);
    await userEvent.type(box, "The new barn{Enter}");
    expect(title).toHaveBeenCalledWith("p1", 3, "The new barn");
    expect(await screen.findByRole("heading", { level: 2, name: "The new barn" })).toBeInTheDocument();
  });

  it("You shows who is applying and opens About you", async () => {
    open();
    const you = await screen.findByRole("link", { name: /^Ada Lovelace/ });
    expect(you).toHaveAttribute("href", "/projects/p1/about_you");
    expect(you).toHaveTextContent("a@example.com");
  });

  it("removes a single part after asking", async () => {
    const remove = vi.spyOn(apps, "removePart").mockResolvedValue({ revision: 4, missing: [] });
    open();
    await userEvent.click(await screen.findByRole("button", { name: "Remove" }));
    await userEvent.click(await screen.findByRole("button", { name: "Remove" }));
    expect(remove).toHaveBeenCalledWith("p1", 3, "d1");
  });
});
