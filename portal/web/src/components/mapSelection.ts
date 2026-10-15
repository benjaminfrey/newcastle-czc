import type { Facts } from "../api";

type Lot = Facts["geometry"];

// Just the parts of a MapLibre map this needs, so it can be tested without WebGL.
export type SelectionMap = {
  getSource(id: string): unknown;
  fitBounds(bounds: [[number, number], [number, number]], options?: { padding?: number; maxZoom?: number }): unknown;
  once(event: "load", listener: () => void): unknown;
};

type DataSource = { setData(data: unknown): unknown };

// Outline the chosen lot and zoom to it. Waits only until the style has created the
// "selected" source: MapLibre's isStyleLoaded() is false whenever any tiles are still
// loading, and its "load" event fires once per map, so waiting on those could leave
// the outline on the previous lot.
export function showSelection(map: SelectionMap, lot: Lot | null): void {
  const source = map.getSource("selected") as DataSource | undefined;
  if (!source) {
    map.once("load", () => showSelection(map, lot));
    return;
  }
  source.setData(lot ? { type: "Feature", properties: {}, geometry: lot } : { type: "FeatureCollection", features: [] });
  if (!lot) return;
  let [w, s, e, n] = [Infinity, Infinity, -Infinity, -Infinity];
  for (const poly of lot.coordinates) {
    for (const ring of poly) {
      for (const [x, y] of ring) {
        w = Math.min(w, x); s = Math.min(s, y); e = Math.max(e, x); n = Math.max(n, y);
      }
    }
  }
  map.fitBounds([[w, s], [e, n]], { padding: 40, maxZoom: 18 });
}
