import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes, useLocation } from "react-router";
import { describe, expect, it } from "vitest";
import StepSidebar from "./StepSidebar";
import type { ShellStep } from "./types";

const STEPS: ShellStep[] = [
  { id: "a", title: "Your lot", status: "done", unknowns: 0, href: "/s/a" },
  { id: "b", title: "About you", status: "done", unknowns: 2, href: "/s/b" },
  { id: "c", title: "Buildings", status: "todo", unknowns: 0, href: "/s/c",
    children: [{ id: "i1", title: "Building 1: House", status: "started", unknowns: 0, href: "/s/c?item=i1" }] },
];

function Where() {
  return <p>at {useLocation().pathname}</p>;
}

const renderBar = () =>
  render(
    <MemoryRouter initialEntries={["/s/a"]}>
      <StepSidebar steps={STEPS} currentId="a" />
      <Routes><Route path="*" element={<Where />} /></Routes>
    </MemoryRouter>,
  );

describe("StepSidebar", () => {
  it("glyph names are announced", () => {
    renderBar();
    expect(screen.getByRole("link", { name: "Your lot, Done" })).toHaveAttribute("aria-current", "step");
    expect(screen.getByRole("link", { name: "About you, Done, with 2 answers to follow up" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Buildings, Not started" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Building 1: House, Started" })).toBeInTheDocument();
  });

  it("shows the Town seal", () => {
    renderBar();
    expect(screen.getByRole("img", { name: "Town of Newcastle seal" })).toHaveAttribute("src", "/town-seal.png");
  });

  it("arrow keys move and Enter opens", async () => {
    renderBar();
    screen.getByRole("link", { name: /Your lot/ }).focus();
    await userEvent.keyboard("{ArrowDown}");
    expect(screen.getByRole("link", { name: /About you/ })).toHaveFocus();
    await userEvent.keyboard("{Enter}");
    expect(screen.getByText("at /s/b")).toBeInTheDocument();
  });
});
