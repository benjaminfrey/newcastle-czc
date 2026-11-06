import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import { useTheme } from "@mui/material/styles";
import Typography from "@mui/material/Typography";
import { useId, useLayoutEffect, useRef, useState, type PointerEvent } from "react";
import type { Drawing, LotLine, Pt, Role } from "../api";
import { fill, WORDS } from "../words";
import { dragDistance, fitView, houseBox, secondarySide, type Distances, type Edge } from "./geometry";

export type Asking = "front" | "front_setback" | "side_1" | "side_2" | "secondary" | "rear";
type Props = {
  drawing: Drawing; distances: Distances; asking?: Asking | null;
  onPickLine?: (id: string) => void; onDrag?: (n: number) => void;
};

// On a corner lot the house's second side faces the other road and takes its secondary setback.
const EDGE_OF: Partial<Record<Asking, Edge>> = {
  front_setback: "front", side_1: "side_1", side_2: "side_2", secondary: "side_2", rear: "rear",
};
const LIMIT_OF: Partial<Record<Role, "front" | "side" | "rear" | "secondary">> = {
  front: "front", side: "side", rear: "rear", secondary: "secondary",
};

function inwardOffset(line: LotLine, ft: number): [Pt, Pt] {
  // Lines run clockwise round the lot (y north), so the lot is on their right.
  const a = line.points[0]; const b = line.points[line.points.length - 1];
  const len = Math.hypot(b[0] - a[0], b[1] - a[1]) || 1;
  const n: Pt = [(b[1] - a[1]) / len, -(b[0] - a[0]) / len];
  return [[a[0] + n[0] * ft, a[1] + n[1] * ft], [b[0] + n[0] * ft, b[1] + n[1] * ft]];
}

const mid = (a: Pt, b: Pt): Pt => [(a[0] + b[0]) / 2, (a[1] + b[1]) / 2];

