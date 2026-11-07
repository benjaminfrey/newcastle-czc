import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router";
import { beforeEach, expect, test, vi } from "vitest";
import * as api from "../api";
import type { Packet } from "../api";
import { check } from "../turns/fixtures";
import { RECT } from "../drawing/fixtures";
import PacketPage from "./PacketPage";

vi.mock("../api", async (orig) => ({ ...(await orig<typeof import("../api")>()), getPacket: vi.fn() }));

const PACKET: Packet = {
  state: "now", sent_at: null, finished: true,
  summary: { own_words: [{ body: "Line one\n<b>Two</b>", at: "2026-11-06T12:00:00Z" }],
    reading: "So you'd like to build a new house on lot 4-36, in D1 Rural.",
    deciders: ["The Code Enforcement Officer decides within 10 days of accepting your project."],
    corrections: { lot_disputed: false, note: null } },
  history: [
    { turn_id: "confirm", ask: "So you'd like to build a new house?", answer: "Yes, that's right", value: "yes", marks: ["confirmed"] },
    { turn_id: "doesnt_fit:setback_side_1", ask: "That's 4 ft short of the limit here.", answer: "Make it 15 ft", value: "nearest", marks: ["took_suggestion"] },
  ],
  checks: { setback_front: check({ value: 30, min: 25 }) },
  checklist: {
    town: [{ turn_id: "dwelling_units", ask: "How many homes will it have?", reason: "unsure", check: null, why: null }],
    fits: [{ turn_id: "setback_front", ask: "How far from the front?", check: check({ value: 30, min: 25 }), why: null },
           { turn_id: "setback_rear", ask: "How far from the rear?", check: check({ value: 40, min: 15 }), why: null }],
  },
  drawing: RECT, drafts: [],
};

const show = (p: Packet | api.GuideRefusal = PACKET) => {
  vi.mocked(api.getPacket).mockResolvedValue(p);
  return render(<MemoryRouter initialEntries={["/projects/p1/packet"]}><Routes>
    <Route path="/projects/:id/packet" element={<PacketPage />} />
    <Route path="/projects/:id" element={<p>The project page</p>} />
  </Routes></MemoryRouter>);
};

beforeEach(() => vi.clearAllMocks());

test("the four parts come in the spec's order", async () => {
  show();
  await screen.findByRole("heading", { level: 2, name: "In your own words" });
  expect(screen.getAllByRole("heading", { level: 2 }).map((h) => h.textContent)).toEqual(
    ["In your own words", "Your project in the Code's terms", "Who decides", "The questions and your answers",
     "The checklist", "Your lot"]);
});

test("own words are shown exactly as written", async () => {
  show();
  const words = await screen.findByText(/Line one/);
  expect(words.textContent).toBe("Line one\n<b>Two</b>");
  expect(words).toHaveStyle({ whiteSpace: "pre-wrap" });
});

test("judgment comes first and the passes are folded", async () => {
  show();
  expect(await screen.findByText("How many homes will it have?")).toBeVisible();
  const open = screen.getByRole("button", { name: "Show what fits (2)" });
  expect(open).toHaveAttribute("aria-expanded", "false");
  expect(screen.getByText("How far from the rear?")).not.toBeVisible();   // folded, but there to print
  await userEvent.click(open);
  expect(screen.getByText("How far from the rear?")).toBeVisible();
});

test("every highlight carries its words", async () => {
  show();
  expect(await screen.findByText("You took the suggestion")).toBeVisible();
  expect(screen.getByText("You confirmed this")).toBeVisible();
});

test("as sent says when", async () => {
  show({ ...PACKET, state: "sent", sent_at: "2026-11-06T15:00:00Z" });
  expect(await screen.findByText("As sent on November 6, 2026")).toBeVisible();
});

test("a lot corrected by the person is flagged in the summary", async () => {
  show({ ...PACKET, summary: { ...PACKET.summary, corrections: { lot_disputed: true, note: "The lot is bigger." } } });
  expect(await screen.findByText("The Town's facts about your lot, which you said aren't right")).toBeVisible();
  expect(screen.getByText("The lot is bigger.")).toBeVisible();
});

test("no outline, no drawing, and it says why", async () => {
  show({ ...PACKET, drawing: null });
  expect(await screen.findByText("The Town's tax map has no outline for this lot, so there is no drawing.")).toBeVisible();
});

test("not started leads back to the project", async () => {
  show("not_started");
  expect(await screen.findByRole("link", { name: /your project/ })).toHaveAttribute("href", "/projects/p1");
});

test("an unfinished conversation says so", async () => {
  show({ ...PACKET, finished: false });
  expect(await screen.findByText("The conversation isn't finished, so this shows what's settled so far.")).toBeVisible();
});

test("the drawing sits with its list", async () => {
  show();
  const lot = (await screen.findByRole("heading", { level: 2, name: "Your lot" })).closest("section")!;
  expect(within(lot).getByRole("img")).toBeInTheDocument();
  expect(within(lot).getByText("The setbacks on your lot")).toBeInTheDocument();
});
