import { render, screen, within } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { beforeEach, describe, expect, it, vi } from "vitest";
import AppShell, { rememberProject } from "./AppShell";
import * as layout from "./useWideLayout";

const shell = (props: Partial<Parameters<typeof AppShell>[0]> = {}) => render(
  <MemoryRouter initialEntries={["/projects/p1"]}>
    <AppShell title="My project" project="p1" {...props}><p>the page</p></AppShell>
  </MemoryRouter>,
);

beforeEach(() => localStorage.clear());

describe("the window", () => {
  it("on a desktop, a sidebar under the seal: Home, Project, Messages, You", () => {
    vi.spyOn(layout, "useWideLayout").mockReturnValue(true);
    shell({ saveState: "saved" });
    const nav = screen.getByRole("navigation", { name: "The app" });
    expect(within(nav).getAllByRole("link").map((l) => [l.textContent, l.getAttribute("href")])).toEqual([
      ["Home", "/"], ["Project", "/projects/p1"], ["Messages", "/messages"], ["You", "/you"]]);
    expect(screen.getByRole("img", { name: "Town of Newcastle seal" })).toBeInTheDocument();
    expect(screen.getByRole("status")).toHaveTextContent("Saved");
    expect(screen.getByRole("heading", { level: 1, name: "My project" })).toBeInTheDocument();
  });

  it("on a phone, a bottom tab bar with the same four, and ‹ Project over a card", () => {
    vi.spyOn(layout, "useWideLayout").mockReturnValue(false);
    shell({ back: { href: "/projects/p1", label: "Project" }, card: true });
    const nav = screen.getByRole("navigation", { name: "The app" });
    expect(within(nav).getAllByRole("link").map((l) => l.textContent)).toEqual(["Home", "Project", "Messages", "You"]);
    const [bar] = screen.getAllByRole("link", { name: "Project" }); // ‹ Project, above the card
    expect(bar).toHaveAttribute("href", "/projects/p1");
    expect(nav).not.toContainElement(bar);
    expect(screen.queryByRole("img", { name: "Town of Newcastle seal" })).not.toBeInTheDocument();
  });

  it("Project goes back to the project last opened", () => {
    vi.spyOn(layout, "useWideLayout").mockReturnValue(true);
    rememberProject("p7");
    shell({ project: null });
    expect(screen.getByRole("link", { name: "Project" })).toHaveAttribute("href", "/projects/p7");
  });
});
