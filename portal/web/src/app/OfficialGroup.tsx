import { Link } from "react-router";
import { Button } from "@heroui/react";
import { mapLotLabel } from "../format";
import type { Attachment, FormField } from "../applications";
import type { Block } from "../forms/applicability";
import InsetGroup from "../shell/InsetGroup";
import { buildingLabel } from "../controls/pickers";
import { useApplication } from "./ApplicationStore";

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

const asked = (f: FormField) => (f.source === "question" || f.may_correct) && !!f.label;
const unanswered = (v: unknown) => v === null || v === undefined || v === "" || (Array.isArray(v) && v.length === 0);

const fromMaps = (f: FormField) => f.source === "property" || (f.source === "derived" && f.from === "map_lot");

type Props = {
  block: Block; title: string; note: string; attachments: Attachment[]; useNames: Record<string, string>;
  changeHref: (fieldId: string, itemId: string | null) => string | null; onAddDetail: () => void;
};

// One section of the official form: each answer under the question as it was asked, with the
// form's own term beneath for staff (the printout keeps the form's labels), then the applicant's
// added detail. Change opens that question's screen.
export default function OfficialGroup({ block, title, note, attachments, useNames, changeHref, onAddDetail }: Props) {
  const files = (f: FormField) => attachments.filter((a) => a.field_id === f.id && a.item_id === block.itemId);
  const { cur, form } = useApplication();
  // The Town's map had a value for this field (a lot with no address on the map has none to change).
  const mapKnew = (f: FormField) => {
    const v = f.from ? (cur!.property as Record<string, unknown>)[f.from] : null;
    return f.source !== "property" || (Array.isArray(v) ? v.length > 0 : v !== null && v !== undefined && v !== "");
  };
  const changed = (fieldId: string) => cur!.answers.some((a) => a.field_id === fieldId && a.item_id === block.itemId);
  return (
    <InsetGroup title={title}
                footer={
                  <span className="flex flex-wrap gap-x-4">
                    <Button variant="ghost" className="min-h-11 px-0 text-[var(--app-accent-text)]" onPress={onAddDetail}
                            aria-label={`${note ? "Change the detail for" : "Add more detail to"} ${title}`}>
                      {note ? "Change the detail" : "Add more detail"}
                    </Button>
                  </span>
                }>
      {block.rows.map(({ field, value: stored }) => {
        // "Attached to" stores the building; print its name as it is now.
        const value = field.control === "building-picker" && typeof stored === "string" ? buildingLabel(form!, cur!, stored) : stored;
        return (
        <InsetGroup.Row key={field.id} label={asked(field) ? (
          <span className="flex flex-col">
            <span>{field.label}</span>
            <span className="text-[13px] text-[var(--app-secondary-label)]">{field.official_label}</span>
          </span>
        ) : <span className="text-[var(--app-secondary-label)]">{field.official_label}</span>}>
          {field.type === "upload" && files(field).length > 0 ? (
            <span className="flex flex-col">
              {files(field).map((a) => <a key={a.id} className="underline" href={`/api/attachments/${a.id}`}>{a.filename}</a>)}
            </span>
          ) : (
            <span className="flex flex-wrap items-baseline justify-between gap-x-3">
              <span>
              {asked(field) && field.type !== "upload" && unanswered(value)
                ? (field.required
                    ? <span className="text-[var(--app-destructive)]">Still to answer</span>
                    : <span className="text-[var(--app-secondary-label)]">Not answered</span>)
                : <span>{field.type === "upload" ? "None added" : display(field, value, useNames)}</span>}
              {fromMaps(field) && value !== null && (mapKnew(field) || !changed(field.id)) && (
                // A map value the applicant corrected is theirs, not the Town's: say which, for staff.
                <span className="text-[13px] text-[var(--app-secondary-label)]">
                  {changed(field.id) ? " (you changed the map's value — staff confirm)" : " (from the Town's maps — staff confirm)"}
                </span>
              )}
              </span>
              {asked(field) && changeHref(field.id, block.itemId) && (
                <Link to={changeHref(field.id, block.itemId)!} aria-label={`Change ${field.label}`}
                      className="min-h-11 py-2 text-[15px] text-[var(--app-accent-text)]">Change</Link>
              )}
            </span>
          )}
        </InsetGroup.Row>
        );
      })}
      {note && (
        <InsetGroup.Row label={<span className="text-[var(--app-secondary-label)]">More detail</span>}>
          <p className="whitespace-pre-line">{note}</p>
        </InsetGroup.Row>
      )}
    </InsetGroup>
  );
}
