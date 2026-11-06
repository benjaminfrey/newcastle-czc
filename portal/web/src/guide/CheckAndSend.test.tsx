import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router";
import { beforeEach, expect, test, vi } from "vitest";
import * as projects from "../projects";
import CheckAndSend from "./CheckAndSend";
import { ended, project } from "./endingFixtures";
import { FLOOR, LOT } from "./fixtures";
import { RECT } from "./drawing/fixtures";
import * as drawn from "./drawing/useDrawing";
import * as hook from "./useGuide";

vi.mock("./useGuide", () => ({ useGuide: vi.fn() }));
vi.mock("./drawing/useDrawing", () => ({ useDrawing: vi.fn(() => null) }));
vi.mock("../projects", async (orig) => ({ ...(await orig<typeof import("../projects")>()),
  getProject: vi.fn(), submitProject: vi.fn() }));

const change = vi.fn(async () => true);
const reload = vi.fn(async () => undefined);
const actions = { start: vi.fn(), answer: vi.fn(), back: vi.fn(), change, note: vi.fn(), dismissNotice: vi.fn(), reload };
const READY = { ...ended(), history: [{ shown: LOT, value: "yes" }, { shown: FLOOR, value: 1800 }] };
const talk = (g = READY) => vi.mocked(hook.useGuide).mockReturnValue(
  { view: { phase: "talk", guide: g, busy: false, notice: null, locked: false, epoch: 0 }, ...actions });

function open() {
  render(<MemoryRouter initialEntries={["/projects/p1/guide/check"]}><Routes>
    <Route path="/projects/:id/guide/check" element={<CheckAndSend />} />
    <Route path="/projects/:id/guide" element={<p>The guide</p>} />
    <Route path="/projects/:id/:step" element={<p>The form</p>} />
  </Routes></MemoryRouter>);
}

beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(projects.getProject).mockResolvedValue(project());
});

test("the summary, the fees, and Send", async () => {
  talk();
  vi.mocked(projects.submitProject).mockResolvedValue({ revision: 10, missing: [] });
  open();
  expect(await screen.findByRole("heading", { level: 2, name: "Check your project" })).toBeVisible();
  expect(screen.getByText("1,800 sq ft")).toBeVisible();
  expect(screen.getByText("$30")).toBeVisible();
  await userEvent.click(screen.getByRole("button", { name: "Send to the Town" }));
  expect(projects.submitProject).toHaveBeenCalledWith("p1", 9);
  expect(await screen.findByText("Sent. The Town has your project.")).toBeVisible();
});

test("Change from Check and send goes back into the conversation", async () => {
  talk();
  open();
  await userEvent.click(await screen.findByRole("button", { name: /^Change: What is the floor area/ }));
  expect(change).toHaveBeenCalledWith("floor_area");
  expect(await screen.findByText("The guide")).toBeVisible();
});

test("what the official form still needs is listed, each linking to its step", async () => {
  talk();
  vi.mocked(projects.submitProject).mockResolvedValue({ incomplete: [{ field_id: "owner_name", item_id: null }] });
  open();
  await userEvent.click(await screen.findByRole("button", { name: "Send to the Town" }));
  expect(await screen.findByText("Before you send, the Town's form still needs:")).toBeVisible();
  await userEvent.click(screen.getByRole("link", { name: "Who owns the property?" }));
  expect(await screen.findByText("The form")).toBeVisible();
});

test("it is only for a project that is ready", async () => {
  talk({ ...READY, ending: { ...READY.ending!, kind: "town_judgment" } });
  open();
  expect(await screen.findByText("The guide")).toBeVisible();
});

test("after a conflict, the conversation reloads too, so a project no longer ready can't be sent", async () => {
  talk();
  vi.mocked(projects.submitProject).mockResolvedValue({ conflict: 10 });
  open();
  await userEvent.click(await screen.findByRole("button", { name: "Send to the Town" }));
  expect(await screen.findByText(/changed in another window/)).toBeVisible();
  expect(reload).toHaveBeenCalledOnce();
});

test("its way back names where it goes", async () => {
  talk();
  open();
  expect(await screen.findByRole("link", { name: "Back to the conversation" })).toHaveAttribute("href", "/projects/p1/guide");
});


test("check and send shows the drawing and its list", async () => {
  vi.mocked(drawn.useDrawing).mockReturnValue(RECT);
  talk();
  open();
  expect(await screen.findByRole("img", { name: /A drawing of your lot/ })).toBeVisible();
  expect(screen.getByRole("group", { name: "The setbacks on your lot" })).toBeVisible();
});

test("a note for the Town can be added on Check and send, and the notes so far are shown", async () => {
  // The chair, 2026-11-05: one optional note box here, read by the Town's staff; the guide never reads it.
  talk({ ...READY, notes: [{ body: "There's a well by the road.", at: "2026-11-05T10:00:00Z" }] });
  open();
  expect(screen.getByText("There's a well by the road.")).toBeVisible();
  expect(screen.getByText(/The Town Office will read this/)).toBeVisible();
  await userEvent.type(screen.getByRole("textbox", { name: "Anything else the Town should know?" }), "The barn stays.{Enter}");
  expect(actions.note).toHaveBeenCalledWith("The barn stays.");
});
