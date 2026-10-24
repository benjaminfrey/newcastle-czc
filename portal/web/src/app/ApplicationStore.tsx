// One open application: its pinned form, its answers, and every save, in order.
//
// Answers save as they are given. Each change shows at once (cur), then goes to the API in a
// single queue, so saves never overtake each other and each carries the revision the last
// one returned. A save from a tab that fell behind (409) stops the queue: the shell offers
// "Load the latest", and nothing more is sent until then. A failed save keeps the value and
// is sent again with the next change. Continue waits on flush() so nothing is lost on the way.
import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import { getMe, UNREACHABLE } from "../api";
import {
  addItem as apiAddItem, getApplication, getForm, removeItem as apiRemoveItem, saveAnswers, saveNote as apiSaveNote,
  type AppState, type Change, type FormDef,
} from "../applications";
import type { Current } from "../forms/applicability";
import type { SaveState } from "../shell/types";

export type SetOutcome = { ok: true } | { error: string };

type Store = {
  app: AppState | null; form: FormDef | null; cur: Current | null; problem: string | null;
  saveState: SaveState;
  setAnswer: (fieldId: string, itemId: string | null, value: unknown) => Promise<SetOutcome>;
  flush: () => Promise<void>;
  addItem: (kind: string, preset?: number) => Promise<string | null>;
  removeItem: (itemId: string) => Promise<boolean>;
  saveNote: (sectionId: string, itemId: string | null, text: string) => Promise<boolean>;
  reload: () => Promise<void>;
  visited: Set<string>;
  markVisited: (stepId: string) => void;
};

const Context = createContext<Store | null>(null);

export function useApplication(): Store {
  const s = useContext(Context);
  if (!s) throw new Error("useApplication outside ApplicationProvider");
  return s;
}

function readVisited(id: string): Set<string> {
  try {
    return new Set(JSON.parse(localStorage.getItem(`portal.visited.${id}`) ?? "[]") as string[]);
  } catch {
    return new Set();
  }
}

function withChange(answers: AppState["answers"], c: Change): AppState["answers"] {
  const rest = answers.filter((a) => !(a.field_id === c.field_id && a.item_id === c.item_id));
  return c.value === null ? rest : [...rest, { field_id: c.field_id, item_id: c.item_id, value: c.value }];
}

