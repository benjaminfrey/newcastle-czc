import { useTheme } from "@mui/material/styles";
import { useLayoutEffect, useRef, useState } from "react";
import { gabled, iso, pts, type Box, type P3 } from "./iso";
import { usePicturePalette } from "./palette";

// The opening scene (guided plan 5, design §5–6): a Newcastle lot with a cape, its ell and a red
// barn in a row along the road, a stone wall, a maple, and a shed out back. Each place to tap is
// a pin standing over the thing it names. The picture is one image to a screen reader; the list
// under it is the way in for a keyboard (§6.3), so no pin is a tab stop.

// Each pin stands `lift` feet over the point it names. Placed so that at a 390 px phone every 48 px
// target stands clear of the others, and at 320 px their centres stay 40 px apart.
// `label`: where its name sits, clear of a neighbour's (to the right unless it says).
export const SPOTS: { id: string; at: P3; lift: number; label?: "left" | "below" }[] = [
  { id: "house_outline", at: [0, 100, 0], lift: 20 },
  { id: "barn", at: [140, 40, 8], lift: 29, label: "left" },
  { id: "addition", at: [-4, 50, 0], lift: 10 },
  { id: "deck", at: [60, 86, 3], lift: 30 },
  { id: "solar", at: [80, 54, 15], lift: 14 },
  { id: "shed", at: [158, 96, 8], lift: 26 },
  { id: "driveway", at: [112, 8, 0], lift: 18 },
  { id: "wall", at: [60, 2, 3], lift: 26 },
  { id: "sign", at: [160, 4, 10], lift: 29 },
  { id: "shingle", at: [38, 50, 6], lift: 10, label: "below" },
]

const LOT = { x0: -12, x1: 168, y0: 0, y1: 118 };
const ROAD = -16;
const CAPE: Box = { x0: 15, x1: 62, y0: 50, y1: 74, h: 14, rise: 12 };
const ELL: Box = { x0: 62, x1: 92, y0: 50, y1: 70, h: 10, rise: 7 };
const BARN: Box = { x0: 100, x1: 150, y0: 30, y1: 76, h: 18, rise: 14 };
const SHED: Box = { x0: 150, x1: 166, y0: 90, y1: 104, h: 8, rise: 5 };
const MARGIN = 24;

const head = (s: (typeof SPOTS)[number]) => iso(s.at[0], s.at[1], s.at[2] + s.lift);

function viewBox(): { x: number; y: number; w: number; h: number } {
  const corners: P3[] = [[LOT.x0, ROAD, 0], [LOT.x1, ROAD, 0], [LOT.x1, LOT.y1, 0], [LOT.x0, LOT.y1, 0],
    [BARN.x1, (BARN.y0 + BARN.y1) / 2, BARN.h + BARN.rise]];
  const all = [...corners.map((p) => iso(...p)), ...SPOTS.map(head)];
  const xs = all.map((p) => p[0]); const ys = all.map((p) => p[1]);
  const x = Math.min(...xs) - MARGIN; const y = Math.min(...ys) - MARGIN;
  return { x, y, w: Math.max(...xs) + MARGIN - x, h: Math.max(...ys) + MARGIN - y };
}
const VIEW = viewBox();

function Building({ b, wall, wallShade, roof, roofShade }: { b: Box; wall: string; wallShade: string; roof: string; roofShade: string }) {
  const f = gabled(b);
  return (
    <g>
      <polygon points={pts(f.north)} fill={roofShade} />
      <polygon points={pts(f.west)} fill={wallShade} />
      <polygon points={pts(f.south)} fill={wall} />
      <polygon points={pts(f.roof)} fill={roof} />
    </g>
  );
}

