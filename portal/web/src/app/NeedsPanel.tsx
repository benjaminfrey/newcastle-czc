import type { Needs, ReviewNeed } from "../projects";

function Review({ r }: { r: ReviewNeed }) {
  const clock = r.clocks.map((c) => c.due_words ?? c.plain).filter(Boolean) as string[];
  return (
    <li className="flex flex-col gap-0.5 border-t-[0.5px] border-[var(--app-separator)] py-[9px] pl-7 pr-4 text-[14px]">
      <span className="flex items-baseline justify-between gap-3">
        <span className="text-[var(--app-label)]">{r.review_key === "structure" ? "Structure (each new building)" : r.name}</span>
        <span className="shrink-0 text-[13px] text-[var(--app-secondary-label)]">{r.fee_words}</span>
      </span>
      {r.reviewer && <span className="text-[13px] text-[var(--app-secondary-label)]">{r.reviewer}</span>}
      {clock.map((c) => <span key={c} className="text-[13px] text-[var(--app-secondary-label)]">{c}</span>)}
      {r.certainty === "may_need" && (
        <span className="text-[13px] text-[var(--app-secondary-label)]">May be needed — the Code Enforcement Officer confirms</span>
      )}
      {!r.in_portal && (
        <span className="text-[13px] text-[var(--app-secondary-label)]">Not in the portal yet — the Town Office takes this one</span>
      )}
    </li>
  );
}

// What you'll need (projects brief §3.4, §6–§8): each permit with its application fee, its reviews
// with their permit fees, and each review's clock in plain words (or its due date once locked).
export default function NeedsPanel({ needs, useNames }: { needs: Needs | null; useNames?: Record<string, string> }) {
  const box = "overflow-hidden rounded-[12px] border-[0.5px] border-[var(--app-separator)] bg-[var(--app-row)]";
  let body;
  if (!needs || "refused" in needs) {
    body = <p className="px-4 py-[11px] text-[14px] text-[var(--app-secondary-label)]">
      What you'll need shows here once the Town has approved its rules.</p>;
  } else if (needs.town_only) {
    body = <p className="px-4 py-[11px] text-[14px] text-[var(--app-secondary-label)]">
      Only the Town builds on Civic land: Town Meeting votes on it, and no permit application is made through this site.</p>;
  } else if (!needs.permits.length) {
    body = <p className="px-4 py-[11px] text-[14px] text-[var(--app-secondary-label)]">
      Nothing yet. Answer your parts' questions and this fills in.</p>;
  } else {
    body = needs.permits.map((p) => (
      <section key={p.key} aria-label={p.name} className="border-t-[0.5px] border-[var(--app-separator)] first:border-t-0">
        <h3 className="flex items-baseline justify-between gap-3 px-4 py-[11px] text-[15px] font-semibold text-[var(--app-label)]">
          <span>{p.name}</span>
          {p.application_fee_words && p.application_fee !== 0 && (
            <span className="shrink-0 text-[13px] font-normal text-[var(--app-secondary-label)]">
              {p.application_fee === "varies" ? p.application_fee_words : `${p.application_fee_words} when you send`}</span>
          )}
        </h3>
        <ul>{p.reviews.map((r, i) => (
          <Review key={`${r.review_key}|${r.use_key ?? ""}|${r.part_id ?? i}`}
                  r={r.use_key && useNames?.[r.use_key] ? { ...r, name: `${r.name}: ${useNames[r.use_key]}` } : r} />
        ))}</ul>
      </section>
    ));
  }
  return (
    <section aria-labelledby="needs-heading" className="flex flex-col gap-2">
      <h2 id="needs-heading" className="px-4 text-[13px] text-[var(--app-secondary-label)]">What you'll need</h2>
      {needs && !("refused" in needs) && needs.notes.map((n) => (
        <p key={n.text} className="px-4 text-[13px] text-[var(--app-secondary-label)]">{n.text}</p>
      ))}
      <div className={box}>{body}</div>
      {needs && !("refused" in needs) && !needs.town_only && needs.permits.length > 0 && (
        <p className="px-4 text-[13px] text-[var(--app-secondary-label)]">
          {needs.application_fees_vary ? "Some fees are set by the Town Office. " : ""}Permit fees are due before a permit is issued.
        </p>
      )}
    </section>
  );
}
