// "Do I need a permit?" one question at a time: which of the screener's questions apply, in order.
// A building-work kind brings its size question and the two home counts; dividing land brings the
// lots and whether the land was divided before.
import type { ProjectKind, ScreenerAnswers } from "../screener";

export type Kind = NonNullable<ScreenerAnswers["building"]["kind"]>;
export type StartState = { project: ProjectKind[]; kind: Kind | "" };
export type StartScreenId = "plan" | "kind" | "area" | "total" | "parking" | "homes" | "earlier" | "lots" | "divided";
export type StartScreen = { id: StartScreenId; kind: "multi" | "choice" | "number" | "stepper"; auto: boolean; optional: boolean };

const S = (id: StartScreenId, kind: StartScreen["kind"], optional = false): StartScreen =>
  ({ id, kind, auto: kind === "choice", optional });

export function startScreens(s: StartState): StartScreen[] {
  const out = [S("plan", "multi")];
  if (s.project.includes("build")) {
    out.push(S("kind", "choice"));
    if (s.kind === "new" || s.kind === "addition") out.push(S("area", "number", true));
    if (s.kind === "renovation") out.push(S("total", "number", true));
    if (s.kind === "site") out.push(S("parking", "stepper", true));
    if (s.kind) out.push(S("homes", "stepper", true), S("earlier", "stepper", true));
  }
  if (s.project.includes("divide")) out.push(S("lots", "stepper"), S("divided", "choice"));
  return out;
}
