import { useCallback, useEffect, useReducer, useRef } from "react";
import { addPart, getProject } from "../projects";
import {
  addNote, answerTurn, getGuide, getOpenings, goBack, isRefusal, revisit, startGuide,
  type Guide, type GuideRefusal, type Opening,
} from "./api";
import type { WORDS } from "./words";

type Notice = keyof typeof WORDS.notices;
type StartOptions = { addPart?: string; note?: string };
type Why = "signed_out" | "not_found" | "not_approved" | "unavailable" | "busy";
export type GuideView =
  | { phase: "loading" }
  | { phase: "pick"; openings: Opening[]; revision: number; busy: boolean; notice: Notice | null; locked: boolean }
  // epoch counts reloads: a turn shown again after one starts fresh (its key changes). unsent is
  // the scene's box text when its note didn't go through, waiting in the reply box (plan 5).
  | { phase: "talk"; guide: Guide; busy: boolean; notice: Notice | null; locked: boolean; epoch: number; unsent?: string | null }
  | { phase: "refused"; why: Why };

type Act =
  | { t: "view"; view: GuideView }
  | { t: "busy"; busy: boolean }
  | { t: "guide"; guide: Guide; notice?: Notice | null; reload?: boolean; unsent?: string | null }
  | { t: "locked" }
  | { t: "dismiss" };

function reduce(v: GuideView, a: Act): GuideView {
  switch (a.t) {
    case "view": return a.view;
    case "busy": return v.phase === "talk" || v.phase === "pick" ? { ...v, busy: a.busy } : v;
    case "guide": {
      const epoch = v.phase === "talk" ? v.epoch + (a.reload ? 1 : 0) : 0;
      return { phase: "talk", guide: a.guide, busy: false, notice: a.notice ?? null,
        locked: v.phase === "talk" && v.locked, epoch, unsent: a.unsent ?? null };
    }
    case "locked": return v.phase === "talk" || v.phase === "pick" ? { ...v, busy: false, locked: true } : v;
    case "dismiss": return v.phase === "talk" || v.phase === "pick" ? { ...v, notice: null } : v;
  }
}

function why(r: GuideRefusal): Why {
  return r === "signed_out" || r === "not_found" || r === "not_approved" || r === "busy" ? r : "unavailable";
}

// The one place a project's conversation lives (guided plan 3). It holds the guide as the API
// last returned it and its revision, and lets one change be in flight at a time: a second tap
// while one is on its way is ignored, never queued or sent twice. Each action's promise settles
// once the guide shows its result, so a caller can move on after it (Change from Check and send).
export function useGuide(projectId: string) {
  const [view, dispatch] = useReducer(reduce, { phase: "loading" } as GuideView);
  const live = useRef(view);
  live.current = view;
  const inFlight = useRef(false);

  const load = useCallback(async (notice: Notice | null = null) => {
    const g = await getGuide(projectId);
    if (g === "not_started") {
      const [openings, project] = await Promise.all([getOpenings(projectId), getProject(projectId)]);
      if (isRefusal(openings)) return dispatch({ t: "view", view: { phase: "refused", why: why(openings) } });
      if (typeof project === "string") return dispatch({ t: "view", view: { phase: "refused", why: why(project) } });
      return dispatch({ t: "view", view: { phase: "pick", openings, revision: project.revision, busy: false, notice, locked: false } });
    }
    if (isRefusal(g)) return dispatch({ t: "view", view: { phase: "refused", why: why(g) } });
    dispatch({ t: "guide", guide: g, notice, reload: true });
  }, [projectId]);

  useEffect(() => { void load(); }, [load]);

  // True once the change has landed; false when it was ignored or refused (a caller can keep what
  // the person typed).
  const run = useCallback(async (send: (rev: number) => Promise<Guide | GuideRefusal>): Promise<boolean> => {
    const v = live.current;
    if (inFlight.current) return false;
    if (v.phase !== "talk" && v.phase !== "pick") return false;
    if (v.phase === "talk" && v.locked) return false;
    inFlight.current = true;
    dispatch({ t: "busy", busy: true });
    try {
      const out = await send(v.phase === "talk" ? v.guide.revision : v.revision);
      if (!isRefusal(out)) {
        dispatch({ t: "guide", guide: out });
        return true;
      }
      if (out === "locked") dispatch({ t: "locked" });
      else if (typeof out === "object" && "conflict" in out) await load("changed_elsewhere");
      else if (typeof out === "object" && "rejected" in out) await load("try_again");
      else dispatch({ t: "view", view: { phase: "refused", why: why(out) } });
      return false;
    } finally {
      inFlight.current = false;
      dispatch({ t: "busy", busy: false });
    }
  }, [load]);

  // From the scene (guided plan 5): add the part first when asked, then start, then keep what the
  // person wrote as the conversation's first note. A refused add starts nothing; a note that fails
  // after the start leaves the guide started, says to try again, and puts the words in the reply box.
  const startFrom = useCallback(async (opening: string, opts: StartOptions): Promise<boolean> => {
    let noteFailed = false;
    let started: Guide | null = null;
    const ok = await run(async (rev) => {
      let r = rev;
      if (opts.addPart) {
        const added = await addPart(projectId, r, opts.addPart);
        if (typeof added === "string") return added;
        if ("conflict" in added) return { conflict: true };
        if (!("revision" in added)) return { rejected: "add_part" };
        r = added.revision;
      }
      const g = await startGuide(projectId, opening, r);
      if (isRefusal(g)) return g;
      started = g;
      const note = opts.note?.trim();
      if (!note) return g;
      const n = await addNote(projectId, note, g.revision);
      if (isRefusal(n)) { noteFailed = true; return g; }
      return n;
    });
    if (ok && noteFailed && started) dispatch({ t: "guide", guide: started, notice: "try_again", unsent: opts.note?.trim() ?? null });
    return ok;
  }, [projectId, run]);

  return {
    view,
    start: (opening: string, opts: StartOptions = {}) => startFrom(opening, opts),
    answer: (turnId: string, value: unknown) => run((rev) => answerTurn(projectId, turnId, value, rev)),
    back: () => run((rev) => goBack(projectId, rev)),
    change: (turnId: string) => run((rev) => revisit(projectId, turnId, rev)),
    note: (body: string) => run((rev) => addNote(projectId, body, rev)),
    dismissNotice: () => dispatch({ t: "dismiss" }),
    reload: () => load(),
  };
}