// The person's lot as the tax map has it, labelled approximate, with the setback limits the API
// gives and the house where their distances put it (spec §4.4). It shows; it never decides
// (decision 12): a drag only reports a distance, which goes into the question's own field.
export function LotDrawing({ drawing, distances, asking, onPickLine, onDrag }: Props) {
  const theme = useTheme();
  const clip = `lot-${useId().replace(/[^a-zA-Z0-9_-]/g, "")}`;
  const svg = useRef<SVGSVGElement>(null);
  const dragging = useRef(false);
  const [swapped, setFlip] = useState(false);
  // Screen pixels per view unit, so the handle and the line targets are 48 px across (spec §10.4).
  const [ppu, setPpu] = useState(1);
  const outline = drawing.outline;
  const vbWidth = outline ? Number(fitView(outline).viewBox.split(" ")[2]) : 1;
  useLayoutEffect(() => {
    const el = svg.current;
    if (!el) return;
    const measure = () => {
      const r = el.getBoundingClientRect();
      const vbHeight = Number(el.getAttribute("viewBox")?.split(" ")[3]) || 1;
      const k = Math.min(r.width / vbWidth, r.height / vbHeight);
      if (k > 0) setPpu(k);
    };
    measure();
    if (typeof ResizeObserver !== "function") return;
    const ro = new ResizeObserver(measure);
    ro.observe(el);
    return () => ro.disconnect();
  }, [vbWidth]);
  if (!outline) return null;

  const { viewBox, scale } = fitView(outline);
  const [vbX, vbY, vbW, vbH] = viewBox.split(" ").map(Number);
  const v = (p: Pt) => `${p[0] * scale},${-p[1] * scale}`;
  const pts = (ps: Pt[]) => ps.map(v).join(" ");
  const at = (p: Pt) => ({ x: p[0] * scale, y: -p[1] * scale });
  const roles = drawing.roles;
  const front = roles ? drawing.front : null;
  // A corner lot's sides are fixed by its roads: side 2 is the one beside the other road.
  const fixedSide = front && roles ? secondarySide(outline, front, roles) : null;
  const flip = fixedSide ? fixedSide === "left" : swapped;
  const edge = asking ? EDGE_OF[asking] : undefined;
  // The edge being asked needs somewhere to start before it has a number: at its limit if the
  // API gave one, else 10 ft in. That only places the handle; no number is shown or entered.
  const startAt = (e: Edge) => drawing.limits[
    asking === "secondary" ? "secondary" : e === "front" ? "front" : e === "rear" ? "rear" : "side"]?.min ?? 10;
  const placed = edge && distances[edge] == null ? { ...distances, [edge]: startAt(edge) } : distances;
  const box = front ? houseBox(outline, front, placed, flip, roles ?? undefined) : null;
  const stroke = Math.max(1.5, 400 / 250);

  // A screen point in feet. The picture keeps its shape ("meet"), so when its box is wider or
  // taller than the picture it is centred with margins, which the mapping must skip.
  function world(e: PointerEvent): Pt {
    const r = svg.current!.getBoundingClientRect();
    const k = Math.min((r.width || vbW) / vbW, (r.height || vbH) / vbH);
    const ox = ((r.width || vbW) - vbW * k) / 2; const oy = ((r.height || vbH) - vbH * k) / 2;
    const x = vbX + (e.clientX - r.left - ox) / k;
    const y = vbY + (e.clientY - r.top - oy) / k;
    return [x / scale, -y / scale];
  }
  function move(e: PointerEvent) {
    if (!dragging.current || !edge || !front) return;
    onDrag?.(dragDistance(outline!, front, edge, world(e), flip, roles ?? undefined));
  }

  // Each edge of the box, and the distance that set it: front, right, rear, left.
  const left = flip ? "side_2" : "side_1"; const right = flip ? "side_1" : "side_2";
  const edges: [Edge, Pt, Pt][] = box
    ? [["front", box[0], box[1]], [right, box[1], box[2]], ["rear", box[2], box[3]], [left, box[3], box[0]]] : [];

  return (
    <Box>
      <svg ref={svg} role="img" viewBox={viewBox} aria-label={fill(WORDS.drawing.summary, { lines: outline.lines.length })}
        style={{ width: "100%", height: "auto", maxHeight: "50dvh", display: "block" }}
        onPointerMove={move} onPointerUp={() => { dragging.current = false; }} onPointerCancel={() => { dragging.current = false; }}>
        <defs><clipPath id={clip}><polygon points={pts(outline.parts[0])} /></clipPath></defs>
        {outline.streets.map((s, i) => (
          <g key={`road-${i}`} data-road={s.name}>
            <polyline points={pts(s.points)} fill="none" stroke={theme.palette.grey[300]} strokeWidth={10} strokeLinecap="round" />
          </g>
        ))}
        {outline.parts.map((part, i) => (
          <polygon key={`part-${i}`} data-lot={i === 0 ? "" : undefined} points={pts(part)}
            fill={theme.palette.background.paper} stroke="none" />
        ))}
        <g clipPath={`url(#${clip})`}>
          {roles && outline.lines.map((l) => {
            const which = LIMIT_OF[roles[l.id]];
            const lim = which ? drawing.limits[which] : null;
            return lim?.min ? (
              <polyline key={`strip-${l.id}`} data-strip={l.id} points={pts(l.points)} fill="none"
                stroke={theme.palette.action.selected} strokeWidth={2 * lim.min * scale} strokeLinecap="round" strokeLinejoin="round" />
            ) : null;
          })}
          {roles && outline.lines.map((l) => {
            const which = LIMIT_OF[roles[l.id]];
            const lim = which ? drawing.limits[which] : null;
            if (!lim?.max) return null;
            const [a, b] = inwardOffset(l, lim.max);
            return <line key={`max-${l.id}`} data-max={l.id} x1={at(a).x} y1={at(a).y} x2={at(b).x} y2={at(b).y}
              stroke={theme.palette.text.secondary} strokeWidth={stroke} strokeDasharray="6 4" />;
          })}
        </g>
        {outline.parts.map((part, i) => (
          <polygon key={`edge-${i}`} points={pts(part)} fill="none" stroke={theme.palette.text.primary} strokeWidth={stroke} />
        ))}
        {front && (() => {
          const l = outline.lines.find((x) => x.id === front);
          return l ? <polyline data-front={l.id} points={pts(l.points)} fill="none" stroke={theme.palette.text.primary}
            strokeWidth={stroke * 3} strokeLinecap="round" /> : null;
        })()}
        {outline.lines.map((l) => {
          const m = at(mid(l.points[0], l.points[l.points.length - 1]));
          return <text key={`len-${l.id}`} data-line-label={l.id} x={m.x} y={m.y} fontSize={12} textAnchor="middle"
            fill={theme.palette.text.secondary} stroke={theme.palette.background.paper} strokeWidth={3} paintOrder="stroke">
            {fill(WORDS.drawing.line_length, { n: l.length_ft })}</text>;
        })}
        {box && (
          <polygon data-house="" points={pts(box)} fill={theme.palette.primary.main} fillOpacity={0.18}
            stroke={theme.palette.primary.main} strokeWidth={stroke} />
        )}
        {edges.map(([e, a, b]) => {
          const n = distances[e];
          if (n == null) return null;
          const m = at(mid(a, b));
          return <text key={`d-${e}`} x={m.x} y={m.y} fontSize={12} textAnchor="middle" fill={theme.palette.primary.dark}
            stroke={theme.palette.background.paper} strokeWidth={3} paintOrder="stroke">{`${n} ft`}</text>;
        })}
        {asking === "front" && outline.lines.map((l) => (
          <polyline key={`pick-${l.id}`} data-pick={l.id} aria-hidden="true" points={pts(l.points)} fill="none"
            stroke="transparent" strokeWidth={48 / ppu} strokeLinecap="round" style={{ cursor: "pointer" }}
            // Only a line along a road is offered as the front; tapping another is "A different line".
            onClick={() => onPickLine?.(l.street ? l.id : "other")} />
        ))}
        {edge && edges.filter(([e]) => e === edge).map(([e, a, b]) => {
          const m = at(mid(a, b));
          return <circle key={`h-${e}`} data-handle={e} aria-hidden="true" cx={m.x} cy={m.y} r={24 / ppu}
            fill={theme.palette.primary.main} stroke={theme.palette.background.paper} strokeWidth={3}
            style={{ cursor: "grab", touchAction: "none" }}
            onPointerDown={(ev) => { dragging.current = true; ev.currentTarget.setPointerCapture?.(ev.pointerId); }} />;
        })}
      </svg>
      <Box sx={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 1, flexWrap: "wrap" }}>
        <Typography variant="caption" color="text.secondary">{WORDS.drawing.approximate}</Typography>
        {!fixedSide && (distances.side_1 != null || distances.side_2 != null) && (
          <Button size="small" onClick={() => setFlip((f) => !f)} sx={{ minHeight: 48 }}>{WORDS.drawing.swap_sides}</Button>
        )}
      </Box>
    </Box>
  );
}
