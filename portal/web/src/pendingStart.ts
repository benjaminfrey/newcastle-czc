// An application someone started before signing in. The emailed sign-in link opens a
// new tab, whose session storage is empty, so this one lives in local storage until
// it is used (once). Blocked or full storage means nothing is pending: the page then
// asks for the property again.
import type { ChosenProperty } from "./property";

export type PendingStart = { formKey: string; property: ChosenProperty | null; useKey: string | null };

const KEY = "portal.pendingStart";

export function savePendingStart(p: PendingStart): void {
  try {
    localStorage.setItem(KEY, JSON.stringify(p));
  } catch {
    // Nothing kept.
  }
}

export function peekPendingStart(): PendingStart | null {
  try {
    const raw = localStorage.getItem(KEY);
    return raw ? (JSON.parse(raw) as PendingStart) : null;
  } catch {
    return null;
  }
}

export function takePendingStart(): PendingStart | null {
  const p = peekPendingStart();
  try {
    localStorage.removeItem(KEY);
  } catch {
    // Nothing to clear.
  }
  return p;
}
