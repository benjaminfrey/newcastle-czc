import { describe, expect, it, vi } from "vitest";
import { showSelection } from "./mapSelection";

const LOT = { type: "MultiPolygon" as const, coordinates: [[[[-69.6, 44.04], [-69.59, 44.04], [-69.59, 44.05], [-69.6, 44.04]]]] };

describe("showSelection", () => {
  it("outlines the new lot even while tiles are still loading", () => {
    // MapLibre's isStyleLoaded() is false while any tiles load; "load" fires only once per map,
    // so waiting for it left the outline on the previous lot.
    const source = { setData: vi.fn() };
    const map = { isStyleLoaded: () => false, getSource: () => source, fitBounds: vi.fn(), once: vi.fn() };
    showSelection(map, LOT);
    expect(source.setData).toHaveBeenCalledWith({ type: "Feature", properties: {}, geometry: LOT });
    expect(map.fitBounds).toHaveBeenCalled();
    expect(map.once).not.toHaveBeenCalled();
  });

  it("waits for the style only before the selection layer exists", () => {
    const map = { isStyleLoaded: () => false, getSource: () => undefined, fitBounds: vi.fn(), once: vi.fn() };
    showSelection(map, LOT);
    expect(map.once).toHaveBeenCalledWith("load", expect.any(Function));
  });

  it("clears the outline when nothing is selected", () => {
    const source = { setData: vi.fn() };
    const map = { isStyleLoaded: () => true, getSource: () => source, fitBounds: vi.fn(), once: vi.fn() };
    showSelection(map, null);
    expect(source.setData).toHaveBeenCalledWith({ type: "FeatureCollection", features: [] });
    expect(map.fitBounds).not.toHaveBeenCalled();
  });
});
