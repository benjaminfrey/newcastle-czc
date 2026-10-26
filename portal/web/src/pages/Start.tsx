import { NumberField } from "@heroui/react";
import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router";
import type { FormField } from "../projects";
import Icon from "../controls/Icon";
import { ChoiceTiles, MultiTiles } from "../controls/Tiles";
import Card from "../shell/Card";
import { saveAnswers, type ProjectKind } from "../screener";
import { startScreens, type Kind, type StartScreenId } from "../start/startScreens";

const CHOICES: { value: ProjectKind; label: string; icon: string }[] = [
  { value: "build", label: "Build something new or add on", icon: "home-plus" },
  { value: "use", label: "Start a business or change how a building is used", icon: "building-store" },
  { value: "driveway", label: "Put in or move a driveway", icon: "road" },
  { value: "divide", label: "Divide land", icon: "layout-grid" },
  { value: "other", label: "Something else / not sure", icon: "help-circle" },
];
const KINDS: { value: Kind; label: string; icon: string }[] = [
  { value: "new", label: "A new building", icon: "building-cottage" },
  { value: "addition", label: "An addition to a building", icon: "home-plus" },
  { value: "renovation", label: "Renovating a building", icon: "paint" },
  { value: "site", label: "Work on the site only (parking, grading, landscaping)", icon: "shovel" },
];
const DIVIDED = [{ value: "yes", label: "Yes" }, { value: "no", label: "No" }, { value: "unsure", label: "I don't know" }];

// Each screen's question and its line of help.
const ASK: Record<StartScreenId, [string, string | null]> = {
  plan: ["What are you planning?", "Choose all that apply."],
  kind: ["What kind of building work?", "Choose one."],
  area: ["", "Count every storey. Leave it blank if you don't know yet."],
  total: ["What is the floor area of the whole building, in square feet?", "Count every storey. Leave it blank if you don't know yet."],
  parking: ["How many parking spaces will there be?", "Leave it blank if there's no parking, or you don't know yet."],
  homes: ["How many new homes will you build or place?", "Count only new homes, not ones already there. Leave it blank if none."],
  earlier: ["How many homes were added on this lot in the last five years, before this project?", "Homes added within five years count together. Leave it blank if you don't know."],
  lots: ["How many lots will there be afterwards?", null],
  divided: ["Has this land been divided in the last five years?", "Lots made within five years count together."],
};
const asked = (id: StartScreenId, kind: Kind | "") => id !== "area" ? ASK[id][0]
  : kind === "addition" ? "How much floor area will the addition add, in square feet?" : "How much floor area will the new building have, in square feet?";

// "2,400 sq ft" → 2400; blank → null; anything without a number → NaN (an error).
function parseNumber(s: string): number | null {
  if (s.trim() === "") return null;
  const m = s.replace(/,/g, "").match(/\d+(\.\d+)?/);
  return m ? Number(m[0]) : NaN;
}
const toControl = (s: string) => { const n = parseNumber(s); return n === null ? NaN : n; };
const fromControl = (v: number) => (Number.isNaN(v) ? "" : String(v));
// The tiles want a field; the screener's questions aren't form fields, so each gets a small one.
const field = (id: string, label: string, options: { value: string; label: string; icon?: string }[]): FormField => ({
  id, label, official_label: label, source: "question", from: null, may_correct: false, help: null, why: null, type: "choice",
  unit: null, min: null, max: null, required: true, allow_unknown: false, show_if: null,
  options: options.map((o) => ({ ...o, official: o.label })),
});

