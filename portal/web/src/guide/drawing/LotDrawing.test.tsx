import { fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { expect, test, vi } from "vitest";
import type { Drawing, Pt } from "../api";
import { GuideTheme } from "../theme/GuideTheme";
import { CORNER, NOISY96, RECT, SECONDARY, SECONDARY_WEST } from "./fixtures";
import { fitView, fromFrame, frontFrame } from "./geometry";
import { LotDrawing } from "./LotDrawing";

function draw(drawing: Drawing, props: Partial<Parameters<typeof LotDrawing>[0]> = {}) {
  const utils = render(<GuideTheme><LotDrawing drawing={drawing} distances={{}} {...props} /></GuideTheme>);
  return { ...utils, svg: utils.container.querySelector("svg[role=img]") as SVGSVGElement };
}

// jsdom lays nothing out: give the SVG a box the size of its viewBox, so a client point is a view point.
function layOut(svg: SVGSVGElement, drawing: Drawing) {
  const [x, y, w, h] = fitView(drawing.outline!).viewBox.split(" ").map(Number);
  svg.getBoundingClientRect = () => ({ left: 0, top: 0, width: w, height: h, right: w, bottom: h, x: 0, y: 0, toJSON: () => ({}) });
  const { scale } = fitView(drawing.outline!);
  return (p: Pt) => ({ clientX: p[0] * scale - x, clientY: -p[1] * scale - y });
}

test("it shows the approximate caption", () => {
  draw(RECT);
  expect(screen.getByText("Approximate: from the Town's tax map, not a survey")).toBeVisible();
});

test("the svg has an accessible name", () => {
  const { svg } = draw(RECT);
  expect(svg).toHaveAccessibleName(/A drawing of your lot from the Town's tax map, with 4 lot lines/);
});

test("it labels each line with its length", () => {
  const { container } = draw(RECT);
  const labels = [...container.querySelectorAll("[data-line-label]")].map((t) => t.textContent);
  expect(labels.sort()).toEqual(["about 100 ft", "about 100 ft", "about 200 ft", "about 200 ft"]);
});

test("it draws a strip for each role with a minimum and none for a frontage", () => {
  const { container } = draw(CORNER);
  const strips = [...container.querySelectorAll("[data-strip]")].map((s) => s.getAttribute("data-strip"));
  expect(strips.sort()).toEqual(["L1", "L2", "L4"]);   // front and both sides; L3 is another road frontage
});

test("it draws no strip when the limit has no numbers", () => {
  const none = { min: null, max: null, unit: "ft", reason: "two_districts", standard_keys: [] };
  const { container } = draw({ ...RECT, limits: { front: none, side: none, rear: none, secondary: none } });
  expect(container.querySelectorAll("[data-strip]")).toHaveLength(0);
});

test("it draws no strips or roles before the front is chosen", () => {
  const { container } = draw({ ...RECT, front: null, roles: null });
  expect(container.querySelectorAll("[data-strip]")).toHaveLength(0);
  expect(container.querySelector("[data-front]")).toBeNull();
});

test("it draws the house box once the front distance is known", () => {
  expect(draw(RECT, { distances: { side_1: 20 } }).container.querySelector("[data-house]")).toBeNull();
  expect(draw(RECT, { distances: { front: 30 } }).container.querySelector("[data-house]")).not.toBeNull();
});

test("picking a line calls onPickLine, only when asking for the front", async () => {
  const onPickLine = vi.fn();
  const { container } = draw(RECT, { asking: "front", onPickLine });
  await userEvent.click(container.querySelector("[data-pick='L1']")!);
  expect(onPickLine).toHaveBeenCalledWith("L1");
  expect(draw(RECT, { onPickLine }).container.querySelector("[data-pick]")).toBeNull();
});

test("dragging the asked edge calls onDrag with the new distance", () => {
  const onDrag = vi.fn();
  const { svg, container } = draw(RECT, { asking: "front_setback", distances: { front: 30 }, onDrag });
  const at = layOut(svg, RECT);
  const f = frontFrame(RECT.outline!, "L1")!;
  const handle = container.querySelector("[data-handle='front']")!;
  fireEvent.pointerDown(handle, { ...at(fromFrame(f, [50, 30])), pointerId: 1 });
  fireEvent.pointerMove(svg, { ...at(fromFrame(f, [50, 55])), pointerId: 1 });
  fireEvent.pointerUp(svg, { pointerId: 1 });
  expect(onDrag).toHaveBeenLastCalledWith(55);
  fireEvent.pointerMove(svg, { ...at(fromFrame(f, [50, 80])), pointerId: 1 });
  expect(onDrag).toHaveBeenCalledTimes(1);   // released: moving no longer drags
});

test("only the asked edge has a handle", () => {
  const { container } = draw(RECT, { asking: "side_1", distances: { front: 30, side_1: 20 } });
  expect([...container.querySelectorAll("[data-handle]")].map((h) => h.getAttribute("data-handle"))).toEqual(["side_1"]);
  expect(container.querySelector("[data-handle]")).toHaveAttribute("aria-hidden", "true");
  expect(draw(RECT, { distances: { front: 30 } }).container.querySelector("[data-handle]")).toBeNull();
});

test("Swap sides flips which side the first distance is on", async () => {
  const { container } = draw(RECT, { distances: { front: 30, side_1: 10, side_2: 30 } });
  const xs = () => container.querySelector("[data-house]")!.getAttribute("points")!.split(" ").map((p) => Number(p.split(",")[0]));
  const before = Math.min(...xs());
  await userEvent.click(screen.getByRole("button", { name: "Swap sides" }));
  expect(Math.min(...xs())).toBeGreaterThan(before);
});

test("there is no Swap sides button until a side distance is known", () => {
  draw(RECT, { distances: { front: 30 } });
  expect(screen.queryByRole("button", { name: "Swap sides" })).toBeNull();
});

test("it renders a 96-vertex lot", () => {
  const { container } = draw(NOISY96, { distances: { front: 30, side_1: 20, side_2: 20, rear: 40 } });
  expect(container.querySelector("[data-lot]")!.getAttribute("points")!.split(" ")).toHaveLength(96);
  expect(container.querySelector("[data-house]")).not.toBeNull();
});

// --- final review findings 1, 2, 7 and 8 ---

test("tapping a line that isn't along a road chooses A different line", async () => {
  const onPickLine = vi.fn();
  const { container } = draw(RECT, { asking: "front", onPickLine });
  await userEvent.click(container.querySelector("[data-pick='L3']")!);
  expect(onPickLine).toHaveBeenCalledWith("other");
});

test("a drag is read through the letterbox when the drawing is shorter than its box", () => {
  // RECT is twice as deep as it is wide; in a wide, short box the picture sits in the middle.
  const onDrag = vi.fn();
  const { svg, container } = draw(RECT, { asking: "side_1", distances: { front: 30, side_1: 20 }, onDrag });
  const [x, y, w, h] = fitView(RECT.outline!).viewBox.split(" ").map(Number);
  const k = 0.5;   // drawn at half size, centred in a box twice as wide as that
  const width = w * k * 2; const height = h * k;
  svg.getBoundingClientRect = () => ({ left: 0, top: 0, width, height, right: width, bottom: height, x: 0, y: 0, toJSON: () => ({}) });
  const { scale } = fitView(RECT.outline!);
  const f = frontFrame(RECT.outline!, "L1")!;
  const at = (q: Pt) => { const p = fromFrame(f, q); return { clientX: (width - w * k) / 2 + (p[0] * scale - x) * k, clientY: (-p[1] * scale - y) * k, pointerId: 1 }; };
  fireEvent.pointerDown(container.querySelector("[data-handle='side_1']")!, at([20, 80]));
  fireEvent.pointerMove(svg, at([12, 80]));
  expect(onDrag).toHaveBeenLastCalledWith(12);
});

test("the handle and the line targets are 48 px across on screen", () => {
  const [, , w] = fitView(RECT.outline!).viewBox.split(" ").map(Number);
  const spy = vi.spyOn(SVGSVGElement.prototype, "getBoundingClientRect").mockReturnValue(
    { left: 0, top: 0, width: w / 2, height: 300, right: w / 2, bottom: 300, x: 0, y: 0, toJSON: () => ({}) });
  const { container } = draw(RECT, { asking: "side_1", distances: { front: 30, side_1: 20 } });
  expect(Number(container.querySelector("[data-handle]")!.getAttribute("r"))).toBeCloseTo(48);   // 24 px at half scale
  const picks = draw(RECT, { asking: "front" }).container.querySelector("[data-pick]")!;
  expect(Number(picks.getAttribute("stroke-width"))).toBeCloseTo(96);
  spy.mockRestore();
});

test("the drawing doesn't stop a phone from scrolling; only the handle takes the touch", () => {
  const { svg, container } = draw(RECT, { asking: "side_1", distances: { front: 30, side_1: 20 } });
  expect(svg.style.touchAction).not.toBe("none");
  expect((container.querySelector("[data-handle]") as SVGElement).style.touchAction).toBe("none");
});

test("a corner lot draws its secondary strip and puts that edge's handle beside the other road", () => {
  for (const [d, east] of [[SECONDARY, true], [SECONDARY_WEST, false]] as const) {
    const { container, unmount } = draw(d, { distances: { front: 30 }, asking: "secondary" });
    const road = d.roles!.L4 === "secondary" ? "L4" : "L2";
    expect(container.querySelector(`[data-strip=${road}]`)).not.toBeNull();
    const h = container.querySelector("[data-handle=side_2]")!;
    expect(Number(h.getAttribute("cx")) > 0).toBe(east);
    // The edge facing the road is fixed by the road, so the sides can't be swapped.
    expect(screen.queryByRole("button", { name: "Swap sides" })).toBeNull();
    unmount();
  }
});
