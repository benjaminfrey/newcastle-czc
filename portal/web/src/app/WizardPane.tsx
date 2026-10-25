// The body of one card (task-list brief §4.5): the question, a line of help when it earns one,
// and the control. A single choice is tiles that answer at a tap; a value from the Town's map asks
// "Is this right?"; a set of values sits as short names beside their fields; the setbacks sit
// around the lot drawing and the walls around the compass, once the front's direction is chosen.
import { useState, type MutableRefObject } from "react";
import type { FormField } from "../applications";
import FieldControl from "../controls/FieldControl";
import { BuildingPicker, BuildingTypeControl, StreetPicker } from "../controls/pickers";
import { ChoiceTiles, MultiTiles } from "../controls/Tiles";
import { mapValueOf, valueOf, type Row } from "../forms/applicability";
import type { Screen } from "../forms/screens";
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
  return (r: Row, opts: { compact?: boolean; bare?: boolean; inSet?: boolean; field?: FormField } = {}) => {
    const key = rowKey(r);
    return (
      <FieldControl key={key} field={opts.field ?? r.field} itemId={r.itemId} value={valueOf(form!, r.field, r.itemId, cur!)}
                    error={errors[key]} compact={opts.compact} bare={opts.bare} inSet={opts.inSet}
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

// The words a card asks with, for its heading and the screen reader.
export function headingOf(s: Screen): string {
  if (s.kind === "setbacks") return "How far will it be from each lot line?";
  if (s.kind === "walls") {
    const facing = s.rows.find((r) => r.field.id.endsWith("front_facing"));
    return facing ? facing.field.label ?? facing.field.official_label : "About how much of each wall is windows and doors?";
  }
  const f = s.rows[0].field;
  return f.label ?? f.official_label;
}

function helpOf(s: Screen): string | null {
  if (s.kind === "setbacks") return "In feet, to the closest part of the building.";
  const f = s.rows[0]?.field;
  if (!f) return null;
  if (s.kind === "choice" || s.kind === "facing") return f.help ?? "Choose one.";
  if (s.kind === "multi") return f.help ?? "Choose all that apply.";
  return f.help;
}

type Props = {
  screen: Screen;
  editing: boolean;                 // "Is this right?": the applicant chose to correct it; "Another road": typing one
  errorsRef: MutableRefObject<Record<string, string>>;
  onPick: (r: Row, value: unknown) => void;      // a tap that answers and moves on
  onConfirm: (r: Row, keep: boolean) => void;    // "Yes, that's right" (keep the answer shown) / "Use the map's"
  onCorrect: () => void;                         // "No, I'll correct it"; "Another road"
  onUnknown: () => void;                         // "I don't know yet" / "I don't know some of these yet"
};

const isChoice = (f: FormField) => f.type === "choice" || f.type === "yesno";

export default function CardQuestion({ screen, editing, errorsRef, onPick, onConfirm, onCorrect, onUnknown }: Props) {
  const { form, cur, app, setAnswer } = useApplication();
  const control = useRowControls(errorsRef);
  const value = (r: Row) => valueOf(form!, r.field, r.itemId, cur!);
  const answer = (r: Row, v: unknown) => void setAnswer(r.field.id, r.itemId, v);
  const street = ((cur?.property.streets as { name: string }[] | undefined) ?? [])[0]?.name ?? null;
  const row = screen.rows[0];
  const heading = headingOf(screen);
  const carried = screen.rows.some((r) => app?.answers.some((x) => x.field_id === r.field.id && x.item_id === r.itemId && x.carried));
  const help = helpOf(screen);
  const short = (r: Row) => r.field.short ?? r.field.label ?? r.field.official_label;

  // One value of a set: its short name on the left, its field on the right; tiles take the width.
  const member = (r: Row) => {
    if (isChoice(r.field) || r.field.type === "multichoice") {
      return (
        <div key={r.field.id} className="col-span-2 flex flex-col gap-2">
          <span className="text-[14px] text-[var(--app-label)]">{short(r)}</span>
          {r.field.type === "multichoice"
            ? <MultiTiles field={{ ...r.field, label: short(r) }} value={value(r)} onValue={(v) => answer(r, v)} />
            : <ChoiceTiles field={{ ...r.field, label: short(r) }} value={value(r)} tap={false} onPick={(v) => answer(r, v)} onValue={(v) => answer(r, v)} />}
        </div>
      );
    }
    return (
      <div key={r.field.id} className="contents">
        <span className="self-center text-[14px] text-[var(--app-label)]">{short(r)}</span>
        {control(r, { inSet: true, field: { ...r.field, label: short(r) } })}
      </div>
    );
  };

  const body = (() => {
    switch (screen.kind) {
      case "choice": case "facing": {
        const c = row.field.control;
        if (c === "building-type") return <BuildingTypeControl field={row.field} value={value(row)} onValue={(v) => onPick(row, v)} labelId="" inputId="" />;
        if (c === "building-picker") return <BuildingPicker field={row.field} value={value(row)} onValue={(v) => onPick(row, v)} labelId="" inputId="" />;
        if (c === "street-picker") return <StreetPicker field={row.field} value={value(row)} onValue={(v) => onPick(row, v)} labelId="" inputId=""
                                                        onAnother={onCorrect} onTyped={(v) => answer(row, v)} />;
        return <ChoiceTiles field={row.field} value={value(row)} onPick={(v) => onPick(row, v)} />;
      }
      case "multi":
        return <MultiTiles field={row.field} value={value(row)} onValue={(v) => answer(row, v)} />;
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
      case "set": {
        // Values asked together; one per floor sits under a hairline, below the rest.
        const repeated = (r: Row) => /_\d+$/.test(r.field.id);
        const grid = "grid w-full grid-cols-[minmax(0,1fr)_auto] items-center gap-x-[14px] gap-y-[10px] text-left";
        const wide = screen.rows.some((r) => r.field.type === "text" || r.field.type === "longtext") ? "max-w-[480px]" : "max-w-[380px]";
        const floors = screen.rows.filter(repeated);
        return (
          <div className={`flex w-full flex-col items-center ${wide}`}>
            <div className={grid}>{screen.rows.filter((r) => !repeated(r)).map(member)}</div>
            {floors.length > 0 && (
              <div className={`${grid} mt-[10px] border-t-[0.5px] border-[var(--app-separator)] pt-[10px]`}>{floors.map(member)}</div>
            )}
          </div>
        );
      }
      case "setbacks": {
        const by = (s: string) => screen.rows.find((r) => r.field.id.endsWith(s));
        const side = (s: string, words: string) => (by(s) ? (
          <div className="flex flex-col items-center gap-1.5 text-[13px] text-[var(--app-secondary-label)]">
            <span>{words}</span>{control(by(s)!, { bare: true })}
          </div>) : null);
        return (
          <div className="w-full">
            <LotDiagramLayout parcelId={app?.property.parcel_id ?? null} street={street}
                              sides={{ front: side("setback_front", `Front${street ? `, along ${street}` : ""}`), side1: side("setback_side_1", "One side"),
                                       side2: side("setback_side_2", "Other side"), rear: side("setback_rear", "Back") }} />
          </div>
        );
      }
      case "walls": {
        // The front's direction first; the four walls, named from it, once it is chosen.
        const facing = screen.rows.find((r) => r.field.id.endsWith("front_facing"));
        const dir = facing ? value(facing) : cur!.answers.find((x) => x.item_id === screen.itemId && x.field_id.endsWith("front_facing"))?.value;
        const labels = wallLabels(dir, street);
        const wall = (w: string) => {
          const r = screen.rows.find((x) => x.field.id.endsWith(`windows_${w}`));
          if (!r) return null;
          const field = { ...r.field, label: labels?.[w] ?? r.field.label };
          return <div className="flex flex-col gap-1 text-left"><span className="text-[15px]">{field.label}</span>{control(r, { bare: true, field })}</div>;
        };
        return (
          <div className="flex w-full flex-col items-center gap-5">
            {facing && <ChoiceTiles field={facing.field} value={dir} tap={false} onPick={(v) => answer(facing, v)} onValue={(v) => answer(facing, v)} />}
            {(!facing || labels) && (
              <div className="w-full">
                {facing && <p className="mb-3 text-[13px] text-[var(--app-secondary-label)]">About how much of each wall is windows and doors? A rough share is fine.</p>}
                <CompassLayout street={null} walls={{ north: wall("north"), east: wall("east"), south: wall("south"), west: wall("west") }} />
              </div>
            )}
          </div>
        );
      }
      default:
        return control(row, { bare: true });
    }
  })();
  const unknownable = screen.kind !== "confirm" && screen.rows.some((r) => r.field.allow_unknown);
  const several = screen.rows.length > 1;

  return (
    <>
      <h2 tabIndex={-1} data-screen-title className="max-w-[30ch] text-balance text-[20px] font-medium leading-[1.3] outline-none">{heading}</h2>
      <p className="mb-4 mt-1 max-w-[46ch] text-pretty text-[13px] text-[var(--app-secondary-label)] empty:mb-3">{help ?? ""}</p>
      {carried && (
        <p className="-mt-2 mb-3 text-[13px] text-[var(--app-secondary-label)]">Filled in from your answers at the start. Change it if you need to.</p>
      )}
      {body}
      {unknownable && (
        <button type="button" onClick={onUnknown}
                className="mt-3 min-h-11 px-1 text-[13px] text-[var(--app-accent-text)] outline-none focus-visible:ring-2 focus-visible:ring-[var(--app-accent-text)]">
          {several ? "I don't know some of these yet" : "I don't know yet"}
        </button>
      )}
    </>
  );
}
