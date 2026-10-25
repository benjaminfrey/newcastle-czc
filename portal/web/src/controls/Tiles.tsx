import { useRef, type KeyboardEvent, type ReactNode } from "react";
import type { FormField } from "../applications";
import Icon from "./Icon";
import RoofGlyph from "./RoofGlyph";

export type Choice = { value: unknown; key: string; label: string; icon?: ReactNode };

const label = (f: FormField) => f.label ?? f.official_label;

// The choices a field offers as tiles: Yes and No for a yes/no question, else its options, each
// with its outline icon from the form (roof styles carry their silhouette instead).
export function choicesOf(field: FormField): Choice[] {
  if (field.type === "yesno") return [{ value: true, key: "yes", label: "Yes" }, { value: false, key: "no", label: "No" }];
  const roof = /roof_style$/.test(field.id);
  return field.options.map((o) => ({ value: o.value, key: o.value, label: o.label,
    icon: roof ? <RoofGlyph kind={o.value} /> : o.icon ? <Icon name={o.icon} /> : undefined }));
}

// A tile (task-list brief §4.5): 48 px tall at least, a 0.5 px edge, 8 px corners, no fill. Chosen,
// a 1.5 px edge in the label colour (1 px less padding, so nothing moves) and the icon darkens.
const tile = "flex min-h-12 w-full items-center gap-[10px] rounded-[8px] bg-transparent text-left text-[14px] text-[var(--app-label)] outline-none "
  + "focus-visible:ring-2 focus-visible:ring-[var(--app-accent-text)] focus-visible:ring-offset-2 focus-visible:ring-offset-[var(--app-row)] ";
const off = "border-[0.5px] border-[var(--app-edge)] px-3 py-[10px] text-[var(--app-secondary-label)] [@media(hover:hover)]:hover:border-[var(--app-secondary-label)]";
const on = "border-[1.5px] border-[var(--app-label)] px-[11px] py-[9px]";
// Two columns, one when the card is narrower than 400 px; at most 500 px wide.
const grid = "grid w-full max-w-[500px] grid-cols-1 gap-2 @[25rem]:grid-cols-2";

function Words({ c }: { c: Choice }) {
  return <>{c.icon}<span className="text-[var(--app-label)]">{c.label}</span></>;
}

// One choice, as tiles: a tap answers (and the card moves on), even a tap on the tile already
// chosen. Inside a set of values (`tap={false}`) a tap only answers, through onValue. A radio
// group with one tab stop; the arrow keys move between tiles.
export function ChoiceTiles({ field, value, onPick, onValue, choices, tap = true }: {
  field: FormField; value: unknown; onPick: (v: unknown) => void; onValue?: (v: unknown) => void; choices?: Choice[]; tap?: boolean;
}) {
  const list = choices ?? choicesOf(field);
  const refs = useRef<(HTMLButtonElement | null)[]>([]);
  const chosen = list.findIndex((c) => c.value === value);
  const stop = chosen >= 0 ? chosen : 0;
  function onKey(e: KeyboardEvent, i: number) {
    const d = e.key === "ArrowDown" || e.key === "ArrowRight" ? 1 : e.key === "ArrowUp" || e.key === "ArrowLeft" ? -1 : 0;
    if (!d) return;
    e.preventDefault();
    refs.current[(i + d + list.length) % list.length]?.focus();
  }
  return (
    <div className="@container flex w-full justify-center">
      <div role="radiogroup" aria-label={label(field)} className={grid}>
        {list.map((c, i) => (
          <button key={c.key} ref={(el) => { refs.current[i] = el; }} type="button" role="radio" aria-checked={i === chosen}
                  data-chosen={i === chosen ? "" : undefined} tabIndex={i === stop ? 0 : -1}
                  onClick={() => (tap ? onPick(c.value) : (onValue ?? onPick)(c.value))} onKeyDown={(e) => onKey(e, i)}
                  className={tile + (i === chosen ? on : off)}>
            <Words c={c} />
          </button>
        ))}
      </div>
    </div>
  );
}

// Several choices, as tiles; nothing chosen is no answer.
export function MultiTiles({ field, value, onValue }: { field: FormField; value: unknown; onValue: (v: unknown) => void }) {
  const chosen = Array.isArray(value) ? (value as string[]) : [];
  const toggle = (v: string) => {
    const next = field.options.map((o) => o.value).filter((x) => (x === v ? !chosen.includes(v) : chosen.includes(x)));
    onValue(next.length ? next : null);
  };
  return (
    <div className="@container flex w-full justify-center">
      <div role="group" aria-label={label(field)} className={grid}>
        {choicesOf(field).map((c) => {
          const isOn = chosen.includes(c.key);
          return (
            <button key={c.key} type="button" role="checkbox" aria-checked={isOn} data-chosen={isOn ? "" : undefined}
                    onClick={() => toggle(c.key)} className={tile + (isOn ? on : off)}>
              <Words c={c} />
            </button>
          );
        })}
      </div>
    </div>
  );
}
