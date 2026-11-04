import { describe, expect, it } from "vitest";
import type { Pt } from "../api";
import { dragDistance, fitView, frontFrame, fromFrame, houseBox, rayToBoundary, toFrame } from "./geometry";
import { NOISY96, RECT, TRAPEZOID } from "./fixtures";

const rect = RECT.outline!;
const inFrame = (box: Pt[]) => box.map((p) => toFrame(frontFrame(rect, "L1")!, p));
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

  it("houseBox uses the lot's own edge for a distance not entered yet", () => {
    const f = inFrame(houseBox(rect, "L1", { front: 30 })!);
    expect(span(f, 0).map(Math.round)).toEqual([0, 100]);
    expect(span(f, 1).map(Math.round)).toEqual([30, 200]);
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
