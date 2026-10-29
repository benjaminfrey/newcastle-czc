import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes, useLocation } from "react-router";
import { beforeEach, describe, expect, it, vi } from "vitest";
import * as api from "../api";
import * as apps from "../projects";
import * as layout from "../shell/useWideLayout";
import ProjectPage from "./ProjectPage";

vi.mock("../components/ParcelMap", () => ({ default: () => <div>map</div> }));

const q = (id: string, label: string, extra: Partial<apps.FormField> = {}): apps.FormField => ({
  id, official_label: id, source: "question", from: null, may_correct: false, label, help: null, why: null,
  type: "text", unit: null, min: null, max: null, required: true, allow_unknown: false, show_if: null, options: [],
  step: null, screen: null, ask_first: 0, control: null, step_size: null, default: null, autocomplete: null, ...extra,
});
const sec = (id: string, step: string, fields: apps.FormField[]): apps.FormSection =>
  ({ id, official_title: id, chapter: id, show_if: null, repeat: null, step, screens: [], fields });
const FORM: apps.FormDef = {
  key: "project", version: 1, ruleset_key: "adopted-v1.0", official_title: "Project",
  steps: [{ id: "your_lot", title: "Your lot" }, { id: "about_you", title: "About you" }, { id: "driveway", title: "Driveway" }],
  sections: [
    sec("location", "your_lot", [q("deed_book", "What is the deed book?", { required: false })]),
    sec("applicant", "about_you", [q("applicant_is_owner", "Do you own this property?", { type: "yesno" })]),
    sec("entrance", "driveway", [q("driveway_width", "How wide is the driveway?", { type: "number" }),
                                 q("first_20ft_slope", "How steep is the first 20 feet?", { type: "number" })]),
  ],
};
const NEEDS: apps.Needs = {
  permits: [{ key: "building_permit", name: "Building Permit", application_fee: 30, application_fee_words: "$30", reviews: [
    { review_key: "entrance_permit", use_key: null, name: "Entrances", code_name: "Driveway and Entrance Permit", plain: null,
      reviewer: "Code Enforcement Officer", certainty: "needed", in_portal: true, districts: [], fee: 0, fee_words: "No permit fee", clocks: [] }] }],
  application_fees_total: 30, permit_fees_total: 0, application_fees_vary: false, notes: [], not_listed: [], town_only: false,
};
const DONE = [{ field_id: "applicant_is_owner", item_id: null, value: true }, { field_id: "driveway_width", item_id: null, value: 12 },
              { field_id: "first_20ft_slope", item_id: null, value: 5 }];
const PROJECT: apps.ProjectState = {
  id: "p1", title: "A driveway at Sheepscot Road", status: "draft", revision: 3, ruleset_key: "adopted-v1.0", submitted_at: null,
  forms: { cover_sheet: 1, entrance_permit: 1 }, form: FORM, needs: NEEDS,
  property: { source: "lookup", parcel_id: 229, map_lot: "004-036", verified: true, disputed: false, note: "", parcels_as_of: null,
              facts: { location: "SHEEPSCOT ROAD", acres: 2.73, districts: [], streets: [] } },
  items: [{ id: "d1", kind: "driveway", position: 0 }], answers: DONE, notes: [], attachments: [], missing: [],
};

function Where() {
  const l = useLocation();
  return <p data-testid="where">{l.pathname}{l.search}</p>;
}
const open = (path = "/projects/p1/send") => render(<MemoryRouter initialEntries={[path]}><Routes>
  <Route path="/projects/:id/:stepId?/:sub?" element={<><ProjectPage /><Where /></>} />
</Routes></MemoryRouter>);

beforeEach(() => {
  localStorage.clear();
  vi.spyOn(layout, "useWideLayout").mockReturnValue(true);
  vi.spyOn(apps, "getProject").mockResolvedValue(PROJECT);
  vi.spyOn(apps, "getParts").mockResolvedValue([]);
  vi.spyOn(api, "getMe").mockResolvedValue({ email: "a@example.com", role: "applicant", name: "Ada Lovelace", phone: "207", mailing_address: "PO Box 1" });
  vi.spyOn(api, "getUseGroups").mockResolvedValue([]);
});

