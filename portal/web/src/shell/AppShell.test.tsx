import { fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { beforeEach, describe, expect, it, vi } from "vitest";
import AppShell from "./AppShell";
import type { ShellStep } from "./types";
import * as layout from "./useWideLayout";

const STEPS: ShellStep[] = [
  { id: "project", title: "Your project", status: "done", unknowns: 0, href: "/x/project" },
  { id: "about_you", title: "About you", status: "started", unknowns: 1, href: "/x/about_you" },
  { id: "buildings", title: "Buildings", status: "todo", unknowns: 0, href: "/x/buildings" },
];

const renderShell = (props: Partial<Parameters<typeof AppShell>[0]> = {}) =>
  render(
    <MemoryRouter>
      <AppShell steps={STEPS} currentId="about_you" formTitle="Small Project Plan" saveState="idle"
                onDone={vi.fn()} rootHref="/x" {...props}>
        <label>Your name<input name="n" /></label>
      </AppShell>
    </MemoryRouter>,
  );

beforeEach(() => vi.restoreAllMocks());

describe("AppShell, wide", () => {
  beforeEach(() => vi.spyOn(layout, "useWideLayout").mockReturnValue(true));

  it("shows sidebar, toolbar and Back/Continue at the bottom right", () => {
    renderShell({ actions: { back: vi.fn(), onContinue: vi.fn() } });
    expect(screen.getByRole("navigation", { name: "Steps" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { level: 1, name: "About you" })).toBeInTheDocument();
    const buttons = screen.getAllByRole("button").map((b) => b.textContent);
    expect(buttons.slice(-2)).toEqual(["Back", "Continue"]);
    expect(screen.getByRole("button", { name: "Done" })).toBeInTheDocument();
  });

  it("Return in a field triggers Continue", async () => {
    const onContinue = vi.fn();
    renderShell({ actions: { onContinue } });
    await userEvent.type(screen.getByLabelText("Your name"), "Ada{Enter}");
    expect(onContinue).toHaveBeenCalledTimes(1);
  });

  it("save state reads Saving… then Saved", () => {
    const { rerender } = renderShell({ saveState: "saving" });
    expect(screen.getByRole("status")).toHaveTextContent("Saving…");
    rerender(
      <MemoryRouter>
        <AppShell steps={STEPS} currentId="about_you" formTitle="Small Project Plan" saveState="saved"
                  onDone={vi.fn()} rootHref="/x"><p>x</p></AppShell>
      </MemoryRouter>,
    );
    expect(screen.getByRole("status")).toHaveTextContent("Saved");
  });

  it("⌘↓ goes to the next step and ⌥↑ back; an arrow alone does nothing", () => {
    const onStep = vi.fn();
    renderShell({ onStep });
    fireEvent.keyDown(window, { key: "ArrowDown" });
    expect(onStep).not.toHaveBeenCalled();
    fireEvent.keyDown(window, { key: "ArrowDown", metaKey: true });
    expect(onStep).toHaveBeenLastCalledWith("buildings");
    fireEvent.keyDown(window, { key: "ArrowUp", altKey: true });
    expect(onStep).toHaveBeenLastCalledWith("project");
  });

  it("shows the conflict with Load the latest", async () => {
    const onReload = vi.fn();
    renderShell({ saveState: "conflict", onReload });
    expect(screen.getByRole("status")).toHaveTextContent("Changed in another tab");
    await userEvent.click(screen.getByRole("button", { name: "Load the latest" }));
    expect(onReload).toHaveBeenCalled();
  });
});

describe("AppShell, narrow", () => {
  beforeEach(() => vi.spyOn(layout, "useWideLayout").mockReturnValue(false));

  it("root shows the step list and no Continue", () => {
    renderShell({ currentId: null });
    expect(screen.getByRole("heading", { level: 1, name: "Your application" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /About you/ })).toHaveAttribute("href", "/x/about_you");
    expect(screen.queryByRole("button", { name: "Continue" })).not.toBeInTheDocument();
  });

  it("a step shows the chevron and a fixed Continue", () => {
    renderShell({ actions: { onContinue: vi.fn(), back: vi.fn() } });
    expect(screen.getByRole("link", { name: "Application" })).toHaveAttribute("href", "/x");
    const bar = screen.getByRole("button", { name: "Continue" }).closest("[data-action-bar]");
    expect(bar).toHaveClass("fixed");
    expect(screen.queryByRole("button", { name: "Back" })).not.toBeInTheDocument();
  });
});
