import { useEffect, useMemo } from "react";
import { Navigate, useNavigate, useParams, useSearchParams } from "react-router";
import { REVIEW_STEP, START_STEPS, statusOf, stepModels } from "../forms/steps";
import AppShell from "../shell/AppShell";
import type { ShellStep } from "../shell/types";
import { useWideLayout } from "../shell/useWideLayout";
import { ApplicationProvider, useApplication } from "./ApplicationStore";
import HubPane from "./HubPane";
import ItemSheet from "./ItemSheet";
import StepPane from "./StepPane";

// /applications/:id/:stepId — one application in the shell.
export default function ApplicationPage() {
  const { id = "" } = useParams();
  return <ApplicationProvider id={id}><Steps id={id} /></ApplicationProvider>;
}

function Steps({ id }: { id: string }) {
  const { stepId } = useParams();
  const [params, setParams] = useSearchParams();
  const navigate = useNavigate();
  const wide = useWideLayout();
  const store = useApplication();
  const { app, form, cur, problem, saveState, flush, markVisited, visited, reload } = store;
  const base = `/applications/${id}`;

  const models = useMemo(() => (form && cur ? stepModels(form, cur) : []), [form, cur]);
  const shellSteps: ShellStep[] = useMemo(() => [
    // The start steps are behind the applicant by now; they lead to the review of what was found.
    ...START_STEPS.map((s) => ({ id: s.id, title: s.title, status: "done" as const, unknowns: 0, href: `${base}/review` })),
    ...models.map((m) => ({
      id: m.id, title: m.title, href: `${base}/${m.id}`, ...statusOf(m, cur!, visited),
      children: m.hub?.items.map((i) => ({ id: i.id, title: i.label, status: i.status, unknowns: i.unknowns,
                                            href: `${base}/${m.id}?item=${i.id}` })),
    })),
    { id: REVIEW_STEP.id, title: REVIEW_STEP.title, status: "todo" as const, unknowns: 0, href: `${base}/review` },
  ], [models, cur, visited, base]);

  const current = models.find((m) => m.id === stepId);
  const at = models.findIndex((m) => m.id === stepId);

  // Arriving at a step: the title takes focus and names the page.
  useEffect(() => {
    if (!current || !form) return;
    document.title = `${current.title} — ${form.official_title}`;
    const h1 = document.querySelector<HTMLElement>("[data-step-title]");
    h1?.focus();
  }, [current?.id, form]); // eslint-disable-line react-hooks/exhaustive-deps

  if (problem === "signed_out") return <Navigate to="/signin" replace />;
  if (problem) return <p role="alert" className="p-8">{problem}</p>;
  if (!app || !form || !cur) return <p className="p-8">Loading…</p>;
  if (stepId && !current) return <Navigate to={base} replace />;
  if (!stepId && wide) {
    const first = models.find((m) => statusOf(m, cur, visited).status !== "done") ?? models[0];
    return <Navigate to={first ? `${base}/${first.id}` : `${base}/review`} replace />;
  }

  async function next() {
    await flush();
    if (current) markVisited(current.id);
    const following = models[at + 1];
    navigate(following ? `${base}/${following.id}` : `${base}/review`);
  }

  const itemId = params.get("item");
  return (
    <AppShell
      steps={shellSteps}
      currentId={current?.id ?? null}
      formTitle={form.official_title}
      saveState={saveState}
      rootHref={base}
      onDone={() => void flush().then(() => navigate("/my-applications"))}
      onReload={() => void reload()}
      onStep={(sid) => navigate(shellSteps.find((s) => s.id === sid)?.href ?? base)}
      actions={current ? {
        back: at > 0 ? () => navigate(`${base}/${models[at - 1].id}`) : undefined,
        onContinue: () => void next(),
        continueLabel: models[at + 1] ? "Continue" : "Review",
      } : {}}
    >
      {current?.kind === "fields" && <StepPane rows={current.rows} sections={current.sections} />}
      {current?.kind === "hub" && (
        <HubPane step={current} onOpen={(item, page) => setParams(page ? { item, page } : { item })} />
      )}
      {current?.kind === "hub" && itemId && current.hub!.items.some((i) => i.id === itemId) && (
        <ItemSheet step={current} itemId={itemId} pageId={params.get("page")}
                   onPage={(page) => setParams({ item: itemId, page })}
                   onClose={() => setParams({})} />
      )}
    </AppShell>
  );
}
