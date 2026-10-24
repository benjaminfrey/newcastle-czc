import {
  Description, Input, Label, ListBox, NumberField, Radio, RadioGroup, Select, Slider, Switch, Tag, TagGroup, TextArea,
  TextField, ToggleButton, ToggleButtonGroup,
} from "@heroui/react";
import { useEffect, useState } from "react";
import type { FormField } from "../applications";
import RoofGlyph from "./RoofGlyph";

export type ControlProps = { field: FormField; value: unknown; onValue: (v: unknown) => void; labelId: string; inputId: string };

const isUnknown = (v: unknown) => typeof v === "object" && v !== null && (v as { unknown?: unknown }).unknown === true;
const label = (f: FormField) => f.label ?? f.official_label;

// Typed text keeps a draft and saves when the field is left (blur), trimmed; blank clears.
export function TextControl({ field, value, onValue, inputId, long }: ControlProps & { long?: boolean }) {
  const [draft, setDraft] = useState(typeof value === "string" ? value : "");
  useEffect(() => setDraft(typeof value === "string" ? value : ""), [value]);
  const commit = () => {
    const v = draft.trim();
    if (v !== (typeof value === "string" ? value : "")) onValue(v === "" ? null : v);
  };
  return (
    <TextField value={draft} onChange={setDraft} onBlur={commit} aria-label={label(field)} className="w-full">
      {long ? <TextArea id={inputId} rows={4} /> : <Input id={inputId} autoComplete={field.autocomplete ?? undefined} />}
    </TextField>
  );
}

// Numbers: a field with a unit after it; with `stepper`, − and + buttons as well.
export function NumberControl({ field, value, onValue, stepper }: ControlProps & { stepper?: boolean }) {
  const n = typeof value === "number" ? value : NaN;
  return (
    <div className="flex items-center gap-2">
      <NumberField
        value={n}
        onChange={(v) => onValue(Number.isNaN(v) ? null : v)}
        minValue={field.min ?? undefined}
        maxValue={field.max ?? undefined}
        step={field.step_size ?? (stepper ? 1 : undefined)}
        formatOptions={{ maximumFractionDigits: 2, useGrouping: false }}
        aria-label={label(field)}
        className={stepper ? "w-40" : "w-36"}
      >
        <NumberField.Group className="min-h-11">
          {stepper && <NumberField.DecrementButton className="min-h-11 min-w-11" />}
          <NumberField.Input className="text-right" />
          {stepper && <NumberField.IncrementButton className="min-h-11 min-w-11" />}
        </NumberField.Group>
      </NumberField>
      {field.unit && <span className="text-[var(--app-secondary-label)]">{field.unit}</span>}
    </div>
  );
}

// A slider for a share or an angle, with the value written beside it.
export function SliderControl({ field, value, onValue }: ControlProps) {
  const min = field.min ?? 0;
  const max = field.max ?? 100;
  const [v, setV] = useState(typeof value === "number" ? value : min);
  useEffect(() => { if (typeof value === "number") setV(value); }, [value]);
  // The spoken value comes from the number format: "20%", "45°".
  const format: Intl.NumberFormatOptions | undefined = field.unit === "%" ? { style: "unit", unit: "percent" }
    : field.unit === "degrees" ? { style: "unit", unit: "degree" } : undefined;
  return (
    <Slider
      value={v}
      onChange={(x) => setV(x as number)}
      onChangeEnd={(x) => onValue(x as number)}
      minValue={min}
      maxValue={max}
      step={field.step_size ?? 1}
      aria-label={label(field)}
      formatOptions={format}
      className="w-full"
    >
      <div className="flex justify-end"><Slider.Output className="text-[15px] tabular-nums" /></div>
      <Slider.Track className="min-h-11"><Slider.Fill /><Slider.Thumb /></Slider.Track>
    </Slider>
  );
}

export function SwitchControl({ field, value, onValue }: ControlProps) {
  return (
    <Switch isSelected={value === true} onChange={(on) => onValue(on)} className="min-h-11">
      <Switch.Control><Switch.Thumb /></Switch.Control>
      <Switch.Content className="sr-only">{label(field)}</Switch.Content>
    </Switch>
  );
}

