import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { addItem, clearFormCache, getForm } from "./applications";

const FORM = { key: "use_permit", version: 1, ruleset_key: "adopted-v1.0", official_title: "Use Permit Application", sections: [] };

beforeEach(() => clearFormCache());

describe("getForm", () => {
  it("says busy on 429 instead of handing back the error as a form", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response(JSON.stringify({ detail: "too_many_requests" }), { status: 429 }));
    expect(await getForm("use_permit", 1)).toBe("busy");
  });

  it("fetches each form version once", async () => {
    const spy = vi.spyOn(globalThis, "fetch").mockImplementation(async () => new Response(JSON.stringify(FORM), { status: 200 }));
    expect(await getForm("use_permit", 1)).toEqual(FORM);
    expect(await getForm("use_permit", 1)).toEqual(FORM);
    expect(spy).toHaveBeenCalledTimes(1);
  });

  it("does not keep a refusal", async () => {
    const spy = vi.spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(new Response("{}", { status: 503 }))
      .mockResolvedValueOnce(new Response(JSON.stringify(FORM), { status: 200 }));
    expect(await getForm("use_permit", 1)).toBe("unavailable");
    expect(await getForm("use_permit", 1)).toEqual(FORM);
    expect(spy).toHaveBeenCalledTimes(2);
  });
});

describe("addItem", () => {
  afterEach(() => vi.restoreAllMocks());
  const created = () => new Response(JSON.stringify({ id: "b2", revision: 4 }), { status: 201, headers: { "Content-Type": "application/json" } });

  it("Copy Building 1 sends the building to copy", async () => {
    const fetch = vi.spyOn(globalThis, "fetch").mockResolvedValue(created());
    expect(await addItem("abc", 3, "building", "b1")).toEqual({ revision: 4, missing: [], id: "b2" });
    expect(JSON.parse(String(fetch.mock.calls[0][1]!.body))).toEqual({ kind: "building", base_revision: 3, copy_from: "b1" });
  });

  it("a plain add sends no copy", async () => {
    const fetch = vi.spyOn(globalThis, "fetch").mockResolvedValue(created());
    await addItem("abc", 3, "building");
    expect(JSON.parse(String(fetch.mock.calls[0][1]!.body))).toEqual({ kind: "building", base_revision: 3 });
  });
});
