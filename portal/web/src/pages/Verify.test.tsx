import { render, screen } from "@testing-library/react";
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
      </Routes>
    </MemoryRouter>,
  );
};

describe("Verify", () => {
  it("redeems the token from the URL fragment with a POST and moves on", async () => {
    const spy = vi.spyOn(api, "verifyToken").mockResolvedValue({ email: "a@example.com", role: "applicant" });
    renderAt("#token=abc123");
    expect(await screen.findByText("My applications page")).toBeInTheDocument();
    expect(spy).toHaveBeenCalledWith("abc123");
    expect(window.location.hash).toBe("");
  });

  it("explains a used or expired link and offers a new one", async () => {
    vi.spyOn(api, "verifyToken").mockResolvedValue(null);
    renderAt("#token=old");
    expect(await screen.findByText(/expired or was already used/)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Get a new link" })).toHaveAttribute("href", "/signin");
  });

  it("handles a missing token without calling the API", async () => {
    const spy = vi.spyOn(api, "verifyToken");
    renderAt("");
    expect(await screen.findByText(/expired or was already used/)).toBeInTheDocument();
    expect(spy).not.toHaveBeenCalled();
  });
});
