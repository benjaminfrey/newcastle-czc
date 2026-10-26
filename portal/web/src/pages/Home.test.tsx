import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router";
import { describe, expect, it, vi } from "vitest";
import * as api from "../api";
import * as apps from "../projects";
import { AppRoutes } from "../App";

const ME = { email: "a@example.com", role: "applicant", name: "Ada", phone: "207", mailing_address: "PO Box 1" };
const ROW = (over: Partial<apps.ProjectSummary>): apps.ProjectSummary => ({
  id: "p1", title: "A new building at Sheepscot Road", status: "draft", map_lot: "004-036",
  updated_at: "2026-10-25T12:00:00Z", submitted_at: null, first_part: "building", left: 2, ...over });

const at = (path: string) => render(<MemoryRouter initialEntries={[path]}><AppRoutes /></MemoryRouter>);

describe("Home", () => {
  it("signed out, every page shows the sign-in card", async () => {
    for (const path of ["/", "/new", "/projects/x", "/messages", "/you"]) {
      vi.spyOn(api, "getMe").mockResolvedValue(null);
      const { unmount } = at(path);
      expect(await screen.findByRole("button", { name: "Email me a sign-in link" })).toBeInTheDocument();
      expect(screen.getByText("No password. We'll email you a link.")).toBeInTheDocument();
      expect(screen.getByRole("heading", { name: "Town of Newcastle — Permits" })).toBeInTheDocument();
      expect(screen.queryByText(/Do I need a permit/)).not.toBeInTheDocument();
      unmount();
      vi.restoreAllMocks();
    }
  });

  it("signed in, it offers Start, Continue and the list, newest first, with pills", async () => {
    vi.spyOn(api, "getMe").mockResolvedValue(ME);
    vi.spyOn(apps, "listProjects").mockResolvedValue([
      ROW({ id: "p2", title: "Yoga studio", status: "submitted", submitted_at: "2026-10-03T12:00:00Z", first_part: "use", left: 0 }),
      ROW({}),
    ]);
    at("/");
    expect(await screen.findByRole("link", { name: "Start a new application" })).toHaveAttribute("href", "/new");
    expect(screen.getByRole("button", { name: "Continue an application" })).toBeInTheDocument();
    const list = await screen.findByRole("list", { name: "Your applications" });
    const rows = within(list).getAllByRole("link");
    expect(rows.map((r) => r.getAttribute("href"))).toEqual(["/projects/p2", "/projects/p1"]);
    expect(rows[0]).toHaveTextContent("Yoga studio");
    expect(rows[0]).toHaveTextContent("Map 4, Lot 36 · sent October 3");
    expect(rows[0]).toHaveTextContent("Sent");
    expect(rows[1]).toHaveTextContent("Map 4, Lot 36 · 2 things left");
    expect(rows[1]).toHaveTextContent("Draft");
  });

  it("Continue opens the latest project in progress, or says there is none", async () => {
    vi.spyOn(api, "getMe").mockResolvedValue(ME);
    vi.spyOn(apps, "listProjects").mockResolvedValue([ROW({ id: "p9", status: "locked" }), ROW({ id: "p1" })]);
    render(<MemoryRouter initialEntries={["/"]}><Routes>
      <Route path="/projects/:id/*" element={<p>Project page</p>} />
      <Route path="*" element={<AppRoutes />} />
    </Routes></MemoryRouter>);
    await userEvent.click(await screen.findByRole("button", { name: "Continue an application" }));
    expect(await screen.findByText("Project page")).toBeInTheDocument();
  });

  it("Continue with nothing in progress says so", async () => {
    vi.spyOn(api, "getMe").mockResolvedValue(ME);
    vi.spyOn(apps, "listProjects").mockResolvedValue([ROW({ status: "locked" })]);
    at("/");
    await userEvent.click(await screen.findByRole("button", { name: "Continue an application" }));
    expect(await screen.findByText("You have no application in progress.")).toBeInTheDocument();
  });

  it("old addresses go Home", async () => {
    vi.spyOn(api, "getMe").mockResolvedValue(ME);
    vi.spyOn(apps, "listProjects").mockResolvedValue([]);
    for (const path of ["/start", "/start/needs", "/my-applications", "/apply/use_permit", "/applications/abc/about_you"]) {
      const { unmount } = at(path);
      expect(await screen.findByRole("link", { name: "Start a new application" })).toBeInTheDocument();
      unmount();
    }
  });
});
