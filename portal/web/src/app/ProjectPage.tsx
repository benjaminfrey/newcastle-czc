import { useEffect, useMemo, useRef, useState } from "react";
import { Navigate, useNavigate, useParams, useSearchParams } from "react-router";
import { missing, valueOf, type Row } from "../forms/applicability";
import type { Screen } from "../forms/screens";
import { stepModels } from "../forms/steps";
import { cardsOf, progressOf, taskStatus } from "../forms/tasks";
import AppShell, { rememberProject } from "../shell/AppShell";
import Card from "../shell/Card";
import { commitFocused } from "../shell/commitFocused";
import { ProjectProvider, useProject } from "./ProjectStore";
import CheckPane from "./CheckPane";
import Dashboard from "./Dashboard";
import ItemsPane, { itemTitle } from "./ItemsPane";
import SendPane from "./SendPane";
import { todoRows } from "./todo";
import CardQuestion, { headingOf, rowKey } from "./WizardPane";

// /projects/:id                          the dashboard
// /projects/:id/:part?screen=&item=       a card (a building's, with item)
// /projects/:id/:part                     a part's first card, or its buildings
// /projects/:id/:part/check?item=         a part's (or one building's) check page
// /projects/:id/send                      Check and send
// (projects brief §3.4; the cards are the task-list brief's)
export default function ProjectPage() {
  const { id = "" } = useParams();
  useEffect(() => rememberProject(id), [id]);
  return <ProjectProvider id={id}><Tasks id={id} /></ProjectProvider>;
}
const SEND = "send";

const empty = (v: unknown) => v === null || v === undefined || v === "" || (Array.isArray(v) && v.length === 0);
const keyOf = (s: Screen) => `${s.itemId ?? ""}|${s.id}`;
type Pending = { from: Screen } | { added: string; step: string; check: boolean };

