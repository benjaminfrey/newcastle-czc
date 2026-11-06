import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Drawer from "@mui/material/Drawer";
import Typography from "@mui/material/Typography";
import { IconListDetails } from "@tabler/icons-react";
import { useEffect, useId, useRef, useState } from "react";
import { useParams } from "react-router";
import { getProject } from "../projects";
import { useWideLayout } from "../shell/useWideLayout";
import type { Guide } from "./api";
import { AnswerList } from "./components/AnswerList";
import { distancesOf, DrawingList } from "./drawing/DrawingList";
import type { Edge } from "./drawing/geometry";
import { LotDrawing } from "./drawing/LotDrawing";
import { useDrawing } from "./drawing/useDrawing";
import { Bubble } from "./components/Bubble";
import { ReplyBox } from "./components/ReplyBox";
import { EndingView } from "./EndingView";
import { GuideShell } from "./GuideShell";
import { ProjectPanel } from "./ProjectPanel";
import { said } from "./said";
import { GuideTheme } from "./theme/GuideTheme";
import { DOESNT_FIT, TURN_HEADING } from "./turns/heading";
import { parseNumber } from "./turns/NumberAnswer";
import { TurnView } from "./turns/TurnView";
import { useGuide } from "./useGuide";

const PICK_OPENING = "pick_opening";   // the engine's picker after "No" (guided plan 2)
import { draftWording, fill, WORDS } from "./words";

function History({ guide }: { guide: Guide }) {
  return <>{guide.history.map(({ shown, value }, i) => (
    <Box key={`${shown.turn_id}-${i}`} sx={{ display: "contents" }}>
      <Bubble from="app">{shown.ask}</Bubble>
      <Bubble from="you">{said(shown, value)}</Bubble>
    </Box>
  ))}</>;
}

// What the last Change reopened, until the person closes it; a new list shows again.
function Reopened({ guide }: { guide: Guide }) {
  const id = useId();
  const list = guide.reopened;
  const key = list.map((r) => r.turn_id).join("|");
  const [closed, setClosed] = useState("");
  if (!list.length || closed === key) return null;
  const heading = list.length === 1 ? WORDS.reopened_one : fill(WORDS.reopened_many, { n: list.length });
  return (
    <Alert severity="info" role="status" aria-labelledby={id} onClose={() => setClosed(key)}>
      <Typography id={id} sx={{ fontWeight: 500 }}>{heading}</Typography>
      <Box component="ul" sx={{ m: 0, pl: 2.5 }}>{list.map((r) => <li key={r.turn_id}>{r.ask}</li>)}</Box>
    </Alert>
  );
}

function Notes({ guide }: { guide: Guide }) {
  if (!guide.notes.length) return null;
  return <>
    {guide.notes.map((n, i) => <Bubble key={`${n.at}-${i}`} from="you">{n.body}</Bubble>)}
    <Typography variant="body2" color="text.secondary" sx={{ alignSelf: "flex-end", maxWidth: "88%", textAlign: "right" }}>
      {WORDS.notes_kept}
    </Typography>
  </>;
}