// Two to four choices side by side; a yes/no question shows Yes and No, neither picked until answered.
export function SegmentedControl({ field, value, onValue }: ControlProps) {
  const options = field.type === "yesno"
    ? [{ value: "yes", label: "Yes" }, { value: "no", label: "No" }]
    : field.options.map((o) => ({ value: o.value, label: o.label }));
  const current = field.type === "yesno" ? (value === true ? "yes" : value === false ? "no" : null) : (typeof value === "string" ? value : null);
  return (
    <RadioGroup value={current} onChange={(v) => onValue(field.type === "yesno" ? v === "yes" : v)}
                aria-label={label(field)} orientation="horizontal" className="flex flex-wrap gap-2">
      {options.map((o) => (
        <Radio key={o.value} value={o.value}
               className="min-h-11 rounded-lg border border-[var(--app-separator)] px-4 data-[selected]:border-[var(--app-accent)] data-[selected]:bg-[var(--app-selection)]">
          <Radio.Content><Radio.Control className="sr-only"><Radio.Indicator /></Radio.Control>{o.label}</Radio.Content>
        </Radio>
      ))}
    </RadioGroup>
  );
}

// Larger choices as tiles; roof styles carry a silhouette.
export function TileControl({ field, value, onValue }: ControlProps) {
  const roof = /roof_style$/.test(field.id);
  return (
    <RadioGroup value={typeof value === "string" ? value : null} onChange={onValue} aria-label={label(field)}
                className="grid grid-cols-1 gap-2 sm:grid-cols-2">
      {field.options.map((o) => (
        <Radio key={o.value} value={o.value}
               className="min-h-14 rounded-xl border border-[var(--app-separator)] bg-[var(--app-row)] px-4 py-3 data-[selected]:border-[var(--app-accent)] data-[selected]:bg-[var(--app-selection)]">
          <Radio.Content className="flex items-center gap-3">
            <Radio.Control className="sr-only"><Radio.Indicator /></Radio.Control>
            {roof && <RoofGlyph kind={o.value} />}
            <span>{o.label}</span>
          </Radio.Content>
        </Radio>
      ))}
    </RadioGroup>
  );
}

export function PickerControl({ field, value, onValue, items }: ControlProps & { items?: { id: string; label: string }[] }) {
  const list = items ?? field.options.map((o) => ({ id: o.value, label: o.label }));
  return (
    <Select selectedKey={typeof value === "string" ? value : null} onSelectionChange={(k) => onValue(String(k))}
            aria-label={label(field)} placeholder="Choose…" className="w-full sm:w-72">
      <Select.Trigger className="min-h-11"><Select.Value /><Select.Indicator /></Select.Trigger>
      <Select.Popover>
        <ListBox>
          {list.map((o) => <ListBox.Item key={o.id} id={o.id} textValue={o.label}>{o.label}</ListBox.Item>)}
        </ListBox>
      </Select.Popover>
    </Select>
  );
}

export function ChipsControl({ field, value, onValue }: ControlProps) {
  const chosen = Array.isArray(value) ? (value as string[]) : [];
  return (
    <TagGroup selectionMode="multiple" selectedKeys={new Set(chosen)} aria-label={label(field)}
              onSelectionChange={(keys) => {
                const next = field.options.map((o) => o.value).filter((v) => (keys as Set<string>).has(v));
                onValue(next.length ? next : null); // nothing chosen is no answer, not an empty list
              }}>
      <TagGroup.List className="flex flex-wrap gap-2">
        {field.options.map((o) => (
          <Tag key={o.value} id={o.value} textValue={o.label}
               className="min-h-11 rounded-full border border-[var(--app-separator)] px-4 data-[selected]:border-[var(--app-accent)] data-[selected]:bg-[var(--app-selection)]">
            {o.label}
          </Tag>
        ))}
      </TagGroup.List>
    </TagGroup>
  );
}

export { isUnknown, Description, Label, ToggleButton, ToggleButtonGroup };
