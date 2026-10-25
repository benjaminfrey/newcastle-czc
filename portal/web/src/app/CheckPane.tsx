// "Check <task>" (task-list brief §4.7): the task's (or one building's) answers, each under its
// question as asked, with Change to its card, which comes back here; Done to the task list.
import { useEffect, useState } from "react";
import { Link } from "react-router";
import { getUseGroups } from "../api";
import { isUnknown } from "../controls/basic";
import { buildingKind } from "../controls/pickers";
import { valueOf } from "../forms/applicability";
import type { Screen } from "../forms/screens";
import Card from "../shell/Card";
import { useApplication } from "./ApplicationStore";
import { display } from "./OfficialGroup";

const blank = (v: unknown) => v === null || v === undefined || v === "" || (Array.isArray(v) && v.length === 0);

export default function CheckPane({ title, cards, changeHref, onBack, onDone }: {
  title: string; cards: Screen[]; changeHref: (s: Screen) => string; onBack: () => void; onDone: () => void;
}) {
  const { form, cur, app } = useApplication();
  const [useNames, setUseNames] = useState<Record<string, string>>({});
  useEffect(() => {
    if (!cards.some((s) => s.rows.some((r) => r.field.type === "uses"))) return;
    getUseGroups().then((g) => Array.isArray(g) && setUseNames(Object.fromEntries(g.flatMap((x) => x.uses).map((u) => [u.use_key, u.code_name]))));
  }, [cards]);
  const rows = cards.flatMap((s) => s.rows.map((r) => ({ s, r })));
  const shown = (s: Screen, fieldId: string, itemId: string | null) => {
    const r = s.rows.find((x) => x.field.id === fieldId)!;
    if (r.field.type === "upload") {
      const files = app!.attachments.filter((x) => x.field_id === fieldId && x.item_id === itemId).map((x) => x.filename);
      return files.length ? files.join(", ") : null;
    }
    const v = valueOf(form!, r.field, itemId, cur!);
    if (blank(v)) return null;
    if (isUnknown(v)) return "Not known yet";
    // The tile the applicant tapped, in its words; the printout keeps the form's terms.
    const f = r.field;
    if (f.id === "building_class" && typeof v === "string") return buildingKind(v)?.label ?? display(f, v, useNames);
    if (f.type === "choice") return f.options.find((o) => o.value === v)?.label ?? display(f, v, useNames);
    if (f.type === "multichoice" && Array.isArray(v)) return v.map((x) => f.options.find((o) => o.value === x)?.label ?? x).join(", ");
    return display(f, v, useNames);
  };

  return (
    <Card>
      <Card.Header title={`Check ${title}`} count={cards.length || 1} at={(cards.length || 1) - 1} />
      <ul className="flex flex-col text-left">
        {rows.map(({ s, r }, k) => {
          const words = shown(s, r.field.id, r.itemId);
          const q = r.field.label ?? r.field.official_label;
          return (
            <li key={`${r.field.id}|${r.itemId ?? ""}`} className={`flex items-center gap-3 px-4 py-[11px] ${k ? "border-t-[0.5px] border-[var(--app-separator)]" : ""}`}>
              <div className="min-w-0 flex-1">
                <p className="text-[14px] text-[var(--app-label)]">{q}</p>
                <p className="text-[14px] text-[var(--app-secondary-label)]">{words ?? "Not answered"}</p>
              </div>
              <Link to={changeHref(s)} aria-label={`Change ${q}`}
                    className="flex min-h-11 items-center px-1 text-[13px] text-[var(--app-accent-text)] outline-none focus-visible:ring-2 focus-visible:ring-[var(--app-accent-text)]">
                Change
              </Link>
            </li>
          );
        })}
      </ul>
      <Card.Footer back={{ label: "Back", onPress: onBack }} next={{ label: "Done", onPress: onDone }} />
    </Card>
  );
}