// The guided conversation for one project (guided plan 3; spec §4): what was said, the turn
// being asked, or the ending; Back in the app bar; the project beside it on a computer and a
// tap away on a phone. Everything shown comes from useGuide, which holds what the API returned.
function GuideScreen({ projectId }: { projectId: string }) {
  const g = useGuide(projectId);
  const wide = useWideLayout();
  const [title, setTitle] = useState<string>(WORDS.your_project);
  const [panelOpen, setPanelOpen] = useState(false);
  const main = useRef<HTMLDivElement>(null);
  const v = g.view;
  const turnId = v.phase === "talk" ? (v.guide.current?.turn_id ?? `ending:${v.guide.ending?.kind}`) : null;
  const seen = useRef<string | null>(null);
  const drawing = useDrawing(projectId, v.phase === "talk" ? v.guide.revision : undefined);
  // The number field's text on a setback turn, held here so a drag in the drawing can set it.
  const [draft, setDraft] = useState<{ key: string; text: string }>({ key: "", text: "" });

  useEffect(() => {
    void getProject(projectId).then((p) => { if (typeof p === "object") setTitle(p.title); });
  }, [projectId]);

  // A new question takes focus, so a screen reader reads it and a keyboard starts there. The
  // first one on arrival doesn't: the page's own heading comes first then.
  useEffect(() => {
    if (turnId == null) return;
    if (seen.current != null && seen.current !== turnId) {
      main.current?.querySelector<HTMLElement>("[data-turn-heading]")?.focus();
    }
    seen.current = turnId;
  }, [turnId]);

  const change = (t: string) => { setPanelOpen(false); g.change(t); };

  if (v.phase !== "talk") {
    return (
      <GuideShell title={title} draft={draftWording()} back={{ href: `/projects/${projectId}`, label: WORDS.back_to_project }}>
        <div ref={main}>
          {v.phase === "loading" && <Typography role="status">{WORDS.loading}</Typography>}
          {v.phase === "refused" && <Alert severity="info">{WORDS.refusals[v.why]}</Alert>}
          {v.phase === "pick" && (
            <Box component="section" data-turn="pick_opening">
              <AnswerList question={WORDS.pick_opening} headingProps={TURN_HEADING} disabled={v.busy}
                answers={v.openings.map((o) => ({ id: o.id, label: o.label }))} onAnswer={(id) => void g.start(id)} />
            </Box>
          )}
        </div>
      </GuideShell>
    );
  }

  const { guide, busy, locked, notice, epoch } = v;
  const current = guide.current;
  const ownPage = current?.turn_id.startsWith(DOESNT_FIT) ?? false;
  const last = guide.history.at(-1)?.shown.step;
  const step = guide.step ?? last;
  const back = guide.history.length && !locked
    ? { onClick: g.back, label: WORDS.back_a_turn, disabled: busy }
    : { href: `/projects/${projectId}`, label: WORDS.back_to_project };
  // The lot drawing (plan 4): beside the conversation on a computer, inside a "where" turn on a
  // phone, and always in the project sheet. Only the turn being asked can be dragged or tapped.
  const asking = current?.drawing ?? null;
  const edge: Edge | null = asking === "front_setback" ? "front" : asking === "secondary" ? "side_2"
    : asking && asking !== "front" ? asking : null;
  const turnKey = current ? `${current.turn_id}:${epoch}` : "";
  const text = draft.key === turnKey ? draft.text : "";
  const setText = (t: string) => setDraft({ key: turnKey, text: t });
  const distances = distancesOf(guide);
  if (edge) {
    const n = parseNumber(text);
    if (typeof n === "number") distances[edge] = n; else delete distances[edge];
  }
  const picture = (live: boolean) => drawing && (
    <LotDrawing drawing={drawing} distances={distances} asking={live ? asking : null}
      onPickLine={(id) => { if (!busy && !locked && current) void g.answer(current.turn_id, id); }}
      onDrag={(n) => { if (!locked) setText(String(n)); }} />
  );
  const list = drawing && <DrawingList drawing={drawing} guide={guide} />;
  const figure = (live: boolean) => drawing && <Box sx={{ display: "grid", gap: 1 }}>{picture(live)}{list}</Box>;
  // On a phone the list follows the answer, so the field stays close to its question.
  const inTurn = !wide && asking;
  const panel = <ProjectPanel guide={guide} onChange={change} locked={locked} drawing={figure(wide && !!asking)} />;

  return (
    <GuideShell title={title} draft={draftWording(guide.drafts)} back={back} step={step ? { step: step.n, of: step.of, label: step.label } : undefined}
      aside={wide ? panel : undefined}
      actions={!wide && (
        <Button onClick={() => setPanelOpen(true)} startIcon={<IconListDetails size={20} aria-hidden="true" />}
          sx={{ minHeight: 48 }}>{WORDS.your_project}</Button>
      )}>
      <Box ref={main} sx={{ display: "flex", flexDirection: "column", gap: 1.5 }}>
        {notice && <Alert severity="info" onClose={g.dismissNotice}>{WORDS.notices[notice]}</Alert>}
        {!ownPage && <History guide={guide} />}
        {!ownPage && <Notes guide={guide} />}
        <Reopened guide={guide} />
        {current && <TurnView key={turnKey} shown={current} projectId={projectId} busy={busy}
          locked={locked} figure={inTurn ? picture(true) : undefined} footer={inTurn ? list : undefined}
          text={edge ? text : undefined} onTextChange={edge ? setText : undefined}
          // After "No" on "So you mean…", the picture chosen starts the conversation again from it.
          onAnswer={(value) => void (current.turn_id === PICK_OPENING ? g.start(String(value)) : g.answer(current.turn_id, value))} />}
        {!current && guide.ending && <EndingView guide={guide} projectId={projectId} />}
        {locked
          ? <Alert severity="info">{WORDS.locked}</Alert>
          : !ownPage && <ReplyBox placeholder={WORDS.reply_placeholder} onSend={g.note} />}
      </Box>
      {!wide && (
        <Drawer anchor="bottom" open={panelOpen} onClose={() => setPanelOpen(false)}
          slotProps={{ paper: { "aria-label": WORDS.your_project,
            sx: { maxHeight: "85dvh", borderTopLeftRadius: 16, borderTopRightRadius: 16 } } }}>
          <Box sx={{ p: 1 }}>
            <Button onClick={() => setPanelOpen(false)} sx={{ minHeight: 48 }}>{WORDS.close}</Button>
            {panel}
          </Box>
        </Drawer>
      )}
    </GuideShell>
  );
}

export default function GuidePage() {
  const { id } = useParams();
  return <GuideTheme><GuideScreen projectId={id!} /></GuideTheme>;
}
