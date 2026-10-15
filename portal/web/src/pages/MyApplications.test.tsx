import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router";
import { describe, expect, it, vi } from "vitest";
import * as api from "../api";
import MyApplications from "./MyApplications";

const renderPage = () =>
  render(
    <MemoryRouter initialEntries={["/my-applications"]}>
      <Routes>
        <Route path="/my-applications" element={<MyApplications />} />
        <Route path="/signin" element={<p>Sign in page</p>} />
      </Routes>
    </MemoryRouter>,
  );

describe("MyApplications", () => {
  it("shows who is signed in and an empty list", async () => {
    vi.spyOn(api, "getMe").mockResolvedValue({ email: "a@example.com", role: "applicant" });
    renderPage();
    expect(await screen.findByText(/a@example.com/)).toBeInTheDocument();
    expect(screen.getByText(/You haven't started any applications yet/)).toBeInTheDocument();
  });

  it("sends a signed-out visitor to sign in", async () => {
    vi.spyOn(api, "getMe").mockResolvedValue(null);
    renderPage();
    expect(await screen.findByText("Sign in page")).toBeInTheDocument();
  });

  it("does not sign a person out when the server can't be reached", async () => {
    vi.spyOn(api, "getMe").mockResolvedValue("unavailable");
    renderPage();
    expect(await screen.findByText(/couldn't reach the Town's server/)).toBeInTheDocument();
    expect(screen.queryByText("Sign in page")).not.toBeInTheDocument();
  });
});
