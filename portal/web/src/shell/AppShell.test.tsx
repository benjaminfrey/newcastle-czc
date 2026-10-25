import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes, useLocation } from "react-router";
import { beforeEach, describe, expect, it, vi } from "vitest";
import * as layout from "./useWideLayout";
import AppShell from "./AppShell";
import Card from "./Card";
import type { TaskRow } from "./TaskList";

const TASKS: TaskRow[] = [
  { id: "your_lot", title: "Your lot", href: "/a/your_lot", status: { kind: "done" } },
  { id: "the_work", title: "The work", href: "/a/the_work", status: { kind: "todo" }, current: true },
];

function Where() {
  return <p data-testid="where">{useLocation().pathname}</p>;
}
const draw = (inTask: boolean, onDone = vi.fn()) => render(
  <MemoryRouter initialEntries={["/a/the_work"]}>
    <AppShell tasks={TASKS} send={{ href: "/a/review", open: false }} formTitle="Small Project Plan" mapLot="004-036"
              saveState="saved" home="/a" onDone={onDone} inTask={inTask}>
      {inTask && <Card><Card.Header title="The work" count={3} at={0} /><Card.Body motionKey="q1">What kind of work?</Card.Body></Card>}
    </AppShell>
    <Routes><Route path="*" element={<Where />} /></Routes>
  </MemoryRouter>,
);

beforeEach(() => vi.restoreAllMocks());

describe("AppShell", () => {
  it("on a desktop: the task list beside the card", () => {
    vi.spyOn(layout, "useWideLayout").mockReturnValue(true);
    draw(true);
    expect(screen.getByRole("navigation", { name: "Tasks" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /^The work,.*Not started$/ })).toHaveAttribute("aria-current", "step");
    expect(screen.getByText("What kind of work?")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Save and close" })).toBeInTheDocument();
  });

  it("on a phone, in a task: ‹ Tasks, the save status, and the card", async () => {
    vi.spyOn(layout, "useWideLayout").mockReturnValue(false);
    draw(true);
    expect(screen.queryByRole("navigation", { name: "Tasks" })).not.toBeInTheDocument();
    expect(screen.getByText("What kind of work?")).toBeInTheDocument();
    expect(screen.getByText("Saved")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("link", { name: "Tasks" }));
    expect(screen.getByTestId("where")).toHaveTextContent(/^\/a$/);
  });

  it("on a phone, at home: the task list itself, and Save and close", async () => {
    vi.spyOn(layout, "useWideLayout").mockReturnValue(false);
    const onDone = vi.fn();
    draw(false, onDone);
    expect(screen.getByRole("link", { name: /^Your lot,.*Done$/ })).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Save and close" }));
    expect(onDone).toHaveBeenCalled();
  });

  it("only the card's body moves", () => {
    vi.spyOn(layout, "useWideLayout").mockReturnValue(true);
    const { container } = draw(true);
    expect(container.querySelectorAll(".pane-push, .pane-pull, .pane-fade")).toHaveLength(1);
    expect(container.querySelector("[data-card-body]")!.className).toMatch(/pane-push|pane-fade/);
  });
});
