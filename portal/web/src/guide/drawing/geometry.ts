// Geometry for drawing the lot (guided plan 4). It only places things on the picture: it never
// reads a standard or a limit, and never says whether anything fits (decision 12). Coordinates
// are the API's feet, x east and y north.
import type { Outline, Pt } from "../api";

export type Frame = { origin: Pt; u: Pt; v: Pt };
export type Distances = { front?: number; side_1?: number; side_2?: number; rear?: number };
export type Edge = keyof Distances;

const EPS = 1e-6;
const add = (a: Pt, b: Pt): Pt => [a[0] + b[0], a[1] + b[1]];
const sub = (a: Pt, b: Pt): Pt => [a[0] - b[0], a[1] - b[1]];
const mul = (a: Pt, k: number): Pt => [a[0] * k, a[1] * k];
const dot = (a: Pt, b: Pt) => a[0] * b[0] + a[1] * b[1];
const cross = (a: Pt, b: Pt) => a[0] * b[1] - a[1] * b[0];

export function inside(poly: Pt[], p: Pt): boolean {
  let c = false;
  for (let i = 0, j = poly.length - 1; i < poly.length; j = i++) {
    const [xi, yi] = poly[i]; const [xj, yj] = poly[j];
    if ((yi > p[1]) !== (yj > p[1]) && p[0] < ((xj - xi) * (p[1] - yi)) / (yj - yi) + xi) c = !c;
  }
  return c;
}

/** A viewBox that holds the whole outline with `pad` view units round it. SVG's y runs down. */
export function fitView(outline: Outline, pad = 20, size = 400): { viewBox: string; scale: number } {
  const pts = outline.parts.flat();
  const xs = pts.map((p) => p[0]); const ys = pts.map((p) => p[1]);
  const w = Math.max(...xs) - Math.min(...xs); const h = Math.max(...ys) - Math.min(...ys);
  const scale = size / Math.max(w, h, 1);
  const x = Math.min(...xs) * scale - pad; const y = -Math.max(...ys) * scale - pad;
  return { viewBox: `${x} ${y} ${w * scale + 2 * pad} ${h * scale + 2 * pad}`, scale };
}

/** The front line's frame: u along it, v (u's left-hand normal) into the lot, origin at its
 *  end with the smaller u. Null when there is no such line. */
export function frontFrame(outline: Outline, frontId: string): Frame | null {
  const line = outline.lines.find((l) => l.id === frontId);
  if (!line) return null;
  const a = line.points[0]; const b = line.points[line.points.length - 1];
  const len = Math.hypot(b[0] - a[0], b[1] - a[1]) || 1;
  // The API's lines run clockwise round the lot (y north), so the lot is on each line's right.
  // (Probing beside the chord's middle fails for a front that bends outward, as on lot 4-36.)
  const u: Pt = [-(b[0] - a[0]) / len, -(b[1] - a[1]) / len];
  const v: Pt = [-u[1], u[0]];
  const origin = line.points.reduce((m, p) => (dot(p, u) < dot(m, u) ? p : m), line.points[0]);
  return { origin, u, v };
}

export const toFrame = (f: Frame, p: Pt): Pt => [dot(sub(p, f.origin), f.u), dot(sub(p, f.origin), f.v)];
export const fromFrame = (f: Frame, q: Pt): Pt => add(f.origin, add(mul(f.u, q[0]), mul(f.v, q[1])));

/** Distance from `from` along the unit vector `dir` to the nearest boundary crossing, or null. */
export function rayToBoundary(poly: Pt[], from: Pt, dir: Pt): number | null {
  let best: number | null = null;
  for (let i = 0; i < poly.length; i++) {
    const a = poly[i]; const b = poly[(i + 1) % poly.length];
    const e = sub(b, a); const den = cross(dir, e);
    if (Math.abs(den) < EPS) continue;
    const w = sub(a, from);
    const t = cross(w, e) / den; const s = cross(w, dir) / den;
    if (t > EPS && s >= -EPS && s <= 1 + EPS && (best === null || t < best)) best = t;
  }
  return best;
}

