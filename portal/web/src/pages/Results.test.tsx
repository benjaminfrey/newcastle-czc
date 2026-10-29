import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { beforeEach, describe, expect, it, vi } from "vitest";
import * as api from "../api";
import { saveProperty } from "../property";
import { saveAnswers } from "../screener";
import Results from "./Results";

const USE_PERMIT: api.Outcome = {
  application: "use_permit", code_name: "Use Permit", plain: "Permission to start a new use.",
  reviewer: "Code Enforcement Officer", certainty: "needed", district: "D1", district_name: "Rural (D1)", in_portal: true,
  days: [{ label: "Use permit decision", days: 30, basis: "calendar", cite: "8.15.d", when: null }],
  why: { cite: "8.15.b.1", text: "Applies to all applications seeking to engage in a new Use or a change of Use.", ruling: null },
};
const SPECIAL: api.Outcome = { ...USE_PERMIT, application: "special_permit", code_name: "Special Permit",
  reviewer: "Planning Board", in_portal: false, days: [], why: { cite: "8.18.b.1", text: "Special permits may only be requested as specifically authorized.", ruling: null } };
const RESULT: api.ScreenerResult = {
  outcomes: [USE_PERMIT, SPECIAL], notes: [{ kind: "note", text: "Measure the floor area.", cite: "8.10.b.1" }],
  not_listed: [], town_only: false, drafts_used: [],
};
const VERDICT_WORDS = ["approved", "denied", "compliant", "meets", "fails", "violates"];

const renderPage = () => render(<MemoryRouter><Results /></MemoryRouter>);

beforeEach(() => {
  sessionStorage.clear();
  saveAnswers({ project: ["use"], use_key: "restaurant_cafe",
                building: { kind: null, gross_floor_area_sf: null, total_floor_area_sf: null, parking_spaces: null, new_dwelling_units: null, homes_added_last_5_years: null }, division: { lots_after: null, divided_last_5_years: null } });
  saveProperty({ source: "lookup", parcel_id: 229, map_lot: "004-036", district_code: "D1", district_codes: ["D1"],
                 on_state_highway: false, disputed: false, note: "", as_of: "2026-10-15" });
});

