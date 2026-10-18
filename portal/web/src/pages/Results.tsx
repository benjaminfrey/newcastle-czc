import { Card } from "@heroui/react";
import { useEffect, useState } from "react";
import { Link } from "react-router";
import { runScreener, type Outcome, type ScreenerResult } from "../api";
import { loadProperty } from "../property";
import { citeLabel, loadAnswers } from "../screener";

const CIVIC = "This is Town-owned land in the Civic district. Only the Town builds on Civic land: Town Meeting " +
  "votes on it, on the Select Board's recommendation, and no permit application is made through this site.";

function days(o: Outcome): string | null {
  if (o.days.length === 0) return null;
  return o.days.map((d) => `${d.label}: ${d.days} ${d.basis === "business" ? "business days" : "days"}` +
    `${d.when ? `, ${d.when}` : ""} (${citeLabel(d.cite)})`).join("; ");
}

export default function Results() {
  const [result, setResult] = useState<ScreenerResult | null>(null);
  const [problem, setProblem] = useState<string | null>(null);

  useEffect(() => {
    const answers = loadAnswers();
    const property = loadProperty();
    if (!answers) return setProblem("Start from the beginning so we know what you're planning.");
    const codes = property?.district_codes ?? [];
    runScreener({
      ...answers,
      property: { district_codes: codes, on_state_highway: property?.on_state_highway ?? null,
                  civic: false },  // the server decides whether the lot is wholly Civic
    }).then((r) => {
      if (r === "not_approved") setProblem("This tool isn't ready yet. Please contact the Town Office.");
      else if (r === "busy") setProblem("Please wait a minute and try again.");
      else if (r === "invalid") setProblem("Some of your answers couldn't be used. Please go back and check them.");
      else if (r === "unavailable") setProblem("We couldn't reach the Town's server. Please try again.");
      else setResult(r);
    });
  }, []);

  if (problem) return <p role="alert">{problem}</p>;
  if (!result) return <p>Working it out…</p>;
  if (result.town_only) return <p>{CIVIC}</p>;
  return (
    <div className="flex flex-col gap-4">
      <h1 className="text-xl font-semibold">Here's what you'll need</h1>
      {result.outcomes.length === 0 && result.not_listed.length === 0 && result.notes.length === 0 && (
        <p>From your answers, the Code doesn't call for any of the applications this site covers.</p>
      )}
      {result.outcomes.map((o) => (
        <Card key={`${o.application}-${o.district ?? ""}`}>
          <Card.Header>
            <Card.Title>{o.code_name}</Card.Title>
            <Card.Description>{o.plain}</Card.Description>
            <p className="text-sm font-semibold">{o.certainty === "needed" ? "The Code calls for this." : "You may need this."}</p>
          </Card.Header>
          <Card.Content className="flex flex-col gap-1">
            {o.district && <p>For the part of your lot in the {o.district_name ?? o.district} district.</p>}
            <p>Reviewed by: {o.reviewer}.</p>
            {days(o) && <p>Time the Code gives the reviewer: {days(o)}.</p>}
            <details>
              <summary>Why: {citeLabel(o.why.cite)}</summary>
              <p className="text-sm whitespace-pre-line">{o.why.text}</p>
              {o.why.ruling && <p className="text-sm">{o.why.ruling}</p>}
            </details>
            <p className="font-semibold">{o.in_portal ? "You can apply here." : "Apply through the Town Office."}</p>
          </Card.Content>
        </Card>
      ))}
      {result.not_listed.map((n) => <p key={n.district}>{n.text}</p>)}
      {result.notes.map((n) => <p key={n.text}>{n.text}</p>)}
      <p>Fees: Set by the Town's fee schedule — the Town Office will tell you the amount.</p>
      <p className="text-sm">The Code Enforcement Officer confirms this when you apply.</p>
      <Link to="/start" className="underline">Start again</Link>
    </div>
  );
}
