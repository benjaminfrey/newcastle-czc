import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router";
import { beforeEach, describe, expect, it, vi } from "vitest";
import * as api from "../api";
import * as apps from "../applications";
import Wizard from "./Wizard";

vi.mock("../components/ParcelMap", () => ({ default: () => <div>map</div> }));

const q = (id: string, label: string, extra: Partial<apps.FormField> = {}): apps.FormField => ({
  id, official_label: id, source: "question", from: null, may_correct: false, label, help: null,
  why: { cite: "8.2.a.2", text: "Applications must include all necessary information." },
  type: "text", unit: null, min: null, max: null, required: true, allow_unknown: false, show_if: null, options: [], ...extra,
});
const FORM: apps.FormDef = {
  key: "use_permit", version: 1, ruleset_key: "adopted-v1.0", official_title: "Use Permit Application",
  sections: [{ id: "applicant", official_title: "Applicant", chapter: "Who's applying", show_if: null, repeat: null, fields: [
    q("applicant_name", "What is your full name?"),
    q("lot_width", "How wide is your lot, in feet?", { type: "number", unit: "ft", min: 0, max: 50000, allow_unknown: true }),
    q("is_owner", "Do you own the property?", { type: "yesno" }),
  ] }],
};
const APP: apps.AppState = {
  id: "abc", form_key: "use_permit", form_version: 1, ruleset_key: "adopted-v1.0", status: "draft", revision: 3,
  property: { source: "lookup", parcel_id: 229, map_lot: "004-036", facts: {}, parcels_as_of: "2026-10-15", verified: true, disputed: false, note: "" },
  items: [], answers: [], notes: [], attachments: [], missing: [], newer_version: false,
};

const renderAt = (path = "/applications/abc") =>
  render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route path="/applications/:id" element={<Wizard />} />
        <Route path="/applications/:id/review" element={<p>Review page</p>} />
        <Route path="/signin" element={<p>Sign in page</p>} />
      </Routes>
    </MemoryRouter>,
  );

beforeEach(() => {
  vi.spyOn(apps, "getForm").mockResolvedValue(FORM);
  vi.spyOn(api, "getUseGroups").mockResolvedValue([]);
});

