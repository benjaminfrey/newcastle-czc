import { act, fireEvent, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router";
import { beforeEach, expect, test, vi } from "vitest";
import * as projects from "../projects";
import { FLOOR, guide, LOT, SIDE } from "./fixtures";
import GuidePage from "./GuidePage";
import { RECT } from "./drawing/fixtures";
import { fitView, fromFrame, frontFrame } from "./drawing/geometry";
import * as drawn from "./drawing/useDrawing";
import * as hook from "./useGuide";
import { shown } from "./turns/fixtures";

vi.mock("./useGuide", () => ({ useGuide: vi.fn() }));
vi.mock("./drawing/useDrawing", () => ({ useDrawing: vi.fn(() => null) }));
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


// --- plan 4: the lot drawing in the conversation ---

const FRONT = shown({ turn_id: "front_line", kind: "choice", ask: "Which lot line is the front?", drawing: "front",
  step: { n: 1, of: 4, label: "Your lot" }, answers: [{ id: "L1", label: "The line along Sheepscot Road", hint: null },
    { id: "other", label: "A different line", hint: null }, { id: "unsure", label: "I'm not sure yet", hint: null }] });
const FRONT_SETBACK = shown({ turn_id: "setback_front", kind: "number", ask: "How far from the front lot line?",
  drawing: "front_setback", step: SIDE.step, input: { unit: "ft", min: 0, max: 50000 }, answers: [] });

const phone = async () => vi.spyOn(await import("../shell/useWideLayout"), "useWideLayout").mockReturnValue(false);
const computer = async () => vi.spyOn(await import("../shell/useWideLayout"), "useWideLayout").mockReturnValue(true);

test("the front turn shows the drawing, and tapping a line answers with its id", async () => {
  const spy = await phone();
  vi.mocked(drawn.useDrawing).mockReturnValue({ ...RECT, front: null, roles: null });
  talk(guide({ current: FRONT }));
  const { container } = open();
  const turn = container.querySelector("[data-turn='front_line']")!;
  expect(turn.querySelector("svg[role=img]")).not.toBeNull();
  await userEvent.click(turn.querySelector("[data-pick='L1']")!);
  expect(actions.answer).toHaveBeenCalledWith("front_line", "L1");
  await userEvent.click(screen.getByRole("radio", { name: "A different line" }));
  expect(actions.answer).toHaveBeenLastCalledWith("front_line", "other");
  expect(screen.getByRole("radio", { name: "I'm not sure yet" })).toBeInTheDocument();
  spy.mockRestore();
});

test("on a setback turn, dragging fills the field and Next sends that number", async () => {
  const spy = await phone();
  vi.mocked(drawn.useDrawing).mockReturnValue(RECT);
  talk(guide({ current: FRONT_SETBACK }));
  const { container } = open();
  const turn = container.querySelector("[data-turn='setback_front']")!;
  const svg = turn.querySelector("svg[role=img]") as SVGSVGElement;
  const [x, y, w, h] = fitView(RECT.outline!).viewBox.split(" ").map(Number);
  const { scale } = fitView(RECT.outline!);
  svg.getBoundingClientRect = () => ({ left: 0, top: 0, width: w, height: h, right: w, bottom: h, x: 0, y: 0, toJSON: () => ({}) });
  const f = frontFrame(RECT.outline!, "L1")!;
  const at = (q: [number, number]) => { const p = fromFrame(f, q); return { clientX: p[0] * scale - x, clientY: -p[1] * scale - y, pointerId: 1 }; };
  // No distance yet: the box starts at the front limit's line so there is an edge to drag.
  const handle = turn.querySelector("[data-handle='front']")!;
  fireEvent.pointerDown(handle, at([50, 25]));
  fireEvent.pointerMove(svg, at([50, 55]));
  fireEvent.pointerUp(svg, { pointerId: 1 });
  expect(screen.getByRole("textbox", { name: FRONT_SETBACK.ask })).toHaveValue("55");
  await userEvent.click(screen.getByRole("button", { name: "Next" }));
  expect(actions.answer).toHaveBeenCalledWith("setback_front", 55);
  spy.mockRestore();
});

test("no drawing when the lot has no outline", () => {
  vi.mocked(drawn.useDrawing).mockReturnValue(null);
  talk(guide({ current: FRONT_SETBACK }));
  const { container } = open();
  expect(container.querySelector("svg[role=img]")).toBeNull();
  expect(screen.getByRole("textbox", { name: FRONT_SETBACK.ask })).toBeVisible();
});

test("on a computer the drawing heads the project panel, not the turn", async () => {
  const spy = await computer();
  vi.mocked(drawn.useDrawing).mockReturnValue(RECT);
  talk(guide({ current: FRONT_SETBACK }));
  const { container } = open();
  expect(container.querySelector("[data-turn] svg[role=img]")).toBeNull();
  expect(container.querySelectorAll("svg[role=img]")).toHaveLength(1);
  expect(container.querySelector("[data-handle='front']")).not.toBeNull();   // and it can be dragged there
  spy.mockRestore();
});

test("on a phone the drawing is inside the turn, and only on a where turn", async () => {
  const spy = await phone();
  vi.mocked(drawn.useDrawing).mockReturnValue(RECT);
  talk(guide({ current: FRONT_SETBACK }));
  const { container, unmount } = open();
  expect(container.querySelector("[data-turn='setback_front'] svg[role=img]")).not.toBeNull();
  unmount();
  talk(guide({ current: FLOOR }));
  const second = open();
  expect(second.container.querySelector("svg[role=img]")).toBeNull();
  spy.mockRestore();
});

test("the drawing is asked for at the guide's revision", () => {
  vi.mocked(drawn.useDrawing).mockReturnValue(null);
  talk(guide({ current: FRONT, revision: 7 }));
  open();
  expect(drawn.useDrawing).toHaveBeenCalledWith("p1", 7);
});

test("on a phone the setbacks list comes after the field, so the field stays near its question", async () => {
  const spy = await phone();
  vi.mocked(drawn.useDrawing).mockReturnValue(RECT);
  talk(guide({ current: FRONT_SETBACK }));
  const { container } = open();
  const turn = container.querySelector("[data-turn='setback_front']")!;
  const field = screen.getByRole("textbox", { name: FRONT_SETBACK.ask });
  const list = within(turn as HTMLElement).getByRole("group", { name: "The setbacks on your lot" });
  const svg = turn.querySelector("svg[role=img]")!;
  expect(svg.compareDocumentPosition(field) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
  expect(field.compareDocumentPosition(list) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
  spy.mockRestore();
});

test("after a Change, the later questions it reopened are listed by their own words", async () => {
  // The chair, 2026-11-05: a Change says which later answers it reopened.
  talk(guide({ reopened: [{ turn_id: "setback_side_1", ask: SIDE.ask }, { turn_id: "floor_area", ask: FLOOR.ask }] }));
  open();
  const note = screen.getByRole("status", { name: "Changing that answer reopened 2 later questions" });
  expect(note).toHaveTextContent(SIDE.ask);
  expect(note).toHaveTextContent(FLOOR.ask);
  await userEvent.click(within(note).getByRole("button", { name: "Close" }));
  expect(screen.queryByRole("status", { name: /reopened/ })).toBeNull();
});

test("one reopened question is told as one", () => {
  talk(guide({ reopened: [{ turn_id: "floor_area", ask: FLOOR.ask }] }));
  open();
  expect(screen.getByRole("status", { name: "Changing that answer reopened 1 later question" })).toBeVisible();
});
