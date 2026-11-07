import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import type { Approx, LotFacts as Facts } from "../api";
import { WORDS } from "../words";

const fmt = (n: number) => n.toLocaleString("en-US");

function approx(a: Approx, unit: string) {
  if (a.value == null) return WORDS.unknown;
  return <>{fmt(a.value)} {unit}{a.approximate && (
    <Typography component="span" variant="body2" color="text.secondary"> · {WORDS.approximate}</Typography>)}</>;
}

// What the Town believes about the lot (spec §4.1). Anything the data can't tell is said as
// unknown, never left blank or guessed; tax-map figures say they are approximate.
export function LotFacts({ facts }: { facts: Facts }) {
  const rows: [string, React.ReactNode][] = [
    [WORDS.lot_map_lot, facts.map_lot ?? WORDS.unknown],
    [WORDS.lot_districts, facts.districts.length ? facts.districts.map((d) => d.name || d.code).join(" and ") : WORDS.unknown],
    [WORDS.lot_acres, approx(facts.acres, WORDS.acres)],
    [WORDS.lot_frontage, approx(facts.frontage_ft, WORDS.ft)],
  ];
  return (
    <Box component="dl" sx={{ display: "grid", gridTemplateColumns: "auto 1fr", columnGap: 2, rowGap: 0.75, my: 1.5 }}>
      {rows.map(([k, v]) => (
        <Box key={k} sx={{ display: "contents" }}>
          <Typography component="dt" variant="body2" color="text.secondary">{k}</Typography>
          <Typography component="dd" variant="body1" sx={{ m: 0 }}>{v}</Typography>
        </Box>
      ))}
    </Box>
  );
}