describe("Wizard", () => {
  it("saves on Next and advances", async () => {
    vi.spyOn(apps, "getApplication").mockResolvedValue(APP);
    const save = vi.spyOn(apps, "saveAnswers").mockResolvedValue({ revision: 4, missing: [] });
    renderAt();
    await userEvent.type(await screen.findByLabelText("What is your full name?"), "Ada Lovelace");
    await userEvent.click(screen.getByRole("button", { name: "Next" }));
    expect(save).toHaveBeenCalledWith("abc", 3, [{ field_id: "applicant_name", item_id: null, value: "Ada Lovelace" }]);
    expect(await screen.findByLabelText("How wide is your lot, in feet?")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Who's applying" })).toBeInTheDocument();
  });

  it("keeps the answer when the save fails", async () => {
    vi.spyOn(apps, "getApplication").mockResolvedValue(APP);
    vi.spyOn(apps, "saveAnswers").mockResolvedValue("unavailable");
    renderAt();
    await userEvent.type(await screen.findByLabelText("What is your full name?"), "Ada");
    await userEvent.click(screen.getByRole("button", { name: "Next" }));
    expect(await screen.findByText(/couldn't save that/)).toBeInTheDocument();
    expect(screen.getByLabelText("What is your full name?")).toHaveValue("Ada");
  });

  it("warns when the application changed in another tab", async () => {
    const latest = { ...APP, revision: 5, answers: [{ field_id: "applicant_name", item_id: null, value: "From the other tab" }] };
    const get = vi.spyOn(apps, "getApplication").mockResolvedValueOnce(APP).mockResolvedValueOnce(latest);
    const save = vi.spyOn(apps, "saveAnswers").mockResolvedValueOnce({ conflict: 5 }).mockResolvedValueOnce({ revision: 6, missing: [] });
    renderAt();
    await userEvent.type(await screen.findByLabelText("What is your full name?"), "Mine");
    await userEvent.click(screen.getByRole("button", { name: "Next" }));
    expect(await screen.findByText(/changed in another tab or window/)).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Keep mine" }));
    expect(save).toHaveBeenLastCalledWith("abc", 5, [{ field_id: "applicant_name", item_id: null, value: "Mine" }]);
    expect(await screen.findByLabelText("How wide is your lot, in feet?")).toBeInTheDocument();
    expect(get).toHaveBeenCalledTimes(1);
  });

  it("loads the latest when asked", async () => {
    const latest = { ...APP, revision: 5, answers: [{ field_id: "applicant_name", item_id: null, value: "From the other tab" }] };
    vi.spyOn(apps, "getApplication").mockResolvedValueOnce(APP).mockResolvedValueOnce(latest);
    vi.spyOn(apps, "saveAnswers").mockResolvedValueOnce({ conflict: 5 });
    renderAt();
    await userEvent.type(await screen.findByLabelText("What is your full name?"), "Mine");
    await userEvent.click(screen.getByRole("button", { name: "Next" }));
    await userEvent.click(await screen.findByRole("button", { name: "Load the latest" }));
    expect(await screen.findByDisplayValue("From the other tab")).toBeInTheDocument();
  });

  it("offers I don't know yet only where allowed", async () => {
    vi.spyOn(apps, "getApplication").mockResolvedValue(APP);
    const save = vi.spyOn(apps, "saveAnswers").mockResolvedValue({ revision: 4, missing: [] });
    renderAt();
    await screen.findByLabelText("What is your full name?");
    expect(screen.queryByRole("button", { name: "I don't know yet" })).not.toBeInTheDocument();
    renderAt("/applications/abc?s=applicant.lot_width");
    await userEvent.click(await screen.findByRole("button", { name: "I don't know yet" }));
    expect(save).toHaveBeenCalledWith("abc", 3, [{ field_id: "lot_width", item_id: null, value: { unknown: true } }]);
  });

  it("rejects a number out of range with a plain message", async () => {
    vi.spyOn(apps, "getApplication").mockResolvedValue(APP);
    const save = vi.spyOn(apps, "saveAnswers");
    renderAt("/applications/abc?s=applicant.lot_width");
    await userEvent.type(await screen.findByLabelText("How wide is your lot, in feet?"), "-5");
    await userEvent.click(screen.getByRole("button", { name: "Next" }));
    expect(await screen.findByText("Please enter a number from 0 to 50000 ft.")).toBeInTheDocument();
    expect(save).not.toHaveBeenCalled();
  });

  it("reload resumes at the same screen", async () => {
    vi.spyOn(apps, "getApplication").mockResolvedValue({ ...APP, answers: [{ field_id: "is_owner", item_id: null, value: true }] });
    renderAt("/applications/abc?s=applicant.is_owner");
    expect(await screen.findByRole("radio", { name: "Yes" })).toBeChecked();
  });

  it("goes to review after the last question", async () => {
    vi.spyOn(apps, "getApplication").mockResolvedValue(APP);
    vi.spyOn(apps, "saveAnswers").mockResolvedValue({ revision: 4, missing: [] });
    renderAt("/applications/abc?s=applicant.is_owner");
    await userEvent.click(await screen.findByRole("radio", { name: "No" }));
    await userEvent.click(screen.getByRole("button", { name: "Next" }));
    expect(await screen.findByText("Review page")).toBeInTheDocument();
  });

  it("shows why we ask", async () => {
    vi.spyOn(apps, "getApplication").mockResolvedValue(APP);
    renderAt();
    await userEvent.click(await screen.findByRole("button", { name: /Why we ask/ }));
    expect(await screen.findByText("Art. 8 §2.a.2")).toBeVisible();
  });
});
