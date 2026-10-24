import { TextArea, TextField } from "@heroui/react";
import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router";
import { getUseGroups } from "../api";
import { applicable, printed } from "../forms/applicability";
import { itemLabel, type StepModel } from "../forms/steps";
import { longDate, mapLotLabel } from "../format";
import InsetGroup from "../shell/InsetGroup";
import Sheet from "../shell/Sheet";
import { useApplication } from "./ApplicationStore";
import OfficialGroup from "./OfficialGroup";
import StepPane from "./StepPane";

// Sections the paper form ends with: the signatures and the office's box.
const isClosing = (fields: { source: string }[]) => fields.length > 0 && fields.every((f) => f.source === "at_submit" || f.source === "staff");

// Review and sign: the official form as it will print, section by section, each with Edit
// (the step it's asked in, in a sheet) and Add more detail. Sending it arrives in Milestone 6.
export default function ReviewPane({ models, base }: { models: StepModel[]; base: string }) {
  const { app, form, cur, saveNote, flush } = useApplication();
  const [useNames, setUseNames] = useState<Record<string, string>>({});
  const [editing, setEditing] = useState<string | null>(null); // a step id
  const [detail, setDetail] = useState<{ sectionId: string; itemId: string | null; title: string; text: string } | null>(null);
  useEffect(() => {
    getUseGroups().then((g) => Array.isArray(g) && setUseNames(Object.fromEntries(g.flatMap((x) => x.uses).map((u) => [u.use_key, u.code_name]))));
  }, []);

  const blocks = useMemo(() => {
    const all = printed(form!, cur!);
    return [...all.filter((b) => !isClosing(b.section.fields)), ...all.filter((b) => isClosing(b.section.fields))];
  }, [form, cur]);
  const stepOfSection = (id: string) => form!.sections.find((s) => s.id === id)?.step ?? null;
  const gaps = app!.missing.map((m) => {
    const sec = form!.sections.find((s) => s.fields.some((f) => f.id === m.field_id))!;
    const field = sec.fields.find((f) => f.id === m.field_id)!;
    const step = field.step ?? sec.step;
    const href = m.item_id ? `${base}/${step}?item=${m.item_id}&page=${field.page ?? ""}` : `${base}/${step}?focus=${m.field_id}`;
    return { key: `${m.field_id}|${m.item_id ?? ""}`, label: field.official_label, href, item: m.item_id ? itemLabel(form!, cur!, m.item_id) : null };
  });
  const editModel = models.find((m) => m.id === editing);
  const editRows = editModel ? applicable(form!, cur!).filter((r) => (r.field.step ?? r.section.step) === editModel.id) : [];

  return (
    <>
      <InsetGroup>
        <InsetGroup.Row label={form!.official_title}>
          <span>{mapLotLabel(app!.property.map_lot)}{app!.property.parcels_as_of && ` · Town maps as of ${longDate(app!.property.parcels_as_of)}`}</span>
        </InsetGroup.Row>
        {!app!.property.verified && (
          <InsetGroup.Row label="Property not verified"><span>You entered it yourself, and staff will check it.</span></InsetGroup.Row>
        )}
      </InsetGroup>
      {gaps.length > 0 && (
        <InsetGroup title="Still to answer" footer="You can come back to these. Staff need them before the application is complete.">
          {gaps.map((g) => (
            <Link key={g.key} to={g.href} className="flex min-h-11 items-center gap-2 px-4 text-[var(--app-accent-text)]">
              {g.item && <span className="text-[var(--app-secondary-label)]">{g.item}:</span>}{g.label}
            </Link>
          ))}
        </InsetGroup>
      )}
      {blocks.map((b) => {
        const title = b.itemId ? `${b.section.official_title} — ${itemLabel(form!, cur!, b.itemId)}` : b.section.official_title;
        const step = stepOfSection(b.section.id);
        const note = app!.notes.find((n) => n.section_id === b.section.id && n.item_id === b.itemId)?.text ?? "";
        return (
          <OfficialGroup key={`${b.section.id}|${b.itemId ?? ""}`} block={b} title={title} note={note}
                         attachments={app!.attachments} useNames={useNames}
                         onEdit={step && !b.itemId && models.some((m) => m.id === step && m.kind === "fields") ? () => setEditing(step) : undefined}
                         onAddDetail={() => setDetail({ sectionId: b.section.id, itemId: b.itemId, title, text: note })} />
        );
      })}
      <InsetGroup>
        <InsetGroup.Row label="Sign and submit">
          <span>Your application is saved. Signing it and sending it to the Town arrives soon.</span>
        </InsetGroup.Row>
      </InsetGroup>
      {editModel && (
        <Sheet open title={editModel.title} onCancel={() => void flush().then(() => setEditing(null))}
               onDone={() => void flush().then(() => setEditing(null))}>
          <StepPane rows={editRows} sections={editModel.sections} />
        </Sheet>
      )}
      {detail && (
        <Sheet open title="More detail" onCancel={() => setDetail(null)}
               onDone={async () => { if (await saveNote(detail.sectionId, detail.itemId, detail.text)) setDetail(null); }}>
          <TextField value={detail.text} onChange={(text) => setDetail({ ...detail, text })} aria-label={`More detail for ${detail.title}`}>
            <TextArea rows={6} className="w-full" />
          </TextField>
          <p className="text-[13px] text-[var(--app-secondary-label)]">This prints under "{detail.title}" on your application.</p>
        </Sheet>
      )}
    </>
  );
}
