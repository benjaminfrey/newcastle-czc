import { TextArea, TextField } from "@heroui/react";
import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router";
import { getUseGroups } from "../api";
import { printed } from "../forms/applicability";
import { cardsOf } from "../forms/tasks";
import { itemLabel, type StepModel } from "../forms/steps";
import { longDate, mapLotLabel } from "../format";
import InsetGroup from "../shell/InsetGroup";
import Sheet from "../shell/Sheet";
import { useApplication } from "./ApplicationStore";
import OfficialGroup from "./OfficialGroup";

// Sections the paper form ends with: the signatures and the office's box.
const isClosing = (fields: { source: string }[]) => fields.length > 0 && fields.every((f) => f.source === "at_submit" || f.source === "staff");

// Check and send: the official form section by section, each answer under the question as it was
// asked (the form's term beneath), with Change to that question's screen, which comes back here.
// Add more detail sits on each section. Sending it arrives in Milestone 6.
export default function ReviewPane({ models, base }: { models: StepModel[]; base: string }) {
  const { app, form, cur, saveNote } = useApplication();
  const [useNames, setUseNames] = useState<Record<string, string>>({});
  const [detail, setDetail] = useState<{ sectionId: string; itemId: string | null; title: string; text: string } | null>(null);
  useEffect(() => {
    getUseGroups().then((g) => Array.isArray(g) && setUseNames(Object.fromEntries(g.flatMap((x) => x.uses).map((u) => [u.use_key, u.code_name]))));
  }, []);

  const blocks = useMemo(() => {
    const all = printed(form!, cur!);
    return [...all.filter((b) => !isClosing(b.section.fields)), ...all.filter((b) => isClosing(b.section.fields))];
  }, [form, cur]);
  // The card a question is asked on (a grouped field opens its card), coming back here.
  const screens = useMemo(() => models.flatMap((m) => cardsOf(form!, cur!, m)), [models, form, cur]);
  const changeHref = (fieldId: string, itemId: string | null): string | null => {
    const s = screens.find((x) => x.rows.some((r) => r.field.id === fieldId && r.itemId === itemId));
    if (!s) return null;
    const q = new URLSearchParams({ screen: s.id, ...(s.itemId ? { item: s.itemId } : {}), return: "review" });
    return `${base}/${s.step}?${q.toString().replace(/%3A/g, ":")}`;
  };
  const gaps = app!.missing.map((m) => {
    const sec = form!.sections.find((s) => s.fields.some((f) => f.id === m.field_id))!;
    const field = sec.fields.find((f) => f.id === m.field_id)!;
    const step = field.step ?? sec.step;
    const href = changeHref(m.field_id, m.item_id) ?? `${base}/${step}`;
    return { key: `${m.field_id}|${m.item_id ?? ""}`, question: field.label ?? field.official_label, official: field.official_label,
             href, item: m.item_id ? itemLabel(form!, cur!, m.item_id) : null };
  });

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
      {gaps.length === 0 && (
        <InsetGroup>
          <InsetGroup.Row label="Answers"><span>Everything is answered.</span></InsetGroup.Row>
        </InsetGroup>
      )}
      {gaps.length > 0 && (
        <InsetGroup title="Still to answer" footer="You can come back to these. Staff need them before the application is complete.">
          {gaps.map((g) => (
            // The question as it was asked leads; the form's own term follows, for staff and the printout.
            <Link key={g.key} to={g.href} className="flex min-h-11 flex-col justify-center px-4 py-2">
              <span className="text-[15px] text-[var(--app-accent-text)]">
                {g.item && <span className="text-[var(--app-secondary-label)]">{g.item}: </span>}{g.question}
              </span>
              <span className="text-[13px] text-[var(--app-secondary-label)]"> {g.official}</span>
            </Link>
          ))}
        </InsetGroup>
      )}
      {blocks.map((b) => {
        const title = b.itemId ? `${b.section.official_title} — ${itemLabel(form!, cur!, b.itemId)}` : b.section.official_title;
        const note = app!.notes.find((n) => n.section_id === b.section.id && n.item_id === b.itemId)?.text ?? "";
        return (
          <OfficialGroup key={`${b.section.id}|${b.itemId ?? ""}`} block={b} title={title} note={note}
                         attachments={app!.attachments} useNames={useNames} changeHref={changeHref}
                         onAddDetail={() => setDetail({ sectionId: b.section.id, itemId: b.itemId, title, text: note })} />
        );
      })}
      {/* The end of the page says where things stand: saved, not yet sent, and how to come back. */}
      <InsetGroup title="What happens next">
        <InsetGroup.Row label="Saved">
          <span>Your application is saved. You can close it and come back any time from My applications.</span>
        </InsetGroup.Row>
        <InsetGroup.Row label="Sending it">
          <span>Signing it and sending it to the Town arrives soon. Nothing has gone to the Town yet.</span>
        </InsetGroup.Row>
      </InsetGroup>
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
