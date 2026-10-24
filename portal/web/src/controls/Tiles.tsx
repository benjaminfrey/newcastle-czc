import { useRef, type KeyboardEvent, type ReactNode } from "react";
import type { FormField } from "../applications";
import RoofGlyph from "./RoofGlyph";

type Choice = { value: unknown; key: string; label: string; icon?: ReactNode };

const label = (f: FormField) => f.label ?? f.official_label;

// The choices a field offers as tiles: Yes and No for a yes/no question, else its options (roof
// styles carry their silhouette).
export function choicesOf(field: FormField): Choice[] {
  if (field.type === "yesno") return [{ value: true, key: "yes", label: "Yes" }, { value: false, key: "no", label: "No" }];
  const roof = /roof_style$/.test(field.id);
  return field.options.map((o) => ({ value: o.value, key: o.value, label: o.label, icon: roof ? <RoofGlyph kind={o.value} /> : undefined }));
}

const tile = "flex min-h-[58px] w-full items-center gap-3 rounded-xl border bg-[var(--app-row)] px-4 py-3 text-left text-[17px] outline-none "
  + "focus-visible:ring-2 focus-visible:ring-[var(--app-accent-text)] ";
const off = "border-[var(--app-separator)] hover:border-[var(--app-tertiary-label)]";
const on = "border-2 border-[var(--app-accent)] px-[15px] py-[11px]";
const grid = "grid w-full max-w-xl grid-cols-1 gap-2.5 sm:grid-cols-2";

// One choice, as tiles: a tap answers (and the wizard moves on), even a tap on the tile already
// chosen. A radio group with one tab stop; the arrow keys move between tiles.
export function ChoiceTiles({ field, value, onPick, choices }: {
  field: FormField; value: unknown; onPick: (v: unknown) => void; choices?: Choice[];
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
    <div role="radiogroup" aria-label={label(field)} className={list.length <= 2 ? "grid w-full max-w-md grid-cols-1 gap-2.5" : grid}>
      {list.map((c, i) => (
        <button key={c.key} ref={(el) => { refs.current[i] = el; }} type="button" role="radio" aria-checked={i === chosen}
                tabIndex={i === stop ? 0 : -1} onClick={() => onPick(c.value)} onKeyDown={(e) => onKey(e, i)}
                className={tile + (i === chosen ? on : off)}>
          {c.icon}
          <span>{c.label}</span>
        </button>
      ))}
    </div>
  );
}

// Several choices, as tiles with a check on each one chosen; nothing chosen is no answer.
export function MultiTiles({ field, value, onValue }: { field: FormField; value: unknown; onValue: (v: unknown) => void }) {
  const chosen = Array.isArray(value) ? (value as string[]) : [];
  const toggle = (v: string) => {
    const next = field.options.map((o) => o.value).filter((x) => (x === v ? !chosen.includes(v) : chosen.includes(x)));
    onValue(next.length ? next : null);
  };
  return (
    <div role="group" aria-label={label(field)} className={grid}>
      {field.options.map((o) => {
        const isOn = chosen.includes(o.value);
        return (
          <button key={o.value} type="button" role="checkbox" aria-checked={isOn} onClick={() => toggle(o.value)}
                  className={tile + (isOn ? on : off)}>
            <span className="flex-1">{o.label}</span>
            {isOn && (
              <svg aria-hidden="true" viewBox="0 0 24 24" className="size-5 shrink-0 text-[var(--app-accent-text)]" fill="none"
                   stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round"><path d="M5 12l5 5 9-10" /></svg>
            )}
          </button>
        );
      })}
    </div>
  );
}