export function ApplicationProvider({ id, children }: { id: string; children: ReactNode }) {
  const [app, setApp] = useState<AppState | null>(null);
  const [form, setForm] = useState<FormDef | null>(null);
  const [email, setEmail] = useState<string | null>(null);
  const [problem, setProblem] = useState<string | null>(null);
  const [saveState, setSaveState] = useState<SaveState>("idle");
  const [visited, setVisited] = useState<Set<string>>(() => readVisited(id));
  const chain = useRef<Promise<unknown>>(Promise.resolve());
  const revision = useRef(0);
  const stopped = useRef(false); // after a conflict
  const failed = useRef<Change[]>([]);
  const lastGood = useRef<AppState["answers"]>([]);

  const load = useCallback(async () => {
    const a = await getApplication(id);
    if (a === "signed_out") return setProblem("signed_out");
    if (a === "not_found") return setProblem("We couldn't find that application.");
    if (typeof a === "string") return setProblem(a === "busy" ? "The Town's server is busy. Please wait a minute." : UNREACHABLE);
    const f = await getForm(a.form_key, a.form_version);
    if (f === "not_approved") return setProblem("This application isn't ready yet. Please contact the Town Office.");
    if (typeof f === "string") return setProblem(UNREACHABLE);
    revision.current = a.revision;
    lastGood.current = a.answers;
    stopped.current = false;
    failed.current = [];
    setApp(a);
    setForm(f);
    setSaveState("idle");
  }, [id]);

  useEffect(() => {
    void load();
    getMe().then((m) => m && m !== "unavailable" && setEmail(m.email));
  }, [load]);

  const enqueue = useCallback(<T,>(job: () => Promise<T>): Promise<T> => {
    const next = chain.current.then(job, job);
    chain.current = next.catch(() => undefined);
    return next;
  }, []);

  const setAnswer = useCallback((fieldId: string, itemId: string | null, value: unknown): Promise<SetOutcome> => {
    const change: Change = { field_id: fieldId, item_id: itemId, value };
    setApp((a) => (a ? { ...a, answers: withChange(a.answers, change) } : a));
    if (stopped.current) return Promise.resolve({ ok: true });
    setSaveState("saving");
    return enqueue(async (): Promise<SetOutcome> => {
      if (stopped.current) return { ok: true };
      const changes = [...failed.current.filter((c) => !(c.field_id === fieldId && c.item_id === itemId)), change];
      const r = await saveAnswers(id, revision.current, changes);
      if (r === "signed_out") {
        setProblem("signed_out");
        return { ok: true };
      }
      if (typeof r === "string") {
        failed.current = changes;
        setSaveState("error");
        return { ok: true };
      }
      if ("conflict" in r) {
        stopped.current = true;
        setSaveState("conflict");
        return { ok: true };
      }
      if ("invalid" in r) {
        // Put back what the server holds for this field; tell the control why.
        setApp((a) => (a ? { ...a, answers: withChange(a.answers, {
          field_id: fieldId, item_id: itemId,
          value: lastGood.current.find((x) => x.field_id === fieldId && x.item_id === itemId)?.value ?? null,
        }) } : a));
        setSaveState("idle");
        return { error: r.invalid[0]?.reason ?? "wrong_type" };
      }
      failed.current = [];
      revision.current = r.revision;
      for (const c of changes) lastGood.current = withChange(lastGood.current, c);
      setApp((a) => (a ? { ...a, revision: r.revision, missing: r.missing } : a));
      setSaveState("saved");
      return { ok: true };
    });
  }, [enqueue, id]);

  const flush = useCallback(() => chain.current.then(() => undefined), []);

  const addItem = useCallback((kind: string, preset?: number) => enqueue(async () => {
    if (stopped.current) return null;
    const r = await apiAddItem(id, revision.current, kind, preset);
    if (typeof r === "object" && "conflict" in r) {
      stopped.current = true;
      setSaveState("conflict");
      return null;
    }
    if (typeof r === "string" || !("revision" in r)) return null;
    await load(); // the new item arrives with its defaults and preset answers
    return (r as { id?: string }).id ?? null;
  }), [enqueue, id, load]);

  const removeItem = useCallback((itemId: string) => enqueue(async () => {
    if (stopped.current) return false;
    const r = await apiRemoveItem(id, revision.current, itemId);
    if (typeof r === "object" && "conflict" in r) {
      stopped.current = true;
      setSaveState("conflict");
      return false;
    }
    if (typeof r === "string" || !("revision" in r)) return false;
    await load();
    return true;
  }), [enqueue, id, load]);

  const saveNote = useCallback((sectionId: string, itemId: string | null, text: string) => enqueue(async () => {
    if (stopped.current) return false;
    setSaveState("saving");
    const r = await apiSaveNote(id, revision.current, sectionId, itemId, text);
    if (typeof r === "object" && "conflict" in r) {
      stopped.current = true;
      setSaveState("conflict");
      return false;
    }
    if (typeof r === "string" || !("revision" in r)) {
      setSaveState("error");
      return false;
    }
    revision.current = r.revision;
    setApp((a) => {
      if (!a) return a;
      const notes = a.notes.filter((n) => !(n.section_id === sectionId && n.item_id === itemId));
      return { ...a, revision: r.revision, notes: text.trim() ? [...notes, { section_id: sectionId, item_id: itemId, text: text.trim() }] : notes };
    });
    setSaveState("saved");
    return true;
  }), [enqueue, id]);

  const markVisited = useCallback((stepId: string) => {
    setVisited((v) => {
      if (v.has(stepId)) return v;
      const next = new Set(v).add(stepId);
      try {
        localStorage.setItem(`portal.visited.${id}`, JSON.stringify([...next]));
      } catch {
        // Blocked storage: steps are marked for this visit only.
      }
      return next;
    });
  }, [id]);

  const cur: Current | null = useMemo(
    () => (app ? { answers: app.answers, items: app.items, property: app.property.facts, account: { email } } : null),
    [app, email]);

  const value: Store = {
    app, form, cur, problem, saveState, setAnswer, flush, addItem, removeItem, saveNote,
    reload: load, visited, markVisited,
  };
  return <Context.Provider value={value}>{children}</Context.Provider>;
}
