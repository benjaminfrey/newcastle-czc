import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes, useLocation } from "react-router";
import { afterEach, describe, expect, it, vi } from "vitest";
import AppShell from "./AppShell";
import type { ShellStep } from "./types";
import * as layout from "./useWideLayout";

const STEPS: ShellStep[] = [
  { id: "a", title: "Your lot", status: "done", unknowns: 0, href: "/x/a" },
  { id: "b", title: "About you", status: "todo", unknowns: 0, href: "/x/b" },
  { id: "c", title: "The work", status: "todo", unknowns: 0, href: "/x/c" },
];

function stubMotion(reduce: boolean) {
  vi.stubGlobal("matchMedia", vi.fn((q: string) => ({
    matches: q.includes("reduced-motion") ? reduce : q.includes("min-width") ? false : false,
    addEventListener: vi.fn(), removeEventListener: vi.fn(),
  })));
}

function Where() {
  return <p data-testid="where">{useLocation().pathname}</p>;
}

const shell = () => render(
  <MemoryRouter initialEntries={["/x/b"]}>
    <Routes><Route path="*" element={<>
      <AppShell steps={STEPS} currentId="b" formTitle="Use Permit" saveState="idle" rootHref="/x"><p>content</p></AppShell>
      <Where />
    </>} /></Routes>
  </MemoryRouter>,
);

afterEach(() => vi.unstubAllGlobals());

describe("motion and focus", () => {
  it("pushes the step in on a phone, and only fades when the device asks for less motion", () => {
    vi.spyOn(layout, "useWideLayout").mockReturnValue(false);
    stubMotion(false);
    const { unmount } = shell();
    expect(screen.getByText("content").closest("[data-pane]")).toHaveClass("pane-push");
    unmount();
    stubMotion(true);
    shell();
    expect(screen.getByText("content").closest("[data-pane]")).toHaveClass("pane-fade");
  });

  it("the live region announces the step", () => {
    vi.spyOn(layout, "useWideLayout").mockReturnValue(true);
    stubMotion(false);
    shell();
    expect(screen.getByTestId("step-announcer")).toHaveTextContent("Step 2 of 3: About you");
    expect(screen.getByTestId("step-announcer")).toHaveAttribute("aria-live", "polite");
  });

  it("a swipe in from the left edge goes back to the list", () => {
    vi.spyOn(layout, "useWideLayout").mockReturnValue(false);
    stubMotion(false);
    shell();
    const pane = screen.getByText("content").closest("[data-pane]")!;
    fireEvent.pointerDown(pane, { clientX: 8, clientY: 300, pointerType: "touch" });
    fireEvent.pointerMove(pane, { clientX: 140, clientY: 310, pointerType: "touch" });
    fireEvent.pointerUp(pane, { clientX: 140, clientY: 310, pointerType: "touch" });
    expect(screen.getByTestId("where")).toHaveTextContent("/x");
    expect(screen.getByTestId("where")).not.toHaveTextContent("/x/b");
  });

  it("a swipe that starts mid-screen does nothing", () => {
    vi.spyOn(layout, "useWideLayout").mockReturnValue(false);
    stubMotion(false);
    shell();
    const pane = screen.getByText("content").closest("[data-pane]")!;
    fireEvent.pointerDown(pane, { clientX: 200, clientY: 300, pointerType: "touch" });
    fireEvent.pointerUp(pane, { clientX: 380, clientY: 300, pointerType: "touch" });
    expect(screen.getByTestId("where")).toHaveTextContent("/x/b");
  });
});
