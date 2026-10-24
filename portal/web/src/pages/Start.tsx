import { Checkbox, CheckboxGroup, Form, NumberField, Radio, RadioGroup } from "@heroui/react";
import { useState, type FormEvent } from "react";
import { useNavigate } from "react-router";
import ActionBar from "../shell/ActionBar";
import InsetGroup from "../shell/InsetGroup";
import { useWideLayout } from "../shell/useWideLayout";
import { saveAnswers, type ProjectKind, type ScreenerAnswers } from "../screener";

const CHOICES: { value: ProjectKind; label: string }[] = [
  { value: "build", label: "Build something new or add on" },
  { value: "use", label: "Start a business or change how a building is used" },
  { value: "driveway", label: "Put in or move a driveway" },
  { value: "divide", label: "Divide land" },
  { value: "other", label: "Something else / not sure" },
];

type Kind = NonNullable<ScreenerAnswers["building"]["kind"]>;
const KINDS: { value: Kind; label: string }[] = [
  { value: "new", label: "A new building" },
  { value: "addition", label: "An addition to a building" },
  { value: "renovation", label: "Renovating a building" },
  { value: "site", label: "Work on the site only (parking, grading, landscaping)" },
];

// "2,400 sq ft" → 2400; blank → null; anything without a number → NaN (an error).
function parseNumber(s: string): number | null {
  if (s.trim() === "") return null;
  const m = s.replace(/,/g, "").match(/\d+(\.\d+)?/);
  return m ? Number(m[0]) : NaN;
}

const ROW = "flex min-h-11 w-full items-center justify-between gap-4 px-4 py-2.5 text-[17px]";
const HELP = "text-[15px]";

// A number is kept as the text the page has always kept; a blank field is NaN to the control.
const toControl = (s: string) => { const n = parseNumber(s); return n === null ? NaN : n; };
const fromControl = (v: number) => (Number.isNaN(v) ? "" : String(v));

// One question as its own inset group: the question on the row, a number (with a unit or − / +)
// beside it, and the help line as the footnote.
function NumberQuestion({ label, help, value, onChange, unit, stepper, min = 0 }: {
  label: string; help?: string; value: string; onChange: (v: string) => void; unit?: string; stepper?: boolean; min?: number;
}) {
  return (
    <InsetGroup footer={help && <span className={HELP}>{help}</span>}>
      <InsetGroup.Row label={label}>
        <div className="flex items-center justify-end gap-2">
          <NumberField
            value={toControl(value)}
            onChange={(v) => onChange(fromControl(v))}
            minValue={min}
            step={1}
            formatOptions={stepper ? { maximumFractionDigits: 0, useGrouping: false } : { maximumFractionDigits: 2 }}
            aria-label={label}
            className={stepper ? "w-40" : "w-36"}
          >
            <NumberField.Group className="min-h-11">
              {stepper && <NumberField.DecrementButton className="min-h-11 min-w-11" />}
              <NumberField.Input className="text-right" />
              {stepper && <NumberField.IncrementButton className="min-h-11 min-w-11" />}
            </NumberField.Group>
          </NumberField>
          {unit && <span className="text-[var(--app-secondary-label)]">{unit}</span>}
        </div>
      </InsetGroup.Row>
    </InsetGroup>
  );
}

