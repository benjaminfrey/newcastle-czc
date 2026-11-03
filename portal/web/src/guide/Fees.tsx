import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import type { Needs } from "../projects";
import { WORDS } from "./words";

const money = (n: number) => `$${n.toLocaleString("en-US")}`;

// What the project needs from the Town and what it costs, as the API's needs say (the screener
// and the Town's fee schedule); nothing here is worked out on the screen.
export function Fees({ needs }: { needs: Needs | null }) {
  if (!needs || "refused" in needs) return <Typography color="text.secondary">{WORDS.fees_unknown}</Typography>;
  const reviews = needs.permits.flatMap((p) => p.reviews);
  const line = (label: string, amount: string) => (
    <Box sx={{ display: "flex", justifyContent: "space-between", gap: 2, py: 0.75, borderTop: 1, borderColor: "divider" }}>
      <Typography>{label}</Typography><Typography sx={{ fontVariantNumeric: "tabular-nums", fontWeight: 500 }}>{amount}</Typography>
    </Box>
  );
  return (
    <Box sx={{ display: "grid", gap: 2 }}>
      <Box component="section" aria-label={WORDS.reviews_heading}>
        <Typography variant="subtitle2" component="h3">{WORDS.reviews_heading}</Typography>
        {reviews.map((r) => (
          <Box key={`${r.review_key}|${r.use_key ?? ""}|${r.part_id ?? ""}`} sx={{ py: 0.75, borderTop: 1, borderColor: "divider" }}>
            <Typography sx={{ fontWeight: 500 }}>{r.name}</Typography>
            {r.plain && <Typography variant="body2" color="text.secondary">{r.plain}</Typography>}
          </Box>
        ))}
      </Box>
      <Box component="section" aria-label={WORDS.fees_heading}>
        <Typography variant="subtitle2" component="h3">{WORDS.fees_heading}</Typography>
        {line(WORDS.application_fees, needs.application_fees_vary ? WORDS.fee_varies : money(needs.application_fees_total))}
        {line(WORDS.permit_fees, money(needs.permit_fees_total))}
      </Box>
    </Box>
  );
}
