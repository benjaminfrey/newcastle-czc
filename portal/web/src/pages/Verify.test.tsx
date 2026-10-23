import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router";
import { describe, expect, it, vi } from "vitest";
import * as api from "../api";
import Verify from "./Verify";

const renderAt = (hash: string) => {
  window.location.hash = hash;
  return render(
    <MemoryRouter initialEntries={["/signin/verify"]}>
      <Routes>
        <Route path="/signin/verify" element={<Verify />} />
        <Route path="/my-applications" element={<p>My applications page</p>} />
        <Route path="/apply/:formKey" element={<p>Apply page</p>} />
      </Routes>
    </MemoryRouter>,
  );
};

describe("Verify", () => {
  it("does not use the link until the person presses Sign me in", async () => {
    // Mail scanners that run JavaScript open links too; only a person clicks.
    const spy = vi.spyOn(api, "verifyToken").mockResolvedValue({ email: "a@example.com", role: "applicant" });
    renderAt("#token=abc123");
    expect(await screen.findByRole("button", { name: "Sign me in" })).toBeInTheDocument();
    expect(spy).not.toHaveBeenCalled();
    expect(window.location.hash).toBe("");
    await userEvent.click(screen.getByRole("button", { name: "Sign me in" }));
    expect(await screen.findByText("My applications page")).toBeInTheDocument();
    expect(spy).toHaveBeenCalledWith("abc123");
  });

  it("explains a used or expired link and offers a new one", async () => {
    vi.spyOn(api, "verifyToken").mockResolvedValue("invalid");
    vi.spyOn(api, "getMe").mockResolvedValue(null);
    renderAt("#token=old");
    await userEvent.click(await screen.findByRole("button", { name: "Sign me in" }));
    expect(await screen.findByText(/expired or was already used/)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Get a new link" })).toHaveAttribute("href", "/signin");
  });

  it("handles a missing token without calling the API", async () => {
    const spy = vi.spyOn(api, "verifyToken");
    renderAt("");
    expect(await screen.findByText(/expired or was already used/)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Sign me in" })).not.toBeInTheDocument();
    expect(spy).not.toHaveBeenCalled();
  });

  it("keeps the link usable when the server can't be reached", async () => {
    const spy = vi.spyOn(api, "verifyToken").mockResolvedValue("unavailable");
    renderAt("#token=abc123");
    await userEvent.click(await screen.findByRole("button", { name: "Sign me in" }));
    expect(await screen.findByText(/couldn't reach the Town's server/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Sign me in" })).toBeEnabled();
    spy.mockResolvedValue({ email: "a@example.com", role: "applicant" });
    await userEvent.click(screen.getByRole("button", { name: "Sign me in" }));
    expect(await screen.findByText("My applications page")).toBeInTheDocument();
    expect(spy).toHaveBeenLastCalledWith("abc123");
  });

  it("goes on to My applications when the link was already used in another tab", async () => {
    vi.spyOn(api, "verifyToken").mockResolvedValue("invalid");
    vi.spyOn(api, "getMe").mockResolvedValue({ email: "a@example.com", role: "applicant" });
    renderAt("#token=used");
    await userEvent.click(await screen.findByRole("button", { name: "Sign me in" }));
    expect(await screen.findByText("My applications page")).toBeInTheDocument();
  });

  it("resumes a pending start", async () => {
    localStorage.setItem("portal.pendingStart", JSON.stringify({ formKey: "entrance_permit", property: null, useKey: null }));
    vi.spyOn(api, "verifyToken").mockResolvedValue({ email: "a@example.com", role: "applicant" });
    renderAt("#token=abc123");
    await userEvent.click(await screen.findByRole("button", { name: "Sign me in" }));
    expect(await screen.findByText("Apply page")).toBeInTheDocument();
    localStorage.clear();
  });
});
