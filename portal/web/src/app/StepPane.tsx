import { useState } from "react";
import type { FormSection } from "../applications";
import WhyWeAsk from "../components/WhyWeAsk";
import FieldControl from "../controls/FieldControl";
import { valueOf, type Row } from "../forms/applicability";
import InsetGroup from "../shell/InsetGroup";
import { useApplication } from "./ApplicationStore";
import CompassLayout from "./layouts/CompassLayout";
import LotDiagramLayout from "./layouts/LotDiagramLayout";

export const REASONS: Record<string, string> = {
  out_of_range: "That number is outside the range this question takes.",
  wrong_type: "That answer isn't in the form this question needs.",
  not_an_option: "Please choose one of the options.",
  too_long: "That's longer than this space allows. Please shorten it, or use \"Add more detail\" on the review page.",
  unknown_not_allowed: "Please give an answer to this one.",
};

// The controls for some rows, wired to the store: each answer saves as it is given.
export function useRowControls() {
  const { form, cur, setAnswer } = useApplication();
  const [errors, setErrors] = useState<Record<string, string>>({});
  return (r: Row, compact = false) => {
    const key = `${r.field.id}|${r.itemId ?? ""}`;
    return (
      <FieldControl key={key} field={r.field} itemId={r.itemId} value={valueOf(form!, r.field, r.itemId, cur!)}
                    error={errors[key]} compact={compact}
                    onValue={async (v) => {
                      setErrors((e) => ({ ...e, [key]: "" }));
                      const out = await setAnswer(r.field.id, r.itemId, v);
                      if ("error" in out) setErrors((e) => ({ ...e, [key]: REASONS[out.error] ?? REASONS.wrong_type }));
                    }} />
    );
  };
}

// Rows arranged by a sheet page's layout (the compass of walls, the lot diagram), else a list.
export function RowsInLayout({ rows, layout }: { rows: Row[]; layout: string | null | undefined }) {
  const { app, cur } = useApplication();
  const control = useRowControls();
  const street = ((cur?.property.streets as { name: string }[] | undefined) ?? [])[0]?.name ?? null;
  const by = (suffix: string) => rows.find((r) => r.field.id.endsWith(suffix));
  if (layout === "compass") {
    const wall = (w: string) => (by(`windows_${w}`) ? <InsetGroup>{control(by(`windows_${w}`)!, true)}</InsetGroup> : null);
    const others = rows.filter((r) => !/windows_(north|east|south|west)$/.test(r.field.id));
    const first = by("windows_north") ?? rows[0];
    return (
      <>
        {first?.field.help && <p className="text-[15px]">{first.field.help}</p>}
        <CompassLayout street={street} walls={{ north: wall("north"), east: wall("east"), south: wall("south"), west: wall("west") }} />
        {first && <WhyWeAsk why={first.field.why} />}
        {others.length > 0 && <InsetGroup>{others.map((r) => control(r))}</InsetGroup>}
      </>
    );
  }
  if (layout === "lot-diagram") {
    const side = (s: string) => (by(s) ? <InsetGroup>{control(by(s)!)}</InsetGroup> : null);
    return (
      <LotDiagramLayout parcelId={app?.property.parcel_id ?? null} street={street}
                        sides={{ front: side("setback_front"), side1: side("setback_side_1"), side2: side("setback_side_2"), rear: side("setback_rear") }} />
    );
  }
  return <InsetGroup>{rows.map((r) => control(r))}</InsetGroup>;
}

// A step of questions: one grouped list per section of the official form. A section that
// applies only on an answer (the owner's details) appears in place as soon as it does.
export default function StepPane({ rows, sections }: { rows: Row[]; sections: FormSection[] }) {
  const control = useRowControls();
  return (
    <>
      {sections.map((s) => {
        const mine = rows.filter((r) => r.section.id === s.id);
        if (mine.length === 0) return null;
        return <InsetGroup key={s.id} title={s.official_title}>{mine.map((r) => control(r))}</InsetGroup>;
      })}
    </>
  );
}
