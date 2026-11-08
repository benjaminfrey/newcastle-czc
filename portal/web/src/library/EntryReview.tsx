import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Dialog from "@mui/material/Dialog";
import DialogActions from "@mui/material/DialogActions";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import { useEffect, useId, useState } from "react";
import type { Entry } from "../guide/api";
import { entryCard } from "../guide/components/entryCard";
import { fill } from "../guide/words";
import { decide, getPreview, isRefusal, pullEntry, type District, type ReviewItem, type Texts } from "./api";
import { LW } from "./words";

const FIELDS = ["overline", "answer", "detail", "why"] as const;
const select = { select: { native: true }, inputLabel: { shrink: true } } as const;

// One entry on the review page (design 2, §7): as a resident sees it in the district picked, the
// Code it cites, its checks and status, and the chair's four actions.
export function EntryReview({ item, districts }: { item: ReviewItem; districts: District[] }) {
  const e = item.entry;
  const [district, setDistrict] = useState(districts[0]?.key ?? "");
  const buildings = districts.find((d) => d.key === district)?.buildings ?? [];
  const [building, setBuilding] = useState<string | null>(buildings[0] ?? null);
  const [preview, setPreview] = useState<Entry | "none" | null>(null);
  const [pending, setPending] = useState<string | null>(item.pending ? LW.actions[item.pending.action] : null);
  const [editing, setEditing] = useState(false);
  const [texts, setTexts] = useState<Texts>({ overline: e.overline, answer: e.answer, detail: e.detail, why: e.why });
  const [note, setNote] = useState("");
  const [pulling, setPulling] = useState(false);
  const [why, setWhy] = useState("");
  const [pulled, setPulled] = useState(item.pulled?.why ?? null);
  const titleId = useId();

  useEffect(() => {
    if (!buildings.includes(building ?? "")) setBuilding(buildings[0] ?? null);
  }, [district]);  // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => {
    if (!district) return;
    let live = true;
    void getPreview(e.id, district, building).then((p) => { if (live) setPreview(isRefusal(p) ? "none" : p); });
    return () => { live = false; };
  }, [e.id, district, building]);

  const act = async (action: "approve" | "edit" | "send_back") => {
    const extra = action === "edit" ? { body: texts } : action === "send_back" ? { note: note.trim() } : undefined;
    const r = extra ? await decide(e.id, e.version, action, extra) : await decide(e.id, e.version, action);
    if (!isRefusal(r)) {
      setPending(LW.actions[action]);
      if (action === "edit") setEditing(false);
    }
  };
  const pull = async () => {
    const r = await pullEntry(e.id, e.version, why.trim());
    if (!isRefusal(r)) { setPulled(why.trim()); setPulling(false); }
  };

  return (
    <Box component="section" aria-labelledby={`${titleId}-h`} sx={{ display: "grid", gap: 1.5, py: 2, borderTop: 1, borderColor: "divider" }}>
      <Typography id={`${titleId}-h`} variant="h6" component="h2">{e.overline}</Typography>
      <Typography variant="body2" sx={{ fontWeight: 500 }}>{LW.status[e.status]} · v{e.version} · {e.id}</Typography>
      {pending && <Typography variant="body2" sx={{ fontWeight: 500 }}>{fill(LW.pending, { action: pending })}</Typography>}
      {pulled && <Typography variant="body2" color="error">{fill(LW.pulled_now, { why: pulled })}</Typography>}
      {e.review_note && <Typography variant="body2">{fill(LW.sent_back_note, { note: e.review_note })}</Typography>}

      <Box sx={{ display: "flex", gap: 1.5, flexWrap: "wrap" }}>
        <TextField select label={LW.district} value={district} onChange={(ev) => setDistrict(ev.target.value)}
          slotProps={select} sx={{ minWidth: 220 }}>
          {districts.map((d) => <option key={d.key} value={d.key}>{d.name}</option>)}
        </TextField>
        {buildings.length > 0 && (
          <TextField select label={LW.building} value={building ?? ""} onChange={(ev) => setBuilding(ev.target.value)}
            slotProps={select} sx={{ minWidth: 200 }}>
            {buildings.map((b) => <option key={b} value={b}>{b}</option>)}
          </TextField>
        )}
      </Box>
      {preview === "none" ? <Typography variant="body2">{LW.not_for_district}</Typography> : preview && entryCard(preview)}

      <Box>
        <Typography variant="subtitle2" component="h3">{LW.code_heading}</Typography>
        {item.code.map((c) => (
          <Typography key={c.cite} variant="body2" sx={{ whiteSpace: "pre-wrap" }}><b>{c.cite}</b> {c.text}</Typography>
        ))}
      </Box>
      {item.flags.length > 0 && (
        <Box>
          <Typography variant="subtitle2" component="h3">{LW.flags_heading}</Typography>
          {item.flags.map((f) => <Typography key={f} variant="body2">{f}</Typography>)}
        </Box>
      )}

      {editing && (
        <Box sx={{ display: "grid", gap: 1.5 }}>
          {FIELDS.map((k) => (
            <TextField key={k} label={LW.fields[k]} value={texts[k]} multiline={k !== "overline"}
              onChange={(ev) => setTexts({ ...texts, [k]: ev.target.value })} />
          ))}
          <Box sx={{ display: "flex", gap: 1 }}>
            <Button variant="contained" onClick={() => void act("edit")} sx={{ minHeight: 48 }}>{LW.save_edit}</Button>
            <Button onClick={() => setEditing(false)} sx={{ minHeight: 48 }}>{LW.cancel}</Button>
          </Box>
        </Box>
      )}
      <TextField label={LW.note_label} value={note} onChange={(ev) => setNote(ev.target.value)} multiline />
      <Box sx={{ display: "flex", gap: 1, flexWrap: "wrap" }}>
        <Button variant="contained" onClick={() => void act("approve")} sx={{ minHeight: 48 }}>{LW.approve}</Button>
        {!editing && <Button variant="outlined" onClick={() => setEditing(true)} sx={{ minHeight: 48 }}>{LW.edit}</Button>}
        <Button variant="outlined" disabled={!note.trim()} onClick={() => void act("send_back")} sx={{ minHeight: 48 }}>{LW.send_back}</Button>
        <Button color="error" onClick={() => setPulling(true)} sx={{ minHeight: 48 }}>{LW.pull}</Button>
      </Box>

      <Dialog open={pulling} onClose={() => setPulling(false)} aria-labelledby={titleId}>
        <DialogTitle id={titleId}>{LW.confirm_pull}</DialogTitle>
        <DialogContent sx={{ display: "grid", gap: 1.5 }}>
          <Typography variant="body2">{LW.confirm_pull_body}</Typography>
          <TextField label={LW.why_label} value={why} onChange={(ev) => setWhy(ev.target.value)} autoFocus />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setPulling(false)} sx={{ minHeight: 48 }}>{LW.cancel}</Button>
          <Button color="error" variant="contained" disabled={!why.trim()} onClick={() => void pull()} sx={{ minHeight: 48 }}>
            {LW.confirm_pull_yes}</Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}
