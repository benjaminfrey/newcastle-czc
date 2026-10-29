import { AlertDialog, Button } from "@heroui/react";
import { useState } from "react";
import { Link } from "react-router";
import Icon from "../controls/Icon";
import type { Current } from "../forms/applicability";
import type { StepModel } from "../forms/steps";
import { mapLotLabel } from "../format";
import type { FormDef, ProjectState } from "../projects";
import Card from "../shell/Card";
import { useWideLayout } from "../shell/useWideLayout";
import { partSummary } from "./Dashboard";
import NeedsPanel from "./NeedsPanel";
import type { SendOutcome } from "./ProjectStore";
import { todoRows } from "./todo";

// The official forms a project fills, by key (the cover sheet prints with each).
const FORM_NAMES: Record<string, string> = {
  small_project_plan: "Small Project Plan Application",
  entrance_permit: "Driveway and Entrance Permit Application",
  use_permit: "Use Permit Application",
};
// Each row's tile icon (parts.yaml), and About the work's.
const icons: Record<string, string> = {
  the_work: "hammer", building: "building-cottage", addition: "home-plus", renovation: "paint", site: "shovel",
  use: "building-store", driveway: "road", divide: "layout-grid", other: "help-circle",
};
const money = (n: number) => `$${n.toLocaleString("en-US")}`;

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
  const wide = useWideLayout();

  const todo = todoRows(form, cur, models, base);
  const needs = project.needs && !("refused" in project.needs) ? project.needs : null;
  const printed = Object.keys(project.forms).filter((k) => k in FORM_NAMES);
  // While a building's size isn't known, either plan may apply (the needs say "May be needed").
  const eitherPlan = !!needs?.permits.some((p) => p.reviews.some((r) => r.review_key === "large_project_plan" && r.certainty === "may_need"));
  const formName = (k: string) => (k === "small_project_plan" && eitherPlan ? "Small or Large Project Plan Application" : FORM_NAMES[k]);
  const parts = models.filter((m) => m.id !== "your_lot" && m.id !== "about_you");
  const sent = project.status !== "draft";
  const box = "overflow-hidden rounded-[12px] border-[0.5px] border-[var(--app-separator)] bg-[var(--app-row)]";
  const row = "flex min-h-12 items-center gap-3 px-4 py-1 text-[14px]";
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

  const title = <h1 className="text-[30px] font-bold leading-tight">Check and send</h1>;
  const alert = message && <p role="alert" className="text-[15px] text-[var(--app-destructive)]">{message}</p>;
  const dialog = confirming && (
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
  );

  // Wide (≥ 1024 px): the dashboard's two columns, the fees and Send in the rail, on the first
  // screen. A phone keeps the card, Send pinned in its footer.
  if (wide) {
    return (
      <div className="mx-auto grid w-full max-w-[1040px] grid-cols-[minmax(0,1fr)_280px] gap-6">
        <div className="flex min-w-0 flex-col gap-6">
          <header className="flex flex-col gap-1">
            <Link to={base} className="flex min-h-11 items-center gap-1 self-start text-[15px] text-[var(--app-accent-text)] no-underline">
              <span aria-hidden="true" className="text-[20px] leading-none">‹</span>Your project
            </Link>
            {title}
          </header>
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
                <Link to={`${base}/your_lot/check`} className="flex min-h-11 items-center self-center px-1 text-[13px] text-[var(--app-accent-text)]">Change</Link>
              </li>
              <li className={`${row} ${line(1)}`}>
                <Icon name="user" className="text-[var(--app-secondary-label)]" />
                <span className="flex-1 text-[var(--app-label)]">{(cur.account.name as string | null) ?? cur.account.email as string}</span>
                <Link to={`${base}/about_you/check`} className="flex min-h-11 items-center self-center px-1 text-[13px] text-[var(--app-accent-text)]">Change</Link>
              </li>
              {parts.map((m) => (
                <li key={m.id} className={`${row} ${line(1)}`}>
                  <Icon name={icons[m.id] ?? "clipboard-list"} className="text-[var(--app-secondary-label)]" />
                  <span className="min-w-0 flex-1">
                    <span className="block text-[var(--app-label)]">{m.title}</span>
                    {partSummary(form, cur, m) && (
                      <span className="block truncate text-[12px] text-[var(--app-secondary-label)]">{partSummary(form, cur, m)}</span>
                    )}
                  </span>
                  <Link to={m.hub ? `${base}/${m.id}` : `${base}/${m.id}/check`} aria-label={`Change ${m.title}`}
                        className="flex min-h-11 items-center self-center px-1 text-[13px] text-[var(--app-accent-text)]">Change</Link>
                </li>
              ))}
            </ul>
          ))}

          {printed.length > 0 && section("The official forms", (
            <ul>{printed.map((k, i) => (
              <li key={k} className={`${row} ${line(i)}`}>
                <span className="min-w-0 flex-1">
                  <span className="block text-[var(--app-label)]">{formName(k)}</span>
                  {formName(k) !== FORM_NAMES[k] && (
                    <span className="block text-[12px] text-[var(--app-secondary-label)]">Depends on the building's size</span>
                  )}
                </span>
                <button type="button" disabled className="btn" aria-describedby="printing-note">View</button>
              </li>
            ))}</ul>
          ), <span id="printing-note">Printing arrives in the next update.</span>)}

        </div>
        <aside aria-label="Fees and sending" className="flex min-w-0 flex-col gap-4">
          <NeedsPanel needs={project.needs} base={base} />
          {alert}
          {!sent && (
            <button type="button" data-filled={todo.length ? undefined : ""} className={`btn w-full ${todo.length ? "" : "btn-filled"}`}
                    onClick={onPressSend}>Send to the Town</button>
          )}
        </aside>
        {dialog}
      </div>
    );
  }

  return (
    <Card>
      <Card.Scroll>
        <div className="flex flex-col gap-6 px-4 py-5 text-left">
          {title}
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
                <Link to={`${base}/your_lot/check`} className="flex min-h-11 items-center self-center px-1 text-[13px] text-[var(--app-accent-text)]">Change</Link>
              </li>
              <li className={`${row} ${line(1)}`}>
                <Icon name="user" className="text-[var(--app-secondary-label)]" />
                <span className="flex-1 text-[var(--app-label)]">{(cur.account.name as string | null) ?? cur.account.email as string}</span>
                <Link to={`${base}/about_you/check`} className="flex min-h-11 items-center self-center px-1 text-[13px] text-[var(--app-accent-text)]">Change</Link>
              </li>
              {parts.map((m) => (
                <li key={m.id} className={`${row} ${line(1)}`}>
                  <Icon name={icons[m.id] ?? "clipboard-list"} className="text-[var(--app-secondary-label)]" />
                  <span className="min-w-0 flex-1">
                    <span className="block text-[var(--app-label)]">{m.title}</span>
                    {partSummary(form, cur, m) && (
                      <span className="block truncate text-[12px] text-[var(--app-secondary-label)]">{partSummary(form, cur, m)}</span>
                    )}
                  </span>
                  <Link to={m.hub ? `${base}/${m.id}` : `${base}/${m.id}/check`} aria-label={`Change ${m.title}`}
                        className="flex min-h-11 items-center self-center px-1 text-[13px] text-[var(--app-accent-text)]">Change</Link>
                </li>
              ))}
            </ul>
          ))}

          <NeedsPanel needs={project.needs} base={base} />

          {printed.length > 0 && section("The official forms", (
            <ul>{printed.map((k, i) => (
              <li key={k} className={`${row} ${line(i)}`}>
                <span className="min-w-0 flex-1">
                  <span className="block text-[var(--app-label)]">{formName(k)}</span>
                  {formName(k) !== FORM_NAMES[k] && (
                    <span className="block text-[12px] text-[var(--app-secondary-label)]">Depends on the building's size</span>
                  )}
                </span>
                <button type="button" disabled className="btn" aria-describedby="printing-note">View</button>
              </li>
            ))}</ul>
          ), <span id="printing-note">Printing arrives in the next update.</span>)}

          {alert}
        </div>
      </Card.Scroll>
      <Card.Footer back={{ label: "Back", onPress: onBack }}
                   next={sent ? null : { label: "Send to the Town", onPress: onPressSend, plain: todo.length > 0 }} />
      {dialog}
    </Card>
  );
}
