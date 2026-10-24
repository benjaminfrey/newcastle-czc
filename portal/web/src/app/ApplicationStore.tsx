// One open application: its pinned form, its answers, and every save, in order.
//
// Answers save as they are given. Each change shows at once (cur), then goes to the API in a
// single queue, so saves never overtake each other and each carries the revision the last
// one returned. A save from a tab that fell behind (409) stops the queue: the shell offers
// "Load the latest", and nothing more is sent until then. A failed save keeps the value and
// is sent again: after a pause, with the next change, and by flush(). Continue waits on flush(),
// which says whether everything reached the server; Save and close stays put until it has.
// A refused answer (422) is put back and told to its own field; the rest still go.
import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import { getMe, UNREACHABLE } from "../api";
import {
  addItem as apiAddItem, getApplication, getForm, removeItem as apiRemoveItem, saveAnswers, saveNote as apiSaveNote,
  type AppState, type Attachment, type Change, type FormDef,
} from "../applications";
import type { Current } from "../forms/applicability";
import type { SaveState } from "../shell/types";

const RETRY_MS = 5000;

export type SetOutcome = { ok: true } | { error: string };

type Store = {
  app: AppState | null; form: FormDef | null; cur: Current | null; problem: string | null;
  saveState: SaveState;
  setAnswer: (fieldId: string, itemId: string | null, value: unknown) => Promise<SetOutcome>;
  flush: () => Promise<boolean>; // true when every change has reached the server
  addItem: (kind: string, preset?: number) => Promise<string | null>;
  removeItem: (itemId: string) => Promise<boolean>;
  saveNote: (sectionId: string, itemId: string | null, text: string) => Promise<boolean>;
  reload: () => Promise<void>;
  // A file the Town kept, or took away: review and the step both list app.attachments.
  attachmentAdded: (a: Attachment) => void;
  attachmentRemoved: (attachmentId: string) => void;
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
    // Changes that haven't reached the server yet stay shown, and go with the next save.
    const pending = failed.current;
    setApp({ ...a, answers: pending.reduce(withChange, a.answers) });
    setForm(f);
    setSaveState(pending.length ? "error" : "idle");
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

  const retry = useRef<ReturnType<typeof setTimeout> | null>(null);
  useEffect(() => () => { if (retry.current) clearTimeout(retry.current); }, []);

  // Send a batch of changes and settle what each outcome means. `mine` is the field whose change
  // started the batch, so a refusal of that field comes back to it as a message.
  const send = useRef<(changes: Change[], mine?: { fieldId: string; itemId: string | null }) => Promise<SetOutcome>>(null!);
  const resend = useCallback(() => enqueue(async () => {
    if (stopped.current || failed.current.length === 0) return;
    await send.current(failed.current);
  }), [enqueue]);
  send.current = async (changes, mine) => {
    const r = await saveAnswers(id, revision.current, changes);
    if (r === "signed_out") {
      setProblem("signed_out");
      return { ok: true };
    }
    if (typeof r === "string") {
      failed.current = changes;
      setSaveState("error");
      if (retry.current) clearTimeout(retry.current);
      retry.current = setTimeout(() => void resend(), RETRY_MS);
      return { ok: true };
    }
    if ("conflict" in r) {
      stopped.current = true;
      setSaveState("conflict");
      return { ok: true };
    }
    if ("invalid" in r) {
      const same = (a: { field_id: string; item_id: string | null }, b: { field_id: string; item_id: string | null }) =>
        a.field_id === b.field_id && a.item_id === b.item_id;
      // The server names each refused answer; if it names none we know, refuse the whole batch.
      const named = r.invalid.filter((p) => changes.some((c) => same(c, p)));
      const refused = named.length ? named : changes.map((c) => ({ ...c, reason: r.invalid[0]?.reason ?? "wrong_type" }));
      const back = changes.filter((c) => refused.some((p) => same(c, p)));
      setApp((a) => (a ? { ...a, answers: back.reduce((acc, c) => withChange(acc, {
        ...c, value: lastGood.current.find((x) => same(x, c))?.value ?? null,
      }), a.answers) } : a));
      failed.current = [];
      const rest = changes.filter((c) => !refused.some((p) => same(c, p)));
      if (rest.length) await send.current(rest);
      else setSaveState("idle");
      const own = mine && refused.find((p) => p.field_id === mine.fieldId && p.item_id === mine.itemId);
      return own ? { error: own.reason } : { ok: true };
    }
    failed.current = [];
    if (retry.current) clearTimeout(retry.current);
    revision.current = r.revision;
    for (const c of changes) lastGood.current = withChange(lastGood.current, c);
    setApp((a) => (a ? { ...a, revision: r.revision, missing: r.missing } : a));
    setSaveState("saved");
    return { ok: true };
  };

  const setAnswer = useCallback((fieldId: string, itemId: string | null, value: unknown): Promise<SetOutcome> => {
    const change: Change = { field_id: fieldId, item_id: itemId, value };
    setApp((a) => (a ? { ...a, answers: withChange(a.answers, change) } : a));
    if (stopped.current) return Promise.resolve({ ok: true });
    setSaveState("saving");
    return enqueue(async (): Promise<SetOutcome> => {
      if (stopped.current) return { ok: true };
      const changes = [...failed.current.filter((c) => !(c.field_id === fieldId && c.item_id === itemId)), change];
      return send.current(changes, { fieldId, itemId });
    });
  }, [enqueue]);

  const flush = useCallback(async () => {
    await chain.current;
    if (failed.current.length && !stopped.current) await resend();
    return !stopped.current && failed.current.length === 0;
  }, [resend]);

  // Closing the page with answers still unsent: the browser asks first.
  useEffect(() => {
    const warn = (e: BeforeUnloadEvent) => { if (failed.current.length) e.preventDefault(); };
    window.addEventListener("beforeunload", warn);
    return () => window.removeEventListener("beforeunload", warn);
  }, []);

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

  const attachmentAdded = useCallback((x: Attachment) => {
    setApp((a) => (a ? { ...a, attachments: [...a.attachments, x] } : a));
  }, []);
  const attachmentRemoved = useCallback((attachmentId: string) => {
    setApp((a) => (a ? { ...a, attachments: a.attachments.filter((x) => x.id !== attachmentId) } : a));
  }, []);

  const cur: Current | null = useMemo(
    () => (app ? { answers: app.answers, items: app.items, property: app.property.facts, account: { email } } : null),
    [app, email]);

  const value: Store = {
    app, form, cur, problem, saveState, setAnswer, flush, addItem, removeItem, saveNote,
    reload: load, attachmentAdded, attachmentRemoved, visited, markVisited,
  };
  return <Context.Provider value={value}>{children}</Context.Provider>;
}
