// How a value prints on the official form: the Code's own terms, never the plain wording. The
// check pages and the cards' "Is this right?" show values this way.
import { mapLotLabel } from "../format";
import type { FormField } from "../projects";

const isUnknown = (v: unknown) => typeof v === "object" && v !== null && (v as { unknown?: unknown }).unknown === true;

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
