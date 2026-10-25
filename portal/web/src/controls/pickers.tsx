import { Input, Radio, RadioGroup, TextField } from "@heroui/react";
import { useEffect, useState } from "react";
import { useApplication } from "../app/ApplicationStore";
import type { FormDef } from "../applications";
import type { Current } from "../forms/applicability";
import { itemLabel } from "../forms/steps";
import { type ControlProps } from "./basic";
import { ChoiceTiles } from "./Tiles";

const FREE = "Free-standing";
const ANOTHER = "__another__";

// "Attached to": one of this application's buildings, or free-standing. Stores the building's id,
// so renaming or deleting a building can't leave stale words; review shows its name as it is now.
export function BuildingPicker(p: ControlProps) {
  const { form, cur } = useApplication();
  const buildings = (cur?.items ?? []).filter((i) => i.kind === "building").sort((a, b) => a.position - b.position);
  const items = [...buildings.map((i) => ({ id: i.id, label: itemLabel(form!, cur!, i.id) })), { id: FREE, label: FREE }];
  // An answer from before ids were stored names a building by its words: show it as that building.
  const legacy = typeof p.value === "string" ? items.find((x) => x.label === p.value)?.id : undefined;
  return <ChoiceTiles field={p.field} value={legacy ?? p.value} onPick={p.onValue}
                      choices={items.map((x) => ({ value: x.id, key: x.id, label: x.label }))} />;
}

// The words for an "attached to" answer: the building's current name, "Free-standing", an older
// answer's own words, or null when that building has since been deleted.
export function buildingLabel(form: FormDef, cur: Current, value: string): string | null {
  if (value === FREE) return FREE;
  if (cur.items.some((i) => i.id === value)) return itemLabel(form, cur, value);
  return /^[0-9a-f]{8}-[0-9a-f]{4}-/.test(value) ? null : value;
}

// The entrance's road: one along the lot (from the Town's map), or another road, typed. A road
// typed in saves through `onTyped` (it waits for Continue); a road tapped answers through onValue.
export function StreetPicker(p: ControlProps & { onTyped?: (v: string) => void; onAnother?: () => void }) {
  const { cur } = useApplication();
  const roads = ((cur?.property.streets as { name: string }[] | undefined) ?? []).map((s) => s.name);
  const typed = typeof p.value === "string" && p.value !== "" && !roads.includes(p.value);
  const [another, setAnother] = useState(typed);
  const [draft, setDraft] = useState(typed ? (p.value as string) : "");
  useEffect(() => { if (typed) setAnother(true); }, [typed]);
  const choices = [...roads.map((r) => ({ value: r, key: r, label: r })), { value: ANOTHER, key: ANOTHER, label: "Another road" }];
  return (
    <div className="flex w-full flex-col items-center gap-3">
      <ChoiceTiles field={p.field} value={another ? ANOTHER : p.value} choices={choices}
                   onPick={(v) => (v === ANOTHER ? (setAnother(true), p.onAnother?.()) : (setAnother(false), p.onValue(v)))} />
      {another && (
        <TextField value={draft} onChange={setDraft} aria-label="Name of the road"
                   onBlur={() => draft.trim() && (p.onTyped ?? p.onValue)(draft.trim())}>
          <Input placeholder="Name of the road" className="min-h-11" />
        </TextField>
      )}
    </div>
  );
}

// The building type in two easy steps: what kind of thing it is, then (only where the Code
// splits it) which exactly. Options come from the field (Art. 5 §1.c).
const GROUPS: { key: string; label: string; values: string[] }[] = [
  { key: "home", label: "A home", values: ["residential"] },
  { key: "business", label: "A building for a business", values: ["single_unit_commercial", "multi_unit_commercial", "mixed_use"] },
  { key: "smaller", label: "A smaller building that goes with a home or business", values: ["residential_accessory", "commercial_accessory", "general_accessory"] },
  { key: "farm", label: "A farm building", values: ["agricultural"] },
  { key: "other", label: "Something else", values: ["special_use"] },
];

export function BuildingTypeControl({ field, value, onValue }: ControlProps) {
  const groupOf = (v: unknown) => GROUPS.find((g) => g.values.includes(v as string))?.key ?? null;
  const [group, setGroup] = useState<string | null>(groupOf(value));
  useEffect(() => { if (groupOf(value)) setGroup(groupOf(value)); }, [value]);
  const g = GROUPS.find((x) => x.key === group);
  const options = g ? field.options.filter((o) => g.values.includes(o.value)) : [];
  const tile = "min-h-12 rounded-xl border border-[var(--app-separator)] bg-[var(--app-row)] px-4 py-3 data-[selected]:border-[var(--app-accent)] data-[selected]:bg-[var(--app-selection)]";
  return (
    <div className="flex flex-col gap-3">
      <RadioGroup value={group} aria-label={field.label ?? field.official_label} className="grid gap-2"
                  onChange={(k) => {
                    setGroup(k);
                    const only = GROUPS.find((x) => x.key === k)!.values;
                    if (only.length === 1) onValue(only[0]);
                  }}>
        {GROUPS.map((x) => (
          <Radio key={x.key} value={x.key} className={tile}>
            <Radio.Content><Radio.Control className="sr-only"><Radio.Indicator /></Radio.Control>
              {x.key === "home" ? options.length === 1 || !g ? field.options.find((o) => o.value === "residential")?.label ?? x.label : x.label : x.label}
            </Radio.Content>
          </Radio>
        ))}
      </RadioGroup>
      {options.length > 1 && (
        <RadioGroup value={typeof value === "string" && g!.values.includes(value) ? value : null} onChange={onValue}
                    aria-label="Which kind?" className="grid gap-2 pl-4">
          {options.map((o) => (
            <Radio key={o.value} value={o.value} className={tile}>
              <Radio.Content><Radio.Control className="sr-only"><Radio.Indicator /></Radio.Control>{o.label}</Radio.Content>
            </Radio>
          ))}
        </RadioGroup>
      )}
    </div>
  );
}
