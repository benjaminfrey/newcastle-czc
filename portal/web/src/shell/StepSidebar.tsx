import { useRef, type KeyboardEvent } from "react";
import { Link } from "react-router";
import StatusGlyph, { statusName } from "./StatusGlyph";
import type { ShellStep } from "./types";

type Props = { steps: ShellStep[]; currentId: string | null; title?: string };

// The source list of a macOS settings window: the Town seal, then every step with its state.
// Up and Down move between steps; Enter opens one.
export default function StepSidebar({ steps, currentId, title }: Props) {
  const list = useRef<HTMLUListElement>(null);

  function onKeyDown(e: KeyboardEvent) {
    if (e.key !== "ArrowDown" && e.key !== "ArrowUp") return;
    const links = Array.from(list.current?.querySelectorAll<HTMLAnchorElement>("a") ?? []);
    const at = links.indexOf(document.activeElement as HTMLAnchorElement);
    if (at < 0) return;
    e.preventDefault();
    links[Math.min(links.length - 1, Math.max(0, at + (e.key === "ArrowDown" ? 1 : -1)))].focus();
  }

  const row = (s: ShellStep, nested = false) => (
    <li key={s.id}>
      <Link
        to={s.href}
        aria-label={`${s.title}, ${statusName(s.status, s.unknowns)}`}
        aria-current={s.id === currentId ? "step" : undefined}
        className={`flex min-h-11 items-center gap-3 rounded-lg px-3 text-[15px] outline-none
          focus-visible:ring-2 focus-visible:ring-[var(--app-accent-text)]
          ${nested ? "pl-9 text-[14px]" : ""}
          ${s.id === currentId ? "bg-[var(--app-selection)] font-semibold" : "hover:bg-[var(--app-selection)]/60"}`}
      >
        <StatusGlyph status={s.status} unknowns={s.unknowns} />
        <span className="min-w-0 py-2 leading-snug">{s.title}</span>
      </Link>
      {s.children && s.children.length > 0 && <ul>{s.children.map((c) => row(c, true))}</ul>}
    </li>
  );

  return (
    <nav aria-label="Steps" className="flex h-full flex-col gap-4 px-3 py-4" onKeyDown={onKeyDown}>
      <div className="flex items-center gap-3 px-3">
        <img src="/town-seal.png" alt="Town of Newcastle seal" className="size-10" width={40} height={40} />
        <div className="leading-tight">
          <p className="text-[13px] font-semibold">Town of Newcastle</p>
          {title && <p className="text-[13px] text-[var(--app-secondary-label)]">{title}</p>}
        </div>
      </div>
      <ul ref={list} className="flex flex-col gap-0.5">{steps.map((s) => row(s))}</ul>
    </nav>
  );
}
