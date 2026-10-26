import { Button } from "@heroui/react";
import type { SaveState } from "./types";

const WORDS: Record<SaveState, string> = {
  idle: "", saving: "Saving…", saved: "Saved", error: "Couldn't save — retrying",
  conflict: "Changed in another tab", locked: "With the Town",
};

// What the app is doing with your answers, said quietly beside Save and close or ‹ Tasks.
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
