import { Button } from "@heroui/react";
import type { ShellActions } from "./types";

// The dots at the bottom left; Back and Continue at the bottom right, Continue rightmost. A
// question a tap answers has no Continue. On a phone the bar is fixed above the home indicator,
// and Back is the navigation bar's chevron.
export default function ActionBar({ actions, wide }: { actions: ShellActions; wide: boolean }) {
  if (!actions.onContinue && !actions.back && !actions.dots) return null;
  if (wide) {
    return (
      <div data-action-bar className="flex items-center justify-end gap-3 border-t border-[var(--app-separator)] px-8 py-4">
        {actions.dots && <div className="mr-auto">{actions.dots}</div>}
        {actions.back && <Button variant="secondary" className="min-h-11 min-w-24 text-[var(--app-label)]" onPress={actions.back}>Back</Button>}
        {actions.onContinue && (
          <Button type="submit" variant="primary" className="min-h-11 min-w-28">{actions.continueLabel ?? "Continue"}</Button>
        )}
      </div>
    );
  }
  if (!actions.onContinue && !actions.dots) return null;
  return (
    <div data-action-bar
         className="fixed inset-x-0 bottom-0 z-10 flex min-h-[68px] items-center gap-3 border-t border-[var(--app-separator)] bg-[var(--app-row)]/95 px-4 pt-3 backdrop-blur"
         style={{ paddingBottom: "max(0.75rem, env(safe-area-inset-bottom))" }}>
      {actions.dots && <div className="mr-auto">{actions.dots}</div>}
      {actions.onContinue && (
        <Button type="submit" variant="primary" fullWidth={!actions.dots}
                className={`min-h-12 text-[17px] ${actions.dots ? "min-w-32" : ""}`}>{actions.continueLabel ?? "Continue"}</Button>
      )}
    </div>
  );
}
