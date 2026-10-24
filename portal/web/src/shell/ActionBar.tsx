import { Button } from "@heroui/react";
import type { ShellActions } from "./types";

// Back and Continue. On a desktop they sit bottom right, Continue rightmost; on a phone
// Continue fills a bar fixed above the home indicator, and Back is the navigation bar's chevron.
export default function ActionBar({ actions, wide }: { actions: ShellActions; wide: boolean }) {
  if (!actions.onContinue && !actions.back) return null;
  if (wide) {
    return (
      <div data-action-bar className="flex justify-end gap-3 border-t border-[var(--app-separator)] px-8 py-4">
        {actions.back && <Button variant="secondary" className="min-h-11 min-w-24" onPress={actions.back}>Back</Button>}
        {actions.onContinue && (
          <Button type="submit" variant="primary" className="min-h-11 min-w-28">{actions.continueLabel ?? "Continue"}</Button>
        )}
      </div>
    );
  }
  if (!actions.onContinue) return null;
  return (
    <div data-action-bar
         className="fixed inset-x-0 bottom-0 z-10 border-t border-[var(--app-separator)] bg-[var(--app-row)]/95 px-4 pt-3 backdrop-blur"
         style={{ paddingBottom: "max(0.75rem, env(safe-area-inset-bottom))" }}>
      <Button type="submit" variant="primary" fullWidth className="min-h-12 text-[17px]">{actions.continueLabel ?? "Continue"}</Button>
    </div>
  );
}
