import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes, useLocation } from "react-router";
import { beforeEach, describe, expect, it, vi } from "vitest";
import * as api from "../api";
import * as apps from "../applications";
import { peekPendingStart } from "../pendingStart";
import { saveProperty } from "../property";
import { saveAnswers } from "../screener";
import ApplyStart from "./ApplyStart";

const PROPERTY = { source: "lookup" as const, parcel_id: 229, map_lot: "004-036", district_code: "D2",
                   district_codes: ["D2"], on_state_highway: false, disputed: false, note: "", as_of: "2026-10-15" };

const renderAt = (path = "/apply/use_permit") =>
  render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route path="/apply/:formKey" element={<ApplyStart />} />
        <Route path="/signin" element={<p>Sign in page</p>} />
        <Route path="/start/property" element={<p>Where page</p>} />
        <Route path="/applications/:id" element={<p>Wizard page</p>} />
      </Routes>
    </MemoryRouter>,
  );

function Search() {
  return <p data-testid="search">{useLocation().search}</p>;
}

beforeEach(() => {
  localStorage.clear();
  sessionStorage.clear();
});

describe("ApplyStart", () => {
  it("sends a signed-out visitor to sign in with the start saved", async () => {
    saveProperty(PROPERTY);
    vi.spyOn(api, "getMe").mockResolvedValue(null);
    renderAt();
    expect(await screen.findByText("Sign in page")).toBeInTheDocument();
    expect(peekPendingStart()).toEqual({ formKey: "use_permit", property: PROPERTY, useKey: null, carry: null });
  });

  it("asks for the property first", async () => {
    vi.spyOn(api, "getMe").mockResolvedValue({ email: "a@example.com", role: "applicant" });
    renderAt();
    expect(await screen.findByText("Where page")).toBeInTheDocument();
  });

  it("creates the application and opens it", async () => {
    saveProperty(PROPERTY);
    vi.spyOn(api, "getMe").mockResolvedValue({ email: "a@example.com", role: "applicant" });
    const spy = vi.spyOn(apps, "createApplication").mockResolvedValue({ id: "abc" });
    renderAt();
    expect(await screen.findByText("Wizard page")).toBeInTheDocument();
    expect(spy).toHaveBeenCalledWith({ form_key: "use_permit", property: { source: "lookup", parcel_id: 229 },
                                       disputed: false, note: "", use_key: null, carry: null });
  });

  it("opens the first question, on a phone too", async () => {
    saveProperty(PROPERTY);
    vi.spyOn(api, "getMe").mockResolvedValue({ email: "a@example.com", role: "applicant" });
    vi.spyOn(apps, "createApplication").mockResolvedValue({ id: "abc" });
    render(
      <MemoryRouter initialEntries={["/apply/use_permit"]}>
        <Routes>
          <Route path="/apply/:formKey" element={<ApplyStart />} />
          <Route path="/applications/:id" element={<Search />} />
        </Routes>
      </MemoryRouter>,
    );
    expect(await screen.findByTestId("search")).toHaveTextContent("?start=1");
  });

  it("a screener answer the form can't take starts without it, rather than not at all", async () => {
    saveProperty(PROPERTY);
    saveAnswers({ project: ["build"], use_key: null, division: { lots_after: null, divided_last_5_years: null },
                  building: { kind: "new", gross_floor_area_sf: 1200, total_floor_area_sf: null, parking_spaces: null,
                              new_dwelling_units: 600, homes_added_last_5_years: null } });
    vi.spyOn(api, "getMe").mockResolvedValue({ email: "a@example.com", role: "applicant" });
    const spy = vi.spyOn(apps, "createApplication").mockImplementation(async (b) => (b.carry ? "invalid" : { id: "abc" }));
    renderAt("/apply/small_project_plan");
    expect(await screen.findByText("Wizard page")).toBeInTheDocument();
    expect(spy).toHaveBeenCalledTimes(2);
    expect(spy.mock.calls[1][0].carry).toBeNull();
  });

  it("sends the screener's carry: the kind of work, its floor area and new homes", async () => {
    saveProperty(PROPERTY);
    saveAnswers({ project: ["build"], use_key: null, division: { lots_after: null, divided_last_5_years: null },
                  building: { kind: "new", gross_floor_area_sf: 1200, total_floor_area_sf: null, parking_spaces: null,
                              new_dwelling_units: 1, homes_added_last_5_years: null } });
    vi.spyOn(api, "getMe").mockResolvedValue({ email: "a@example.com", role: "applicant" });
    const spy = vi.spyOn(apps, "createApplication").mockResolvedValue({ id: "abc" });
    renderAt("/apply/small_project_plan");
    expect(await screen.findByText("Wizard page")).toBeInTheDocument();
    expect(spy.mock.calls[0][0].carry).toEqual({ work_kind: "new", floor_area: 1200, new_homes: 1 });
  });

  it("uses the pending start after signing in, in a new tab", async () => {
    localStorage.setItem("portal.pendingStart", JSON.stringify({ formKey: "use_permit", property: PROPERTY, useKey: "bar_tavern" }));
    vi.spyOn(api, "getMe").mockResolvedValue({ email: "a@example.com", role: "applicant" });
    const spy = vi.spyOn(apps, "createApplication").mockResolvedValue({ id: "abc" });
    renderAt();
    expect(await screen.findByText("Wizard page")).toBeInTheDocument();
    expect(spy.mock.calls[0][0].use_key).toBe("bar_tavern");
    expect(peekPendingStart()).toBeNull();
  });

  it("falls back to manual property when lookup is down", async () => {
    saveProperty(PROPERTY);
    vi.spyOn(api, "getMe").mockResolvedValue({ email: "a@example.com", role: "applicant" });
    vi.spyOn(apps, "createApplication").mockResolvedValue("property_unavailable");
    renderAt();
    const link = await screen.findByRole("link", { name: /Enter your property yourself/ });
    expect(link).toHaveAttribute("href", "/start/property?manual=1&next=%2Fapply%2Fuse_permit");
  });

  it("says when the form isn't ready", async () => {
    saveProperty(PROPERTY);
    vi.spyOn(api, "getMe").mockResolvedValue({ email: "a@example.com", role: "applicant" });
    vi.spyOn(apps, "createApplication").mockResolvedValue("not_approved");
    renderAt();
    expect(await screen.findByText(/isn't ready yet/)).toBeInTheDocument();
  });

  it("refuses a form this site doesn't offer", async () => {
    vi.spyOn(api, "getMe").mockResolvedValue({ email: "a@example.com", role: "applicant" });
    renderAt("/apply/special_permit");
    expect(await screen.findByText(/isn't one you can apply for here/)).toBeInTheDocument();
  });
});
