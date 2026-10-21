import { Button, Checkbox, CheckboxGroup, Description, Input, Label, Radio, RadioGroup, TextArea, TextField } from "@heroui/react";
import type { Attachment, FormField } from "../applications";
import PointField from "./PointField";
import UploadField from "./UploadField";
import UseSearch from "./UseSearch";

// What a question's widget holds while the person is answering: text for text and
// numbers (checked on Next), a list for lists, "yes"/"no" for yes-no questions.
export type Draft = string | string[] | { lon: number; lat: number } | { unknown: true } | null;

export const isUnknown = (d: unknown): d is { unknown: true } =>
  typeof d === "object" && d !== null && !Array.isArray(d) && (d as { unknown?: unknown }).unknown === true;

export function toDraft(field: FormField, value: unknown): Draft {
  if (value === null || value === undefined) return field.type === "multichoice" || field.type === "uses" ? [] : null;
  if (isUnknown(value)) return value;
  if (field.type === "number") return String(value);
  if (field.type === "yesno") return value ? "yes" : "no";
  return value as Draft;
}

const NUMBER = /^-?\d+(\.\d+)?$/;

// The value to save, or a plain message saying what to fix.
export function fromDraft(field: FormField, draft: Draft): { value: unknown } | { error: string } {
  if (draft === null || draft === "" || (Array.isArray(draft) && draft.length === 0 && field.type !== "uses")) return { value: null };
  if (isUnknown(draft)) return { value: draft };
  if (field.type === "number") {
    const text = String(draft).replace(/,/g, "").trim();
    if (!NUMBER.test(text)) return { error: "Please enter a number, using digits, like 24 or 2.5." };
    const n = Number(text);
    if ((field.min !== null && n < field.min) || (field.max !== null && n > field.max)) {
      return { error: `Please enter a number from ${field.min ?? 0} to ${field.max}${field.unit ? ` ${field.unit}` : ""}.` };
    }
    return { value: n };
  }
  if (field.type === "yesno") return { value: draft === "yes" };
  return { value: draft };
}

type Props = {
  field: FormField; draft: Draft; onChange: (d: Draft) => void;
  appId: string; itemId: string | null; parcelId: number | null;
  attachments: Attachment[]; onAttachments: (all: Attachment[]) => void;
  useNames: Record<string, string>; onUseName: (key: string, name: string) => void;
};

function Help({ field }: { field: FormField }) {
  return field.help ? <Description>{field.help}</Description> : null;
}

export default function QuestionField(p: Props) {
  const { field, draft, onChange } = p;
  const label = field.label ?? field.official_label;
  const text = typeof draft === "string" ? draft : "";
  switch (field.type) {
    case "upload":
      return <UploadField appId={p.appId} fieldId={field.id} itemId={p.itemId} label={label}
                          attachments={p.attachments} onChange={p.onAttachments} />;
    case "point":
      return <PointField label={label} parcelId={p.parcelId}
                         value={draft && typeof draft === "object" && "lon" in draft ? draft : null} onChange={onChange} />;
    case "longtext":
      return (
        <TextField value={text} onChange={onChange}>
          <Label>{label}</Label>
          <TextArea rows={5} />
          <Help field={field} />
        </TextField>
      );
    case "number":
      return (
        <TextField value={text} onChange={onChange} inputMode="decimal">
          <Label>{label}</Label>
          <div className="flex items-center gap-2">
            <Input className="max-w-40" />
            {field.unit && <span>{field.unit}</span>}
          </div>
          <Help field={field} />
        </TextField>
      );
    case "choice":
    case "yesno": {
      const options = field.type === "yesno"
        ? [{ value: "yes", label: "Yes" }, { value: "no", label: "No" }] : field.options;
      return (
        <RadioGroup value={text} onChange={onChange} name={field.id}>
          <Label>{label}</Label>
          <Help field={field} />
          {options.map((o) => (
            <Radio key={o.value} value={o.value}>
              <Radio.Content>
                <Radio.Control><Radio.Indicator /></Radio.Control>
                {o.label}
              </Radio.Content>
            </Radio>
          ))}
        </RadioGroup>
      );
    }
    case "multichoice":
      return (
        <CheckboxGroup value={Array.isArray(draft) ? draft : []} onChange={onChange} name={field.id}>
          <Label>{label}</Label>
          <Help field={field} />
          {field.options.map((o) => (
            <Checkbox key={o.value} value={o.value}>
              <Checkbox.Content>
                <Checkbox.Control><Checkbox.Indicator /></Checkbox.Control>
                {o.label}
              </Checkbox.Content>
            </Checkbox>
          ))}
        </CheckboxGroup>
      );
    case "uses": {
      const chosen = Array.isArray(draft) ? draft : [];
      return (
        <div className="flex flex-col gap-3">
          <Label>{label}</Label>
          {field.help && <p className="text-sm">{field.help}</p>}
          {chosen.length > 0 && (
            <ul className="flex flex-col gap-1" aria-label="Uses chosen">
              {chosen.map((k) => (
                <li key={k} className="flex items-center gap-2">
                  <span>{p.useNames[k] ?? k}</span>
                  <Button variant="ghost" size="sm" onPress={() => onChange(chosen.filter((x) => x !== k))}
                          aria-label={`Remove ${p.useNames[k] ?? k}`}>Remove</Button>
                </li>
              ))}
            </ul>
          )}
          <UseSearch chosen={chosen} chooseLabel="Add" onChoose={(k, name) => { p.onUseName(k, name); onChange([...chosen, k]); }} />
        </div>
      );
    }
    case "date":
      return (
        <TextField value={text} onChange={onChange} type="date">
          <Label>{label}</Label>
          <Input />
          <Help field={field} />
        </TextField>
      );
    default:
      return (
        <TextField value={text} onChange={onChange}>
          <Label>{label}</Label>
          <Input />
          <Help field={field} />
        </TextField>
      );
  }
}
