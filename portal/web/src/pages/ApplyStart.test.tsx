import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router";
import { beforeEach, describe, expect, it, vi } from "vitest";
import * as api from "../api";
import * as apps from "../applications";
import { peekPendingStart } from "../pendingStart";
import { saveProperty } from "../property";
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
    expect(peekPendingStart()).toEqual({ formKey: "use_permit", property: PROPERTY, useKey: null });
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
                                       disputed: false, note: "", use_key: null });
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
