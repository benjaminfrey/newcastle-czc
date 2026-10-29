import { Input, TextField } from "@heroui/react";
import { useEffect, useState } from "react";
import { useProject } from "../app/ProjectStore";
import type { FormDef } from "../projects";
import type { Current } from "../forms/applicability";
import { itemLabel } from "../forms/steps";
import { type ControlProps } from "./basic";
import Icon from "./Icon";
import { ChoiceTiles } from "./Tiles";

const FREE = "Free-standing";
const ANOTHER = "__another__";

// "Attached to": one of this application's buildings, or free-standing. Stores the building's id,
// so renaming or deleting a building can't leave stale words; review shows its name as it is now.
export function BuildingPicker(p: ControlProps) {
  const { form, cur } = useProject();
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
  const { cur } = useProject();
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
// The first step's icons (task-list brief §5): the step is the control's own grouping, not form options.
const KIND_ICONS: Record<string, string> = { home: "home", business: "building-store", smaller: "building-warehouse", farm: "tractor", other: "building" };
const GROUPS: { key: string; label: string; values: string[] }[] = [
  { key: "home", label: "A home", values: ["residential"] },
  { key: "business", label: "A building for a business", values: ["single_unit_commercial", "multi_unit_commercial", "mixed_use"] },
  { key: "smaller", label: "A smaller building that goes with a home or business", values: ["residential_accessory", "commercial_accessory", "general_accessory"] },
  { key: "farm", label: "A farm building", values: ["agricultural"] },
  { key: "other", label: "Something else", values: ["special_use"] },
];

// A building type's kind in the applicant's words ("A home") and its icon: the building's line on
// the buildings list and its cards' header.
export function buildingKind(value: string): { label: string; icon: string } | null {
  const g = GROUPS.find((x) => x.values.includes(value));
  return g ? { label: g.label, icon: KIND_ICONS[g.key] } : null;
}

export function BuildingTypeControl({ field, value, onValue }: ControlProps) {
  const groupOf = (v: unknown) => GROUPS.find((g) => g.values.includes(v as string))?.key ?? null;
  const [group, setGroup] = useState<string | null>(groupOf(value));
  useEffect(() => { if (groupOf(value)) setGroup(groupOf(value)); }, [value]);
  const g = GROUPS.find((x) => x.key === group);
  const options = g ? field.options.filter((o) => g.values.includes(o.value)) : [];
  const home = field.options.find((o) => o.value === "residential")?.label;
  const kinds = GROUPS.map((x) => ({ value: x.key, key: x.key, label: x.key === "home" ? home ?? x.label : x.label,
                                     icon: <Icon name={KIND_ICONS[x.key]} /> }));
  // A kind with one building type answers at once; one with several asks which (no icons there).
  const pickKind = (k: unknown) => {
    setGroup(k as string);
    const only = GROUPS.find((x) => x.key === k)!.values;
    if (only.length === 1) onValue(only[0]);
  };
  return (
    <div className="flex w-full flex-col items-center gap-3">
      <ChoiceTiles field={field} value={group} choices={kinds} onPick={pickKind} />
      {options.length > 1 && (
        <ChoiceTiles field={{ ...field, label: "Which kind?" }} value={typeof value === "string" && g!.values.includes(value) ? value : null}
                     choices={options.map((o) => ({ value: o.value, key: o.value, label: o.label }))} onPick={onValue} />
      )}
    </div>
  );
}