export default function Start() {
  const navigate = useNavigate();
  const wide = useWideLayout();
  const [project, setProject] = useState<string[]>([]);
  const [kind, setKind] = useState<Kind | "">("");
  const [area, setArea] = useState("");
  const [total, setTotal] = useState("");
  const [parking, setParking] = useState("");
  const [homes, setHomes] = useState("");
  const [earlierHomes, setEarlierHomes] = useState("");
  const [divided, setDivided] = useState<"yes" | "no" | "unsure">("unsure");
  const [lots, setLots] = useState("");
  const [error, setError] = useState<string | null>(null);
  const build = project.includes("build");

  function onSubmit(e: FormEvent) {
    e.preventDefault();
    if (project.length === 0) return setError("Choose at least one thing you're planning.");
    if (build && !kind) return setError("Choose what kind of building work you're planning.");
    const n = {
      area: kind === "new" || kind === "addition" ? parseNumber(area) : null,
      total: kind === "renovation" ? parseNumber(total) : null,
      parking: kind === "site" ? parseNumber(parking) : null,
      homes: build ? parseNumber(homes) : null,
      earlierHomes: build ? parseNumber(earlierHomes) : null,
      lots: project.includes("divide") ? parseNumber(lots) : null,
    };
    if (Object.values(n).some((v) => v !== null && Number.isNaN(v))) return setError("Please enter numbers as digits, like 2400.");
    for (const [v, what] of [[n.parking, "parking spaces"], [n.homes, "homes"], [n.earlierHomes, "earlier homes"], [n.lots, "lots"]] as const) {
      if (v !== null && !Number.isInteger(v)) return setError(`The number of ${what} should be a whole number.`);
    }
    if (n.lots !== null && n.lots < 1) return setError("The number of lots should be 1 or more.");
    saveAnswers({
      project: CHOICES.map((c) => c.value).filter((v) => project.includes(v)),
      use_key: null,
      building: { kind: build ? (kind as Kind) : null, gross_floor_area_sf: n.area, total_floor_area_sf: n.total,
                  parking_spaces: n.parking, new_dwelling_units: n.homes, homes_added_last_5_years: n.earlierHomes },
      division: { lots_after: n.lots,
                  divided_last_5_years: project.includes("divide") && divided !== "unsure" ? divided === "yes" : null },
    });
    navigate("/start/property");
  }

  return (
    <div className="flex flex-col gap-4">
      <p className="text-[17px]">Answer a few questions and we'll tell you what the Town's Code calls for. It takes a couple of minutes.</p>
      <Form onSubmit={onSubmit} className="flex flex-col gap-5">
        <InsetGroup title="What are you planning?" footer={<span className={HELP}>Choose all that apply.</span>}>
          <CheckboxGroup value={project} onChange={(v) => { setProject(v); setError(null); }} name="project" aria-label="What are you planning?"
                         className="gap-0 divide-y divide-[var(--app-separator)]">
            {CHOICES.map((c) => (
              <Checkbox key={c.value} value={c.value} className="w-full">
                <Checkbox.Content className={ROW}>
                  <span>{c.label}</span>
                  <Checkbox.Control>
                    <Checkbox.Indicator />
                  </Checkbox.Control>
                </Checkbox.Content>
              </Checkbox>
            ))}
          </CheckboxGroup>
        </InsetGroup>
        {build && (
          <>
            <InsetGroup title="What kind of building work?">
              <RadioGroup value={kind} onChange={(v) => { setKind(v as Kind); setError(null); }} name="kind" aria-label="What kind of building work?"
                          className="gap-0 divide-y divide-[var(--app-separator)]">
                {KINDS.map((k) => (
                  <Radio key={k.value} value={k.value} className="w-full">
                    <Radio.Content className={ROW}>
                      <span>{k.label}</span>
                      <Radio.Control>
                        <Radio.Indicator />
                      </Radio.Control>
                    </Radio.Content>
                  </Radio>
                ))}
              </RadioGroup>
            </InsetGroup>
            {kind === "new" && (
              <NumberQuestion label="How much floor area will the new building have, in square feet?" value={area} onChange={setArea} unit="sq ft"
                              help="Count every storey. Leave it blank if you don't know yet." />
            )}
            {kind === "addition" && (
              <NumberQuestion label="How much floor area will the addition add, in square feet?" value={area} onChange={setArea} unit="sq ft"
                              help="Leave it blank if you don't know yet." />
            )}
            {kind === "renovation" && (
              <NumberQuestion label="What is the floor area of the whole building, in square feet?" value={total} onChange={setTotal} unit="sq ft"
                              help="Count every storey. Leave it blank if you don't know yet." />
            )}
            {kind === "site" && (
              <NumberQuestion label="How many parking spaces will there be?" value={parking} onChange={setParking} stepper
                              help="Leave it blank if there's no parking, or you don't know yet." />
            )}
            {kind && (
              <>
                <NumberQuestion label="How many new homes will you build or place?" value={homes} onChange={setHomes} stepper
                                help="Count only new homes, not ones already there. Leave it blank if none." />
                <NumberQuestion label="How many homes were added on this lot in the last five years, before this project?"
                                value={earlierHomes} onChange={setEarlierHomes} stepper
                                help="Homes added within five years count together. Leave it blank if you don't know." />
              </>
            )}
          </>
        )}
        {project.includes("divide") && (
          <>
            <NumberQuestion label="How many lots will there be afterwards?" value={lots} onChange={setLots} stepper />
            <InsetGroup title="Has this land been divided in the last five years?"
                        footer={<span className={HELP}>Lots made within five years count together.</span>}>
              <RadioGroup value={divided} onChange={(v) => setDivided(v as "yes" | "no" | "unsure")} name="divided"
                          aria-label="Has this land been divided in the last five years?" className="gap-0 divide-y divide-[var(--app-separator)]">
                {([["yes", "Yes"], ["no", "No"], ["unsure", "I don't know"]] as const).map(([v, l]) => (
                  <Radio key={v} value={v} className="w-full">
                    <Radio.Content className={ROW}>
                      <span>{l}</span>
                      <Radio.Control>
                        <Radio.Indicator />
                      </Radio.Control>
                    </Radio.Content>
                  </Radio>
                ))}
              </RadioGroup>
            </InsetGroup>
          </>
        )}
        {error && <p role="alert" className="px-4 text-[15px] text-[var(--app-destructive)]">{error}</p>}
        <ActionBar actions={{ onContinue: () => {} }} wide={wide} />
      </Form>
    </div>
  );
}
