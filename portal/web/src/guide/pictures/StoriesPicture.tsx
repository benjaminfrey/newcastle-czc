import { useTheme } from "@mui/material/styles";
import { WORDS } from "../words";
import { iso, pts, type P3 } from "./iso";
import { usePicturePalette } from "./palette";

// "How stories are counted" (guided plan 5, design §7): a cape seen the same way as the scene,
// its gable end facing the road and cut open. It carries no number of its own: the 3-foot and
// 5-foot tests are labelled as the Code states them (Art. 5 §7.c.5–6), and the words say the rest.
const X0 = 0, X1 = 40, XM = 20, Y0 = 0, Y1 = 34;
const BASE = -9, FRONT_GRADE = -5, FLOOR2 = 9, ATTIC = 18, KNEE = 22, RIDGE = 36;

const VIEW = (() => {
  const ps = ([[X0 - 16, Y0 - 12, BASE], [X1 + 16, Y0 - 12, BASE], [X1 + 16, Y1 + 10, 0], [X0 - 16, Y1 + 10, 0],
    [XM, Y1, RIDGE], [XM, Y0, RIDGE]] as P3[]).map((p) => iso(...p));
  const xs = ps.map((p) => p[0]); const ys = ps.map((p) => p[1]);
  const x = Math.min(...xs) - 40; const y = Math.min(...ys) - 6;
  return `${x} ${y} ${Math.max(...xs) + 52 - x} ${Math.max(...ys) + 6 - y}`;
})();

export function StoriesPicture() {
  const c = usePicturePalette();
  const theme = useTheme();
  const words = WORDS.pictures.stories;
  const ink = theme.palette.text.primary;
  const text = (p: P3, s: string, anchor: "start" | "middle" | "end" = "middle") => {
    const [x, y] = iso(...p);
    return <text x={x} y={y} fontSize={7} textAnchor={anchor} fill={ink}
      stroke={theme.palette.background.paper} strokeWidth={2} paintOrder="stroke">{s}</text>;
  };
  const line = (a: P3, b: P3, stroke: string, width = 1) => {
    const [x1, y1] = iso(...a); const [x2, y2] = iso(...b);
    return <line x1={x1} y1={y1} x2={x2} y2={y2} stroke={stroke} strokeWidth={width} strokeLinecap="round" />;
  };
  // The cut: the gable end's outline, walls to the knee, the roof to the ridge.
  const section: P3[] = [[X0, Y0, BASE], [X1, Y0, BASE], [X1, Y0, KNEE], [XM, Y0, RIDGE], [X0, Y0, KNEE]];
  return (
    <svg viewBox={VIEW} style={{ width: "100%", height: "auto", display: "block" }} aria-hidden="true">
      {/* The ground: level beside and behind the house, lower in front, so the basement shows. */}
      <polygon points={pts([[X0 - 16, Y0, 0], [X1 + 16, Y0, 0], [X1 + 16, Y1 + 10, 0], [X0 - 16, Y1 + 10, 0]])} fill={c.lot} />
      <polygon points={pts([[X0 - 16, Y0 - 12, FRONT_GRADE], [X1 + 16, Y0 - 12, FRONT_GRADE], [X1 + 16, Y0, FRONT_GRADE], [X0 - 16, Y0, FRONT_GRADE]])} fill={c.lot} />
      <polygon points={pts([[X0 - 16, Y0, FRONT_GRADE], [X1 + 16, Y0, FRONT_GRADE], [X1 + 16, Y0, 0], [X0 - 16, Y0, 0]])} fill={c.lotEdge} />
      {/* The west wall and the west slope of the roof, running back from the cut. */}
      <polygon points={pts([[X0, Y0, FRONT_GRADE], [X0, Y1, 0], [X0, Y1, KNEE], [X0, Y0, KNEE]])} fill={c.clapboardShade} />
      <polygon points={pts([[X0, Y0, KNEE], [X0, Y1, KNEE], [XM, Y1, RIDGE], [XM, Y0, RIDGE]])} fill={c.roof} />
      {/* The cut itself: the inside, the floors, the basement below the ground. */}
      <polygon points={pts(section)} fill={c.clapboard} stroke={c.roofShade} strokeWidth={1.5} strokeLinejoin="round" />
      <polygon points={pts([[X0, Y0, BASE], [X1, Y0, BASE], [X1, Y0, 0], [X0, Y0, 0]])} fill={c.stone} opacity={0.35} />
      {[0, FLOOR2, ATTIC].map((z) => <g key={z}>{line([X0, Y0, z], [X1, Y0, z], c.roofShade, 1.2)}</g>)}
      {line([X0 - 3, Y0, FRONT_GRADE], [X1 + 3, Y0, FRONT_GRADE], c.lotEdge, 1.5)}
      {/* The two tests, marked where they are measured. */}
      {line([X1 + 1.5, Y0, ATTIC], [X1 + 1.5, Y0, KNEE], c.maple, 2.5)}
      {line([X0 - 1.5, Y0, FRONT_GRADE], [X0 - 1.5, Y0, 0], c.maple, 2.5)}
      {text([XM, Y0, 3], words.first)}
      {text([XM, Y0, FLOOR2 + 3], words.second)}
      {text([XM, Y0, ATTIC + 4], words.roof)}
      {text([XM, Y0, BASE + 2.5], words.basement)}
      {text([X1 + 5, Y0, ATTIC + 1], words.knee, "start")}
      {text([X0 - 5, Y0, FRONT_GRADE + 1], words.exposed, "end")}
    </svg>
  );
}
