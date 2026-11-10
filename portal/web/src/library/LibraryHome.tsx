import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Link from "@mui/material/Link";
import Typography from "@mui/material/Typography";
import { useEffect, useState } from "react";
import { Link as RouterLink } from "react-router";
import { GuideShell } from "../guide/GuideShell";
import { GuideTheme } from "../guide/theme/GuideTheme";
import { fill } from "../guide/words";
import { getBatches, isRefusal, type BatchCount, type Refusal } from "./api";
import { libraryDraft, LW } from "./words";

export function Refused({ why }: { why: Refusal }) {
  return <Alert severity="info">{why === "staff_only" || why === "signed_out" ? LW.staff_only : LW.unavailable}</Alert>;
}

// The library's batches (design 2, §7): one per Article, with where each stands.
function Batches() {
  const [rows, setRows] = useState<BatchCount[] | Refusal | null>(null);
  useEffect(() => {
    let live = true;
    void getBatches().then((r) => { if (live) setRows(r); });
    return () => { live = false; };
  }, []);
  return (
    <GuideShell title={LW.title} draft={libraryDraft()}>
      {rows === null && <Typography role="status">{LW.loading}</Typography>}
      {rows !== null && isRefusal(rows) && <Refused why={rows} />}
      {rows !== null && !isRefusal(rows) && (
        <Box component="ul" sx={{ m: 0, p: 0, listStyle: "none", display: "grid", gap: 1.5 }}>
          {rows.map((b) => (
            <Box component="li" key={b.batch} sx={{ py: 1, borderTop: 1, borderColor: "divider", display: "grid", gap: 0.5 }}>
              <Typography variant="h6" component="h2">
                <Link component={RouterLink} to={`/library/${b.batch}`} underline="hover"
                  sx={{ display: "inline-flex", alignItems: "center", minHeight: 48 }}>{b.batch}</Link>
              </Typography>
              <Typography variant="body2">{fill(LW.counts, b)}</Typography>
              {b.pending > 0 && <Typography variant="body2" sx={{ fontWeight: 500 }}>{fill(LW.pending_count, { n: b.pending })}</Typography>}
            </Box>
          ))}
        </Box>
      )}
    </GuideShell>
  );
}

export default function LibraryHome() {
  return <GuideTheme><Batches /></GuideTheme>;
}