/** The nearest boundary u left and right of `uMid` within vFront < v < vRear, or null when the
 *  boundary crosses the middle there. Points are in the front frame. */
function bandAround(ring: Pt[], v0: number, v1: number, uMid: number): [number, number] | null {
  const lo = v0 + EPS; const hi = v1 - EPS;
  let left = -Infinity; let right = Infinity;
  for (let i = 0; i < ring.length; i++) {
    let [a, b] = [ring[i], ring[(i + 1) % ring.length]];
    if (a[1] > b[1]) [a, b] = [b, a];
    if (b[1] < lo || a[1] > hi) continue;
    const at = (v: number): Pt => (b[1] === a[1] ? a : [a[0] + ((v - a[1]) * (b[0] - a[0])) / (b[1] - a[1]), v]);
    const p = a[1] < lo ? at(lo) : a; const q = b[1] > hi ? at(hi) : b;
    if ((p[0] - uMid) * (q[0] - uMid) <= 0) return null;
    for (const u of [p[0], q[0]]) {
      if (u < uMid) left = Math.max(left, u); else right = Math.min(right, u);
    }
  }
  return Number.isFinite(left) && Number.isFinite(right) ? [left, right] : null;
}

function spanOfFront(outline: Outline, f: Frame, frontId: string): [number, number] {
  const us = outline.lines.find((l) => l.id === frontId)!.points.map((p) => toFrame(f, p)[0]);
  return [Math.min(...us), Math.max(...us)];
}

/** The house as the person's distances place it, in the front frame: front edge at `front`
 *  from the front line, the rest at their distances from the boundary (a side not entered yet on
 *  the boundary, a rear not entered yet halfway back). Null without a front distance, or when
 *  the distances cross. */
export function houseBox(outline: Outline, frontId: string, d: Distances, flip = false): Pt[] | null {
  const f = frontFrame(outline, frontId);
  if (!f || d.front == null) return null;
  const poly = outline.parts[0];
  const [u0, u1] = spanOfFront(outline, f, frontId);
  const uMid = (u0 + u1) / 2;
  const start = fromFrame(f, [uMid, d.front]);
  if (!inside(poly, start)) return null;
  const toRear = rayToBoundary(poly, start, f.v);
  if (toRear == null) return null;
  // A rear edge not entered yet stops halfway back: run to the boundary, a box on a lot that
  // narrows away from the road (a wedge, like lot 4-36) would shrink to nothing. Picture only.
  const vFront = d.front; const vRear = d.front + (d.rear == null ? toRear / 2 : toRear - d.rear);
  if (vFront >= vRear) return null;
  // How wide the lot is across the box's whole depth: every boundary edge is clipped to the band
  // between the box's front and rear, and the nearest boundary point on each side of the middle
  // limits that side. Exact for any outline (sampling a few depths let a corner poke out of a lot
  // whose edge pinches in between them).
  const band = bandAround(poly.map((p) => toFrame(f, p)), vFront, vRear, uMid);
  if (!band) return null;
  const [bLeft, bRight] = band;
  const left = flip ? d.side_2 : d.side_1; const right = flip ? d.side_1 : d.side_2;
  const uLeft = bLeft + (left ?? 0); const uRight = bRight - (right ?? 0);
  if (uLeft >= uRight) return null;
  return [[uLeft, vFront], [uRight, vFront], [uRight, vRear], [uLeft, vRear]].map((q) => fromFrame(f, q as Pt));
}

/** The distance a pointer at `p` sets for one edge of the house: whole feet, never below 0. */
export function dragDistance(outline: Outline, frontId: string, edge: Edge, p: Pt, flip = false): number {
  const f = frontFrame(outline, frontId);
  if (!f) return 0;
  const poly = outline.parts[0];
  const q = toFrame(f, p);
  const left = flip ? "side_2" : "side_1";
  let n: number | null;
  if (edge === "front") n = q[1];
  else if (edge === "rear") n = inside(poly, p) ? rayToBoundary(poly, p, f.v) : null;
  else n = inside(poly, p) ? rayToBoundary(poly, p, edge === left ? mul(f.u, -1) : f.u) : null;
  return n == null ? 0 : Math.max(0, Math.round(n));
}
