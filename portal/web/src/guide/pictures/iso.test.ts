import { expect, test } from "vitest";
import { iso } from "./iso";

test("the origin stays put", () => {
  const [x, y] = iso(0, 0, 0);
  expect(x).toBeCloseTo(0);
  expect(y).toBeCloseTo(0);
});

test("east and north lean opposite ways and both go up the picture", () => {
  const [ex, ey] = iso(10, 0, 0);
  const [nx, ny] = iso(0, 10, 0);
  expect(Math.sign(ex)).toBe(-Math.sign(nx));
  expect(ey).toBeLessThan(0);
  expect(ny).toBeCloseTo(ey);
});

test("up goes straight up", () => {
  const [ux, uy] = iso(0, 0, 10);
  expect(ux).toBe(0);
  expect(uy).toBeLessThan(0);
});
