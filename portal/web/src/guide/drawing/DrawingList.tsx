import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import { IconCheck, IconMessageCircleQuestion } from "@tabler/icons-react";
import { useId } from "react";
import type { Check, Drawing, Limit } from "../api";
import { fill, WORDS } from "../words";
import type { Distances, Edge } from "./geometry";

// The setback turn for each edge of the house the drawing shows.
export const EDGE_TURN: Record<Edge, string> = {
  front: "setback_front", side_1: "setback_side_1", side_2: "setback_side_2", rear: "setback_rear",
};
const EDGE_LIMIT = { front: "front", side_1: "side", side_2: "side", rear: "rear" } as const;

// A corner lot is asked its secondary setback in place of the second side (the chair,
// 2026-11-05): that edge of the house faces the other road.
const SECONDARY_TURN = "setback_secondary";

/** The distances the person has given so far: the API's checked value when there is one (it
 *  follows "Make it 15 ft"), otherwise the answer as given. */
// What the list reads: the API's checks and each answer as given. The live guide has both, and so
// does the packet (plan 6).
export type Drawn = { checks: Record<string, Check>; history: { shown: { turn_id: string }; value: unknown }[] };

export function distancesOf(guide: Drawn): Distances {
  const out: Distances = {};
  const turns = Object.entries(EDGE_TURN) as [Edge, string][];
  for (const [edge, turnId] of [...turns, ["side_2", SECONDARY_TURN] as [Edge, string]]) {
    if (out[edge] !== undefined) continue;
    const checked = guide.checks[turnId]?.value;
    const given = guide.history.find((h) => h.shown.turn_id === turnId)?.value;
    const n = typeof checked === "number" ? checked : typeof given === "number" ? given : undefined;
    if (n !== undefined) out[edge] = n;
  }
  return out;
}

function limitWords(limit: Limit | null): string {
  if (!limit) return WORDS.drawing.no_limit;
  const unit = limit.unit ?? "ft";
  if (limit.min != null && limit.max != null) return fill(WORDS.drawing.between, { min: limit.min, max: limit.max, unit });
  if (limit.min != null) return fill(WORDS.drawing.at_least, { n: limit.min, unit });
  if (limit.max != null) return fill(WORDS.drawing.at_most, { n: limit.max, unit });
  const reason = limit.reason as keyof typeof WORDS.unsettled | null;
  return reason && reason in WORDS.unsettled ? WORDS.unsettled[reason] : WORDS.drawing.no_limit;
}

function Mark({ check }: { check: Check | undefined }) {
  if (!check) return null;
  const fits = check.result === "fits";
  return (
    <Typography component="span" variant="caption" color={fits ? "success.main" : "text.secondary"}
      sx={{ display: "inline-flex", alignItems: "center", gap: 0.5, fontWeight: 500 }}>
      {fits ? <IconCheck size={14} aria-hidden="true" /> : <IconMessageCircleQuestion size={14} aria-hidden="true" />}
      {fits ? WORDS.fits_mark : WORDS.for_the_town}
    </Typography>
  );
}

function Row({ name, limit, yours, check }: { name: string; limit: string; yours: string; check?: Check }) {
  return (
    <Box component="li" sx={{ py: 0.75, borderTop: 1, borderColor: "divider", listStyle: "none" }}>
      <Typography variant="body2" sx={{ fontWeight: 500 }}>{name}</Typography>
      <Typography variant="body2" color="text.secondary">{limit}</Typography>
      <Typography variant="body2">{yours}</Typography>
      <Mark check={check} />
    </Box>
  );
}

// The drawing in words (spec §10.4), and the live checklist beside it (§4.4): each setback as
// the API gives it, the person's number, and the API's own mark. Nothing here compares numbers.
export function DrawingList({ drawing, guide }: { drawing: Drawing; guide: Drawn }) {
  const id = useId();
  const d = distancesOf(guide);
  const lines = drawing.outline?.lines ?? [];
  const frontages = drawing.roles ? lines.filter((l) => drawing.roles![l.id] === "frontage") : [];
  const secondary = drawing.roles ? lines.find((l) => drawing.roles![l.id] === "secondary") : undefined;
  return (
    <Box role="group" aria-labelledby={id}>
      <Typography id={id} variant="overline" color="text.secondary">{WORDS.drawing.list_heading}</Typography>
      {!drawing.roles && <Typography variant="body2">{WORDS.drawing.choose_front_first}</Typography>}
      <Box component="ul" sx={{ m: 0, p: 0 }}>
        {drawing.roles && (Object.keys(EDGE_TURN) as Edge[]).map((edge) => {
          const road = edge === "side_2" ? secondary : undefined;
          const limit = drawing.limits[road ? "secondary" : EDGE_LIMIT[edge]];
          const n = d[edge];
          return (
            <Row key={edge} limit={limitWords(limit)}
              name={road ? fill(WORDS.drawing.rows.secondary, { street: road.street?.name ?? "" }) : WORDS.drawing.rows[edge]}
              yours={n == null ? WORDS.drawing.not_entered : fill(WORDS.drawing.yours, { n, unit: limit?.unit ?? "ft" })}
              check={guide.checks[road ? SECONDARY_TURN : EDGE_TURN[edge]]} />
          );
        })}
        {frontages.map((l) => (
          <Row key={l.id} name={fill(WORDS.drawing.rows.frontage, { street: l.street?.name ?? "" })}
            limit={WORDS.drawing.frontage_town} yours="" />
        ))}
        <Box component="li" sx={{ py: 0.75, borderTop: 1, borderColor: "divider", listStyle: "none" }}>
          <Typography variant="body2" color="text.secondary">{WORDS.drawing.not_shown}</Typography>
        </Box>
      </Box>
    </Box>
  );
}
