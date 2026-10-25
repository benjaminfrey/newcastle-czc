import { Link } from "react-router";
import Icon from "../controls/Icon";
import { mapLotLabel } from "../format";
import { TASK_HINTS, TASK_ICONS, type TaskStatus } from "../forms/tasks";
import { commitFocused } from "./commitFocused";
import { SaveStatus } from "./SaveStatus";
import type { SaveState } from "./types";

export type TaskRow = { id: string; title: string; href: string; status: TaskStatus; current?: boolean };

// The pill on a task's row (task-list brief §4.2): Done, "2 of 4", Not started. A row's name is
// its own words, so what a screen reader says is what the row shows: "Your lot, Size, frontage and
// what is there now, Done"; "The work, 2 of 4 answered".
function Pill({ status }: { status: TaskStatus }) {
  const [words, look] = status.kind === "done" ? ["Done", "bg-[var(--app-done-bg)] text-[var(--app-done-text)]"]
    : status.kind === "progress" ? [`${status.answered} of ${status.total}`, "bg-[var(--app-selection)] text-[var(--app-accent-text)]"]
    : ["Not started", "bg-[var(--app-fill)] text-[var(--app-secondary-label)]"];
  return (
    <span data-pill={status.kind} className={`shrink-0 whitespace-nowrap rounded-full px-[9px] py-[2px] text-[12px] ${look}`}>
      <span className="sr-only">, </span>{words}{status.kind === "progress" && <span className="sr-only"> answered</span>}
    </span>
  );
}

const rowCls = "flex min-h-11 items-center gap-3 px-4 py-[11px] text-[14px] outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-[var(--app-accent-text)]";

function Words({ id, title, hint, muted }: { id: string; title: string; hint?: string; muted?: boolean }) {
  return (
    <>
      <Icon name={TASK_ICONS[id] ?? "dots"} className={muted ? "text-[var(--app-secondary-label)]" : "text-[var(--app-label)]"} />
      <span className="min-w-0 flex-1">
        <span className={`block ${muted ? "text-[var(--app-secondary-label)]" : "text-[var(--app-label)]"}`}>{title}</span>
        {hint && <span className="block text-[12px] text-[var(--app-secondary-label)]"><span className="sr-only">, </span>{hint}</span>}
      </span>
    </>
  );
}

// The application as a short list of tasks, each row a link with its status; "Check and send"
// last, closed until every task is done. As a card on its own (a phone's home, a desktop's first
// view), or `compact` in the desktop's sidebar, the task you're in marked.
export default function TaskList({ formTitle, mapLot, saveState, onReload, tasks, send, compact }: {
  formTitle: string; mapLot: string | null; saveState: SaveState; onReload?: () => void;
  tasks: TaskRow[]; send: { href: string; open: boolean }; compact?: boolean;
}) {
  const sep = compact ? "" : "border-t-[0.5px] border-[var(--app-separator)] first:border-t-0";
  const rows = (
    <ul className={compact ? "flex flex-col gap-0.5" : ""}>
      {tasks.map((t) => (
        <li key={t.id} className={sep}>
          <Link to={t.href} onClick={commitFocused}
                aria-current={t.current ? "step" : undefined}
                className={`${rowCls} ${compact ? "rounded-lg" : ""} ${t.current ? "bg-[var(--app-selection)]" : compact ? "hover:bg-[var(--app-selection)]/60" : ""}`}>
            <Words id={t.id} title={t.title} hint={TASK_HINTS[t.id]} />
            <Pill status={t.status} />
          </Link>
        </li>
      ))}
      <li className={sep}>
        {send.open ? (
          <Link to={send.href} onClick={commitFocused} className={`${rowCls} ${compact ? "rounded-lg" : ""}`}>
            <Words id="review" title="Check and send" />
          </Link>
        ) : (
          <div className={rowCls}><Words id="review" title="Check and send" hint="Opens when the tasks above are done" muted /></div>
        )}
      </li>
    </ul>
  );
  if (compact) return rows;
  return (
    <section className="mx-auto w-full max-w-[640px] overflow-hidden rounded-[12px] border-[0.5px] border-[var(--app-separator)] bg-[var(--app-row)]">
      <div className="flex items-center gap-[10px] border-b-[0.5px] border-[var(--app-separator)] px-4 py-[10px]">
        <h1 className="min-w-0 truncate text-[15px] font-medium text-[var(--app-label)]">{formTitle}</h1>
        <span className="ml-auto flex shrink-0 items-center gap-1 text-[13px] text-[var(--app-secondary-label)]">
          {mapLot && <span>{mapLotLabel(mapLot)}{saveState !== "idle" ? " ·" : ""}</span>}
          <SaveStatus state={saveState} onReload={onReload} />
        </span>
      </div>
      {rows}
    </section>
  );
}
