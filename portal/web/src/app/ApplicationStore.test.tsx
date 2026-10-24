import { act, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import * as api from "../api";
import * as apps from "../applications";
import { ApplicationProvider, useApplication } from "./ApplicationStore";

const FORM: apps.FormDef = { key: "use_permit", version: 1, ruleset_key: "adopted-v1.0", official_title: "Use Permit Application",
  sections: [], steps: [] };
const APP: apps.AppState = {
  id: "abc", form_key: "use_permit", form_version: 1, ruleset_key: "adopted-v1.0", status: "draft", revision: 3,
  property: { source: "lookup", parcel_id: 1, map_lot: "004-036", facts: {}, parcels_as_of: null, verified: true, disputed: false, note: "" },
  items: [], answers: [], notes: [], attachments: [], missing: [], newer_version: false,
};

let store: ReturnType<typeof useApplication>;
function Probe() {
  store = useApplication();
  return <p>{store.saveState}|{JSON.stringify(store.cur?.answers ?? [])}</p>;
}

async function mount() {
  render(<ApplicationProvider id="abc"><Probe /></ApplicationProvider>);
  await waitFor(() => expect(store.app).not.toBeNull());
}

function deferred<T>() {
  let resolve!: (v: T) => void;
  const promise = new Promise<T>((r) => { resolve = r; });
  return { promise, resolve };
}

beforeEach(() => {
  localStorage.clear();
  vi.spyOn(apps, "getApplication").mockResolvedValue(APP);
  vi.spyOn(apps, "getForm").mockResolvedValue(FORM);
  vi.spyOn(api, "getMe").mockResolvedValue({ email: "a@example.com", role: "applicant" });
});

describe("ApplicationStore", () => {
  it("saves stay in order", async () => {
    const save = vi.spyOn(apps, "saveAnswers")
      .mockResolvedValueOnce({ revision: 4, missing: [] })
      .mockResolvedValueOnce({ revision: 5, missing: [] });
    await mount();
    act(() => {
      void store.setAnswer("a", null, "one");
      void store.setAnswer("b", null, "two");
    });
    await act(() => store.flush());
    expect(save.mock.calls.map((c) => [c[1], c[2][0].field_id])).toEqual([[3, "a"], [4, "b"]]);
    expect(store.saveState).toBe("saved");
  });

  it("Continue waits for the pending save", async () => {
    const slow = deferred<apps.SaveResult>();
    vi.spyOn(apps, "saveAnswers").mockReturnValueOnce(slow.promise);
    await mount();
    act(() => { void store.setAnswer("a", null, "one"); });
    let flushed = false;
    const f = store.flush().then(() => { flushed = true; });
    await Promise.resolve();
    expect(flushed).toBe(false);
    expect(screen.getByText(/^saving\|/)).toBeInTheDocument();
    await act(async () => { slow.resolve({ revision: 4, missing: [] }); await f; });
    expect(flushed).toBe(true);
  });

  it("a conflict stops autosave and offers Load the latest", async () => {
    const save = vi.spyOn(apps, "saveAnswers").mockResolvedValueOnce({ conflict: 9 });
    await mount();
    await act(async () => { await store.setAnswer("a", null, "one"); });
    expect(store.saveState).toBe("conflict");
    await act(async () => { await store.setAnswer("b", null, "two"); });
    expect(save).toHaveBeenCalledTimes(1); // nothing more is sent until the latest is loaded
    vi.spyOn(apps, "getApplication").mockResolvedValue({ ...APP, revision: 9 });
    await act(() => store.reload());
    expect(store.saveState).toBe("idle");
    expect(store.app!.revision).toBe(9);
  });

  it("a failed save keeps the value and retries with the next change", async () => {
    const save = vi.spyOn(apps, "saveAnswers")
      .mockResolvedValueOnce("unavailable")
      .mockResolvedValueOnce({ revision: 4, missing: [] });
    await mount();
    await act(async () => { await store.setAnswer("a", null, "one"); });
    expect(store.saveState).toBe("error");
    expect(store.cur!.answers).toContainEqual({ field_id: "a", item_id: null, value: "one" });
    await act(async () => { await store.setAnswer("b", null, "two"); });
    expect(save.mock.calls[1][2].map((c) => c.field_id)).toEqual(["a", "b"]);
    expect(store.saveState).toBe("saved");
  });

  it("saved answers update cur immediately", async () => {
    vi.spyOn(apps, "saveAnswers").mockReturnValue(new Promise(() => {}));
    await mount();
    act(() => { void store.setAnswer("a", null, "one"); });
    expect(store.cur!.answers).toContainEqual({ field_id: "a", item_id: null, value: "one" });
  });

  it("a refused value is reported to the caller and not kept", async () => {
    vi.spyOn(apps, "saveAnswers").mockResolvedValueOnce({ invalid: [{ field_id: "a", item_id: null, reason: "out_of_range" }] });
    await mount();
    let outcome: unknown;
    await act(async () => { outcome = await store.setAnswer("a", null, 99); });
    expect(outcome).toEqual({ error: "out_of_range" });
    expect(store.cur!.answers).not.toContainEqual({ field_id: "a", item_id: null, value: 99 });
  });

  it("remembers the steps visited", async () => {
    await mount();
    act(() => store.markVisited("about_you"));
    expect(store.visited.has("about_you")).toBe(true);
    expect(JSON.parse(localStorage.getItem("portal.visited.abc")!)).toEqual(["about_you"]);
  });
});
