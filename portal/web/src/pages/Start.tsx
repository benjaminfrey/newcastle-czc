import { Button, Checkbox, CheckboxGroup, Description, Form, Input, Label, TextField } from "@heroui/react";
import { useState, type FormEvent } from "react";
import { useNavigate } from "react-router";
import { saveAnswers, type ProjectKind } from "../screener";

const CHOICES: { value: ProjectKind; label: string }[] = [
  { value: "build", label: "Build something new or add on" },
  { value: "use", label: "Start a business or change how a building is used" },
  { value: "driveway", label: "Put in or move a driveway" },
  { value: "divide", label: "Divide land" },
  { value: "other", label: "Something else / not sure" },
];

const toNumber = (s: string): number | null => {
  const n = Number(s.replace(/,/g, "").trim());
  return s.trim() === "" || !Number.isFinite(n) || n < 0 ? null : n;
};

export default function Start() {
  const navigate = useNavigate();
  const [project, setProject] = useState<string[]>([]);
  const [area, setArea] = useState("");
  const [homes, setHomes] = useState("");
  const [lots, setLots] = useState("");
  const [error, setError] = useState<string | null>(null);

  function onSubmit(e: FormEvent) {
    e.preventDefault();
    if (project.length === 0) return setError("Choose at least one thing you're planning.");
    const build = project.includes("build");
    saveAnswers({
      project: CHOICES.map((c) => c.value).filter((v) => project.includes(v)),
      use_key: null,
      building: { kind: build ? "new" : null, gross_floor_area_sf: build ? toNumber(area) : null,
                  dwelling_units: build ? toNumber(homes) : null },
      division: { lots_after: project.includes("divide") ? toNumber(lots) : null },
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
        {project.includes("build") && (
          <>
            <TextField value={area} onChange={setArea} inputMode="numeric">
              <Label>How much floor area will you add, in square feet?</Label>
              <Input />
              <Description>Count every storey. Leave it blank if you don't know yet.</Description>
            </TextField>
            <TextField value={homes} onChange={setHomes} inputMode="numeric">
              <Label>How many homes will there be on the lot afterwards?</Label>
              <Input />
              <Description>Leave it blank if none, or if you don't know yet.</Description>
            </TextField>
          </>
        )}
        {project.includes("divide") && (
          <TextField value={lots} onChange={setLots} inputMode="numeric">
            <Label>How many lots will there be afterwards?</Label>
            <Input />
          </TextField>
        )}
        {error && <p role="alert">{error}</p>}
        <div>
          <Button type="submit" variant="primary">Next</Button>
        </div>
      </Form>
    </div>
  );
}
