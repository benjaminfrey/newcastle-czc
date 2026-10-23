import { beforeEach, describe, expect, it, vi } from "vitest";
import { peekPendingStart, savePendingStart, takePendingStart } from "./pendingStart";

const START = {
  formKey: "use_permit",
  property: { source: "lookup" as const, parcel_id: 229, map_lot: "004-036", district_code: "D2", district_codes: ["D2"],
              on_state_highway: false, disputed: false, note: "", as_of: "2026-10-15" },
  useKey: "health_fitness_studio",
};

beforeEach(() => {
  localStorage.clear();
  sessionStorage.clear();
});

describe("pending start", () => {
  it("survives a new tab", () => {
    savePendingStart(START);
    sessionStorage.clear(); // the emailed link opens a tab with an empty session
    expect(peekPendingStart()).toEqual(START);
    expect(takePendingStart()).toEqual(START);
  });

  it("is taken once", () => {
    savePendingStart(START);
    expect(takePendingStart()).toEqual(START);
    expect(takePendingStart()).toBeNull();
  });

  it("blocked storage is nothing pending", () => {
    vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => { throw new Error("blocked"); });
    vi.spyOn(Storage.prototype, "getItem").mockImplementation(() => { throw new Error("blocked"); });
    expect(() => savePendingStart(START)).not.toThrow();
    expect(takePendingStart()).toBeNull();
  });
});
