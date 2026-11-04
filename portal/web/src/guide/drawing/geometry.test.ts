import { describe, expect, it } from "vitest";
import type { Outline, Pt } from "../api";
import { dragDistance, fitView, frontFrame, fromFrame, houseBox, rayToBoundary, toFrame } from "./geometry";
import { NOISY96, RECT, TRAPEZOID, WEDGE } from "./fixtures";

const rect = RECT.outline!;
const inFrame = (box: Pt[]) => box.map((p) => toFrame(frontFrame(rect, "L1")!, p));
const inFrameOf = (o: typeof rect, box: Pt[]) => box.map((p) => toFrame(frontFrame(o, "L1")!, p));
const span = (pts: Pt[], k: 0 | 1) => [Math.min(...pts.map((p) => p[k])), Math.max(...pts.map((p) => p[k]))];

function inside(poly: Pt[], p: Pt) {
  let c = false;
  for (let i = 0, j = poly.length - 1; i < poly.length; j = i++) {
    const [xi, yi] = poly[i]; const [xj, yj] = poly[j];
    if ((yi > p[1]) !== (yj > p[1]) && p[0] < ((xj - xi) * (p[1] - yi)) / (yj - yi) + xi) c = !c;
  }
  return c;
}

describe("drawing geometry", () => {
  it("fitView keeps the whole outline inside the view with its padding", () => {
    const { viewBox, scale } = fitView(rect, 20);
    const [x, y, w, h] = viewBox.split(" ").map(Number);
    for (const [px, py] of rect.parts[0]) {
      const vx = px * scale; const vy = -py * scale;
      expect(vx - x).toBeGreaterThanOrEqual(19.9); expect(x + w - vx).toBeGreaterThanOrEqual(19.9);
      expect(vy - y).toBeGreaterThanOrEqual(19.9); expect(y + h - vy).toBeGreaterThanOrEqual(19.9);
    }
  });

  it("frontFrame points v into the lot", () => {
    const f = frontFrame(rect, "L1")!;
    expect(f.v[0]).toBeCloseTo(0); expect(f.v[1]).toBeCloseTo(1);
    const back = fromFrame(f, toFrame(f, [12, 34]));
    expect(back[0]).toBeCloseTo(12); expect(back[1]).toBeCloseTo(34);
  });

  it("rayToBoundary finds the nearest crossing", () => {
    expect(rayToBoundary(rect.parts[0], [0, 0], [0, 1])).toBeCloseTo(100);
    expect(rayToBoundary(rect.parts[0], [0, 0], [1, 0])).toBeCloseTo(50);
    expect(rayToBoundary(rect.parts[0], [500, 0], [1, 0])).toBeNull();
  });

  it("houseBox places each edge at its entered distance", () => {
    const box = houseBox(rect, "L1", { front: 30, side_1: 20, side_2: 20, rear: 40 })!;
    const [u0, u1] = span(inFrame(box), 0); const [v0, v1] = span(inFrame(box), 1);
    expect(u0).toBeCloseTo(20, 0); expect(u1).toBeCloseTo(80, 0);
    expect(v0).toBeCloseTo(30, 0); expect(v1).toBeCloseTo(160, 0);
  });

  it("the first side is on the left seen from the road, and flip swaps it", () => {
    const d = { front: 30, side_1: 10, side_2: 30 };
    expect(span(inFrame(houseBox(rect, "L1", d)!), 0).map(Math.round)).toEqual([10, 70]);
    expect(span(inFrame(houseBox(rect, "L1", d, true)!), 0).map(Math.round)).toEqual([30, 90]);
  });

  it("houseBox needs the front distance", () => {
    expect(houseBox(rect, "L1", { side_1: 20 })).toBeNull();
  });

  it("houseBox puts a side not entered yet on the boundary, and a rear halfway back", () => {
    const f = inFrame(houseBox(rect, "L1", { front: 30 })!);
    expect(span(f, 0).map(Math.round)).toEqual([0, 100]);
    expect(span(f, 1).map(Math.round)).toEqual([30, 115]);
  });

  it("houseBox returns null when the distances cross", () => {
    expect(houseBox(rect, "L1", { front: 30, side_1: 400, side_2: 400 })).toBeNull();
    expect(houseBox(rect, "L1", { front: 150, rear: 100 })).toBeNull();
    expect(houseBox(rect, "L1", { front: 900 })).toBeNull();
  });

  it("houseBox works on a trapezoid", () => {
    const t = TRAPEZOID.outline!;
    const box = houseBox(t, "L1", { front: 10, side_1: 5, side_2: 5, rear: 10 })!;
    expect(box).toHaveLength(4);
    for (const p of box) expect(inside(t.parts[0], p)).toBe(true);
  });

  it("houseBox is null for an unknown front line", () => {
    expect(houseBox(rect, "L9", { front: 30 })).toBeNull();
  });

  it("dragDistance reads the distance a pointer sets", () => {
    const f = frontFrame(rect, "L1")!;
    expect(dragDistance(rect, "L1", "front", fromFrame(f, [50, 55]))).toBe(55);
    expect(dragDistance(rect, "L1", "rear", fromFrame(f, [50, 170]))).toBe(30);
    expect(dragDistance(rect, "L1", "side_1", fromFrame(f, [12.4, 90]))).toBe(12);
    expect(dragDistance(rect, "L1", "side_2", fromFrame(f, [70, 90]))).toBe(30);
    expect(dragDistance(rect, "L1", "side_1", fromFrame(f, [70, 90]), true)).toBe(30);
    expect(dragDistance(rect, "L1", "front", fromFrame(f, [50, -40]))).toBe(0);
  });

  it("geometry copes with 96 vertices", () => {
    const n = NOISY96.outline!;
    expect(n.parts[0]).toHaveLength(96);
    const box = houseBox(n, "L1", { front: 30, side_1: 20, side_2: 20, rear: 40 })!;
    expect(box).toHaveLength(4);
    expect(box.flat().some(Number.isNaN)).toBe(false);
  });
});

