import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes, useLocation } from "react-router";
import { describe, expect, it } from "vitest";
import TaskList, { type TaskRow } from "./TaskList";

const TASKS: TaskRow[] = [
  { id: "your_lot", title: "Your lot", href: "/a/your_lot", status: { kind: "done" } },
  { id: "the_work", title: "The work", href: "/a/the_work", status: { kind: "progress", answered: 2, total: 4 } },
  { id: "buildings", title: "Buildings", href: "/a/buildings", status: { kind: "todo" }, current: true },
];

function Where() {
  return <p data-testid="where">{useLocation().pathname}</p>;
}
const draw = (open: boolean, compact = false) => render(
  <MemoryRouter initialEntries={["/a"]}>
    <TaskList formTitle="Small Project Plan" mapLot="004-036" saveState="saved" tasks={TASKS}
              send={{ href: "/a/review", open }} compact={compact} />
    <Routes><Route path="*" element={<Where />} /></Routes>
  </MemoryRouter>,
);

describe("TaskList", () => {
  it("each task is one row, a link, with its pill", () => {
    draw(false);
    const pill = (name: RegExp) => screen.getByRole("link", { name }).querySelector("[data-pill]")!;
    expect(pill(/^Your lot,.*Done$/)).toHaveAttribute("data-pill", "done");
    expect(pill(/^The work,.*2 of 4 ?answered$/)).toHaveAttribute("data-pill", "progress");
    expect(pill(/^The work,.*2 of 4 ?answered$/)).toHaveTextContent("2 of 4");
    expect(pill(/^Buildings,.*Not started$/)).toHaveAttribute("data-pill", "todo");
  });

  it("the hints and icons come with the task", () => {
    draw(false);
    const lot = screen.getByRole("link", { name: /^Your lot,.*Done$/ });
    expect(lot).toHaveTextContent("Size, frontage and what is there now");
    expect(lot.querySelector("svg")).not.toBeNull();
  });

  it("the header names the form and the lot, and says it's saved", () => {
    draw(false);
    expect(screen.getByText("Small Project Plan")).toBeInTheDocument();
    expect(screen.getByText(/Map 4, Lot 36/)).toBeInTheDocument();
    expect(screen.getByText("Saved")).toBeInTheDocument();
  });

  it("Check and send is closed, without a pill, until the tasks are done", () => {
    draw(false);
    expect(screen.queryByRole("link", { name: /Check and send/ })).not.toBeInTheDocument();
    expect(screen.getByText("Check and send")).toBeInTheDocument();
    expect(screen.getByText("Opens when the tasks above are done")).toBeInTheDocument();
  });

  it("then it opens", async () => {
    draw(true);
    await userEvent.click(screen.getByRole("link", { name: "Check and send" }));
    expect(screen.getByTestId("where")).toHaveTextContent("/a/review");
    expect(screen.queryByText("Opens when the tasks above are done")).not.toBeInTheDocument();
  });

  it("the task you're in is marked", () => {
    draw(false, true);
    expect(screen.getByRole("link", { name: /^Buildings,.*Not started$/ })).toHaveAttribute("aria-current", "step");
  });
});
