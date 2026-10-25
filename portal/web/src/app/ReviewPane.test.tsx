import { render, screen, within } from "@testing-library/react";
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
const sec = (id: string, title: string, step: string | null, fields: apps.FormField[], extra: Partial<apps.FormSection> = {}): apps.FormSection =>
  ({ id, official_title: title, chapter: title, show_if: null, repeat: null, step, pages: [], fields: fields.map((f) => ({ ...f, step: f.step ?? step })), ...extra });
const FORM: apps.FormDef = {
  key: "use_permit", version: 1, ruleset_key: "adopted-v1.0", official_title: "Use Permit Application",
  steps: [{ id: "your_lot", title: "Your lot" }, { id: "about_you", title: "About you" }],
  sections: [
    sec("site", "Site Information (existing)", "your_lot", [
      q("map_lot", "Map / Lot", { source: "property", from: "map_lot" }),
      q("lot_width", "Lot Width (ft)", { type: "number", unit: "ft", allow_unknown: true })]),
    sec("certification", "Certification", null, [q("signature", "Applicant Signature", { source: "at_submit" })]),
    sec("office", "Official Use Only", null, [q("date_received", "Date Received", { source: "staff" })]),
    sec("applicant", "Applicant", "about_you", [
      q("applicant_name", "Name"),
      q("applicant_email", "Email", { source: "account", from: "email" }),
      q("applicant_is_owner", "Applicant is the Property Owner", { type: "yesno", control: "switch", label: "Do you own this property?" })]),
    sec("owner", "Property Owner (if different)", "about_you", [q("owner_name", "Name")], { show_if: { eq: ["answers.applicant_is_owner", false] } }),
    sec("docs", "Attachments", "about_you", [q("use_documents", "Other relevant documentation", { type: "upload", required: false })]),
  ],
};
const APP: apps.AppState = {
  id: "abc", form_key: "use_permit", form_version: 1, ruleset_key: "adopted-v1.0", status: "draft", revision: 3,
  property: { source: "lookup", parcel_id: null, map_lot: "004-036", facts: { map_lot: "004-036" }, parcels_as_of: "2026-10-15",
              verified: true, disputed: false, note: "" },
  items: [], notes: [], newer_version: false, missing: [],
  attachments: [{ id: "t1", field_id: "use_documents", item_id: null, filename: "plan.pdf", content_type: "application/pdf", size_bytes: 10 }],
  answers: [{ field_id: "applicant_name", item_id: null, value: "Ada Lovelace" },
            { field_id: "applicant_is_owner", item_id: null, value: true },
            { field_id: "lot_width", item_id: null, value: { unknown: true } }],
};
const VERDICT = /\b(approved|denied|compliant|meets|fails|violates)\b/i;

function Where() {
  const l = useLocation();
  return <p data-testid="where">{l.pathname}{l.search}</p>;
}
const open = () => render(
  <MemoryRouter initialEntries={["/applications/abc/review"]}>
    <Routes><Route path="/applications/:id/:stepId?" element={<><ApplicationPage /><Where /></>} /></Routes>
  </MemoryRouter>,
);
const block = (name: string) => screen.getByRole("group", { name });

beforeEach(() => {
  localStorage.clear();
  vi.spyOn(layout, "useWideLayout").mockReturnValue(true);
  vi.spyOn(apps, "getApplication").mockResolvedValue(APP);
  vi.spyOn(apps, "getForm").mockResolvedValue(FORM);
  vi.spyOn(api, "getMe").mockResolvedValue({ email: "ada@example.com", role: "applicant" });
  vi.spyOn(api, "getUseGroups").mockResolvedValue([]);
});

