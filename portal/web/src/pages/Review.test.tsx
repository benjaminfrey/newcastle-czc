import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes, useLocation } from "react-router";
import { beforeEach, describe, expect, it, vi } from "vitest";
import * as api from "../api";
import * as apps from "../applications";
import Review from "./Review";

vi.mock("../components/ParcelMap", () => ({ default: () => <div>map</div> }));

const f = (id: string, official: string, extra: Partial<apps.FormField> = {}): apps.FormField => ({
  id, official_label: official, source: "question", from: null, may_correct: false, label: `${official}?`, help: null,
  why: { cite: "8.2.a.2", text: "Applications must include all necessary information." },
  type: "text", unit: null, min: null, max: null, required: true, allow_unknown: false, show_if: null, options: [], ...extra,
});
const sec = (id: string, title: string, fields: apps.FormField[], extra: Partial<apps.FormSection> = {}): apps.FormSection =>
  ({ id, official_title: title, chapter: title, show_if: null, repeat: null, fields, ...extra });
const FORM: apps.FormDef = {
  key: "use_permit", version: 1, ruleset_key: "adopted-v1.0", official_title: "Use Permit Application",
  sections: [
    sec("site", "Site Information (existing)", [
      f("map_lot", "Map / Lot", { source: "property", from: "map_lot" }),
      f("zoning_district", "Zoning District", { source: "property", from: "districts" }),
      f("lot_width", "Lot Width (ft)", { type: "number", unit: "ft", allow_unknown: true }),
    ]),
    sec("applicant", "Applicant", [
      f("applicant_name", "Name"),
      f("applicant_email", "Email", { source: "account", from: "email" }),
      f("applicant_is_owner", "Applicant is the Property Owner", { type: "yesno" }),
    ]),
    sec("owner", "Property Owner (if different)", [f("owner_name", "Name")],
        { show_if: { eq: ["answers.applicant_is_owner", false] } }),
    sec("certification", "Certification", [f("signature", "Applicant Signature", { source: "at_submit" })]),
    sec("office", "Official Use Only", [f("date_received", "Date Received", { source: "staff" })]),
  ],
};
const APP: apps.AppState = {
  id: "abc", form_key: "use_permit", form_version: 1, ruleset_key: "adopted-v1.0", status: "draft", revision: 3,
  property: { source: "lookup", parcel_id: 229, map_lot: "004-036",
              facts: { map_lot: "004-036", districts: [{ code: "D2", name: "D2 - Neighborhood Residential" }] },
              parcels_as_of: "2026-10-15", verified: true, disputed: false, note: "" },
  items: [], notes: [], attachments: [], newer_version: false,
  answers: [{ field_id: "applicant_name", item_id: null, value: "Ada Lovelace" },
            { field_id: "applicant_is_owner", item_id: null, value: true },
            { field_id: "lot_width", item_id: null, value: { unknown: true } }],
  missing: [],
};
const VERDICT = /\b(approved|denied|compliant|meets|fails|violates)\b/i;

function Where() {
  const loc = useLocation();
  return <p>Wizard at {loc.search}</p>;
}

const renderPage = () =>
  render(
    <MemoryRouter initialEntries={["/applications/abc/review"]}>
      <Routes>
        <Route path="/applications/:id/review" element={<Review />} />
        <Route path="/applications/:id" element={<Where />} />
      </Routes>
    </MemoryRouter>,
  );

beforeEach(() => {
  vi.spyOn(apps, "getForm").mockResolvedValue(FORM);
  vi.spyOn(api, "getMe").mockResolvedValue({ email: "ada@example.com", role: "applicant" });
  vi.spyOn(api, "getUseGroups").mockResolvedValue([]);
});

const block = (title: string) => screen.getByRole("region", { name: title });

