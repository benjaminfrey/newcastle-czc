import { useEffect, useMemo, useRef, useState } from "react";
import { Navigate, useNavigate, useParams, useSearchParams } from "react-router";
import Dots from "../shell/Dots";
import { valueOf, type Row } from "../forms/applicability";
import { groupOf, place, screenAfter, screenBefore, screensOf, type Place, type Screen } from "../forms/screens";
import { REVIEW_STEP, START_STEPS, statusOf, stepModels } from "../forms/steps";
import { buildingLabel } from "../controls/pickers";
import AppShell from "../shell/AppShell";
import { commitFocused } from "../shell/commitFocused";
import type { ShellStep } from "../shell/types";
import { useWideLayout } from "../shell/useWideLayout";
import AnswerTrail, { type Chip } from "./AnswerTrail";
import { ApplicationProvider, useApplication } from "./ApplicationStore";
import { display } from "./OfficialGroup";
import ReviewPane from "./ReviewPane";
import WizardPane, { headingOf, rowKey } from "./WizardPane";

// /applications/:id/:stepId?screen=&item=&return=review — one application, one question at a time.
export default function ApplicationPage() {
  const { id = "" } = useParams();
  return <ApplicationProvider id={id}><Steps id={id} /></ApplicationProvider>;
}

const empty = (v: unknown) => v === null || v === undefined || v === "" || (Array.isArray(v) && v.length === 0);
type Pending = { from: Place } | { step: string; item: string };

