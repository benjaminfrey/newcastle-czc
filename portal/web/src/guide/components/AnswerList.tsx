import FormControlLabel from "@mui/material/FormControlLabel";
import Paper from "@mui/material/Paper";
import Radio from "@mui/material/Radio";
import RadioGroup from "@mui/material/RadioGroup";
import Typography from "@mui/material/Typography";
import { useId, useRef, useState, type KeyboardEvent } from "react";

export type Answer = { id: string; label: string; hint?: string };

// The question's answers as a list you tap. A tap or click answers at once; on a keyboard the
// arrows move the choice and Enter or Space answers, so a stray arrow never answers for you, and
// an answer is never sent twice in a row.
export function AnswerList({ question, answers, onAnswer }: {
  question: string; answers: Answer[]; onAnswer: (id: string) => void;
}) {
  const headingId = useId();
  const [chosen, setChosen] = useState<string | null>(null);
  const answered = useRef<string | null>(null);
  const arrowed = useRef(false);
  const answer = (id: string) => {
    if (answered.current === id) return;
    answered.current = id;
    onAnswer(id);
  };
  // A tap, a click on the words or Space on an unchosen answer changes the choice and answers.
  // An arrow only moves the choice; Enter or Space then answers it.
  const onChange = (id: string) => {
    setChosen(id);
    if (arrowed.current) arrowed.current = false;
    else answer(id);
  };
  const onKeyDown = (e: KeyboardEvent) => {
    if (e.key.startsWith("Arrow")) arrowed.current = true;
    else if ((e.key === "Enter" || e.key === " ") && chosen) {
      e.preventDefault();
      answer(chosen);
    }
  };
  return (
    <div>
      <Typography id={headingId} variant="subtitle1" component="h2" sx={{ fontWeight: 500, mb: 1 }}>
        {question}
      </Typography>
      <Paper variant="outlined" sx={{ borderRadius: 2, overflow: "hidden", borderColor: "divider" }}>
        <RadioGroup aria-labelledby={headingId} value={chosen ?? ""}
          onChange={(_, v) => onChange(v)} onKeyDown={onKeyDown}>
          {answers.map((a, i) => (
            <FormControlLabel key={a.id} value={a.id}
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
