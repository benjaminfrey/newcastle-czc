import { beforeEach, describe, expect, it, vi } from "vitest";
import { clearFormCache, getForm } from "./applications";

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