// "Do I need a permit?", Your project, one question to a card (task-list brief §9): a tap answers
// a single choice and moves on; the rest have Continue. The bar counts the questions that apply to
// what has been chosen so far, and never fewer than already answered. The answers are saved when
// the last one is given.
export default function Start() {
  const navigate = useNavigate();
  const [project, setProject] = useState<ProjectKind[]>([]);
  const [kind, setKind] = useState<Kind | "">("");
  const [nums, setNums] = useState<Record<string, string>>({});
  const [divided, setDivided] = useState<"yes" | "no" | "unsure">("unsure");
  const [at, setAt] = useState(0);
  const [dir, setDir] = useState<1 | -1>(1);
  const [error, setError] = useState<string | null>(null);
  const [reached, setReached] = useState(1);
  const busy = useRef(false);
  const list = startScreens({ project, kind });
  const i = Math.min(at, list.length - 1);
  const screen = list[i];
  const heading = asked(screen.id, kind);
  const num = (id: string) => nums[id] ?? "";
  useEffect(() => { document.querySelector<HTMLElement>("[data-screen-title]")?.focus(); }, [screen.id]);
  useEffect(() => setReached((r) => Math.max(r, i + 1)), [i]);

  function finish(divOverride?: "yes" | "no" | "unsure") {
    const build = project.includes("build");
    const n = {
      area: kind === "new" || kind === "addition" ? parseNumber(num("area")) : null,
      total: kind === "renovation" ? parseNumber(num("total")) : null,
      parking: kind === "site" ? parseNumber(num("parking")) : null,
      homes: build ? parseNumber(num("homes")) : null,
      earlierHomes: build ? parseNumber(num("earlier")) : null,
      lots: project.includes("divide") ? parseNumber(num("lots")) : null,
    };
    const div = divOverride ?? divided;
    saveAnswers({
      project: CHOICES.map((c) => c.value).filter((v) => project.includes(v)),
      use_key: null,
      building: { kind: build ? (kind as Kind) : null, gross_floor_area_sf: n.area, total_floor_area_sf: n.total,
                  parking_spaces: n.parking, new_dwelling_units: n.homes, homes_added_last_5_years: n.earlierHomes },
      division: { lots_after: n.lots, divided_last_5_years: project.includes("divide") && div !== "unsure" ? div === "yes" : null },
    });
    navigate("/start/property");
  }
  const forward = () => { setError(null); setDir(1); if (i >= list.length - 1) finish(); else setAt(i + 1); };

  function onContinue() {
    if (screen.id === "plan" && project.length === 0) return setError("Choose at least one thing you're planning.");
    if (screen.kind === "number" || screen.kind === "stepper") {
      const v = parseNumber(num(screen.id));
      if (v !== null && Number.isNaN(v)) return setError("Please enter numbers as digits, like 2400.");
      if (screen.kind === "stepper" && v !== null && !Number.isInteger(v)) return setError("Please enter a whole number.");
      if (screen.id === "lots" && v !== null && v < 1) return setError("The number of lots should be 1 or more.");
    }
    forward();
  }
  // A tap answers and, after a moment to see the tile chosen, moves on.
  function tap(apply: () => void, last?: () => void) {
    if (busy.current) return;
    busy.current = true;
    apply();
    setTimeout(() => { busy.current = false; if (last) last(); else { setDir(1); setAt(i + 1); } }, 200);
  }

  const body = (() => {
    switch (screen.id) {
      case "plan":
        return <MultiTiles field={field("plan", heading, CHOICES)} value={project}
                           onValue={(v) => { setProject((v as ProjectKind[] | null) ?? []); setError(null); }} />;
      case "kind":
        return <ChoiceTiles field={field("kind", heading, KINDS)} value={kind}
                            choices={KINDS.map((k) => ({ value: k.value, key: k.value, label: k.label, icon: <Icon name={k.icon} /> }))}
                            onPick={(v) => tap(() => setKind(v as Kind))} />;
      case "divided":
        return <ChoiceTiles field={field("divided", heading, DIVIDED)} value={null}
                            onPick={(v) => tap(() => setDivided(v as "yes" | "no" | "unsure"), () => finish(v as "yes" | "no" | "unsure"))} />;
      default: {
        const stepper = screen.kind === "stepper";
        return (
          <div className="flex items-center justify-center gap-2">
            <NumberField value={toControl(num(screen.id))} onChange={(v) => setNums((n) => ({ ...n, [screen.id]: fromControl(v) }))}
                         minValue={screen.id === "lots" ? 1 : 0} step={1} aria-label={heading} className={stepper ? "w-44" : "w-40"}
                         formatOptions={stepper ? { maximumFractionDigits: 0, useGrouping: false } : { maximumFractionDigits: 2 }}>
              <NumberField.Group className="min-h-12">
                {stepper && <NumberField.DecrementButton className="min-h-12 min-w-12" />}
                <NumberField.Input className="text-right text-[17px]" />
                {stepper && <NumberField.IncrementButton className="min-h-12 min-w-12" />}
              </NumberField.Group>
            </NumberField>
            {(screen.id === "area" || screen.id === "total") && <span className="text-[17px] text-[var(--app-secondary-label)]">sq ft</span>}
          </div>
        );
      }
    }
  })();
  const blank = screen.kind !== "multi" && !num(screen.id);
  const count = Math.max(list.length, reached);

  return (
    <Card onSubmit={onContinue}>
      <Card.Header title="Your project" count={count} at={i} />
      <Card.Body motionKey={screen.id} direction={dir}>
        <h2 tabIndex={-1} data-screen-title className="max-w-[30ch] text-balance text-[20px] font-medium leading-[1.3] outline-none">{heading}</h2>
        <p className="mb-4 mt-1 max-w-[46ch] text-pretty text-[13px] text-[var(--app-secondary-label)]">{ASK[screen.id][1] ?? ""}</p>
        {body}
        {error && <p role="alert" className="mt-3 text-[15px] text-[var(--app-destructive)]">{error}</p>}
      </Card.Body>
      <Card.Footer
        back={i > 0 ? { label: "Back", onPress: () => { setDir(-1); setError(null); setAt(i - 1); } } : undefined}
        next={screen.auto ? null : { label: screen.optional && blank ? "Skip for now" : "Continue", plain: screen.optional && blank, onPress: onContinue }} />
      <p className="sr-only" aria-live="polite">Question {i + 1} of {count}: {heading}</p>
    </Card>
  );
}
