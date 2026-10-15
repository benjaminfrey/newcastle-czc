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
    vi.spyOn(api, "verifyToken").mockResolvedValue(null);
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
});
