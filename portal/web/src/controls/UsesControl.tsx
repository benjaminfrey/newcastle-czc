import { Button, Tag, TagGroup } from "@heroui/react";
import { useEffect, useState } from "react";
import { getUseGroups } from "../api";
import Sheet from "../shell/Sheet";
import UseSearch from "../components/UseSearch";
import type { ControlProps } from "./basic";

// Uses from the Code's list, shown as chips; "Add a use" opens the search in a sheet.
export default function UsesControl({ field, value, onValue }: ControlProps) {
  const chosen = Array.isArray(value) ? (value as string[]) : [];
  const [open, setOpen] = useState(false);
  const [names, setNames] = useState<Record<string, string>>({});
  useEffect(() => {
    getUseGroups().then((g) => Array.isArray(g) && setNames(Object.fromEntries(g.flatMap((x) => x.uses).map((u) => [u.use_key, u.code_name]))));
  }, []);
  return (
    <div className="flex flex-col gap-3">
      {chosen.length > 0 && (
        <TagGroup aria-label={field.label ?? field.official_label}
                  onRemove={(keys) => {
                    const left = chosen.filter((k) => !(keys as Set<string>).has(k));
                    onValue(left.length ? left : null); // no uses left is no answer, not an empty list
                  }}>
          <TagGroup.List className="flex flex-wrap gap-2">
            {chosen.map((k) => (
              <Tag key={k} id={k} textValue={names[k] ?? k} className="min-h-11 rounded-full bg-[var(--app-selection)] px-4">
                {names[k] ?? k}<Tag.RemoveButton />
              </Tag>
            ))}
          </TagGroup.List>
        </TagGroup>
      )}
      <div><Button variant="secondary" className="min-h-11" onPress={() => setOpen(true)}>Add a use</Button></div>
      <Sheet open={open} title="Add a use" onCancel={() => setOpen(false)} onDone={() => setOpen(false)}>
        <UseSearch chosen={chosen} chooseLabel="Add"
                   onChoose={(k, name) => { setNames((n) => ({ ...n, [k]: name })); onValue([...chosen, k]); setOpen(false); }} />
      </Sheet>
    </div>
  );
}
