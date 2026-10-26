import type { ReactNode } from "react";

// A small rounded label (task-list brief §4.2): Done, "2 of 4", Not started; a project's status;
// "2 things left" in the warning tones (projects brief §3.4).
export type Tone = "done" | "progress" | "todo" | "warn";
const LOOK: Record<Tone, string> = {
  done: "bg-[var(--app-done-bg)] text-[var(--app-done-text)]",
  progress: "bg-[var(--app-selection)] text-[var(--app-accent-text)]",
  todo: "bg-[var(--app-fill)] text-[var(--app-secondary-label)]",
  warn: "bg-[var(--app-warn-bg)] text-[var(--app-warn-text)]",
};

export default function Pill({ tone, children, className }: { tone: Tone; children: ReactNode; className?: string }) {
  return (
    <span data-pill={tone} className={`shrink-0 whitespace-nowrap rounded-full px-[9px] py-[2px] text-[12px] ${LOOK[tone]} ${className ?? ""}`}>
      <span className="sr-only">, </span>{children}
    </span>
  );
}
