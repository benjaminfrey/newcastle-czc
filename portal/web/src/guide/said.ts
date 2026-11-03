import type { Guide, Shown } from "./api";
import { DOESNT_FIT } from "./turns/heading";

const fmt = (n: number) => n.toLocaleString("en-US", { maximumFractionDigits: 2 });

// An answer as the person gave it: the answer's own label, or the number with its unit.
export function said(shown: Shown, value: unknown): string {
  if (typeof value === "number") return [fmt(value), shown.input?.unit].filter(Boolean).join(" ");
  return shown.answers.find((a) => a.id === value)?.label ?? String(value);
}

export type Row = { shown: Shown; words: string; mark: "fits" | "for_the_town" | null };

// The answers in force, one row per turn (a "doesn't fit" choice folds into its turn's row), in
// the order given, grouped by step. After "Make it …" the value shown is the one now in force,
// which the API's latest check holds; the marks are the API's own results.
export function rows(guide: Guide): { step: string; rows: Row[] }[] {
  const nearest = new Set(guide.history.filter((h) => h.shown.turn_id.startsWith(DOESNT_FIT) && h.value === "nearest")
    .map((h) => h.shown.turn_id.slice(DOESNT_FIT.length)));
  const groups = new Map<string, Row[]>();
  for (const { shown, value } of guide.history) {
    if (shown.turn_id.startsWith(DOESNT_FIT)) continue;
    const chk = guide.checks[shown.turn_id];
    const inForce = nearest.has(shown.turn_id) && chk?.value != null ? chk.value : value;
    const mark = !chk ? null : chk.result === "fits" ? "fits" : "for_the_town";
    const list = groups.get(shown.step.label) ?? [];
    list.push({ shown, words: said(shown, inForce), mark });
    groups.set(shown.step.label, list);
  }
  return [...groups].map(([step, r]) => ({ step, rows: r }));
}