function Tasks({ id }: { id: string }) {
  const { stepId, sub } = useParams();
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const store = useProject();
  const { project: app, form, cur, problem, saveState, flush, markVisited, visited, reload, setAnswer, addPart: addItem, removePart: removeItem, setTitle, locked, submit } = store;
  const base = `/projects/${id}`;
  const [direction, setDirection] = useState<1 | -1>(1);
  const [editing, setEditing] = useState(false);
  const [pending, setPending] = useState<Pending | null>(null);
  const [unknownFor, setUnknownFor] = useState<Screen | null>(null); // "I don't know…": mark the blanks, then move on
  const busy = useRef(false);
  const errorsRef = useRef<Record<string, string>>({});

  const models = useMemo(() => (form && cur ? stepModels(form, cur) : []), [form, cur]);
  const current = models.find((m) => m.id === stepId);
  const hub = current?.hub;
  const itemParam = params.get("item");
  const isCheck = sub === "check";
  const returning = params.get("return"); // "review" or "check": where Continue goes back to
  const cards = useMemo(() => (form && cur && current && (!hub || itemParam) ? cardsOf(form, cur, current, itemParam ?? undefined) : []),
    [form, cur, current, hub, itemParam]);

  const sp = params.get("screen");
  const focus = params.get("focus");
  const showItems = !!hub && !itemParam && !isCheck;
  const screen: Screen | undefined = isCheck || showItems ? undefined
    : (sp && cards.find((s) => s.id === sp)) || (focus && cards.find((s) => s.rows.some((r) => r.field.id === focus))) || cards[0];
  const at = screen ? cards.indexOf(screen) : -1;
  const paneKey = screen ? `${screen.step}:${screen.itemId ?? ""}:${screen.id}` : `${stepId ?? "home"}:${sub ?? ""}:${itemParam ?? ""}`;
  const paneRef = useRef(paneKey);
  paneRef.current = paneKey;
  // The task's cards as they stood when this one opened: a Change asks only the cards an answer adds.
  const asked = useRef<Set<string>>(new Set());
  const [hadAnswer, setHadAnswer] = useState<string | null>(null); // the card that was answered when it opened
  const [hintFirst] = useState(() => hintUnseen(id));
  const [hintCard, setHintCard] = useState<string | null>(null);

  const href = (s: Screen, ret: string | null = returning) => {
    const q = new URLSearchParams({ screen: s.id, ...(s.itemId ? { item: s.itemId } : {}), ...(ret ? { return: ret } : {}) });
    return `${base}/${s.step}?${q.toString()}`;
  };
  const checkHref = (step: string, item?: string | null) => `${base}/${step}/check${item ? `?item=${item}` : ""}`;
  const go = (to: string, dir: 1 | -1 = 1) => {
    commitFocused(); // a typed answer saves first, even where a tap doesn't leave the field (iOS)
    setDirection(dir);
    navigate(to);
  };

  // A task counts as visited once it is opened, however the person got there.
  const currentId = current?.id;
  useEffect(() => { if (currentId) markVisited(currentId); }, [currentId, markVisited]);
  useEffect(() => {
    setEditing(false);
    errorsRef.current = {};
    asked.current = new Set(cards.map(keyOf));
    setHadAnswer(screen && form && cur && screen.rows.length > 0 && screen.rows.every((r) => {
      const v = valueOf(form, r.field, r.itemId, cur);
      return !empty(v) && v !== r.field.default; // the form's default (saved at the start) isn't the applicant's
    }) ? paneKey : null);
  }, [paneKey]); // eslint-disable-line react-hooks/exhaustive-deps

  const heading = screen ? headingOf(screen) : current?.title;
  useEffect(() => {
    if (!form) return;
    document.title = `${heading ?? app?.title ?? "Your project"} — Newcastle permits`;
    document.querySelector<HTMLElement>("[data-screen-title]")?.focus();
  }, [heading, form, paneKey]);

  useEffect(() => {
    if (!unknownFor || !form || !cur) return;
    setUnknownFor(null);
    // Only the values left blank that may be unknown.
    for (const r of unknownFor.rows) {
      if (r.field.allow_unknown && empty(valueOf(form, r.field, r.itemId, cur))) void setAnswer(r.field.id, r.itemId, { unknown: true });
    }
    setPending({ from: unknownFor });
  }, [unknownFor, form, cur]); // eslint-disable-line react-hooks/exhaustive-deps

  // Moving on is worked out after the answer has landed, so cards an answer adds or removes (the
  // owner's) are counted, and a new building's first card exists.
  useEffect(() => {
    if (!pending || !form || !cur) return;
    if ("added" in pending) {
      const m = models.find((x) => x.id === pending.step);
      const first = m && cardsOf(form, cur, m, pending.added)[0];
      if (!first) return; // the new item hasn't arrived yet
      setPending(null);
      return go(pending.check ? checkHref(pending.step, pending.added) : href(first, null));
    }
    setPending(null);
    const from = pending.from;
    const m = models.find((x) => x.id === from.step);
    const list = m ? cardsOf(form, cur, m, from.itemId ?? undefined) : [];
    const i = list.findIndex((x) => x.id === from.id);
    if (returning) {
      // Back to where the Change came from, unless the answer opened new cards in this task (the
      // owner's details after "No, I don't own it"). Cards skipped before stay where they are.
      const open = list.slice(i + 1).find((x) => !asked.current.has(keyOf(x)) && x.rows.length > 0
        && x.rows.every((r) => empty(valueOf(form, r.field, r.itemId, cur))));
      if (open) return go(href(open));
      return go(returning === "review" ? `${base}/${SEND}` : checkHref(from.step, from.itemId));
    }
    if (i >= 0 && i < list.length - 1) return go(href(list[i + 1]));
    go(checkHref(from.step, from.itemId));
  }, [pending, form, cur, models]); // eslint-disable-line react-hooks/exhaustive-deps

  if (problem === "signed_out") return <Navigate to="/" replace />;
  if (problem) return <p role="alert" className="p-8">{problem}</p>;
  if (!app || !form || !cur) return <p className="p-8">Loading…</p>;
  if (stepId && stepId !== SEND && !current) return <Navigate to={base} replace />;

  const statuses = models.map((m) => taskStatus(form, cur, m, visited));
  // "2 things left": the rows (a part, About you, Your lot) with something required still blank.
  const stepOfRow = new Map(models.flatMap((m) => m.rows.map((r) => [`${r.field.id}|${r.itemId ?? ""}`, m.id] as const)));
  const left = new Set(missing(form, cur).map(([f, i]) => stepOfRow.get(`${f}|${i ?? ""}`)).filter(Boolean)).size;
  const shell = (inCard: boolean, children: React.ReactNode, titled = false) => (
    <AppShell title={app.title} project={id} saveState={saveState} onReload={() => void reload()}
              back={inCard ? { href: base, label: "Project" } : undefined} card={inCard} titled={titled}>
      {children}
    </AppShell>
  );
  if (!stepId) {
    return shell(false, (
      <Dashboard project={app} form={form} cur={cur} models={models} statuses={statuses} base={base} left={left} locked={locked}
                 onAdd={(kind) => void addItem(kind).then((made) => made && setPending({ added: made, step: kind, check: false }))}
                 onRemove={(part) => void removeItem(part)} onRename={setTitle} next={todoRows(form, cur, models, base)[0]} />
    ), true);
  }
  if (stepId === SEND) {
    if (locked) return <Navigate to={base} replace />;
    return shell(true, (
      <SendPane project={app} form={form} cur={cur} models={models} base={base} onBack={() => go(base, -1)}
                onSend={submit} onSent={() => go(base)} />
    ), true);
  }
  const step = current!;

  // The buildings (or additions) list.
  if (showItems) {
    return shell(true, (
      <ItemsPane form={form} cur={cur} step={step}
                 onOpen={(item, finish) => {
                   if (!finish) return go(checkHref(step.id, item));
                   const list = cardsOf(form, cur, step, item);
                   const todo = list.find((s) => s.rows.some((r) => r.field.required && empty(valueOf(form, r.field, r.itemId, cur)))) ?? list[0];
                   go(href(todo, null));
                 }}
                 onAdd={() => void addItem(step.hub!.kind).then((made) => made && setPending({ added: made, step: step.id, check: false }))}
                 onCopy={(src) => void addItem(step.hub!.kind, src).then((made) => made && setPending({ added: made, step: step.id, check: true }))}
                 onDelete={(item) => void removeItem(item)}
                 onDone={() => { markVisited(step.id); go(base); }} />
    ));
  }

  // A task's (or a building's) check page.
  if (isCheck) {
    const title = itemParam ? itemTitle(form, cur, itemParam).title.split(" · ")[0] : step.title;
    const done = () => { markVisited(step.id); go(itemParam ? `${base}/${step.id}` : base); };
    const last = cards[cards.length - 1];
    return shell(true, (
      <CheckPane title={title} cards={cards} changeHref={(s) => href(s, "check")}
                 onBack={() => (last ? go(href(last, null), -1) : go(base, -1))} onDone={done} />
    ));
  }

  if (!screen) return <Navigate to={hub ? `${base}/${step.id}` : base} replace />;
  const moveOn = (s: Screen) => setPending({ from: s });
  const back = at > 0
    ? { label: "Back", onPress: () => go(href(cards[at - 1]), -1) }
    : screen.itemId ? { label: "Back", onPress: () => go(`${base}/${step.id}`, -1) }
    : { label: "Back", onPress: () => go(base, -1) };

  async function onContinue() {
    if (!screen) return;
    commitFocused();
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
    const from = paneKey;
    // Long enough to see the tile chosen; then the next card slides in, unless the applicant has
    // gone elsewhere in the meantime.
    setTimeout(() => { busy.current = false; if (paneRef.current === from) moveOn(s); }, 200);
  }
  function onConfirm(r: Row, keep: boolean) {
    if (!screen) return;
    // "Yes" keeps what is shown (the map's value, or the applicant's correction); "Use the map's"
    // takes a correction back. Nothing new is written.
    if (!keep && cur!.answers.some((x) => x.field_id === r.field.id && x.item_id === r.itemId)) void setAnswer(r.field.id, r.itemId, null);
    moveOn(screen);
  }
  async function onUnknown() {
    if (!screen) return;
    // A value typed but not yet left saves first; which values are blank is decided once it has
    // landed (the effect above), so what was typed stays.
    commitFocused();
    await flush();
    setUnknownFor(screen);
  }

  // The bar: the cards that apply now (they change only when an answer adds or removes one).
  const progress = progressOf(cards, screen, 0);
  const title = screen.itemId ? itemTitle(form, cur, screen.itemId).title : step.title;

  // Continue for what is typed; a tap card has none, unless it was answered before (coming back to
  // it) or a road is being typed in; "Is this right?" has it while correcting.
  const needsContinue = editing || (screen.kind === "confirm" ? false : !screen.auto || hadAnswer === paneKey);
  const blank = screen.rows.every((r) => r.field.type === "upload"
    ? !app.attachments.some((x) => x.field_id === r.field.id && x.item_id === r.itemId)
    : empty(valueOf(form, r.field, r.itemId, cur)));
  const hint = !needsContinue && hintFirst && (hintCard === null || hintCard === paneKey);
  if (hint && hintCard === null) {
    setHintCard(paneKey);
    markHintSeen(id);
  }
  const wide = screen.kind === "setbacks" || screen.kind === "walls";

  return shell(true, (
    <Card wide={wide} onSubmit={() => void onContinue()}>
      <Card.Header title={title} count={progress.count} at={progress.at} />
      <Card.Body motionKey={paneKey} direction={direction}>
        {locked && (
          <p className="mb-3 max-w-[46ch] text-[13px] text-[var(--app-secondary-label)]">
            The Town is reviewing this project; changes go through the Code Enforcement Officer.</p>
        )}
        {/* Locked: the controls show the answers, and take no changes. */}
        <fieldset disabled={locked} className="contents">
          <CardQuestion screen={screen} editing={editing} errorsRef={errorsRef} onPick={onPick} onConfirm={onConfirm}
                        onCorrect={() => setEditing(true)} onUnknown={() => void onUnknown()} />
        </fieldset>
      </Card.Body>
      <Card.Footer back={back}
                   next={needsContinue ? { label: screen.optional && blank ? "Skip for now" : "Continue", plain: screen.optional && blank, onPress: () => void onContinue() }
                     : hint ? { hint: "A tap moves on" } : null} />
      <p className="sr-only" aria-live="polite">Question {progress.at + 1} of {progress.count}: {heading}</p>
    </Card>
  ));
}

// "A tap moves on" is said on the first tap card of an application only: decided once per visit,
// and remembered in browser storage (read in a try, as storage can be blocked).
function hintUnseen(appId: string): boolean {
  try { return localStorage.getItem(`portal.taphint.${appId}`) !== "1"; } catch { return true; }
}
function markHintSeen(appId: string): void {
  try { localStorage.setItem(`portal.taphint.${appId}`, "1"); } catch { /* fine */ }
}