describe("Check and send", () => {
  it("has a title, and on a wide screen keeps the fees and Send beside the project", async () => {
    open();
    expect(await screen.findByRole("heading", { level: 1, name: "Check and send" })).toBeInTheDocument();
    const rail = screen.getByRole("complementary", { name: "Fees and sending" });
    expect(within(rail).getByRole("region", { name: "Fees" })).toBeInTheDocument();
    expect(within(rail).getByRole("button", { name: "Send to the Town" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Your project" })).toHaveAttribute("href", "/projects/p1");
  });

  it("lists what to finish first, each opening the card it stops at; Send answers with the first", async () => {
    vi.spyOn(apps, "getProject").mockResolvedValue({ ...PROJECT, answers: DONE.slice(0, 2) });
    const submit = vi.spyOn(apps, "submitProject");
    open();
    const todo = await screen.findByRole("region", { name: "1 thing to finish first" });
    expect(within(todo).getByRole("link", { name: /Driveway/ })).toHaveAttribute("href", "/projects/p1/driveway?screen=first_20ft_slope");
    // It looks unavailable (plain, not filled) but answers with the first thing to finish.
    expect(screen.getByRole("button", { name: "Send to the Town" })).not.toHaveAttribute("data-filled");
    await userEvent.click(screen.getByRole("button", { name: "Send to the Town" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("First, finish Driveway.");
    expect(submit).not.toHaveBeenCalled();
  });

  it("shows the project at a glance, the fees due, and the official forms", async () => {
    open();
    const glance = await screen.findByRole("region", { name: "Your project at a glance" });
    expect(glance).toHaveTextContent("Map 4, Lot 36");
    expect(glance).toHaveTextContent("Ada Lovelace");
    expect(within(glance).getByRole("link", { name: /Change.*Driveway|Driveway.*Change/ })).toHaveAttribute("href", "/projects/p1/driveway/check");
    const fees = screen.getByRole("region", { name: "Fees" });
    expect(within(fees).getByRole("group", { name: "Due when you send" })).toHaveTextContent("Building Permitapplication fee$30");
    expect(within(fees).getByText("Total").parentElement).toHaveTextContent("Total$30");
    const forms = screen.getByRole("region", { name: "The official forms" });
    expect(forms).toHaveTextContent("Driveway and Entrance Permit Application");
    expect(within(forms).getByRole("button", { name: /View/ })).toBeDisabled();
    expect(forms).toHaveTextContent("Printing arrives in the next update");
  });

  it("asks first, then sends; the project stays editable", async () => {
    const submit = vi.spyOn(apps, "submitProject").mockResolvedValue({ revision: 4, missing: [] });
    open();
    await userEvent.click(await screen.findByRole("button", { name: "Send to the Town" }));
    const sheet = await screen.findByRole("alertdialog");
    expect(within(sheet).getByRole("heading", { name: "Send your project to the Town?" })).toBeInTheDocument();
    expect(sheet).toHaveTextContent("Building Permit");
    expect(sheet).toHaveTextContent("$30 in application fees");
    expect(sheet).toHaveTextContent("You can still add to your project until the Town locks it for review.");
    vi.spyOn(apps, "getProject").mockResolvedValue({ ...PROJECT, status: "submitted", revision: 4, submitted_at: "2026-10-25T15:00:00Z" });
    await userEvent.click(within(sheet).getByRole("button", { name: "Send" }));
    expect(submit).toHaveBeenCalledWith("p1", 3);
    await waitFor(() => expect(screen.getByTestId("where")).toHaveTextContent(/^\/projects\/p1$/));
    expect(await screen.findByText(/Sent October 25\. You can still add to your project until the Town locks it for review\./)).toBeInTheDocument();
  });

  it("a locked project's cards are read-only, with the line", async () => {
    vi.spyOn(apps, "getProject").mockResolvedValue({ ...PROJECT, status: "locked" });
    open("/projects/p1/driveway?screen=driveway_width");
    expect(await screen.findByText("The Town is reviewing this project; changes go through the Code Enforcement Officer.")).toBeInTheDocument();
    expect(screen.getByRole("textbox", { name: "How wide is the driveway?" })).toBeDisabled();
  });
});
