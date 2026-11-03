import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Typography from "@mui/material/Typography";
import { useEffect, useState } from "react";
import { Link } from "react-router";
import { getProject, type Needs } from "../projects";
import type { Guide } from "./api";
import { WhyCard } from "./components/WhyCard";
import { Fees } from "./Fees";
import { TURN_HEADING } from "./turns/heading";
import { WORDS, fill } from "./words";

function List({ heading, items }: { heading: string; items: { key: string; main: string; sub?: string }[] }) {
  if (!items.length) return null;
  return (
    <Box component="section" sx={{ display: "grid", gap: 0.5 }}>
      <Typography variant="subtitle2" component="h3">{heading}</Typography>
      <Box component="ul" sx={{ m: 0, p: 0, listStyle: "none" }}>
        {items.map((i) => (
          <Box component="li" key={i.key} sx={{ py: 0.75, borderTop: 1, borderColor: "divider" }}>
            <Typography>{i.main}</Typography>
            {i.sub && <Typography variant="body2" color="text.secondary">{i.sub}</Typography>}
          </Box>
        ))}
      </Box>
    </Box>
  );
}

// How the conversation ended (spec §4.6), in the content's words, with what the API settled.
// "This needs the Town's judgment" sends nothing: the handoff to the Code Enforcement Officer
// is the staff design's (4); until then it says what's open and keeps the project saved.
export function EndingView({ guide, projectId }: { guide: Guide; projectId: string }) {
  const e = guide.ending!;
  const [needs, setNeeds] = useState<Needs | null | undefined>(undefined);
  useEffect(() => {
    if (e.kind !== "ready") return;
    void getProject(projectId).then((p) => { if (typeof p === "object") setNeeds(p.needs); });
  }, [e.kind, projectId, guide.revision]);
  const ask = (t: string | null) => (t ? guide.history.find((h) => h.shown.turn_id === t)?.shown.ask : undefined);
  const reasons = WORDS.unsettled as Record<string, string>;

  return (
    <Box component="section" sx={{ display: "grid", gap: 2 }}>
      <Typography variant="h6" component="h2" {...TURN_HEADING}>{e.title}</Typography>
      <Typography>{e.body}</Typography>
      {e.entry && <WhyCard overline={e.entry.overline} answer={e.entry.answer} detail={e.entry.detail} />}
      {e.kind === "ready" && <>
        <Fees needs={needs} />
        <Button component={Link} to={`/projects/${projectId}/guide/check`} variant="contained"
          sx={{ minHeight: 48, justifySelf: "start", px: 3 }}>{WORDS.check_and_send}</Button>
      </>}
      {e.kind === "no_permit" && <>
        <Typography>{WORDS.no_permit_keep}</Typography>
        <List heading={WORDS.settled_heading} items={e.settled.map((s) => ({ key: s.turn_id, main: ask(s.turn_id) ?? s.turn_id, sub: WORDS.fits_mark }))} />
      </>}
      {e.kind === "town_judgment" && <>
        <List heading={WORDS.settled_heading} items={e.settled.map((s) => ({ key: s.turn_id, main: ask(s.turn_id) ?? s.turn_id, sub: WORDS.fits_mark }))} />
        <List heading={WORDS.unsettled_heading} items={e.unsettled.map((u, i) => ({
          key: `${u.turn_id}|${u.reason}|${i}`, main: reasons[u.reason] ?? WORDS.town_decides, sub: ask(u.turn_id) }))} />
        <Typography>{WORDS.talk_to_town}</Typography>
      </>}
      {e.kind === "not_here" && <>
        {e.allowed_uses.map((d) => (
          <List key={d.district} heading={fill(WORDS.allowed_heading, { district: d.district })}
            items={d.uses.map((u) => ({ key: u.use_key, main: u.code_name }))} />
        ))}
        <Typography>{WORDS.talk_to_town}</Typography>
      </>}
      {!["ready", "no_permit", "town_judgment", "not_here"].includes(e.kind) && <Typography>{WORDS.town_decides}</Typography>}
    </Box>
  );
}
