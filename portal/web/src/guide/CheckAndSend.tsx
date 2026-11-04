import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Link from "@mui/material/Link";
import Typography from "@mui/material/Typography";
import { useCallback, useEffect, useState } from "react";
import { Navigate, Link as RouterLink, useNavigate, useParams } from "react-router";
import { getProject, submitProject, type Missing, type ProjectState } from "../projects";
import { Fees } from "./Fees";
import { GuideShell } from "./GuideShell";
import { distancesOf, DrawingList } from "./drawing/DrawingList";
import { LotDrawing } from "./drawing/LotDrawing";
import { useDrawing } from "./drawing/useDrawing";
import { ProjectPanel } from "./ProjectPanel";
import { GuideTheme } from "./theme/GuideTheme";
import { useGuide } from "./useGuide";
import { WORDS } from "./words";

type Sent = "idle" | "sending" | "sent" | { missing: Missing } | { refused: keyof typeof WORDS.refusals } | "conflict";

// What the form still lacks, by its own labels, each linking to its step on the project's form.
function StillNeeds({ missing, project }: { missing: Missing; project: ProjectState }) {
  const fields = project.form.sections.flatMap((s) => s.fields.map((f) => ({ f, step: s.step })));
  return (
    <Alert severity="info">
      <Typography sx={{ fontWeight: 500 }}>{WORDS.still_needs}</Typography>
      <Box component="ul" sx={{ m: 0, pl: 2.5 }}>
        {missing.map((m) => {
          const hit = fields.find((x) => x.f.id === m.field_id);
          const label = hit?.f.label ?? m.field_id;
          return (
            <li key={`${m.field_id}|${m.item_id ?? ""}`}>
              <Link component={RouterLink} to={`/projects/${project.id}/${hit?.step ?? ""}`}>{label}</Link>
            </li>
          );
        })}
      </Box>
      <Typography variant="body2" sx={{ mt: 1 }}>{WORDS.finish_on_form}</Typography>
    </Alert>
  );
}

// Check and send (spec §4.7): the project as the conversation has it, each answer with a Change
// back into the conversation, the fees, then Send. Only for a project whose guide is ready.
function Check({ projectId }: { projectId: string }) {
  const g = useGuide(projectId);
  const drawing = useDrawing(projectId, g.view.phase === "talk" ? g.view.guide.revision : undefined);
  const navigate = useNavigate();
  const [project, setProject] = useState<ProjectState | null>(null);
  const [sent, setSent] = useState<Sent>("idle");
  const load = useCallback(() => getProject(projectId).then((p) => { if (typeof p === "object") setProject(p); }), [projectId]);
  useEffect(() => { void load(); }, [load]);

  const v = g.view;
  if (v.phase === "talk" && v.guide.ending?.kind !== "ready") return <Navigate to={`/projects/${projectId}/guide`} replace />;
  if (v.phase !== "talk" && v.phase !== "loading") return <Navigate to={`/projects/${projectId}/guide`} replace />;

  const change = async (t: string) => {
    await g.change(t);
    navigate(`/projects/${projectId}/guide`, { replace: true });
  };
  const send = async () => {
    if (!project || sent === "sending") return;
    setSent("sending");
    const r = await submitProject(projectId, project.revision);
    if (typeof r === "string") setSent({ refused: r });
    else if ("incomplete" in r) setSent({ missing: r.incomplete });
    else if ("conflict" in r) {
      // Another window changed the project: reload both, so one no longer ready is redirected.
      setSent("conflict");
      await Promise.all([load(), g.reload()]);
    }
    else if ("invalid" in r) setSent({ refused: "unavailable" });
    else setSent("sent");
  };

  return (
    <GuideShell title={project?.title ?? WORDS.your_project} draft
      back={{ href: `/projects/${projectId}/guide`, label: WORDS.back_to_conversation }}>
      <Box sx={{ display: "grid", gap: 2.5 }}>
        <Typography variant="h6" component="h2">{WORDS.check_heading}</Typography>
        {v.phase === "talk" && <ProjectPanel guide={v.guide} onChange={(t) => void change(t)} locked={v.locked}
          drawing={drawing && (
            <Box sx={{ display: "grid", gap: 1 }}>
              <LotDrawing drawing={drawing} distances={distancesOf(v.guide)} />
              <DrawingList drawing={drawing} guide={v.guide} />
            </Box>
          )} />}
        {project && <Fees needs={project.needs} />}
        {sent === "conflict" && <Alert severity="info">{WORDS.notices.changed_elsewhere}</Alert>}
        {typeof sent === "object" && "refused" in sent && <Alert severity="info">{WORDS.refusals[sent.refused]}</Alert>}
        {typeof sent === "object" && "missing" in sent && project && <StillNeeds missing={sent.missing} project={project} />}
        {sent === "sent" ? (
          <Box sx={{ display: "grid", gap: 1 }}>
            <Typography role="status" sx={{ fontWeight: 500 }}>{WORDS.sent}</Typography>
            <Link component={RouterLink} to={`/projects/${projectId}`}>{WORDS.to_project}</Link>
          </Box>
        ) : (
          <Button variant="contained" onClick={() => void send()} disabled={!project || sent === "sending"}
            sx={{ minHeight: 48, justifySelf: "start", px: 3 }}>{sent === "sending" ? WORDS.sending : WORDS.send}</Button>
        )}
      </Box>
    </GuideShell>
  );
}

export default function CheckAndSend() {
  const { id } = useParams();
  return <GuideTheme><Check projectId={id!} /></GuideTheme>;
}
