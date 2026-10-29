import type { ReactNode } from "react";
import { Link, NavLink } from "react-router";
import Icon from "../controls/Icon";
import { commitFocused } from "./commitFocused";
import { SaveStatus } from "./SaveStatus";
import type { SaveState } from "./types";
import { useWideLayout } from "./useWideLayout";

// The project last opened, so the Project tab goes back to it from Home, Messages and You.
const LAST = "portal.lastProject";
export function rememberProject(id: string): void {
  try { localStorage.setItem(LAST, id); } catch { /* blocked storage: the tab goes Home */ }
}
function lastProject(): string | null {
  try { return localStorage.getItem(LAST); } catch { return null; }
}

type Props = {
  title: string;              // the page's name, for its heading (shown on a phone's bar in a card)
  project?: string | null;    // the open project's id
  saveState?: SaveState; onReload?: () => void;
  back?: { href: string; label: string }; // a phone's bar in a card: ‹ Project
  card?: boolean;             // a card fills a phone's screen
  titled?: boolean;           // the page shows its own h1 (the dashboard, Check and send, Home)
  children: ReactNode;
};

const TABS = [
  { to: "/", label: "Home", icon: "home", end: true },
  { to: "project", label: "Project", icon: "clipboard-list", end: false },
  { to: "/messages", label: "Messages", icon: "message", end: true },
  { to: "/you", label: "You", icon: "user", end: true },
] as const;

// The app's window (projects brief §3.4): a desktop sidebar under the Town seal (Home, Project,
// Messages, You); a phone's bottom tab bar with the same four. In a card, a phone's 44 px bar
// carries ‹ Project and the save status, and the card fills the screen above the tab bar.
export default function AppShell({ title, project, saveState, onReload, back, card, titled, children }: Props) {
  const wide = useWideLayout();
  const projectHref = project ? `/projects/${project}` : lastProject() ? `/projects/${lastProject()}` : "/";
  const tabs = TABS.map((t) => ({ ...t, to: t.to === "project" ? projectHref : t.to }));
  const item = (t: (typeof tabs)[number], phone: boolean) => (
    <NavLink key={t.label} to={t.to} end={t.end} onClick={commitFocused}
             className={({ isActive }) => {
               const on = isActive || (t.label === "Project" && !!project);
               return phone
                 ? `flex min-h-12 flex-1 flex-col items-center justify-center gap-0.5 text-[11px] no-underline ${on ? "text-[var(--app-accent-text)]" : "text-[var(--app-secondary-label)]"}`
                 : `flex min-h-11 items-center gap-3 rounded-[8px] px-3 text-[15px] no-underline ${on ? "bg-[var(--app-selection)] font-medium text-[var(--app-label)]" : "text-[var(--app-label)]"}`;
             }}>
      <Icon name={t.icon} size={phone ? 22 : 18} />{t.label}
    </NavLink>
  );

  if (wide) {
    return (
      <div className="grid min-h-dvh grid-cols-[250px_minmax(0,1fr)] bg-[var(--app-grouped-ground)]">
        <aside className="sticky top-0 flex h-dvh flex-col gap-4 border-r-[0.5px] border-[var(--app-separator)] px-[10px] py-4">
          <Link to="/" className="flex items-center gap-3 px-3 no-underline">
            <img src="/town-seal.png" alt="Town of Newcastle seal" className="size-10" width={40} height={40} />
            <span className="min-w-0 leading-tight">
              <span className="block text-[13px] font-semibold text-[var(--app-label)]">Town of Newcastle</span>
              <span className="block text-[13px] text-[var(--app-secondary-label)]">Permits</span>
            </span>
          </Link>
          <nav aria-label="The app" className="flex flex-col gap-0.5">{tabs.map((t) => item(t, false))}</nav>
          {saveState && <div className="mt-auto px-3"><SaveStatus state={saveState} onReload={onReload} /></div>}
        </aside>
        <main className="min-w-0 px-8 pb-8 pt-8">
          {!titled && <h1 className="sr-only">{title}</h1>}
          {children}
        </main>
      </div>
    );
  }

  const bar = "sticky top-0 z-10 flex h-11 items-center justify-between border-b-[0.5px] border-[var(--app-separator)] bg-[var(--app-grouped-ground)]/95 px-2 backdrop-blur";
  return (
    <div className="flex h-dvh flex-col bg-[var(--app-grouped-ground)]">
      {back && (
        <div className={bar}>
          <Link to={back.href} onClick={commitFocused} className="flex min-h-11 items-center gap-1 px-2 text-[17px] text-[var(--app-accent-text)] no-underline">
            <span aria-hidden="true" className="text-[22px] leading-none">‹</span>{back.label}
          </Link>
          {saveState && <span className="px-2"><SaveStatus state={saveState} onReload={onReload} /></span>}
        </div>
      )}
      {!titled && <h1 className="sr-only">{title}</h1>}
      <main className={card ? "flex min-h-0 flex-1 flex-col [&>*]:min-h-0 [&>*]:flex-1" : "min-h-0 flex-1 overflow-y-auto px-4 py-3"}>
        {children}
      </main>
      <nav aria-label="The app" className="flex border-t-[0.5px] border-[var(--app-separator)] bg-[var(--app-grouped-ground)]/95 backdrop-blur"
           style={{ paddingBottom: "env(safe-area-inset-bottom)" }}>
        {tabs.map((t) => item(t, true))}
      </nav>
    </div>
  );
}
