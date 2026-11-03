import { useCallback, useEffect, useReducer, useRef } from "react";
import { getProject } from "../projects";
import {
  addNote, answerTurn, getGuide, getOpenings, goBack, isRefusal, revisit, startGuide,
  type Guide, type GuideRefusal, type Opening,
} from "./api";
import type { WORDS } from "./words";

type Notice = keyof typeof WORDS.notices;
type Why = "signed_out" | "not_found" | "not_approved" | "unavailable" | "busy";
export type GuideView =
  | { phase: "loading" }
  | { phase: "pick"; openings: Opening[]; revision: number; busy: boolean }
  | { phase: "talk"; guide: Guide; busy: boolean; notice: Notice | null; locked: boolean }
  | { phase: "refused"; why: Why };

type Act =
  | { t: "view"; view: GuideView }
  | { t: "busy"; busy: boolean }
  | { t: "guide"; guide: Guide; notice?: Notice | null }
  | { t: "locked" }
  | { t: "dismiss" };

function reduce(v: GuideView, a: Act): GuideView {
  switch (a.t) {
    case "view": return a.view;
    case "busy": return v.phase === "talk" || v.phase === "pick" ? { ...v, busy: a.busy } : v;
    case "guide": return { phase: "talk", guide: a.guide, busy: false,
      notice: a.notice ?? null, locked: v.phase === "talk" && v.locked };
    case "locked": return v.phase === "talk" ? { ...v, busy: false, locked: true } : v;
    case "dismiss": return v.phase === "talk" ? { ...v, notice: null } : v;
  }
}

function why(r: GuideRefusal): Why {
  return r === "signed_out" || r === "not_found" || r === "not_approved" || r === "busy" ? r : "unavailable";
}

// The one place a project's conversation lives (guided plan 3). It holds the guide as the API
// last returned it and its revision, and lets one change be in flight at a time: a second tap
// while one is on its way is ignored, never queued or sent twice.
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
      return dispatch({ t: "view", view: { phase: "pick", openings, revision: project.revision, busy: false } });
    }
    if (isRefusal(g)) return dispatch({ t: "view", view: { phase: "refused", why: why(g) } });
    dispatch({ t: "guide", guide: g, notice });
  }, [projectId]);

  useEffect(() => { void load(); }, [load]);

  const run = useCallback(async (send: (rev: number) => Promise<Guide | GuideRefusal>) => {
    const v = live.current;
    if (inFlight.current) return;
    if (v.phase !== "talk" && v.phase !== "pick") return;
    if (v.phase === "talk" && v.locked) return;
    inFlight.current = true;
    dispatch({ t: "busy", busy: true });
    try {
      const out = await send(v.phase === "talk" ? v.guide.revision : v.revision);
      if (!isRefusal(out)) dispatch({ t: "guide", guide: out });
      else if (out === "locked") dispatch({ t: "locked" });
      else if (typeof out === "object" && "conflict" in out) await load("changed_elsewhere");
      else if (typeof out === "object" && "rejected" in out) await load("try_again");
      else dispatch({ t: "view", view: { phase: "refused", why: why(out) } });
    } finally {
      inFlight.current = false;
      dispatch({ t: "busy", busy: false });
    }
  }, [load]);

  return {
    view,
    start: (opening: string) => void run((rev) => startGuide(projectId, opening, rev)),
    answer: (turnId: string, value: unknown) => void run((rev) => answerTurn(projectId, turnId, value, rev)),
    back: () => void run((rev) => goBack(projectId, rev)),
    change: (turnId: string) => void run((rev) => revisit(projectId, turnId, rev)),
    note: (body: string) => void run((rev) => addNote(projectId, body, rev)),
    dismissNotice: () => dispatch({ t: "dismiss" }),
  };
}
