import { Link } from "react-router";
import type { Needs, ReviewNeed } from "../projects";

// What settles a fee that may apply: the answer still missing, in the applicant's words.
const SETTLES: Record<string, string> = {
  floor_area: "the floor area", added_floor_area: "the addition's floor area",
  renovation_total_floor_area: "the building's floor area", parking_spaces: "the number of parking spaces",
  lots_after: "the number of lots", divided_last_5_years: "whether the land was divided recently",
  homes_last_5_years: "the homes added before", dwelling_units: "the number of homes",
};
const PLANS = ["small_project_plan", "large_project_plan"];
const money = (n: number) => `$${n.toLocaleString("en-US")}`;

type Line = { key: string; name: string; sub?: string; amount: string; plan?: boolean;
  settle?: { href: string; words: string } };

// The receipt's lines before the permit is issued: each review the project needs at its permit fee
// (Structure once per new building, counted together); a review that may apply at $0, with the
// answer that settles it — never a range (the chair's ruling, 2026-10-26).
function laterLines(needs: Exclude<Needs, { refused: string }>, base: string, useNames: Record<string, string>): Line[] {
  const all = needs.permits.flatMap((p) => p.reviews);
  const lines: Line[] = [];
  const structures = all.filter((r) => r.review_key === "structure");
  if (structures.length) {
    const n = structures.length, fee = structures[0].fee;
    lines.push({ key: "structure", name: "Structure", sub: `${n} new ${n === 1 ? "building" : "buildings"}`,
                 amount: typeof fee === "number" ? money(fee * n) : structures[0].fee_words });
  }
  for (const r of all) {
    if (r.review_key === "structure") continue;
    const name = r.use_key && useNames[r.use_key] ? `${r.name}: ${useNames[r.use_key]}` : r.name;
    if (r.certainty === "may_need") {
      const s = r.settled_by;
      const key = `may|${s ? `${s.step}|${s.field_id}|${s.part_id ?? ""}` : r.review_key}`;
      const plan = PLANS.includes(r.review_key);
      // Small and Large Project Plan, both waiting on the same answer, are one line.
      const twin = plan && lines.find((l) => l.key === key && l.plan);
      if (twin) { twin.name = "Project Plan"; continue; }
      lines.push({ key, name, amount: "$0", plan, settle: s ? {
        href: `${base}/${s.step}?focus=${s.field_id}${s.part_id ? `&item=${s.part_id}` : ""}`,
        words: `Add ${SETTLES[s.field_id] ?? "the missing answer"} to see this fee` } : undefined });
      continue;
    }
    lines.push({ key: `${r.review_key}|${r.use_key ?? ""}`, name,
                 sub: r.review_key === "entrance_permit" ? "driveway" : !r.in_portal ? "the Town Office takes this one" : undefined,
                 amount: typeof r.fee === "number" ? money(r.fee) : r.fee_words });
  }
  return lines;
}

function Row({ l }: { l: Line }) {
  return (
    <li className="flex justify-between gap-3 px-4 py-[5px] text-[14px]">
      <span className="min-w-0">
        <span className="block text-[var(--app-label)]">{l.name}</span>
        {l.sub && <span className="block text-[12px] text-[var(--app-secondary-label)]">{l.sub}</span>}
        {l.settle && <Link to={l.settle.href} className="block text-[12px] text-[var(--app-accent-text)]">{l.settle.words}</Link>}
      </span>
      <span className="shrink-0 tabular-nums text-[var(--app-label)]">{l.amount}</span>
    </li>
  );
}

function Group({ title, lines, subtotal }: { title: string; lines: Line[]; subtotal: number }) {
  return (
    <div role="group" aria-label={title}>
      <h3 className="px-4 pb-1 pt-[10px] text-[12px] font-normal text-[var(--app-secondary-label)]">{title}</h3>
      <ul>{lines.map((l) => <Row key={l.key} l={l} />)}</ul>
      <p className="flex justify-between border-b-[0.5px] border-dashed border-[var(--app-edge)] px-4 pb-[10px] pt-[6px] text-[13px] text-[var(--app-secondary-label)]">
        <span>Subtotal</span><span className="tabular-nums">{money(subtotal)}</span>
      </p>
    </div>
  );
}

