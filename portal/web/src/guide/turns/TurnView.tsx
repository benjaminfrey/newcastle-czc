import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import type { ReactNode } from "react";
import type { Shown } from "../api";
import { AnswerList } from "../components/AnswerList";
import { entryCard } from "../components/entryCard";
import { TURN_HEADING } from "./heading";
import { LotFacts } from "./LotFacts";
import { NumberAnswer } from "./NumberAnswer";

type Props = {
  shown: Shown; projectId: string; busy: boolean; locked: boolean; onAnswer: (value: unknown) => void;
  // Plan 4: the lot drawing inside the turn (on a phone), and the number field's text when the
  // page holds it so a drag in the drawing can set it.
  figure?: ReactNode; footer?: ReactNode; text?: string; onTextChange?: (text: string) => void;
};

const card = entryCard;

// One turn, as the API shows it. A "doesn't fit" turn is a page of its own in neutral words,
// never an error (spec §4.5); its answers come in the API's order, the nearest version first.
export function TurnView({ shown, projectId, busy, locked, onAnswer, figure, footer, text, onTextChange }: Props) {
  if (shown.kind === "number") {
    return <NumberAnswer shown={shown} projectId={projectId} busy={busy} locked={locked} onAnswer={onAnswer}
      figure={figure} footer={footer} text={text} onTextChange={onTextChange} />;
  }
  const between = (
    <Box sx={{ display: "grid", gap: 1.5, mb: 1.5 }}>
      {shown.help && <Typography variant="body2" color="text.secondary">{shown.help}</Typography>}
      {shown.facts_shown && <LotFacts facts={shown.facts_shown} />}
      {figure}
      {shown.defines.map(card)}
      {shown.why && card(shown.why)}
    </Box>
  );
  return (
    <Box component="section" data-turn={shown.turn_id}>
      <AnswerList question={shown.ask} between={between} headingProps={TURN_HEADING} disabled={busy || locked}
        answers={shown.answers.map((a) => ({ id: a.id, label: a.label, hint: a.hint ?? undefined }))}
        onAnswer={(id) => onAnswer(id)} />
      {footer && <Box sx={{ mt: 1.5 }}>{footer}</Box>}
    </Box>
  );
}
