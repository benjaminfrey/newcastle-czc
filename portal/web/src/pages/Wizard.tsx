import { Button, Card } from "@heroui/react";
import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate, useParams, useSearchParams } from "react-router";
import { getUseGroups, UNREACHABLE } from "../api";
import {
  addItem, getApplication, getForm, saveAnswers, type AppState, type Change, type FormDef, type SaveResult,
} from "../applications";
import QuestionField, { fromDraft, isUnknown, toDraft, type Draft } from "../components/QuestionField";
import WhyWeAsk from "../components/WhyWeAsk";
import { answerOf, type Current } from "../forms/applicability";
import { screens, type Screen } from "../forms/wizard";

const REASONS: Record<string, string> = {
  out_of_range: "That number is outside the range this question takes.",
  wrong_type: "That answer isn't in the form this question needs.",
  not_an_option: "Please choose one of the options.",
  too_long: "That's longer than this space allows. Please shorten it, or use \"Add more detail\" on the review page.",
  unknown_not_allowed: "Please give an answer to this one.",
};

export function currentOf(app: AppState): Current {
  return { answers: app.answers, items: app.items, property: app.property.facts, account: {} };
}

// Put a saved change into the local copy, so the screens recompute without a reload.
function applyChange(app: AppState, c: Change, revision: number, missing: AppState["missing"]): AppState {
  const answers = app.answers.filter((a) => !(a.field_id === c.field_id && a.item_id === c.item_id));
  if (c.value !== null) answers.push({ field_id: c.field_id, item_id: c.item_id, value: c.value });
  return { ...app, answers, revision, missing };
}

