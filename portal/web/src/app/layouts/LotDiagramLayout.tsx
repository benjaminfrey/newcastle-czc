import { useEffect, useState, type ReactNode } from "react";
import { getProperty, type Facts } from "../../api";

type Geometry = Facts["geometry"];

// The lot's outer ring, projected into a box (north up, aspect kept).
export function projectOutline(geometry: Geometry, w: number, h: number, pad = 10): [number, number][] {
  const ring = geometry.coordinates.flat(1).sort((a, b) => b.length - a.length)[0] ?? [];
  const xs = ring.map((p) => p[0]);
  const ys = ring.map((p) => p[1]);
  const [x0, x1, y0, y1] = [Math.min(...xs), Math.max(...xs), Math.min(...ys), Math.max(...ys)];
  const midLat = ((y0 + y1) / 2) * (Math.PI / 180);
  const sx = Math.cos(midLat); // degrees of longitude are shorter than latitude here
  const scale = Math.min((w - 2 * pad) / ((x1 - x0) * sx || 1), (h - 2 * pad) / ((y1 - y0) || 1));
  return ring.map(([x, y]) => [pad + (x - x0) * sx * scale, h - pad - (y - y0) * scale]);
}

// The lot (or a plain square when the Town's map doesn't know it) with the building as a box.
export function LotOutline({ geometry }: { geometry: Geometry | null }) {
  const pts = geometry ? projectOutline(geometry, 200, 200) : [[10, 10], [190, 10], [190, 190], [10, 190], [10, 10]];
  return (
    <figure className="flex flex-col items-center gap-1">
      <svg viewBox="0 0 200 200" className="size-48" role="img" aria-label="Drawing of your lot with the building, not to scale">
        <polygon points={pts.map((p) => p.join(",")).join(" ")} fill="var(--app-selection)" stroke="var(--app-seal)" strokeWidth="2" />
        <rect x="80" y="80" width="40" height="40" fill="var(--app-row)" stroke="var(--app-label)" strokeWidth="2" />
      </svg>
      <figcaption className="text-[13px] text-[var(--app-secondary-label)]">Not to scale</figcaption>
    </figure>
  );
}

type Sides = { front: ReactNode; side1: ReactNode; side2: ReactNode; rear: ReactNode };

// The four setbacks placed beside the sides they measure: front (toward the road) above, the
// rear below, the two sides left and right of the drawing.
export default function LotDiagramLayout({ parcelId, street, sides }: { parcelId: number | null; street?: string | null; sides: Sides }) {
  const [geometry, setGeometry] = useState<Geometry | null>(null);
  useEffect(() => {
    if (parcelId === null) return;
    getProperty(parcelId).then((f) => { if (f && typeof f === "object") setGeometry(f.geometry); });
  }, [parcelId]);
  return (
    <div className="flex flex-col gap-3">
      <p className="text-center text-[15px] text-[var(--app-secondary-label)]">
        The front is the side along {street ?? "the road"}.
      </p>
      <div className="grid grid-cols-1 gap-2 sm:grid-cols-[1fr_auto_1fr] sm:items-center">
        <div className="sm:col-span-3">{sides.front}</div>
        <div>{sides.side1}</div>
        <div className="order-first sm:order-none"><LotOutline geometry={geometry} /></div>
        <div>{sides.side2}</div>
        <div className="sm:col-span-3">{sides.rear}</div>
      </div>
    </div>
  );
}
