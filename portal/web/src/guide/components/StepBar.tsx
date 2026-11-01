import LinearProgress from "@mui/material/LinearProgress";
import Typography from "@mui/material/Typography";
import { useId } from "react";

// Where the person is: "Step 3 of 6 · The building", with a bar. The steps come from the
// project, so the total can change as it takes shape (spec §4.4).
export function StepBar({ step, of, label }: { step: number; of: number; label: string }) {
  const id = useId();
  const words = `Step ${step} of ${of} · ${label}`;
  return (
    <div>
      <Typography id={id} variant="overline" color="text.secondary" sx={{ display: "block", lineHeight: 1.6 }}>
        {words}
      </Typography>
      <LinearProgress variant="determinate" value={(step / of) * 100} aria-labelledby={id}
        aria-valuenow={step} aria-valuemin={0} aria-valuemax={of} />
    </div>
  );
}
