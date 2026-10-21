import { Button, Card, Label, TextArea, TextField } from "@heroui/react";
import { useState } from "react";
import type { Attachment, FormDef, FormField } from "../applications";
import type { Block, Current, Row } from "../forms/applicability";
import { answerOf } from "../forms/applicability";
import { mapLotLabel } from "../format";
import QuestionField, { fromDraft, isUnknown, toDraft, type Draft } from "./QuestionField";

type Props = {
  form: FormDef; block: Block; title: string; cur: Current; questions: Row[];
  note: string; attachments: Attachment[]; useNames: Record<string, string>;
  appId: string; parcelId: number | null; busy: boolean;
  onSave: (changes: { field_id: string; item_id: string | null; value: unknown }[]) => Promise<boolean>;
  onSaveNote: (text: string) => Promise<boolean>;
  onAttachments: (all: Attachment[]) => void;
  onUseName: (key: string, name: string) => void;
};

// How a value prints on the official form: the Code's own terms, never the plain wording.
export function display(field: FormField, value: unknown, attachments: Attachment[], itemId: string | null,
                        useNames: Record<string, string>): string {
  if (field.type === "upload") {
    const files = attachments.filter((a) => a.field_id === field.id && a.item_id === itemId).map((a) => a.filename);
    return files.length ? files.join(", ") : "None added";
  }
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

export default function OfficialSection(p: Props) {
  const { block, title } = p;
  const [editing, setEditing] = useState(false);
  const [drafts, setDrafts] = useState<Record<string, Draft>>({});
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [noting, setNoting] = useState(false);
  const [noteText, setNoteText] = useState(p.note);

  function startEdit() {
    setDrafts(Object.fromEntries(p.questions.map((r) => [r.field.id, toDraft(r.field, answerOf(p.cur, r.field.id, r.itemId))])));
    setErrors({});
    setEditing(true);
  }

  async function save() {
    const changes = [];
    const errs: Record<string, string> = {};
    for (const r of p.questions) {
      if (r.field.type === "upload") continue;
      const out = fromDraft(r.field, drafts[r.field.id] ?? null);
      if ("error" in out) errs[r.field.id] = out.error;
      else if (JSON.stringify(out.value) !== JSON.stringify(answerOf(p.cur, r.field.id, r.itemId))) {
        changes.push({ field_id: r.field.id, item_id: r.itemId, value: out.value });
      }
    }
    setErrors(errs);
    if (Object.keys(errs).length) return;
    if (changes.length === 0 || (await p.onSave(changes))) setEditing(false);
  }

  async function saveNote() {
    if (await p.onSaveNote(noteText)) setNoting(false);
  }

  return (
    <Card role="region" aria-label={title}>
      <Card.Header>
        <h2 className="text-lg font-semibold">{title}</h2>
      </Card.Header>
      <Card.Content className="flex flex-col gap-3">
        {!editing ? (
          <dl className="grid grid-cols-1 gap-x-4 gap-y-1 sm:grid-cols-[minmax(10rem,auto)_1fr]">
            {block.rows.map(({ field, value }) => (
              <div key={field.id} className="contents">
                <dt className="font-semibold">{field.official_label}</dt>
                <dd className="mb-2 sm:mb-0">
                  <span>{display(field, value, p.attachments, block.itemId, p.useNames)}</span>
                  {fromMaps(field) && value !== null && <span className="text-sm"> (from the Town's maps — staff confirm)</span>}
                </dd>
              </div>
            ))}
          </dl>
        ) : (
          <div className="flex flex-col gap-4">
            {p.questions.map((r) => (
              <div key={r.field.id}>
                <QuestionField field={r.field} draft={isUnknown(drafts[r.field.id]) ? null : (drafts[r.field.id] ?? null)}
                               onChange={(d) => setDrafts({ ...drafts, [r.field.id]: d })}
                               appId={p.appId} itemId={r.itemId} parcelId={p.parcelId}
                               attachments={p.attachments} onAttachments={p.onAttachments}
                               useNames={p.useNames} onUseName={p.onUseName} />
                {r.field.allow_unknown && (
                  <Button variant="ghost" size="sm" onPress={() => setDrafts({ ...drafts, [r.field.id]: { unknown: true } })}>
                    I don't know yet
                  </Button>
                )}
                {isUnknown(drafts[r.field.id]) && <p className="text-sm">Not known yet — staff will follow up.</p>}
                {errors[r.field.id] && <p role="alert">{errors[r.field.id]}</p>}
              </div>
            ))}
          </div>
        )}
        {p.note && !noting && (
          <div>
            <p className="font-semibold">More detail</p>
            <p className="whitespace-pre-line">{p.note}</p>
          </div>
        )}
        {noting && (
          <TextField value={noteText} onChange={setNoteText}>
            <Label>More detail for {title}</Label>
            <TextArea rows={4} />
          </TextField>
        )}
      </Card.Content>
      <Card.Footer className="flex flex-wrap gap-2">
        {p.questions.length > 0 && !editing && (
          <Button variant="secondary" onPress={startEdit} aria-label={`Edit ${title}`}>Edit</Button>
        )}
        {editing && (
          <>
            <Button variant="primary" onPress={() => void save()} isDisabled={p.busy} aria-label={`Save ${title}`}>Save</Button>
            <Button variant="ghost" onPress={() => setEditing(false)}>Cancel</Button>
          </>
        )}
        {!noting ? (
          <Button variant="ghost" onPress={() => { setNoteText(p.note); setNoting(true); }} aria-label={`Add more detail to ${title}`}>
            {p.note ? "Change the detail" : "Add more detail"}
          </Button>
        ) : (
          <>
            <Button variant="primary" onPress={() => void saveNote()} isDisabled={p.busy} aria-label={`Save detail for ${title}`}>Save detail</Button>
            <Button variant="ghost" onPress={() => setNoting(false)}>Cancel</Button>
          </>
        )}
      </Card.Footer>
    </Card>
  );
}
