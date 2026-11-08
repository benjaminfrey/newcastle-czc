import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router";
import { beforeEach, expect, test, vi } from "vitest";
import * as api from "./api";
import type { Batch, ReviewItem } from "./api";
import BatchPage from "./BatchPage";

vi.mock("./api", async (orig) => ({
  ...(await orig<typeof import("./api")>()),
  getBatch: vi.fn(), getPreview: vi.fn(), decide: vi.fn(), pullEntry: vi.fn(),
}));

const ITEM: ReviewItem = {
  entry: { id: "total_stories", kind: "standard", overline: "Why · how tall", answer: "At most {stories}.",
    detail: "Count full stories.", why: "Scale.", cites: ["2.3.c.3"], version: 1, status: "draft",
    standards: ["building:total_stories"], review_note: null },
  flags: ["grade 9.1"], code: [{ cite: "2.3.c.3", text: "Buildings shall not exceed the stories shown." }],
  pending: null, pulled: null,
};
const BATCH: Batch = {
  batch: "article-02", open_questions: ["D3: no rear setback is given."], entries: [ITEM],
  districts: [{ key: "d1", code: "D1", name: "D1 - Rural", buildings: ["Residential", "General Accessory"] },
              { key: "d2", code: "D2", name: "D2 - Neighborhood Residential", buildings: ["Residential"] }],
};
const PREVIEW = { id: "total_stories", overline: "Why · how tall", answer: "At most 2 stories.", detail: "Count full stories.",
  why: "Scale.", cites: ["2.3.c.3"], version: 1, governs: "The adopted Code governs.", interpretations: [] as string[] };

const show = (b: Batch = BATCH) => {
  vi.mocked(api.getBatch).mockResolvedValue(b);
  vi.mocked(api.getPreview).mockResolvedValue(PREVIEW);
  vi.mocked(api.decide).mockResolvedValue({ id: 1 });
  vi.mocked(api.pullEntry).mockResolvedValue({ entry_id: "total_stories" });
  return render(<MemoryRouter initialEntries={["/library/article-02"]}><Routes>
    <Route path="/library/:batch" element={<BatchPage />} />
  </Routes></MemoryRouter>);
};
beforeEach(() => vi.clearAllMocks());

test("the open questions come first, then each entry as a resident sees it, with its Code", async () => {
  show();
  expect(await screen.findByRole("heading", { level: 2, name: "Questions for the chair" })).toBeInTheDocument();
  expect(screen.getByText("D3: no rear setback is given.")).toBeInTheDocument();
  expect(await screen.findByText("At most 2 stories.")).toBeInTheDocument();
  expect(screen.getByText("Buildings shall not exceed the stories shown.")).toBeInTheDocument();
  expect(screen.getByText("grade 9.1")).toBeInTheDocument();
  expect(screen.getByText("Draft · v1 · total_stories")).toBeInTheDocument();
});

test("picking a district fetches its preview", async () => {
  show();
  await screen.findByText("At most 2 stories.");
  expect(api.getPreview).toHaveBeenLastCalledWith("total_stories", "d1", "Residential");
  await userEvent.selectOptions(screen.getByLabelText("District"), "d2");
  await waitFor(() => expect(api.getPreview).toHaveBeenLastCalledWith("total_stories", "d2", "Residential"));
});

test("a district where it doesn't apply says so", async () => {
  show();
  await screen.findByText("At most 2 stories.");
  vi.mocked(api.getPreview).mockResolvedValue("not_found");
  await userEvent.selectOptions(screen.getByLabelText("District"), "d2");
  expect(await screen.findByText(/the standard goes to the Town/)).toBeInTheDocument();
});

test("approve posts the entry's version", async () => {
  show();
  await userEvent.click(await screen.findByRole("button", { name: "Approve" }));
  expect(api.decide).toHaveBeenCalledWith("total_stories", 1, "approve");
});

test("send back is disabled until a note is typed", async () => {
  show();
  const send = await screen.findByRole("button", { name: "Send back" });
  expect(send).toBeDisabled();
  await userEvent.type(screen.getByLabelText("Note for the record"), "Say which permit.");
  await userEvent.click(send);
  expect(api.decide).toHaveBeenCalledWith("total_stories", 1, "send_back", { note: "Say which permit." });
});

test("an edit posts the four texts, then offers Approve", async () => {
  show();
  await userEvent.click(await screen.findByRole("button", { name: "Edit" }));
  const answer = screen.getByLabelText("Answer");
  await userEvent.clear(answer);
  await userEvent.type(answer, "No more than {{stories}.");
  await userEvent.click(screen.getByRole("button", { name: "Save edit" }));
  expect(api.decide).toHaveBeenCalledWith("total_stories", 1, "edit", { body: {
    overline: "Why · how tall", answer: "No more than {stories}.", detail: "Count full stories.", why: "Scale." } });
  expect(await screen.findByRole("button", { name: "Approve" })).toBeEnabled();
});

test("pull asks to confirm, and needs a reason", async () => {
  show();
  await userEvent.click(await screen.findByRole("button", { name: "Pull" }));
  const dialog = await screen.findByRole("dialog", { name: "Pull this entry now?" });
  const yes = within(dialog).getByRole("button", { name: "Pull it" });
  expect(yes).toBeDisabled();
  await userEvent.type(within(dialog).getByLabelText("Why pull it?"), "The number is wrong");
  await userEvent.click(yes);
  expect(api.pullEntry).toHaveBeenCalledWith("total_stories", 1, "The number is wrong");
});

test("a pending decision shows the pending line", async () => {
  show({ ...BATCH, entries: [{ ...ITEM, pending: { id: 3, entry_id: "total_stories", version: 1, action: "approve",
    body: null, note: null, decided_at: "2026-11-20T15:00:00Z", decided_by_email: "chair@example.com" } }] });
  expect(await screen.findByText("Pending: approved, not yet recorded")).toBeInTheDocument();
});

test("the interpretation mark is the API's word, shown only when it sends one", async () => {
  show();
  await screen.findByText("At most 2 stories.");
  expect(screen.queryByText("The Town's reading of the Code")).not.toBeInTheDocument();
  vi.mocked(api.getPreview).mockResolvedValue({ ...PREVIEW, interpretations: ["Decided by the chair."], mark: "The Town's reading of the Code" });
  await userEvent.selectOptions(screen.getByLabelText("District"), "d2");
  expect(await screen.findByText("The Town's reading of the Code")).toBeInTheDocument();
});

test("a pending edit is shown, and editing again starts from it", async () => {
  const body = { overline: "Why · how tall", answer: "No more than {stories}.", detail: "Count full stories.", why: "Scale." };
  show({ ...BATCH, entries: [{ ...ITEM, pending: { id: 3, entry_id: "total_stories", version: 1, action: "edit",
    body, note: null, decided_at: "2026-11-20T15:00:00Z", decided_by_email: "chair@example.com" } }] });
  const waiting = await screen.findByRole("region", { name: "The edited text, waiting for approval" });
  expect(within(waiting).getByText("No more than {stories}.")).toBeInTheDocument();
  await userEvent.click(screen.getByRole("button", { name: "Edit" }));
  expect(screen.getByLabelText("Answer")).toHaveValue("No more than {stories}.");
});

test("a resident sees the page is for staff", async () => {
  vi.mocked(api.getBatch).mockResolvedValue("staff_only");
  render(<MemoryRouter initialEntries={["/library/article-02"]}><Routes>
    <Route path="/library/:batch" element={<BatchPage />} /></Routes></MemoryRouter>);
  expect(await screen.findByText("This page is for Town staff.")).toBeInTheDocument();
});
