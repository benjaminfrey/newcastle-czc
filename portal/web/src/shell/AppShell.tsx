import type { ReactNode } from "react";
import { Link } from "react-router";
import { commitFocused } from "./commitFocused";
import TaskList, { type TaskRow } from "./TaskList";
import { SaveStatus } from "./SaveStatus";
import type { SaveState } from "./types";
import { useWideLayout } from "./useWideLayout";

type Props = {
  tasks: TaskRow[]; send: { href: string; open: boolean };
  formTitle: string; mapLot: string | null; saveState: SaveState;
  home: string;            // the task list's address
  inTask: boolean;         // a card is showing; otherwise the task list is the page
  onDone: () => void;      // Save and close
  onReload?: () => void;
  children?: ReactNode;    // the card
};

// The application window (task-list brief §4.1).
// - Desktop: the task list in a 250 px sidebar under the Town seal, with Save and close; the
//   card centred in the main area, 32 px from the top.
// - Phone: in a task, a 44 px bar (‹ Tasks, the save status) over the card, which fills the screen
//   in 12 px gutters with its footer at its foot; at home, the task list is the page.
export default function AppShell({ tasks, send, formTitle, mapLot, saveState, home, inTask, onDone, onReload, children }: Props) {
  const wide = useWideLayout();
  const list = (compact: boolean) => (
    <TaskList formTitle={formTitle} mapLot={mapLot} saveState={saveState} onReload={onReload} tasks={tasks} send={send} compact={compact} />
  );

  if (wide) {
    return (
      <div className="grid min-h-dvh grid-cols-[250px_minmax(0,1fr)] bg-[var(--app-grouped-ground)]">
        <aside className="flex flex-col gap-4 border-r-[0.5px] border-[var(--app-separator)] px-[10px] py-4">
          <div className="flex items-center gap-3 px-3">
            <img src="/town-seal.png" alt="Town of Newcastle seal" className="size-10" width={40} height={40} />
            <div className="min-w-0 leading-tight">
              <p className="text-[13px] font-semibold">Town of Newcastle</p>
              <p className="truncate text-[13px] text-[var(--app-secondary-label)]">{formTitle}</p>
            </div>
          </div>
          <nav aria-label="Tasks">{list(true)}</nav>
          <div className="mt-auto flex flex-wrap items-center gap-3 px-3">
            <SaveStatus state={saveState} onReload={onReload} />
            <button type="button" className="btn" onClick={() => { commitFocused(); onDone(); }}>Save and close</button>
          </div>
        </aside>
        <main className="min-w-0 px-8 pb-8 pt-8">
          {inTask ? children : list(false)}
        </main>
      </div>
    );
  }

  const bar = "sticky top-0 z-10 flex h-11 items-center justify-between border-b-[0.5px] border-[var(--app-separator)] bg-[var(--app-grouped-ground)]/95 px-2 backdrop-blur";
  if (!inTask) {
    return (
      <div className="min-h-dvh bg-[var(--app-grouped-ground)]">
        <div className={bar}>
          <button type="button" onClick={onDone} className="flex min-h-11 items-center px-2 text-[17px] text-[var(--app-accent-text)]">Save and close</button>
        </div>
        <main className="p-3">{list(false)}</main>
      </div>
    );
  }
  return (
    <div className="flex h-dvh flex-col bg-[var(--app-grouped-ground)]">
      <div className={bar}>
        <Link to={home} onClick={commitFocused} aria-label="Tasks" className="flex min-h-11 items-center gap-1 px-2 text-[17px] text-[var(--app-accent-text)]">
          <span aria-hidden="true" className="text-[22px] leading-none">‹</span>Tasks
        </Link>
        <span className="px-2"><SaveStatus state={saveState} onReload={onReload} /></span>
      </div>
      <h1 className="sr-only">{formTitle}</h1>
      <main className="flex min-h-0 flex-1 flex-col px-3 pt-3 [&>*]:min-h-0 [&>*]:flex-1"
            style={{ paddingBottom: "max(12px, env(safe-area-inset-bottom))" }}>
        {children}
      </main>
    </div>
  );
}
