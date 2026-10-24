// Typed answers save when their field is left (blur). Before the window moves on by a key, a
// swipe or a sheet closing, leave the focused field first, so its answer is queued ahead of the
// save that Continue waits for: React doesn't fire onBlur for a field it removes.
export function commitFocused(): void {
  // Only a field that takes typing: leaving a button would move focus out of a dialog.
  const el = document.activeElement;
  if (el instanceof HTMLElement && (el.tagName === "INPUT" || el.tagName === "TEXTAREA" || el.isContentEditable)) el.blur();
}

// A long answer keeps ⌘↓ and ⌥↓ for moving within its text.
export function isLongText(target: EventTarget | null): boolean {
  return target instanceof HTMLElement && (target.tagName === "TEXTAREA" || target.isContentEditable);
}
