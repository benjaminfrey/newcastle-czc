import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { beforeEach, expect, test, vi } from "vitest";
import * as api from "./api";
import LibraryHome from "./LibraryHome";

vi.mock("./api", async (orig) => ({ ...(await orig<typeof import("./api")>()), getBatches: vi.fn() }));
beforeEach(() => vi.clearAllMocks());

const show = () => render(<MemoryRouter><LibraryHome /></MemoryRouter>);

test("a resident sees the page is for staff, and no batches", async () => {
  vi.mocked(api.getBatches).mockResolvedValue("staff_only");
  show();
  expect(await screen.findByText("This page is for Town staff.")).toBeInTheDocument();
  expect(screen.queryByRole("link", { name: /article/i })).not.toBeInTheDocument();
});

test("the counts show per batch", async () => {
  vi.mocked(api.getBatches).mockResolvedValue([
    { batch: "article-02", total: 30, draft: 28, approved: 2, ratified: 0, pulled: 0, pending: 3, open_questions: 4 },
  ]);
  show();
  const link = await screen.findByRole("link", { name: "article-02" });
  expect(link).toHaveAttribute("href", "/library/article-02");
  expect(screen.getByText("30 entries · 28 drafts · 2 approved · 0 ratified · 0 pulled")).toBeInTheDocument();
  expect(screen.getByText("3 waiting to be recorded")).toBeInTheDocument();
  expect(screen.getByText("Draft wording, not approved")).toBeInTheDocument();
});
