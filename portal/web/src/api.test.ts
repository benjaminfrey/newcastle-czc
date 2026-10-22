import { describe, expect, it, vi } from "vitest";
import { getMe, getProperty, parcelAt, requestLink, searchProperty, verifyToken } from "./api";

const respond = (status: number, body: unknown = {}) =>
  vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response(JSON.stringify(body), { status }));
const offline = () => vi.spyOn(globalThis, "fetch").mockRejectedValue(new TypeError("Failed to fetch"));

describe("api", () => {
  it("requestLink reports a lost connection as unreachable", async () => {
    offline();
    expect(await requestLink("a@example.com")).toBe("unreachable");
  });

  it("verifyToken tells an invalid link from an unavailable server", async () => {
    respond(400, { detail: "link_invalid" });
    expect(await verifyToken("t")).toBe("invalid");
    vi.restoreAllMocks();
    respond(502);
    expect(await verifyToken("t")).toBe("unavailable");
    vi.restoreAllMocks();
    offline();
    expect(await verifyToken("t")).toBe("unavailable");
  });

  it("getMe tells signed out from an unavailable server", async () => {
    respond(401, { detail: "signed_out" });
    expect(await getMe()).toBeNull();
    vi.restoreAllMocks();
    respond(500);
    expect(await getMe()).toBe("unavailable");
    vi.restoreAllMocks();
    offline();
    expect(await getMe()).toBe("unavailable");
  });

  it("property lookups report a rate limit as busy", async () => {
    respond(429, { detail: "too_many_requests" });
    expect(await searchProperty("461 Sheepscot")).toBe("busy");
    vi.restoreAllMocks();
    respond(429, { detail: "too_many_requests" });
    expect(await parcelAt(-69.5, 44.0)).toBe("busy");
    vi.restoreAllMocks();
    respond(429, { detail: "too_many_requests" });
    expect(await getProperty(1)).toBe("busy");
  });
});

describe("getUseGroups", () => {
  it("fetches the list once and keeps it", async () => {
    const { getUseGroups, clearUseGroupsCache } = await import("./api");
    clearUseGroupsCache();
    const spy = vi.spyOn(globalThis, "fetch").mockImplementation(async () => new Response("[]", { status: 200 }));
    await getUseGroups();
    await getUseGroups();
    expect(spy).toHaveBeenCalledTimes(1);
  });
});

