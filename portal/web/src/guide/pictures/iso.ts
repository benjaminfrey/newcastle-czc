// The one view every picture shares (guided plan 5): the lot in feet, x east, y north and z up,
// seen from the south-west and above, so the road runs along the front. A 2:1 dimetric
// projection: a foot east goes right and up the picture, a foot north left and up.
export type P3 = [number, number, number];

export const iso = (x: number, y: number, z: number): [number, number] => [x - y, -(x + y) / 2 - z];

// An SVG points list for a polygon given in feet.
export const pts = (ps: P3[]) => ps.map((p) => iso(...p).join(",")).join(" ");

export type Box = { x0: number; x1: number; y0: number; y1: number; h: number; rise: number };

// A building with a gable roof whose ridge runs east–west, as the faces the view sees, back to
// front: its west wall and gable, its south wall, then the roof's north and south slopes.
export function gabled(b: Box) {
  const { x0, x1, y0, y1, h, rise } = b;
  const ym = (y0 + y1) / 2; const top = h + rise;
  return {
    west: [[x0, y0, 0], [x0, y1, 0], [x0, y1, h], [x0, ym, top], [x0, y0, h]] as P3[],
    south: [[x0, y0, 0], [x1, y0, 0], [x1, y0, h], [x0, y0, h]] as P3[],
    north: [[x0, ym, top], [x1, ym, top], [x1, y1, h], [x0, y1, h]] as P3[],
    roof: [[x0, y0, h], [x1, y0, h], [x1, ym, top], [x0, ym, top]] as P3[],
  };
}
