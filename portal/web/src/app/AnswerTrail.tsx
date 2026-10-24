export type Chip = { id: string; text: string; carried: boolean };

// The answers given so far in this section (or this building), as chips above the question; a tap
// goes back to that question. An answer carried from "Do I need a permit?" has a dashed edge.
export default function AnswerTrail({ chips, onGo }: { chips: Chip[]; onGo: (id: string) => void }) {
  return (
    <div aria-label="Your answers" role="group"
         className="flex min-h-11 flex-wrap items-center gap-1.5 border-b border-[var(--app-separator)] px-5 py-2.5">
      {chips.length === 0 && <span className="text-[13px] text-[var(--app-secondary-label)]">Your answers appear here as you go</span>}
      {chips.map((c) => (
        <button key={c.id} type="button" onClick={() => onGo(c.id)} data-carried={c.carried ? "true" : undefined}
                aria-label={`${c.text}${c.carried ? ", from your answers at the start" : ""}. Change it`}
                className={`max-w-full truncate rounded-full border bg-[var(--app-row)] px-3 py-1 text-[13px] outline-none
                  focus-visible:ring-2 focus-visible:ring-[var(--app-accent-text)]
                  ${c.carried ? "border-dashed border-[var(--app-tertiary-label)]" : "border-[var(--app-separator)]"}`}>
          {c.text}
        </button>
      ))}
    </div>
  );
}
