import { Link } from "react-router";
import { SaveStatus } from "./Toolbar";
import type { SaveState } from "./types";

type Props = {
  title: string; backHref: string; backLabel: string; saveState: SaveState; onReload?: () => void;
  onBack?: () => void; // the wizard: ‹ Back goes to the previous question, and "Steps" opens the list
};

// A phone navigation bar: ‹ back (to the previous question in the wizard, else to the list of
// steps), the save status, then a large title.
export default function NavBar({ title, backHref, backLabel, saveState, onReload, onBack }: Props) {
  const chevron = <span aria-hidden="true" className="text-[22px] leading-none">‹</span>;
  const look = "flex min-h-11 items-center gap-1 px-2 text-[17px] text-[var(--app-accent-text)]";
  return (
    <div>
      <div className="sticky top-0 z-10 flex min-h-11 items-center justify-between border-b border-[var(--app-separator)] bg-[var(--app-ground)]/95 px-2 backdrop-blur">
        {onBack
          ? <button type="button" onClick={onBack} className={look}>{chevron}Back</button>
          : <Link to={backHref} aria-label={backLabel} className={look}>{chevron}{backLabel}</Link>}
        <div className="flex items-center gap-1 px-2">
          <SaveStatus state={saveState} onReload={onReload} />
          {onBack && <Link to={backHref} className="flex min-h-11 items-center px-2 text-[17px] text-[var(--app-accent-text)]">Steps</Link>}
        </div>
      </div>
      <h1 tabIndex={-1} data-step-title className="px-4 pb-2 pt-3 text-[30px] font-bold leading-tight outline-none">{title}</h1>
    </div>
  );
}
