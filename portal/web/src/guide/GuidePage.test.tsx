import { act, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router";
import { beforeEach, expect, test, vi } from "vitest";
import * as projects from "../projects";
import { FLOOR, guide, LOT, SIDE } from "./fixtures";
import GuidePage from "./GuidePage";
import * as hook from "./useGuide";

vi.mock("./useGuide", () => ({ useGuide: vi.fn() }));
vi.mock("../projects", async (orig) => ({ ...(await orig<typeof import("../projects")>()), getProject: vi.fn() }));

const actions = { start: vi.fn(), answer: vi.fn(), back: vi.fn(), change: vi.fn(), note: vi.fn(), dismissNotice: vi.fn(), reload: vi.fn() };
const talk = (g = guide(), more = {}) => vi.mocked(hook.useGuide).mockReturnValue(
  { view: { phase: "talk", guide: g, busy: false, notice: null, locked: false, epoch: 0, ...more }, ...actions });

function open() {
  return render(<MemoryRouter initialEntries={["/projects/p1/guide"]}><Routes>
    <Route path="/projects/:id/guide" element={<GuidePage />} />
    <Route path="/projects/:id" element={<p>The project page</p>} />
  </Routes></MemoryRouter>);
}

beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(projects.getProject).mockResolvedValue({ title: "A new house at Sheepscot Road" } as projects.ProjectState);
});

test("the history shows as said", async () => {
  talk();
  open();
  expect(await screen.findByRole("heading", { level: 1, name: "A new house at Sheepscot Road" })).toBeVisible();
  const main = screen.getByRole("main");
  expect(main).toHaveTextContent("Is this your lot?");
  expect(main).toHaveTextContent("You saidYes");
  expect(screen.getByRole("heading", { level: 2, name: FLOOR.ask })).toBeVisible();
});

test("Back goes back with history, and links to the project without it", async () => {
  talk();
  const { unmount } = open();
  await userEvent.click(screen.getByRole("button", { name: "Back to the last question" }));
  expect(actions.back).toHaveBeenCalledOnce();
  unmount();
  talk(guide({ history: [], current: LOT }));
  open();
  await userEvent.click(screen.getByRole("link", { name: "Back to your project" }));
  expect(await screen.findByText("The project page")).toBeVisible();
});

test("focus moves to each new question", async () => {
  talk();
  const { rerender } = open();
  talk(guide({ current: SIDE, history: [{ shown: LOT, value: "yes" }, { shown: FLOOR, value: 1800 }] }));
  await act(async () => rerender(<MemoryRouter initialEntries={["/projects/p1/guide"]}><Routes>
    <Route path="/projects/:id/guide" element={<GuidePage />} /></Routes></MemoryRouter>));
  expect(screen.getByRole("heading", { level: 2, name: SIDE.ask })).toHaveFocus();
});

test("notes are kept and shown back, and say the guide doesn't act on them", async () => {
  talk(guide({ notes: [{ body: "There's a well by the road.", at: "2026-11-02T10:00:00Z" }] }));
  open();
  expect(screen.getByRole("main")).toHaveTextContent("There's a well by the road.");
  expect(screen.getByText(/The guide's questions don't change because of it/)).toBeVisible();
  await userEvent.type(screen.getByRole("textbox", { name: "Anything else the Town should know?" }), "A porch too.{Enter}");
  expect(actions.note).toHaveBeenCalledWith("A porch too.");
});

test("before it starts, the openings are offered", async () => {
  vi.mocked(hook.useGuide).mockReturnValue({ view: { phase: "pick", revision: 1, busy: false,
    openings: [{ id: "new_house", label: "Build a new house", part: "building" }] }, ...actions });
  open();
  await userEvent.click(await screen.findByText("Build a new house"));
  expect(actions.start).toHaveBeenCalledWith("new_house");
});

test("a doesn't-fit turn is its own page, without the conversation above it", async () => {
  const fit = { ...SIDE, turn_id: "doesnt_fit:setback_side_1", kind: "choice" as const, ask: "That's 4 ft short of the limit here.",
    answers: [{ id: "nearest", label: "Make it 15 ft", hint: null }] };
  talk(guide({ current: fit, history: [{ shown: LOT, value: "yes" }, { shown: SIDE, value: 11 }] }));
  open();
  expect(screen.getByRole("heading", { level: 2, name: fit.ask })).toBeVisible();
  expect(screen.getByRole("main")).not.toHaveTextContent("Is this your lot?");
});

test("a locked project is read-only and says so", () => {
  talk(guide(), { locked: true });
  open();
  expect(screen.getByText("The Town is reviewing this project, so it can't be changed now.")).toBeVisible();
  expect(screen.queryByRole("textbox", { name: "Anything else the Town should know?" })).toBeNull();
});

test("a notice says why the page changed", async () => {
  talk(guide(), { notice: "changed_elsewhere" });
  open();
  expect(screen.getByText(/changed in another window/)).toBeVisible();
});

test("after No on So you mean, choosing a picture starts again from it", async () => {
  const pick = { ...LOT, turn_id: "pick_opening", kind: "choice" as const, ask: "What would you like to do?", facts_shown: null,
    answers: [{ id: "new_house", label: "A new house", hint: null }, { id: "change_of_use", label: "A change of use", hint: null }] };
  talk(guide({ current: pick }));
  open();
  await userEvent.click(screen.getByText("A change of use"));
  expect(actions.start).toHaveBeenCalledWith("change_of_use");
  expect(actions.answer).not.toHaveBeenCalled();
});

test("on a phone, your project opens as a named sheet", async () => {
  const wide = await import("../shell/useWideLayout");
  const spy = vi.spyOn(wide, "useWideLayout").mockReturnValue(false);
  talk();
  open();
  await userEvent.click(screen.getByRole("button", { name: "Your project" }));
  expect(await screen.findByRole("dialog", { name: "Your project" })).toBeVisible();
  spy.mockRestore();
});
