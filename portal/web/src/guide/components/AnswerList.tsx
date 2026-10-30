import FormControlLabel from "@mui/material/FormControlLabel";
import Paper from "@mui/material/Paper";
import Radio from "@mui/material/Radio";
import RadioGroup from "@mui/material/RadioGroup";
import Typography from "@mui/material/Typography";
import { useId, useState, type KeyboardEvent, type MouseEvent } from "react";

export type Answer = { id: string; label: string; hint?: string };

// The question's answers as a list you tap. A tap or click answers at once; on a keyboard the
// arrows move the choice and Enter or Space answers, so a stray arrow never answers for you.
export function AnswerList({ question, answers, onAnswer }: {
  question: string; answers: Answer[]; onAnswer: (id: string) => void;
}) {
  const headingId = useId();
  const [chosen, setChosen] = useState<string | null>(null);
  const onKeyDown = (e: KeyboardEvent) => {
    if ((e.key === "Enter" || e.key === " ") && chosen) {
      e.preventDefault();
      onAnswer(chosen);
    }
  };
  // A pointer click has detail ≥ 1; the click a browser makes for an arrow or Space has 0.
  const onClick = (id: string) => (e: MouseEvent) => { if (e.detail > 0) onAnswer(id); };
  return (
    <div>
      <Typography id={headingId} variant="subtitle1" component="h2" sx={{ fontWeight: 500, mb: 1 }}>
        {question}
      </Typography>
      <Paper variant="outlined" sx={{ borderRadius: 2, overflow: "hidden", borderColor: "divider" }}>
        <RadioGroup aria-labelledby={headingId} value={chosen ?? ""}
          onChange={(_, v) => setChosen(v)} onKeyDown={onKeyDown}>
          {answers.map((a, i) => (
            <FormControlLabel key={a.id} value={a.id} onClick={onClick(a.id)}
              control={<Radio />}
              label={<span>{a.label}{a.hint && (
                <Typography component="span" variant="body2" color="text.secondary" sx={{ display: "block" }}>
                  {a.hint}</Typography>)}</span>}
              sx={{ m: 0, px: 1, minHeight: 56, borderTop: i ? 1 : 0, borderColor: "divider" }} />
          ))}
        </RadioGroup>
      </Paper>
    </div>
  );
}
