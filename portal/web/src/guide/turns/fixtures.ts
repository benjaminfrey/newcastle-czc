import type { Check, Shown } from "../api";

export const shown = (over: Partial<Shown> = {}): Shown => ({
  turn_id: "full_stories", kind: "choice", step: { n: 2, of: 4, label: "The building" }, ask: "How many?",
  help: null, answers: [{ id: "yes", label: "Yes", hint: null }, { id: "unsure", label: "I'm not sure yet", hint: null }],
  input: null, why: null, defines: [], check: null, facts_shown: null, ...over,
});

export const entry = (id: string, overline: string) => ({ id, overline, answer: `${id} answer`, detail: `${id} detail`,
  why: null, cites: [], version: 1, governs: "" });

export const check = (over: Partial<Check> = {}): Check => ({
  result: "fits", value: 20, min: 15, max: null, unit: "ft", room: 5, gap: null, direction: null, reason: null,
  standard_keys: ["d1/x"], nearest: [], ...over,
});
