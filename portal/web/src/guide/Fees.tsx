import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import type { Needs } from "../projects";
import { WORDS } from "./words";

const money = (n: number) => `$${n.toLocaleString("en-US")}`;

// What the project needs from the Town and what it costs, as the API's needs say (the screener
// and the Town's fee schedule); nothing here is worked out on the screen.
// `undefined` while the project is still loading: nothing is said until it has.
export function Fees({ needs }: { needs: Needs | null | undefined }) {
  if (needs === undefined) return null;
  if (!needs || "refused" in needs) return <Typography color="text.secondary">{WORDS.fees_unknown}</Typography>;
  // A review that may apply waits on an answer still to come; it is never shown as needed.
  const all = needs.permits.flatMap((p) => p.reviews);
  const reviews = all.filter((r) => r.certainty === "needed");
  const maybe = all.filter((r) => r.certainty !== "needed");
  const list = (heading: string, rs: typeof all) => rs.length > 0 && (
    <Box component="section" aria-label={heading}>
      <Typography variant="subtitle2" component="h3">{heading}</Typography>
      {rs.map((r) => (
        <Box key={`${r.review_key}|${r.use_key ?? ""}|${r.part_id ?? ""}`} sx={{ py: 0.75, borderTop: 1, borderColor: "divider" }}>
          <Typography sx={{ fontWeight: 500 }}>{r.name}</Typography>
          {r.plain && <Typography variant="body2" color="text.secondary">{r.plain}</Typography>}
        </Box>
      ))}
    </Box>
  );
  const line = (label: string, amount: string) => (
    <Box sx={{ display: "flex", justifyContent: "space-between", gap: 2, py: 0.75, borderTop: 1, borderColor: "divider" }}>
      <Typography>{label}</Typography><Typography sx={{ fontVariantNumeric: "tabular-nums", fontWeight: 500 }}>{amount}</Typography>
    </Box>
  );
  return (
    <Box sx={{ display: "grid", gap: 2 }}>
      {list(WORDS.reviews_heading, reviews)}
      {list(WORDS.may_apply_heading, maybe)}
      <Box component="section" aria-label={WORDS.fees_heading}>
        <Typography variant="subtitle2" component="h3">{WORDS.fees_heading}</Typography>
        {line(WORDS.application_fees, needs.application_fees_vary ? WORDS.fee_varies : money(needs.application_fees_total))}
        {line(WORDS.permit_fees, money(needs.permit_fees_total))}
      </Box>
    </Box>
  );
}
