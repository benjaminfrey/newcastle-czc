import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Typography from "@mui/material/Typography";
import { useId, useState } from "react";
import type { Check, Packet, PacketRow } from "../api";
import { entryCard } from "../components/entryCard";
import { fill, WORDS } from "../words";

const P = WORDS.packet;

// The limit as the API gives it, in the drawing's approved words. Nothing here compares numbers.
function required(c: Check): string | null {
  const unit = c.unit ?? "";
  if (c.min != null && c.max != null) return fill(WORDS.drawing.between, { min: c.min, max: c.max, unit });
  if (c.min != null) return fill(WORDS.drawing.at_least, { n: c.min, unit });
  if (c.max != null) return fill(WORDS.drawing.at_most, { n: c.max, unit });
  return null;
}

function Row({ row, town }: { row: PacketRow; town: boolean }) {
  const c = row.check;
  const reason = row.reason && row.reason in WORDS.unsettled ? WORDS.unsettled[row.reason as keyof typeof WORDS.unsettled] : null;
  const limit = c ? required(c) : null;
  return (
    <Box component="li" sx={{ py: 1, borderTop: 1, borderColor: "divider", listStyle: "none", display: "grid", gap: 0.5 }}>
      {row.ask && <Typography variant="body2" sx={{ fontWeight: 500 }}>{row.ask}</Typography>}
      <Typography variant="caption" sx={{ fontWeight: 500 }} color={town ? "text.primary" : "success.main"}>
        {town ? WORDS.for_the_town : WORDS.fits_mark}{reason ? ` · ${reason}` : ""}
      </Typography>
      {limit && <Typography variant="body2" color="text.secondary">{P.required}: {limit}</Typography>}
      {c?.value != null && <Typography variant="body2">{fill(WORDS.drawing.yours, { n: c.value, unit: c.unit ?? "" })}</Typography>}
      {row.why && entryCard(row.why)}
    </Box>
  );
}

// Judgment first and highlighted; the routine passes folded below them (spec §7.3, decision 8).
export function PacketChecklist({ checklist }: { checklist: Packet["checklist"] }) {
  const [open, setOpen] = useState(false);
  const fitsId = useId();
  return (
    <Box sx={{ display: "grid", gap: 1.5 }}>
      {checklist.town.length > 0 && (
        <Box sx={{ p: 1.5, borderRadius: 2, bgcolor: "surfaceContainer" }}>
          <Typography variant="subtitle1" component="h3">{WORDS.unsettled_heading}</Typography>
          <Box component="ul" sx={{ m: 0, p: 0 }}>
            {checklist.town.map((r, i) => <Row key={`t${i}`} row={r} town />)}
          </Box>
        </Box>
      )}
      {checklist.fits.length > 0 && <Box>
        <Typography variant="subtitle1" component="h3">{WORDS.settled_heading}</Typography>
        <Button aria-expanded={open} aria-controls={fitsId} onClick={() => setOpen((o) => !o)} sx={{ minHeight: 48 }}>
          {open ? P.hide_fits : fill(P.show_fits, { n: checklist.fits.length })}
        </Button>
        <Box component="ul" id={fitsId} data-fits="" hidden={!open} sx={{ m: 0, p: 0 }}>
          {checklist.fits.map((r, i) => <Row key={`f${i}`} row={r} town={false} />)}
        </Box>
      </Box>}
    </Box>
  );
}
