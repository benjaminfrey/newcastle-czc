// One open project: its form (the cover sheet, its parts' questions; built by the API from the
// forms it has pinned), its answers, what it needs, and every save, in order.
//
// Answers save as they are given. Each change shows at once (cur), then goes to the API in a
// single queue, so saves never overtake each other and each carries the revision the last
// one returned. A save from a tab that fell behind (409) stops the queue: the shell offers
// "Load the latest", and nothing more is sent until then. A failed save keeps the value and
// is sent again: after a pause, with the next change, and by flush(). Continue waits on flush(),
// which says whether everything reached the server.
// A refused answer (422) is put back and told to its own field; the rest still go. Once the Town
// has locked the project (409 locked, or a project that opens locked), nothing more is sent or
// changed: the save state says "With the Town".
import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import { getMe, UNREACHABLE, type Me } from "../api";
import {
  addPart as apiAddPart, getProject, removePart as apiRemovePart, saveAnswers, saveNote as apiSaveNote,
  setTitle as apiSetTitle, submitProject, type Attachment, type Change, type FormDef, type Missing, type ProjectState,
} from "../projects";
import type { Current } from "../forms/applicability";
import { withDerived } from "../forms/derived";
import type { SaveState } from "../shell/types";

const RETRY_MS = 5000;

export type SetOutcome = { ok: true } | { error: string };

type AppState = ProjectState;
export type SendOutcome = "sent" | { missing: Missing } | "failed";

type Store = {
  project: ProjectState | null; form: FormDef | null; cur: Current | null; problem: string | null;
  saveState: SaveState;
  locked: boolean; // the Town has locked it for review: nothing can change
  setAnswer: (fieldId: string, itemId: string | null, value: unknown) => Promise<SetOutcome>;
  flush: () => Promise<boolean>; // true when every change has reached the server
  addPart: (kind: string, copyFrom?: string) => Promise<string | null>;
  removePart: (partId: string) => Promise<boolean>;
  saveNote: (sectionId: string, itemId: string | null, text: string) => Promise<boolean>;
  setTitle: (title: string) => Promise<boolean>;
  submit: () => Promise<SendOutcome>; // Send to the Town
  reload: () => Promise<void>;
  // A file the Town kept, or took away: the check pages and the step both list project.attachments.
  attachmentAdded: (a: Attachment) => void;
  attachmentRemoved: (attachmentId: string) => void;
  visited: Set<string>;
  markVisited: (stepId: string) => void;
};

const Context = createContext<Store | null>(null);

export function useProject(): Store {
  const s = useContext(Context);
  if (!s) throw new Error("useProject outside ProjectProvider");
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

export function ProjectProvider({ id, children }: { id: string; children: ReactNode }) {
  const [app, setApp] = useState<AppState | null>(null);
  const [me, setMe] = useState<Me | null>(null);
  const [problem, setProblem] = useState<string | null>(null);
  const [saveState, setSaveState] = useState<SaveState>("idle");
  const saveStateRef = useRef<SaveState>("idle");
  saveStateRef.current = saveState;
  const [visited, setVisited] = useState<Set<string>>(() => readVisited(id));
  const chain = useRef<Promise<unknown>>(Promise.resolve());
  const revision = useRef(0);
  const stopped = useRef(false); // after a conflict, or once the Town has locked it
  const failed = useRef<Change[]>([]);
  const lastGood = useRef<AppState["answers"]>([]);

  const load = useCallback(async () => {
    const a = await getProject(id);
    if (a === "signed_out") return setProblem("signed_out");
    if (a === "not_found") return setProblem("We couldn't find that project.");
    if (a === "not_approved") return setProblem("This project isn't ready yet. Please contact the Town Office.");
    if (typeof a === "string") return setProblem(a === "busy" ? "The Town's server is busy. Please wait a minute." : UNREACHABLE);
    revision.current = a.revision;
    lastGood.current = a.answers;
    const locked = a.status === "locked" || a.status === "decided";
    stopped.current = locked;
    // Changes that haven't reached the server yet stay shown, and go with the next save.
    const pending = locked ? [] : failed.current;
    if (locked) failed.current = [];
    setApp({ ...a, answers: pending.reduce(withChange, a.answers) });
    setSaveState(locked ? "locked" : pending.length ? "error" : "idle");
  }, [id]);

  useEffect(() => {
    void load();
    getMe().then((m) => m && m !== "unavailable" && setMe(m));
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
    if (r === "locked") {
      stopped.current = true;
      failed.current = [];
      setApp((a) => (a ? { ...a, status: "locked", answers: lastGood.current } : a));
      setSaveState("locked");
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
    if ("incomplete" in r) return { ok: true }; // only Send answers this
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
    if (stopped.current && saveStateRef.current === "locked") return Promise.resolve({ ok: true });
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

  const addPart = useCallback((kind: string, copyFrom?: string) => enqueue(async () => {
    if (stopped.current) return null;
    const r = await apiAddPart(id, revision.current, kind, copyFrom);
    if (typeof r === "object" && "conflict" in r) {
      stopped.current = true;
      setSaveState("conflict");
      return null;
    }
    if (typeof r === "string" || !("revision" in r)) return null;
    await load(); // the new part arrives with its defaults and its questions, and a copy with its copied answers
    return (r as { id?: string }).id ?? null;
  }), [enqueue, id, load]);

  const removePart = useCallback((partId: string) => enqueue(async () => {
    if (stopped.current) return false;
    const r = await apiRemovePart(id, revision.current, partId);
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

  const setTitle = useCallback((title: string) => enqueue(async () => {
    if (stopped.current) return false;
    const r = await apiSetTitle(id, revision.current, title);
    if (typeof r !== "object" || !("revision" in r)) return false;
    revision.current = r.revision;
    setApp((a) => (a ? { ...a, title: title.trim(), revision: r.revision } : a));
    return true;
  }), [enqueue, id]);

  const submit = useCallback(async (): Promise<SendOutcome> => {
    if (!(await flush())) return "failed";
    return enqueue(async (): Promise<SendOutcome> => {
      const r = await submitProject(id, revision.current);
      if (typeof r === "object" && "incomplete" in r) return { missing: r.incomplete };
      if (typeof r !== "object" || !("revision" in r)) return "failed";
      await load();
      return "sent";
    });
  }, [enqueue, flush, id, load]);

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
    () => (app ? { answers: withDerived(app.items, app.answers), items: app.items, property: app.property.facts,
                   account: { email: me?.email ?? null, name: me?.name ?? null, phone: me?.phone ?? null,
                              mailing_address: me?.mailing_address ?? null } } : null),
    [app, me]);

  const value: Store = {
    project: app, form: app?.form ?? null, cur, problem, saveState, locked: saveState === "locked",
    setAnswer, flush, addPart, removePart, saveNote, setTitle, submit,
    reload: load, attachmentAdded, attachmentRemoved, visited, markVisited,
  };
  return <Context.Provider value={value}>{children}</Context.Provider>;
}