describe("ReviewPane", () => {
  it("rows lead with the question as asked, the form's term beneath", async () => {
    open();
    const applicant = await screen.findByRole("group", { name: "Applicant" });
    expect(within(applicant).getByText("Name?")).toBeInTheDocument();
    expect(within(applicant).getByText("Name")).toBeInTheDocument();
    const width = within(block("Site Information (existing)")).getByText("Lot Width (ft)?").closest("[data-row]")!;
    expect(width.textContent!.startsWith("Lot Width (ft)?")).toBe(true);
    expect(width).toHaveTextContent("Lot Width (ft)");
    expect(within(applicant).getByText("Ada Lovelace")).toBeInTheDocument();
    expect(within(applicant).getByText("ada@example.com")).toBeInTheDocument();
    expect(within(applicant).getByText("Yes")).toBeInTheDocument();
    expect(screen.queryByRole("group", { name: "Property Owner (if different)" })).not.toBeInTheDocument();
    expect(within(block("Site Information (existing)")).getByText(/Not known yet/)).toBeInTheDocument();
    expect(within(block("Certification")).getByText("Signed when you submit")).toBeInTheDocument();
  });

  it("Certification and Office use come last", async () => {
    open();
    await screen.findByRole("group", { name: "Applicant" });
    const names = screen.getAllByRole("group").map((g) => g.getAttribute("aria-label") ?? g.textContent?.split("\n")[0]);
    // The official form's own sections; "What happens next" closes the page but isn't the form's.
    const titles = screen.getAllByRole("heading", { level: 2 }).map((h) => h.textContent).filter((t) => t !== "What happens next");
    expect(titles.slice(-2)).toEqual(["Certification", "Official Use Only"]);
    expect(names.length).toBeGreaterThan(2);
  });

  it("marks property facts and a property entered by hand", async () => {
    open();
    const site = await screen.findByRole("group", { name: "Site Information (existing)" });
    expect(within(site).getByText(/from the Town's maps — staff confirm/)).toBeInTheDocument();
    expect(screen.queryByText(/Property not verified/)).not.toBeInTheDocument();
  });

  it("links uploaded files", async () => {
    open();
    const docs = await screen.findByRole("group", { name: "Attachments" });
    expect(within(docs).getByRole("link", { name: "plan.pdf" })).toHaveAttribute("href", "/api/attachments/t1");
  });

  it("Add more detail saves a note printed under its section", async () => {
    const note = vi.spyOn(apps, "saveNote").mockResolvedValue({ revision: 4, missing: [] });
    open();
    await userEvent.click(await screen.findByRole("button", { name: "Add more detail to Applicant" }));
    await userEvent.type(await screen.findByLabelText("More detail for Applicant"), "Call after 5 pm.");
    await userEvent.click(screen.getByRole("button", { name: "Done" }));
    expect(note).toHaveBeenCalledWith("abc", 3, "applicant", null, "Call after 5 pm.");
    expect(await within(block("Applicant")).findByText("Call after 5 pm.")).toBeInTheDocument();
  });

  it("a map value the applicant changed isn't credited to the Town's maps", async () => {
    const area = q("lot_area", "Lot Area (acres)", { source: "property", from: "acres", may_correct: true, type: "number" });
    vi.spyOn(apps, "getForm").mockResolvedValue({ ...FORM, sections: FORM.sections.map((s) => s.id === "site" ? { ...s, fields: [...s.fields, { ...area, step: "your_lot" }] } : s) });
    vi.spyOn(apps, "getApplication").mockResolvedValue({ ...APP, property: { ...APP.property, facts: { map_lot: "004-036", acres: 2.1 } },
                                                         answers: [...APP.answers, { field_id: "lot_area", item_id: null, value: 2.4 }] });
    open();
    const site = await screen.findByRole("group", { name: "Site Information (existing)" });
    const row = within(site).getByText("Lot Area (acres)").closest("[data-row]")!;
    expect(row).toHaveTextContent("2.4");
    expect(row).not.toHaveTextContent("from the Town's maps");
    expect(row).toHaveTextContent("you changed the map's value");
    // The map's own values keep their note.
    expect(within(site).getByText("Map / Lot").closest("[data-row]")).toHaveTextContent("from the Town's maps");
  });

  it("a typed value the map never had isn't called a change to the map", async () => {
    const addr = q("street_address", "Street Address", { source: "property", from: "location", may_correct: true });
    vi.spyOn(apps, "getForm").mockResolvedValue({ ...FORM, sections: FORM.sections.map((s) => s.id === "site" ? { ...s, fields: [...s.fields, { ...addr, step: "your_lot" }] } : s) });
    vi.spyOn(apps, "getApplication").mockResolvedValue({ ...APP, property: { ...APP.property, facts: { map_lot: "004-036", location: null } },
                                                         answers: [...APP.answers, { field_id: "street_address", item_id: null, value: "12 Main St" }] });
    open();
    const site = await screen.findByRole("group", { name: "Site Information (existing)" });
    const row = within(site).getByText("Street Address").closest("[data-row]")!;
    expect(row).toHaveTextContent("12 Main St");
    expect(row).not.toHaveTextContent(/map/);
  });

  it("Still to answer links open the question's screen and come back", async () => {
    vi.spyOn(apps, "getApplication").mockResolvedValue({ ...APP, missing: [{ field_id: "lot_width", item_id: null }] });
    open();
    // The question as the resident was asked it leads; the form's own term follows, smaller.
    const link = await screen.findByRole("link", { name: /^Lot Width \(ft\)\?\s*Lot Width \(ft\)$/ });
    expect(link).toHaveAttribute("href", "/applications/abc/your_lot?screen=lot_width&return=review");
  });

  it("Change opens the question's screen and comes back; no Edit sheets", async () => {
    open();
    const site = await screen.findByRole("group", { name: "Site Information (existing)" });
    const change = within(site).getByRole("link", { name: "Change Lot Width (ft)?" });
    expect(change).toHaveAttribute("href", "/applications/abc/your_lot?screen=lot_width&return=review");
    expect(screen.queryByRole("button", { name: /^Edit / })).not.toBeInTheDocument();
    await userEvent.click(change);
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("a grouped screen's Change opens the group; a building's opens its own screen", async () => {
    const deed = sec("location", "Location", "your_lot", [q("deed_book", "Deed Book", { screen: "deed" }), q("deed_page", "Page", { screen: "deed" })],
                     { screens: [{ id: "deed", layout: null }] });
    const building = sec("main_mass", "Main Building Mass Details", "buildings", [q("width", "Width of Main Building Mass")],
                         { repeat: { kind: "building", add_label: "Add a building", min: 1, max: 20 } });
    vi.spyOn(apps, "getForm").mockResolvedValue({ ...FORM, steps: [...(FORM.steps ?? []), { id: "buildings", title: "Buildings" }],
                                                  sections: [deed, ...FORM.sections, building] });
    vi.spyOn(apps, "getApplication").mockResolvedValue({ ...APP, items: [{ id: "b1", kind: "building", position: 0 }] });
    open();
    expect(await screen.findByRole("link", { name: "Change Page?" })).toHaveAttribute("href", "/applications/abc/your_lot?screen=deed_book&return=review");
    expect(screen.getByRole("link", { name: "Change Width of Main Building Mass?" }))
      .toHaveAttribute("href", "/applications/abc/buildings?screen=width&item=b1&return=review");
  });

  it("an unanswered question says Still to answer", async () => {
    vi.spyOn(apps, "getApplication").mockResolvedValue({ ...APP, answers: APP.answers.filter((x) => x.field_id !== "applicant_name") });
    open();
    const applicant = await screen.findByRole("group", { name: "Applicant" });
    expect(within(applicant).getByText("Name?").closest("[data-row]")).toHaveTextContent("Still to answer");
  });

  it("says when everything is answered, and ends with what happens next", async () => {
    open();
    expect(await screen.findByText("Everything is answered.")).toBeInTheDocument();
    const next = screen.getByRole("group", { name: "What happens next" });
    expect(next).toHaveTextContent("Nothing has gone to the Town yet.");
    expect(next).toHaveTextContent("My applications");
  });

  it("no Submit button, and no verdict words", async () => {
    open();
    await screen.findByRole("group", { name: "Applicant" });
    expect(screen.queryByRole("button", { name: /Submit/ })).not.toBeInTheDocument();
    expect(screen.getByText(/Your application is saved/)).toBeInTheDocument();
    expect(document.body.textContent).not.toMatch(VERDICT);
  });
});
