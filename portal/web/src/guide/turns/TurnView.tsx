import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import type { Entry, Shown } from "../api";
import { AnswerList } from "../components/AnswerList";
import { WhyCard } from "../components/WhyCard";
import { TURN_HEADING } from "./heading";
import { LotFacts } from "./LotFacts";
import { NumberAnswer } from "./NumberAnswer";

type Props = { shown: Shown; projectId: string; busy: boolean; locked: boolean; onAnswer: (value: unknown) => void };

const card = (e: Entry) => <WhyCard key={e.id} overline={e.overline} answer={e.answer} detail={e.detail} />;

// One turn, as the API shows it. A "doesn't fit" turn is a page of its own in neutral words,
// never an error (spec §4.5); its answers come in the API's order, the nearest version first.
export function TurnView({ shown, projectId, busy, locked, onAnswer }: Props) {
  if (shown.kind === "number") {
    return <NumberAnswer shown={shown} projectId={projectId} busy={busy} locked={locked} onAnswer={onAnswer} />;
  }
  const between = (
    <Box sx={{ display: "grid", gap: 1.5, mb: 1.5 }}>
      {shown.help && <Typography variant="body2" color="text.secondary">{shown.help}</Typography>}
      {shown.facts_shown && <LotFacts facts={shown.facts_shown} />}
      {shown.defines.map(card)}
      {shown.why && card(shown.why)}
    </Box>
  );
  return (
    <Box component="section" data-turn={shown.turn_id}>
      <AnswerList question={shown.ask} between={between} headingProps={TURN_HEADING} disabled={busy || locked}
        answers={shown.answers.map((a) => ({ id: a.id, label: a.label, hint: a.hint ?? undefined }))}
        onAnswer={(id) => onAnswer(id)} />
    </Box>
  );
}
