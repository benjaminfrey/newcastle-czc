import type { StepStatus } from "./types";

// ○ not started, ◐ started, ✓ done; a dot when answers were left "I don't know yet".
export function statusName(status: StepStatus, unknowns: number): string {
  const base = { todo: "Not started", started: "Started", done: "Done" }[status];
  return unknowns > 0 ? `${base}, with ${unknowns === 1 ? "an answer" : `${unknowns} answers`} to follow up` : base;
}

export default function StatusGlyph({ status, unknowns }: { status: StepStatus; unknowns: number }) {
  return (
    <span className="relative inline-flex size-5 shrink-0 items-center justify-center" aria-hidden="true">
      <svg viewBox="0 0 20 20" className="size-5">
        {status === "done" ? (
          <>
            <circle cx="10" cy="10" r="9" fill="var(--app-accent)" />
            <path d="M6 10.4l2.6 2.6L14 7.6" fill="none" stroke="var(--app-on-accent)" strokeWidth="2"
                  strokeLinecap="round" strokeLinejoin="round" />
          </>
        ) : (
          <>
            <circle cx="10" cy="10" r="8.25" fill="none" stroke="var(--app-tertiary-label)" strokeWidth="1.5" />
            {status === "started" && <path d="M10 1.75a8.25 8.25 0 0 1 0 16.5z" fill="var(--app-accent)" />}
          </>
        )}
      </svg>
      {unknowns > 0 && (
        <span className="absolute -right-0.5 -top-0.5 size-2 rounded-full ring-2 ring-[var(--app-row)]"
              style={{ background: "var(--app-seal)" }} />
      )}
    </span>
  );
}
