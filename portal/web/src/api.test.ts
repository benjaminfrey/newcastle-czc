import { describe, expect, it, vi } from "vitest";
import { getMe, requestLink, verifyToken } from "./api";

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
});
