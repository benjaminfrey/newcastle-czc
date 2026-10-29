// One screen of the wizard (brief 2026-10-24): a large question, a line of help when it earns one,
// and the control. A single choice is a set of tiles that answers at a tap; a value from the
// Town's map asks "Is this right?"; fields asked together (deed book and page, the setbacks, the
// four walls) share the screen.
import { AlertDialog, Button } from "@heroui/react";
import { useState, type MutableRefObject } from "react";
import type { FormField } from "../applications";
import FieldControl from "../controls/FieldControl";
import { BuildingPicker, StreetPicker } from "../controls/pickers";
import { ChoiceTiles, MultiTiles } from "../controls/Tiles";
import { mapValueOf, valueOf, type Row } from "../forms/applicability";
import type { Screen } from "../forms/screens";
import { itemLabel } from "../forms/steps";
import { display } from "./OfficialGroup";
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

// A number out of range says what the range is.
function reason(code: string, f: FormField): string {
  if (code === "out_of_range" && f.min !== null && f.max !== null) {
    return `Please enter a number from ${f.min} to ${f.max}${f.unit ? ` ${f.unit}` : ""}.`;
  }
  return REASONS[code] ?? REASONS.wrong_type;
}

export const rowKey = (r: Row) => `${r.field.id}|${r.itemId ?? ""}`;

// The controls for some rows, wired to the store: each answer saves as it is given. A refused
// answer's message is kept in `errors` (a ref too, so Continue can see it at once).
export function useRowControls(errorsRef?: MutableRefObject<Record<string, string>>) {
  const { form, cur, setAnswer } = useApplication();
  const [errors, setErrors] = useState<Record<string, string>>({});
  const put = (key: string, msg: string) => {
    if (errorsRef) errorsRef.current = { ...errorsRef.current, [key]: msg };
    setErrors((e) => ({ ...e, [key]: msg }));
  };
  return (r: Row, opts: { compact?: boolean; bare?: boolean; field?: FormField } = {}) => {
    const key = rowKey(r);
    return (
      <FieldControl key={key} field={opts.field ?? r.field} itemId={r.itemId} value={valueOf(form!, r.field, r.itemId, cur!)}
                    error={errors[key]} compact={opts.compact} bare={opts.bare}
                    onValue={async (v) => {
                      put(key, "");
                      const out = await setAnswer(r.field.id, r.itemId, v);
                      if ("error" in out) put(key, reason(out.error, r.field));
                    }} />
    );
  };
}

const OPPOSITE: Record<string, string> = { north: "south", south: "north", east: "west", west: "east" };
const WALLS = ["north", "east", "south", "west"] as const;

// "Front (north, faces Sheepscot Road)", "Back (south)", "Side (east)": the walls named from the
// way the front faces; without that answer, the compass names alone.
export function wallLabels(facing: unknown, road: string | null): Record<string, string> | null {
  if (typeof facing !== "string" || !OPPOSITE[facing]) return null;
  return Object.fromEntries(WALLS.map((w) => [w, w === facing ? `Front (${w}${road ? `, faces ${road}` : ""})`
    : w === OPPOSITE[facing] ? `Back (${w})` : `Side (${w})`]));
}

const NOUNS: Record<string, string> = { building: "building", component: "addition, porch or deck" };

// The words a screen asks with, for its heading and the screen reader.
export function headingOf(s: Screen): string {
  if (s.kind === "another") return `Is there another ${s.id.endsWith("building") ? "building" : "addition, porch or deck"} in this project?`;
  if (s.kind === "any") return `Are you adding ${s.id.endsWith("component") ? "an addition, porch or deck" : `a ${NOUNS[s.id.split(":")[1]] ?? "building"}`}?`;
  if (s.kind === "setbacks") return "How far will it be from each lot line?";
  if (s.kind === "walls") return "About how much of each wall is windows and doors?";
  const f = s.rows[0].field;
  return f.label ?? f.official_label;
}

function helpOf(s: Screen): string | null {
  if (s.kind === "setbacks") return "In feet, to the closest part of the building.";
  if (s.kind === "walls") return "A rough share is fine, in steps of 5%. Most walls are between 10% and 30%.";
  if (s.kind === "another" || s.kind === "any") return null;
  return s.rows[0].field.help;
}

