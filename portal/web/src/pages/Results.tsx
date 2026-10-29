import { Button } from "@heroui/react";
import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router";
import InsetGroup from "../shell/InsetGroup";
import { carryFrom, savePendingStart } from "../pendingStart";
import { getMe, runScreener, type Outcome, type ScreenerResult } from "../api";
import { mapLotLabel } from "../format";
import { loadProperty } from "../property";
import { loadAnswers } from "../screener";

const CIVIC = "This is Town-owned land in the Civic district. Only the Town builds on Civic land: Town Meeting " +
  "votes on it, on the Select Board's recommendation, and no permit application is made through this site.";

function days(o: Outcome): string | null {
  if (o.days.length === 0) return null;
  return o.days.map((d) => `${d.label}: ${d.days} ${d.basis === "business" ? "business days" : "days"}` +
    `${d.when ? `, ${d.when}` : ""}`).join("; ");
}

// "a Use Permit", "an Entrance Permit".
function article(name: string): string {
  // By sound, not spelling: "a Use Permit" (a "you" sound), "an Entrance Permit".
  return /^[aeiou]/i.test(name) && !/^(us|un[iy]|eu)/i.test(name) ? "an" : "a";
}

// One Start link per application, on its first card, when a lot in two districts
// gets a card for each.
function firstOf(all: Outcome[], o: Outcome): boolean {
  return all.find((x) => x.application === o.application) === o;
}

export default function Results() {
  const navigate = useNavigate();
  const [result, setResult] = useState<ScreenerResult | null>(null);

  // Signed in: straight to the application. Signed out: sign in here, in a sheet; the emailed
  // link brings the person back to start it.
  async function start(formKey: string) {
    const me = await getMe();
    if (me && me !== "unavailable") return navigate(`/apply/${formKey}`);
    savePendingStart({ formKey, property: loadProperty(), useKey: loadAnswers()?.use_key ?? null, carry: carryFrom(loadAnswers()) });
    navigate("/start/signin");
  }
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

  const lot = loadProperty()?.map_lot ?? null;
  if (problem) return <p role="alert">{problem}</p>;
  if (!result) return <p>Working it out…</p>;
  if (result.town_only) return <p>{CIVIC}</p>;
  return (
    <div className="flex flex-col gap-8">
      {result.outcomes.length === 0 && result.not_listed.length === 0 && result.notes.length === 0 && (
        <p className="text-[17px]">From your answers, the Code doesn't call for any of the applications this site covers.</p>
      )}
      {result.outcomes.map((o) => (
        // The answer first, as a title; what it means in a sentence; reviewer, time, fees and lot as
        // rows; Start as the one primary action.
        <section key={`${o.application}-${o.district ?? ""}`} aria-label={o.code_name} className="flex flex-col gap-3">
          <h2 className="text-[30px] font-bold leading-tight">
            {o.certainty === "needed" ? "You'll need " : "You may need "}{article(o.code_name)} <span>{o.code_name}</span>
          </h2>
          <p className="text-[17px]">{o.plain}</p>
          <InsetGroup footer="The Code Enforcement Officer confirms this when you apply.">
            {o.district && <InsetGroup.Row label="Where">For the part of your lot in the {o.district_name ?? o.district} district.</InsetGroup.Row>}
            <InsetGroup.Row label="Reviewed by">{o.reviewer}</InsetGroup.Row>
            {days(o) && <InsetGroup.Row label="How long the review can take">{days(o)}</InsetGroup.Row>}
            <InsetGroup.Row label="Fees">Set by the Town's fee schedule — the Town Office will tell you the amount.</InsetGroup.Row>
            {lot && <InsetGroup.Row label="Your lot">{mapLotLabel(lot)}</InsetGroup.Row>}
            <InsetGroup.Row label="How to apply">{o.in_portal ? "You can apply here." : "Apply through the Town Office."}</InsetGroup.Row>
          </InsetGroup>
          {o.in_portal && firstOf(result.outcomes, o) && (
            <Button variant="primary" className="min-h-12 self-start px-6 text-[17px]" aria-label={`Start this application: ${o.code_name}`}
                    onPress={() => void start(o.application)}>
              Start this application
            </Button>
          )}
        </section>
      ))}
      {result.not_listed.map((n) => <p key={n.district} className="text-[17px]">{n.text}</p>)}
      {result.notes.map((n) => <p key={n.text} className="text-[17px]">{n.text}</p>)}
      <Link to="/start" className="flex min-h-11 items-center self-start text-[15px] text-[var(--app-accent-text)]">Start again</Link>
    </div>
  );
}
