import type { Drawing, LotLine, Outline, Pt } from "../api";

const ROAD = { name: "Sheepscot Road", type: "R2" };
const NO_LIMITS: Drawing["limits"] = { front: null, side: null, rear: null };

function outlineOf(ring: Pt[], streets: (typeof ROAD | null)[]): Outline {
  const lines: LotLine[] = ring.map((p, i) => {
    const q = ring[(i + 1) % ring.length];
    return { id: `L${i + 1}`, points: [p, q], length_ft: Math.round(Math.hypot(q[0] - p[0], q[1] - p[1])),
      street: streets[i] ?? null };
  });
  return { units: "ft", approximate: true, parts: [ring], lines,
    streets: streets.some(Boolean) ? [{ name: ROAD.name, points: [[-120, -130], [120, -130]] }] : [] };
}

// 100 × 200 ft, clockwise from the south-east corner: L1 south (the road), L2 west, L3 north, L4 east.
export const RECT_OUTLINE = outlineOf([[50, -100], [-50, -100], [-50, 100], [50, 100]], [ROAD]);
export const RECT: Drawing = {
  outline: RECT_OUTLINE, front: "L1", roles: { L1: "front", L2: "side", L3: "rear", L4: "side" },
  limits: {
    front: { min: 25, max: null, unit: "ft", reason: null, standard_keys: ["d1/front"] },
    side: { min: 15, max: null, unit: "ft", reason: null, standard_keys: ["d1/side"] },
    rear: { min: 15, max: null, unit: "ft", reason: null, standard_keys: ["d1/rear"] },
  },
};

// Wider at the road (120 ft) than at the back (60 ft), 150 ft deep.
export const TRAPEZOID: Drawing = {
  outline: outlineOf([[60, -75], [-60, -75], [-30, 75], [30, 75]], [ROAD]),
  front: "L1", roles: { L1: "front", L2: "side", L3: "rear", L4: "side" }, limits: NO_LIMITS,
};

// A corner lot: roads on the south (front) and the north (another frontage).
export const CORNER: Drawing = {
  outline: outlineOf([[50, -50], [-50, -50], [-50, 50], [50, 50]], [ROAD, null, { name: "River Road", type: "R2" }]),
  front: "L1", roles: { L1: "front", L2: "side", L3: "frontage", L4: "side" },
  limits: { ...RECT.limits },
};

// A noisy 96-vertex lot, close to RECT's rectangle.
function noisy(): Pt[] {
  const corners: Pt[] = [[50, -100], [-50, -100], [-50, 100], [50, 100]];
  const out: Pt[] = [];
  corners.forEach((a, i) => {
    const b = corners[(i + 1) % 4];
    for (let k = 0; k < 24; k++) {
      const t = k / 24;
      const j = 0.4 * Math.sin(k * 1.3 + i);
      const nx = (b[1] - a[1]) / Math.hypot(b[0] - a[0], b[1] - a[1]);
      const ny = -(b[0] - a[0]) / Math.hypot(b[0] - a[0], b[1] - a[1]);
      out.push([a[0] + t * (b[0] - a[0]) + j * nx, a[1] + t * (b[1] - a[1]) + j * ny]);
    }
  });
  return out;
}
const NOISY_RING = noisy();
export const NOISY96: Drawing = {
  outline: { ...RECT_OUTLINE, parts: [NOISY_RING] }, front: "L1", roles: RECT.roles, limits: RECT.limits,
};
