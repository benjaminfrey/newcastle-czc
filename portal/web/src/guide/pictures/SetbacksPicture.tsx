import { useTheme } from "@mui/material/styles";
import { WORDS } from "../words";
import { gabled, iso, pts, type Box, type P3 } from "./iso";
import { usePicturePalette } from "./palette";

// "How far from the lot lines" (guided plan 5, Task 7): the house on its lot in the scene's view,
// with an arrow from each lot line to the nearest part of the house. The arrows show where a
// setback is measured, never how far: there are no distances, and the names are the lot drawing's
// own approved rows.
const LOT = { x0: 0, x1: 64, y0: 0, y1: 72 };
const HOUSE: Box = { x0: 20, x1: 44, y0: 24, y1: 46, h: 12, rise: 9 };
const MX = (HOUSE.x0 + HOUSE.x1) / 2, MY = (HOUSE.y0 + HOUSE.y1) / 2;

const VIEW = (() => {
  const ps = ([[LOT.x0, -10, 0], [LOT.x1, -10, 0], [LOT.x1, LOT.y1, 0], [LOT.x0, LOT.y1, 0],
    [MX, MY, HOUSE.h + HOUSE.rise]] as P3[]).map((p) => iso(...p));
  const xs = ps.map((p) => p[0]); const ys = ps.map((p) => p[1]);
  const x = Math.min(...xs) - 40; const y = Math.min(...ys) - 10;
  return `${x} ${y} ${Math.max(...xs) + 40 - x} ${Math.max(...ys) + 10 - y}`;
})();

export function SetbacksPicture() {
  const c = usePicturePalette();
  const theme = useTheme();
  const rows = WORDS.drawing.rows;
  const f = gabled(HOUSE);
  const flat = (x0: number, x1: number, y0: number, y1: number): P3[] => [[x0, y0, 0], [x1, y0, 0], [x1, y1, 0], [x0, y1, 0]];
  // An arrow on the ground from a lot line to the house, and its name beside its middle. The names
  // are drawn last, so the house never hides one.
  const line = (from: P3, to: P3) => {
    const [x1, y1] = iso(...from); const [x2, y2] = iso(...to);
    const a = Math.atan2(y2 - y1, x2 - x1); const h = 4;
    const head = `${x2},${y2} ${x2 - h * Math.cos(a - 0.45)},${y2 - h * Math.sin(a - 0.45)} ${x2 - h * Math.cos(a + 0.45)},${y2 - h * Math.sin(a + 0.45)}`;
    return <g><line x1={x1} y1={y1} x2={x2} y2={y2} stroke={c.maple} strokeWidth={1.8} /><polygon points={head} fill={c.maple} /></g>;
  };
  const name = (from: P3, to: P3, label: string, anchor: "start" | "end", dx: number) => {
    const [lx, ly] = iso((from[0] + to[0]) / 2, (from[1] + to[1]) / 2, 0);
    return <text x={lx + dx} y={ly + 3} fontSize={7} textAnchor={anchor} fill={theme.palette.text.primary}
      stroke={theme.palette.background.paper} strokeWidth={2} paintOrder="stroke">{label}</text>;
  };
  const REAR: [P3, P3] = [[MX, LOT.y1, 0], [MX, HOUSE.y1, 0]];
  const SIDE_2: [P3, P3] = [[LOT.x1, MY, 0], [HOUSE.x1, MY, 0]];
  const FRONT: [P3, P3] = [[MX, LOT.y0, 0], [MX, HOUSE.y0, 0]];
  const SIDE_1: [P3, P3] = [[LOT.x0, MY, 0], [HOUSE.x0, MY, 0]];
  return (
    <svg viewBox={VIEW} style={{ width: "100%", height: "auto", display: "block" }} aria-hidden="true">
      <polygon points={pts(flat(LOT.x0, LOT.x1, -10, 0))} fill={c.stone} opacity={0.45} />
      <polygon points={pts(flat(LOT.x0, LOT.x1, LOT.y0, LOT.y1))} fill={c.lot} stroke={c.lotEdge} strokeWidth={1.5} />
      {line(...REAR)}
      {line(...SIDE_2)}
      <polygon points={pts(f.north)} fill={c.roofShade} />
      <polygon points={pts(f.west)} fill={c.clapboardShade} />
      <polygon points={pts(f.south)} fill={c.clapboard} />
      <polygon points={pts(f.roof)} fill={c.roof} />
      {line(...FRONT)}
      {line(...SIDE_1)}
      {name(...REAR, rows.rear, "end", -6)}
      {name(...SIDE_2, rows.side_2, "start", 6)}
      {name(...FRONT, rows.front, "start", 6)}
      {name(...SIDE_1, rows.side_1, "end", -6)}
    </svg>
  );
}
