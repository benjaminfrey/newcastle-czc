import { Button } from "@heroui/react";
import { useId } from "react";
import type { FormField } from "../applications";
import InsetGroup from "../shell/InsetGroup";
import {
  ChipsControl, isUnknown, NumberControl, PickerControl, SegmentedControl, SliderControl, SwitchControl, TextControl, TileControl,
} from "./basic";
import PointControl from "./PointControl";
import { BuildingPicker, BuildingTypeControl, StreetPicker } from "./pickers";
import UploadControl from "./UploadControl";
import UsesControl from "./UsesControl";

export type ControlKind = "text" | "longtext" | "number" | "stepper" | "slider" | "switch" | "segmented" | "tiles" | "picker"
  | "chips" | "building-picker" | "street-picker" | "building-type" | "uses" | "upload" | "point" | "date";

// The control a question gets: the one its form names, else one chosen by its type.
export function controlFor(f: FormField): ControlKind {
  if (f.control) return f.control;
  switch (f.type) {
    case "number": return "number";
    case "yesno": return "segmented";
    case "choice": return f.options.length <= 4 ? "segmented" : "tiles";
    case "multichoice": return "chips";
    case "uses": return "uses";
    case "upload": return "upload";
    case "point": return "point";
    case "longtext": return "longtext";
    case "date": return "date";
    default: return "text";
  }
}

// Short controls sit beside their question on a wide screen; the rest go under it.
const BESIDE = new Set<ControlKind>(["stepper", "number", "picker", "building-picker", "street-picker", "text", "date"]);

type Props = {
  field: FormField; itemId: string | null; value: unknown; onValue: (v: unknown) => void; error?: string | null;
  compact?: boolean; // part of a layout that gives the help once for the group
  bare?: boolean;    // the wizard's screen: the control alone; the screen shows the question, help and "I don't know yet"
};

export default function FieldControl({ field, itemId, value, onValue, error, compact, bare }: Props) {
  const kind = controlFor(field);
  const inputId = useId();
  const labelId = useId();
  const props = { field, value: isUnknown(value) ? null : value, onValue, labelId, inputId };
  const control = (() => {
    switch (kind) {
      case "longtext": return <TextControl {...props} long />;
      case "number": return <NumberControl {...props} />;
      case "stepper": return <NumberControl {...props} stepper />;
      case "slider": return <SliderControl {...props} />;
      case "switch": return <SwitchControl {...props} />;
      case "segmented": return <SegmentedControl {...props} />;
      case "tiles": return <TileControl {...props} />;
      case "picker": return <PickerControl {...props} />;
      case "chips": return <ChipsControl {...props} />;
      case "building-picker": return <BuildingPicker {...props} />;
      case "street-picker": return <StreetPicker {...props} />;
      case "building-type": return <BuildingTypeControl {...props} />;
      case "uses": return <UsesControl {...props} />;
      case "upload": return <UploadControl field={field} itemId={itemId} />;
      case "point": return <PointControl value={value} onValue={onValue} />;
      default: return <TextControl {...props} />;
    }
  })();
  if (bare) {
    return (
      <div data-field={field.id} className="flex w-full max-w-md flex-col items-center gap-2">
        {control}
        {isUnknown(value) && <p className="text-[15px] text-[var(--app-secondary-label)]">Not known yet — staff will follow up.</p>}
        {error && <p role="alert" className="text-[15px] text-[var(--app-destructive)]">{error}</p>}
      </div>
    );
  }
  const question = field.label ?? field.official_label;
  // A switch sits at the end of its question's line, as in Settings; its help goes underneath.
  const inline = kind === "switch";
  return (
    <InsetGroup.Row stacked={inline || !BESIDE.has(kind)} field={field.id}
                    label={inline ? undefined : <span id={labelId}>{kind === "text" || kind === "longtext" ? <label htmlFor={inputId}>{question}</label> : question}</span>}>
      <div className="flex flex-col gap-1.5">
        {inline ? (
          <div className="flex min-h-11 items-center gap-3">
            <span id={labelId} aria-hidden="true" className="flex-1 text-[15px]">{question}</span>
            {control}
          </div>
        ) : control}
        {field.help && !compact && <p className="text-[15px] text-[var(--app-secondary-label)]">{field.help}</p>}
        {isUnknown(value) && <p className="text-[15px] text-[var(--app-secondary-label)]">Not known yet — staff will follow up.</p>}
        {error && <p role="alert" className="text-[15px] text-[var(--app-destructive)]">{error}</p>}
        <div className="flex flex-wrap items-center gap-x-4">
          {field.allow_unknown && !isUnknown(value) && (
            <Button variant="ghost" size="sm" className="min-h-11 px-0 text-[var(--app-accent-text)]" onPress={() => onValue({ unknown: true })}>
              I don't know yet
            </Button>
          )}
        </div>
      </div>
    </InsetGroup.Row>
  );
}