describe("Review", () => {
  it("prints official labels, not questions", async () => {
    vi.spyOn(apps, "getApplication").mockResolvedValue(APP);
    renderPage();
    const applicant = await screen.findByRole("region", { name: "Applicant" });
    expect(within(applicant).getByText("Name")).toBeInTheDocument();
    expect(within(applicant).getByText("Ada Lovelace")).toBeInTheDocument();
    expect(within(applicant).getByText("ada@example.com")).toBeInTheDocument();
    expect(within(applicant).getByText("Yes")).toBeInTheDocument();
    expect(screen.queryByText("Name?")).not.toBeInTheDocument();
    expect(screen.queryByRole("region", { name: "Property Owner (if different)" })).not.toBeInTheDocument();
    expect(within(block("Site Information (existing)")).getByText(/Not known yet/)).toBeInTheDocument();
    expect(within(block("Certification")).getByText("Signed when you submit")).toBeInTheDocument();
    expect(within(block("Official Use Only")).getByText("Office use")).toBeInTheDocument();
  });

  it("marks property facts and manual property", async () => {
    vi.spyOn(apps, "getApplication").mockResolvedValue(APP);
    const { unmount } = renderPage();
    const site = await screen.findByRole("region", { name: "Site Information (existing)" });
    expect(within(site).getByText("D2 - Neighborhood Residential")).toBeInTheDocument();
    expect(within(site).getAllByText(/from the Town's maps — staff confirm/).length).toBeGreaterThan(0);
    expect(screen.queryByText(/Property not verified/)).not.toBeInTheDocument();
    unmount();
    vi.spyOn(apps, "getApplication").mockResolvedValue({ ...APP, property: { ...APP.property, source: "manual", verified: false, parcel_id: null } });
    renderPage();
    expect(await screen.findByText(/Property not verified/)).toBeInTheDocument();
  });

  it("edit in place saves and re-renders", async () => {
    vi.spyOn(apps, "getApplication").mockResolvedValue(APP);
    const save = vi.spyOn(apps, "saveAnswers").mockResolvedValue({ revision: 4, missing: [] });
    renderPage();
    await userEvent.click(await screen.findByRole("button", { name: "Edit Applicant" }));
    const name = screen.getByLabelText("Name?");
    await userEvent.clear(name);
    await userEvent.type(name, "Ada King");
    await userEvent.click(screen.getByRole("button", { name: "Save Applicant" }));
    expect(save).toHaveBeenCalledWith("abc", 3, [{ field_id: "applicant_name", item_id: null, value: "Ada King" }]);
    expect(await within(block("Applicant")).findByText("Ada King")).toBeInTheDocument();
  });

  it("sends the applicant through only the new questions", async () => {
    vi.spyOn(apps, "getApplication").mockResolvedValue(APP);
    vi.spyOn(apps, "saveAnswers").mockResolvedValue({ revision: 4, missing: [{ field_id: "owner_name", item_id: null }] });
    renderPage();
    await userEvent.click(await screen.findByRole("button", { name: "Edit Applicant" }));
    await userEvent.click(within(block("Applicant")).getByRole("radio", { name: "No" }));
    await userEvent.click(screen.getByRole("button", { name: "Save Applicant" }));
    expect(await screen.findByText("A few new questions apply")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Answer them" }));
    expect(await screen.findByText(/Wizard at \?only=owner\.owner_name&s=owner\.owner_name&back=review/)).toBeInTheDocument();
  });

  it("Add more detail prints under its section", async () => {
    vi.spyOn(apps, "getApplication").mockResolvedValue(APP);
    const note = vi.spyOn(apps, "saveNote").mockResolvedValue({ revision: 4, missing: [] });
    renderPage();
    await userEvent.click(await screen.findByRole("button", { name: "Add more detail to Applicant" }));
    await userEvent.type(screen.getByLabelText("More detail for Applicant"), "Call after 5 pm.");
    await userEvent.click(screen.getByRole("button", { name: "Save detail for Applicant" }));
    expect(note).toHaveBeenCalledWith("abc", 3, "applicant", null, "Call after 5 pm.");
    expect(await within(block("Applicant")).findByText("Call after 5 pm.")).toBeInTheDocument();
  });

  it("lists what is still to answer", async () => {
    vi.spyOn(apps, "getApplication").mockResolvedValue({ ...APP, missing: [{ field_id: "lot_width", item_id: null }] });
    renderPage();
    const link = await screen.findByRole("link", { name: "Lot Width (ft)" });
    expect(link).toHaveAttribute("href", "/applications/abc?s=site.lot_width&back=review");
  });

  it("has no verdict words", async () => {
    vi.spyOn(apps, "getApplication").mockResolvedValue({ ...APP, missing: [{ field_id: "lot_width", item_id: null }] });
    renderPage();
    await screen.findByRole("region", { name: "Applicant" });
    expect(document.body.textContent).not.toMatch(VERDICT);
  });

  it("does not offer submitting yet", async () => {
    vi.spyOn(apps, "getApplication").mockResolvedValue(APP);
    renderPage();
    expect(await screen.findByRole("button", { name: /Submit/ })).toBeDisabled();
  });
});
