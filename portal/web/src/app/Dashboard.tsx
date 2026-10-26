import { AlertDialog, Button, Input, TextField } from "@heroui/react";
import { useEffect, useState, type FormEvent } from "react";
import { Link } from "react-router";
import { getUseGroups } from "../api";
import Icon from "../controls/Icon";
import { answerOf, type Current } from "../forms/applicability";
import type { StepModel } from "../forms/steps";
import { itemSummary, type TaskStatus } from "../forms/tasks";
import { longDate, mapLotLabel } from "../format";
import { STATUS_TONE, STATUS_WORDS } from "../pages/Home";
import { getParts, type FormDef, type PartDef, type ProjectState } from "../projects";
import Pill from "../shell/Pill";
import NeedsPanel from "./NeedsPanel";

export const PART_STEPS = ["building", "addition", "renovation", "site", "use", "driveway", "divide", "other"];
const ICONS: Record<string, string> = { the_work: "hammer" };

// A row's one-line summary: a building's size and facing; "2 buildings"; "3 answers to go".
export function partSummary(form: FormDef, cur: Current, m: StepModel): string {
  if (m.hub) {
    const n = m.hub.items.length;
    if (n === 0) return "";
    if (n === 1) return itemSummary(form, cur, m.hub.items[0].id);
    return `${n} ${m.id === "building" ? "buildings" : "additions"}`;
  }
  const gaps = m.rows.filter((r) => r.field.required && [null, undefined, ""].includes(answerOf(cur, r.field.id, r.itemId) as never)).length;
  return gaps ? `${gaps} ${gaps === 1 ? "answer" : "answers"} to go` : "";
}

function StatusPill({ status }: { status: TaskStatus }) {
  if (status.kind === "done") return <Pill tone="done">Done</Pill>;
  if (status.kind === "progress") return <Pill tone="progress">{status.answered} of {status.total}<span className="sr-only"> answered</span></Pill>;
  return <Pill tone="todo">Not started</Pill>;
}

// "2.73 acres · 675 ft on Sheepscot Road"; "461 Sheepscot Road · Rural (D1)".
function lotLines(facts: Record<string, unknown>): string[] {
  const districts = (facts.districts as { name?: string | null; code: string }[] | undefined) ?? [];
  const streets = (facts.streets as { name: string; frontage_ft?: number }[] | undefined) ?? [];
  const where = typeof facts.location === "string" ? facts.location.toLowerCase().replace(/\b\w/g, (c) => c.toUpperCase()) : null;
  const first = [where, districts.map((d) => d.name ?? d.code).join(", ") || null].filter(Boolean).join(" · ");
  const second = [typeof facts.acres === "number" ? `${facts.acres} acres` : null,
                  streets[0]?.frontage_ft ? `${streets[0].frontage_ft} ft on ${streets[0].name}` : null].filter(Boolean).join(" · ");
  return [first, second].filter(Boolean);
}

type Props = {
  project: ProjectState; form: FormDef; cur: Current; models: StepModel[]; statuses: TaskStatus[]; base: string;
  left: number;                         // parts (and About you) with something required still blank
  locked: boolean;
  onAdd: (kind: string) => void; onRemove: (partId: string) => void; onRename: (title: string) => Promise<boolean>;
};

