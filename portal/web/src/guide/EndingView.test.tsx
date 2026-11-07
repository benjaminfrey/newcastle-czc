import { act, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { beforeEach, expect, test, vi } from "vitest";
import * as projects from "../projects";
import { ended, project } from "./endingFixtures";
import { EndingView } from "./EndingView";
import { GuideTheme } from "./theme/GuideTheme";
import { WORDS } from "./words";

vi.mock("../projects", async (orig) => ({ ...(await orig<typeof import("../projects")>()), getProject: vi.fn() }));
beforeEach(() => vi.mocked(projects.getProject).mockResolvedValue(project()));

const view = (g = ended()) => render(<MemoryRouter><GuideTheme><EndingView guide={g} projectId="p1" /></GuideTheme></MemoryRouter>);

test("ready shows what the project needs, its fees and the way to Check and send", async () => {
  view();
  expect(screen.getByRole("heading", { level: 2, name: "Your application is ready to send" })).toBeVisible();
  expect(await screen.findByText("Small Project Plan")).toBeVisible();
  expect(screen.getByText("$30")).toBeVisible();
  expect(screen.getByRole("link", { name: "Check and send" })).toHaveAttribute("href", "/projects/p1/guide/check");
});

test("no permit says to keep to it, and offers no send", () => {
  view(ended({ kind: "no_permit", title: "You don't need a permit for this" }));
  expect(screen.getByText(WORDS.no_permit_keep)).toBeVisible();
  expect(screen.queryByRole("link", { name: "Check and send" })).toBeNull();
});

test("the Town's judgment lists what was settled and what goes to the Town, and sends nothing", () => {
  view(ended({ kind: "town_judgment", title: "This needs the Town's judgment",
    unsettled: [{ turn_id: "setback_side_1", reason: "kept_past_the_limit" }, { turn_id: null, reason: "town_only" }] }));
  expect(screen.getByRole("heading", { name: WORDS.settled_heading })).toBeVisible();
  expect(screen.getByText(WORDS.unsettled.kept_past_the_limit)).toBeVisible();
  expect(screen.getByText(WORDS.unsettled.town_only)).toBeVisible();
  expect(screen.getByText(WORDS.talk_to_town)).toBeVisible();
  expect(screen.queryByRole("link", { name: "Check and send" })).toBeNull();
  expect(screen.queryByRole("button", { name: /send/i })).toBeNull();
});

test("every reason the engine gives has words", () => {
  const reasons = ["not_listed", "not_listed_in_one_district", "unsure", "kept_past_the_limit", "talk_to_town",
    "lot_disputed", "no_district", "not_checkable", "two_districts", "unknown_input", "board_decides", "town_only", "contact_town"];
  expect(reasons.filter((r) => !(r in WORDS.unsettled))).toEqual([]);
});

test("an unknown reason is for the Town, never blank", () => {
  view(ended({ kind: "town_judgment", unsettled: [{ turn_id: null, reason: "something_new" }] }));
  expect(screen.getAllByText(WORDS.town_decides).length).toBeGreaterThan(0);
});

test("not here shows what each district allows", () => {
  view(ended({ kind: "not_here", title: "Not here, but…",
    allowed_uses: [{ district: "D1", uses: [{ use_key: "residence", code_name: "Residence" }] }] }));
  expect(screen.getByRole("heading", { name: "What D1 allows" })).toBeVisible();
  expect(screen.getByText("Residence")).toBeVisible();
  expect(screen.getByText(WORDS.talk_to_town)).toBeVisible();
});

test("an ending's library entry shows as a card", () => {
  view(ended({ kind: "not_here", entry: { id: "use_not_listed", overline: "Why · uses", answer: "a", detail: "d", why: null,
    cites: [], version: 1, governs: "" } }));
  expect(screen.getByRole("article")).toHaveTextContent("Why · uses");
});

test("the fees say nothing until they've loaded", async () => {
  let resolve!: (p: projects.ProjectState) => void;
  vi.mocked(projects.getProject).mockReturnValue(new Promise((r) => { resolve = r; }));
  view();
  expect(screen.queryByText(WORDS.fees_unknown)).toBeNull();
  await act(async () => resolve(project()));
  expect(await screen.findByText("$30")).toBeVisible();
});

test("an ending that sends you to the Town links to the Town's own contact page", () => {
  // The chair, 2026-11-05: no phone, hours or address on the screens; the Town's Citizens
  // Request Center, which lists Code Enforcement.
  for (const kind of ["town_judgment", "not_here"] as const) {
    const { unmount } = view(ended({ kind, title: "t", unsettled: [] }));
    const link = screen.getByRole("link", { name: "Contact the Town Office" });
    expect(link).toHaveAttribute("href", "https://www.newcastlemaine.us/citizens_request_center/index.php");
    expect(link).toHaveAttribute("target", "_blank");
    expect(link).toHaveAttribute("rel", expect.stringContaining("noopener"));
    unmount();
  }
});


test("every ending leads to the packet (plan 6)", () => {
  view();
  expect(screen.getByRole("link", { name: "Your packet" })).toHaveAttribute("href", "/projects/p1/packet");
});
