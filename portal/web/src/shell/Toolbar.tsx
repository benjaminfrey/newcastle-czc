import { Button } from "@heroui/react";
import type { SaveState } from "./types";

const WORDS: Record<SaveState, string> = {
  idle: "", saving: "Saving…", saved: "Saved", error: "Couldn't save — retrying",
  conflict: "Changed in another tab",
};

// What the app is doing with your answers, said quietly beside the toolbar's buttons.
export function SaveStatus({ state, onReload }: { state: SaveState; onReload?: () => void }) {
  return (
    <span className="flex items-center gap-2">
      <span role="status" aria-live="polite" className="text-[13px] text-[var(--app-secondary-label)]">{WORDS[state]}</span>
      {state === "conflict" && onReload && (
        <Button size="sm" variant="secondary" className="min-h-11" onPress={onReload}>Load the latest</Button>
      )}
    </span>
  );
}

type Props = { title: string; saveState: SaveState; onDone?: () => void; onReload?: () => void };

// The content pane's toolbar: the step's title, the save status and Done.
export default function Toolbar({ title, saveState, onDone, onReload }: Props) {
  return (
    <header className="flex min-h-14 items-center justify-between gap-4 border-b border-[var(--app-separator)] px-8 py-2">
      <h1 tabIndex={-1} data-step-title className="text-[22px] font-bold outline-none">{title}</h1>
      <div className="flex items-center gap-3">
        <SaveStatus state={saveState} onReload={onReload} />
        {onDone && <Button variant="secondary" className="min-h-11" onPress={onDone}>Done</Button>}
      </div>
    </header>
  );
}
