import { afterEach, describe, expect, it, vi } from "vitest";
import { followDeviceScheme } from "./colorScheme";

function stubMatchMedia(dark: boolean) {
  const listeners: ((e: { matches: boolean }) => void)[] = [];
  const mql = { matches: dark, addEventListener: (_: string, l: (e: { matches: boolean }) => void) => listeners.push(l),
                removeEventListener: vi.fn() };
  vi.stubGlobal("matchMedia", vi.fn(() => mql));
  return (next: boolean) => { mql.matches = next; listeners.forEach((l) => l({ matches: next })); };
}

afterEach(() => {
  vi.unstubAllGlobals();
  document.documentElement.removeAttribute("data-theme");
  document.documentElement.classList.remove("dark", "light");
});

describe("followDeviceScheme", () => {
  it("follows the device and its changes", () => {
    const change = stubMatchMedia(true);
    const stop = followDeviceScheme();
    expect(document.documentElement.dataset.theme).toBe("dark");
    expect(document.documentElement.classList.contains("dark")).toBe(true);
    change(false);
    expect(document.documentElement.dataset.theme).toBe("light");
    expect(document.documentElement.classList.contains("dark")).toBe(false);
    stop();
  });
});
