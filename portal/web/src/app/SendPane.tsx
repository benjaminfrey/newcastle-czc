import { AlertDialog, Button } from "@heroui/react";
import { useState } from "react";
import { Link } from "react-router";
import Icon from "../controls/Icon";
import { valueOf, type Current } from "../forms/applicability";
import type { StepModel } from "../forms/steps";
import { cardsOf, itemSummary } from "../forms/tasks";
import { mapLotLabel } from "../format";
import type { FormDef, ProjectState } from "../projects";
import Card from "../shell/Card";
import type { SendOutcome } from "./ProjectStore";

// The official forms a project fills, by key (the cover sheet prints with each).
const FORM_NAMES: Record<string, string> = {
  small_project_plan: "Small Project Plan Application",
  entrance_permit: "Driveway and Entrance Permit Application",
  use_permit: "Use Permit Application",
};
const money = (n: number) => `$${n.toLocaleString("en-US")}`;
const empty = (v: unknown) => v === null || v === undefined || v === "" || (Array.isArray(v) && v.length === 0);

type Props = {
  project: ProjectState; form: FormDef; cur: Current; models: StepModel[]; base: string;
  onBack: () => void; onSend: () => Promise<SendOutcome>; onSent: () => void;
};

// Check and send (projects brief §3.5): what to finish first, the project at a glance, what's due
// when you send, the official forms, and Send to the Town with its confirmation (§5.3). A short
// screen, not a printout: each form's full content is its printout and its check pages.
export default function SendPane({ project, form, cur, models, base, onBack, onSend, onSent }: Props) {
  const [confirming, setConfirming] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  // Each row (a part, About you, Your lot) with something required still blank, and its first such card.
  const todo = models.flatMap((m) => {
    const card = cardsOf(form, cur, m).find((s) => s.rows.some((r) => r.field.required && r.field.type !== "upload"
      && empty(valueOf(form, r.field, r.itemId, cur))));
    if (!card) return [];
    const q = new URLSearchParams({ screen: card.id, ...(card.itemId ? { item: card.itemId } : {}) });
    return [{ id: m.id, title: m.title, href: `${base}/${m.id}?${q.toString()}` }];
  });
  const needs = project.needs && !("refused" in project.needs) ? project.needs : null;
  const due = needs?.permits.filter((p) => p.application_fee !== null && p.application_fee !== 0) ?? [];
  const printed = Object.keys(project.forms).filter((k) => k in FORM_NAMES);
  const parts = models.filter((m) => m.id !== "your_lot" && m.id !== "about_you");
  const sent = project.status !== "draft";
  const box = "overflow-hidden rounded-[12px] border-[0.5px] border-[var(--app-separator)] bg-[var(--app-row)]";
  const row = "flex min-h-12 items-center gap-3 px-4 py-[11px] text-[14px]";
  const line = (k: number) => (k ? "border-t-[0.5px] border-[var(--app-separator)]" : "");
  const section = (label: string, children: React.ReactNode, foot?: React.ReactNode) => (
    <section aria-label={label} className="flex flex-col gap-2">
      <h2 className="px-4 text-[13px] text-[var(--app-secondary-label)]">{label}</h2>
      <div className={box}>{children}</div>
      {foot && <p className="px-4 text-[13px] text-[var(--app-secondary-label)]">{foot}</p>}
    </section>
  );

  function onPressSend() {
    if (todo.length) return setMessage(`First, finish ${todo[0].title}.`);
    setConfirming(true);
  }
  async function send() {
    setBusy(true);
    const r = await onSend();
    setBusy(false);
    setConfirming(false);
    if (r === "sent") return onSent();
    if (r === "failed") return setMessage("We couldn't send it just now. Please try again in a minute.");
    setMessage("Something still needs an answer. It's listed above.");
  }

  return (
    <Card>
      <Card.Header title="Check and send" />
      <Card.Scroll>
        <div className="flex flex-col gap-6 px-4 py-5 text-left">
          {todo.length > 0 && section(`${todo.length} ${todo.length === 1 ? "thing" : "things"} to finish first`,
            <ul>{todo.map((t, k) => (
              <li key={t.id} className={line(k)}>
                <Link to={t.href} className={`${row} no-underline`}>
                  <span className="flex-1 text-[var(--app-label)]">{t.title}</span>
                  <Icon name="chevron-right" className="text-[var(--app-tertiary-label)]" />
                </Link>
              </li>
            ))}</ul>)}

          {section("Your project at a glance", (
            <ul>
              <li className={row}>
                <Icon name="map-2" className="text-[var(--app-secondary-label)]" />
                <span className="flex-1 text-[var(--app-label)]">{mapLotLabel(project.property.map_lot)}</span>
                <Link to={`${base}/your_lot/check`} className="min-h-11 px-1 pt-3 text-[13px] text-[var(--app-accent-text)]">Change</Link>
              </li>
              <li className={`${row} ${line(1)}`}>
                <Icon name="user" className="text-[var(--app-secondary-label)]" />
                <span className="flex-1 text-[var(--app-label)]">{(cur.account.name as string | null) ?? cur.account.email as string}</span>
                <Link to={`${base}/about_you/check`} className="min-h-11 px-1 pt-3 text-[13px] text-[var(--app-accent-text)]">Change</Link>
              </li>
              {parts.map((m) => (
                <li key={m.id} className={`${row} ${line(1)}`}>
                  <span className="min-w-0 flex-1">
                    <span className="block text-[var(--app-label)]">{m.title}</span>
                    {m.hub && m.hub.items.length === 1 && (
                      <span className="block truncate text-[12px] text-[var(--app-secondary-label)]">{itemSummary(form, cur, m.hub.items[0].id)}</span>
                    )}
                  </span>
                  <Link to={m.hub ? `${base}/${m.id}` : `${base}/${m.id}/check`} aria-label={`Change ${m.title}`}
                        className="min-h-11 px-1 pt-3 text-[13px] text-[var(--app-accent-text)]">Change</Link>
                </li>
              ))}
            </ul>
          ))}

          {section("What's due when you send", (
            <ul>
              {due.map((p, k) => (
                <li key={p.key} className={`${row} ${line(k)} justify-between`}>
                  <span className="text-[var(--app-label)]">{p.name} application fee</span>
                  <span className="text-[var(--app-label)]">{p.application_fee_words}</span>
                </li>
              ))}
              <li className={`${row} ${line(due.length)} justify-between font-semibold`}>
                <span>Total, payable when you send</span>
                <span>{money(needs?.application_fees_total ?? 0)}{needs?.application_fees_vary ? " + set by the Town Office" : ""}</span>
              </li>
            </ul>
          ), "Permit fees are due before a permit is issued.")}

          {printed.length > 0 && section("The official forms", (
            <ul>{printed.map((k, i) => (
              <li key={k} className={`${row} ${line(i)}`}>
                <span className="flex-1 text-[var(--app-label)]">{FORM_NAMES[k]}</span>
                <button type="button" disabled className="btn" aria-describedby="printing-note">View</button>
              </li>
            ))}</ul>
          ), <span id="printing-note">Printing arrives in the next update.</span>)}

          {message && <p role="alert" className="text-[15px] text-[var(--app-destructive)]">{message}</p>}
        </div>
      </Card.Scroll>
      <Card.Footer back={{ label: "Back", onPress: onBack }}
                   next={sent ? null : { label: "Send to the Town", onPress: onPressSend }} />

      {confirming && (
        <AlertDialog.Backdrop isOpen onOpenChange={(o) => !o && setConfirming(false)}>
          <AlertDialog.Container>
            <AlertDialog.Dialog>
              <AlertDialog.Header><AlertDialog.Heading>Send your project to the Town?</AlertDialog.Heading></AlertDialog.Header>
              <AlertDialog.Body>
                <ul className="mb-2">{(needs?.permits ?? []).map((p) => <li key={p.key}>{p.name}</li>)}</ul>
                <p>{money(needs?.application_fees_total ?? 0)} in application fees, payable when you send.</p>
                <p>You can still add to your project until the Town locks it for review.</p>
              </AlertDialog.Body>
              <AlertDialog.Footer>
                <Button variant="secondary" onPress={() => setConfirming(false)}>Cancel</Button>
                <Button variant="primary" isDisabled={busy} onPress={() => void send()}>Send</Button>
              </AlertDialog.Footer>
            </AlertDialog.Dialog>
          </AlertDialog.Container>
        </AlertDialog.Backdrop>
      )}
    </Card>
  );
}
