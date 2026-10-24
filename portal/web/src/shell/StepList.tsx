import { Link } from "react-router";
import InsetGroup from "./InsetGroup";
import StatusGlyph, { statusName } from "./StatusGlyph";
import type { ShellStep } from "./types";

// The phone's root page: a large title and the steps as a grouped list, each with its state.
export default function StepList({ steps, title, subtitle }: { steps: ShellStep[]; title: string; subtitle?: string }) {
  return (
    <div className="flex flex-col gap-4 px-4 pb-10">
      <div className="flex items-center gap-3 pt-4">
        <img src="/town-seal.png" alt="Town of Newcastle seal" className="size-11" width={44} height={44} />
        <div>
          <h1 tabIndex={-1} data-step-title className="text-[30px] font-bold leading-tight outline-none">{title}</h1>
          {subtitle && <p className="text-[15px] text-[var(--app-secondary-label)]">{subtitle}</p>}
        </div>
      </div>
      <InsetGroup>
        {steps.flatMap((s) => [s, ...(s.children ?? [])]).map((s) => (
          <Link key={s.id} to={s.href} aria-label={`${s.title}, ${statusName(s.status, s.unknowns)}`}
                className="flex min-h-12 items-center gap-3 px-4 text-[17px]">
            <StatusGlyph status={s.status} unknowns={s.unknowns} />
            <span className="flex-1">{s.title}</span>
            <span aria-hidden="true" className="text-[var(--app-tertiary-label)]">›</span>
          </Link>
        ))}
      </InsetGroup>
    </div>
  );
}