// The project's home (projects brief §3.4): its title and a pill, the parcel, a row per part, the
// parts still to add, and beside them what it needs, who is applying, and Check and send. The
// dashboard is the recap: there is no long review page.
export default function Dashboard({ project, form, cur, models, statuses, base, left, locked, onAdd, onRemove, onRename }: Props) {
  const [parts, setParts] = useState<PartDef[]>([]);
  const [useNames, setUseNames] = useState<Record<string, string>>({});
  const [renaming, setRenaming] = useState<string | null>(null);
  const [removing, setRemoving] = useState<{ id: string; title: string } | null>(null);
  useEffect(() => {
    getParts().then((p) => typeof p !== "string" && setParts(p));
    getUseGroups().then((g) => typeof g !== "string" && setUseNames(Object.fromEntries(
      g.flatMap((x) => x.uses.map((u) => [u.use_key, u.code_name])))));
  }, []);

  const present = new Set(project.items.map((i) => i.kind));
  // About the work and the parts: every step after the cover sheet's two (Your lot, About you).
  const rows = models.filter((m) => m.id !== "your_lot" && m.id !== "about_you");
  const statusOf = (id: string) => statuses[models.findIndex((m) => m.id === id)];
  const iconOf = (id: string) => ICONS[id] ?? parts.find((p) => p.id === id)?.icon ?? "clipboard-list";
  const toAdd = parts.filter((p) => !present.has(p.id));
  const sent = project.status !== "draft";
  const pill = locked ? <Pill tone="progress">{STATUS_WORDS[project.status]}</Pill>
    : left ? <Pill tone="warn">{left} {left === 1 ? "thing" : "things"} left</Pill>
    : sent ? <Pill tone={STATUS_TONE[project.status]}>{STATUS_WORDS[project.status]}</Pill>
    : <Pill tone="done">Ready to send</Pill>;

  async function rename(e: FormEvent) {
    e.preventDefault();
    if (renaming !== null && renaming.trim() && (await onRename(renaming))) setRenaming(null);
  }

  const owner = answerOf(cur, "applicant_is_owner", null);
  const box = "overflow-hidden rounded-[12px] border-[0.5px] border-[var(--app-separator)] bg-[var(--app-row)]";
  const facts = project.property.facts;
  const rowCls = "flex min-h-14 w-full items-center gap-3 px-4 py-[11px] text-left text-[14px] no-underline";

  return (
    <div className="mx-auto grid w-full max-w-[1040px] grid-cols-[minmax(0,1fr)] gap-6 lg:grid-cols-[minmax(0,1fr)_280px]">
      <div className="flex min-w-0 flex-col gap-6">
        <header className="flex flex-col gap-2">
          {renaming === null ? (
            <div className="flex items-start gap-2">
              <h2 className="text-[30px] font-bold leading-tight">{project.title}</h2>
              {!locked && (
                <button type="button" aria-label="Rename the project" onClick={() => setRenaming(project.title)}
                        className="mt-2 flex size-11 shrink-0 items-center justify-center rounded-full text-[var(--app-accent-text)]">
                  <Icon name="pencil" />
                </button>
              )}
            </div>
          ) : (
            <form onSubmit={rename} className="flex items-end gap-2">
              <TextField aria-label="The project's name" value={renaming} onChange={setRenaming} className="flex-1">
                <Input className="min-h-11 text-[17px]" autoFocus />
              </TextField>
              <button type="submit" data-filled="" className="btn btn-filled">Save</button>
              <button type="button" className="btn" onClick={() => setRenaming(null)}>Cancel</button>
            </form>
          )}
          <div className="flex flex-wrap items-center gap-2">
            {pill}
            {sent && project.submitted_at && !locked && (
              <span className="text-[13px] text-[var(--app-secondary-label)]">
                Sent {longDate(project.submitted_at).replace(/, \d{4}$/, "")}. You can still add to your project until the Town locks it for review.
              </span>
            )}
            {locked && <span className="text-[13px] text-[var(--app-secondary-label)]">The Town is reviewing this project; changes go through the Code Enforcement Officer.</span>}
          </div>
        </header>

        <Link to={`${base}/your_lot`} className={`${box} ${rowCls}`}>
          <span className="sr-only">Your lot, </span>
          <Icon name="map-2" className="text-[var(--app-secondary-label)]" />
          <span className="min-w-0 flex-1">
            <span className="block text-[15px] font-semibold text-[var(--app-label)]">{mapLotLabel(project.property.map_lot)}</span>
            {lotLines(facts).map((l) => <span key={l} className="block text-[13px] text-[var(--app-secondary-label)]">{l}</span>)}
          </span>
          {statusOf("your_lot") && <StatusPill status={statusOf("your_lot")} />}
          <Icon name="chevron-right" className="text-[var(--app-tertiary-label)]" />
        </Link>

        <section aria-labelledby="parts-heading" className="flex flex-col gap-2">
          <h2 id="parts-heading" className="px-4 text-[13px] text-[var(--app-secondary-label)]">Your project</h2>
          <ul aria-labelledby="parts-heading" className={box}>
            {rows.map((m, k) => {
              const part = project.items.find((i) => i.kind === m.id);
              const single = part && !m.hub;
              const line = partSummary(form, cur, m);
              return (
                <li key={m.id} className={`flex items-center ${k ? "border-t-[0.5px] border-[var(--app-separator)]" : ""}`}>
                  <Link to={`${base}/${m.id}`} className={`${rowCls} min-w-0 flex-1`}>
                    <Icon name={iconOf(m.id)} className="text-[var(--app-secondary-label)]" />
                    <span className="min-w-0 flex-1">
                      <span className="block text-[15px] text-[var(--app-label)]">{m.title}</span>
                      {line && <span className="block truncate text-[12px] text-[var(--app-secondary-label)]">{line}</span>}
                    </span>
                    <StatusPill status={statusOf(m.id)} />
                    <Icon name="chevron-right" className="text-[var(--app-tertiary-label)]" />
                  </Link>
                  {single && !locked && project.items.length > 1 && (
                    <button type="button" onClick={() => setRemoving({ id: part.id, title: m.title })}
                            className="mr-2 min-h-11 px-2 text-[13px] text-[var(--app-destructive)]">Remove</button>
                  )}
                </li>
              );
            })}
          </ul>
        </section>

        {!locked && toAdd.length > 0 && (
          <section aria-labelledby="add-heading" className="flex flex-col gap-2">
            <h2 id="add-heading" className="px-4 text-[13px] text-[var(--app-secondary-label)]">Add to your project</h2>
            <div className="@container">
              <div className="grid grid-cols-1 gap-2 @[25rem]:grid-cols-2">
                {toAdd.map((p) => (
                  <button key={p.id} type="button" onClick={() => onAdd(p.id)}
                          className="flex min-h-12 items-center gap-[10px] rounded-[8px] border-[0.5px] border-[var(--app-edge)] bg-[var(--app-row)] px-3 py-[10px] text-left text-[14px] text-[var(--app-label)]">
                    <Icon name={p.icon} className="text-[var(--app-secondary-label)]" />
                    <span className="flex-1">{p.label}</span>
                    <Icon name="plus" className="text-[var(--app-accent-text)]" />
                    <span className="sr-only">, add</span>
                  </button>
                ))}
              </div>
            </div>
          </section>
        )}
      </div>

      <aside className="flex min-w-0 flex-col gap-6">
        <NeedsPanel needs={project.needs} base={base} locked={locked} useNames={useNames} />
        <section aria-labelledby="you-heading" className="flex flex-col gap-2">
          <h2 id="you-heading" className="px-4 text-[13px] text-[var(--app-secondary-label)]">You</h2>
          <Link to={`${base}/about_you`} className={`${box} ${rowCls}`}>
            <Icon name="user" className="text-[var(--app-secondary-label)]" />
            <span className="min-w-0 flex-1">
              <span className="block text-[15px] text-[var(--app-label)]">{(cur.account.name as string | null) ?? "Your details"}</span>
              <span className="block truncate text-[13px] text-[var(--app-secondary-label)]">
                {owner === true ? "The owner" : owner === false ? "Helping the owner" : "Owner or helper?"}{cur.account.email ? ` · ${cur.account.email}` : ""}
              </span>
            </span>
            {statusOf("about_you") && <StatusPill status={statusOf("about_you")} />}
            <Icon name="chevron-right" className="text-[var(--app-tertiary-label)]" />
          </Link>
        </section>
        {!locked && <Link to={`${base}/send`} data-filled="" className="btn btn-filled w-full no-underline">Check and send</Link>}
      </aside>

      {removing && (
        <AlertDialog.Backdrop isOpen onOpenChange={(o) => !o && setRemoving(null)}>
          <AlertDialog.Container>
            <AlertDialog.Dialog>
              <AlertDialog.Header><AlertDialog.Heading>Remove {removing.title.toLowerCase()} from your project?</AlertDialog.Heading></AlertDialog.Header>
              <AlertDialog.Body>Its answers are kept, and come back if you add it again.</AlertDialog.Body>
              <AlertDialog.Footer>
                <Button variant="secondary" onPress={() => setRemoving(null)}>Cancel</Button>
                <Button variant="danger" onPress={() => { const id = removing.id; setRemoving(null); onRemove(id); }}>Remove</Button>
              </AlertDialog.Footer>
            </AlertDialog.Dialog>
          </AlertDialog.Container>
        </AlertDialog.Backdrop>
      )}
    </div>
  );
}