function Details({ reviews }: { reviews: ReviewNeed[] }) {
  return (
    <details className="px-4 text-[13px] text-[var(--app-secondary-label)]">
      <summary className="min-h-11 cursor-pointer py-3 text-[var(--app-accent-text)]">Who reviews it, and how long</summary>
      <ul className="flex flex-col gap-3 pb-3">
        {reviews.filter((r) => r.reviewer).map((r) => (
          <li key={`${r.review_key}|${r.use_key ?? ""}`} className="flex flex-col gap-0.5">
            <span className="text-[var(--app-label)]">{r.name}</span>
            <span>{r.reviewer}</span>
            {r.clocks.map((c) => <span key={c.key}>{c.due_words ? `${c.plain ?? c.label} ${c.due_words}.` : c.plain}</span>)}
            {r.certainty === "may_need" && <span>May be needed — the Code Enforcement Officer confirms</span>}
            {!r.in_portal && <span>Not in the portal yet — the Town Office takes this one</span>}
          </li>
        ))}
      </ul>
    </details>
  );
}

// The project's fees as a receipt (the chair's ruling, 2026-10-26): what is due when you send, what
// is due before the permit is issued, and the total; who reviews it and how long behind one link.
// The total follows each answer as it is saved.
export default function NeedsPanel({ needs, base, locked, useNames = {} }: {
  needs: Needs | null; base: string; locked?: boolean; useNames?: Record<string, string>;
}) {
  const box = "overflow-hidden rounded-[12px] border-[0.5px] border-[var(--app-separator)] bg-[var(--app-row)]";
  const say = (text: string) => <p className="px-4 py-[11px] text-[14px] text-[var(--app-secondary-label)]">{text}</p>;
  let body;
  if (!needs || "refused" in needs) body = say("Your fees show here once the Town has approved its rules.");
  else if (needs.town_only) body = say("Only the Town builds on Civic land: Town Meeting votes on it, and no permit application is made through this site.");
  else if (!needs.permits.length) body = say("Nothing yet. Answer your parts' questions and your fees fill in.");
  else {
    const due = needs.permits.filter((p) => p.due_at_send !== false && p.application_fee !== null && p.application_fee !== 0);
    const total = needs.application_fees_total + needs.permit_fees_total;
    body = (
      <>
        {due.length > 0 && (
          <Group title="Due when you send" subtotal={needs.application_fees_total} lines={due.map((p) => ({
            key: p.key, name: p.name, sub: "application fee",
            amount: p.application_fee === "varies" ? "Set by the Town Office" : money(p.application_fee as number) }))} />
        )}
        <Group title="Before the permit is issued" subtotal={needs.permit_fees_total} lines={laterLines(needs, base, useNames)} />
        <p className="flex justify-between bg-[var(--app-fill)] px-4 py-3 text-[17px] font-semibold text-[var(--app-label)]">
          <span>Total</span><span key={total} className="fee-fade tabular-nums">{money(total)}</span>
        </p>
      </>
    );
  }
  const shown = needs && !("refused" in needs) ? needs : null;
  return (
    <section aria-label="Fees" className="flex flex-col gap-2">
      <h2 className="px-4 text-[13px] text-[var(--app-secondary-label)]">Fees</h2>
      {shown?.not_listed.map((n) => (
        <p key={`${n.district}|${n.use}`} className="px-4 text-[14px] text-[var(--app-label)]">{n.text}</p>
      ))}
      <div className={box}>{body}</div>
      {shown && !shown.town_only && shown.permits.length > 0 && (
        <>
          {!locked && (
            <p className="px-4 text-[13px] text-[var(--app-secondary-label)]">
              The Code Enforcement Officer confirms the fees when the Town locks your project.</p>
          )}
          <Details reviews={shown.permits.flatMap((p) => p.reviews)} />
        </>
      )}
    </section>
  );
}
