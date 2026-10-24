import { Button } from "@heroui/react";
import { mapLotLabel } from "../format";
import type { Attachment, FormField } from "../applications";
import type { Block } from "../forms/applicability";
import InsetGroup from "../shell/InsetGroup";

const isUnknown = (v: unknown) => typeof v === "object" && v !== null && (v as { unknown?: unknown }).unknown === true;

// How a value prints on the official form: the Code's own terms, never the plain wording.
export function display(field: FormField, value: unknown, useNames: Record<string, string>): string {
  if (isUnknown(value)) return "Not known yet — staff will follow up";
  if (value === null || value === undefined || value === "" || (Array.isArray(value) && value.length === 0)) {
    if (field.source === "at_submit") return "Signed when you submit";
    if (field.source === "staff") return "Office use";
    if (field.source === "question" || field.may_correct) return "Not answered yet";
    return "Staff will fill this in";
  }
  if (typeof value === "boolean") return value ? "Yes" : "No";
  if (field.type === "choice") return field.options.find((o) => o.value === value)?.official ?? String(value);
  if (field.type === "multichoice" && Array.isArray(value)) {
    return value.map((v) => field.options.find((o) => o.value === v)?.official ?? v).join("; ");
  }
  if (field.type === "uses" && Array.isArray(value)) return value.map((k) => useNames[k] ?? k).join("; ");
  if (field.type === "point" && typeof value === "object") {
    const p = value as { lon: number; lat: number };
    return `Marked on the map (${p.lat.toFixed(5)}, ${p.lon.toFixed(5)})`;
  }
  if (field.from === "map_lot" && typeof value === "string") return mapLotLabel(value);
  if (typeof value === "number") return `${value.toLocaleString("en-US")}${field.unit ? ` ${field.unit}` : ""}`;
  return String(value);
}

const fromMaps = (f: FormField) => f.source === "property" || (f.source === "derived" && f.from === "map_lot");

type Props = {
  block: Block; title: string; note: string; attachments: Attachment[]; useNames: Record<string, string>;
  onEdit?: () => void; onAddDetail: () => void;
};

// One section of the official form as it will print: the Code's labels and the answers, then
// the applicant's added detail. Edit opens the step it's asked in.
export default function OfficialGroup({ block, title, note, attachments, useNames, onEdit, onAddDetail }: Props) {
  const files = (f: FormField) => attachments.filter((a) => a.field_id === f.id && a.item_id === block.itemId);
  return (
    <InsetGroup title={title}
                footer={
                  <span className="flex flex-wrap gap-x-4">
                    {onEdit && <Button variant="ghost" className="min-h-11 px-0 text-[var(--app-accent-text)]" onPress={onEdit} aria-label={`Edit ${title}`}>Edit</Button>}
                    <Button variant="ghost" className="min-h-11 px-0 text-[var(--app-accent-text)]" onPress={onAddDetail}
                            aria-label={`${note ? "Change the detail for" : "Add more detail to"} ${title}`}>
                      {note ? "Change the detail" : "Add more detail"}
                    </Button>
                  </span>
                }>
      {block.rows.map(({ field, value }) => (
        <InsetGroup.Row key={field.id} label={<span className="text-[var(--app-secondary-label)]">{field.official_label}</span>}>
          {field.type === "upload" && files(field).length > 0 ? (
            <span className="flex flex-col">
              {files(field).map((a) => <a key={a.id} className="underline" href={`/api/attachments/${a.id}`}>{a.filename}</a>)}
            </span>
          ) : (
            <span>
              <span>{field.type === "upload" ? "None added" : display(field, value, useNames)}</span>
              {fromMaps(field) && value !== null && <span className="text-[13px] text-[var(--app-secondary-label)]"> (from the Town's maps — staff confirm)</span>}
            </span>
          )}
        </InsetGroup.Row>
      ))}
      {note && (
        <InsetGroup.Row label={<span className="text-[var(--app-secondary-label)]">More detail</span>}>
          <p className="whitespace-pre-line">{note}</p>
        </InsetGroup.Row>
      )}
    </InsetGroup>
  );
}
