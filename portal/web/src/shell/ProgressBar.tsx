// Where you are in a task (task-list brief §4.4): a segment per card, 3 px tall and 3 px apart;
// the answered and current ones in the label colour, the rest in the edge colour.
export default function ProgressBar({ count, at }: { count: number; at: number }) {
  return (
    <div role="img" aria-label={`Question ${at + 1} of ${count}`} className="flex min-w-0 flex-1 gap-[3px]">
      {Array.from({ length: count }, (_, i) => (
        <i key={i} data-seg="" data-on={i <= at ? "" : undefined}
           className={`h-[3px] flex-1 rounded-[2px] ${i <= at ? "bg-[var(--app-label)]" : "bg-[var(--app-edge)]"}`} />
      ))}
    </div>
  );
}
