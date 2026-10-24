import { Button, Dropdown } from "@heroui/react";
import type { StepModel } from "../forms/steps";
import InsetGroup from "../shell/InsetGroup";
import StatusGlyph, { statusName } from "../shell/StatusGlyph";
import { useApplication } from "./ApplicationStore";

type Props = { step: StepModel; onOpen: (itemId: string, pageId?: string) => void };

// The buildings (or additions) as a list, each opening its sheet, with Add at the end. When the
// form offers several ways to add one ("A building", "A detached garage or shed"), Add is a menu.
export default function HubPane({ step, onOpen }: Props) {
  const { addItem } = useApplication();
  const hub = step.hub!;
  const options = hub.repeat.add_options ?? [];
  const noun = hub.kind === "building" ? "a building" : "an addition, porch or deck";
  const full = hub.items.length >= hub.repeat.max;

  async function add(preset?: number) {
    const id = await addItem(hub.kind, preset);
    if (id) onOpen(id, hub.pages[0]?.id);
  }

  return (
    <InsetGroup footer={hub.items.length === 0 ? `None yet. Add ${noun} if your project has one.` : undefined}>
      {hub.items.map((i) => (
        <button key={i.id} type="button" onClick={() => onOpen(i.id, hub.pages[0]?.id)}
                aria-label={`${i.label}, ${statusName(i.status, i.unknowns)}`}
                className="flex min-h-12 w-full items-center gap-3 px-4 text-left text-[17px]">
          <StatusGlyph status={i.status} unknowns={i.unknowns} />
          <span className="flex-1">{i.label}</span>
          <span aria-hidden="true" className="text-[var(--app-tertiary-label)]">›</span>
        </button>
      ))}
      {!full && (options.length > 1 ? (
        <Dropdown>
          <Button variant="ghost" fullWidth className="min-h-12 justify-start px-4 text-[17px] text-[var(--app-accent-text)]">
            <span aria-hidden="true">＋</span> Add {noun}
          </Button>
          <Dropdown.Popover>
            <Dropdown.Menu onAction={(key) => void add(Number(key))}>
              {options.map((o, k) => <Dropdown.Item key={o.label} id={String(k)} textValue={o.label}>{o.label}</Dropdown.Item>)}
            </Dropdown.Menu>
          </Dropdown.Popover>
        </Dropdown>
      ) : (
        <Button variant="ghost" fullWidth className="min-h-12 justify-start px-4 text-[17px] text-[var(--app-accent-text)]"
                onPress={() => void add(options.length === 1 ? 0 : undefined)}>
          <span aria-hidden="true">＋</span> Add {noun}
        </Button>
      ))}
    </InsetGroup>
  );
}
