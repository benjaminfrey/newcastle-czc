import { act, renderHook, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import * as projects from "../projects";
import * as api from "./api";
import { useGuide } from "./useGuide";

vi.mock("./api", async (orig) => ({ ...(await orig<typeof import("./api")>()),
  getGuide: vi.fn(), getOpenings: vi.fn(), startGuide: vi.fn(), answerTurn: vi.fn(), goBack: vi.fn(),
  revisit: vi.fn(), addNote: vi.fn() }));
vi.mock("../projects", async (orig) => ({ ...(await orig<typeof import("../projects")>()), getProject: vi.fn() }));

const m = vi.mocked(api);
const guide = (revision: number, turn = "lot"): api.Guide => ({
  revision, opening: "new_house", history: [], ending: null, unsure: [], checks: {}, notes: [], drafts: [],
  step: { n: 1, of: 4, label: "Your lot" },
  current: { turn_id: turn, kind: "choice", step: { n: 1, of: 4, label: "Your lot" }, ask: "?", help: null,
    answers: [], input: null, why: null, defines: [], check: null, facts_shown: null },
});

function deferred<T>() {
  let resolve!: (v: T) => void;
  const promise = new Promise<T>((r) => { resolve = r; });
  return { promise, resolve };
}

async function talking(rev = 1) {
  m.getGuide.mockResolvedValue(guide(rev));
  const h = renderHook(() => useGuide("p1"));
  await waitFor(() => expect(h.result.current.view.phase).toBe("talk"));
  return h;
}

beforeEach(() => vi.clearAllMocks());

describe("useGuide", () => {
  it("loads, then talks", async () => {
    const h = await talking();
    const v = h.result.current.view;
    expect(v.phase === "talk" && v.guide.current?.turn_id).toBe("lot");
  });

  it("offers the openings when the guide hasn't started, and starts with the project's revision", async () => {
    m.getGuide.mockResolvedValue("not_started");
    m.getOpenings.mockResolvedValue([{ id: "new_house", label: "A new house", part: "building" }]);
    vi.mocked(projects.getProject).mockResolvedValue({ revision: 7 } as projects.ProjectState);
    m.startGuide.mockResolvedValue(guide(8));
    const h = renderHook(() => useGuide("p1"));
    await waitFor(() => expect(h.result.current.view.phase).toBe("pick"));
    const v = h.result.current.view;
    expect(v.phase === "pick" && v.openings.map((o) => o.id)).toEqual(["new_house"]);
    act(() => h.result.current.start("new_house"));
    await waitFor(() => expect(h.result.current.view.phase).toBe("talk"));
    expect(m.startGuide).toHaveBeenCalledWith("p1", "new_house", 7);
  });

  it("sends nothing on a second tap while the first is in flight", async () => {
    const h = await talking();
    const d = deferred<api.Guide>();
    m.answerTurn.mockReturnValue(d.promise);
    act(() => h.result.current.answer("lot", "yes"));
    act(() => h.result.current.answer("lot", "yes"));
    expect(m.answerTurn).toHaveBeenCalledTimes(1);
    await act(async () => d.resolve(guide(2, "confirm")));
    const v = h.result.current.view;
    expect(v.phase === "talk" && !v.busy && v.guide.current?.turn_id).toBe("confirm");
  });

  it("reloads on a stale revision and says so", async () => {
    const h = await talking(1);
    m.answerTurn.mockResolvedValue({ conflict: true });
    m.getGuide.mockResolvedValue(guide(5, "floor_area"));
    await act(async () => h.result.current.answer("lot", "yes"));
    await waitFor(() => expect(h.result.current.view.phase === "talk" && h.result.current.view.guide.revision).toBe(5));
    const v = h.result.current.view;
    expect(v.phase === "talk" && [v.notice, v.guide.current?.turn_id]).toEqual(["changed_elsewhere", "floor_area"]);
    expect(m.answerTurn).toHaveBeenCalledTimes(1);
  });

  it("keeps the guide shown, read-only, once the project is locked", async () => {
    const h = await talking();
    m.goBack.mockResolvedValue("locked");
    await act(async () => h.result.current.back());
    const v = h.result.current.view;
    expect(v.phase === "talk" && [v.locked, v.guide.current?.turn_id]).toEqual([true, "lot"]);
    act(() => h.result.current.answer("lot", "yes"));
    expect(m.answerTurn).not.toHaveBeenCalled();
  });

  it("sends each change with the latest revision", async () => {
    const h = await talking(1);
    m.answerTurn.mockResolvedValueOnce(guide(2, "confirm"));
    await act(async () => h.result.current.answer("lot", "yes"));
    m.revisit.mockResolvedValueOnce(guide(3, "lot"));
    await act(async () => h.result.current.change("lot"));
    m.addNote.mockResolvedValueOnce(guide(4, "lot"));
    await act(async () => h.result.current.note("A porch."));
    expect(m.answerTurn).toHaveBeenCalledWith("p1", "lot", "yes", 1);
    expect(m.revisit).toHaveBeenCalledWith("p1", "lot", 2);
    expect(m.addNote).toHaveBeenCalledWith("p1", "A porch.", 3);
  });

  it("reloads and asks to try again when an answer is refused", async () => {
    const h = await talking(1);
    m.answerTurn.mockResolvedValue({ rejected: "not_current" });
    await act(async () => h.result.current.answer("lot", "yes"));
    await waitFor(() => expect(h.result.current.view.phase === "talk" && h.result.current.view.notice).toBe("try_again"));
    expect(m.getGuide).toHaveBeenCalledTimes(2);
  });

  it("says why when the guide can't be shown", async () => {
    m.getGuide.mockResolvedValue("not_approved");
    const h = renderHook(() => useGuide("p1"));
    await waitFor(() => expect(h.result.current.view).toEqual({ phase: "refused", why: "not_approved" }));
  });
});