describe("a front line that bends outward (lot 4-36)", () => {
  it("frontFrame still points v into the lot", () => {
    const w = WEDGE.outline!;
    const f = frontFrame(w, "L1")!;
    const n = w.parts[0].length;
    const c: Pt = [w.parts[0].reduce((s, p) => s + p[0], 0) / n, w.parts[0].reduce((s, p) => s + p[1], 0) / n];
    expect(toFrame(f, c)[1]).toBeGreaterThan(0);
  });

  it("houseBox gives a real box inside the lot", () => {
    const w = WEDGE.outline!;
    const box = houseBox(w, "L1", { front: 30, side_1: 20, side_2: 10, rear: 10 })!;
    const f = inFrameOf(w, box);
    expect(span(f, 1)[1] - span(f, 1)[0]).toBeGreaterThan(50);
    for (const p of box) expect(inside(w.parts[0], p)).toBe(true);
  });
});

// --- final review findings 3 and 4 ---

// A lot whose rear line slants: 100 ft wide, 200 ft deep on the west and 120 ft on the east.
const SLANT: Outline = {
  units: "ft", approximate: true, parts: [[[50, -100], [-50, -100], [-50, 100], [50, 20]]],
  lines: [
    { id: "L1", points: [[50, -100], [-50, -100]], length_ft: 100, street: { name: "Sheepscot Road", type: "R2" } },
    { id: "L2", points: [[-50, -100], [-50, 100]], length_ft: 200, street: null },
    { id: "L3", points: [[-50, 100], [50, 20]], length_ft: 128, street: null },
    { id: "L4", points: [[50, 20], [50, -100]], length_ft: 120, street: null },
  ], streets: [] };
const SLANT_ROLES = { L1: "front", L2: "side", L3: "rear", L4: "side" } as const;

function segPt(p: Pt, a: Pt, b: Pt) {
  const dx = b[0] - a[0]; const dy = b[1] - a[1];
  const t = Math.max(0, Math.min(1, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / (dx * dx + dy * dy)));
  return Math.hypot(p[0] - (a[0] + t * dx), p[1] - (a[1] + t * dy));
}
const distTo = (box: Pt[], line: Pt[]) => Math.min(...box.map((p) => segPt(p, line[0], line[1])));

describe("distances are measured from the lot lines themselves (finding 3)", () => {
  it("the house keeps its rear distance from a slanted rear line", () => {
    const box = houseBox(SLANT, "L1", { front: 20, side_1: 15, side_2: 15, rear: 15 }, false, SLANT_ROLES)!;
    expect(distTo(box, SLANT.lines[2].points)).toBeGreaterThanOrEqual(14.5);
    expect(distTo(box, SLANT.lines[1].points)).toBeGreaterThanOrEqual(14.5);
    expect(distTo(box, SLANT.lines[3].points)).toBeGreaterThanOrEqual(14.5);
  });

  it("a drag reads the distance to the slanted line, not along the front's axes", () => {
    // A point 20 ft straight back from the slanted rear line's middle.
    const n: Pt = [80 / Math.hypot(100, 80), 100 / Math.hypot(100, 80)];
    const p: Pt = [0 - n[0] * 20, 60 - n[1] * 20];
    expect(dragDistance(SLANT, "L1", "rear", p, false, SLANT_ROLES)).toBe(20);
  });
});

describe("a front setback of 0 (finding 4)", () => {
  it("still draws the house, on the front line", () => {
    const box = houseBox(rect, "L1", { front: 0, side_1: 5, side_2: 5, rear: 5 })!;
    expect(box).not.toBeNull();
    expect(span(inFrame(box), 1)[0]).toBeCloseTo(0, 1);
  });

  it("works at any rotation", () => {
    for (const t of [0.3, 1.0, 2.0]) {
      const r = (p: Pt): Pt => [p[0] * Math.cos(t) - p[1] * Math.sin(t), p[0] * Math.sin(t) + p[1] * Math.cos(t)];
      const o: Outline = { ...rect, parts: [rect.parts[0].map(r)], lines: rect.lines.map((l) => ({ ...l, points: l.points.map(r) })) };
      expect(houseBox(o, "L1", { front: 0 })).not.toBeNull();
    }
  });
});
