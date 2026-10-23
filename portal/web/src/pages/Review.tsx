import { Button, Card } from "@heroui/react";
import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate, useParams } from "react-router";
import { getMe, getUseGroups, UNREACHABLE } from "../api";
import {
  getApplication, getForm, removeItem, saveAnswers, saveNote, type AppState, type Change, type FormDef, type SaveResult,
} from "../applications";
import OfficialSection from "../components/OfficialSection";
import { applicable, printed, valueOf, type Current } from "../forms/applicability";
import { itemLabel, screenKey } from "../forms/wizard";
import { longDate, mapLotLabel } from "../format";

export default function Review() {
  const { id = "" } = useParams();
  const navigate = useNavigate();
  const [app, setApp] = useState<AppState | null>(null);
  const [form, setForm] = useState<FormDef | null>(null);
  const [email, setEmail] = useState<string | null>(null);
  const [problem, setProblem] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [conflict, setConflict] = useState(false);
  const [busy, setBusy] = useState(false);
  const [newKeys, setNewKeys] = useState<string[]>([]);
  const [useNames, setUseNames] = useState<Record<string, string>>({});

  async function load() {
    const a = await getApplication(id);
    if (a === "signed_out") return navigate("/signin", { replace: true });
    if (a === "not_found") return setProblem("We couldn't find that application.");
    if (typeof a === "string") return setProblem(UNREACHABLE);
    const f = await getForm(a.form_key, a.form_version);
    if (f === "not_approved") return setProblem("This application isn't ready yet. Please contact the Town Office.");
    if (f === "busy") return setProblem("The Town's server is busy. Please wait a minute and reload the page.");
    if (typeof f === "string") return setProblem(UNREACHABLE);
    setApp(a);
    setForm(f);
  }

  useEffect(() => {
    void load();
    getMe().then((m) => m && m !== "unavailable" && setEmail(m.email));
    getUseGroups().then((g) => {
      if (Array.isArray(g)) setUseNames(Object.fromEntries(g.flatMap((x) => x.uses).map((u) => [u.use_key, u.code_name])));
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  const cur: Current | null = useMemo(
    () => app && { answers: app.answers, items: app.items, property: app.property.facts, account: { email } },
    [app, email]);

  function sectionOf(fieldId: string): string {
    return form!.sections.find((s) => s.fields.some((f) => f.id === fieldId))?.id ?? "";
  }

  function handle(r: SaveResult): r is { revision: number; missing: AppState["missing"] } {
    if (r === "signed_out") {
      navigate("/signin");
      return false;
    }
    if (typeof r === "string") {
      setMessage("We couldn't save that — please try again.");
      return false;
    }
    if ("conflict" in r) {
      setConflict(true);
      return false;
    }
    if ("invalid" in r) {
      setMessage("We couldn't use one of those answers. Please check them.");
      return false;
    }
    setMessage(null);
    return true;
  }

  async function onSave(changes: Change[]): Promise<boolean> {
    setBusy(true);
    try {
      const r = await saveAnswers(id, app!.revision, changes);
      if (!handle(r)) return false;
      // Questions the change brings in that have no answer yet, required or not.
      const keyOf = (r: { section: { id: string }; field: { id: string }; itemId: string | null }) =>
        screenKey(r.section.id, r.field.id, r.itemId);
      const before = new Set(applicable(form!, cur!).map(keyOf));
      let answers = app!.answers;
      for (const c of changes) {
        answers = answers.filter((a) => !(a.field_id === c.field_id && a.item_id === c.item_id));
        if (c.value !== null) answers.push({ field_id: c.field_id, item_id: c.item_id, value: c.value });
      }
      setApp({ ...app!, answers, revision: r.revision, missing: r.missing });
      const after: Current = { ...cur!, answers };
      const unanswered = (row: ReturnType<typeof applicable>[number]) => row.field.type === "upload"
        ? !app!.attachments.some((a) => a.field_id === row.field.id && a.item_id === row.itemId)
        : [null, undefined, ""].includes(valueOf(form!, row.field, row.itemId, after) as null)
          || (Array.isArray(valueOf(form!, row.field, row.itemId, after))
              && (valueOf(form!, row.field, row.itemId, after) as unknown[]).length === 0);
      setNewKeys(applicable(form!, after).filter((row) => !before.has(keyOf(row)) && unanswered(row)).map(keyOf));
      return true;
    } finally {
      setBusy(false);
    }
  }

  async function onSaveNote(sectionId: string, itemId: string | null, text: string): Promise<boolean> {
    setBusy(true);
    try {
      const r = await saveNote(id, app!.revision, sectionId, itemId, text);
      if (!handle(r)) return false;
      const notes = app!.notes.filter((n) => !(n.section_id === sectionId && n.item_id === itemId));
      if (text.trim()) notes.push({ section_id: sectionId, item_id: itemId, text: text.trim() });
      setApp({ ...app!, notes, revision: r.revision });
      return true;
    } finally {
      setBusy(false);
    }
  }

  async function onRemove(itemId: string) {
    setBusy(true);
    try {
      if (!handle(await removeItem(id, app!.revision, itemId))) return;
      await load();
    } finally {
      setBusy(false);
    }
  }

  if (problem) return <p role="alert">{problem}</p>;
  if (!app || !form || !cur) return <p>Loading…</p>;

  // A building or component can be removed from its first section, while more than the
  // form's minimum remain.
  const firstOfKind = (sectionId: string) => {
    const s = form.sections.find((x) => x.id === sectionId);
    return !!s?.repeat && form.sections.find((x) => x.repeat?.kind === s.repeat!.kind)?.id === s.id;
  };
  const removable = (sectionId: string) => {
    const s = form.sections.find((x) => x.id === sectionId)!;
    return firstOfKind(sectionId) && app.items.filter((i) => i.kind === s.repeat!.kind).length > s.repeat!.min;
  };

  const questions = applicable(form, cur);
  const blocks = printed(form, cur);
  const missingFields = app.missing.map((m) => {
    const field = form.sections.flatMap((s) => s.fields).find((f) => f.id === m.field_id);
    return { ...m, label: field?.official_label ?? m.field_id, key: screenKey(sectionOf(m.field_id), m.field_id, m.item_id),
             item: m.item_id ? itemLabel(form, cur, m.item_id) : null };
  });

  return (
    <div className="flex flex-col gap-4">
      <h1 className="text-xl font-semibold">{form.official_title}</h1>
      <p>
        {mapLotLabel(app.property.map_lot)}
        {app.property.parcels_as_of && ` · Town maps as of ${longDate(app.property.parcels_as_of)}`}
      </p>
      {!app.property.verified && (
        <p className="font-semibold">Property not verified: you entered it yourself, and staff will check it.</p>
      )}
      <p className="text-sm">
        This is your application as it will print. Use Edit to change answers, or Add more detail to say more about any part.
      </p>
      {conflict && (
        <Card>
          <Card.Header>
            <Card.Title>This application was changed in another tab or window</Card.Title>
            <Card.Description>Load the latest before making more changes.</Card.Description>
          </Card.Header>
          <Card.Footer>
            <Button variant="primary" onPress={() => { setConflict(false); void load(); }}>Load the latest</Button>
          </Card.Footer>
        </Card>
      )}
      {message && <p role="alert">{message}</p>}
      {newKeys.length > 0 && (
        <Card>
          <Card.Header>
            <Card.Title>A few new questions apply</Card.Title>
            <Card.Description>Your change means we need to ask {newKeys.length === 1 ? "one more question" : `${newKeys.length} more questions`}.</Card.Description>
          </Card.Header>
          <Card.Footer>
            <Button variant="primary" onPress={() => navigate(`/applications/${id}?only=${newKeys.join(",")}&s=${newKeys[0]}&back=review`)}>
              Answer them
            </Button>
          </Card.Footer>
        </Card>
      )}
      {missingFields.length > 0 && (
        <Card>
          <Card.Header>
            <Card.Title>Still to answer</Card.Title>
            <Card.Description>You can come back to these. Staff will need them before your application is complete.</Card.Description>
          </Card.Header>
          <Card.Content>
            <ul className="flex flex-col gap-1">
              {missingFields.map((m) => (
                <li key={m.key}>
                  {m.item && <span>{m.item}: </span>}
                  <Link className="underline" to={`/applications/${id}?s=${m.key}&back=review`}>{m.label}</Link>
                </li>
              ))}
            </ul>
          </Card.Content>
        </Card>
      )}
      {blocks.map((b) => {
        const title = b.itemId ? `${b.section.official_title} — ${itemLabel(form, cur, b.itemId)}` : b.section.official_title;
        return (
          <div key={`${b.section.id}|${b.itemId ?? ""}`} className="flex flex-col gap-2">
          {b.itemId && removable(b.section.id) && (
            <div>
              <Button variant="ghost" size="sm" isDisabled={busy} aria-label={`Remove ${title}`}
                      onPress={() => void onRemove(b.itemId!)}>
                Remove this {b.section.repeat!.kind === "building" ? "building" : "addition, porch or deck"}
              </Button>
            </div>
          )}
          <OfficialSection
            key={`${b.section.id}|${b.itemId ?? ""}`} form={form} block={b} title={title} cur={cur}
            questions={questions.filter((q) => q.section.id === b.section.id && q.itemId === b.itemId)}
            note={app.notes.find((n) => n.section_id === b.section.id && n.item_id === b.itemId)?.text ?? ""}
            attachments={app.attachments} useNames={useNames} appId={id} parcelId={app.property.parcel_id} busy={busy}
            onSave={onSave} onSaveNote={(text) => onSaveNote(b.section.id, b.itemId, text)}
            onAttachments={(all) => setApp({ ...app, attachments: all })}
            onUseName={(k, n) => setUseNames({ ...useNames, [k]: n })}
          />
          </div>
        );
      })}
      <Card>
        <Card.Header>
          <Card.Title>Sign and submit</Card.Title>
          <Card.Description>Signing and sending your application to the Town is coming soon. Your answers are saved.</Card.Description>
        </Card.Header>
        <Card.Footer className="flex flex-wrap gap-2">
          <Button variant="primary" isDisabled>Submit (coming soon)</Button>
          <Link className="underline" to={`/applications/${id}`}>Back to the questions</Link>
        </Card.Footer>
      </Card>
    </div>
  );
}
