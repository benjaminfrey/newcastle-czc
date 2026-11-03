import { afterEach, describe, expect, it, vi } from "vitest";
import { addNote, answerTurn, checkValue, getGuide, getOpenings, goBack, revisit, startGuide } from "./api";

const res = (status: number, body: unknown) =>
  new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });
const GUIDE = { revision: 3, opening: "new_house", current: null, history: [], ending: null, step: null,
  unsure: [], notes: [], drafts: [] };

afterEach(() => vi.restoreAllMocks());

describe("the guide's calls", () => {
  it.each([
    [res(401, { detail: "signed_out" }), "signed_out"],
    [res(404, { detail: "not_found" }), "not_found"],
    [res(404, { detail: "not_started" }), "not_started"],
    [res(409, { detail: "changed_elsewhere", revision: 4 }), { conflict: true }],
    [res(409, { detail: "locked" }), "locked"],
    [res(422, { detail: "out_of_range" }), { rejected: "out_of_range" }],
    [res(429, { detail: "too_many_requests" }), "busy"],
    [res(503, { detail: "guide_not_approved" }), "not_approved"],
    [res(500, {}), "unavailable"],
  ])("maps each refusal (%#)", async (response, expected) => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(response as Response);
    expect(await answerTurn("p1", "lot", "yes", 2)).toEqual(expected);
  });

  it("says unavailable when the request never completes", async () => {
    vi.spyOn(globalThis, "fetch").mockRejectedValue(new TypeError("offline"));
    expect(await getGuide("p1")).toBe("unavailable");
  });

  it("sends each change with its revision", async () => {
    const fetch = vi.spyOn(globalThis, "fetch").mockImplementation(async () => res(200, GUIDE));
    await startGuide("p1", "new_house", 1);
    await answerTurn("p1", "floor_area", 1800, 2);
    await goBack("p1", 3);
    await revisit("p1", "lot", 4);
    await addNote("p1", "A porch too.", 5);
    const calls = fetch.mock.calls.map(([u, i]) => [String(u), JSON.parse(String((i as RequestInit).body))]);
    expect(calls).toEqual([
      ["/api/projects/p1/guide", { opening: "new_house", base_revision: 1 }],
      ["/api/projects/p1/guide/answers", { turn_id: "floor_area", value: 1800, base_revision: 2 }],
      ["/api/projects/p1/guide/back", { base_revision: 3 }],
      ["/api/projects/p1/guide/revisit", { turn_id: "lot", base_revision: 4 }],
      ["/api/projects/p1/guide/notes", { body: "A porch too.", base_revision: 5 }],
    ]);
  });

  it("reads the openings", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(res(200, { openings: [{ id: "new_house", label: "A new house", part: "building" }] }));
    expect(await getOpenings("p1")).toEqual([{ id: "new_house", label: "A new house", part: "building" }]);
  });

  it("passes the check's abort signal", async () => {
    const fetch = vi.spyOn(globalThis, "fetch").mockResolvedValue(res(200, { result: null }));
    const c = new AbortController();
    expect(await checkValue("p1", "floor_area", 1800, c.signal)).toEqual({ result: null });
    expect((fetch.mock.calls[0][1] as RequestInit).signal).toBe(c.signal);
  });
});
