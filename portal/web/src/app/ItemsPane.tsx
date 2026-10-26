// A task's buildings or additions (task-list brief §4.7): one row per item with its summary, Change
// (or Finish while unfinished) and Delete; then Add, Copy Building 1, and Done.
import { AlertDialog, Button } from "@heroui/react";
import { useState } from "react";
import type { FormDef } from "../projects";
import Icon from "../controls/Icon";
import { buildingKind } from "../controls/pickers";
import type { Current } from "../forms/applicability";
import { itemLabel, type StepModel } from "../forms/steps";
import { firstCopySource, itemSummary } from "../forms/tasks";
import Card from "../shell/Card";

const NOUNS: Record<string, { add: string; done: string; none: string; ask: string }> = {
  building: { add: "Add a building", done: "Done with buildings", none: "No buildings", ask: "Are you adding a building?" },
  component: { add: "Add an addition, porch or deck", done: "Done with additions", none: "No additions",
               ask: "Are you adding an addition, a porch or a deck?" },
  addition: { add: "Add an addition, porch or deck", done: "Done with additions", none: "No additions",
               ask: "Are you adding an addition, a porch or a deck?" },
};

// "Building 1 · A home", "Addition 2 · A deck": the item's number and, once known, its type in the
// applicant's words; with the type's icon.
export function itemTitle(form: FormDef, cur: Current, itemId: string): { title: string; icon: string } {
  const base = itemLabel(form, cur, itemId).split(":")[0];
  const kindOf = cur.answers.find((x) => x.item_id === itemId && x.field_id === "building_class")?.value;
  if (typeof kindOf === "string") {
    const k = buildingKind(kindOf);
    if (k) return { title: `${base} · ${k.label}`, icon: k.icon };
  }
  for (const s of form.sections) {
    for (const f of s.fields) {
      if (!f.id.endsWith("_kind") || f.type !== "choice") continue;
      const o = f.options.find((x) => x.value === cur.answers.find((a) => a.item_id === itemId && a.field_id === f.id)?.value);
      if (o) return { title: `${base} · ${o.label}`, icon: o.icon ?? "stairs" };
    }
  }
  return { title: base, icon: base.startsWith("Building") ? "building-cottage" : "stairs" };
}

type Props = {
  form: FormDef; cur: Current; step: StepModel;
  onOpen: (itemId: string, finish: boolean) => void;  // Change: its check page; Finish: its first card still to answer
  onAdd: () => void; onCopy: (sourceId: string) => void; onDelete: (itemId: string) => void; onDone: () => void;
};

export default function ItemsPane({ form, cur, step, onOpen, onAdd, onCopy, onDelete, onDone }: Props) {
  const hub = step.hub!;
  const words = NOUNS[hub.kind] ?? NOUNS.building;
  const [confirm, setConfirm] = useState<{ id: string; title: string } | null>(null);
  const canDelete = hub.items.length > hub.repeat.min;
  // Copy only where the form copies something (buildings; an addition copies nothing).
  const copyable = form.sections.some((s) => s.repeat?.kind === hub.kind && s.fields.some((f) => f.copies));
  const copy = copyable ? firstCopySource(form, cur, hub.kind) : null;
  const full = hub.items.length >= hub.repeat.max;
  const empty = hub.items.length === 0;

  return (
    <Card>
      <Card.Header title={step.title} aside={empty ? undefined : `${hub.items.length} added`} />
      <Card.Scroll>
      <div className="flex flex-col">
        {empty && <p className="px-6 py-6 text-center text-[15px] text-[var(--app-secondary-label)]">{words.ask}</p>}
        {hub.items.map((i, k) => {
          const t = itemTitle(form, cur, i.id);
          const summary = itemSummary(form, cur, i.id);
          const unfinished = /to go$/.test(summary);
          return (
            <div key={i.id} className={`flex items-center gap-3 px-4 py-[11px] text-[14px] ${k ? "border-t-[0.5px] border-[var(--app-separator)]" : ""}`}>
              <Icon name={t.icon} />
              <div className="min-w-0 flex-1">
                <p className="text-[var(--app-label)]">{t.title}</p>
                {summary && <p className="text-[12px] text-[var(--app-secondary-label)]">{summary}</p>}
              </div>
              <button type="button" onClick={() => onOpen(i.id, unfinished)} aria-label={`${unfinished ? "Finish" : "Change"} ${t.title.split(" · ")[0]}`}
                      className="min-h-11 px-1 text-[13px] text-[var(--app-accent-text)] outline-none focus-visible:ring-2 focus-visible:ring-[var(--app-accent-text)]">
                {unfinished ? "Finish" : "Change"}
              </button>
              {canDelete && (
                <button type="button" onClick={() => setConfirm({ id: i.id, title: t.title.split(" · ")[0] })} aria-label={`Delete ${t.title.split(" · ")[0]}`}
                        className="min-h-11 px-1 text-[13px] text-[var(--app-destructive)] outline-none focus-visible:ring-2 focus-visible:ring-[var(--app-accent-text)]">
                  Delete
                </button>
              )}
            </div>
          );
        })}
      </div>
      </Card.Scroll>
      <Card.Footer
        extra={<>
          {!full && <button type="button" className="btn" onClick={onAdd}><Icon name="plus" size={16} />{words.add}</button>}
          {copy && !full && <button type="button" className="btn" onClick={() => onCopy(copy.id)}><Icon name="copy" size={16} />Copy {copy.label}</button>}
        </>}
        next={{ label: empty ? words.none : words.done, onPress: onDone }} />
      {confirm && (
        <AlertDialog.Backdrop isOpen onOpenChange={(o) => !o && setConfirm(null)}>
          <AlertDialog.Container>
            <AlertDialog.Dialog>
              <AlertDialog.Header><AlertDialog.Heading>Delete {confirm.title}?</AlertDialog.Heading></AlertDialog.Header>
              <AlertDialog.Body>Its answers and files leave the application. This can't be undone here.</AlertDialog.Body>
              <AlertDialog.Footer>
                <Button variant="secondary" onPress={() => setConfirm(null)}>Cancel</Button>
                <Button variant="danger" onPress={() => { const id = confirm.id; setConfirm(null); onDelete(id); }}>Delete</Button>
              </AlertDialog.Footer>
            </AlertDialog.Dialog>
          </AlertDialog.Container>
        </AlertDialog.Backdrop>
      )}
    </Card>
  );
}