function Steps({ id }: { id: string }) {
  const { stepId } = useParams();
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const wide = useWideLayout();
  const store = useApplication();
  const { app, form, cur, problem, saveState, flush, markVisited, visited, reload, setAnswer, addItem } = store;
  const base = `/applications/${id}`;
  const [direction, setDirection] = useState<1 | -1>(1);
  const [editing, setEditing] = useState(false);
  const [pending, setPending] = useState<Pending | null>(null);
  const busy = useRef(false);
  const errorsRef = useRef<Record<string, string>>({});

  const models = useMemo(() => (form && cur ? stepModels(form, cur) : []), [form, cur]);
  const isReview = stepId === REVIEW_STEP.id;
  const current = models.find((m) => m.id === stepId);
  const list = useMemo(() => (form && cur && current ? screensOf(form, cur, current) : []), [form, cur, current]);
  const returning = params.get("return") === "review";

  // The screen the address names; a field from review's "Still to answer" (?focus=) opens its screen;
  // an item alone opens its first screen.
  const sp = params.get("screen");
  const ip = params.get("item");
  const focus = params.get("focus");
  const screen: Screen | undefined =
    (sp && list.find((s) => s.id === sp && (!ip || s.itemId === ip)))
    || (focus && list.find((s) => s.rows.some((r) => r.field.id === focus && (!ip || r.itemId === ip))))
    || (ip && list.find((s) => s.itemId === ip))
    || list[0];
  const group = screen ? groupOf(list, screen) : [];
  const at = screen ? group.indexOf(screen) : -1;
  const paneKey = screen ? `${screen.step}:${screen.itemId ?? ""}:${screen.id}` : stepId ?? "root";

  const href = (p: Place, ret = returning) => {
    const q = new URLSearchParams({ screen: p.screen, ...(p.item ? { item: p.item } : {}), ...(ret ? { return: "review" } : {}) });
    return `${base}/${p.step}?${q.toString().replace(/%3A/g, ":")}`; // "any:component" reads as written
  };
  const go = (p: Place | { review: true }, dir: 1 | -1 = 1, ret = returning) => {
    setDirection(dir);
    navigate("review" in p ? `${base}/review` : href(p, ret));
  };

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

  // A step counts as visited once it is opened, however the person got there.
  const currentId = current?.id;
  useEffect(() => { if (currentId) markVisited(currentId); }, [currentId, markVisited]);
  useEffect(() => { setEditing(false); errorsRef.current = {}; }, [paneKey]);

  const heading = isReview ? REVIEW_STEP.title : screen ? headingOf(screen) : current?.title;
  useEffect(() => {
    if (!heading || !form) return;
    document.title = `${heading} — ${form.official_title}`;
    (document.querySelector<HTMLElement>("[data-screen-title]") ?? document.querySelector<HTMLElement>("[data-step-title]"))?.focus();
  }, [heading, form, paneKey]);

  // Moving on is worked out after the answer has landed, so screens that an answer adds or
  // removes (the owner's questions) are counted, and a new building's first screen exists.
  useEffect(() => {
    if (!pending || !form || !cur) return;
    if ("item" in pending) {
      const m = models.find((x) => x.id === pending.step);
      const first = m && screensOf(form, cur, m).find((s) => s.itemId === pending.item);
      if (!first) return; // the new item hasn't arrived yet
      setPending(null);
      return go(place(first));
    }
    setPending(null);
    const after = screenAfter(form, cur, models, pending.from);
    const leaving = "review" in after || after.step !== pending.from.step;
    if (leaving) markVisited(pending.from.step);
    if (returning) {
      // From review's Change: back to review, unless the answer opened a question still to answer.
      if ("review" in after) return go(after);
      const to = after;
      const next = models.find((m) => m.id === to.step);
      const s = next && screensOf(form, cur, next).find((x) => x.id === to.screen && (to.item === undefined || x.itemId === to.item));
      const open = s && s.step === pending.from.step && s.rows.length > 0 && s.rows.every((r) => empty(valueOf(form, r.field, r.itemId, cur)));
      return open ? go(after, 1, true) : go({ review: true });
    }
    go(after);
  }, [pending, form, cur, models]); // eslint-disable-line react-hooks/exhaustive-deps

  if (problem === "signed_out") return <Navigate to="/signin" replace />;
  if (problem) return <p role="alert" className="p-8">{problem}</p>;
  if (!app || !form || !cur) return <p className="p-8">Loading…</p>;
  if (stepId && !current && !isReview) return <Navigate to={base} replace />;
  if (!stepId && wide) {
    const first = models.find((m) => statusOf(m, cur, visited).status !== "done") ?? models[0];
    return <Navigate to={first ? `${base}/${first.id}` : `${base}/review`} replace />;
  }

  const moveOn = (s: Screen) => setPending({ from: place(s) });
  const back = (() => {
    if (isReview) {
      const last = models.length ? screensOf(form, cur, models[models.length - 1]).at(-1) : undefined;
      return last ? () => go(place(last), -1, false) : undefined;
    }
    const before = screen && screenBefore(form, cur, models, place(screen));
    return before ? () => { commitFocused(); go(before, -1); } : undefined;
  })();

  async function onContinue() {
    if (!screen) return;
    await flush();
    await Promise.resolve();
    if (screen.rows.some((r) => errorsRef.current[rowKey(r)])) return; // a refused answer stays on screen
    moveOn(screen);
  }
  function onPick(r: Row, v: unknown) {
    if (busy.current || !screen) return;
    busy.current = true;
    void setAnswer(r.field.id, r.itemId, v);
    const s = screen;
    // Long enough to see the tile chosen; then the next question slides in.
    setTimeout(() => { busy.current = false; moveOn(s); }, 200);
  }
  function onConfirm(r: Row) {
    if (!screen) return;
    // The map's value stands: an earlier correction is taken back, and nothing new is written.
    if (cur!.answers.some((x) => x.field_id === r.field.id && x.item_id === r.itemId)) void setAnswer(r.field.id, r.itemId, null);
    moveOn(screen);
  }
  function onUnknown() {
    if (!screen) return;
    for (const r of screen.rows) void setAnswer(r.field.id, r.itemId, { unknown: true });
    moveOn(screen);
  }
  async function onLoop(yes: boolean) {
    if (busy.current || !screen || !current?.hub) return;
    if (!yes) {
      markVisited(current.id);
      return moveOn(screen);
    }
    busy.current = true;
    const newId = await addItem(current.hub.kind);
    busy.current = false;
    if (newId) setPending({ step: current.id, item: newId });
  }

  // The trail: this group's answers before the current screen, in the words review prints.
  const chips: Chip[] = group.slice(0, Math.max(at, 0)).filter((s) => s.rows.length > 0).flatMap((s) => {
    const words = s.rows.map((r) => {
      const v = valueOf(form, r.field, r.itemId, cur);
      if (empty(v)) return null;
      if (r.field.control === "building-picker" && typeof v === "string") return buildingLabel(form, cur, v);
      return display(r.field, v, {});
    }).filter((x): x is string => !!x);
    if (!words.length) return [];
    const carried = s.rows.some((r) => app.answers.some((x) => x.field_id === r.field.id && x.item_id === r.itemId && x.carried));
    return [{ id: `${s.itemId ?? ""}|${s.id}`, text: words.join(", "), carried }];
  });
  const goChip = (key: string) => {
    const s = group.find((x) => `${x.itemId ?? ""}|${x.id}` === key);
    if (s) go(place(s), -1);
  };

  const needsContinue = screen && (!screen.auto && (screen.kind !== "confirm" || editing));
  const blank = screen && screen.rows.every((r) => r.field.type === "upload"
    ? !app.attachments.some((x) => x.field_id === r.field.id && x.item_id === r.itemId)
    : empty(valueOf(form, r.field, r.itemId, cur)));
  const dots = screen && group.length > 0 ? <Dots count={group.length} index={at} /> : undefined;

  return (
    <AppShell
      steps={shellSteps}
      currentId={isReview ? REVIEW_STEP.id : current?.id ?? null}
      formTitle={form.official_title}
      saveState={saveState}
      rootHref={base}
      onDone={() => void flush().then((ok) => ok && navigate("/my-applications"))}
      onReload={() => void reload()}
      onStep={(sid) => navigate(shellSteps.find((s) => s.id === sid)?.href ?? base)}
      trail={!isReview && screen ? <AnswerTrail chips={chips} onGo={goChip} /> : undefined}
      paneKey={isReview ? "review" : paneKey}
      direction={direction}
      announce={screen && !isReview ? `Question ${at + 1} of ${group.length}: ${heading}` : undefined}
      phoneBack={back}
      actions={isReview ? { back } : screen ? {
        back,
        dots,
        onContinue: needsContinue ? () => void onContinue() : undefined,
        continueLabel: screen.optional && blank ? "Skip for now" : "Continue",
      } : {}}
    >
      {isReview && <ReviewPane models={models} base={base} />}
      {!isReview && screen && (
        <WizardPane screen={screen} editing={editing} errorsRef={errorsRef} onPick={onPick} onConfirm={onConfirm}
                    onCorrect={() => setEditing(true)} onLoop={(y) => void onLoop(y)} onUnknown={onUnknown} />
      )}
    </AppShell>
  );
}
