import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import Typography from "@mui/material/Typography";
import { IconCheck, IconMessageCircleQuestion } from "@tabler/icons-react";
import { useId, type ReactNode } from "react";
import type { Guide, LotFacts } from "./api";
import { rows, type Row } from "./said";
import { WORDS } from "./words";

function Mark({ mark }: { mark: Row["mark"] }) {
  if (!mark) return null;
  const fits = mark === "fits";
  return (
    <Typography component="span" variant="caption" color={fits ? "success.main" : "text.secondary"}
      sx={{ display: "inline-flex", alignItems: "center", gap: 0.5, fontWeight: 500 }}>
      {fits ? <IconCheck size={14} aria-hidden="true" /> : <IconMessageCircleQuestion size={14} aria-hidden="true" />}
      {fits ? WORDS.fits_mark : WORDS.for_the_town}
    </Typography>
  );
}

function Step({ step, list, onChange, locked }: { step: string; list: Row[]; onChange: (t: string) => void; locked?: boolean }) {
  const id = useId();
  return (
    <Box role="group" aria-labelledby={id} sx={{ display: "grid", gap: 0.5 }}>
      <Typography id={id} variant="overline" color="text.secondary" sx={{ lineHeight: 1.8 }}>{step}</Typography>
      {list.map((r) => (
        <Box key={r.shown.turn_id} sx={{ display: "grid", gridTemplateColumns: "minmax(0, 1fr) auto", alignItems: "center",
          gap: 1, py: 0.5, borderTop: 1, borderColor: "divider" }}>
          <Box sx={{ minWidth: 0 }}>
            <Typography variant="body2" color="text.secondary">{r.shown.ask}</Typography>
            <Typography variant="body1" sx={{ fontWeight: 500 }}>{r.words}</Typography>
            <Mark mark={r.mark} />
          </Box>
          {!locked && (
            <Button size="small" onClick={() => onChange(r.shown.turn_id)} aria-label={`${WORDS.change}: ${r.shown.ask}`}
              sx={{ minHeight: 48, minWidth: 64 }}>{WORDS.change}</Button>
          )}
        </Box>
      ))}
    </Box>
  );
}

function lotOf(guide: Guide): LotFacts | null {
  return guide.history.find((h) => h.shown.facts_shown)?.shown.facts_shown ?? guide.current?.facts_shown ?? null;
}

// The project as the conversation has it so far (spec §4.4, §4.7): the lot, then each answer
// grouped by step with a Change link. Marks are the API's results; none is ever red.
export function ProjectPanel({ guide, onChange, locked, drawing }: {
  guide: Guide; onChange: (turnId: string) => void; locked?: boolean; drawing?: ReactNode;
}) {
  const lot = lotOf(guide);
  return (
    <Card variant="outlined">
      <CardContent sx={{ display: "grid", gap: 1.5 }}>
        <Typography variant="subtitle1" component="h2" sx={{ fontWeight: 500 }}>{WORDS.your_project}</Typography>
        {drawing}
        {lot && (
          <Box>
            <Typography variant="body1" sx={{ fontWeight: 500 }}>{lot.map_lot ?? WORDS.unknown}</Typography>
            <Typography variant="body2" color="text.secondary">
              {lot.districts.length ? lot.districts.map((d) => d.name || d.code).join(" and ") : WORDS.unknown}
            </Typography>
          </Box>
        )}
        {rows(guide).map((g) => <Step key={g.step} step={g.step} list={g.rows} onChange={onChange} locked={locked} />)}
      </CardContent>
    </Card>
  );
}
