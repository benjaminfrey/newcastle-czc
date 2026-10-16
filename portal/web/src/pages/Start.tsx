import { Button, Checkbox, CheckboxGroup, Description, Form, Input, Label, Radio, RadioGroup, TextField } from "@heroui/react";
import { useState, type FormEvent } from "react";
import { useNavigate } from "react-router";
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

function NumberField({ label, help, value, onChange }: { label: string; help?: string; value: string; onChange: (v: string) => void }) {
  return (
    <TextField value={value} onChange={onChange} inputMode="decimal">
      <Label>{label}</Label>
      <Input />
      {help && <Description>{help}</Description>}
    </TextField>
  );
}

export default function Start() {
  const navigate = useNavigate();
  const [project, setProject] = useState<string[]>([]);
  const [kind, setKind] = useState<Kind | "">("");
  const [area, setArea] = useState("");
  const [total, setTotal] = useState("");
  const [parking, setParking] = useState("");
  const [homes, setHomes] = useState("");
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
      lots: project.includes("divide") ? parseNumber(lots) : null,
    };
    if (Object.values(n).some((v) => v !== null && Number.isNaN(v))) return setError("Please enter numbers as digits, like 2400.");
    for (const [v, what] of [[n.parking, "parking spaces"], [n.homes, "homes"], [n.lots, "lots"]] as const) {
      if (v !== null && !Number.isInteger(v)) return setError(`The number of ${what} should be a whole number.`);
    }
    if (n.lots !== null && n.lots < 1) return setError("The number of lots should be 1 or more.");
    saveAnswers({
      project: CHOICES.map((c) => c.value).filter((v) => project.includes(v)),
      use_key: null,
      building: { kind: build ? (kind as Kind) : null, gross_floor_area_sf: n.area, total_floor_area_sf: n.total,
                  parking_spaces: n.parking, new_dwelling_units: n.homes },
      division: { lots_after: n.lots },
    });
    navigate("/where");
  }

  return (
    <div className="flex flex-col gap-4">
      <h1 className="text-xl font-semibold">Do I need a permit?</h1>
      <p>Answer a few questions and we'll tell you what the Town's Code calls for. It takes a couple of minutes.</p>
      <Form onSubmit={onSubmit} className="flex flex-col gap-5">
        <CheckboxGroup value={project} onChange={(v) => { setProject(v); setError(null); }} name="project">
          <Label>What are you planning?</Label>
          <Description>Choose all that apply.</Description>
          {CHOICES.map((c) => (
            <Checkbox key={c.value} value={c.value}>
              <Checkbox.Content>
                <Checkbox.Control>
                  <Checkbox.Indicator />
                </Checkbox.Control>
                {c.label}
              </Checkbox.Content>
            </Checkbox>
          ))}
        </CheckboxGroup>
        {build && (
          <>
            <RadioGroup value={kind} onChange={(v) => { setKind(v as Kind); setError(null); }} name="kind">
              <Label>What kind of building work?</Label>
              {KINDS.map((k) => (
                <Radio key={k.value} value={k.value}>
                  <Radio.Content>
                    <Radio.Control>
                      <Radio.Indicator />
                    </Radio.Control>
                    {k.label}
                  </Radio.Content>
                </Radio>
              ))}
            </RadioGroup>
            {kind === "new" && (
              <NumberField label="How much floor area will the new building have, in square feet?" value={area} onChange={setArea}
                           help="Count every storey. Leave it blank if you don't know yet." />
            )}
            {kind === "addition" && (
              <NumberField label="How much floor area will the addition add, in square feet?" value={area} onChange={setArea}
                           help="Leave it blank if you don't know yet." />
            )}
            {kind === "renovation" && (
              <NumberField label="What is the floor area of the whole building, in square feet?" value={total} onChange={setTotal}
                           help="Count every storey. Leave it blank if you don't know yet." />
            )}
            {kind === "site" && (
              <NumberField label="How many parking spaces will there be?" value={parking} onChange={setParking}
                           help="Leave it blank if there's no parking, or you don't know yet." />
            )}
            {kind && (
              <NumberField label="How many new homes will you build or place?" value={homes} onChange={setHomes}
                           help="Count only new homes, not ones already there. Leave it blank if none." />
            )}
          </>
        )}
        {project.includes("divide") && (
          <NumberField label="How many lots will there be afterwards?" value={lots} onChange={setLots} />
        )}
        {error && <p role="alert">{error}</p>}
        <div>
          <Button type="submit" variant="primary">Next</Button>
        </div>
      </Form>
    </div>
  );
}
