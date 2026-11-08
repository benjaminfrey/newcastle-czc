import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import { useEffect, useState } from "react";
import { useParams } from "react-router";
import { GuideShell } from "../guide/GuideShell";
import { GuideTheme } from "../guide/theme/GuideTheme";
import { getBatch, isRefusal, type Batch, type Refusal } from "./api";
import { EntryReview } from "./EntryReview";
import { Refused } from "./LibraryHome";
import { libraryDraft, LW } from "./words";

// One batch (an Article): the chair's open questions first, then each entry as a resident reads it.
function BatchScreen({ name }: { name: string }) {
  const [batch, setBatch] = useState<Batch | Refusal | null>(null);
  useEffect(() => {
    let live = true;
    void getBatch(name).then((b) => { if (live) setBatch(b); });
    return () => { live = false; };
  }, [name]);
  return (
    <GuideShell title={`${LW.title}: ${name}`} back={{ href: "/library", label: LW.all_batches }} draft={libraryDraft()}>
      {batch === null && <Typography role="status">{LW.loading}</Typography>}
      {batch !== null && isRefusal(batch) && <Refused why={batch} />}
      {batch !== null && !isRefusal(batch) && <>
        {batch.open_questions.length > 0 && (
          <Box component="section" sx={{ p: 1.5, borderRadius: 2, bgcolor: "surfaceContainer" }}>
            <Typography variant="h6" component="h2">{LW.questions_heading}</Typography>
            <Box component="ol" sx={{ m: 0, pl: 3 }}>
              {batch.open_questions.map((q) => <Typography component="li" variant="body2" key={q}>{q}</Typography>)}
            </Box>
          </Box>
        )}
        {batch.entries.map((item) => <EntryReview key={item.entry.id} item={item} districts={batch.districts} />)}
      </>}
    </GuideShell>
  );
}

export default function BatchPage() {
  const { batch } = useParams();
  return <GuideTheme><BatchScreen name={batch ?? ""} /></GuideTheme>;
}
