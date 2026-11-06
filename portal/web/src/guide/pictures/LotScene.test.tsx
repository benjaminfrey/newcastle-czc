import { fireEvent, render, screen } from "@testing-library/react";
import { expect, test, vi } from "vitest";
import { GuideTheme } from "../theme/GuideTheme";
import { LotScene, SPOTS } from "./LotScene";

const labels = Object.fromEntries(SPOTS.map((s) => [s.id, `Label ${s.id}`]));
const scene = (onSpot = vi.fn()) => {
  render(<GuideTheme><LotScene labels={labels} description="A Newcastle lot" onSpot={onSpot} /></GuideTheme>);
  return onSpot;
};

test("the scene is one picture with its description, and a spot for every place to tap", () => {
  scene();
  expect(screen.getByRole("img", { name: "A Newcastle lot" })).toBeInTheDocument();
  const ids = [...document.querySelectorAll("[data-spot]")].map((g) => g.getAttribute("data-spot"));
  expect(ids).toEqual(SPOTS.map((s) => s.id));
  expect(SPOTS.map((s) => s.id)).toEqual(["house_outline", "barn", "addition", "deck", "solar", "shed", "driveway",
    "wall", "sign", "shingle"]);
});

test("tapping a spot names it", () => {
  const onSpot = scene();
  fireEvent.click(document.querySelector('[data-spot="deck"] circle[data-hit]')!);
  expect(onSpot).toHaveBeenCalledWith("deck");
});

test("no spot is a tab stop: the list under the scene is the keyboard's way in", () => {
  scene();
  expect(document.querySelectorAll("[data-spot] [tabindex], [data-spot] [role=button]")).toHaveLength(0);
  for (const c of document.querySelectorAll("circle[data-hit]")) expect(c.getAttribute("aria-hidden")).toBe("true");
});

// Ruling (plan 5, Task 3): ten pins at a natural height can't all stand 48 px apart on a 320 px
// screen. At a 390 px phone they do; at 320 px their centres stay 40 px apart, each target is still
// 48 px across, and the list under the scene is the fallback.
function hitsAt(width: number) {
  const rect = { width, height: 2000, left: 0, top: 0, right: width, bottom: 2000, x: 0, y: 0, toJSON: () => ({}) };
  const spy = vi.spyOn(SVGElement.prototype, "getBoundingClientRect").mockReturnValue(rect as DOMRect);
  const { unmount } = render(<GuideTheme><LotScene labels={labels} description="A Newcastle lot" /></GuideTheme>);
  const svg = document.querySelector("svg[role=img]")!;
  const [, , vbW] = svg.getAttribute("viewBox")!.split(" ").map(Number);
  const ppu = width / vbW;
  const hits = [...document.querySelectorAll("circle[data-hit]")].map((c) => ({
    x: Number(c.getAttribute("cx")) * ppu, y: Number(c.getAttribute("cy")) * ppu, r: Number(c.getAttribute("r")) * ppu }));
  unmount(); spy.mockRestore();
  return hits;
}

function closest(hits: { x: number; y: number }[]) {
  let m = Infinity;
  for (let i = 0; i < hits.length; i++) for (let j = i + 1; j < hits.length; j++)
    m = Math.min(m, Math.hypot(hits[i].x - hits[j].x, hits[i].y - hits[j].y));
  return m;
}

test("spot targets are 48 px and stand apart on a 390 px phone", () => {
  const hits = hitsAt(390);
  for (const h of hits) expect(h.r).toBeGreaterThanOrEqual(24 - 1e-9);
  expect(closest(hits)).toBeGreaterThanOrEqual(48);
});

test("on a 320 px phone the targets stay 48 px and their centres 40 px apart", () => {
  const hits = hitsAt(320);
  for (const h of hits) expect(h.r).toBeGreaterThanOrEqual(24 - 1e-9);
  expect(closest(hits)).toBeGreaterThanOrEqual(40);
});