export default function Wizard() {
  const { id = "" } = useParams();
  const navigate = useNavigate();
  const [params, setParams] = useSearchParams();
  const [app, setApp] = useState<AppState | null>(null);
  const [form, setForm] = useState<FormDef | null>(null);
  const [problem, setProblem] = useState<string | null>(null);
  const [draft, setDraft] = useState<Draft>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [conflict, setConflict] = useState<{ revision: number; change: Change } | null>(null);
  const [busy, setBusy] = useState(false);
  const [useNames, setUseNames] = useState<Record<string, string>>({});

  async function load() {
    const a = await getApplication(id);
    if (a === "signed_out") return navigate("/signin", { replace: true });
    if (a === "not_found") return setProblem("We couldn't find that application.");
    if (typeof a === "string") return setProblem(UNREACHABLE);
    const f = await getForm(a.form_key, a.form_version);
    if (f === "not_approved") return setProblem("This application isn't ready yet. Please contact the Town Office.");
    if (typeof f === "string") return setProblem(UNREACHABLE);
    setApp(a);
    setForm(f);
  }

  useEffect(() => {
    void load();
    getUseGroups().then((g) => {
      if (Array.isArray(g)) setUseNames(Object.fromEntries(g.flatMap((x) => x.uses).map((u) => [u.use_key, u.code_name])));
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  const only = params.get("only")?.split(",").filter(Boolean) ?? null;
  const list: Screen[] = useMemo(() => {
    if (!app || !form) return [];
    const all = screens(form, currentOf(app));
    return only ? all.filter((s) => only.includes(s.key)) : all;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [app, form, params]);
  const index = Math.max(0, list.findIndex((s) => s.key === params.get("s")));
  const here = list[index] as Screen | undefined;

  // Show the saved answer when arriving at a question.
  useEffect(() => {
    if (app && here?.kind === "question") setDraft(toDraft(here.field, answerOf(currentOf(app), here.field.id, here.itemId)));
    setMessage(null);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [here?.key, app?.revision]);

  function go(to: number, after: Screen[] = list) {
    if (to >= after.length) return navigate(`/applications/${id}/review`);
    const next = new URLSearchParams(params);
    next.set("s", after[Math.max(0, to)].key);
    setParams(next);
  }

  function afterSave(r: SaveResult, change: Change): boolean {
    if (r === "signed_out") {
      navigate("/signin");
      return false;
    }
    if (typeof r === "string") {
      setMessage("We couldn't save that — please try again.");
      return false;
    }
    if ("conflict" in r) {
      setConflict({ revision: r.conflict, change });
      return false;
    }
    if ("invalid" in r) {
      setMessage(REASONS[r.invalid[0]?.reason] ?? "We couldn't use that answer. Please check it.");
      return false;
    }
    const updated = applyChange(app!, change, r.revision, r.missing);
    setApp(updated);
    const after = screens(form!, currentOf(updated)).filter((s) => !only || only.includes(s.key));
    const at = after.findIndex((s) => s.key === here!.key);
    go(at + 1, after);
    return true;
  }

  async function save(value: unknown, baseRevision = app!.revision) {
    if (!here || here.kind !== "question") return;
    const change = { field_id: here.field.id, item_id: here.itemId, value };
    const saved = answerOf(currentOf(app!), here.field.id, here.itemId);
    if (JSON.stringify(saved) === JSON.stringify(value) && baseRevision === app!.revision) return go(index + 1);
    setBusy(true);
    try {
      afterSave(await saveAnswers(id, baseRevision, [change]), change);
    } finally {
      setBusy(false);
    }
  }

  function next() {
    if (!here || here.kind !== "question") return;
    if (here.field.type === "upload") return go(index + 1);
    const out = fromDraft(here.field, draft);
    if ("error" in out) return setMessage(out.error);
    void save(out.value);
  }

  async function keepMine() {
    if (!conflict) return;
    const c = conflict;
    setConflict(null);
    setBusy(true);
    try {
      afterSave(await saveAnswers(id, c.revision, [c.change]), c.change);
    } finally {
      setBusy(false);
    }
  }

  async function loadLatest() {
    setConflict(null);
    await load();
  }

  async function addAnother() {
    if (!here || here.kind !== "add") return;
    setBusy(true);
    try {
      const r = await addItem(id, app!.revision, here.repeat.kind);
      if (typeof r === "string" || !("revision" in r)) {
        if (typeof r === "object" && "conflict" in r) setConflict(null);
        setMessage("We couldn't add that — please try again.");
        return;
      }
      const fresh = await getApplication(id);
      if (typeof fresh === "string") return setMessage(UNREACHABLE);
      setApp(fresh);
      const after = screens(form!, currentOf(fresh));
      const newId = (r as { id?: string }).id;
      const first = after.findIndex((s) => s.kind === "question" && s.itemId === newId);
      go(first >= 0 ? first : index + 1, after);
    } finally {
      setBusy(false);
    }
  }

  if (problem) return <p role="alert">{problem}</p>;
  if (!app || !form) return <p>Loading…</p>;
  if (!here) {
    return (
      <Card>
        <Card.Header><Card.Title>Nothing more to ask</Card.Title></Card.Header>
        <Card.Content><Link className="underline" to={`/applications/${id}/review`}>Review your application</Link></Card.Content>
      </Card>
    );
  }

  const inChapter = list.filter((s) => s.chapter === here.chapter);
  const step = inChapter.findIndex((s) => s.key === here.key) + 1;
  return (
    <div className="flex flex-col gap-4">
      <p className="text-sm">
        {form.official_title}
        {params.get("back") === "review" && (
          <> · <Link className="underline" to={`/applications/${id}/review`}>Back to review</Link></>
        )}
      </p>
      <h1 className="text-xl font-semibold">{here.chapter}</h1>
      <p className="text-sm">Step {step} of {inChapter.length} in this part</p>
      {app.newer_version && (
        <p className="text-sm">The Town has a newer version of this form. Yours stays on the version you started.</p>
      )}
      {conflict && (
        <Card>
          <Card.Header>
            <Card.Title>This application was changed in another tab or window</Card.Title>
            <Card.Description>Load the latest to see those changes, or keep your answer here.</Card.Description>
          </Card.Header>
          <Card.Footer className="flex flex-wrap gap-2">
            <Button variant="primary" onPress={() => void loadLatest()}>Load the latest</Button>
            <Button variant="secondary" onPress={() => void keepMine()}>Keep mine</Button>
          </Card.Footer>
        </Card>
      )}
      {here.kind === "question" ? (
        <Card>
          <Card.Content className="flex flex-col gap-3">
            {here.itemLabel && <p className="font-semibold">{here.itemLabel}</p>}
            <QuestionField
              field={here.field} draft={isUnknown(draft) ? null : draft} onChange={(d) => { setDraft(d); setMessage(null); }}
              appId={id} itemId={here.itemId} parcelId={app.property.parcel_id}
              attachments={app.attachments} onAttachments={(all) => setApp({ ...app, attachments: all })}
              useNames={useNames} onUseName={(k, n) => setUseNames({ ...useNames, [k]: n })}
            />
            {isUnknown(draft) && <p className="text-sm">You said you don't know yet. Staff will follow up.</p>}
            <WhyWeAsk why={here.field.why} />
            {message && <p role="alert">{message}</p>}
          </Card.Content>
          <Card.Footer className="flex flex-wrap gap-2">
            {index > 0 && <Button variant="ghost" onPress={() => go(index - 1)}>Back</Button>}
            <Button variant="primary" onPress={next} isDisabled={busy || !!conflict}>Next</Button>
            {here.field.allow_unknown && (
              <Button variant="secondary" onPress={() => void save({ unknown: true })} isDisabled={busy || !!conflict}>
                I don't know yet
              </Button>
            )}
          </Card.Footer>
        </Card>
      ) : (
        <Card>
          <Card.Header>
            <Card.Title>{here.repeat.add_label}?</Card.Title>
            <Card.Description>
              {here.count === 0 ? "You haven't added any yet." : `You've added ${here.count} so far.`}
            </Card.Description>
          </Card.Header>
          {message && <Card.Content><p role="alert">{message}</p></Card.Content>}
          <Card.Footer className="flex flex-wrap gap-2">
            {index > 0 && <Button variant="ghost" onPress={() => go(index - 1)}>Back</Button>}
            <Button variant="secondary" onPress={() => void addAnother()} isDisabled={busy}>Yes, add one</Button>
            <Button variant="primary" onPress={() => go(index + 1)}>No, go on</Button>
          </Card.Footer>
        </Card>
      )}
    </div>
  );
}