describe("Results", () => {
  it("sends the answers and the property's districts to the screener", async () => {
    const spy = vi.spyOn(api, "runScreener").mockResolvedValue(RESULT);
    renderPage();
    await screen.findByText("Use Permit");
    expect(spy).toHaveBeenCalledWith(expect.objectContaining({
      use_key: "restaurant_cafe", property: { district_codes: ["D1"], on_state_highway: false, civic: false } }));
  });

  it("lists each application with reviewer and time limit, with no Code citation or why", async () => {
    vi.spyOn(api, "runScreener").mockResolvedValue(RESULT);
    renderPage();
    expect(await screen.findByText("Use Permit")).toBeInTheDocument();
    expect(screen.getAllByText(/Code Enforcement Officer/).length).toBeGreaterThan(0);
    expect(screen.getByText(/30 days/)).toBeInTheDocument();
    expect(screen.queryByText(/Art\. \d/)).not.toBeInTheDocument();
    expect(screen.getByText("Measure the floor area.")).toBeInTheDocument(); // a note in plain words stays
    expect(screen.queryByText(/Why the Code/)).not.toBeInTheDocument();
    expect(screen.getAllByText(/the Rural \(D1\) district/).length).toBeGreaterThan(0);
  });

  it("marks the ones you can apply for here", async () => {
    vi.spyOn(api, "runScreener").mockResolvedValue(RESULT);
    renderPage();
    expect(await screen.findByText("You can apply here.")).toBeInTheDocument();
    expect(screen.getByText("Apply through the Town Office.")).toBeInTheDocument();
  });

  it("explains a use the Code doesn't list in the district", async () => {
    vi.spyOn(api, "runScreener").mockResolvedValue({ ...RESULT, outcomes: [], not_listed: [
      { district: "D2", use: "gas_station", cite: "8.19.b.1",
        text: "The Code doesn't list this use in the Neighborhood Residential (D2) district. A variance can't be granted for a use (Art. 8 §19.b)." }] });
    renderPage();
    expect(await screen.findByText(/doesn't list this use/)).toBeInTheDocument();
  });

  it("shows the fee line", async () => {
    vi.spyOn(api, "runScreener").mockResolvedValue(RESULT);
    renderPage();
    expect((await screen.findAllByText(/Set by the Town's fee schedule/)).length).toBeGreaterThan(0);
  });

  it("says when answers aren't approved yet", async () => {
    vi.spyOn(api, "runScreener").mockResolvedValue("not_approved");
    renderPage();
    expect(await screen.findByText("This tool isn't ready yet. Please contact the Town Office.")).toBeInTheDocument();
  });

  it("shows only the Civic explanation on Civic land", async () => {
    vi.spyOn(api, "runScreener").mockResolvedValue({ ...RESULT, outcomes: [], notes: [], town_only: true });
    renderPage();
    expect(await screen.findByText(/Only the Town builds on Civic land/)).toBeInTheDocument();
    expect(screen.queryByText("Use Permit")).not.toBeInTheDocument();
  });

  it("contains no verdict words", async () => {
    vi.spyOn(api, "runScreener").mockResolvedValue(RESULT);
    const { container } = renderPage();
    await screen.findByText("Use Permit");
    const text = container.textContent!.toLowerCase();
    for (const w of VERDICT_WORDS) expect(text).not.toContain(w);
  });

  it("says 'you may need' when the answer isn't certain", async () => {
    vi.spyOn(api, "runScreener").mockResolvedValue({ ...RESULT, outcomes: [{ ...USE_PERMIT, certainty: "may_need" }] });
    renderPage();
    expect(await screen.findByRole("heading", { name: /^You may need a Use Permit/ })).toBeInTheDocument();
    expect(screen.queryByText("You may need this.")).not.toBeInTheDocument(); // the title says it
  });

  it("the answer, then reviewer, fees and lot, with no talk of the Code", async () => {
    vi.spyOn(api, "runScreener").mockResolvedValue({ ...RESULT, outcomes: [USE_PERMIT] });
    renderPage();
    const block = await screen.findByRole("region", { name: "Use Permit" });
    expect(block).toHaveTextContent("Reviewed by");
    expect(block).toHaveTextContent("Fees");
    expect(block).toHaveTextContent("Your lot");
    expect(document.body.textContent).not.toMatch(/The Code calls for this|Time the Code gives/);
  });

  it("never says nothing is needed beside a caveat", async () => {
    vi.spyOn(api, "runScreener").mockResolvedValue({ ...RESULT, outcomes: [],
      notes: [{ kind: "contact_town", text: "Talk to the Code Enforcement Officer.", cite: "8.9.c.1" }] });
    renderPage();
    expect(await screen.findByText("Talk to the Code Enforcement Officer.")).toBeInTheDocument();
    expect(screen.queryByText(/doesn't call for any/)).not.toBeInTheDocument();
  });

  it("points back to the answers when they can't be used", async () => {
    vi.spyOn(api, "runScreener").mockResolvedValue("invalid");
    renderPage();
    expect(await screen.findByText(/Some of your answers couldn't be used/)).toBeInTheDocument();
  });

  it("labels the Planning Board's timeline as conditional", async () => {
    vi.spyOn(api, "runScreener").mockResolvedValue({ ...RESULT, outcomes: [{ ...USE_PERMIT,
      application: "large_project_plan", code_name: "Large Project Plan",
      days: [{ label: "Large Project Plan decision (CEO)", days: 45, basis: "calendar", cite: "8.11.d.3", when: null },
             { label: "Planning Board hearing", days: 30, basis: "calendar", cite: "8.11.d.4.a", when: "if sent to the Planning Board" }] }] });
    renderPage();
    expect(await screen.findByText(/30 days, if sent to the Planning Board/)).toBeInTheDocument();
  });

  it("doesn't show the Code's why, nor a ruling under it", async () => {
    vi.spyOn(api, "runScreener").mockResolvedValue({ ...RESULT, outcomes: [{ ...USE_PERMIT,
      why: { ...USE_PERMIT.why, ruling: "Any home is the Residence use. (Ruling of Ben Frey, Planning Board chair, 2026-10-18.)" } }] });
    renderPage();
    expect(await screen.findByText("Use Permit")).toBeInTheDocument();
    expect(screen.queryByText(/Ruling of Ben Frey/)).not.toBeInTheDocument();
  });

  it("offers Start only for the applications this site takes", async () => {
    vi.spyOn(api, "runScreener").mockResolvedValue(RESULT);
    renderPage();
    expect(await screen.findByRole("button", { name: "Start this application: Use Permit" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Start this application: Special Permit/ })).not.toBeInTheDocument();
  });
});
