import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Drawer from "@mui/material/Drawer";
import Typography from "@mui/material/Typography";
import { IconListDetails } from "@tabler/icons-react";
import { useEffect, useRef, useState } from "react";
import { useParams } from "react-router";
import { getProject } from "../projects";
import { useWideLayout } from "../shell/useWideLayout";
import type { Guide } from "./api";
import { AnswerList } from "./components/AnswerList";
import { Bubble } from "./components/Bubble";
import { ReplyBox } from "./components/ReplyBox";
import { EndingView } from "./EndingView";
import { GuideShell } from "./GuideShell";
import { ProjectPanel } from "./ProjectPanel";
import { said } from "./said";
import { GuideTheme } from "./theme/GuideTheme";
import { DOESNT_FIT, TURN_HEADING } from "./turns/heading";
import { TurnView } from "./turns/TurnView";
import { useGuide } from "./useGuide";
import { WORDS } from "./words";

function History({ guide }: { guide: Guide }) {
  return <>{guide.history.map(({ shown, value }, i) => (
    <Box key={`${shown.turn_id}-${i}`} sx={{ display: "contents" }}>
      <Bubble from="app">{shown.ask}</Bubble>
      <Bubble from="you">{said(shown, value)}</Bubble>
    </Box>
  ))}</>;
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
      <GuideShell title={title} draft back={{ href: `/projects/${projectId}`, label: WORDS.back_to_project }}>
        <div ref={main}>
          {v.phase === "loading" && <Typography role="status">{WORDS.loading}</Typography>}
          {v.phase === "refused" && <Alert severity="info">{WORDS.refusals[v.why]}</Alert>}
          {v.phase === "pick" && (
            <AnswerList question={WORDS.pick_opening} headingProps={TURN_HEADING} disabled={v.busy}
              answers={v.openings.map((o) => ({ id: o.id, label: o.label }))} onAnswer={g.start} />
          )}
        </div>
      </GuideShell>
    );
  }

  const { guide, busy, locked, notice } = v;
  const current = guide.current;
  const ownPage = current?.turn_id.startsWith(DOESNT_FIT) ?? false;
  const last = guide.history.at(-1)?.shown.step;
  const step = guide.step ?? last;
  const back = guide.history.length && !locked
    ? { onClick: g.back, label: WORDS.back_a_turn, disabled: busy }
    : { href: `/projects/${projectId}`, label: WORDS.back_to_project };
  const panel = <ProjectPanel guide={guide} onChange={change} locked={locked} />;

  return (
    <GuideShell title={title} draft back={back} step={step ? { step: step.n, of: step.of, label: step.label } : undefined}
      aside={wide ? panel : undefined}
      actions={!wide && (
        <Button onClick={() => setPanelOpen(true)} startIcon={<IconListDetails size={20} aria-hidden="true" />}
          sx={{ minHeight: 48 }}>{WORDS.your_project}</Button>
      )}>
      <Box ref={main} sx={{ display: "flex", flexDirection: "column", gap: 1.5 }}>
        {notice && <Alert severity="info" onClose={g.dismissNotice}>{WORDS.notices[notice]}</Alert>}
        {!ownPage && <History guide={guide} />}
        {!ownPage && <Notes guide={guide} />}
        {current && <TurnView key={current.turn_id} shown={current} projectId={projectId} busy={busy} locked={locked}
          onAnswer={(value) => g.answer(current.turn_id, value)} />}
        {!current && guide.ending && <EndingView guide={guide} projectId={projectId} />}
        {locked
          ? <Alert severity="info">{WORDS.locked}</Alert>
          : !ownPage && <ReplyBox placeholder={WORDS.reply_placeholder} onSend={g.note} />}
      </Box>
      {!wide && (
        <Drawer anchor="bottom" open={panelOpen} onClose={() => setPanelOpen(false)}
          slotProps={{ paper: { sx: { maxHeight: "85dvh", borderTopLeftRadius: 16, borderTopRightRadius: 16 } } }}>
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
