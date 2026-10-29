import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { addPart, clearFormCache, createProject, getForm, getProject, removePart, saveAnswers, saveNote, setTitle,
  submitProject } from "./projects";

const FORM = { key: "use_permit", version: 1, ruleset_key: "adopted-v1.0", official_title: "Use Permit Application", sections: [] };
const ok = (body: unknown, status = 200) =>
  new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });
const sent = (fetch: ReturnType<typeof vi.spyOn>, i = 0) => ({
  url: String(fetch.mock.calls[i][0]), method: (fetch.mock.calls[i][1] as RequestInit | undefined)?.method ?? "GET",
  body: (fetch.mock.calls[i][1] as RequestInit | undefined)?.body ? JSON.parse(String((fetch.mock.calls[i][1] as RequestInit).body)) : null,
});

beforeEach(() => clearFormCache());
afterEach(() => vi.restoreAllMocks());

describe("getForm", () => {
  it("says busy on 429 instead of handing back the error as a form", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response(JSON.stringify({ detail: "too_many_requests" }), { status: 429 }));
    expect(await getForm("use_permit", 1)).toBe("busy");
  });

  it("fetches each form version once", async () => {
    const spy = vi.spyOn(globalThis, "fetch").mockImplementation(async () => ok(FORM));
    expect(await getForm("use_permit", 1)).toEqual(FORM);
    expect(await getForm("use_permit", 1)).toEqual(FORM);
    expect(spy).toHaveBeenCalledTimes(1);
  });
});

describe("the project client", () => {
  it("creates a project from its property and parts", async () => {
    const fetch = vi.spyOn(globalThis, "fetch").mockResolvedValue(ok({ id: "p1" }, 201));
    expect(await createProject({ property: { source: "lookup", parcel_id: 7 }, disputed: false, note: "",
                                 parts: ["building", "driveway"], title: "A new building and a driveway at Sheepscot Road" }))
      .toEqual({ id: "p1" });
    expect(sent(fetch)).toEqual({ url: "/api/projects", method: "POST", body: {
      property: { source: "lookup", parcel_id: 7 }, disputed: false, note: "", parts: ["building", "driveway"],
      title: "A new building and a driveway at Sheepscot Road" } });
  });

  it("reads parts as the cards' items, part_id as item_id", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(ok({
      id: "p1", title: "T", status: "draft", revision: 2, ruleset_key: "adopted-v1.0", submitted_at: null,
      property: { map_lot: "004-036" }, forms: { cover_sheet: 1 }, form: FORM, needs: null,
      parts: [{ id: "b1", kind: "building", position: 0 }],
      answers: [{ field_id: "stories", part_id: "b1", value: 2, derived: false }],
      notes: [{ section_id: "s", part_id: null, text: "n" }],
      attachments: [{ id: "a", field_id: "f", part_id: "b1", filename: "x.pdf", content_type: "application/pdf", size_bytes: 1 }],
      missing: [{ field_id: "floor_area", part_id: "b1" }],
    }));
    const p = await getProject("p1");
    if (typeof p === "string") throw new Error(p);
    expect(p.items).toEqual([{ id: "b1", kind: "building", position: 0 }]);
    expect(p.answers).toEqual([{ field_id: "stories", item_id: "b1", value: 2, derived: false }]);
    expect(p.notes[0].item_id).toBeNull();
    expect(p.attachments[0].item_id).toBe("b1");
    expect(p.missing).toEqual([{ field_id: "floor_area", item_id: "b1" }]);
  });

  it("writes item_id as part_id", async () => {
    const fetch = vi.spyOn(globalThis, "fetch").mockImplementation(async () => ok({ revision: 4, missing: [{ field_id: "x", part_id: "b1" }] }));
    expect(await saveAnswers("p1", 3, [{ field_id: "stories", item_id: "b1", value: 2 }]))
      .toEqual({ revision: 4, missing: [{ field_id: "x", item_id: "b1" }] });
    expect(sent(fetch)).toEqual({ url: "/api/projects/p1/answers", method: "PUT",
      body: { base_revision: 3, changes: [{ field_id: "stories", part_id: "b1", value: 2 }] } });
    await saveNote("p1", 4, "proposed", null, "Weekends");
    expect(sent(fetch, 1)).toEqual({ url: "/api/projects/p1/notes", method: "PUT",
      body: { base_revision: 4, section_id: "proposed", part_id: null, text: "Weekends" } });
  });

  it("adds a part, with Copy Building 1, and removes one", async () => {
    const fetch = vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(ok({ id: "b2", revision: 4 }, 201))
      .mockResolvedValueOnce(ok({ revision: 5 }));
    expect(await addPart("p1", 3, "building", "b1")).toEqual({ revision: 4, missing: [], id: "b2" });
    expect(sent(fetch)).toEqual({ url: "/api/projects/p1/parts", method: "POST",
      body: { kind: "building", base_revision: 3, copy_from: "b1" } });
    expect(await removePart("p1", 4, "b2")).toEqual({ revision: 5, missing: [] });
    expect(sent(fetch, 1)).toEqual({ url: "/api/projects/p1/parts/b2", method: "DELETE", body: { base_revision: 4 } });
  });

  it("renames and sends", async () => {
    const fetch = vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(ok({ revision: 2 }))
      .mockResolvedValueOnce(ok({ revision: 3, status: "submitted" }));
    await setTitle("p1", 1, "Studio");
    expect(sent(fetch)).toEqual({ url: "/api/projects/p1/title", method: "PUT", body: { base_revision: 1, title: "Studio" } });
    expect(await submitProject("p1", 2)).toEqual({ revision: 3, missing: [] });
    expect(sent(fetch, 1)).toEqual({ url: "/api/projects/p1/submit", method: "POST", body: { base_revision: 2 } });
  });

  it("a locked project's writes come back as locked, not as a conflict", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(ok({ detail: "locked" }, 409));
    expect(await saveAnswers("p1", 3, [])).toBe("locked");
  });

  it("send with blanks left comes back with what is missing", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(ok({ detail: "incomplete", missing: [{ field_id: "x", part_id: null }] }, 422));
    expect(await submitProject("p1", 2)).toEqual({ incomplete: [{ field_id: "x", item_id: null }] });
  });
});
