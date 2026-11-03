import Typography from "@mui/material/Typography";
import type { Guide } from "./api";
import { TURN_HEADING } from "./turns/heading";

// The ending (spec §4.6). Task 6 fills in each kind.
export function EndingView({ guide }: { guide: Guide; projectId: string }) {
  const e = guide.ending!;
  return <section>
    <Typography variant="h6" component="h2" {...TURN_HEADING}>{e.title}</Typography>
    <Typography>{e.body}</Typography>
  </section>;
}
