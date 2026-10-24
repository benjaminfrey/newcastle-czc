import { Card } from "@heroui/react";
import { useEffect, useRef, useState } from "react";
import { Link, useNavigate, useParams } from "react-router";
import { getMe, UNREACHABLE } from "../api";
import { createApplication, type NewApplication } from "../applications";
import { carryFrom, savePendingStart, takePendingStart } from "../pendingStart";
import { loadProperty, type ChosenProperty } from "../property";
import { loadAnswers } from "../screener";

const PORTAL_FORMS = ["use_permit", "small_project_plan", "entrance_permit"];

function propertyBody(p: ChosenProperty): NewApplication["property"] {
  return p.source === "lookup" && p.parcel_id !== null
    ? { source: "lookup", parcel_id: p.parcel_id }
    : { source: "manual", map_lot: p.map_lot, district_code: p.district_code };
}

export default function ApplyStart() {
  const { formKey = "" } = useParams();
  const navigate = useNavigate();
  const [problem, setProblem] = useState<string | null>(null);
  const [lookupDown, setLookupDown] = useState(false);
  const here = `/apply/${formKey}`;
  // Once per visit: StrictMode runs effects twice in development, and a second run
  // would make a second application (and find the pending start already used).
  const started = useRef(false);

  useEffect(() => {
    if (started.current) return;
    started.current = true;
    if (!PORTAL_FORMS.includes(formKey)) return setProblem("That application isn't one you can apply for here. Please contact the Town Office.");
    (async () => {
      const me = await getMe();
      if (me === "unavailable") return setProblem(UNREACHABLE);
      const pending = me ? takePendingStart() : null;
      const fromPending = pending && pending.formKey === formKey ? pending : null;
      const property = fromPending?.property ?? loadProperty();
      const useKey = fromPending ? fromPending.useKey : (loadAnswers()?.use_key ?? null);
      const carry = fromPending ? (fromPending.carry ?? null) : carryFrom(loadAnswers());
      if (!me) {
        savePendingStart({ formKey, property, useKey, carry });
        return navigate("/signin", { replace: true });
      }
      if (!property) return navigate(`/start/property?next=${encodeURIComponent(here)}`, { replace: true });
      const r = await createApplication({ form_key: formKey, property: propertyBody(property),
                                          disputed: property.disputed, note: property.note, use_key: useKey, carry });
      if (r === "property_unavailable") return setLookupDown(true);
      if (r === "not_approved") return setProblem("This application isn't ready yet. Please contact the Town Office.");
      if (r === "signed_out") return navigate("/signin", { replace: true });
      if (typeof r === "string") return setProblem(r === "unavailable" ? UNREACHABLE : "Something about that property didn't work. Please choose it again.");
      navigate(`/applications/${r.id}`, { replace: true });
    })();
  }, [formKey, here, navigate]);

  if (lookupDown) {
    return (
      <Card>
        <Card.Header>
          <Card.Title>We can't look up properties right now</Card.Title>
          <Card.Description>You can enter your property's details yourself, and staff will check them.</Card.Description>
        </Card.Header>
        <Card.Content>
          <Link className="underline" to={`/start/property?manual=1&next=${encodeURIComponent(here)}`}>Enter your property yourself</Link>
        </Card.Content>
      </Card>
    );
  }
  if (problem) return <p role="alert">{problem}</p>;
  return <p>Starting your application…</p>;
}