type Props = {
  screen: Screen;
  editing: boolean;                 // "Is this right?": the applicant chose to correct it
  errorsRef: MutableRefObject<Record<string, string>>;
  onPick: (r: Row, value: unknown) => void;      // a tap that answers and moves on
  onConfirm: (r: Row, keep: boolean) => void;    // "Yes, that's right" (keep the answer shown) / "Use the map's"
  onCorrect: () => void;                         // "No, I'll correct it"
  onLoop: (yes: boolean) => void;                // "Is there another?" / "Are you adding…?"
  onUnknown: () => void;                         // "I don't know yet"
  onDelete?: { noun: string; run: () => void };  // a building or addition's first screen, while more than the least remain
};

export default function WizardPane({ screen, editing, errorsRef, onPick, onConfirm, onCorrect, onLoop, onUnknown, onDelete }: Props) {
  const { form, cur, app, setAnswer } = useApplication();
  const [confirmDelete, setConfirmDelete] = useState(false);
  const control = useRowControls(errorsRef);
  const value = (r: Row) => valueOf(form!, r.field, r.itemId, cur!);
  const street = ((cur?.property.streets as { name: string }[] | undefined) ?? [])[0]?.name ?? null;
  const row = screen.rows[0];
  const heading = headingOf(screen);
  const carried = screen.rows.some((r) => app?.answers.some((x) => x.field_id === r.field.id && x.item_id === r.itemId && x.carried));
  const help = helpOf(screen);

  const body = (() => {
    switch (screen.kind) {
      case "choice": case "facing": {
        const c = row.field.control;
        if (c === "building-picker") return <BuildingPicker field={row.field} value={value(row)} onValue={(v) => onPick(row, v)} labelId="" inputId="" />;
        if (c === "street-picker") return <StreetPicker field={row.field} value={value(row)} onValue={(v) => onPick(row, v)} labelId="" inputId=""
                                                        onAnother={onCorrect} onTyped={(v) => void setAnswer(row.field.id, row.itemId, v)} />;
        return <ChoiceTiles field={row.field} value={value(row)} onPick={(v) => onPick(row, v)} />;
      }
      case "multi":
        return <MultiTiles field={row.field} value={value(row)} onValue={(v) => void setAnswer(row.field.id, row.itemId, v)} />;
      case "another": case "any": {
        const noun = screen.id.endsWith("building") ? "building" : "one";
        const choices = screen.kind === "another"
          ? [{ value: true, key: "yes", label: `Yes, add another ${noun}` }, { value: false, key: "no", label: "No, that's all" }]
          : [{ value: true, key: "yes", label: "Yes" }, { value: false, key: "no", label: "No" }];
        return <ChoiceTiles field={{ ...({} as FormField), id: screen.id, label: heading, official_label: heading, type: "choice", options: [] }}
                            value={null} choices={choices} onPick={(v) => onLoop(v === true)} />;
      }
      case "confirm": {
        // A value the applicant corrected is theirs, shown as theirs, with the map's beside it.
        const map = display(row.field, mapValueOf(row.field, cur!), {});
        const own = cur!.answers.find((x) => x.field_id === row.field.id && x.item_id === row.itemId)?.value;
        const corrected = own !== undefined && own !== null;
        const choices = [{ value: "yes", key: "yes", label: "Yes, that's right" },
          ...(corrected ? [{ value: "map", key: "map", label: `Use the map's ${map}` }] : []),
          { value: "no", key: "no", label: "No, I'll correct it" }];
        return (
          <div className="flex w-full flex-col items-center gap-4">
            <p className="text-[30px] font-semibold tabular-nums">{display(row.field, value(row), {})}</p>
            <p className="-mt-3 text-[13px] text-[var(--app-secondary-label)]">
              {corrected ? `You entered this. The Town's map says ${map}.` : "From the Town's map"}
            </p>
            {editing ? control(row, { bare: true }) : (
              <ChoiceTiles field={row.field} value={null} choices={choices}
                           onPick={(v) => (v === "no" ? onCorrect() : onConfirm(row, v === "yes"))} />
            )}
          </div>
        );
      }
      case "set":
        // Values asked together sit side by side, each under its short name from the form.
        return (
          <div className="grid w-full max-w-lg grid-cols-1 gap-4 text-left sm:grid-cols-2">
            {screen.rows.map((r) => (
              <div key={rowKey(r)} className="flex flex-col gap-1.5">
                <p className="text-[13px] text-[var(--app-secondary-label)]">{r.field.official_label}</p>
                {control(r, { bare: true })}
              </div>
            ))}
          </div>
        );
      case "setbacks": {
        const by = (s: string) => screen.rows.find((r) => r.field.id.endsWith(s));
        const side = (s: string, words: string) => (by(s) ? (
          <div className="flex flex-col items-center gap-1.5 text-[13px] text-[var(--app-secondary-label)]">
            <span>{words}</span>{control(by(s)!, { bare: true })}
          </div>) : null);
        return (
          <div className="w-full max-w-3xl">
            <LotDiagramLayout parcelId={app?.property.parcel_id ?? null} street={street}
                              sides={{ front: side("setback_front", `Front${street ? `, along ${street}` : ""}`), side1: side("setback_side_1", "One side"),
                                       side2: side("setback_side_2", "Other side"), rear: side("setback_rear", "Back") }} />
          </div>
        );
      }
      case "walls": {
        const facingRow = cur!.answers.find((x) => x.item_id === screen.itemId && x.field_id.endsWith("front_facing"));
        const labels = wallLabels(facingRow?.value, street);
        const wall = (w: string) => {
          const r = screen.rows.find((x) => x.field.id.endsWith(`windows_${w}`));
          if (!r) return null;
          const field = { ...r.field, label: labels?.[w] ?? r.field.label };
          return <div className="flex flex-col gap-1 text-left"><span className="text-[15px]">{field.label}</span>{control(r, { bare: true, field })}</div>;
        };
        return (
          <div className="w-full max-w-3xl">
            <CompassLayout street={null} walls={{ north: wall("north"), east: wall("east"), south: wall("south"), west: wall("west") }} />
          </div>
        );
      }
      default:
        return control(row, { bare: true });
    }
  })();

  return (
    <section className="flex flex-col items-center gap-2 py-6 text-center">
      {screen.itemId && <p className="text-[13px] text-[var(--app-secondary-label)]">{itemLabel(form!, cur!, screen.itemId)}</p>}
      <h2 tabIndex={-1} data-screen-title className="max-w-[30ch] text-balance text-[22px] font-semibold leading-tight outline-none">{heading}</h2>
      <p className="mb-4 min-h-[1.25rem] max-w-[46ch] text-pretty text-[15px] text-[var(--app-secondary-label)]">{help ?? ""}</p>
      {carried && (
        <p className="-mt-2 mb-3 text-[13px] text-[var(--app-secondary-label)]">Filled in from your answers at the start. Change it if you need to.</p>
      )}
      {body}
      {screen.unknown && screen.kind !== "confirm" && (
        <button type="button" onClick={onUnknown}
                className="mt-3 min-h-11 px-2 text-[15px] text-[var(--app-accent-text)] outline-none focus-visible:ring-2 focus-visible:ring-[var(--app-accent-text)]">
          I don't know yet
        </button>
      )}
      {onDelete && (
        // A building or addition added by mistake goes, behind a confirmation (redesign brief §147).
        <button type="button" onClick={() => setConfirmDelete(true)}
                className="mt-6 min-h-11 px-2 text-[15px] text-[var(--app-destructive)] outline-none focus-visible:ring-2 focus-visible:ring-[var(--app-accent-text)]">
          Delete {onDelete.noun}
        </button>
      )}
      {onDelete && (
        <AlertDialog.Backdrop isOpen={confirmDelete} onOpenChange={setConfirmDelete}>
          <AlertDialog.Container>
            <AlertDialog.Dialog>
              <AlertDialog.Header><AlertDialog.Heading>Delete {onDelete.noun}?</AlertDialog.Heading></AlertDialog.Header>
              <AlertDialog.Body>Its answers and files leave the application. This can't be undone here.</AlertDialog.Body>
              <AlertDialog.Footer>
                <Button variant="secondary" onPress={() => setConfirmDelete(false)}>Cancel</Button>
                <Button variant="danger" onPress={() => { setConfirmDelete(false); onDelete.run(); }}>Delete</Button>
              </AlertDialog.Footer>
            </AlertDialog.Dialog>
          </AlertDialog.Container>
        </AlertDialog.Backdrop>
      )}
    </section>
  );

}
