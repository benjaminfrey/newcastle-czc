import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Dialog from "@mui/material/Dialog";
import DialogActions from "@mui/material/DialogActions";
import DialogContent from "@mui/material/DialogContent";
import DialogContentText from "@mui/material/DialogContentText";
import DialogTitle from "@mui/material/DialogTitle";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import { useId, useRef, useState } from "react";
import type { Opening } from "./api";
import { LotScene } from "./pictures/LotScene";
import { fill, WORDS } from "./words";

type StartOpts = { addPart?: string; note?: string };
type Props = { openings: Opening[]; busy: boolean; onStart: (id: string, opts: StartOpts) => Promise<boolean> };

const lower = (s: string) => s.charAt(0).toLowerCase() + s.slice(1);

// "What would you like to do?" as a picture (guided plan 5, design §6): the scene, the same
// projects as a list for a keyboard or a screen reader, and a box for the person's own words,
// which the guide never reads (decision 14) and keeps as the conversation's first note.
export function OpeningPicker({ openings, busy, onStart }: Props) {
  const w = WORDS.picker;
  const [text, setText] = useState("");
  const [asking, setAsking] = useState<Opening | null>(null);
  const [soon, setSoon] = useState<Opening | null>(null);
  const [pending, setPending] = useState(false);
  const sending = useRef(false);
  const listId = useId();
  const off = busy || pending;

  const go = async (o: Opening, opts: StartOpts) => {
    if (sending.current) return;
    sending.current = true;
    setPending(true);
    const note = text.trim();
    try {
      await onStart(o.id, note ? { ...opts, note } : opts);
    } finally {
      sending.current = false;
      setPending(false);
    }
  };
  const tap = (o: Opening) => {
    if (off) return;
    if (!o.guided) setSoon(o);
    else if (!o.in_project && o.part) setAsking(o);
    else void go(o, {});
  };
  const byPicture = (picture: string) => openings.find((o) => o.picture === picture);

  return (
    <Box component="section" data-turn="pick_opening" sx={{ display: "grid", gap: 2 }}>
      <Typography variant="h5" component="h2">{WORDS.pick_opening}</Typography>
      <LotScene description={w.description} labels={Object.fromEntries(openings.map((o) => [o.picture, o.label]))}
        onSpot={(p) => { const o = byPicture(p); if (o) tap(o); }} />
      <TextField label={w.box_label} value={text} onChange={(e) => setText(e.target.value)} multiline minRows={2} fullWidth />
      <Box>
        <Typography id={listId} variant="subtitle1" component="h3">{w.list_heading}</Typography>
        <Box component="ul" aria-labelledby={listId} sx={{ listStyle: "none", p: 0, m: 0, display: "grid", gap: 1 }}>
          {openings.map((o) => (
            <li key={o.id}>
              <Button variant="outlined" fullWidth disabled={off} onClick={() => tap(o)}
                sx={{ minHeight: 48, justifyContent: "flex-start" }}>{o.label}</Button>
            </li>
          ))}
        </Box>
      </Box>

      <Dialog open={asking !== null} onClose={() => !pending && setAsking(null)} aria-labelledby={`${listId}-add`}>
        {asking && <>
          <DialogTitle id={`${listId}-add`}>{fill(w.add_title, { label: lower(asking.label) })}</DialogTitle>
          <DialogContent><DialogContentText>{w.add_body}</DialogContentText></DialogContent>
          <DialogActions>
            <Button onClick={() => setAsking(null)} disabled={pending} sx={{ minHeight: 48 }}>{w.add_no}</Button>
            <Button variant="contained" disabled={off} sx={{ minHeight: 48 }}
              onClick={() => void go(asking, { addPart: asking.part! })}>{w.add_yes}</Button>
          </DialogActions>
        </>}
      </Dialog>

      <Dialog open={soon !== null} onClose={() => setSoon(null)} aria-labelledby={`${listId}-soon`}>
        {soon && <>
          <DialogTitle id={`${listId}-soon`}>{fill(w.soon_title, { label: soon.label })}</DialogTitle>
          <DialogContent><DialogContentText>{w.soon_body}</DialogContentText></DialogContent>
          <DialogActions>
            <Button variant="contained" onClick={() => setSoon(null)} sx={{ minHeight: 48 }}>{w.soon_ok}</Button>
          </DialogActions>
        </>}
      </Dialog>
    </Box>
  );
}
