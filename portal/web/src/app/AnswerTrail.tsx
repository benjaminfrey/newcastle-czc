import { useEffect, useState } from "react";

export type Chip = { id: string; text: string; carried: boolean };
const SHOWN = 4;

// The answers given so far in this section (or this building), as chips above the question; a tap
// goes back to that question. An answer carried from "Do I need a permit?" has a dashed edge. The
// last four show, so the trail stays one line above the question; the earlier ones are a tap away.
export default function AnswerTrail({ chips, onGo, at }: { chips: Chip[]; onGo: (id: string) => void; at?: string }) {
  const [all, setAll] = useState(false);
  useEffect(() => setAll(false), [at]); // each question starts with the short trail
  const hidden = all ? 0 : Math.max(0, chips.length - SHOWN);
  const chip = "max-w-[18rem] shrink-0 truncate rounded-full border bg-[var(--app-row)] px-3 py-1 text-[13px] outline-none focus-visible:ring-2 focus-visible:ring-[var(--app-accent-text)]";
  return (
    <div aria-label="Your answers" role="group"
         className="flex min-h-11 items-center gap-1.5 overflow-x-auto border-b border-[var(--app-separator)] px-5 py-2.5 sm:flex-wrap sm:overflow-x-visible">
      {chips.length === 0 && <span className="text-[13px] text-[var(--app-secondary-label)]">Your answers appear here as you go</span>}
      {hidden > 0 && (
        <button type="button" onClick={() => setAll(true)} aria-label={`Show ${hidden} earlier answers`}
                className={`${chip} border-[var(--app-separator)] text-[var(--app-secondary-label)]`}>+{hidden}</button>
      )}
      {chips.slice(hidden).map((c) => (
        <button key={c.id} type="button" onClick={() => onGo(c.id)} data-carried={c.carried ? "true" : undefined}
                aria-label={`${c.text}${c.carried ? ", from your answers at the start" : ""}. Change it`}
                className={`${chip} ${c.carried ? "border-dashed border-[var(--app-tertiary-label)]" : "border-[var(--app-separator)]"}`}>
          {c.text}
        </button>
      ))}
    </div>
  );
}