export function LotScene({ onSpot, labels, description }: {
  onSpot?: (picture: string) => void; labels: Record<string, string>; description: string;
}) {
  const c = usePicturePalette();
  const theme = useTheme();
  const svg = useRef<SVGSVGElement>(null);
  // Screen pixels per picture unit, so each pin's target is 48 px across (spec §10.4).
  const [ppu, setPpu] = useState(1);
  useLayoutEffect(() => {
    const el = svg.current;
    if (!el) return;
    const measure = () => {
      const r = el.getBoundingClientRect();
      const k = Math.min(r.width / VIEW.w, r.height / VIEW.h);
      if (k > 0) setPpu(k);
    };
    measure();
    if (typeof ResizeObserver !== "function") return;
    const ro = new ResizeObserver(measure);
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  const dashed = { fill: "none", stroke: c.roofShade, strokeWidth: 1.2, strokeDasharray: "4 3" };
  const flat = (x0: number, x1: number, y0: number, y1: number, z = 0): P3[] => [[x0, y0, z], [x1, y0, z], [x1, y1, z], [x0, y1, z]];
  const stones = Array.from({ length: 15 }, (_, i) => LOT.x0 + 4 + i * 7.6).filter((x) => x < 101 || x > 122);
  const [tx, ty] = iso(-4, 16, 0);

  return (
    <svg ref={svg} role="img" aria-label={description} viewBox={`${VIEW.x} ${VIEW.y} ${VIEW.w} ${VIEW.h}`}
      style={{ width: "100%", height: "auto", display: "block" }}>
      {/* The road, the lot, the driveway. */}
      <polygon points={pts(flat(LOT.x0, LOT.x1, ROAD, 0))} fill={c.stone} opacity={0.45} />
      <polygon points={pts(flat(LOT.x0, LOT.x1, LOT.y0, LOT.y1))} fill={c.lot} stroke={c.lotEdge} strokeWidth={1} />
      <polygon points={pts(flat(104, 120, ROAD, BARN.y0))} fill={c.stone} opacity={0.6} />
      {/* Out back: where a new house could go, and the shed. */}
      <polygon points={pts(flat(-10, 16, 86, 114))} {...dashed} />
      <Building b={SHED} wall={c.barn} wallShade={c.barnShade} roof={c.roof} roofShade={c.roofShade} />
      {/* The barn, the ell, the cape, back to front; the deck behind the cape. */}
      <Building b={BARN} wall={c.barn} wallShade={c.barnShade} roof={c.roof} roofShade={c.roofShade} />
      <polygon points={pts([[105, 30, 0], [120, 30, 0], [120, 30, 12], [105, 30, 12]])} fill={c.barnShade} />
      <polygon points={pts(flat(45, 75, 74, 90, 3))} fill={c.clapboardShade} />
      <Building b={ELL} wall={c.clapboard} wallShade={c.clapboardShade} roof={c.roof} roofShade={c.roofShade} />
      <polygon points={pts(flat(68, 88, 51.5, 57, 12.6))} fill={c.door} opacity={0.85} />
      <Building b={CAPE} wall={c.clapboard} wallShade={c.clapboardShade} roof={c.roof} roofShade={c.roofShade} />
      <polygon points={pts([[36, 62, 22], [40, 62, 22], [40, 62, 30], [36, 62, 30]])} fill={c.brick} />
      <polygon points={pts([[35, 50, 0], [41, 50, 0], [41, 50, 8], [35, 50, 8]])} fill={c.door} />
      {/* Where an addition could go, off the cape's west side. */}
      <polygon points={pts(flat(-10, 15, 50, 70))} {...dashed} />
      {/* The stone wall along the road, the maple, the sign. */}
      {stones.map((x) => { const [sx, sy] = iso(x, 1.5, 1.5); return <ellipse key={x} cx={sx} cy={sy} rx={4.2} ry={2.6} fill={c.stone} />; })}
      <line x1={tx} y1={ty} x2={tx} y2={ty - 16} stroke={c.brick} strokeWidth={3} />
      <circle cx={tx} cy={ty - 26} r={14} fill={c.maple} />
      {(() => { const [sx, sy] = iso(160, 4, 0); return (
        <g><line x1={sx} y1={sy} x2={sx} y2={sy - 10} stroke={c.roofShade} strokeWidth={1.5} />
          <rect x={sx - 6} y={sy - 16} width={12} height={7} fill={c.clapboard} stroke={c.roofShade} strokeWidth={0.8} /></g>); })()}
      {/* The pins: a stem from the thing to its marker, the marker and its name, which can be tapped
          too. Every target is drawn last, above every name, so no name covers a neighbour's pin. */}
      {SPOTS.map((s) => {
        const [fx, fy] = iso(...s.at); const [hx, hy] = head(s);
        return (
          <g key={s.id} data-spot={s.id}>
            <line x1={fx} y1={fy} x2={hx} y2={hy} stroke={theme.palette.primary.main} strokeWidth={1.2} />
            <circle cx={hx} cy={hy} r={6} fill={theme.palette.primary.main} stroke={theme.palette.background.paper} strokeWidth={1.5} />
            <text x={s.label === "left" ? hx - 9 : s.label === "below" ? hx : hx + 9} y={s.label === "below" ? hy + 16 : hy + 3}
              fontSize={9} textAnchor={s.label === "left" ? "end" : s.label === "below" ? "middle" : "start"} fill={theme.palette.text.primary}
              stroke={theme.palette.background.paper} strokeWidth={2.5} paintOrder="stroke"
              style={{ cursor: "pointer" }} onClick={() => onSpot?.(s.id)}>{labels[s.id]}</text>
          </g>
        );
      })}
      {SPOTS.map((s) => {
        const [hx, hy] = head(s);
        return <circle key={s.id} data-hit="" data-for={s.id} aria-hidden="true" cx={hx} cy={hy} r={24 / ppu} fill="transparent"
          style={{ cursor: "pointer" }} onClick={() => onSpot?.(s.id)} />;
      })}
    </svg>
  );
}
