import Box from "@mui/material/Box";
import Chip from "@mui/material/Chip";
import Typography from "@mui/material/Typography";
import type { Packet, PacketMark } from "../api";
import { WORDS } from "../words";

// The moments that matter (spec §7.2), each with its words: a highlight is never colour alone.
const MARK: Record<PacketMark, string> = {
  confirmed: WORDS.packet.mark_confirmed, unsure: WORDS.unsure,
  took_suggestion: WORDS.packet.mark_took_suggestion, kept: WORDS.packet.mark_kept,
};

export function PacketHistory({ history }: { history: Packet["history"] }) {
  return (
    <Box component="ol" sx={{ m: 0, p: 0, listStyle: "none", display: "grid", gap: 1 }}>
      {history.map((h, i) => (
        <Box component="li" key={i} data-marked={h.marks.length ? "" : undefined}
          sx={{ py: 0.75, borderTop: 1, borderColor: "divider", ...(h.marks.length ? { pl: 1, borderLeft: 3, borderLeftColor: "primary.main" } : {}) }}>
          <Typography variant="body2" color="text.secondary">{h.ask}</Typography>
          <Typography variant="body1" sx={{ fontWeight: 500 }}>{h.answer}</Typography>
          {h.marks.map((m) => <Chip key={m} size="small" label={MARK[m]} sx={{ mt: 0.5, mr: 0.5 }} />)}
        </Box>
      ))}
    </Box>
  );
}
