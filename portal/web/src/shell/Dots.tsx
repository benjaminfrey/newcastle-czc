// Where you are among a section's questions, as Setup Assistant shows it: small plain dots, the
// current one in the label colour. Past twelve, the dots would be noise; it says "13 of 20".
export default function Dots({ count, index }: { count: number; index: number }) {
  if (count > 12) {
    return <span className="text-[13px] tabular-nums text-[var(--app-secondary-label)]">{index + 1} of {count}</span>;
  }
  return (
    <span role="img" aria-label={`Question ${index + 1} of ${count}`} className="flex items-center gap-[7px]">
      {Array.from({ length: count }, (_, i) => (
        <span key={i} data-dot data-current={i === index ? "true" : undefined}
              className={`block size-[7px] rounded-full ${i === index ? "bg-[var(--app-label)]" : "bg-[var(--app-separator)]"}`} />
      ))}
    </span>
  );
}
